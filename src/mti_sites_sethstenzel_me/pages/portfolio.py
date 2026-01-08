from nicegui import ui
from mti_sites_sethstenzel_me.utils import load_css, import_web_fonts
from mti_sites_sethstenzel_me.pages.templates.constants import DARK_BLUE
from mti_sites_sethstenzel_me.pages.templates.header import generate_header
from mti_sites_sethstenzel_me.pages.templates.footer import generate_footer
from mti_sites_sethstenzel_me.pages.templates.center_card import generate_center_card
import json
from pathlib import Path

page_url = '/portfolio'

@ui.page(page_url)
def build_portfolio_page():
    ui.add_head_html(import_web_fonts())
    ui.add_head_html('<link rel="stylesheet" href="/static/css/styles.css">')

    def main_content():
        # Load portfolio data
        portfolio_path = Path(__file__).parent.parent / 'content' / 'pages' / 'portfolio.json'
        with open(portfolio_path, 'r') as f:
            projects = json.load(f)

        with ui.element('div').classes("card-inner-row-content w-full px-4"):
            # Responsive grid: 1 column on mobile, 2 on tablet, 3 on desktop
            with ui.element('div').classes('grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 w-full'):
                for project in projects:
                    create_project_card(project)

        with ui.row().classes("card-inner-row-footer"):
            ui.label('In search of the fantastic, hidden in the everyday.')

    generate_center_card(generate_header, main_content, generate_footer, url=page_url)


def create_project_card(project: dict):
    """Create a card for a single portfolio project."""
    with ui.card().classes('w-full'):
        # Project title
        ui.label(project['project_name']).classes('text-xl font-bold mb-2')

        # Main image - clickable if project_clicked_link exists
        if project.get('project_image_main'):
            if project.get('project_clicked_link'):
                with ui.link(target=project['project_clicked_link'], new_tab=True).classes('w-full'):
                    ui.image(project['project_image_main']).classes('w-full rounded cursor-pointer')
            else:
                ui.image(project['project_image_main']).classes('w-full rounded')

        # Links row directly under image
        with ui.row().classes('w-full justify-start gap-2 items-center mt-2'):
            # GitHub link (optional)
            if project.get('project_github_link'):
                with ui.link(target=project['project_github_link'], new_tab=True):
                    ui.image('/static/imgs/gh.png').style('width: 32px; height: 32px;')

            # YouTube link (optional)
            if project.get('project_youtube_link'):
                with ui.link(target=project['project_youtube_link'], new_tab=True):
                    ui.image('/static/imgs/yt.svg').style('width: 32px; height: 32px;')

            # Website link (optional)
            if project.get('project_website_link'):
                with ui.link(target=project['project_website_link'], new_tab=True):
                    ui.icon('language', size='md').style('color: #1d6096')

            # Download link (optional)
            if project.get('project_download_link'):
                with ui.link(target=project['project_download_link'], new_tab=True):
                    ui.icon('download', size='md').style('color: #228B22')

        # Project description
        ui.html(project['project_text'], sanitize=False).classes('mt-2 mb-4')