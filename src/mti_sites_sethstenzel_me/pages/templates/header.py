from nicegui import ui
from mti_sites_sethstenzel_me.pages.templates.nav_bar import nav_bar

def generate_header(page_url=''):
    with ui.row().classes("card-inner-row"):
        with ui.grid(columns=2):
            with ui.column():
                ui.label('Seth Stenzel').classes('site-title')
                ui.label('A little software, a little hardware, and a little of me :)')
            with ui.column().classes('nav-bar-col'):
                nav_bar(page_url)
