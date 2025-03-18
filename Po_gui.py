import flet as ft
import sqlite3
from datetime import datetime, timedelta
from bundle_logic import create_bundle
from refresh_api import refresh_po_data
from  Create_Db import insert_data_from_json
import os
from datetime import datetime, timedelta
from bundle_logic import create_bundle
from refresh_api import refresh_po_data, PURCHASE_ORDERS_FILE, INVENTORY_FILE
from Create_Db import insert_data_from_json
db_name = "warehouse_data2.db"
##
# Add a global flag to indicate if an update is in progress
update_in_progress = False

# Define the refresh button
refresh_button = ft.ElevatedButton("🔄 Refresh PO Data", on_click=lambda e: refresh_po_database(e.page))

# ... existing code ...
### -----------------------------------
### 🔹 Fetch Unreceived Purchase Orders
### -----------------------------------
def get_unreceived_pos():
    """Fetches unreceived POs or those received in the past 7 days."""
    one_week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT id, po_number, project_name, date_received
            FROM Bulk_Storage_Rack_System
            WHERE date_received IS NULL OR date_received >= ?;
        """, (one_week_ago,))
        pos = cursor.fetchall()

    return pos

def get_available_materials(po_number):
    """Fetches available materials and their quantities for a given PO."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, material_name, pallet_qty
        FROM Bulk_Storage_Rack_System
        WHERE po_number = ?;
    """, (po_number,))
    
    materials = {
    row[0]: {"name": row[1], "available_qty": int(row[2]) if row[2] is not None else 0}  # ✅ Handle NULL values
    for row in cursor.fetchall()
}


    conn.close()
    return materials
### -----------------------------------
### 🔹 Refresh PO Data from API
### -----------------------------------I
def refresh_PO_Response():
    """Dummy function to simulate PO response refresh."""
    pass

def refresh_po_database(page):
    """Refreshes PO data from the API and updates the database."""
    global update_in_progress
    if update_in_progress:
        print("Update already in progress. Please wait.")
        return

    update_in_progress = True
    try:
        refresh_po_data()  # This will fetch and save both PO and Inventory data
        print("PO data refreshed from API.")
        insert_data_from_json(PURCHASE_ORDERS_FILE)  # Insert PO data
        print("PO data inserted into database.")
        insert_data_from_json(INVENTORY_FILE)  # Insert Inventory data
        print("Inventory data inserted into database.")

        refresh_PO_Response()
        page.dialog = ft.AlertDialog(title=ft.Text("✅ PO Data Refreshed Successfully!"))
        page.dialog.open = True

        # Reload the POs to show the new data
        pos_list = page.controls[0].controls[2]  # Assuming pos_list is the third control in the main view
        load_pos(page, pos_list)

        page.update()
    except Exception as e:
        print(f"An error occurred: {e}")
        page.dialog = ft.AlertDialog(title=ft.Text(f"❌ Error: {e}"))
        page.dialog.open = True
        page.update()
    finally:
        update_in_progress = False

### -----------------------------------
### 🔹 Show Materials for Selected PO
### -----------------------------------
def show_po_materials(page: ft.Page, po_number: str):
    """Displays materials for a selected PO and lists the bundles associated with it."""

    material_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    bundle_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    selected_bundle_details = ft.Column()
    selected_bundle_text = ft.Text("📦 Select a bundle to view details", size=18, weight=ft.FontWeight.BOLD)
    
    
    def load_materials():
        """Fetch materials for the selected PO."""
        material_list.controls.clear()

        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, material_name, innergy_sku, pallet_qty, updated_qty
                FROM Bulk_Storage_Rack_System
                WHERE po_number = ?;
            """, (po_number,))
            materials = cursor.fetchall()

        if not materials:
            material_list.controls.append(ft.Text("⚠️ No materials found for this PO."))
        else:
            for material in materials:
                material_id, material_name, sku, pallet_qty, updated_qty = material
                qty = updated_qty if updated_qty is not None else pallet_qty if pallet_qty is not None else 0  # Handle None values
                qty_input = ft.TextField(value=str(qty), width=50, text_align=ft.TextAlign.CENTER)

                def update_qty(e, m_id=material_id, input_field=qty_input):
                    """Update material quantity in the database."""
                    try:
                        new_qty = int(input_field.value)
                        with sqlite3.connect(db_name) as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE Bulk_Storage_Rack_System
                                SET updated_qty = ?
                                WHERE id = ?;
                            """, (new_qty, m_id))
                            conn.commit()
                    except ValueError:
                        input_field.value = str(qty)
                    page.update()

                qty_input.on_change = update_qty

                material_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(material_name, weight=ft.FontWeight.BOLD, expand=2),
                            ft.Text(f"SKU: {sku}", expand=1),
                            qty_input
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=ft.padding.all(10),
                        border=ft.border.all(1, "gray"),
                        border_radius=8,
                        ink=True
                    )
                )

        page.update()

    def load_bundle_details(barcode):
        """Fetch and display details of the selected bundle."""
        selected_bundle_details.controls.clear()
        selected_bundle_text.value = f"📦 Bundle Details: {barcode}"

        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT bs.material_name, bs.innergy_sku, bi.quantity
                FROM Bulk_Storage_Rack_System bs
                JOIN Bundle_Items bi ON bs.id = bi.material_id
                WHERE bi.bundle_id = ?;
            """, (barcode,))
            materials = cursor.fetchall()

        if not materials:
            selected_bundle_details.controls.append(ft.Text("⚠️ No materials found in this bundle."))
        else:
            for material_name, sku, qty in materials:
                selected_bundle_details.controls.append(
                    ft.Row([
                        ft.Text(material_name, weight=ft.FontWeight.BOLD, expand=2),
                        ft.Text(f"SKU: {sku}", expand=1),
                        ft.Text(f"Qty: {qty}", expand=1)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )

        page.update()

    def load_bundles(po_number):
        """Fetch only the bundles associated with the selected PO."""
        bundle_list.controls.clear()

        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT barcode, bin_name, date_received
                FROM Bundles
                WHERE po_number = ?;
            """, (po_number,))
            bundles = cursor.fetchall()

        if not bundles:
            bundle_list.controls.append(ft.Text("⚠️ No bundles found for this PO."))
        else:
            for barcode, bin_name, date_received in bundles:
                bundle_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"📦 {barcode}", weight=ft.FontWeight.BOLD, expand=2),
                            ft.Text(f"📍 {bin_name}", expand=1),
                            ft.Text(f"📅 {date_received if date_received else 'N/A'}", expand=1)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=ft.padding.all(10),
                        border=ft.border.all(1, "gray"),
                        border_radius=8,
                        ink=True,
                        on_click=lambda e, b=barcode: view_bundle_details(page, b, load_bundles)
                    )
                )

        page.update()

    def go_back(e):
        """Navigate back to the main page."""
        if page.views:
            page.views.pop()

        page.go("/po")  # ✅ Go back to main page
    


    def create_bundle(e):
        """Navigate to the create bundle page."""
        create_bundle_page(page, po_number, load_bundles)

    load_materials()
    load_bundles(po_number)

    materials_section = ft.Container(
        content=ft.Column([
            ft.Text(f"📦 Materials for PO {po_number}", size=22, weight=ft.FontWeight.BOLD),
            material_list
        ], expand=True),
        padding=ft.padding.all(10),
        expand=True
    )

    bundles_section = ft.Container(
        content=ft.Column([
            ft.Text("📦 Bundles Associated with This PO", size=20, weight=ft.FontWeight.BOLD),
            bundle_list,
            selected_bundle_text,
            selected_bundle_details
        ], expand=True),
        padding=ft.padding.all(10),
        expand=True
    )

    layout = ft.Row(
        [materials_section, ft.VerticalDivider(), bundles_section],
        expand=True
    )

    buttons_section = ft.Container(
        content=ft.Row(
            [
                ft.ElevatedButton("⬅️ Back", on_click=go_back),
                ft.ElevatedButton("➕ Create Bundle", on_click=create_bundle)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            expand=True
        ),
        padding=ft.padding.all(10),
        expand=False
    )

    page.views.append(ft.View(f"/po/{po_number}", [
        ft.Column(
            [layout, buttons_section],
            expand=True
        )
    ]))

    page.go(f"/po/{po_number}")



##########################
### 🔹 create bundles
def create_bundle_page(page: ft.Page, po_number: str, load_bundles):
    """Displays UI for creating a new bundle."""
    
    bin_name_input = ft.TextField(label="📍 Bin Name", expand=True)

    # ✅ Scrollable Material List
    material_selection = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    material_selection_container = ft.Container(
        content=ft.Column(
            [
                ft.Text("📦 Select Materials & Quantity", size=18, weight=ft.FontWeight.BOLD),
                material_selection  # ✅ This column is now scrollable
            ],
            expand=True
        ),
        expand=True,  # ✅ Allows it to fill the space
        border=ft.border.all(1, "gray"),
        border_radius=8,
        padding=ft.padding.all(10),
    )

    # ✅ Scrollable Bundles List
    bundle_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    bundle_list_container = ft.Container(
        content=ft.Column(
            [
                ft.Text("📦 Bundles Associated with This PO", size=18, weight=ft.FontWeight.BOLD),
                bundle_list  # ✅ This column is now scrollable
            ],
            expand=True
        ),
        expand=True,  # ✅ Allows it to fill the space
        border=ft.border.all(1, "gray"),
        border_radius=8,
        padding=ft.padding.all(10),
    )

    selected_materials = {}  # ✅ Stores selected quantities

    def load_materials():
        """Fetch available materials for the selected PO and update the UI to show total and available quantities."""
        material_selection.controls.clear()
        available_materials = get_available_materials(po_number)

        for material_id, details in available_materials.items():
            total_qty = details.get("total_qty", 0)  # Ensure total_qty is retrieved
            available_qty = details["available_qty"]

            qty_input = ft.TextField(
                value="0", width=50, text_align=ft.TextAlign.CENTER, keyboard_type=ft.KeyboardType.NUMBER
            )

            def update_selected_qty(e, m_id=material_id, input_field=qty_input):
                """Update selected material quantities when changed."""
                try:
                    qty = int(input_field.value)
                    if qty > available_qty:
                        input_field.value = str(available_qty)  # Prevent exceeding stock
                    elif qty < 0:
                        input_field.value = "0"  # Prevent negative values
                    selected_materials[m_id] = int(input_field.value)
                except ValueError:
                    input_field.value = "0"
                page.update()

            qty_input.on_change = update_selected_qty

            material_container = ft.Container(
                content=ft.Row([
                    ft.Text(details["name"], expand=2),
                    ft.Text(f"Total: {total_qty}", expand=1),  # ✅ Show total qty
                    ft.Text(f"Available: {available_qty}", expand=1),  # ✅ Show available qty
                    qty_input
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.padding.all(10),
                border=ft.border.all(1, "gray"),
                border_radius=8,
                ink=True,
                on_click=lambda e, input_field=qty_input: input_field.focus()
            )

            material_selection.controls.append(material_container)

        page.update()


    def load_bundles():
        """Fetch all bundles for the selected PO and update the UI."""
        bundle_list.controls.clear()

        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT barcode, bin_name, date_received
                FROM Bundles
                WHERE po_number = ?;
            """, (po_number,))
            bundles = cursor.fetchall()

        if not bundles:
            bundle_list.controls.append(ft.Text("⚠️ No bundles found for this PO."))
        else:
            for barcode, bin_name, date_received in bundles:
                bundle_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"📦 {barcode}", weight=ft.FontWeight.BOLD, expand=2),
                            ft.Text(f"📍 {bin_name}", expand=1),
                            ft.Text(f"📅 {date_received if date_received else 'N/A'}", expand=1)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=ft.padding.all(10),
                        border=ft.border.all(1, "gray"),
                        border_radius=8,
                        ink=True,
                        on_click=lambda e, b=barcode: view_bundle_details(page, b, load_bundles)
                    )
                )

        page.update()  # ✅ Ensure UI updates after loading bundles


    def submit_bundle(e):
        """Creates the bundle if conditions are met and resets quantities."""
        print("🔄 Create Bundle Button Clicked!")

        if not bin_name_input.value.strip():
            print("⚠️ No bin name entered!")
            page.dialog = ft.AlertDialog(title=ft.Text("⚠️ Enter a bin name!"))
            page.dialog.open = True
            page.update()
            return

        if not any(selected_materials.values()):
            print("⚠️ No materials selected!")
            page.dialog = ft.AlertDialog(title=ft.Text("⚠️ Select at least one material!"))
            page.dialog.open = True
            page.update()
            return

        print(f"📦 Creating bundle for PO {po_number} with materials: {selected_materials}")

        # ✅ Ensure foreign key check before proceeding
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON;")  # ✅ Enable foreign key enforcement
            
            # ✅ Check if po_number exists in Bulk_Storage_Rack_System
            cursor.execute("SELECT COUNT(*) FROM Bulk_Storage_Rack_System WHERE po_number = ?", (po_number,))
            exists = cursor.fetchone()[0]

        if exists == 0:
            print(f"⚠️ Error: PO {po_number} does not exist in Bulk_Storage_Rack_System!")
            page.dialog = ft.AlertDialog(title=ft.Text(f"⚠️ Error: PO {po_number} does not exist!"))
            page.dialog.open = True
            page.update()
            return  # ✅ Prevents bundle creation if PO is missing

        # ✅ If PO exists, proceed with bundle creation
        success = create_bundle(po_number, bin_name_input.value, selected_materials)

        if success:
            print("✅ Bundle Created Successfully!")
            dialog = ft.AlertDialog(title=ft.Text("✅ Bundle created successfully!"))  # ✅ Correct dialog usage
            page.dialog = dialog
            dialog.open = True

            # ✅ Refresh bundles after creation
            load_bundles()
            page.update()

            # ✅ Reset the input fields
            for control in material_selection.controls:
                if isinstance(control, ft.Container):
                    for item in control.content.controls:
                        if isinstance(item, ft.TextField):
                            item.value = "0"

            selected_materials.clear()  # ✅ Clear selected materials
            page.update()

        else:
            print("❌ Bundle Creation Failed!")
            dialog = ft.AlertDialog(title=ft.Text("❌ Bundle creation failed! Check console for errors."))  # ✅ Correct dialog usage
            page.dialog = dialog
            dialog.open = True
            page.update()

    def go_back(e):
        """Navigate back to the PO materials page."""
        if page.views:
            page.views.pop()  # ✅ Removes the current "Create Bundle" view
        page.go(f"/po/{po_number}")  # ✅ Navigates back to the PO page

    back_button = ft.ElevatedButton("⬅️ Back", on_click=go_back)

    # ✅ Load materials and bundles when the page opens
    load_materials()
    load_bundles()

    # **Page Layout**
    page.views.append(ft.View("/create_bundle", [
        ft.Text(f"➕ Create Bundle for PO {po_number}", size=22, weight=ft.FontWeight.BOLD),

        # ✅ Left: Bin Name Input
        ft.Row([bin_name_input], alignment=ft.MainAxisAlignment.START),

        # ✅ Center: Material Selection
        material_selection_container,

        # ✅ Right: Bundle List
        bundle_list_container,

        # ✅ Bottom: Action Buttons (Create & Back)
        ft.Row([ft.ElevatedButton("✅ Create Bundle", on_click=submit_bundle), back_button],
               alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    ]))

    page.go("/create_bundle")


def view_bundle_details(page: ft.Page, bundle_id, load_bundles):
    """Displays the materials inside a bundle and allows editing or deleting it."""
    updated_bundle = {}  # Stores updated material quantities in the bundle

    bundle_contents = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def go_back(e=None):
        """Navigate back to the Create Bundles page and refresh the bundle list."""
        if page.views:
            page.views.pop()  # ✅ Removes the current "Edit Bundle" screen
        
        load_bundles()  # ✅ Reload the updated bundle list
        page.update()  # ✅ Refresh the UI to show changes

        page.go("/create_bundle")  # ✅ Goes back to "Create Bundle" page

    def load_bundle_materials():
        """Fetch and display the materials inside the bundle."""
        bundle_contents.controls.clear()
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT bs.material_name, bi.quantity, bs.updated_qty
                FROM Bulk_Storage_Rack_System bs
                JOIN Bundle_Items bi ON bs.id = bi.material_id
                WHERE bi.bundle_id = ?;
            """, (bundle_id,))
            materials = cursor.fetchall()

        if not materials:
            bundle_contents.controls.append(ft.Text("⚠️ No materials found in this bundle."))
        else:
            for material_name, qty, updated_qty in materials:
                qty = updated_qty if updated_qty is not None else qty  # Use updated_qty if available
                qty_input = ft.TextField(value=str(qty), width=50, text_align=ft.TextAlign.CENTER)

                def update_bundle_qty(e, material_name=material_name, input_field=qty_input):
                    """Update the quantity of a material in the bundle."""
                    try:
                        new_qty = int(input_field.value)
                        if new_qty < 0:
                            input_field.value = "0"
                        updated_bundle[material_name] = new_qty
                    except ValueError:
                        input_field.value = str(qty)
                    page.update()

                qty_input.on_change = update_bundle_qty

                bundle_contents.controls.append(
                    ft.Row([
                        ft.Text(material_name, expand=2),
                        qty_input
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )

        page.update()

    def save_changes(e):
        """Update bundle materials in the database and refresh the UI."""
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        for material_name, new_qty in updated_bundle.items():
            # Fetch the current quantity in the bundle
            cursor.execute("""
                SELECT bi.quantity, bs.id
                FROM Bundle_Items bi
                JOIN Bulk_Storage_Rack_System bs ON bi.material_id = bs.id
                WHERE bi.bundle_id = ? AND bs.material_name = ?;
            """, (bundle_id, material_name))
            current_qty, material_id = cursor.fetchone()

            # Update the quantity in the bundle
            cursor.execute("""
                UPDATE Bundle_Items
                SET quantity = ?

                WHERE bundle_id = ? AND material_id = (
                    SELECT id FROM Bulk_Storage_Rack_System WHERE material_name = ? LIMIT 1
                );
            """, (new_qty, bundle_id, material_name))
            cursor.execute("""
                UPDATE Bulk_Storage_Rack_System
                SET updated_qty = ?
                WHERE material_name = ?;
            """, (new_qty, material_name))


        conn.commit()
        conn.close()

        # ✅ Show success message correctly
        dialog = ft.AlertDialog(title=ft.Text("✅ Bundle updated successfully!"))
        page.dialog = dialog
        dialog.open = True
        page.update()

        # ✅ Refresh UI and return to the Create Bundles page
        go_back()

    def delete_bundle(e):
        """Deletes a bundle, restores material availability, and removes the bundle record."""
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON;")  # ✅ Ensure foreign key enforcement

            # Step 1: Fetch all materials in the bundle
            cursor.execute("""
                SELECT material_id, quantity 
                FROM Bundle_Items 
                WHERE bundle_id = ?;
            """, (bundle_id,))
            bundle_items = cursor.fetchall()

            # Step 2: Restore material availability in Bulk_Storage_Rack_System
            for material_id, quantity in bundle_items:
                cursor.execute("""
                    UPDATE Bulk_Storage_Rack_System 
                    SET pallet_qty = pallet_qty + ?
                    WHERE id = ?;
                """, (quantity, material_id))

            # Step 3: Delete bundle items first to avoid foreign key errors
            cursor.execute("DELETE FROM Bundle_Items WHERE bundle_id = ?;", (bundle_id,))

            # Step 4: Delete the bundle itself
            cursor.execute("DELETE FROM Bundles WHERE barcode = ?;", (bundle_id,))

            conn.commit()

        print(f"✅ Bundle {bundle_id} deleted successfully, materials restored!")

        go_back()


    # ✅ Buttons for navigation and actions
    back_button = ft.ElevatedButton("⬅️ Back", on_click=go_back)
    save_button = ft.ElevatedButton("💾 Save Changes", on_click=save_changes)
    delete_button = ft.ElevatedButton("🗑️ Delete Bundle", on_click=lambda e: delete_bundle(bundle_id))


    # ✅ Ensure the buttons are inside the correct View
    page.views.append(ft.View(f"/bundle/{bundle_id}", [
        ft.Text(f"📦 Editing Bundle: {bundle_id}", size=22, weight=ft.FontWeight.BOLD),
        bundle_contents,
        ft.Row([
            save_button,
            delete_button,
            back_button
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
    ]))

    # ✅ Load the materials when the page opens
    load_bundle_materials()

    # ✅ Navigate to the edit bundle view
    page.go(f"/bundle/{bundle_id}")

### -----------------------------------
### 🔹 Load POs with "View Materials" Button
### -----------------------------------
def load_pos(page: ft.Page, pos_list: ft.Column):
    """Loads and displays all unreceived POs."""
    pos = get_unreceived_pos()
    pos_list.controls.clear()

    if not pos:
        pos_list.controls.append(ft.Text("No purchase orders found.", color="gray", size=16, italic=True))

    for po in pos:
        po_number = po[1]
        pos_list.controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Text(po_number, weight=ft.FontWeight.BOLD, expand=1),
                    ft.Text(po[2] if po[2] else "N/A", expand=2),
                    ft.ElevatedButton("View Materials", on_click=lambda e, po_num=po_number: show_po_materials(page, po_num))
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.padding.symmetric(vertical=5)
            )
        )

    page.update()

def show_bundles_page(page: ft.Page, po_number: str):

    """Displays all bundles with search functionality."""
    search_entry = ft.TextField(label="🔍 Search Barcode or Bin", expand=True)
    bundle_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def load_bundles(po_number):
        """Fetch all bundles for the selected PO."""
        bundle_list.controls.clear()

        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT barcode, bin_name, date_received
                FROM Bundles;
            """)
            bundles = cursor.fetchall()

        if not bundles:
            bundle_list.controls.append(ft.Text("⚠️ No bundles found."))
        else:
            for barcode, bin_name, date_received in bundles:
                bundle_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"📦 {barcode}", weight=ft.FontWeight.BOLD, expand=2),
                            ft.Text(f"📍 {bin_name}", expand=1),
                            ft.Text(f"📅 {date_received if date_received else 'N/A'}", expand=1)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=ft.padding.all(10),
                        border=ft.border.all(1, "gray"),
                        border_radius=8,
                        ink=True,
                        on_click=lambda e, b=barcode: view_bundle_details(page, b, load_bundles)
                    )
                )

        page.update()



    def search_bundles(e):
        """Filters bundles based on search input."""
        query = search_entry.value.strip().lower()
        bundle_list.controls.clear()

        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT barcode, bin_name, date_received FROM Bundles;")
            bundles = cursor.fetchall()

        for barcode, bin_name, date_received in bundles:
            if query in barcode.lower() or query in bin_name.lower():
                bundle_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"📦 {barcode}", weight=ft.FontWeight.BOLD, expand=2),
                            ft.Text(f"📍 {bin_name}", expand=1),
                            ft.Text(f"📅 {date_received if date_received else 'N/A'}", expand=1),
                        ]),
                        padding=ft.padding.all(10),
                        border=ft.border.all(1, "gray"),
                        border_radius=8
                    )
                )

        page.update()

    def go_back():
        """Navigate back to the main page."""
        if page.views:
            page.views.pop()  # Remove current view
        page.go("/po")  # Go back to main page

    search_button = ft.ElevatedButton("Search", on_click=search_bundles)
    back_button = ft.ElevatedButton("⬅️ Back", on_click=lambda e: go_back())

    load_bundles(po_number)


    page.views.append(ft.View("/bundles", [
        ft.Text("📦 All Bundles", size=22, weight=ft.FontWeight.BOLD),
        ft.Row([search_entry, search_button]),
        bundle_list,
        back_button
    ]))

    page.go("/bundles")

