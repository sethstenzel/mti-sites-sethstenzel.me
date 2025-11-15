# GitHub Webhook Auto-Deployment Setup Guide

This guide will help you set up automatic deployments triggered by GitHub push events. When you push code to your GitHub repository, GitHub will notify your server, which will automatically pull the changes and restart your service.

## Overview

The auto-deployment system consists of:

1. **webhook_listener.py** - FastAPI app that receives webhook POST requests from GitHub
2. **webhook-listener.service** - systemd service that runs the webhook listener with uvicorn
3. **webhook-nginx.conf** - nginx configuration to expose the webhook endpoint
4. **deploy.sh** - Existing deployment script (already in your repo)

## Architecture

```
GitHub Push Event
    ↓
GitHub sends POST to https://sethstenzel.me/webhook
    ↓
nginx (reverse proxy on port 443)
    ↓
webhook_listener.py (FastAPI app on port 18100, running on uvicorn)
    ↓
Verifies webhook signature (security)
    ↓
Runs ./deploy.sh update
    ↓
Pulls code, updates dependencies, restarts service
```

## Release Branch Workflow

This setup uses a **release branch deployment strategy** for production safety:

- **`main` branch** - Active development branch
- **`release` branch** - Production deployment branch

**Why this approach?**
- Develop and test on `main` without affecting production
- Only deploy to production when you're ready
- Easy rollback if needed
- Better control over what goes live

### Development Workflow

#### 1. Daily Development (on `main` branch)

```bash
# Work on main branch
git checkout main

# Make changes, commit, and push
git add .
git commit -m "Add new feature"
git push origin main
```

**Result**: Code is pushed to GitHub but **NOT** deployed to production.

#### 2. Deploy to Production (merge to `release`)

When you're ready to deploy your changes to production:

**Option A: Merge via Command Line**

```bash
# Ensure main is up to date
git checkout main
git pull origin main

# Switch to release branch
git checkout release

# Pull latest release
git pull origin release

# Merge main into release
git merge main

# Push to GitHub (this triggers auto-deployment!)
git push origin release

# Switch back to main for continued development
git checkout main
```

**Option B: Merge via GitHub Web Interface**

1. Go to your repository on GitHub
2. Click **"Pull requests"** → **"New pull request"**
3. Set base branch: `release`, compare branch: `main`
4. Review changes
5. Click **"Create pull request"**
6. Add description: "Deploy latest changes to production"
7. Click **"Merge pull request"**
8. **Result**: Auto-deployment triggered!

**Option C: Fast-Forward Merge (recommended for clean history)**

```bash
# Switch to release
git checkout release
git pull origin release

# Fast-forward merge (only if release is behind main)
git merge main --ff-only

# Push (triggers deployment)
git push origin release

# Back to main
git checkout main
```

### Creating the Release Branch

If you don't already have a `release` branch:

```bash
# Create release branch from current main
git checkout main
git pull origin main
git checkout -b release
git push origin release

# Set release as a protected branch in GitHub (recommended)
# Settings → Branches → Add branch protection rule
# - Branch name pattern: release
# - Require pull request reviews before merging
# - Require status checks to pass before merging
```

### Hotfix Workflow

For urgent production fixes:

```bash
# Create hotfix from release
git checkout release
git pull origin release
git checkout -b hotfix/fix-critical-bug

# Make your fix
git add .
git commit -m "Fix critical bug"

# Merge back to release (triggers deployment)
git checkout release
git merge hotfix/fix-critical-bug
git push origin release

# Also merge to main to keep it updated
git checkout main
git merge hotfix/fix-critical-bug
git push origin main

# Delete hotfix branch
git branch -d hotfix/fix-critical-bug
```

### Rollback Strategy

If deployment causes issues:

**Option 1: Rollback release branch**

```bash
# On your local machine
git checkout release
git pull origin release

# View commit history
git log --oneline -10

# Reset to previous commit
git reset --hard <previous-commit-hash>

# Force push (triggers redeployment of old version)
git push origin release --force
```

**Option 2: Revert specific commit**

```bash
git checkout release
git revert <bad-commit-hash>
git push origin release  # Triggers deployment
```

**Option 3: Emergency manual rollback on server**

```bash
# SSH to your VPS
cd /var/www/sethstenzel.me
git checkout release
git reset --hard <previous-commit-hash>
sudo systemctl restart sethstenzel-site
```

## Prerequisites

- Ubuntu VPS with nginx and systemd (already set up per DEPLOYMENT.md)
- Your site already deployed and running (per DEPLOYMENT.md)
- Python virtual environment with FastAPI and uvicorn installed
- GitHub repository with admin access

