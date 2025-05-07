

import requests
import pandas as pd
from datetime import datetime, timedelta
import os

# Directorio base del proyecto (padre de 'src')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)


today = datetime.today()
yesterday = today - timedelta(days=1)

url = "https://air-quality-api.open-meteo.com/v1/air-quality"
params = {
    "latitude": 40.4168,
    "longitude": -3.7038,
    "start_date": yesterday.strftime("%Y-%m-%d"),
    "end_date": today.strftime("%Y-%m-%d"),
    "hourly": "nitrogen_dioxide",
    "timezone": "Europe/Madrid"
}

response = requests.get(url, params=params)
data = response.json()

df = pd.DataFrame(data['hourly'])
df['time'] = pd.to_datetime(df['time'])
df.to_csv(os.path.join(DATA_DIR, "no2_madrid.csv"), index=False)
