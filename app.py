from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import mysql.connector
from mysql.connector import Error
import tomllib
import streamlit as st
import requests
import pandas as pd

# -------------------------------------------------------
# Load secrets
# -------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
SECRET_FILES = [
    BASE_DIR / "secrets.toml",
    BASE_DIR / "salaiset_jutut_eli_salasanat.toml",
]


def load_secrets():
    for f in SECRET_FILES:
        if f.exists():
            with open(f, "rb") as fp:
                return tomllib.load(fp)
    raise FileNotFoundError("No secrets.toml found!")


secrets = load_secrets()

DB_HOST = secrets["mysql"]["host"]
DB_USER = secrets["mysql"]["user"]
DB_PASS = secrets["mysql"]["password"]
DB_NAME = secrets["mysql"]["database"]

CITY = secrets["api"]["city"]

# -------------------------------------------------------
# Helpers
# -------------------------------------------------------


def to_local_time_str(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=ZoneInfo("UTC"))
    return ts.astimezone(ZoneInfo("Europe/Helsinki")).strftime("%Y-%m-%d %H:%M")


def get_latest_weather():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
        )
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT city, temperature, humidity, description, timestamp "
            "FROM weather_data ORDER BY timestamp DESC LIMIT 1"
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row
    except Error as e:
        st.error(f"Database error (latest): {e}")
        return None


def get_weather_history():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
        )
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT temperature, humidity, timestamp "
            "FROM weather_data WHERE city = %s ORDER BY timestamp ASC",
            (CITY,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Error as e:
        st.error(f"Database error (history): {e}")
        return []


# -------------------------------------------------------
# Streamlit UI
# -------------------------------------------------------

st.set_page_config(page_title="Weather Command Center", page_icon="⛅", layout="wide")

st.title("Weather Command Center")
st.caption(f"Weather data for city: {CITY}")

# Latest measurement
st.subheader("Latest measurement")
latest = get_latest_weather()

if latest:
    ts = latest["timestamp"]
    ts_str = to_local_time_str(ts) if isinstance(ts, datetime) else str(ts)

    c1, c2, c3 = st.columns(3)

    # temperature
    c1.metric("Temperature (C)", f"{latest['temperature']:.1f}")

    # humidity
    if latest["humidity"] is not None:
        c2.metric("Humidity (%)", f"{latest['humidity']:.0f}")
    else:
        c2.metric("Humidity (%)", "N/A")

    # description + timestamp, without any tricky f-strings
    c3.write("**Description:**")
    c3.write(str(latest["description"]))
    c3.write("")
    c3.write(f"**Updated:** {ts_str}")
else:
    st.warning("No weather data found in database.")


# History section
st.markdown("---")
st.subheader("History")

history = get_weather_history()

if history:
    rows = []
    for r in history:
        ts = r["timestamp"]
        ts_str = to_local_time_str(ts) if isinstance(ts, datetime) else str(ts)
        rows.append(
            {
                "Time": ts_str,
                "Temperature (C)": r["temperature"],
                "Humidity (%)": r["humidity"],
            }
        )

    df = pd.DataFrame(rows).set_index("Time")

    t1, t2 = st.tabs(["Temperature", "Humidity"])
    with t1:
        st.line_chart(df["Temperature (C)"])
    with t2:
        st.line_chart(df["Humidity (%)"])
else:
    st.info("No history data for this city.")


# Random stranger section
st.markdown("---")
st.subheader("Random stranger")

if st.button("Fetch random person"):
    try:
        r = requests.get("https://randomuser.me/api/", timeout=10)
        r.raise_for_status()
        data = r.json()
        user = data["results"][0]

        full_name = f"{user['name']['first']} {user['name']['last']}"
        age = user["dob"]["age"]
        country = user["location"]["country"]
        img_url = user["picture"]["large"]

        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(img_url, caption=full_name)
        with col2:
            st.write(f"**Name:** {full_name}")
            st.write(f"**Age:** {age}")
            st.write(f"**Country:** {country}")
    except Exception as e:
        st.error(f"RandomUser API error: {e}")
