#!/bin/bash
# Deployment script for sethstenzel.me on Ubuntu
# Run this on your Ubuntu VPS

set -e  # Exit on error

APP_NAME="sethstenzel-site"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$APP_DIR/.venv"
PYTHON_BIN="$VENV_PATH/bin/python"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
PORT="${SETHSTENZEL_ME_PORT:-18001}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

function print_green() {
    echo -e "${GREEN}$1${NC}"
}

function print_yellow() {
    echo -e "${YELLOW}$1${NC}"
}

function print_cyan() {
    echo -e "${CYAN}$1${NC}"
}

function print_red() {
    echo -e "${RED}$1${NC}"
}

function install_service() {
    print_cyan "Installing service '$APP_NAME'..."

    # Create logs directory
    mkdir -p "$APP_DIR/logs"

    # Create systemd service file
    print_yellow "Creating systemd service file..."
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Seth Stenzel NiceGUI Site
After=network.target

[Service]
Type=simple
User=appsuser
Group=appsuser
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_PATH/bin"
Environment="SETHSTENZEL_ME_PORT=$PORT"
ExecStart=$PYTHON_BIN -m mti_sites_sethstenzel_me.site
Restart=always
RestartSec=10

# Logging
StandardOutput=append:$APP_DIR/logs/stdout.log
StandardError=append:$APP_DIR/logs/stderr.log

[Install]
WantedBy=multi-user.target
EOF

    # Set proper permissions
    print_yellow "Setting permissions..."
    sudo chown -R appsuser:appsuser "$APP_DIR"

    # Reload systemd
    print_yellow "Reloading systemd daemon..."
    sudo systemctl daemon-reload

    # Enable service
    print_yellow "Enabling service to start on boot..."
    sudo systemctl enable "$APP_NAME"

    # Start service
    print_yellow "Starting service..."
    sudo systemctl start "$APP_NAME"

    # Wait a moment
    sleep 2

    print_green "\nService installed and started!"
    print_cyan "\nService Status:"
    sudo systemctl status "$APP_NAME" --no-pager || true

    print_cyan "\nUseful commands:"
    echo "  sudo systemctl start $APP_NAME"
    echo "  sudo systemctl stop $APP_NAME"
    echo "  sudo systemctl restart $APP_NAME"
    echo "  sudo systemctl status $APP_NAME"
    echo "  sudo journalctl -u $APP_NAME -f"
}

function update_application() {
    print_cyan "Updating application..."

    # Pull latest changes
    print_yellow "Pulling from git..."

    # Get current branch
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

    # Discard all local changes first (before fetching)
    print_yellow "Discarding any local changes..."
    git reset --hard HEAD
    git clean -fd

    # Fetch latest changes
    git fetch origin

    # Reset to remote branch
    print_yellow "Resetting to origin/$CURRENT_BRANCH..."
    git reset --hard "origin/$CURRENT_BRANCH"

    # Update dependencies
    print_yellow "Updating dependencies..."
    source "$VENV_PATH/bin/activate"

    # Use uv if available, otherwise fall back to pip
    if command -v uv &> /dev/null; then
        print_yellow "Using uv from PATH..."
        uv pip install -e .
    elif [ -x "$HOME/.local/bin/uv" ]; then
        print_yellow "Using uv from ~/.local/bin..."
        "$HOME/.local/bin/uv" pip install -e .
    elif [ -x "$HOME/.cargo/bin/uv" ]; then
        print_yellow "Using uv from ~/.cargo/bin..."
        "$HOME/.cargo/bin/uv" pip install -e .
    elif [ -x "/usr/local/bin/uv" ]; then
        print_yellow "Using uv from /usr/local/bin..."
        /usr/local/bin/uv pip install -e .
    else
        print_yellow "uv not found, using pip instead..."
        pip install -e .
    fi

    print_green "Update complete!"
}

function restart_service() {
    print_cyan "Restarting service '$APP_NAME'..."

    # Try to restart the service
    if sudo systemctl restart "$APP_NAME" 2>/dev/null; then
        print_green "Service restarted successfully!"
    else
        print_yellow "Unable to restart service via sudo (this is expected in webhook context)"
        print_yellow "The service will need to be restarted manually or via a separate mechanism"
        print_yellow "Run: sudo systemctl restart $APP_NAME"
        return 0  # Don't fail the deployment
    fi

    # Wait a moment
    sleep 2

    print_cyan "\nService Status:"
    sudo systemctl status "$APP_NAME" --no-pager 2>/dev/null || echo "Cannot check status (permission denied)"

    print_cyan "\nRecent logs:"
    if [ -f "$APP_DIR/logs/stdout.log" ]; then
        tail -20 "$APP_DIR/logs/stdout.log"
    fi
}

function view_logs() {
    print_cyan "Viewing logs for '$APP_NAME'..."
    echo "Press Ctrl+C to exit"
    echo ""
    sudo journalctl -u "$APP_NAME" -f
}

function view_status() {
    print_cyan "Service Status:"
    sudo systemctl status "$APP_NAME" --no-pager || true

    print_cyan "\nPort Status:"
    sudo netstat -tlnp 2>/dev/null | grep ":$PORT" || sudo ss -tlnp | grep ":$PORT" || echo "Not listening on port $PORT"

    print_cyan "\nRecent logs (stdout):"
    if [ -f "$APP_DIR/logs/stdout.log" ]; then
        tail -20 "$APP_DIR/logs/stdout.log"
    else
        echo "No logs found"
    fi

    print_cyan "\nRecent errors (stderr):"
    if [ -f "$APP_DIR/logs/stderr.log" ]; then
        tail -20 "$APP_DIR/logs/stderr.log"
    else
        echo "No error logs found"
    fi
}

function uninstall_service() {
    print_yellow "Uninstalling service '$APP_NAME'..."

    # Stop service
    sudo systemctl stop "$APP_NAME" || true

    # Disable service
    sudo systemctl disable "$APP_NAME" || true

    # Remove service file
    sudo rm -f "$SERVICE_FILE"

    # Reload systemd
    sudo systemctl daemon-reload

    print_green "Service uninstalled!"
}

function show_help() {
    cat <<EOF
${CYAN}Deployment Script for sethstenzel.me${NC}

${YELLOW}Usage:${NC}
    $0 [COMMAND]

${YELLOW}Commands:${NC}
    install         Install and start as systemd service
    update          Update code from git and restart service
    restart         Restart the service
    logs            View live logs (journalctl)
    status          Show service status and recent logs
    uninstall       Stop and remove the service
    help            Show this help message

${YELLOW}Examples:${NC}
    # First time setup
    $0 install

    # After code changes
    $0 update

    # Just restart
    $0 restart

    # View logs
    $0 logs

${YELLOW}Manual systemd commands:${NC}
    sudo systemctl start $APP_NAME
    sudo systemctl stop $APP_NAME
    sudo systemctl restart $APP_NAME
    sudo systemctl status $APP_NAME
    sudo journalctl -u $APP_NAME -f

${YELLOW}View logs:${NC}
    tail -f $APP_DIR/logs/stdout.log
    tail -f $APP_DIR/logs/stderr.log

${YELLOW}Environment:${NC}
    Port: $PORT (set SETHSTENZEL_ME_PORT to change)
    App Directory: $APP_DIR
    Service File: $SERVICE_FILE
EOF
}

# Main script logic
case "${1:-help}" in
    install)
        install_service
        ;;
    update)
        update_application
        restart_service
        ;;
    restart)
        restart_service
        ;;
    logs)
        view_logs
        ;;
    status)
        view_status
        ;;
    uninstall)
        uninstall_service
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_red "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
