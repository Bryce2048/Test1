import flet as ft
from main_menu import main_menu
from Po_gui import po_main_page # Existing PO GUI
from bin_verification import bin_verification_page  # Import bin verification page
from print_bundle_labels import print_bundle_labels_page  # Import print bundle labels page
from bin_management import bin_management_page  # Import bin management page
from Bundle_lookup import bundle_lookup_page  # Import bundle lookup page

def main(page: ft.Page):
    """Main entry point for the warehouse tracking system."""
    page.theme_mode = ft.ThemeMode.DARK

    def route_change(route):
        page.views.clear()


        if page.route == "/":
            main_menu(page)

        elif page.route == "/po":
            po_main_page(page, route_change)  # Call Po_gui.main(page) to load PO view

        elif page.route == "/bins_management":
            bin_management_page(page)  # Load Bin Management page
        elif page.route == "/scan_bundle":
            page.views.append(ft.View("/scan_bundle", [ft.Text("QR Scanning Page - Work in Progress")]))
        elif page.route == "/bin_verification":
            bin_verification_page(page)  # Open Bin Verification Page
        elif page.route == "/print_labels":
            print_bundle_labels_page(page)
        elif page.route == "/bundle_lookup":
             bundle_lookup_page(page)
        page.update()

    page.on_route_change = route_change
    page.go("/")  # Default to main menu


ft.app(target=main, view=ft.WEB_BROWSER, port=8000)
