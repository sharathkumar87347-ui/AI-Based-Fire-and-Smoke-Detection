import pandas as pd
import numpy as np

np.random.seed(42)

rows = 2000

smoke = np.random.uniform(100, 1000, rows)
temperature = np.random.uniform(20, 60, rows)
humidity = np.random.uniform(20, 90, rows)

fire_risk = (
    (smoke > 650) & (temperature > 40)
) | (
    (smoke > 850) & (temperature > 30)
)

data = pd.DataFrame({
    "smoke": smoke,
    "temperature": temperature,
    "humidity": humidity,
    "fire_risk": fire_risk.astype(int)
})

data["fire_risk"] = data["fire_risk"].map({
    0: "NORMAL",
    1: "FIRE RISK"
})

data.to_csv("fire_sensor_data.csv", index=False)

print("Dataset created successfully!")
print(data.head())
print("\nClass distribution:")
print(data["fire_risk"].value_counts())