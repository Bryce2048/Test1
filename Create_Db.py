import sqlite3
import json
#
# Define the SQLite database name
db_name = "warehouse_data2.db"
#
# Create database and tables
def create_database():
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Table: Material_DB (Structure Only, No JSON Data)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Material_DB (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name TEXT,
            pallets TEXT,
            tlf_name TEXT,
            bins TEXT,
            total_qty INTEGER,
            notes TEXT
        )
    """)

    # Table: Bulk_Storage_Rack_System (Populated from JSON)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Bulk_Storage_Rack_System (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            po_number TEXT,
            material_name TEXT,
            tlf_code TEXT,
            project_name TEXT,
            project_number TEXT,
            movement_log TEXT,
            innergy_sku TEXT,
            current_bin TEXT,
            date_received TEXT,
            pallet_qty TEXT,
            updated_qty TEXT,
            notes TEXT,
            UNIQUE(po_number, material_name, date_received)
        )
    """)

    conn.commit()
    conn.close()
    print("Tables created successfully.")

# Function to insert data into Bulk_Storage_Rack_System from JSON
def insert_data_from_json(json_file):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Load JSON file
    with open(json_file, "r", encoding="utf-8") as file:
        try:
            data = json.load(file)  # Parse JSON correctly
            print(f"Loaded JSON type: {type(data)}")  # Debugging

            # Ensure we are accessing the "Items" key
            if "Items" in data:
                data = data["Items"]
            else:
                print("Error: JSON file does not contain 'Items' key.")
                return
            
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return

    # Track the number of items added
    items_added = 0
    batch_data = []

    # Iterate over each purchase order in the "Items" array
    for order in data:
        po_number = order.get("Number")
        
        # Handle missing "Projects" safely
        projects = order.get("Projects", [])
        project_name = projects[0] if projects else None  

        date_received = None

        # Extract line items if available
        if "LineItems" in order and len(order["LineItems"]) > 0:
            for line_item in order["LineItems"]:  # Loop through all line items
                material_name = line_item.get("MaterialName")
                innergy_sku = line_item.get("InnergySKU")
                date_received = line_item.get("FirstDateReceived")

                # Check if the record already exists
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM Bulk_Storage_Rack_System
                    WHERE po_number = ? AND material_name = ? AND date_received = ?
                """, (po_number, material_name, date_received))
                count = cursor.fetchone()[0]

                if count == 0:
                    # Add to batch data if the record does not exist
                    batch_data.append((
                        po_number, material_name, None, project_name, None, None,
                        innergy_sku, None, date_received, None, None
                    ))
                    items_added += 1

    # Insert batch data into the database
    if batch_data:
        cursor.executemany("""
            INSERT INTO Bulk_Storage_Rack_System (
                po_number, material_name, tlf_code, project_name,
                project_number, movement_log, innergy_sku, current_bin,
                date_received, pallet_qty, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch_data)

    # Commit and close connection
    conn.commit()
    conn.close()
    print(f"Data inserted successfully. Items added: {items_added}")

# Run the script
if __name__ == "__main__":
    create_database()
    json_file_path = "PO Response.json"  # Replace with actual JSON file path
    insert_data_from_json(json_file_path)