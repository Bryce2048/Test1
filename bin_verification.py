import flet as ft
import sqlite3


db_name = "warehouse_data2.db"
stored_order = []
scan_queue = []  # ✅ Global queue for storing scanned barcodes


def get_all_bins():
    """Fetch all bin names from `Storage_Bins` and `Bundles`."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # ✅ Fetch all bin names from `Storage_Bins`
    cursor.execute("SELECT DISTINCT bin_name FROM Storage_Bins")
    bins_from_storage = {row[0] for row in cursor.fetchall()}  # Use a set to avoid duplicates

    # ✅ Fetch any additional bin names from `Bundles` that might not be in `Storage_Bins`
    cursor.execute("SELECT DISTINCT bin_name FROM Bundles WHERE bin_name IS NOT NULL")
    bins_from_bundles = {row[0] for row in cursor.fetchall()}

    # ✅ Merge bins from both tables
    all_bins = sorted(bins_from_storage.union(bins_from_bundles))

    conn.close()
    
    return all_bins if all_bins else ["No bins available"]


def get_bin_bundles(bin_name):
    """Fetches all bundles inside a bin, ordered by stack position."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # ✅ Query `Bundles` to get all bundles for a specific bin
    cursor.execute("""
        SELECT barcode, po_number, date_received, stack_position
        FROM Bundles
        WHERE LOWER(bin_name) = LOWER(?)
        ORDER BY stack_position ASC;
    """, (bin_name,))
    
    bundles = cursor.fetchall()
    conn.close()
    return bundles


