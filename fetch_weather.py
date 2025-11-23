#!/usr/bin/env python3
import requests
import mysql.connector
from datetime import datetime
from pathlib import Path
import tomllib

BASE_DIR = Path(__file__).resolve().parent
with open(BASE_DIR / "secrets.toml", "rb") as f:
    secrets = tomllib.load(f)

api_cfg = secrets["api"]
db_cfg = secrets["mysql"]

API_KEY = api_cfg["openweather_api_key"]
CITY = api_cfg.get("city", "Lahti")

URL = (
    f"https://api.openweathermap.org/data/2.5/weather"
    f"?q={CITY}&appid={API_KEY}&units=metric"
)

conn = mysql.connector.connect(
    host=db_cfg["host"],
    user=db_cfg["user"],
    password=db_cfg["password"],
    database=db_cfg["database"],
)

cursor = conn.cursor()
cursor.execute(
    '''
    CREATE TABLE IF NOT EXISTS weather_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        city VARCHAR(50),
        temperature FLOAT,
        humidity FLOAT,
        description VARCHAR(100),
        timestamp DATETIME
    )
    '''
)

response = requests.get(URL)
data = response.json()

if response.status_code != 200 or "main" not in data:
    print("Error fetching data:", data)
else:
    temp = data["main"]["temp"]
    humidity = data["main"].get("humidity")
    desc = data["weather"][0]["description"]
    timestamp = datetime.utcnow()

    cursor.execute(
        "INSERT INTO weather_data (city, temperature, humidity, description, timestamp) VALUES (%s, %s, %s, %s, %s)",
        (CITY, temp, humidity, desc, timestamp)
    )
    conn.commit()
    print(f"Saved: {CITY} {temp:.1f} C, {humidity}% RH, {desc}")

cursor.close()
conn.close()
