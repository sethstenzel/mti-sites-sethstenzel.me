from pathlib import Path
import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from loguru import logger

# Gmail API imports
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GMAIL_API_AVAILABLE = True
except ImportError:
    GMAIL_API_AVAILABLE = False
    logger.warning("Gmail API libraries not available - contact form will not work")

def load_css(file_path: str) -> str:
    """Load CSS file and return as HTML style tag string."""
    css_path = Path(__file__).parent / file_path
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
        logger.debug(f"Loaded CSS file: {file_path} ({len(css_content)} bytes)")
        return f'<style>{css_content}</style>'
    except FileNotFoundError:
        logger.error(f"CSS file not found: {css_path}")
        return ''
    except Exception as e:
        logger.exception(f"Error loading CSS file {file_path}: {e}")
        return ''

def import_web_fonts() -> str:
    return '''
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Ubuntu:ital,wght@0,300;0,400;0,500;0,700;1,300;1,400;1,500;1,700&display=swap" rel="stylesheet">
    '''


# Gmail API Configuration
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.send']
GMAIL_CREDENTIALS_FILE = os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials.json')
GMAIL_TOKEN_FILE = os.getenv('GMAIL_TOKEN_FILE', 'token.json')


def get_gmail_service():
    """
    Authenticate and return Gmail API service.

    Returns:
        Gmail API service object or None if authentication fails
    """
    if not GMAIL_API_AVAILABLE:
        logger.error("Gmail API libraries not installed. Run: uv pip install -e .")
        return None

    creds = None
    token_path = Path(GMAIL_TOKEN_FILE)
    credentials_path = Path(GMAIL_CREDENTIALS_FILE)

    # Check if credentials file exists
    if not credentials_path.exists():
        logger.error(f"Gmail credentials file not found: {GMAIL_CREDENTIALS_FILE}")
        logger.error("Please download credentials.json from Google Cloud Console")
        return None

    # Load saved token if it exists
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), GMAIL_SCOPES)
        except Exception as e:
            logger.error(f"Error loading token file: {e}")
            creds = None

    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Error refreshing token: {e}")
                creds = None

        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logger.error(f"Error during authentication: {e}")
                return None

        # Save the credentials for future use
        try:
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        except Exception as e:
            logger.error(f"Error saving token: {e}")

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Error building Gmail service: {e}")
        return None


def send_email_via_gmail(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    from_email: str | None = None
) -> tuple[bool, str]:
    """
    Send email using Gmail API.

    Args:
        to_email: Recipient email address
        subject: Email subject
        body_text: Plain text body
        body_html: HTML body (optional)
        from_email: Sender email (optional, defaults to authenticated account)

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        service = get_gmail_service()
        if not service:
            return False, "Failed to authenticate with Gmail API"

        # Create message
        if body_html:
            message = MIMEMultipart('alternative')
            part1 = MIMEText(body_text, 'plain')
            part2 = MIMEText(body_html, 'html')
            message.attach(part1)
            message.attach(part2)
        else:
            message = MIMEText(body_text, 'plain')

        message['To'] = to_email
        message['Subject'] = subject
        if from_email:
            message['From'] = from_email

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

        # Send message
        send_message = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()

        logger.info(f"Email sent successfully. Message ID: {send_message['id']}")
        return True, f"Email sent successfully! Message ID: {send_message['id']}"

    except HttpError as error:
        logger.error(f"Gmail API error: {error}")
        return False, f"Gmail API error"
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False, f"Error sending email..."


def send_contact_form_email(
    name: str,
    email: str,
    message: str,
    recipient_email: str
) -> tuple[bool, str]:
    """
    Send contact form submission via Gmail API.

    Args:
        name: Sender's name
        email: Sender's email
        message: Message content
        recipient_email: Email address to receive the contact form

    Returns:
        Tuple of (success: bool, message: str)
    """
    subject = f"Contact Form Submission from {name}"

    body_text = f"""
New Contact Form Submission

Name: {name}
Email: {email}

Message:
{message}

---
This message was sent from the contact form on sethstenzel.me
"""

    body_html = f"""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
    <h2 style="color: #2c3e50;">New Contact Form Submission</h2>

    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
        <p><strong>Name:</strong> {name}</p>
        <p><strong>Email:</strong> <a href="mailto:{email}">{email}</a></p>
    </div>

    <div style="margin: 20px 0;">
        <p><strong>Message:</strong></p>
        <p style="background-color: #ffffff; padding: 15px; border-left: 4px solid #3498db; margin-top: 10px;">
            {message.replace('\n', '<br>')}
        </p>
    </div>

    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
    <p style="color: #7f8c8d; font-size: 12px;">
        This message was sent from the contact form on sethstenzel.me
    </p>
</body>
</html>
"""

    return send_email_via_gmail(
        to_email=recipient_email,
        subject=subject,
        body_text=body_text,
        body_html=body_html
    )