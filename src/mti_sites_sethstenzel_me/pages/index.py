from loguru import logger
from nicegui import ui
from mti_sites_sethstenzel_me.utils import load_css, import_web_fonts
from mti_sites_sethstenzel_me.pages.templates.constants import *
from mti_sites_sethstenzel_me.pages.templates.nav_bar import nav_bar
from mti_sites_sethstenzel_me.pages.templates.header import generate_header
from mti_sites_sethstenzel_me.pages.templates.footer import generate_footer
from mti_sites_sethstenzel_me.pages.templates.center_card import generate_center_card
import json

page_url = '/'
page_content = {}
try:
    with open('./content/pages/index.json', 'r') as json_file:
            page_content = json.load(json_file)
except FileNotFoundError:
    logger.error("Index page content file not found: ./content/pages/index.json")

@ui.page(page_url)
def build_index_page():
    ui.add_head_html(import_web_fonts())
    ui.add_head_html('<link rel="stylesheet" href="/static/css/styles.css">')
    
    def main_conent():
        with ui.row().classes("card-inner-row card-inner-row-content"):
            with ui.grid(columns=2):
                with ui.column().classes("left-main-content"):
                    ui.label(page_content.get("left-content-text-1","?"))
                    ui.html("<br>", sanitize=False)
                    ui.label(page_content.get("left-content-text-2","?"))
                with ui.column().classes("right-main-content").style("justify-content: right;"):
                    with ui.grid(columns=2, rows=2):
                        right_content: dict = page_content.get("right-content",{})
                        if len(right_content.keys()):
                            with ui.label().classes("stat-card"):
                                ui.html(f"<span class='stat-card-large-text'>{right_content.get("tile-1",["",""])[0]}</span><span class='stat-card-small-text'>{right_content.get("tile-1",["",""])[1]}</span>", sanitize=False).classes("stat-card-blue")
                            with ui.label().classes("stat-card"):
                                ui.html(f"<span class='stat-card-large-text'>{right_content.get("tile-2",["",""])[0]}</span><span class='stat-card-small-text'>{right_content.get("tile-2",["",""])[1]}</span>", sanitize=False).classes("stat-card-white")
                            with ui.label().classes("stat-card"):
                                ui.html(f"<span class='stat-card-large-text'>{right_content.get("tile-3",["",""])[0]}</span><span class='stat-card-small-text'>{right_content.get("tile-3",["",""])[1]}</span>", sanitize=False).classes("stat-card-blue")
                            with ui.label().classes("stat-card"):
                                ui.html(f"<span class='stat-card-large-text'>{right_content.get("tile-4",["",""])[0]}</span><span class='stat-card-small-text'>{right_content.get("tile-4",["",""])[1]}</span>", sanitize=False).classes("stat-card-white")
        ui.html("<hr>", sanitize=False).classes("sectioning-hr")
        with ui.row().classes("card-inner-row-footer"):
            ui.label('In search of the fantastic, hidden in the everyday.')

    generate_center_card(generate_header, main_conent, generate_footer, url=page_url)



