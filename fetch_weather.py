#!/usr/bin/env python3
import requests
import mysql.connector
from datetime import datetime, timezone
from pathlib import Path
import tomllib

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SECRET_FILE = BASE_DIR / "secrets.toml"
ALTERNATE_SECRET_FILE = BASE_DIR / "salaiset_jutut_eli_salasanat.toml"


def load_secrets() -> dict:
    if DEFAULT_SECRET_FILE.exists():
        secret_file = DEFAULT_SECRET_FILE
    elif ALTERNATE_SECRET_FILE.exists():
        secret_file = ALTERNATE_SECRET_FILE
    else:
        raise FileNotFoundError(
            "Missing secrets file: expected default 'secrets.toml' or alternate "
            "'salaiset_jutut_eli_salasanat.toml' in the application directory."
        )

    with open(secret_file, "rb") as f:
        return tomllib.load(f)


secrets = load_secrets()

api_cfg = secrets["api"]
db_cfg = secrets["mysql"]

API_KEY = api_cfg["openweather_api_key"]
CITY_ID = api_cfg.get("city_id", 649360)

URL = (
    f"https://api.openweathermap.org/data/2.5/weather"
    f"?id={CITY_ID}&appid={API_KEY}&units=metric"
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

    # Haetaan kaupungin nimi API-vastauksesta
    city_name = data.get("name", "Unknown")

    cursor.execute(
        "INSERT INTO weather_data (city, temperature, humidity, description, timestamp) VALUES (%s, %s, %s, %s, %s)",
        (city_name, temp, humidity, desc, timestamp)
    )
    conn.commit()
    print(f"Saved: {city_name} {temp:.1f} C, {humidity}% RH, {desc}")
