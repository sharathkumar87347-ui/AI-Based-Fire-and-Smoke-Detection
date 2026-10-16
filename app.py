import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import joblib
import plotly.graph_objects as go
import sqlite3
import hashlib
import random
import time
from datetime import datetime

# ---------------- PAGE CONFIG ----------------

st.set_page_config(
    page_title="AIoT Fire Detection System",
    page_icon="🔥",
    layout="wide"
)

DB_NAME = "fire_users.db"
MODEL_NAME = "fire_model.pkl"

# ---------------- DATABASE ----------------

def get_connection():
    return sqlite3.connect(DB_NAME)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_database():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            smoke REAL,
            temperature REAL,
            humidity REAL,
            prediction TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sensor_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            smoke REAL,
            temperature REAL,
            humidity REAL,
            prediction TEXT,
            created_at TEXT
        )
    """)

    cur.execute(
        "SELECT username FROM users WHERE username = ?",
        ("admin",)
    )

    if cur.fetchone() is None:
        cur.execute(
            "INSERT INTO users VALUES (?, ?, ?)",
            ("admin", hash_password("Admin@123"), "admin")
        )

    conn.commit()
    conn.close()

create_database()

# ---------------- SESSION STATE ----------------

defaults = {
    "logged_in": False,
    "username": "",
    "role": "",
    "history": [],
    "last_alert_key": None,
    "automatic_mode": False
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------------- AUTHENTICATION ----------------

def register_user(username, password):
    username = username.strip()

    if not username or not password:
        return False, "Enter a username and password."

    if len(password) < 8:
        return False, "Use a password with at least 8 characters."

    conn = get_connection()

    try:
        conn.execute(
            "INSERT INTO users VALUES (?, ?, ?)",
            (username, hash_password(password), "user")
        )
        conn.commit()
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, "That username already exists."
    finally:
        conn.close()

def authenticate(username, password):
    conn = get_connection()

    row = conn.execute(
        "SELECT password, role FROM users WHERE username = ?",
        (username.strip(),)
    ).fetchone()

    conn.close()

    if row and row[0] == hash_password(password):
        return row[1]

    return None

# ---------------- LOGIN ----------------

if not st.session_state.logged_in:

    st.title("🔥 AIoT Fire and Smoke Detection")
    st.write("Welcome to the Fire Risk Monitoring Portal.")

    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login")

        if login_button:
            role = authenticate(username, password)

            if role:
                st.session_state.logged_in = True
                st.session_state.username = username.strip()
                st.session_state.role = role
                st.rerun()
            else:
                st.error("Invalid username or password.")

    with register_tab:
        with st.form("register_form"):
            new_username = st.text_input("Create username")
            new_password = st.text_input(
                "Create password",
                type="password"
            )
            register_button = st.form_submit_button("Register")

        if register_button:
            success, message = register_user(
                new_username,
                new_password
            )

            if success:
                st.success(message)
            else:
                st.error(message)

    st.info(
        "Local demo administrator: admin / Admin@123. "
        "Change this before any public deployment."
    )

    st.caption(
        "Educational simulation only. "
        "This application is not a certified fire alarm."
    )

    st.stop()

# ---------------- SIDEBAR ----------------

st.sidebar.title("🔥 AIoT Monitoring")

st.sidebar.write(f"User: {st.session_state.username}")
st.sidebar.write(f"Role: {st.session_state.role.title()}")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.automatic_mode = False
    st.rerun()

# ---------------- ADMIN ----------------

if st.session_state.role == "admin":

    st.title("👨‍💼 Administrator Dashboard")
    st.write("System overview and recorded events.")

    conn = get_connection()

    users_df = pd.read_sql_query(
        "SELECT username, role FROM users ORDER BY username",
        conn
    )

    alerts_df = pd.read_sql_query(
        "SELECT * FROM alerts ORDER BY id DESC",
        conn
    )

    history_df = pd.read_sql_query(
        "SELECT * FROM sensor_history ORDER BY id DESC LIMIT 500",
        conn
    )

    conn.close()

    c1, c2, c3 = st.columns(3)

    c1.metric("Registered Users", len(users_df))
    c2.metric("Recorded Alerts", len(alerts_df))
    c3.metric(
        "Fire-Risk Events",
        int((alerts_df["prediction"] == "FIRE RISK").sum())
        if not alerts_df.empty else 0
    )

    st.subheader("Registered Users")
    st.dataframe(users_df, use_container_width=True)

    st.subheader("Alert History")
    st.dataframe(alerts_df, use_container_width=True)

    st.subheader("Recent Sensor History")
    st.dataframe(history_df, use_container_width=True)

    if not alerts_df.empty:
        st.download_button(
            "📥 Download Alert History CSV",
            alerts_df.to_csv(index=False).encode("utf-8"),
            file_name="fire_alert_history.csv",
            mime="text/csv"
        )

    if not history_df.empty:
        st.download_button(
            "📥 Download Sensor History CSV",
            history_df.to_csv(index=False).encode("utf-8"),
            file_name="sensor_history.csv",
            mime="text/csv"
        )

    st.stop()

# ---------------- LOAD MODEL ----------------

try:
    model = joblib.load(MODEL_NAME)
except Exception as error:
    st.error(f"Could not load the trained model: {error}")
    st.stop()

# ---------------- MAIN DASHBOARD ----------------

st.title("🔥 AI-Based Fire and Smoke Detection")
st.caption("Software-only AIoT prototype using simulated sensor data.")

st.warning(
    "Demonstration only: readings are simulated. "
    "This system cannot detect an actual fire."
)

# ---------------- INPUT MODES ----------------

st.sidebar.subheader("Sensor Simulation")

mode = st.sidebar.radio(
    "Choose simulation mode",
    ["Manual", "Automatic"]
)

if mode == "Manual":

    smoke = st.sidebar.slider(
        "Smoke Level",
        min_value=100,
        max_value=1000,
        value=400
    )

    temperature = st.sidebar.slider(
        "Temperature (°C)",
        min_value=20,
        max_value=60,
        value=30
    )

    humidity = st.sidebar.slider(
        "Humidity (%)",
        min_value=20,
        max_value=90,
        value=50
    )

else:

    st.sidebar.info(
        "Automatic mode generates simulated sensor readings."
    )

    if st.sidebar.button("Generate New Sensor Readings") or \
       "automatic_readings" not in st.session_state:

        st.session_state.automatic_readings = {
            "smoke": random.randint(100, 1000),
            "temperature": random.randint(20, 60),
            "humidity": random.randint(20, 90)
        }

    readings = st.session_state.automatic_readings

    smoke = readings["smoke"]
    temperature = readings["temperature"]
    humidity = readings["humidity"]

# ---------------- PREDICTION ----------------

sensor_input = pd.DataFrame(
    [[smoke, temperature, humidity]],
    columns=["smoke", "temperature", "humidity"]
)

prediction = str(model.predict(sensor_input)[0])

risk_detected = prediction == "FIRE RISK"

# Obtain the model's estimated probability for FIRE RISK
class_names = list(model.classes_)
fire_risk_probability = 0.0

if "FIRE RISK" in class_names:
    probabilities = model.predict_proba(sensor_input)[0]
    fire_index = class_names.index("FIRE RISK")
    fire_risk_probability = float(probabilities[fire_index])

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ---------------- SENSOR METRICS ----------------

st.subheader("📡 Current Sensor Readings")

c1, c2, c3 = st.columns(3)

c1.metric("💨 Smoke Level", f"{smoke:.0f}")
c2.metric("🌡️ Temperature", f"{temperature:.1f} °C")
c3.metric("💧 Humidity", f"{humidity:.1f}%")

# ---------------- AI RESULT ----------------

st.subheader("🚨 AI Fire and Smoke Detection")

if risk_detected:
    st.error("🚨 EMERGENCY ALERT: POSSIBLE FIRE DETECTED!")

    components.html("""
    <audio controls autoplay loop>
        <source src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg"
                type="audio/ogg">
        Your browser does not support audio.
    </audio>