## Installation Steps

### 1. Install FastAPI and uvicorn in Your Virtual Environment

On your VPS:

```bash
cd /var/www/sethstenzel.me
source .venv/bin/activate

# Install using the package (recommended - installs all dependencies)
uv pip install -e .

# Or install manually
uv pip install "fastapi>=0.115.0" "uvicorn[standard]>=0.32.0"
```

### 2. Generate a Webhook Secret

Generate a strong random secret for webhook security:

```bash
# Generate a secure random secret
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**IMPORTANT**: Copy this secret! You'll need it for both the systemd service and GitHub webhook configuration.

Example output: `a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2`

### 3. Install the Webhook Listener Service

```bash
cd /var/www/sethstenzel.me

# Make webhook listener executable
chmod +x webhook_listener.py

# Edit the service file to add your webhook secret
sudo nano webhook-listener.service
# Change the line:
#   Environment="WEBHOOK_SECRET=YOUR_SECRET_HERE_CHANGE_THIS"
# To:
#   Environment="WEBHOOK_SECRET=<your-generated-secret>"

# Copy service file to systemd
sudo cp webhook-listener.service /etc/systemd/system/

# Create logs directory if it doesn't exist
mkdir -p logs

# Set proper permissions
sudo chown -R appsuser:appsuser /var/www/sethstenzel.me

# Reload systemd, enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable webhook-listener
sudo systemctl start webhook-listener

# Check status
sudo systemctl status webhook-listener
```

### 4. Configure nginx

Add the webhook endpoint to your nginx configuration:

```bash
# Open your nginx site configuration
sudo nano /etc/nginx/sites-available/sethstenzel.me
```

Find the `server` block that handles HTTPS (port 443) and add the webhook location **BEFORE** the main `location / {` block:

```nginx
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name sethstenzel.me www.sethstenzel.me;

    # SSL configuration...
    ssl_certificate /etc/letsencrypt/live/sethstenzel.me/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sethstenzel.me/privkey.pem;

    # ADD THIS WEBHOOK LOCATION HERE:
    location /webhook {
        if ($request_method != POST) {
            return 405;
        }
        proxy_pass http://127.0.0.1:18100;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-GitHub-Event $http_x_github_event;
        proxy_set_header X-Hub-Signature-256 $http_x_hub_signature_256;
        proxy_connect_timeout 10s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        proxy_buffering off;
        client_max_body_size 10M;
    }

    # Your existing location block for the main app
    location / {
        proxy_pass http://127.0.0.1:18001;
        # ... rest of your config
    }
}
```

Alternatively, you can copy the configuration from `webhook-nginx.conf` in this repo.

Test and reload nginx:

```bash
# Test nginx configuration
sudo nginx -t

# If test passes, reload nginx
sudo systemctl reload nginx
```

### 5. Test the Webhook Listener

Test that the webhook listener is running and accessible:

```bash
# Test health endpoint locally
curl http://localhost:18100/health

# Test health endpoint through nginx (HTTPS)
curl https://sethstenzel.me/webhook/health
```

You should see a JSON response with status information.

**Bonus: Interactive API Documentation**

FastAPI automatically generates interactive API documentation:

```bash
# Access Swagger UI (interactive API docs)
curl http://localhost:18100/docs
# Or visit in browser: http://localhost:18100/docs

# Access ReDoc (alternative documentation)
curl http://localhost:18100/redoc
# Or visit in browser: http://localhost:18100/redoc
```

Note: These documentation endpoints are only accessible locally (127.0.0.1) for security. If you want to expose them via nginx, add additional location blocks, but this is generally not recommended for production.

### 6. Configure GitHub Webhook

Now configure GitHub to send webhook events to your server:

1. Go to your GitHub repository: `https://github.com/sethstenzel/mti-sites-sethstenzel.me`

2. Click **Settings** → **Webhooks** → **Add webhook**

3. Configure the webhook:
   - **Payload URL**: `https://sethstenzel.me/webhook`
   - **Content type**: `application/json`
   - **Secret**: Paste the webhook secret you generated in step 2
   - **SSL verification**: Enable SSL verification (recommended)
   - **Which events would you like to trigger this webhook?**: Select "Just the push event"
   - **Active**: ✓ (checked)

4. Click **Add webhook**

5. GitHub will immediately send a test ping. Check if it succeeded:
   - You should see a green checkmark next to the webhook
   - Click on the webhook to see delivery details
   - Check the "Recent Deliveries" tab

### 7. Test Auto-Deployment

Test that auto-deployment works:

1. Make a small change to your repository (e.g., update README.md)

