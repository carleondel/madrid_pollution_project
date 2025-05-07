
import pandas as pd
import os

# Define la ruta base del proyecto, subiendo desde src/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define la carpeta de datos
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)



df = pd.read_csv(os.path.join(DATA_DIR, "no2_madrid.csv"), parse_dates=["time"])

# Ejemplo simple: eliminar valores nulos
df_transformed = df.dropna(subset=["nitrogen_dioxide"])

# Agregar media por hora (innecesario si ya es horario, pero sirve como ejemplo)
# df_clean = df_clean.resample("1H", on="time").mean().reset_index()

df_transformed.to_csv(os.path.join(DATA_DIR, "no2_transformed.csv"), index=False)