""", height=70)

    st.warning("⚠️ TAKE IMMEDIATE PRECAUTIONS")
    st.write("🔥 Possible fire risk detected!")
    st.write("🏃 Move away from the suspected danger area.")
    st.write("📢 Warn nearby people.")
    st.write("📞 Contact emergency services if needed.")

else:
    st.success("✅ NO FIRE RISK DETECTED")
    st.write("The AI model classified the current readings as NORMAL.")

# ---------------- VISUALIZATION ----------------

left, right = st.columns(2)

with left:
    fig = go.Figure(
        data=[
            go.Bar(
                x=["Smoke", "Temperature", "Humidity"],
                y=[smoke, temperature, humidity]
            )
        ]
    )

    fig.update_layout(
        title="Current Sensor Readings",
        yaxis_title="Reading",
        height=350
    )

    st.plotly_chart(fig, use_container_width=True)

with right:
    gauge = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=100 if risk_detected else 0,
            title={"text": "Model Risk Classification"},
            gauge={
                "axis": {"range": [0, 100]},
                "steps": [
                    {"range": [0, 50]},
                    {"range": [50, 100]}
                ]
            }
        )
    )

    gauge.update_layout(height=350)
    st.plotly_chart(gauge, use_container_width=True)

# ---------------- SAVE SENSOR HISTORY ----------------

conn = get_connection()

conn.execute(
    """
    INSERT INTO sensor_history
    (username, smoke, temperature, humidity, prediction, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """,
    (
        st.session_state.username,
        smoke,
        temperature,
        humidity,
        prediction,
        now
    )
)

# ---------------- SAVE ALERTS ----------------

if risk_detected:

    alert_key = (
        st.session_state.username,
        smoke,
        temperature,
        humidity,
        prediction
    )

    if st.session_state.last_alert_key != alert_key:

        conn.execute(
            """
            INSERT INTO alerts
            (username, smoke, temperature, humidity, prediction, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                st.session_state.username,
                smoke,
                temperature,
                humidity,
                prediction,
                now
            )
        )

        st.session_state.last_alert_key = alert_key

