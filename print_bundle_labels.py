import flet as ft
import sqlite3
import qrcode
import os
import platform
import win32print
import win32api
from reportlab.lib.pagesizes import landscape, inch
from reportlab.pdfgen import canvas

db_name = "warehouse_data2.db"
selected_printer = None  # Global variable to store selected printer

def get_all_bundles():
    """Fetches all bundles for printing labels."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT barcode, po_number, bin_name
        FROM Bundles;
    """)

    bundles = cursor.fetchall()
    conn.close()
    return bundles


def generate_qr_code(data, filename):
    """Generates and saves a QR code for the given data."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,

        box_size=15,
        border=0,
    )
    qr.add_data(data)
    qr.make(fit=True)
    

    img = qr.make_image(fill="black", back_color="white")
    img.save(filename)

def create_label_pdf(bundle):

    """Generates a 6"x4" printable label with a right-aligned QR code and a small margin to ensure full printing."""
    barcode, po_number, project_name, project_number, total_sheets, bundled_sheets = bundle
    pdf_filename = f"label_{barcode}.pdf"
    qr_filename = f"qr_{barcode}.png"

    # ✅ Generate High-Contrast QR Code with NO BORDER
    qr = qrcode.QRCode(
        version=3,  # Slightly larger QR grid for better resolution
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction
        box_size=15,  # Larger QR blocks for scanning at a distance
        border=0  # ❌ Remove extra white space around QR
    )
    qr.add_data(barcode)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white").convert('L')  # Ensure high contrast

    # ✅ Define label size (6 inches wide × 4 inches high)
    label_width = 6 * inch
    label_height = 4 * inch

    # ✅ Ensure QR code is a **perfect square** and fits with a margin from the right
    qr_size = label_height - 10  # QR code fills most of the height

    img = img.resize((int(qr_size), int(qr_size)))  # Maintain square aspect ratio
    img.save(qr_filename)

    # ✅ Create PDF Label in landscape mode
    c = canvas.Canvas(pdf_filename, pagesize=(label_width, label_height))

    # ✅ Adjust font size for readability
    c.setFont("Helvetica-Bold", 11)

    # ✅ Adjust text placement (shift left for better balance)
    text_x = 10  # Moves text further left
    text_y = label_height - 20
    line_spacing = 22  # Increased spacing between lines

    # ✅ Define max width for text wrapping (to prevent QR overlap)
    max_text_width = label_width - qr_size - 50  # Extra padding to ensure space

    # ✅ Function to wrap text into multiple lines
    def draw_wrapped_text(c, text, x, y, max_width):
        """Automatically wraps text to prevent overlap with the QR code."""
        lines = []
        words = text.split(" ")
        current_line = ""

        for word in words:
            test_line = current_line + " " + word if current_line else word
            if c.stringWidth(test_line, "Helvetica-Bold", 14) < max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word

        lines.append(current_line)  # Add last line

        for i, line in enumerate(lines):
            c.drawString(x, y - (i * line_spacing), line)

        return len(lines)  # Return number of lines used

    # ✅ Draw text with better alignment and spacing
    used_lines = draw_wrapped_text(c, f"📦 Bundle: {barcode}", text_x, text_y, max_text_width)
    text_y -= used_lines * line_spacing
    used_lines = draw_wrapped_text(c, f"📜 PO Number: {po_number}", text_x, text_y, max_text_width)
    text_y -= used_lines * line_spacing
    used_lines = draw_wrapped_text(c, f"🏗 Project: {project_name if project_name else 'N/A'}", text_x, text_y, max_text_width)
    text_y -= used_lines * line_spacing
    used_lines = draw_wrapped_text(c, f"🔢 Project #: {project_number if project_number else 'N/A'}", text_x, text_y, max_text_width)
    text_y -= used_lines * line_spacing
    c.drawString(text_x, text_y, f"📑 Sheets in Bundle: {bundled_sheets or 0} / {total_sheets or 0}")

    # ✅ QR Code Placement (flush right, **but with a small margin**)
    qr_margin = 10  # Adds a small margin from the right edge
    qr_x = label_width - qr_size - qr_margin  # Adjusted to leave a gap
    qr_y = 5  # Align to bottom

    # ✅ Draw QR Code (large square, with a small gap from the right edge)
    c.drawImage(qr_filename, qr_x, qr_y, width=qr_size, height=qr_size, mask='auto')


    c.save()
    print(f"✅ Label generated: {pdf_filename}")

    return pdf_filename



def get_all_bundles():
    """Fetches all bundles for printing labels, including project details and sheet count."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT b.barcode, b.po_number, bs.project_name, bs.project_number,
               (SELECT SUM(pallet_qty) FROM Bulk_Storage_Rack_System WHERE po_number = b.po_number) AS total_sheets,
               (SELECT SUM(quantity) FROM Bundle_Items WHERE bundle_id = b.barcode) AS bundled_sheets
        FROM Bundles b
        JOIN Bulk_Storage_Rack_System bs ON b.po_number = bs.po_number
    """)
    
    bundles = cursor.fetchall()
    conn.close()
    return bundles


def print_pdf(file_path, printer_name):
    """Prints the generated PDF label using the Windows Print Manager."""
    print(f"🖨 Sending {file_path} to printer: {printer_name}")
    if platform.system() == "Windows":
        try:
            win32print.SetDefaultPrinter(printer_name)  # Ensure the selected printer is used
            win32api.ShellExecute(0, "print", file_path, None, ".", 0)
        except Exception as e:
            print(f"❌ Printing failed: {e}")
    else:
        print("⚠️ Windows Print Manager is only available on Windows.")

def print_bundle_labels_page(page: ft.Page):
    """UI for selecting multiple bundles and printing labels."""
    global selected_printer
    bundles = get_all_bundles()


    if not bundles:
        page.dialog = ft.AlertDialog(title=ft.Text("⚠️ No bundles available for printing!"))
        page.dialog.open = True
        page.update()
        return

    checkboxes = []


    bundle_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    for bundle in bundles:
        checkbox = ft.Checkbox(label=f"{bundle[0]} - {bundle[1]} - {bundle[2]}")
        checkboxes.append(checkbox)
        bundle_list.controls.append(checkbox)

    printer_list = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)]
    printer_dropdown = ft.Dropdown(
        label="Select a Printer",
        options=[ft.dropdown.Option(p) for p in printer_list],
        value=selected_printer if selected_printer else printer_list[0]
    )

    def update_printer(e):
        """Updates the selected printer."""
        global selected_printer
        selected_printer = printer_dropdown.value.strip()
        print(f"🖨 Printer updated to: {selected_printer}")

    printer_dropdown.on_change = update_printer

    def print_labels(e):
        """Handles printing the selected labels."""
        global selected_printer
        selected_barcodes = [cb.label.split(" - ")[0] for cb in checkboxes if cb.value]
        printer_name = printer_dropdown.value.strip()

        print(f"📋 Selected bundles: {selected_barcodes}")
        print(f"🖨 Printer selected: {printer_name}")

        if not selected_barcodes:
            page.dialog = ft.AlertDialog(title=ft.Text("⚠️ Select at least one bundle!"))
            page.dialog.open = True
            page.update()
            return

        if not printer_name:
            page.dialog = ft.AlertDialog(title=ft.Text("⚠️ Select a printer!"))
            page.dialog.open = True
            page.update()
            return

        selected_printer = printer_name  # Store printer selection
        for barcode in selected_barcodes:
            selected_bundle = next((b for b in bundles if b[0] == barcode), None)
            if selected_bundle:
                pdf_file = create_label_pdf(selected_bundle)
                print_pdf(pdf_file, printer_name)  # Print using Windows Print Manager
            else:
                page.dialog = ft.AlertDialog(title=ft.Text(f"⚠️ Bundle {barcode} not found!"))
                page.dialog.open = True
        page.update()

    search_entry = ft.TextField(label="🔍 Search QR Labels", expand=True)

    def search_qr_labels(e):
        query = search_entry.value.strip().lower()
        filtered_bundles = [b for b in bundles if query in b[0].lower() or query in b[1].lower() or query in b[2].lower()]
        
        bundle_list.controls.clear()
        for bundle in filtered_bundles:
            checkbox = ft.Checkbox(label=f"{bundle[0]} - {bundle[1]} - {bundle[2]}")
            checkboxes.append(checkbox)
            bundle_list.controls.append(checkbox)
        
        page.update()

    search_entry.on_change = search_qr_labels

    page.views.append(ft.View("/print_labels", [
        ft.Text("🖨 Print QR Labels", size=22, weight=ft.FontWeight.BOLD),
        ft.Row([printer_dropdown]),
        ft.Row([search_entry]),
        bundle_list,
        ft.Row([ft.ElevatedButton("Print Selected Labels", on_click=print_labels)]),
        ft.Row([ft.ElevatedButton("⬅️ Back", on_click=lambda e: page.go("/")), ft.ElevatedButton("Print Selected Labels", on_click=print_labels)])
    ]))



    page.go("/print_labels")