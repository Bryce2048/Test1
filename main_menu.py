import flet as ft

def main_menu(page: ft.Page):
    """Main menu for navigating the warehouse system."""

    def go_to_po_page(_):
        """Navigate to the PO page."""
        page.go("/po")

    def go_to_bins_page(_):
        """Navigate to the Bin Management page."""
        page.go("/bins_management")

    def start_scanning(_):
        """Navigate to the QR scanner to move bundles."""
        page.go("/scan_bundle")

    def go_to_bin_verification(_):
        """Navigate to the Bin Verification page."""
        page.go("/bin_verification")

    def go_to_print_labels(_):
        """Navigate to the QR Label Printing page."""
        page.go("/print_labels")

    def go_to_bundle_lookup(_):
        """Navigate to the Bundle Lookup page."""
        page.go("/bundle_lookup")

    # Add the new button for Bin Management
    page.views.append(ft.View("/", [
        ft.Container(
            content=ft.Text("📦 Warehouse Management System", size=20, weight=ft.FontWeight.BOLD),
            alignment=ft.alignment.center,
            padding=ft.padding.all(20),
        ),
        ft.Column(
            [
                ft.Container(
                    content=ft.ElevatedButton("📦 View Purchase Orders", on_click=go_to_po_page, width=250, height=60),
                    alignment=ft.alignment.center,
                    padding=ft.padding.all(10)
                ),
                ft.Container(
                    content=ft.ElevatedButton("🗄️ Bin Management", on_click=go_to_bins_page, width=250, height=60),
                    alignment=ft.alignment.center,
                    padding=ft.padding.all(10)
                ),
                ft.Container(
                    content=ft.ElevatedButton("📷 Scan QR Code to Move Bundle", on_click=start_scanning, width=250, height=60),
                    alignment=ft.alignment.center,
                    padding=ft.padding.all(10)
                ),
                ft.Container(
                    content=ft.ElevatedButton("🔍 Verify Bin Contents", on_click=go_to_bin_verification, width=250, height=60),
                    alignment=ft.alignment.center,
                    padding=ft.padding.all(10)
                ),
                ft.Container(
                    content=ft.ElevatedButton("🖨️ Print Labels", on_click=go_to_print_labels, width=250, height=60),
                    alignment=ft.alignment.center,
                    padding=ft.padding.all(10)
                ),
                ft.Container(
                    content=ft.ElevatedButton("🔍 Bundle Lookup", on_click=go_to_bundle_lookup, width=250, height=60),
                    alignment=ft.alignment.center,
                    padding=ft.padding.all(10)
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO  # Make the column scrollable
            
        )
    ]))


    page.go("/")