import os
from typing import Optional
from pydoc import text
import time
import asyncio
from turtle import width

from numpy import size

# from .utils.gmail_client_copy import send_html_gmail_api, send_html_smtp_fallback
# from .utils.get_attachments import download_from_gcs  # attachments currently disabled

# New: direct Gmail API client usage (token.json based)
from .utils.gmail_client import GmailAPIClient
from .utils.gmail_client import send_html_gmail_api
from .utils.drive_templates import load_template_from_drive

# Dotenv Imports
import dotenv
dotenv.load_dotenv()
SENDER_EMAIL=os.getenv('SENDER_EMAIL')
SENDER_APP_PASSWORD = os.getenv('SENDER_APP_PASSWORD')
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = os.getenv('SMTP_PORT')
EMAIL_CREDS = {
        "host": os.getenv('SMTP_HOST'),  # Example for Gmail
        "port": os.getenv('SMTP_PORT'),
        "sender": os.getenv('SENDER_EMAIL'), # Replace with your sender email
        "password": os.getenv('SENDER_APP_PASSWORD') # Replace with your Gmail App Password
    }


# Location to template filename mapping
LOCATION_TEMPLATE_MAP = {
    'Mumbai': 'Mumbai - Google Account Onboarding - USI  Hardware Collection Required .htm',
    'Bangalore': 'Bangalore - Google Account Onboarding - USI  Hardware Collection Required.htm',
    'Chennai': 'Chennai - Google Account Onboarding - USI  Hardware Collection Required.htm',
    'Hyderabad': 'Hyderabad - Google Account Onboarding - USI  Hardware Collection Required.htm',
    'Gurugram': 'Gurugram - Google Account Onboarding - USI  Hardware Collection Required.htm',
    'Kolkata': 'Kolkata - Google Account Onboarding - USI  Hardware Collection Required.htm',
    'Pune': 'Pune - Google Account Onboarding - USI  Hardware Collection Required.htm',
    'Ireland': 'Ireland - Google Account Onboarding - Hardware Collection Required.htm',
    'UK': 'UK - Google Account Onboarding - Hardware Collection Required.htm',
}

# Default template (fallback)
DEFAULT_TEMPLATE = 'Google Account Onboarding - USI  Hardware Collection Required.htm'

def _load_html_template(location: str = None):
    """Load raw HTML from Google Drive or local .htm template file based on location.
    If location not provided or not found, uses default template.
    Tries Drive first, then falls back to local files.
    """
    # Determine which template to use
    if location and location in LOCATION_TEMPLATE_MAP:
        template_filename = LOCATION_TEMPLATE_MAP[location]
    else:
        template_filename = DEFAULT_TEMPLATE
    
    # Try loading from Google Drive first
    try:
        template_content = load_template_from_drive(template_filename, use_cache=True)
        if template_content:
            print(f"[welcome_mail] Loaded template from Drive: {template_filename}")
            return template_content
    except Exception as e:
        print(f"[welcome_mail] Drive template load failed: {e}, falling back to local")
    
    # Fallback to local templates directory
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    template_path = os.path.join(templates_dir, template_filename)
    
    if not os.path.exists(template_path):
        print(f"[welcome_mail] HTML template not found at {template_path}")
        return "<html><body><p>(Template missing)</p></body></html>"
    try:
        with open(template_path, 'r', encoding='utf-8', errors='replace') as f:
            print(f"[welcome_mail] Loaded template from local: {template_filename}")
            return f.read()
    except Exception as e:
        print(f"[welcome_mail] Failed to read HTML template: {e}")
        return f"<html><body><p>(Template read error: {e})</p></body></html>"

# 1 Send welcome email
_GMAIL_CLIENT = None  # cached instance

def welcome_mail(Candidate_Name:str, Location:str, candidateEmailID:str, PoC: Optional[str] = None) -> dict:
    """Send onboarding email. Primary path: GmailAPIClient(). 
    PoC is optional since templates have hardcoded contact info per location."""
    global EMAIL_CREDS, _GMAIL_CLIENT
    Candidate_Name = Candidate_Name or "Bhanu"
    Location = Location or "N/A"
    candidateEmailID = candidateEmailID or "bhangupta@deloitte.com"
    try:

        # bucket_name = os.getenv('BUCKET_NAME')
        # gcs_files = [
        #     "Section_1.mp4",
        #     "Section_2.mp4"
        # ]
        # # Download files locally
        # attachments_to_send = [download_from_gcs(bucket_name, f) for f in gcs_files]


        # # Define the attachments list
        # attachments_to_send = ["email_attachments/Section_1.mp4", "email_attachments/Section_2.mp4"]
        
        # Load template and substitute placeholders
        raw_template = _load_html_template(location=Location)
        # Use replace() instead of format() to avoid issues with CSS curly braces
        html = raw_template.replace('{Candidate_Name}', Candidate_Name)

        attachments_to_send = []  # currently unused

        subject = "Google Account Onboarding - USI | Hardware Collection Required"

        if _GMAIL_CLIENT is None:
            try:
                _GMAIL_CLIENT = GmailAPIClient()
            except Exception as init_e:
                print(f"[welcome_mail] GmailAPIClient init failed: {init_e}")
                _GMAIL_CLIENT = None

        gmail_status = None
        if _GMAIL_CLIENT:
            gmail_status = _GMAIL_CLIENT.send_email(
                to=candidateEmailID,
                subject=subject,
                body=html,
                attachment_path=None
            )
            print(f"[welcome_mail] Gmail API send status: {gmail_status}")
            if gmail_status and gmail_status.startswith("✅"):
                return {
                    'response': 'Welcome Mail Sent',
                    'transport': 'gmail_api',
                    'status': gmail_status,
                    'recipient': candidateEmailID
                }
        else:
            print("[welcome_mail] Gmail client unavailable; will try SMTP fallback.")

        # --- Fallback: existing SMTP helper (legacy path currently disabled) ---
        missing = [k for k,v in EMAIL_CREDS.items() if v in (None, '')]
        if missing:
            print(f"[welcome_mail] Missing SMTP credentials: {missing}")
            return {'response': 'Welcome Mail Failed', 'error': f'Missing SMTP creds: {missing}', 'gmail_status': gmail_status}

        # NOTE: SMTP fallback code is commented out in this version. If needed, re-enable send logic here.
        smtp_status = None
        print(f"[welcome_mail] Using SMTP host={SMTP_HOST} port={EMAIL_CREDS['port']} sender={SENDER_EMAIL}")
        print(f"📧 Email sending attempt result:\n{smtp_status}")
        if smtp_status and ("Email sent successfully" in smtp_status or "SMTP" in smtp_status or "OK" in smtp_status):
            return {
                'response': 'Welcome Mail Sent',
                'transport': 'smtp',
                'status': smtp_status,
                'gmail_status': gmail_status,
                'recipient': candidateEmailID
            }
        return {
            'response': 'Welcome Mail Failed',
            'error': smtp_status,
            'gmail_status': gmail_status,
            'recipient': candidateEmailID
        }

    except Exception as e:
        print(f"An unexpected error occurred during email sending: {str(e)}")
        email_res = f"Both mail sending attempts failed: {str(e)}"
        print(
            f"❌ Email sending failed completely:\n{email_res}"
        )
        return {'response': 'Welcome Mail Failed'}













