import os

import pandas as pd
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Sydney Fuel Prices", layout="wide")

FUEL_NAMES = {
    "U91": "Unleaded 91",
    "E10": "E10",
    "P95": "Premium 95",
    "P98": "Premium 98",
    "DL": "Diesel",
    "PDL": "Premium Diesel",
    "LPG": "LPG",
    "E85": "E85",
    "B20": "Biodiesel B20",
}

# Shared by the queries below: the newest price for each station and fuel type
LATEST = """
with latest as (
    select distinct on (station_code, fuel_type)
        station_code, fuel_type, price, last_updated
    from prices
    order by station_code, fuel_type, last_updated desc
)
"""


def get_url():
    # On Streamlit Cloud the secret lives in st.secrets, on your laptop it is in .env
    try:
        return st.secrets["DATABASE_URL"]
    except Exception:
        return os.getenv("DATABASE_URL")


@st.cache_data(ttl=3600)
def run_query(sql, params=None):
    conn = psycopg2.connect(get_url())
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        columns = [c[0] for c in cur.description]
        rows = cur.fetchall()
    finally:
        conn.close()
    df = pd.DataFrame(rows, columns=columns)
    for col in ("price", "avg_price"):
        if col in df.columns:
            df[col] = df[col].astype(float)
    return df


st.title("NSW Fuel Prices")
st.caption("Data pulled daily from the NSW FuelCheck API by an automated pipeline.")

fuel = st.selectbox(
    "Fuel type", list(FUEL_NAMES.keys()), format_func=lambda k: FUEL_NAMES[k]
)

# 1. Cheapest stations right now
cheapest = run_query(
    LATEST + """
    select s.name, s.brand, s.address, s.latitude, s.longitude,
           l.price, l.last_updated
    from latest l
    join stations s on s.station_code = l.station_code
    where l.fuel_type = %s
    order by l.price
    limit 10
    """,
    (fuel,),
)

summary = run_query(
    LATEST + """
    select count(*) as stations, round(avg(price), 1) as avg_price
    from latest
    where fuel_type = %s
    """,
    (fuel,),
)

col1, col2, col3 = st.columns(3)
if not cheapest.empty:
    col1.metric("Cheapest right now (c/L)", f"{cheapest['price'].iloc[0]:.1f}")
    col2.metric("NSW average (c/L)", f"{summary['avg_price'].iloc[0]:.1f}")
    col3.metric("Stations reporting", int(summary["stations"].iloc[0]))

    st.subheader("10 cheapest stations right now")
    left, right = st.columns([3, 2])
    left.dataframe(
        cheapest[["name", "address", "price", "last_updated"]], hide_index=True
    )
    right.map(cheapest[["latitude", "longitude"]])
else:
    st.info("No prices found for this fuel type.")

# 2. Cheapest postcodes
st.subheader("Cheapest postcodes (3+ stations)")
postcodes = run_query(
    LATEST + r"""
    select substring(s.address from '(\d{4})\s*$') as postcode,
           round(avg(l.price), 1) as avg_price,
           count(*) as stations
    from latest l
    join stations s on s.station_code = l.station_code
    where l.fuel_type = %s and s.address ~ '\d{4}\s*$'
    group by 1
    having count(*) >= 3
    order by avg_price
    limit 15
    """,
    (fuel,),
)
st.bar_chart(postcodes.set_index("postcode")["avg_price"])

# 3. Trend over full days
st.subheader("Average price of prices updated each day")
trend = run_query(
    """
    select date(last_updated) as day,
           round(avg(price), 1) as avg_price,
           count(*) as price_changes
    from prices
    where fuel_type = %s
      and date(last_updated) >= '2026-11-05'
      and date(last_updated) < (now() at time zone 'Australia/Sydney')::date
    group by 1
    order by 1
    """,
    (fuel,),
)
if len(trend) >= 2:
    st.line_chart(trend.set_index("day")["avg_price"])
else:
    st.info("The trend needs a few full days of data. Check back after a few daily runs.")

st.caption(
    "History starts 5 Nov 2026. The trend shows the average of prices that changed "
    "on each day, not the average price across every station."
)