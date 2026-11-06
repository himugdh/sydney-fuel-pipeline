import os
import json
import glob
from datetime import datetime

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()


def parse_time(text):
    return datetime.strptime(text, "%d/%m/%Y %H:%M:%S")


def main():
    # Use the newest raw file in the data folder
    filename = sorted(glob.glob("data/raw_prices_*.json"))[-1]
    print("Loading", filename)
    with open(filename) as f:
        data = json.load(f)

    station_rows = []
    for s in data["stations"]:
        loc = s.get("location") or {}
        station_rows.append((
            int(s["code"]),
            s.get("name"),
            s.get("brand"),
            s.get("address"),
            loc.get("latitude"),
            loc.get("longitude"),
            s.get("state"),
        ))

    known = {row[0] for row in station_rows}
    price_rows = []
    skipped = 0
    for p in data["prices"]:
        code = int(p["stationcode"])
        if code not in known:
            skipped += 1
            continue
        price_rows.append((code, p["fueltype"], p["price"], parse_time(p["lastupdated"])))

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    execute_values(cur, """
        insert into stations (station_code, name, brand, address, latitude, longitude, state)
        values %s
        on conflict (station_code) do update set
            name = excluded.name,
            brand = excluded.brand,
            address = excluded.address,
            latitude = excluded.latitude,
            longitude = excluded.longitude,
            state = excluded.state
    """, station_rows, page_size=1000)

    cur.execute("select count(*) from prices")
    before = cur.fetchone()[0]

    execute_values(cur, """
        insert into prices (station_code, fuel_type, price, last_updated)
        values %s
        on conflict do nothing
    """, price_rows, page_size=1000)

    cur.execute("select count(*) from prices")
    after = cur.fetchone()[0]

    conn.commit()
    conn.close()

    print("Stations loaded:", len(station_rows))
    print("New price rows added:", after - before)
    print("Price rows skipped (unknown station):", skipped)


if __name__ == "__main__":
    main()
    