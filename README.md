# sethstenzel.me

Personal website built with [NiceGUI](https://nicegui.io/) - a Python-based web framework.

## Development Setup

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

**On Linux/Ubuntu:**
```bash
# Clone the repository
git clone https://github.com/sethstenzel/mti-sites-sethstenzel.me.git
cd mti-sites-sethstenzel.me

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e .
```

**On Windows:**
```powershell
# Clone the repository
git clone https://github.com/sethstenzel/mti-sites-sethstenzel.me.git
cd mti-sites-sethstenzel.me

# Create virtual environment and install dependencies
uv venv
.\.venv\Scripts\activate
uv pip install -e .
```

### Running Locally

```
# Development mode (auto-reload, opens browser)
cd ./src/mti_sites_sethstenzel.me
python -m mti_sites_sethstenzel_me.site --dev (or without argument)

# Production mode (runs on localhost:18001)
cd ./src/mti_sites_sethstenzel.me
python -m mti_sites_sethstenzel_me.site --prod
```

## Project Structure

```
src/mti_sites_sethstenzel_me/
├── site.py              # Application entry point
├── routes.py            # Route definitions
├── utils.py             # Utility functions
├── pages/               # Page components
│   ├── index.py
│   ├── portfolio.py
│   ├── articles.py
│   ├── contact.py
│   └── templates/       # Shared UI components
│       ├── center_card.py
│       ├── constants.py
│       ├── footer.py
│       ├── header.py
│       └── nav_bar.py
├── static/              # Static assets
│   ├── css/
│   ├── js/
│   └── imgs/
└── content/             # Content files
    ├── articles/
    ├── images/
    └── pages/           # Page content (JSON)
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions on deploying to an Ubuntu VPS with nginx, certbot, and HTTPS.

### Quick Deploy (Ubuntu VPS)

```bash
# On your VPS
./deploy.sh install    # First time setup
./deploy.sh update     # Update code and restart
./deploy.sh restart    # Quick restart
./deploy.sh logs       # View live logs
./deploy.sh status     # Check status
```

## Configuration

The application reads the `SETHSTENZEL_ME_PORT` environment variable for production deployment:

**Linux/Ubuntu:**
```bash
export SETHSTENZEL_ME_PORT=18001
python -m mti_sites_sethstenzel_me.site
```

**Windows:**
```powershell
$env:SETHSTENZEL_ME_PORT="18001"
python -m mti_sites_sethstenzel_me.site
```

Default port is 18001 if not specified.

## License

MIT