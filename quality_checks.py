import glob
import json
import sys
from datetime import datetime, timedelta

MIN_STATIONS = 2500      # the API says 2500+ stations
MIN_PRICES = 5000        # we got 10,533 on day one
MAX_BAD_SHARE = 0.01     # allow up to 1% odd prices
MAX_AGE_DAYS = 3         # newest price must be recent

# Believable (min, max) for each fuel type. Liquid fuels are cents per litre.
# EV is priced differently (looks like cents per kWh), so it gets its own range.
PRICE_RANGES = {
    "U91": (50, 500),
    "E10": (50, 500),
    "P95": (50, 500),
    "P98": (50, 500),
    "DL": (50, 500),
    "PDL": (50, 500),
    "B20": (50, 500),
    "E85": (50, 500),
    "LPG": (30, 500),
    "EV": (0, 200),
}


def parse_time(text):
    return datetime.strptime(text, "%d/%m/%Y %H:%M:%S")


def main():
    filename = sorted(glob.glob("data/raw_prices_*.json"))[-1]
    print("Checking", filename)
    with open(filename) as f:
        data = json.load(f)

    stations = data.get("stations", [])
    prices = data.get("prices", [])
    failures = []

    # Check 1: did we get enough data?
    if len(stations) < MIN_STATIONS:
        failures.append(f"Only {len(stations)} stations (expected {MIN_STATIONS}+)")
    if len(prices) < MIN_PRICES:
        failures.append(f"Only {len(prices)} prices (expected {MIN_PRICES}+)")

    # Check 2: is each price believable for its own fuel type?
    bad = []
    unknown_types = set()
    for p in prices:
        fuel = p.get("fueltype")
        if fuel not in PRICE_RANGES:
            unknown_types.add(fuel)
            continue
        low, high = PRICE_RANGES[fuel]
        if p.get("price") is None or not (low <= p["price"] <= high):
            bad.append(p)

    if unknown_types:
        print("Warning: new fuel types we have no range for:", sorted(unknown_types))

    if prices and len(bad) / len(prices) > MAX_BAD_SHARE:
        failures.append(f"{len(bad)} prices outside their expected range")
    elif bad:
        print(f"Warning: {len(bad)} odd prices, e.g. {bad[:2]}")

    # Check 3: does every price belong to a known station?
    known = {int(s["code"]) for s in stations}
    orphans = [p for p in prices if int(p["stationcode"]) not in known]
    if prices and len(orphans) / len(prices) > MAX_BAD_SHARE:
        failures.append(f"{len(orphans)} prices have no matching station")

    # Check 4: is the data fresh?
    if prices:
        newest = max(parse_time(p["lastupdated"]) for p in prices)
        if datetime.now() - newest > timedelta(days=MAX_AGE_DAYS):
            failures.append(f"Newest price is old: {newest}")

    if failures:
        print("\nQUALITY CHECKS FAILED:")
        for message in failures:
            print(" -", message)
        sys.exit(1)

    print("All quality checks passed")


if __name__ == "__main__":
    main()