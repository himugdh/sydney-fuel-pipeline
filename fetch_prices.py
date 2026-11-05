import os
import json
import uuid
from datetime import datetime

import requests
from dotenv import load_dotenv

# Load your secret keys from the .env file
load_dotenv()
API_KEY = os.getenv("FUEL_API_KEY")
API_SECRET = os.getenv("FUEL_API_SECRET")

BASE_URL = "https://api.onegov.nsw.gov.au"


def get_token():
    """Step 1: swap your key and secret for a temporary token."""
    url = f"{BASE_URL}/oauth/client_credential/accesstoken"
    response = requests.get(
        url,
        params={"grant_type": "client_credentials"},
        auth=(API_KEY, API_SECRET),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_all_prices(token):
    """Step 2: use the token to get every fuel price in NSW."""
    url = f"{BASE_URL}/FuelPriceCheck/v2/fuel/prices"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Bearer {token}",
        "apikey": API_KEY,
        "transactionid": str(uuid.uuid4()),
        "requesttimestamp": datetime.now().strftime("%d/%m/%Y %I:%M:%S %p"),
    }
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    return response.json()


def main():
    token = get_token()
    data = get_all_prices(token)

    # Save the raw response exactly as we got it (the "raw layer")
    os.makedirs("data", exist_ok=True)
    filename = f"data/raw_prices_{datetime.now():%Y-%m-%d}.json"
    with open(filename, "w") as f:
        json.dump(data, f)

    print(f"Saved to {filename}")
    print("Stations:", len(data.get("stations", [])))
    print("Prices:", len(data.get("prices", [])))


if __name__ == "__main__":
    main()