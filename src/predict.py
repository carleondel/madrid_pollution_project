
import pandas as pd
import pickle
import os

# Define la ruta base del proyecto, subiendo desde src/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define la carpeta de datos
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Define la carpeta de modelos
MODEL_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)


df = pd.read_csv(os.path.join(DATA_DIR, "no2_transformed.csv"), parse_dates=["time"])
df["hour"] = df["time"].dt.hour

# Cargar el modelo
with open(os.path.join(MODEL_DIR, "model.pkl"), "rb") as f:
    model = pickle.load(f)

df["predicted_no2"] = model["mean_no2"]
df.to_csv(os.path.join(DATA_DIR, "no2_predicted.csv"), index=False)
