import flet as ft
import sqlite3
import qrcode
import os
import platform
import win32print
import win32api
from reportlab.lib.pagesizes import landscape, inch
from reportlab.pdfgen import canvas
from datetime import datetime


DB_NAME = "warehouse_data2.db"
selected_printer = None  # Global variable to store selected printer

# Database interactions

def get_bins():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT bin_name, barcode FROM Storage_Bins;")
        return cursor.fetchall()

def get_bin_contents(bin_name):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT material_name, pallet_qty FROM Bulk_Storage_Rack_System WHERE current_bin = ?", (bin_name,))
        return cursor.fetchall()

def add_bin(bin_name):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        barcode = f"BIN-{len(get_bins()) + 1:03d}"
        cursor.execute("INSERT INTO Storage_Bins (bin_name, barcode) VALUES (?, ?)", (bin_name, barcode))
        conn.commit()

def edit_bin(old_name, new_name):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Storage_Bins SET bin_name = ? WHERE bin_name = ?", (new_name, old_name))
        conn.commit()

def remove_bin(bin_name):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Storage_Bins WHERE bin_name = ?", (bin_name,))
        conn.commit()

# QR Code and PDF Label Generation
def generate_qr_code(barcode, filename):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(barcode)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    img.save(filename)

def create_label_pdf(bin_name, barcode):
    pdf_filename = f"label_{barcode}.pdf"
    qr_filename = f"qr_{barcode}.png"

    generate_qr_code(barcode, qr_filename)

    from reportlab.lib.pagesizes import landscape, inch
    from reportlab.pdfgen import canvas

    label_width = 4 * inch
    label_height = 3 * inch

    c = canvas.Canvas(pdf_filename, pagesize=landscape((label_width := 4 * inch, label_height)))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20, label_height - 20, f"📦 Bin: {bin_name}")
    c.drawString(20, label_height - 40, f"🔢 Barcode: {barcode}")
    c.drawImage(qr_filename, label_width - 140, label_height - 100, width=100, height=100)
    c.save()

    os.remove(qr_filename)

    return pdf_filename

# Automatic PDF Printing
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

def print_bin_label(page, bin_name, barcode):
    global selected_printer

    def update_printer(e):
        """Updates the selected printer."""
        global selected_printer
        selected_printer = printer_dropdown.value.strip()
        print(f"🖨 Printer updated to: {selected_printer}")

    def handle_close(e):
        page.close(edit_dialog)
    
    def print(e):
        pdf_file = create_label_pdf(bin_name, barcode)
        print_pdf(pdf_file, selected_printer)

    printer_list = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)]
    printer_dropdown = ft.Dropdown(
        label="Select Printer",
        options=[ft.dropdown.Option(p) for p in printer_list],
        value=selected_printer if selected_printer else printer_list[0]
    )
    printer_dropdown.on_change = update_printer

    edit_dialog = ft.AlertDialog(
        title=ft.Text("Print Bin Label"),
        content=ft.Column([
            ft.Text("Print label for bin: " + bin_name),
            printer_dropdown
        ]),
        actions=[
            ft.TextButton("Cancel", on_click=handle_close),
            ft.TextButton("Print", on_click=print),
        ]
    )
    page.open(edit_dialog)

    # pdf_file = create_label_pdf(bin_name, barcode)
    # print_pdf(pdf_file)

# Main UI
def bin_management_page(page: ft.Page):
    bin_list = ft.Column(scroll=True, expand=True)
    bin_content_list = ft.Column(scroll=True, expand=True)
    bin_name_input = ft.TextField(label="New Bin Name", expand=True)
    edit_bin_name_input = ft.TextField(label="Edit Bin Name", expand=True)

    def load_bins():
        bin_list.controls.clear()
        bins = get_bins()
        for bin_name, barcode in bins:
            bin_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(f"{bin_name} ({barcode})", expand=2),
                        ft.ElevatedButton("View Contents", on_click=lambda e, b=bin_name: show_bin_contents(b)),
                        ft.ElevatedButton("Edit", on_click=lambda e, b=bin_name: edit_bin_ui(b)),
                        ft.ElevatedButton("Remove", on_click=lambda e, b=bin_name: remove_bin_ui(b)),
                        ft.ElevatedButton("Print Label", on_click=lambda e, p=page, b=bin_name, c=barcode: print_bin_label(p, b, c))
                    ]),
                    padding=ft.padding.all(10),
                    border=ft.border.all(1, "gray"),
                    border_radius=8,
                    ink=True
                )
            )
        page.update()

    def create_bin(e):
        add_bin(bin_name_input.value)
        bin_name_input.value = ""
        load_bins()

    def edit_bin_ui(old_name):
        def handle_close(e):
            page.close(edit_dialog)
        
        def save_changes(e):
            if new_bin_name_entry.value != "":
                new_name = new_bin_name_entry.value
                edit_bin(old_name, new_name)
                load_bins()
                page.close(edit_dialog)

        new_bin_name_entry = ft.TextField(label="New Bin Name", expand=True)

        edit_dialog = ft.AlertDialog(
            title=ft.Text("Edit Bin"),
            content=ft.Column([
                ft.Text("Current Bin Name: " + str(old_name)), 
                new_bin_name_entry
            ]),
            actions=[
                ft.TextButton("Cancel", on_click=handle_close),
                ft.TextButton("Save", on_click=save_changes),
            ]
        )
        page.open(edit_dialog)
        # new_name = edit_bin_name_input.value
        # edit_bin(old_name, new_name)
        # load_bins()

    def remove_bin_ui(bin_name):
        remove_bin(bin_name)
        load_bins()

    def show_bin_contents(bin_name):
        bin_content_list.controls.clear()
        contents = get_bin_contents(bin_name)
        if not contents:
            bin_content_list.controls.append(ft.Text("⚠️ No materials in this bin."))
        else:
            for material, qty in contents:
                bin_content_list.controls.append(ft.Text(f"{material}: {qty}"))
        page.update()

    page.views.append(ft.View("/bins_management", [
        ft.Text("📦 Bin Management", size=22, weight=ft.FontWeight.BOLD),
        ft.Row([bin_name_input, ft.ElevatedButton("Add Bin", on_click=create_bin)]),
        ft.Container(content=bin_list, expand=True),
        ft.Text("📦 Bin Contents", size=18, weight=ft.FontWeight.BOLD),
        ft.Container(content=bin_content_list, expand=True),
        ft.ElevatedButton("⬅️ Back", on_click=lambda e: page.go("/"))
    ]))

    load_bins()

    page.go("/bins_management")
