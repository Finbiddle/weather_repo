from pathlib import Path
from flask import Flask, jsonify, redirect, url_for
import mysql.connector
from mysql.connector import Error
import tomllib
from datetime import datetime
from zoneinfo import ZoneInfo
from flask_cors import CORS
import requests

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SECRET_FILE = BASE_DIR / "salaiset_jutut_eli_salasanat.toml"
LEGACY_SECRET_FILE = BASE_DIR / "secrets.toml"
SECRET_FILE = DEFAULT_SECRET_FILE if DEFAULT_SECRET_FILE.exists() else LEGACY_SECRET_FILE

with open(SECRET_FILE, "rb") as f:
    secrets = tomllib.load(f)

db_cfg = secrets["mysql"]
api_cfg = secrets["api"]

DB_HOST = db_cfg["host"]
DB_USER = db_cfg["user"]
DB_PASS = db_cfg["password"]
DB_NAME = db_cfg["database"]
WEATHER_CITY = api_cfg["city"]

app = Flask(__name__)
CORS(app)

BASE_PATH = "/data-analysis"


@app.route("/")
def root_redirect():
    return redirect(url_for("app_root"))


@app.route(f"{BASE_PATH}/")
def app_root():
    return jsonify({"message": "Weather analysis app is running"})

def to_local_time_str(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=ZoneInfo("UTC"))
    tz_local = ts.astimezone(ZoneInfo("Europe/Helsinki"))
    return tz_local.strftime("%Y-%m-%d %H:%M")

@app.route(f"{BASE_PATH}/api/weather/latest")
def api_weather_latest():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT city, temperature, humidity, description, timestamp "
            "FROM weather_data ORDER BY timestamp DESC LIMIT 1"
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row:
            return jsonify({"error": "No weather data found"}), 404
        ts = row["timestamp"]
        if isinstance(ts, datetime):
            ts = to_local_time_str(ts)
        return jsonify({
            "city": row["city"],
            "temp": row["temperature"],
            "humidity": row["humidity"],
            "desc": row["description"],
            "timestamp": ts
        })
    except Error as e:
        return jsonify({"error": str(e)}), 500

@app.route(f"{BASE_PATH}/api/weather/history")
def api_weather_history():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT temperature, humidity, timestamp FROM weather_data "
            "WHERE city = %s ORDER BY timestamp ASC",
            (WEATHER_CITY,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        data = []
        for r in rows:
            ts = r["timestamp"]
            if isinstance(ts, datetime):
                ts = to_local_time_str(ts)
            data.append({
                "timestamp": ts,
                "temperature": r["temperature"],
                "humidity": r["humidity"] if r["humidity"] is not None else None
            })
        return jsonify(data)
    except Error as e:
        return jsonify({"error": str(e)}), 500

@app.route(f"{BASE_PATH}/api/other")
def api_other():
    try:
        res = requests.get("https://randomuser.me/api/")
        if res.status_code != 200:
            return jsonify({"message": "RandomUser API error"}), 502
        j = res.json()
        user = j["results"][0]
        full_name = f"{user['name']['first']} {user['name']['last']}"
        age = user["dob"]["age"]
        country = user["location"]["country"]
        picture = user["picture"]["large"]
        msg = f"Random stranger: {full_name}, {age} y/o, from {country}."
        return jsonify({"message": msg, "image": picture})
    except Exception as e:
        return jsonify({"message": f"RandomUser API failed: {e}", "image": ""}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
