import os
import sys
import argparse
from nicegui import ui, app
from loguru import logger
from mti_sites_sethstenzel_me.routes import build_routes

# Configure loguru for the application
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/sethstenzel-{time:YYYY-MM-DD}.log",
    rotation="00:00",  # Rotate at midnight
    retention="30 days",  # Keep logs for 30 days
    compression="zip",  # Compress old logs
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG"
)

SITE_URL = 'sethstenzel.me'

logger.info(f"Starting {SITE_URL} hosting application")
build_routes()
logger.debug("Routes built successfully")

if __name__ in {"__main__", "__mp_main__"}:
    parser = argparse.ArgumentParser(description='Run the sethstenzel.me site')
    parser.add_argument('--dev', action='store_true', help='Run in development mode')
    parser.add_argument('--prod', action='store_true', help='Run in production mode')
    args = parser.parse_args()

    logger.info("Adding static file routes")
    app.add_static_files('/static', 'static')
    app.add_static_files('/content', 'content')
    logger.debug("Static file routes added: /static, /content")

    # Set default column styles
    ui.column.default_style('padding: unset; margin: unset; gap: unset;')

    if args.prod:
        # Production configuration
        port = int(os.environ.get('SETHSTENZEL.ME_PORT', 18001))
        logger.info(f"Starting in PRODUCTION mode")
        logger.info(f"Host: 127.0.0.1 (localhost only - nginx proxied)")
        logger.info(f"Port: {port}")
        logger.info(f"Auto-reload: Disabled")
        logger.info(f"Browser auto-open: Disabled")

        ui.run(
            host='127.0.0.1',  # Only listen locally, nginx will proxy
            port=port,
            reload=False,  # Disable auto-reload in production
            show=False,  # Don't open browser
            title='sethstenzel.me',
            favicon='🌐'
        )
    else:
        # Development mode: auto-reload, open browser, default settings
        logger.info(f"Starting in DEVELOPMENT mode")
        logger.info(f"Port: 18001")
        logger.info(f"Auto-reload: Enabled")
        logger.info(f"Browser auto-open: Enabled")
        logger.info(f"Watching: *.py, *.css, *.js, *.ts, *.json")

        ui.run(
            port=18001,
            title='sethstenzel.me',
            favicon='r ',
            uvicorn_reload_includes="*.py, *.css, *.js, *.ts, *.json"
        )