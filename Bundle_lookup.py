import flet as ft
import flet_webview as fw  # Import the new WebView package
import sqlite3
import threading
import http.server
import ssl
import socket
import time

db_name = "warehouse_data2.db"
SERVER_PORT = 8000  # Port for hosting the QR scanner
server_thread = None  # Store server thread

# Get the correct local IP address (NOT 127.0.0.1)
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
local_ip = s.getsockname()[0]
s.close()

def start_server():
    """Starts a local HTTPS web server for the QR scanner."""
    class QRScannerHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            return  # Suppress console logs

    handler = QRScannerHandler
    handler.directory = "."  # Serve files from the current directory

    httpd = http.server.HTTPServer(("0.0.0.0", SERVER_PORT), handler)

    # Wrap the server socket with SSL
    httpd.socket = ssl.wrap_socket(
        httpd.socket,
        keyfile="key.pem",  # Path to the private key file
        certfile="cert.pem",  # Path to the certificate file
        server_side=True
    )

    print(f"📡 Scanner available at: https://{local_ip}:{SERVER_PORT}/qr_scanner.html")
    httpd.serve_forever()

def stop_server():
    """Stops the web server by terminating its thread."""
    global server_thread
    if server_thread and server_thread.is_alive():
        server_thread._stop()
        print("🚫 Stopping QR scanner server...")

def bundle_lookup_page(page: ft.Page):
    """Page for scanning and looking up bundle details."""

    barcode_input = ft.TextField(label="📷 Scanned QR Code", read_only=True, expand=True)
    result_text = ft.Text(size=18, weight=ft.FontWeight.BOLD)
    bundle_contents = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    scanner_view = ft.Column([])  # Placeholder for WebView

    def lookup_bundle(qr_data):
        """Search for a bundle in the database using the scanned QR code."""
        barcode_input.value = qr_data  # Update UI with scanned code
        bundle_contents.controls.clear()

        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT barcode, po_number, bin_name, date_received
            FROM Bundles
            WHERE barcode = ?;
        """, (qr_data,))
        bundle = cursor.fetchone()

        if bundle:
            barcode, po_number, bin_name, date_received = bundle
            bundle_contents.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(
                            f"📦 Barcode: {barcode}\n"
                            f"📜 PO Number: {po_number}\n"
                            f"📍 Bin: {bin_name}\n"
                            f"📅 Date Received: {date_received if date_received else 'N/A'}",
                            weight=ft.FontWeight.BOLD
                        )
                    ]),
                    padding=ft.padding.all(10),
                    border=ft.border.all(1, "blue"),
                    border_radius=8,
                )
            )

            # Fetch materials in the bundle
            cursor.execute("""
                SELECT bs.material_name, bi.quantity
                FROM Bulk_Storage_Rack_System bs
                JOIN Bundle_Items bi ON bs.id = bi.material_id
                WHERE bi.bundle_id = ?;
            """, (qr_data,))
            materials = cursor.fetchall()

            if materials:
                for material_name, qty in materials:
                    bundle_contents.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Text(material_name, expand=2),
                                ft.Text(f"Qty: {qty}", expand=1)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            padding=ft.padding.all(5),
                            border=ft.border.all(1, "gray"),
                            border_radius=8,
                        )
                    )
            else:
                bundle_contents.controls.append(ft.Text("⚠️ No materials found in this bundle."))
        else:
            bundle_contents.controls.append(ft.Text(f"❌ Bundle '{qr_data}' not found!"))

        conn.close()
        stop_server()  # Stop the QR scanner server
        page.update()

    def start_web_qr_scanner(e):
        """Starts the QR scanner web server and displays it inside WebView."""
        global server_thread

        if not server_thread or not server_thread.is_alive():
            server_thread = threading.Thread(target=start_server, daemon=True)
            server_thread.start()
            time.sleep(1)  # Wait a second for the server to start

        scanner_url = "https://Bryce2048.github.io/qr-scanner/qr_scanner.html"

        # Print the scanner link in console for debugging
        print(f"✅ Scanner Ready! Open on iPhone: {scanner_url}")

        # Open the scanner inside Flet using WebView
        scanner_view.controls.clear()
        scanner_view.controls.append(
            ft.Container(
                content=fw.WebView(  # Use flet_webview.WebView
                    url=scanner_url,
                    enable_javascript=True,  # Ensure JavaScript works for QR scanning
                    expand=True
                ),
                expand=True,  # Ensure the container expands to fit available space
                height=600,  # Adjust height dynamically (set a value that fits)
                bgcolor="black",  # Optional: Match app background
                padding=ft.padding.all(10)
            )
        )
        page.update()

    def fallback_message(e):
        """Fallback message for unsupported platforms."""
        scanner_view.controls.clear()
        scanner_view.controls.append(
            ft.Text(
                "⚠️ QR Scanner is not supported on this platform. Please use a supported device (iOS, Android, macOS, or Web).",
                color="red",
                size=16,
                weight=ft.FontWeight.BOLD
            )
        )
        page.update()

    # Check if WebView is supported
    if hasattr(fw, "WebView"):
        start_scanner_button = ft.ElevatedButton("📷 Start QR Scanner", on_click=start_web_qr_scanner)
    else:
        start_scanner_button = ft.ElevatedButton("📷 Start QR Scanner", on_click=fallback_message)

    # Add the scanner_view to the page before updating it
    page.views.append(ft.View("/bundle_lookup", [
        ft.Text("🔍 Bundle Lookup", size=22, weight=ft.FontWeight.BOLD),
        barcode_input,
        start_scanner_button,
        scanner_view,  # Displays the embedded QR scanner or fallback message
        result_text,
        ft.Text("📦 Bundle Contents:", size=18, weight=ft.FontWeight.BOLD),
        bundle_contents,
        ft.ElevatedButton("⬅️ Back", on_click=lambda e: page.go("/"))
    ], scroll=ft.ScrollMode.AUTO))

    page.go("/bundle_lookup")
