import imaplib
import requests
import email
import re
from loguru import logger

# Global session for connection reuse
session = requests.Session()


def get_access_token(client_id, refresh_token):
    """Get OAuth access token from Microsoft"""
    data = {
        'client_id': client_id,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    try:
        response = session.post('https://login.live.com/oauth20_token.srf', data=data, timeout=10)
        return response.json().get('access_token')
    except Exception as e:
        logger.error(f"Error getting access token: {e}")
        return None


def generate_auth_string(user, token):
    """Generate IMAP XOAUTH2 authentication string"""
    return f"user={user}\1auth=Bearer {token}\1\1"


def extract_xm_verification_link(email_address, access_token):
    """Extract XM verification link from email"""
    try:
        mail = imaplib.IMAP4_SSL('outlook.office365.com', timeout=15)
        mail.authenticate('XOAUTH2', lambda x: generate_auth_string(email_address, access_token))
        mail.select("INBOX")

        # Search for XM emails
        status, messages = mail.search(None, 'FROM "site@xm.com"')

        if status != 'OK' or not messages[0]:
            mail.logout()
            logger.warning(f"No XM verification email found for {email_address}")
            return None

        email_ids = messages[0].split()

        # Get the most recent XM email
        if email_ids:
            last_email_id = email_ids[-1]
            status, msg_data = mail.fetch(last_email_id, '(RFC822)')
            if status == 'OK':
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Extract HTML content
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/html":
                            body = part.get_payload(decode=True).decode(errors="ignore")
                            break
                        elif content_type == "text/plain" and not body:
                            body = part.get_payload(decode=True).decode(errors="ignore")
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore")

                if body:
                    # Extract verification link from XM email
                    # Looking for: https://www.xm.com/register/profile-validated/...
                    match = re.search(r'https://www\.xm\.com/register/profile-validated/[a-zA-Z0-9-]+\?lang=en', body)
                    if match:
                        verification_link = match.group(0)
                        logger.success(f"Found XM verification link for {email_address}")
                        mail.logout()
                        return verification_link
                    else:
                        logger.warning(f"Could not find verification link in email body for {email_address}")

        mail.logout()
    except Exception as e:
        logger.error(f"Error extracting XM verification link: {e}")
        return None
    return None


def get_verification_link(email_address, refresh_token, client_id):
    """Get XM verification link from email"""
    access_token = get_access_token(client_id, refresh_token)
    if not access_token:
        logger.error(f"Failed to get access token for {email_address}")
        return None

    return extract_xm_verification_link(email_address, access_token)
