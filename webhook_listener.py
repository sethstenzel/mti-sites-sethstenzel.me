#!/usr/bin/env python3
"""
GitHub Webhook Listener for Automated Deployments
Listens for push events from GitHub and triggers deployments
Built with FastAPI for better performance and async support
"""

import os
import sys
import hmac
import hashlib
import subprocess
from typing import Dict, Any, List

from fastapi import FastAPI, Request, HTTPException, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from loguru import logger

# Configure loguru
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "webhook_listener.log",
    rotation="10 MB",
    retention="1 week",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    level="DEBUG"
)

# Configuration
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', '')
if not WEBHOOK_SECRET:
    logger.critical("WEBHOOK_SECRET environment variable must be set!")
    sys.exit(1)

WEBHOOK_PORT = int(os.environ.get('WEBHOOK_PORT', '18100'))
DEPLOY_SCRIPT = os.environ.get('DEPLOY_SCRIPT', './deploy.sh')
SERVICE_NAME = os.environ.get('SERVICE_NAME', 'sethstenzel-site')
ALLOWED_BRANCHES = os.environ.get('ALLOWED_BRANCHES', 'release').split(',')

# FastAPI app
app = FastAPI(
    title="GitHub Webhook Listener",
    description="Automated deployment service for GitHub webhooks",
    version="2.0.0",
    docs_url="/docs",  # Swagger UI at /docs
    redoc_url="/redoc"  # ReDoc at /redoc
)


# Pydantic models for request validation
class HealthResponse(BaseModel):
    status: str
    service: str
    port: int


class WebhookResponse(BaseModel):
    message: str
    repository: str | None = None
    branch: str | None = None
    pusher: str | None = None
    commits: int | None = None
    output: str | None = None


class ErrorResponse(BaseModel):
    error: str
    repository: str | None = None
    branch: str | None = None
    output: str | None = None


class ServiceInfo(BaseModel):
    service: str
    status: str
    endpoints: Dict[str, str]
    configuration: Dict[str, Any]


def verify_signature(payload_body: bytes, signature_header: str | None) -> bool:
    """Verify that the payload was sent from GitHub by validating SHA256 signature."""
    if not signature_header:
        return False

    try:
        hash_algorithm, github_signature = signature_header.split('=')
        algorithm = hashlib.__dict__.get(hash_algorithm)

        if not algorithm:
            return False

        mac = hmac.new(WEBHOOK_SECRET.encode(), msg=payload_body, digestmod=algorithm)
        return hmac.compare_digest(mac.hexdigest(), github_signature)
    except (ValueError, AttributeError):
        return False


async def run_deployment() -> tuple[bool, str]:
    """Execute the deployment script asynchronously."""
    try:
        logger.info(f"Running deployment script: {DEPLOY_SCRIPT}")

        # Run the deploy.sh update command
        result = subprocess.run(
            [DEPLOY_SCRIPT, 'update'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            logger.info("Deployment successful!")
            logger.info(f"Output: {result.stdout}")
            return True, result.stdout
        else:
            logger.error(f"Deployment failed with exit code {result.returncode}")
            logger.error(f"Error: {result.stderr}")
            return False, result.stderr

    except subprocess.TimeoutExpired:
        logger.error("Deployment timed out!")
        return False, "Deployment timed out after 5 minutes"
    except Exception as e:
        logger.error(f"Deployment error: {str(e)}")
        return False, str(e)


@app.get("/", response_model=ServiceInfo)
async def index():
    """Root endpoint - show service info."""
    return ServiceInfo(
        service="GitHub Webhook Listener",
        status="running",
        endpoints={
            "/": "Service information",
            "/health": "Health check",
            "/webhook": "GitHub webhook endpoint (POST only)",
            "/docs": "Interactive API documentation (Swagger UI)",
            "/redoc": "API documentation (ReDoc)"
        },
        configuration={
            "service_name": SERVICE_NAME,
            "allowed_branches": ALLOWED_BRANCHES,
            "port": WEBHOOK_PORT
        }
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service=SERVICE_NAME,
        port=WEBHOOK_PORT
    )


@app.post("/webhook")
async def webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: str | None = Header(None, alias="X-GitHub-Event")
):
    """
    Handle GitHub webhook POST requests.

    Verifies the webhook signature and triggers deployment for push events
    to allowed branches.
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify the request signature
    if not verify_signature(body, x_hub_signature_256):
        client_host = request.client.host if request.client else "unknown"
        logger.warning(f"Invalid signature from {client_host}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid signature"
        )

    # Parse the JSON payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse JSON payload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON"
        )

    # Get event type
    event_type = x_github_event or 'unknown'
    logger.info(f"Received {event_type} event from GitHub")

    # Only handle push events
    if event_type != 'push':
        logger.info(f"Ignoring {event_type} event")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": f"Event {event_type} ignored"}
        )

    # Check if the push is to an allowed branch
    ref = payload.get('ref', '')
    branch = ref.replace('refs/heads/', '')

    if branch not in ALLOWED_BRANCHES:
        logger.info(f"Ignoring push to branch '{branch}' (allowed: {ALLOWED_BRANCHES})")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": f"Branch {branch} not configured for auto-deployment"}
        )

    # Get repository info
    repo_name = payload.get('repository', {}).get('full_name', 'unknown')
    pusher = payload.get('pusher', {}).get('name', 'unknown')
    commits_count = len(payload.get('commits', []))

    logger.info(f"Push to {repo_name}/{branch} by {pusher} ({commits_count} commits)")

    # Trigger deployment
    success, output = await run_deployment()

    if success:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=WebhookResponse(
                message="Deployment triggered successfully",
                repository=repo_name,
                branch=branch,
                pusher=pusher,
                commits=commits_count,
                output=output
            ).model_dump()
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error="Deployment failed",
                repository=repo_name,
                branch=branch,
                output=output
            ).model_dump()
        )


@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    logger.info(f"Starting GitHub Webhook Listener")
    logger.info(f"Service: {SERVICE_NAME}")
    logger.info(f"Allowed branches: {ALLOWED_BRANCHES}")
    logger.info(f"Deploy script: {DEPLOY_SCRIPT}")
    logger.info(f"Port: {WEBHOOK_PORT}")
    logger.info(f"API Documentation available at: http://127.0.0.1:{WEBHOOK_PORT}/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown information."""
    logger.info("Shutting down GitHub Webhook Listener")


if __name__ == '__main__':
    import uvicorn

    logger.info(f"Starting webhook listener on port {WEBHOOK_PORT}")

    # Run with uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",  # Only listen on localhost - nginx will proxy
        port=WEBHOOK_PORT,
        log_level="info",
        access_log=True
    )