2. Commit and push to main, then merge to release:
   ```bash
   # Commit to main
   git checkout main
   git add .
   git commit -m "Test auto-deployment"
   git push origin main

   # Merge to release (this triggers deployment)
   git checkout release
   git pull origin release
   git merge main
   git push origin release
   ```

3. Watch the webhook listener logs:
   ```bash
   sudo journalctl -u webhook-listener -f
   # or
   tail -f /var/www/sethstenzel.me/logs/webhook-stdout.log
   ```

4. Check your site's logs to see the restart:
   ```bash
   sudo journalctl -u sethstenzel-site -f
   ```

5. Verify your changes are live on your website

## Configuration Options

You can customize the webhook listener by editing `/etc/systemd/system/webhook-listener.service`:

### Environment Variables

- **WEBHOOK_PORT**: Port for webhook listener (default: 18100)
- **WEBHOOK_SECRET**: Secret for verifying GitHub webhooks (REQUIRED)
- **SERVICE_NAME**: Name of the systemd service to restart (default: sethstenzel-site)
- **DEPLOY_SCRIPT**: Path to deployment script (default: /var/www/sethstenzel.me/deploy.sh)
- **ALLOWED_BRANCHES**: Comma-separated list of branches to deploy (default: release)

### Example: Deploy from Multiple Branches

To deploy from both `release` and `staging` branches:

```bash
sudo nano /etc/systemd/system/webhook-listener.service
```

Change:
```ini
Environment="ALLOWED_BRANCHES=release,staging"
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl restart webhook-listener
```

## Management Commands

### View Webhook Listener Status

```bash
sudo systemctl status webhook-listener
```

### View Live Logs

```bash
# systemd journal
sudo journalctl -u webhook-listener -f

# Application logs
tail -f /var/www/sethstenzel.me/logs/webhook-stdout.log
tail -f /var/www/sethstenzel.me/logs/webhook-stderr.log
```

### Restart Webhook Listener

```bash
sudo systemctl restart webhook-listener
```

### Stop/Start Webhook Listener

```bash
sudo systemctl stop webhook-listener
sudo systemctl start webhook-listener
```

### Disable Auto-Start on Boot

```bash
sudo systemctl disable webhook-listener
```

## Security Considerations

### Webhook Secret

- **ALWAYS** use a strong, randomly generated webhook secret
- **NEVER** commit the webhook secret to your repository
- The webhook listener verifies the `X-Hub-Signature-256` header using HMAC-SHA256
- Requests with invalid signatures are rejected with HTTP 403

### Network Security

- The webhook listener only listens on `127.0.0.1` (localhost), not `0.0.0.0`
- Only nginx can access it (via reverse proxy)
- nginx only allows POST requests to `/webhook`
- HTTPS ensures encrypted communication

### Rate Limiting (Optional)

To protect against abuse, you can add rate limiting in nginx:

```nginx
# Add to http block in /etc/nginx/nginx.conf
limit_req_zone $binary_remote_addr zone=webhook:10m rate=10r/m;

# Then in your location block:
location /webhook {
    limit_req zone=webhook burst=5;
    # ... rest of config
}
```

### Firewall

Ensure your firewall only allows necessary ports:

```bash
sudo ufw status
# Should show: 22 (SSH), 80 (HTTP), 443 (HTTPS)
# Port 18100 should NOT be exposed externally
```

## Troubleshooting

### Webhook Returns 403 (Forbidden)

**Cause**: Signature verification failed

**Solutions**:
1. Verify the webhook secret matches in both:
   - GitHub webhook settings
   - `/etc/systemd/system/webhook-listener.service`
2. Check GitHub webhook "Recent Deliveries" for error details
3. Check webhook listener logs: `sudo journalctl -u webhook-listener -n 50`

### Webhook Returns 500 (Internal Server Error)

**Cause**: Deployment script failed

**Solutions**:
1. Check webhook listener logs: `tail -50 /var/www/sethstenzel.me/logs/webhook-stderr.log`
2. Try running deployment manually: `cd /var/www/sethstenzel.me && ./deploy.sh update`
3. Check git permissions: `sudo chown -R appsuser:appsuser /var/www/sethstenzel.me`

### Webhook Not Triggering

**Possible causes**:

1. **Webhook listener not running**:
   ```bash
   sudo systemctl status webhook-listener
   sudo systemctl start webhook-listener
   ```

2. **nginx not configured**:
   ```bash
   sudo nginx -t
   curl https://sethstenzel.me/webhook/health
   ```