conn.commit()
conn.close()

# ---------------- HISTORY ----------------

st.subheader("📜 Sensor History & Analytics")

conn = get_connection()

user_history = pd.read_sql_query(
    """
    SELECT id, smoke, temperature, humidity,
           prediction, created_at
    FROM sensor_history
    WHERE username = ?
    ORDER BY id DESC
    LIMIT 500
    """,
    conn,
    params=(st.session_state.username,)
)

conn.close()

if user_history.empty:
    st.info("No sensor history available yet.")

else:
    # SEARCH AND FILTER

    col1, col2 = st.columns(2)

    with col1:
        search_prediction = st.selectbox(
            "Filter by Prediction",
            ["ALL", "NORMAL", "FIRE RISK"]
        )

    with col2:
        search_smoke = st.number_input(
            "Minimum Smoke Level",
            min_value=0,
            max_value=1000,
            value=0
        )

    filtered_history = user_history.copy()

    if search_prediction != "ALL":
        filtered_history = filtered_history[
            filtered_history["prediction"] == search_prediction
        ]

    filtered_history = filtered_history[
        filtered_history["smoke"] >= search_smoke
    ]

    # SUMMARY METRICS

    st.subheader("📊 Your Statistics")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Total Records",
        len(filtered_history)
    )

    c2.metric(
        "Fire Risk Records",
        int(
            (filtered_history["prediction"] == "FIRE RISK").sum()
        )
    )

    c3.metric(
        "Normal Records",
        int(
            (filtered_history["prediction"] == "NORMAL").sum()
        )
    )

    # HISTORY TABLE

    st.subheader("📋 Filtered Sensor Records")

    st.dataframe(
        filtered_history,
        use_container_width=True,
        hide_index=True
    )

    # SENSOR TREND

    st.subheader("📈 Sensor Reading Trends")

    chart_data = filtered_history.copy()

    chart_data["created_at"] = pd.to_datetime(
        chart_data["created_at"]
    )

    chart_data = chart_data.sort_values("created_at")

    st.line_chart(
        chart_data.set_index("created_at")[
            ["smoke", "temperature", "humidity"]
        ]
    )

    # DOWNLOAD CSV

    st.download_button(
        "📥 Download Filtered History (CSV)",
        data=filtered_history.to_csv(index=False).encode("utf-8"),
        file_name="sensor_history_report.csv",
        mime="text/csv"
    )

st.caption(
    "Educational simulation only. "
    "These predictions are not a substitute for certified fire alarms."
)