def update_stack_positions(bin_name, ordered_barcodes):
    """Assign sequential stack positions to bundles in a specific bin."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # First, clear existing stack positions
    cursor.execute("""
        UPDATE Bundles SET stack_position = NULL WHERE LOWER(bin_name) = LOWER(?);
    """, (bin_name,))

    # Now assign sequential positions explicitly
    for position, barcode in enumerate(ordered_barcodes, start=1):
        cursor.execute("""
            UPDATE Bundles SET stack_position = ? 
            WHERE barcode = ? AND LOWER(bin_name) = LOWER(?);
        """, (position, barcode, bin_name))

    conn.commit()
    conn.close()



def move_bundle_to_bin(barcode, new_bin):
    """Moves a bundle to a different bin."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE Bundles
        SET bin_name = ?, stack_position = NULL
        WHERE barcode = ?;
    """, (new_bin, barcode))
    conn.commit()
    conn.close()

def bin_verification_page(page: ft.Page):
    """Page for selecting a bin and scanning bundles for verification."""
    bins = get_all_bins()
    
    if not bins:
        bins.append("No bins available")

    bin_dropdown = ft.Dropdown(
        label="Select a Bin",
        options=[ft.dropdown.Option(bin_name) for bin_name in bins],
        expand=True
    )

    scanned_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    confirmation_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)  # ✅ Section for messages

    def add_to_queue(e):
        """Extracts full barcodes from the text field and adds them to `scan_queue`."""
        global scan_queue

        scanned_text = scan_input.value.strip()
        if not scanned_text:
            return

        # ✅ Split input into separate barcode entries
        lines = [line.strip() for line in scanned_text.split("\n") if line.strip()]

        for barcode in lines:
            if barcode not in scan_queue:
                scan_queue.append(barcode)
                scanned_list.controls.append(ft.Text(f"📦 Queued: {barcode}"))

        scan_input.value = ""  # ✅ Clear input field
        scan_input.focus()
        page.update()

    # ✅ Now define `scan_input` AFTER `add_to_queue`
    scan_input = ft.TextField(
        label="📷 Scan Bundle Barcode",
        expand=True,
        autofocus=True,
        multiline=True,  
        max_lines=10,  
        keyboard_type=ft.KeyboardType.TEXT,
        on_submit=add_to_queue  # ✅ Now references `add_to_queue` correctly
    )

    def verify_all_scans(e):
        global scan_queue

        add_to_queue(e)  # Ensure all barcodes are stored before verifying

        bin_name = bin_dropdown.value
        if not bin_name:
            confirmation_list.controls.append(ft.Text("⚠️ No bin selected!", color="red"))
            page.update()
            return

        confirmation_list.controls.clear()
        updated_order = []

        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        # Verify and move bundles if necessary, then record new order
        for barcode in scan_queue:
            cursor.execute("SELECT bin_name FROM Bundles WHERE barcode = ?", (barcode,))
            result = cursor.fetchone()
            
            if result:
                actual_bin = result[0]
                if actual_bin == bin_name:
                    confirmation_list.controls.append(ft.Text(f"✅ {barcode} is in the correct bin!", color="green"))
                else:
                    confirmation_list.controls.append(ft.Text(f"⚠️ {barcode} moved from {actual_bin} to {bin_name}!", color="orange"))
                    move_bundle_to_bin(barcode, bin_name)
                updated_order.append(barcode)
            else:
                confirmation_list.controls.append(ft.Text(f"❌ {barcode} not found in database!", color="red"))

        # After confirming barcodes, update the stack positions sequentially
        for idx, barcode in enumerate(scan_queue, start=1):
            cursor.execute("""
                UPDATE Bundles SET stack_position = ? WHERE barcode = ?
            """, (idx, barcode))

        conn.commit()
        conn.close()

        confirmation_list.controls.append(ft.Text("✅ Stack positions updated successfully!", color="green"))

        scan_queue.clear()
        page.update()


    def load_bin_bundles(e):
        """Loads bundles in the selected bin for verification."""
        bin_name = bin_dropdown.value
        if not bin_name or bin_name == "No bins available":
            return

        global stored_order
        stored_order = get_bin_bundles(bin_name)

        scanned_list.controls.clear()
        confirmation_list.controls.clear()
        scan_queue.clear()

        if not stored_order:
            scanned_list.controls.append(ft.Text(f"🪣 {bin_name} is currently empty.", color="gray"))
        else:
            # If positions are None, set them immediately
            ordered_barcodes = [barcode for barcode, _, _, _ in stored_order]
            positions_missing = any(pos is None for _, _, _, pos in stored_order)
            
            if positions_missing:
                update_stack_positions(bin_name, ordered_barcodes)
                stored_order = get_bin_bundles(bin_name)  # Refresh after updating positions

            for barcode, po_number, date_received, stack_position in stored_order:
                position_text = stack_position if stack_position is not None else "Unassigned"
                scanned_list.controls.append(
                    ft.Text(f"📦 {barcode} | 📜 {po_number} | 📅 {date_received if date_received else 'N/A'} | 🔢 Pos: {position_text}")
                )

        page.update()


    verify_all_button = ft.ElevatedButton("✅ Verify All Scans", on_click=verify_all_scans)
    load_bin_button = ft.ElevatedButton("🔍 Load Bin", on_click=load_bin_bundles)
    back_button = ft.ElevatedButton("⬅️ Back", on_click=lambda e: page.go("/"))

    page.views.append(ft.View("/bin_verification", [
        ft.Text("📦 Bin Verification", size=22, weight=ft.FontWeight.BOLD),
        ft.Row([bin_dropdown, load_bin_button]),
        scanned_list,  # ✅ Now shows empty bins properly
        scan_input,
        verify_all_button,
        ft.Text("📢 Status Messages:", size=18, weight=ft.FontWeight.BOLD),
        confirmation_list,
        back_button
    ]))

    page.go("/bin_verification")


    def verify_all_scans(e):
        global scan_queue

        add_to_queue(e)  # Ensure barcodes are queued before verifying

        bin_name = bin_dropdown.value
        if not bin_name:
            confirmation_list.controls.append(ft.Text("⚠️ No bin selected!", color="red"))
            page.update()
            return

        confirmation_list.controls.clear()

        ordered_barcodes = []
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        for barcode in scan_queue:
            cursor.execute("SELECT bin_name FROM Bundles WHERE barcode = ?", (barcode,))
            result = cursor.fetchone()

            if result:
                actual_bin = result[0]
                if actual_bin.lower() == bin_name.lower():
                    confirmation_list.controls.append(ft.Text(f"✅ {barcode} is in the correct bin!", color="green"))
                else:
                    confirmation_list.controls.append(ft.Text(f"⚠️ {barcode} moved from {actual_bin} to {bin_name}!", color="orange"))
                    move_bundle_to_bin(barcode, bin_name)
                ordered_barcodes.append(barcode)
            else:
                confirmation_list.controls.append(ft.Text(f"❌ {barcode} not found in database!", color="red"))

        conn.close()

        if ordered_barcodes:
            update_stack_positions(bin_name, ordered_barcodes)
            confirmation_list.controls.append(ft.Text("✅ Stack positions updated successfully!", color="green"))

        scan_queue.clear()
        page.update()


    scan_input = ft.TextField(
        label="📷 Scan Bundle Barcode",
        expand=True,
        autofocus=True,
        multiline=True,  
        max_lines=10,  
        keyboard_type=ft.KeyboardType.TEXT,
        on_submit=add_to_queue
    )

    verify_all_button = ft.ElevatedButton("✅ Verify All Scans", on_click=verify_all_scans)
    load_bin_button = ft.ElevatedButton("🔍 Load Bin", on_click=load_bin_bundles)
    back_button = ft.ElevatedButton("⬅️ Back", on_click=lambda e: page.go("/"))

    page.views.append(ft.View("/bin_verification", [
        ft.Text("📦 Bin Verification", size=22, weight=ft.FontWeight.BOLD),
        ft.Row([bin_dropdown, load_bin_button]),
        scanned_list,  # ✅ Now shows empty bins properly
        scan_input,
        verify_all_button,
        ft.Text("📢 Status Messages:", size=18, weight=ft.FontWeight.BOLD),
        confirmation_list,
        back_button
    ]))

    page.go("/bin_verification")
