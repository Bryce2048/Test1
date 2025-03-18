import sqlite3
from datetime import datetime
from print_bundle_labels import create_label_pdf, print_pdf
import win32print  # For getting the default printer

db_name = "warehouse_data2.db"
#
def get_available_materials(po_number):
    """Fetches available materials and their quantities for a given PO, ensuring it subtracts bundled items correctly."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT bs.id, bs.project_name, bs.project_number, bs.material_name, COALESCE(bs.pallet_qty, 0), 
               COALESCE(SUM(COALESCE(bi.quantity, 0)), 0) AS total_bundled
        FROM Bulk_Storage_Rack_System bs
        LEFT JOIN Bundle_Items bi ON bs.id = bi.material_id
        WHERE bs.po_number = ?
        GROUP BY bs.id;
    """, (po_number,))

    materials = {
        row[0]: {
            "name": row[1],
            "available_qty": max(int(row[2]) - int(row[3]), 0)  # Ensure it doesn't go negative
        }
        for row in cursor.fetchall()
    }

    conn.close()
    return materials




def create_bundle(po_number, bin_name, selected_materials):
    """Creates a new bundle for a PO, ensuring materials do not exceed available quantity, and prints a label."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # ✅ Check available materials before bundling
    available_materials = get_available_materials(po_number)

    for material_id, selected_qty in selected_materials.items():
        if material_id not in available_materials:
            print(f"⚠️ Material ID {material_id} not found in PO {po_number}.")
            conn.close()
            return False

        if selected_qty > int(available_materials[material_id]["available_qty"]):
            print(f"⚠️ Cannot bundle {selected_qty} of {available_materials[material_id]['name']}. "
                  f"Only {available_materials[material_id]['available_qty']} available.")
            conn.close()
            return False

    # ✅ Generate a unique bundle barcode
    today = datetime.today().strftime("%Y%m%d")
    cursor.execute("SELECT COUNT(*) FROM Bundles;")
    bundle_count = cursor.fetchone()[0] + 1
    bundle_id = f"B-{today}-{bundle_count:03d}"

    # ✅ Insert bundle record
    cursor.execute("""
        INSERT INTO Bundles (barcode, po_number, date_received, bin_name)
        VALUES (?, ?, DATE('now'), ?);
    """, (bundle_id, po_number, bin_name))

    # ✅ Insert materials into the bundle
    for material_id, quantity in selected_materials.items():
        cursor.execute("""
            INSERT INTO Bundle_Items (bundle_id, material_id, quantity)
            VALUES (?, ?, ?);
        """, (bundle_id, material_id, quantity))

        # ✅ Update pallet quantity
        cursor.execute("""
            UPDATE Bulk_Storage_Rack_System
            SET pallet_qty = pallet_qty - ?
            WHERE id = ?;
        """, (quantity, material_id))

    conn.commit()
    conn.close()
    print(f"✅ Bundle {bundle_id} created successfully.")

    # ✅ Generate label
    bundle_data = (bundle_id, po_number, bin_name)
    label_pdf = create_label_pdf(bundle_data)
    
    # ✅ Automatically Print Label
    try:
        default_printer = win32print.GetDefaultPrinter()  # Get system default printer
        print_pdf(label_pdf, default_printer)
        print(f"🖨 Label for {bundle_id} sent to printer: {default_printer}")
    except Exception as e:
        print(f"❌ Printing failed: {e}")

    return True



def bundle_materials(po_number, bin_name, selected_materials):
    """Bundles only the selected materials from the PO."""
    if not selected_materials:
        print("⚠️ No materials selected for bundling.")
        return

    success = create_bundle(po_number, bin_name, selected_materials)
    if success:
        print("✅ Bundling complete.")

def move_bundle(bundle_id, new_bin):
    """Moves a bundle to a different bin."""
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Bundles
            SET bin_name = ?
            WHERE barcode = ?;
        """, (new_bin, bundle_id))
        conn.commit()

    print(f"✅ Bundle {bundle_id} moved to Bin {new_bin} successfully.")