### -----------------------------------
### 🔹 Main App Entry with "View Bundles" Button
### -----------------------------------
def po_main_page(page: ft.Page, main_menu_navigation):
    """PO Management Page with Proper Back Button Functionality"""

    def go_back(e):
        """Navigate back to the main menu via the main routing logic."""
        page.go("/po")  # ✅ This triggers route_change defined in main.py



    def po_route_change(route):
        """Handles navigation to different pages dynamically"""

        # ✅ Prevent unnecessary reloads
        if page.views and page.views[-1].route == route:
            return  





        # ✅ Define a Back to Main Menu button
        main_menu_button = ft.ElevatedButton("🏠 Main Menu", on_click=lambda e: page.go("/po"))

        # if route == "/po":
        #     search_entry = ft.TextField(label="🔍 Search PO Number", expand=True)
        #     pos_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        #     load_pos(page, pos_list)

        #     # Define a back button that navigates to the main menu
        #     back_button = ft.ElevatedButton("⬅️ Back", on_click=lambda e: page.go("/"))
            
        #     page.views.append(ft.View("/po", [
        #         ft.Row([back_button], alignment=ft.MainAxisAlignment.START),  # Add the back button here
        #         ft.Text("📦 Warehouse PO Tracker", size=22, weight=ft.FontWeight.BOLD),
        #         ft.Row([search_entry, ft.ElevatedButton("Search", on_click=lambda e: search_po(e))]),
        #         pos_list
        #     ]))

        # if  route == "/po":
        #     po_number = route.split("/")[-1]
        #     page.views.append(ft.View(route, [
        #         ft.Row([main_menu_button], alignment=ft.MainAxisAlignment.START),
        #         show_po_materials(page, po_number)
        #     ]))


        if route == "/create_bundle/":
            po_number = route.split("/")[-1]
            page.views.append(ft.View(route, [
                ft.Row([main_menu_button], alignment=ft.MainAxisAlignment.START),
                create_bundle_page(page, po_number, lambda: show_bundles_page(page, po_number))
            ]))

        elif route == "/bundle/":
            bundle_id = route.split("/")[-1]
            page.views.append(ft.View(route, [
                ft.Row([main_menu_button], alignment=ft.MainAxisAlignment.START),
                view_bundle_details(page, bundle_id, lambda: show_bundles_page(page, bundle_id))
            ]))

        page.update()

    page.on_route_change = po_route_change
    po_route_change("/po")

    search_entry = ft.TextField(label="🔍 Search PO Number", expand=True)
    pos_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def search_po(e):
        """Filters PO numbers based on user input."""
        query = search_entry.value.strip().lower()
        pos_list.controls.clear()
        pos = get_unreceived_pos()

        for po in pos:
            po_number = po[1]
            if query in po_number.lower():
                pos_list.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(po_number, weight=ft.FontWeight.BOLD, expand=1),
                            ft.Text(po[2] if po[2] else "N/A", expand=2),
                            ft.ElevatedButton("View Materials", on_click=lambda e, po_num=po_number: show_po_materials(page, po_num))
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=ft.padding.symmetric(vertical=5)
                    )
                )
        page.update()

    search_button = ft.ElevatedButton("Search", on_click=search_po)
    view_bundles_button = ft.Container(
        content=ft.ElevatedButton(
            "📦 View All Bundles",
            on_click=lambda e: show_bundles_page(page, pos_list.controls[0].content.controls[0].value)  # Gets first PO number
        ),
        alignment=ft.alignment.top_right,  # Aligns to the top right
        padding=ft.padding.only(right=20, top=10)  # Adds spacing from edges
    )
    load_pos(page, pos_list)

    def main_menu_nav():
        """Navigate back to the main menu."""
        page.on_route_change = main_menu_navigation
        page.go("/")


    page.views.append(ft.View("/po", [
        ft.Row([
            ft.Text("📦 Warehouse PO Tracker", size=22, weight=ft.FontWeight.BOLD, expand=True),
            view_bundles_button,  # Places the button in the top right
            refresh_button  # Add the refresh button here
        ]),
        ft.Row([search_entry, search_button]),
        pos_list,
        ft.ElevatedButton("⬅️ Back", on_click=lambda e: main_menu_nav())
    ]))


    page.go("/po")