3. **Wrong branch**:
   - Check `ALLOWED_BRANCHES` in service file
   - Verify you pushed to `release` (or configured branch)
   - Remember: pushing to `main` does NOT trigger deployment

4. **GitHub webhook not active**:
   - Check GitHub repository settings → Webhooks
   - Verify webhook is active (green checkmark)
   - Check "Recent Deliveries" tab for errors

### Deployment Fails with Permission Errors

```bash
# Ensure proper ownership
sudo chown -R appsuser:appsuser /var/www/sethstenzel.me

# Ensure deploy.sh is executable
chmod +x /var/www/sethstenzel.me/deploy.sh

# Check git config
cd /var/www/sethstenzel.me
sudo -u appsuser git pull
```

### Port 18100 Already in Use

Check what's using the port:

```bash
sudo netstat -tlnp | grep :18100
# or
sudo ss -tlnp | grep :18100
```

Change to a different port:

```bash
# Edit service file
sudo nano /etc/systemd/system/webhook-listener.service
# Change WEBHOOK_PORT to something else (e.g., 18101)

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart webhook-listener
```

## Advanced: Multiple Projects

To set up auto-deployment for multiple projects:

### 1. Option A: Run One Webhook Listener Per Project

For each project:

```bash
# Use different ports
# Project 1: Port 18100 → /var/www/sethstenzel.me
# Project 2: Port 18101 → /var/www/othersite.com
# Project 3: Port 18102 → /var/www/anothersite.com

# Create separate service files
sudo cp webhook-listener.service /etc/systemd/system/webhook-listener-project2.service

# Edit and change:
# - WEBHOOK_PORT
# - WorkingDirectory
# - SERVICE_NAME
# - DEPLOY_SCRIPT
# - ExecStart path

# Add nginx location blocks for each
location /webhook-project2 {
    proxy_pass http://127.0.0.1:18101;
    # ...
}
```

### 2. Option B: Enhanced Webhook Listener (Advanced)

Modify `webhook_listener.py` to:
- Accept repository name in payload
- Route to correct deployment script based on repo
- Run multiple projects from one listener

(This requires custom development)

## Monitoring

### Set Up Monitoring (Recommended)

Monitor your webhook endpoint with:

1. **UptimeRobot** (free): Monitor `/webhook/health` endpoint
2. **Pingdom**: Monitor uptime
3. **Sentry**: Track errors in webhook listener

### Check Deployment History

View webhook deployment history:

```bash
# See all deployments
sudo journalctl -u webhook-listener | grep "Deployment"

# See recent deployments
sudo journalctl -u webhook-listener -n 100 | grep "Push to"
```

## Rollback

If auto-deployment causes issues, you can quickly rollback:

```bash
cd /var/www/sethstenzel.me

# View commit history
git log --oneline -10

# Rollback to previous commit
git reset --hard <commit-hash>

# Restart service
sudo systemctl restart sethstenzel-site
```

## Disabling Auto-Deployment

### Temporarily Disable

```bash
# Stop webhook listener
sudo systemctl stop webhook-listener

# Or disable in GitHub
# Settings → Webhooks → Edit → Uncheck "Active"
```

### Permanently Remove

```bash
# Stop and disable service
sudo systemctl stop webhook-listener
sudo systemctl disable webhook-listener

# Remove service file
sudo rm /etc/systemd/system/webhook-listener.service

# Reload systemd
sudo systemctl daemon-reload

# Remove nginx webhook location block
sudo nano /etc/nginx/sites-available/sethstenzel.me
# Remove the location /webhook { } block

# Reload nginx
sudo nginx -t && sudo systemctl reload nginx

# Delete webhook from GitHub
# Settings → Webhooks → Delete webhook
```

## Files Reference

- **webhook_listener.py** - FastAPI webhook listener application
- **webhook-listener.service** - systemd service configuration
- **webhook-nginx.conf** - nginx configuration snippet
- **deploy.sh** - Deployment script (already exists)
- **WEBHOOK_SETUP.md** - This guide

## Next Steps

1. Set up monitoring for `/webhook/health` endpoint
2. Configure GitHub branch protection rules
3. Set up staging environment for testing before production
4. Consider implementing deployment notifications (Slack, Discord, email)
5. Set up automated backups before deployments

## Support

For issues:
- Check logs: `sudo journalctl -u webhook-listener -f`
- Test manually: `./deploy.sh update`
- Verify nginx: `sudo nginx -t`
- Test endpoint: `curl https://sethstenzel.me/webhook/health`

## References

- [GitHub Webhooks Documentation](https://docs.github.com/en/webhooks)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [nginx Reverse Proxy](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
- [systemd Service Documentation](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
