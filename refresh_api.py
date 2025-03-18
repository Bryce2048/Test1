import requests
import json
import os

# Constants
BASE_URL = "https://app.innergy.com"
API_KEY_PATH = r"U:\Production\workorder install program\api_key.txt"

# Determine the script's directory
script_dir = os.path.dirname(__file__)

# Construct file paths relative to the script's directory
PURCHASE_ORDERS_FILE = os.path.join(script_dir, "PO Response.json")
INVENTORY_FILE = os.path.join(script_dir, "Inventory response.json")

# Read API key safely
with open(API_KEY_PATH, "r") as key_file:
    API_KEY = key_file.read().strip()

# Common function to fetch data and write to a JSON file
def fetch_and_save_data(endpoint, file_path):
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Api-Key": API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            with open(file_path, "w", encoding="utf-8") as json_file:
                json.dump(data, json_file, indent=4)
            print(f"Data saved to {file_path}")
            return data
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None

# Fetch and save purchase orders
def refresh_PO_Response():
    return fetch_and_save_data("/api/purchaseOrders", PURCHASE_ORDERS_FILE)

# Fetch and save inventory
def refresh_Inventory_response():
    return fetch_and_save_data("/api/masterInventory", INVENTORY_FILE)

# Function to refresh PO data
def refresh_po_data():
    po_data = refresh_PO_Response()
    if po_data:
        print("Purchase Orders updated successfully.")
    inventory_data = refresh_Inventory_response()
    if inventory_data:
        print("Inventory data updated successfully.")

if __name__ == "__main__":
    refresh_po_data()
