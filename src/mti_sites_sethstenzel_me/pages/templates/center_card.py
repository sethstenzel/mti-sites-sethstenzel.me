from nicegui import ui
def generate_center_card(header_content, main_content, footer_content, url=''):
    with ui.column().classes('w-full items-center'):
        with ui.card().classes('items-center main-content-card').style():
            header_content(url)
            ui.html("<hr>", sanitize=False).classes("sectioning-hr")
            main_content()
            footer_content()