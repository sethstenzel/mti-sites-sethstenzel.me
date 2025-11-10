import os
import argparse
from nicegui import ui, app
from mti_sites_sethstenzel_me.routes import build_routes

SITE_URL = 'sethstenzel.me'

build_routes()

if __name__ in {"__main__", "__mp_main__"}:
    parser = argparse.ArgumentParser(description='Run the sethstenzel.me site')
    parser.add_argument('--dev', action='store_true', help='Run in development mode')
    parser.add_argument('--prod', action='store_true', help='Run in production mode')
    args = parser.parse_args()

    app.add_static_files('/static', 'static')
    app.add_static_files('/content', 'content') 

    if args.prod:
        # Production configuration
        ui.run(
            host='127.0.0.1',  # Only listen locally, nginx will proxy
            port=int(os.environ.get('SETHSTENZEL.ME_PORT', 18001)),  # Default port 8001, configurable via env var
            reload=False,  # Disable auto-reload in production
            show=False,  # Don't open browser
            title='sethstenzel.me',
            favicon='🌐'  # Optional: customize
        )
    else:
        # Development mode: auto-reload, open browser, default settings
        ui.run(port=18001,
        title='sethstenzel.me',
        favicon='r ',  # Optional: customize
        uvicorn_reload_includes = "*.py, *.css, *.js, *.ts, *.json"
        )

                
    ui.column.default_style('padding: unset; margin: unset; gap: unset;')