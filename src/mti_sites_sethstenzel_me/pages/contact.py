from nicegui import ui
from mti_sites_sethstenzel_me.utils import load_css, import_web_fonts
from mti_sites_sethstenzel_me.pages.templates.constants import *
from mti_sites_sethstenzel_me.pages.templates.header import generate_header
from mti_sites_sethstenzel_me.pages.templates.footer import generate_footer
from mti_sites_sethstenzel_me.pages.templates.center_card import generate_center_card

page_url = '/contact'

@ui.page(page_url)
def build_contact_page():
    ui.add_head_html(import_web_fonts())
    ui.add_head_html('<link rel="stylesheet" href="/static/css/styles.css">')
    
    def main_conent():
        with ui.row().classes("card-inner-row card-inner-row-content"):
            ui.label('UPPER CONTENT')
        with ui.row().classes("card-inner-row-footer"):
            ui.label('In search of the fantastic, hidden in the everyday.')

    generate_center_card(generate_header, main_conent, generate_footer, url=page_url)