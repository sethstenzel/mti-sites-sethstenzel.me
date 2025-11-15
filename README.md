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

### Auto-Deployment with GitHub Webhooks

Set up automatic deployments triggered by GitHub push events. This setup uses a **release branch strategy** for production safety:

- **`main` branch** - Active development (does NOT auto-deploy)
- **`release` branch** - Production deployment (auto-deploys on push)

When you merge `main` to `release` and push, your server automatically pulls changes and restarts the service.

See [WEBHOOK_SETUP.md](WEBHOOK_SETUP.md) for complete setup instructions and release branch workflow.

**Quick Setup:**
1. Install FastAPI & uvicorn: `uv pip install -e .`
2. Generate webhook secret: `python3 -c "import secrets; print(secrets.token_hex(32))"`
3. Configure and start webhook listener service
4. Update nginx configuration with webhook endpoint
5. Add webhook in GitHub repository settings
6. Create `release` branch: `git checkout -b release && git push origin release`

**Deployment Workflow:**
```bash
# Develop on main (does NOT deploy)
git checkout main
git add .
git commit -m "Add feature"
git push origin main

# Deploy to production (merge to release)
git checkout release
git merge main
git push origin release  # Auto-deploys!
```

**Files:**
- `webhook_listener.py` - FastAPI webhook listener (with auto-generated API docs)
- `webhook-listener.service` - systemd service file (runs with uvicorn)
- `webhook-nginx.conf` - nginx configuration snippet
- `WEBHOOK_SETUP.md` - Complete setup guide with workflow details

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