# src/extract.py

import requests
import pandas as pd
from datetime import datetime, timedelta

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
df.to_csv("../data/no2_madrid.csv", index=False)
