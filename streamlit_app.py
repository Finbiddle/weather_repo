from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import mysql.connector
from mysql.connector import Error
import tomllib
import streamlit as st

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
db_cfg = secrets["mysql"]
api_cfg = secrets["api"]

DB_HOST = db_cfg["host"]
DB_USER = db_cfg["user"]
DB_PASS = db_cfg["password"]
DB_NAME = db_cfg["database"]
WEATHER_CITY = api_cfg["city"]


def to_local_time_str(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=ZoneInfo("UTC"))
    tz_local = ts.astimezone(ZoneInfo("Europe/Helsinki"))
    return tz_local.strftime("%Y-%m-%d %H:%M")


def get_latest_weather():
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
        return row
    except Error as e:
        st.error(f"Database error (latest): {e}")
        return None


def get_weather_history():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT temperature, humidity, timestamp "
            "FROM weather_data WHERE city = %s ORDER BY timestamp ASC",
            (WEATHER_CITY,),
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Error as e:
        st.error(f"Database error (history): {e}")
        return []


# ----------------- STREAMLIT UI -----------------

st.set_page_config(page_title="Weather Analysis", page_icon="⛅", layout="wide")

st.title("⛅ Säädata – Lahti")
st.caption("Pieni rakkaudella rakennettu sääanalyysipaneeli")


latest = get_latest_weather()
if latest:
    ts = latest["timestamp"]
    if isinstance(ts, datetime):
        ts_str = to_local_time_str(ts)
    else:
        ts_str = str(ts)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Lämpötila (°C)", f"{latest['temperature']:.1f}")
    with col2:
        if latest["humidity"] is not None:
            st.metric("Kosteus (%)", f"{latest['humidity']:.0f}")
        else:
            st.metric("Kosteus (%)", "–")
    with col3:
        st.write("**Kuvaus:**")
        st.write(latest["description"])
        st.write(f"**Päivitetty:** {ts_str}")
else:
    st.warning("Ei vielä säätietoja tietokannassa.")


st.markdown("---")
st.subheader("📈 Historia")

history = get_weather_history()
if history:
    import pandas as pd

    records = []
    for r in history:
        ts = r["timestamp"]
        if isinstance(ts, datetime):
            ts = to_local_time_str(ts)
        records.append(
            {
                "Aika": ts,
                "Lämpötila (°C)": r["temperature"],
                "Kosteus (%)": r["humidity"],
            }
        )

    df = pd.DataFrame(records)
    df = df.set_index("Aika")

    tab1, tab2 = st.tabs(["Lämpötila", "Kosteus"])
    with tab1:
        st.line_chart(df["Lämpötila (°C)"])
    with tab2:
        st.line_chart(df["Kosteus (%)"])
else:
    st.info("Historiadataa ei löytynyt tälle kaupungille.")
