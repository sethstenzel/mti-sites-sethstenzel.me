# Gmail API Setup Guide for Contact Form

This guide walks you through setting up Gmail API credentials to enable the contact form to send emails.

## Overview

The contact form uses the Gmail API to send emails. This requires:
1. A Google Cloud Project
2. Gmail API enabled
3. OAuth 2.0 credentials
4. User authentication

## Step-by-Step Setup

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top (or create account if you don't have one)
3. Click **"New Project"**
4. Enter project name: e.g., "SethStenzel.me Contact Form"
5. Click **"Create"**
6. Wait for the project to be created, then select it

### 2. Enable Gmail API

1. In the Google Cloud Console, ensure your project is selected
2. Go to **"APIs & Services"** → **"Library"**
3. Search for **"Gmail API"**
4. Click on **"Gmail API"**
5. Click **"Enable"**

### 3. Configure OAuth Consent Screen

Before creating credentials, you need to configure the OAuth consent screen:

1. Go to **"APIs & Services"** → **"OAuth consent screen"**

2. Select **"External"** (unless you have a Google Workspace account)
   - Click **"Create"**

3. **App Information**:
   - **App name**: "SethStenzel.me Contact Form" (or your preference)
   - **User support email**: Your Gmail address
   - **App logo**: (optional)

4. **App domain** (optional but recommended):
   - **Application home page**: https://sethstenzel.me
   - **Application privacy policy link**: (optional)
   - **Application terms of service link**: (optional)

5. **Developer contact information**:
   - Enter your email address
   - Click **"Save and Continue"**

6. **Scopes**:
   - Click **"Add or Remove Scopes"**
   - Search for "Gmail API"
   - Select: `https://www.googleapis.com/auth/gmail.send`
   - Click **"Update"**
   - Click **"Save and Continue"**

7. **Test users** (Important for External apps in testing mode):
   - Click **"Add Users"**
   - Add your Gmail address (the one you'll authenticate with)
   - Click **"Add"**
   - Click **"Save and Continue"**

8. **Summary**:
   - Review your settings
   - Click **"Back to Dashboard"**

### 4. Create OAuth 2.0 Credentials

1. Go to **"APIs & Services"** → **"Credentials"**

2. Click **"Create Credentials"** → **"OAuth client ID"**

3. **Application type**: Select **"Desktop app"**
   - **Name**: "Contact Form Desktop Client"
   - Click **"Create"**

4. **Download Credentials**:
   - You'll see a dialog with your client ID and client secret
   - Click **"Download JSON"**
   - Save the file as **`credentials.json`**
   - Click **"OK"**

### 5. Install the Credentials File

#### For Local Development:

```bash
# Copy credentials.json to your project root
cp ~/Downloads/credentials.json /path/to/mti-sites-sethstenzel.me/credentials.json
```

#### For Production (VPS):

```bash
# Upload to your VPS
scp ~/Downloads/credentials.json user@your-vps:/var/www/sethstenzel.me/credentials.json

# Set proper permissions
sudo chown www-data:www-data /var/www/sethstenzel.me/credentials.json
sudo chmod 600 /var/www/sethstenzel.me/credentials.json
```

### 6. Configure Environment Variables

#### For Local Development:

```bash
# Set recipient email (where contact form submissions go)
export CONTACT_RECIPIENT_EMAIL="your-email@gmail.com"

# Optional: specify custom paths
export GMAIL_CREDENTIALS_FILE="credentials.json"
export GMAIL_TOKEN_FILE="token.json"
```

#### For Production (VPS):

Edit the systemd service file:

```bash
sudo nano /etc/systemd/system/sethstenzel-site.service
```

Add environment variables:

```ini
[Service]
# ... existing configuration ...
Environment="CONTACT_RECIPIENT_EMAIL=your-email@gmail.com"
Environment="GMAIL_CREDENTIALS_FILE=/var/www/sethstenzel.me/credentials.json"
Environment="GMAIL_TOKEN_FILE=/var/www/sethstenzel.me/token.json"
```

Reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart sethstenzel-site
```

### 7. First-Time Authentication

The first time the contact form is used, you'll need to authenticate:

#### Local Development:

1. Run your application:
   ```bash
   python -m mti_sites_sethstenzel_me.site --dev
   ```

2. Fill out the contact form and submit

3. A browser window will open asking you to:
   - Select your Google account
   - Review permissions
   - Click **"Allow"**

4. The authentication will complete, and a `token.json` file will be created

5. Future form submissions will use this token automatically

#### Production (VPS) - First Time Setup:

For production, you need to authenticate once. There are two approaches:

**Option A: Authenticate Locally First (Recommended)**

1. Authenticate on your local machine (steps above)
2. This creates `token.json`
3. Upload `token.json` to your VPS:
   ```bash
   scp token.json user@your-vps:/var/www/sethstenzel.me/
   sudo chown www-data:www-data /var/www/sethstenzel.me/token.json
   sudo chmod 600 /var/www/sethstenzel.me/token.json
   ```

**Option B: Authenticate on VPS via SSH Tunnel**

1. SSH to your VPS with port forwarding:
   ```bash
   ssh -L 8080:localhost:8080 user@your-vps
   ```

2. Temporarily run the app in a way that triggers authentication:
   ```bash
   cd /var/www/sethstenzel.me
   source .venv/bin/activate
   python -c "from mti_sites_sethstenzel_me.utils import get_gmail_service; get_gmail_service()"
   ```

3. The OAuth flow will start and you can authenticate via the tunnel

4. Token file will be created on the VPS

### 8. Verify Setup

Test that email sending works:

```bash
cd /var/www/sethstenzel.me
source .venv/bin/activate
python
```

```python
from mti_sites_sethstenzel_me.utils import send_contact_form_email

success, message = send_contact_form_email(
    name="Test User",
    email="test@example.com",
    message="This is a test message",
    recipient_email="your-email@gmail.com"
)

print(f"Success: {success}")
print(f"Message: {message}")
```

You should receive an email!

## File Structure

After setup, you should have:

```
/var/www/sethstenzel.me/
├── credentials.json    # OAuth client credentials (never commit to git!)
├── token.json         # User authentication token (never commit to git!)
└── ...
```

**IMPORTANT**: Add these to `.gitignore`:

```bash
echo "credentials.json" >> .gitignore
echo "token.json" >> .gitignore
```

## Security Best Practices

### 1. Keep Credentials Secure

```bash
# Set strict permissions
chmod 600 credentials.json token.json

# Only www-data (web server) should access them
sudo chown www-data:www-data credentials.json token.json
```

### 2. Never Commit Credentials

Ensure `.gitignore` includes:
```
credentials.json
token.json
```

### 3. Use Environment Variables

Don't hardcode emails in the code. Use environment variables:

```python
CONTACT_RECIPIENT_EMAIL = os.getenv('CONTACT_RECIPIENT_EMAIL')
```

### 4. Restrict OAuth Scopes

Only request the minimum scope needed:
- ✅ `gmail.send` - Send email only
- ❌ `gmail.readonly` - Not needed
- ❌ `gmail.modify` - Not needed

### 5. Publish Your App (Optional)

If you want to avoid the "unverified app" warning:

1. Go to OAuth consent screen in Google Cloud Console
2. Click **"Publish App"**
3. Submit for verification (requires app review)

For personal use, staying in testing mode is fine - just add yourself as a test user.

## Troubleshooting

### "credentials.json not found"

**Solution**: Make sure `credentials.json` is in the correct location:
```bash
ls -la /var/www/sethstenzel.me/credentials.json
```

If missing, download again from Google Cloud Console.

### "Access blocked: This app's request is invalid"

**Cause**: OAuth consent screen not configured properly

**Solution**:
1. Go to OAuth consent screen in Google Cloud Console
2. Make sure your email is added as a test user
3. Ensure the Gmail API send scope is added

### "Token has been expired or revoked"

**Solution**: Delete `token.json` and re-authenticate:
```bash
rm token.json
# Then trigger authentication again by submitting the contact form
```

### "The user has not granted the app permission"

**Solution**: You need to authenticate at least once:
- Run the app and submit the contact form
- Complete the OAuth flow in the browser
- This creates `token.json` for future use

### "Rate limit exceeded"

**Cause**: Too many emails sent

**Solution**:
- Gmail API has sending limits (500 emails/day for free accounts)
- Consider adding rate limiting to your contact form
- Or use a professional email service for high volume

### Production: "Browser not available for authentication"

**Cause**: Server has no display for browser

**Solution**: Use Option A in "First-Time Authentication" section - authenticate locally first, then upload `token.json`

## Gmail API Quotas and Limits

- **Free tier**: 1 billion quota units/day
- **Sending emails**: ~100 quota units per send
- **Practical limit**: ~10 million sends/day (way more than you need for a contact form)
- **User sending limit**: 500 emails/day for regular Gmail accounts, 2000/day for Google Workspace

For a contact form, these limits are more than sufficient.

## Alternative: Using App Passwords (Simpler but Less Secure)

If you find OAuth too complex, you can use Gmail App Passwords instead:

### Enable App Passwords:

1. Go to your Google Account settings
2. Security → 2-Step Verification (enable if not already)
3. Security → App passwords
4. Generate an app password
5. Use SMTP instead of Gmail API

### SMTP Example:

```python
import smtplib
from email.mime.text import MIMEText

def send_via_smtp(to_email, subject, body):
    gmail_user = 'your-email@gmail.com'
    gmail_app_password = 'your-app-password'  # 16-character password

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = gmail_user
    msg['To'] = to_email

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(gmail_user, gmail_app_password)
        smtp.send_message(msg)
```

**Note**: Gmail API is preferred because:
- More secure (OAuth vs password)
- Better for automation
- More reliable for server environments
- Official Google recommendation

## Support

For issues:
- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Python Quickstart Guide](https://developers.google.com/gmail/api/quickstart/python)

## Summary Checklist

- [ ] Google Cloud Project created
- [ ] Gmail API enabled
- [ ] OAuth consent screen configured
- [ ] Test user added (your Gmail address)
- [ ] OAuth credentials created and downloaded
- [ ] `credentials.json` uploaded to server
- [ ] Environment variables configured
- [ ] First-time authentication completed
- [ ] `token.json` created
- [ ] Files added to `.gitignore`
- [ ] Permissions set correctly (600, owned by www-data)
- [ ] Test email sent successfully

Once complete, your contact form will be fully functional!
