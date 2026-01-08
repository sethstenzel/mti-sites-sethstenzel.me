# sethstenzel.me

A full-stack portfolio website demonstrating modern Python web development practices, production deployment workflows, and DevOps capabilities.

## Technical Overview

This project showcases:

- **Python Web Framework**: Built with [NiceGUI](https://nicegui.io/), a modern Python web framework leveraging FastAPI and Vue.js for reactive UI components
- **Component-Based Architecture**: Modular page structure with reusable template components
- **Production Deployment**: systemd service management, nginx reverse proxy with WebSocket support, SSL/TLS encryption
- **CI/CD Pipeline**: GitHub webhook integration for automated deployments with release branch strategy
- **Cross-Platform Development**: Development environment configured for both Linux/Ubuntu and Windows

## Tech Stack

**Backend:**

- Python 3.13+
- NiceGUI (FastAPI + Vue.js)
- uvicorn ASGI server

**Frontend:**

- Vue.js (via NiceGUI)
- Tailwind CSS (via NiceGUI)
- Responsive design with custom components

**Infrastructure:**

- nginx reverse proxy with WebSocket support
- systemd service management
- Let's Encrypt SSL/TLS certificates
- Ubuntu VPS hosting

**Development Tools:**

- [uv](https://github.com/astral-sh/uv) - Modern Python package manager
- Git for version control
- FastAPI webhook listener for automated deployments

## Development Setup

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

**Linux/Ubuntu:**

```bash
git clone https://github.com/sethstenzel/mti-sites-sethstenzel.me.git
cd mti-sites-sethstenzel.me
uv venv
source .venv/bin/activate
uv pip install -e .
```

**Windows:**

```powershell
git clone https://github.com/sethstenzel/mti-sites-sethstenzel.me.git
cd mti-sites-sethstenzel.me
uv venv
.\.venv\Scripts\activate
uv pip install -e .
```

### Running Locally

```bash
# Development mode (auto-reload, opens browser)
cd ./src/mti_sites_sethstenzel.me
python -m mti_sites_sethstenzel_me.site --dev

# Production mode (runs on localhost:18001)
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
    ├── images/
    └── pages/           # Page content (JSON)
```

## Key Features

### Component-Based Architecture

The application uses a modular component structure with reusable templates:

- **Template System**: Shared UI components ([header.py](src/mti_sites_sethstenzel_me/pages/templates/header.py), [nav_bar.py](src/mti_sites_sethstenzel_me/pages/templates/nav_bar.py), [footer.py](src/mti_sites_sethstenzel_me/pages/templates/footer.py)) promote code reuse
- **Route Management**: Centralized routing in [routes.py](src/mti_sites_sethstenzel_me/routes.py) for clean URL structure
- **Page Components**: Individual page modules ([index.py](src/mti_sites_sethstenzel_me/pages/index.py), [portfolio.py](src/mti_sites_sethstenzel_me/pages/portfolio.py), [articles.py](src/mti_sites_sethstenzel_me/pages/articles.py), [contact.py](src/mti_sites_sethstenzel_me/pages/contact.py)) for separation of concerns

### Production Deployment

Demonstrates professional deployment practices:

- **Process Management**: systemd service configuration for automatic startup and crash recovery
- **Reverse Proxy**: nginx configuration with WebSocket support for real-time updates
- **SSL/TLS**: Automated certificate management with Let's Encrypt
- **Environment Configuration**: Environment-based port configuration for flexible deployment

### CI/CD Pipeline

Implemented GitHub webhook-based continuous deployment:

- **Release Branch Strategy**: Separate development and production branches
- **Automated Deployments**: Push-to-deploy workflow using FastAPI webhook listener
- **Zero-Downtime Updates**: Service restart automation via systemd
- **Security**: HMAC-SHA256 signature verification for webhook authentication

### Configuration Management

The application supports environment-based configuration:

```bash
# Port configuration via environment variable
export SETHSTENZEL_ME_PORT=18001
```

Default port: 18001

## Deployment

For detailed deployment instructions including server setup, nginx configuration, SSL certificates, and webhook automation, see [setup/deployment.md](setup/deployment.md).

## License

MIT