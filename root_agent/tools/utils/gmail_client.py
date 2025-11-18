# dwd_gmail_client.py
import os
import base64
import json
import time
import ssl
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from urllib3.exceptions import NewConnectionError
from dotenv import load_dotenv
# from PIL import Image
import io
# from datetime import datetime, timedelta

# Load environment variables from .env file
load_dotenv()

# def load_and_resize_image(image_path: str, max_width: int, max_height: int = None) -> str:
#     """
#     Load, resize, and convert image to base64 for email embedding
#     """
#     try:
#         # Get the directory where this script is located
#         script_dir = os.path.dirname(os.path.abspath(__file__))
#         full_path = os.path.join(script_dir, image_path)
        
#         if not os.path.exists(full_path):
#             print(f"⚠️ Image file not found: {full_path}")
#             return None
            
#         # Open and resize image
#         with Image.open(full_path) as img:
#             # Convert to RGB if necessary (for JPEG compatibility)
#             if img.mode in ('RGBA', 'P'):
#                 img = img.convert('RGB')
            
#             # Calculate new dimensions maintaining aspect ratio
#             original_width, original_height = img.size
            
#             if max_height is None:
#                 # Only width constraint
#                 if original_width > max_width:
#                     ratio = max_width / original_width
#                     new_width = max_width
#                     new_height = int(original_height * ratio)
#                 else:
#                     new_width, new_height = original_width, original_height
#             else:
#                 # Both width and height constraints
#                 width_ratio = max_width / original_width
#                 height_ratio = max_height / original_height
#                 ratio = min(width_ratio, height_ratio)
                
#                 new_width = int(original_width * ratio)
#                 new_height = int(original_height * ratio)
            
#             # Resize image
#             resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
#             # Convert to base64
#             buffer = io.BytesIO()
#             resized_img.save(buffer, format='JPEG', quality=85, optimize=True)
#             img_data = buffer.getvalue()
            
#             return base64.b64encode(img_data).decode('utf-8')
            
#     except Exception as e:
#         print(f"⚠️ Error processing image {image_path}: {str(e)}")
#         return None

# def get_newsletter_images():
#     """
#     Load and process newsletter images - use exact PNG file for logo
#     """
#     # Load Deloitte logo as-is from PNG file
#     base_path = os.path.dirname(os.path.abspath(__file__))
#     logo_path = os.path.join(base_path, 'deloitte_logo.png')
    
#     try:
#         with open(logo_path, 'rb') as f:
#             logo_data = base64.b64encode(f.read()).decode('utf-8')
#     except:
#         logo_data = None
    
#     return {
#         'deloitte_logo': logo_data,
#         'featured_image': load_and_resize_image('Newsletter_image.jpg', max_width=800, max_height=300)
#     }

# def load_social_icon(filename: str) -> str:
#     """Load a social icon and normalize for consistent visual size.
#     Steps:
#       1. Convert to RGBA.
#       2. Trim fully-transparent border pixels (if any) to reduce wasted space.
#       3. Scale longest side to 36px (upscale small images too).
#       4. Center on a 40x40 transparent canvas.
#     Returns base64 PNG or None if file missing.
#     """
#     base_path = os.path.dirname(os.path.abspath(__file__))
#     path = os.path.join(base_path, filename)
#     if not os.path.exists(path):
#         return None
#     try:
#         from PIL import Image
#         with Image.open(path) as img:
#             if img.mode != 'RGBA':
#                 img = img.convert('RGBA')
#             # Trim transparent borders
#             bbox = img.getbbox()  # For non-transparent trimming: we need alpha mask
#             if bbox:
#                 # Create alpha mask bounding box for transparency cropping
#                 alpha = img.split()[-1]
#                 alpha_bbox = alpha.getbbox()
#                 if alpha_bbox:
#                     img = img.crop(alpha_bbox)
#             w, h = img.size
#             # Allow contact/email icon a slightly larger visual size
#             base_target = 36.0
#             if 'contact' in filename or 'email' in filename or 'mail' in filename:
#                 target_inner = 38.0
#             else:
#                 target_inner = base_target
#             scale = target_inner / max(w, h)
#             new_w = int(w * scale)
#             new_h = int(h * scale)
#             img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
#             canvas = Image.new('RGBA', (40, 40), (255, 255, 255, 0))
#             x = (40 - new_w) // 2
#             y = (40 - new_h) // 2
#             canvas.paste(img, (x, y), img)
#             buf = io.BytesIO()
#             canvas.save(buf, format='PNG', optimize=True)
#             return base64.b64encode(buf.getvalue()).decode('utf-8')
#     except Exception as e:
#         print(f"Icon load error for {filename}: {e}")
#         return None

# def get_social_icons():
#     """Load fixed social icon files (use exact provided names)."""
#     return {
#         'facebook': load_social_icon('facebook_logo.jpg'),
#         'twitter': load_social_icon('twitter_logo.png'),
#         'linkedin': load_social_icon('linkedin_logo.png'),
#         'contact': load_social_icon('contact_logo.png')
#     }

# def generate_social_links_html():
#     icons = get_social_icons()
#     links = [
#         ("https://www.facebook.com/deloitte", icons.get('facebook'), 'Facebook'),
#         ("https://twitter.com/Deloitte", icons.get('twitter'), 'Twitter'),
#         ("http://www.linkedin.com/company/deloitte", icons.get('linkedin'), 'LinkedIn'),
#         ("https://www2.deloitte.com/global/en/get-connected/contact-us.html?icid=bottom_contact-us", icons.get('contact'), 'Contact')
#     ]
#     cells = []
#     for href, b64, label in links:
#         if b64:
#             img_tag = f"<img src='data:image/png;base64,{b64}' alt='{label}' style='display:block; width:40px; height:40px; border-radius:50%;'>"
#         else:
#             img_tag = f"<div style='width:40px; height:40px; background:#e0e0e0; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:14px; color:#2E86C1;'>{label[0]}</div>"
#         cells.append(
#             "<td align='center' valign='middle' style='padding:0 24px;'>"
#             f"<a href='{href}' target='_blank' style='display:block; text-decoration:none; cursor:pointer;' title='{label}'>" + img_tag + "</a></td>"
#         )
#     return "<table role='presentation' cellspacing='0' cellpadding='0' border='0' style='margin:12px auto 0 auto;'><tr>" + ''.join(cells) + "</tr></table>"

# def format_email_body(subject: str, body: str) -> str:
#     """
#     Enhanced email formatting with professional newsletter styling.
#     Converts markdown-style formatting and adds proper HTML structure.
#     """
#     # Enhanced text formatting
#     formatted_body = body
    
#     # Convert markdown-style formatting to HTML
#     import re
    
#     # Convert markdown headings (### or ##) to HTML headings with increased bottom spacing
#     formatted_body = re.sub(r'^### (.+)$', r'<h3 style="color: #2E86C1; margin: 24px 0 18px 0; font-size: 18px; font-weight: 600;">\1</h3>', formatted_body, flags=re.MULTILINE)
#     formatted_body = re.sub(r'^## (.+)$', r'<h2 style="color: #2E86C1; margin: 28px 0 20px 0; font-size: 20px; font-weight: 600;">\1</h2>', formatted_body, flags=re.MULTILINE)
    
#     # Convert **bold** to <strong>bold</strong>
#     formatted_body = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted_body)
    
#     # Convert markdown links [text](url) to HTML links
#     formatted_body = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" style="color: #2E86C1; text-decoration: none;">\1</a>', formatted_body)
    
#     # Convert bullet points (• or -) to proper HTML lists
#     lines = formatted_body.split('\n')
#     processed_lines = []
#     in_list = False
    
#     for line in lines:
#         line = line.strip()
#         if line.startswith('•') or line.startswith('- ') or line.startswith('* '):
#             if not in_list:
#                 processed_lines.append('<ul style="margin: 8px 0; padding-left: 20px;">')
#                 in_list = True
#             if line.startswith('•'):
#                 bullet_text = line[1:].strip()
#             elif line.startswith('- '):
#                 bullet_text = line[2:].strip()
#             elif line.startswith('* '):
#                 bullet_text = line[2:].strip()
#             processed_lines.append(f'<li style="margin: 5px 0; line-height:1.5;">{bullet_text}</li>')
#         else:
#             if in_list:
#                 processed_lines.append('</ul>')
#                 in_list = False
#             if line:
#                 # Check if line looks like a heading (starts with **word** or is all caps)
#                 if line.startswith('**') and line.endswith('**'):
#                     heading_text = line[2:-2]
#                     processed_lines.append(f'<h3 style="color: #2E86C1; margin: 24px 0 18px 0; font-size: 18px; font-weight: 600;">{heading_text}</h3>')
#                 elif line.isupper() and len(line) > 5:
#                     processed_lines.append(f'<h3 style="color: #2E86C1; margin: 24px 0 18px 0; font-size: 18px; font-weight: 600;">{line}</h3>')
#                 else:
#                     processed_lines.append(f'<p style="margin: 8px 0; line-height: 1.55;">{line}</p>')
#             else:
#                 # collapse multiple blank lines: ignore
#                 pass
    
#     if in_list:
#         processed_lines.append('</ul>')
    
#     formatted_body = '\n'.join(processed_lines)
    
#     # Load newsletter images
#     images = get_newsletter_images()
    
#     return f"""
#         <!DOCTYPE html>
#         <html>
#             <head>
#                 <meta charset="utf-8">
#                 <meta name="viewport" content="width=device-width, initial-scale=1.0">
#                 <title>{subject}</title>
#                 <style>
#                     body {{
#                         font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
#                         line-height: 1.6;
#                         color: #333333;
#                         max-width: 800px;
#                         margin: 0 auto;
#                         padding: 20px;
#                         background-color: #ffffff; /* Unified plain white background */
#                     }}
#                     .email-container {{
#                         background-color: #ffffff; /* Single white wrapper */
#                         border-radius: 0;
#                         padding: 0;
#                         box-shadow: none; /* Remove box look */
#                         margin: 0;
#                     }}
#                     .header {{
#                         background-color: #000000;
#                         padding: 8px 0 6px 0; /* reduced header panel padding */
#                         margin: 0;
#                         text-align: center;
#                         border-radius: 0;
#                     }}
#                     .newsletter-bar {{
#                         font-size: 14px;
#                         color: #666;
#                         margin: 8px 0 12px 0; /* reduced bottom spacing */
#                     }}
#                     .featured-image {{
#                         margin: 12px 0 18px 0; /* tighter spacing */
#                         text-align: center;
#                     }}
#                     .header h1 {{
#                         color: #2E86C1;
#                         margin: 0;
#                         font-size: 24px;
#                         font-weight: 600;
#                     }}
#                     .content {{
#                         margin-bottom: 30px;
#                     }}
#                     .content h3 {{
#                         color: #2E86C1;
#                         margin: 24px 0 18px 0; /* further increased bottom spacing before content */
#                         font-size: 18px;
#                         font-weight: 600;
#                     }}
#                     .content p {{
#                         margin: 8px 0; /* moderate paragraph spacing */
#                         line-height: 1.55;
#                     }}
#                     .content ul {{
#                         margin: 8px 0; /* moderate list block spacing */
#                         padding-left: 22px;
#                     }}
#                     .content li {{
#                         margin: 5px 0; /* moderate bullet spacing */
#                         line-height: 1.5;
#                     }}
#                     .footer {{
#                         border-top: 1px solid #e9ecef;
#                         padding-top: 20px;
#                         margin-top: 30px;
#                         font-style: italic;
#                         color: #6c757d;
#                     }}
#                     .signature {{
#                         margin-top: 20px;
#                         font-weight: 500;
#                         color: #495057;
#                     }}
#                     a {{
#                         color: #2E86C1;
#                         text-decoration: none;
#                     }}
#                     a:hover {{
#                         text-decoration: underline;
#                     }}
#                     strong {{
#                         color: #2c3e50;
#                         font-weight: 600;
#                     }}
#                     @media only screen and (max-width: 600px) {{
#                         body {{
#                             padding: 10px;
#                         }}
#                         .email-container {{
#                             padding: 20px;
#                         }}
#                         .header h1 {{
#                             font-size: 18px;
#                         }}
#                         .header div {{
#                             flex-direction: column;
#                             align-items: flex-start !important;
#                         }}
#                         .featured-image img {{
#                             height: 150px;
#                         }}
#                     }}
#                 </style>
#             </head>
#             <body>
#                 <div class="email-container">
#                     <div class="header">
#                         {"<img src='data:image/png;base64," + images['deloitte_logo'] + "' alt='Deloitte Logo' style='max-width: 100px; height: 6px; display: block; margin: 0 auto;'>" if images.get('deloitte_logo') else "<div style='font-weight: bold; color: #ffffff; font-size: 24px; letter-spacing: 2px;'>DELOITTE</div>"}
#                     </div>
#                     <div class="newsletter-bar">Monthly Newsletter | For Internal Use Only | {subject}</div>
#                     <div class="featured-image">
#                         {"<img src='data:image/jpeg;base64," + images['featured_image'] + "' alt='News and Updates' style='width: 70%; height: auto; max-height: 320px; object-fit: cover; border-radius: 8px; display: block; margin: 0 auto;'>" if images['featured_image'] else ""}
#                     </div>
#                     <div class="content">
#                         {formatted_body}
#                     </div>
#                     <div class="footer">
#                         {"" if True else ""}
#                         <div class="signature" style="font-size: 12px;">
#                             <strong>Regards,</strong><br>
#                             <strong>News Letter Agent</strong>
#                         </div>
#                         <p style="font-size: 12px; color: #868e96; margin-top: 15px;">
#                             This monthly newsletter is powered by Deloitte's Newsletter Agent. 
#                         </p>
#                                 <div style="margin-top: 20px; text-align: center; padding-top: 15px; border-top: 1px solid #e9ecef;">
#                                      <p style="font-size: 11px; color: #999; margin-bottom: 10px;">Connect with us:</p>
#                                      {generate_social_links_html()}
#                                 </div>
#                     </div>
#                 </div>
#             </body>
#         </html>
#     """

class GmailAPIClient:
    def __init__(self, use_domain_wide_delegation=False, service_account_file=None, delegate_as_email=None):
        self.SCOPES = [
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.compose'
        ]
        self.service = None
        self.use_domain_wide_delegation = use_domain_wide_delegation
        self.service_account_file = service_account_file
        self.delegate_as_email = delegate_as_email

        if self.use_domain_wide_delegation:
            if not self.service_account_file or not os.path.exists(self.service_account_file):
                raise ValueError("Service account key file path is required and must exist for Domain-Wide Delegation.")
            if not self.delegate_as_email:
                raise ValueError("Email address to delegate as (subject) is required for Domain-Wide Delegation.")
        else:
            # Load OAuth credentials from environment variables
            self.client_id = os.getenv("GOOGLE_CLIENT_ID")
            self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
            self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080")
            
            if not self.client_id or not self.client_secret:
                raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in environment variables or .env file")

        self.authenticate()
    
    def create_client_config(self):
        """Create client configuration from individual credentials for standard OAuth"""
        return {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }
    
    def authenticate(self):
        """Authenticate using client ID and secret"""
        creds = None
        token_file = 'token.json'
        # Load existing token if available
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, self.SCOPES)
        # If no valid credentials, get new ones
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Token refresh failed: {e}")
                # Only remove token file if it exists
                if os.path.exists(token_file):
                    os.remove(token_file)
                creds = None
        if not creds or not creds.valid:
            # Create flow from client config
            client_config = self.create_client_config()
            flow = InstalledAppFlow.from_client_config(
                client_config, 
                scopes=self.SCOPES
            )
            # flow.redirect_uri = self.redirect_uri
            # # Run local server for OAuth
            # creds = flow.run_local_server(port=8080)
            creds = flow.run_local_server(
                port=8080,
                access_type='offline',
                prompt='consent'
            )
            # Save credentials for next run
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        # Build Gmail service with timeout settings and better SSL handling
        try:
            self.service = build(
                'gmail', 
                'v1', 
                credentials=creds, 
                cache_discovery=False,
                # Add timeout configurations
                timeout=30
            )
            print("✅ Gmail API authentication successful")
        except Exception as e:
            print(f"⚠️  Error building Gmail service: {e}")
            # Retry building service once more
            time.sleep(2)
            self.service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
            print("✅ Gmail API authentication successful (retry)")
    
    def create_message_with_attachment(self, to, subject, body, attachment_path=None):
        """Create email message with optional PDF attachment"""
        try:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            message['from'] = self.delegate_as_email if self.use_domain_wide_delegation else 'me'
            
            html_part = MIMEText(body, 'html')
            message.attach(html_part)
            
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as f:
                    pdf_data = f.read()
                
                pdf_attachment = MIMEApplication(pdf_data, _subtype='pdf')
                pdf_attachment.add_header(
                    'Content-Disposition', 
                    'attachment', 
                    filename=os.path.basename(attachment_path)
                )
                message.attach(pdf_attachment)
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            return {'raw': raw_message}
            
        except Exception as e:
            raise Exception(f"Error creating message: {str(e)}")
    # Add this function to your gmail_client.py


    def send_email(self, to, subject, body, attachment_path=None, max_retries=5):
        """Send email using Gmail API with enhanced retry logic for SSL/connection issues"""
        
        # Format the email body with professional styling
        # formatted_body = format_email_body(subject, body)
        formatted_body = body  
        
        for attempt in range(max_retries):
            try:
                if not self.service:
                    print("🔄 Gmail service not initialized, re-authenticating...")
                    self.authenticate()
                
                message = self.create_message_with_attachment(to, subject, formatted_body, attachment_path)
                
                # Add timeout and retry logic for the actual API call
                result = self.service.users().messages().send(
                    userId='me', 
                    body=message
                ).execute()
                
                return f"✅ Email sent successfully via Gmail API. Message ID: {result['id']}"
                
            except (ssl.SSLError, ssl.SSLEOFError, socket.error, OSError, ConnectionError) as ssl_error:
                error_msg = str(ssl_error).lower()
                print(f"⚠️  SSL/Connection error on attempt {attempt + 1}/{max_retries}: {ssl_error}")
                
                if attempt < max_retries - 1:
                    wait_time = min((attempt + 1) * 3, 15)  # Exponential backoff: 3, 6, 9, 12, 15 seconds max
                    print(f"⏳ Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    
                    # Force re-authentication and rebuild service on SSL errors
                    try:
                        print("🔄 Re-building Gmail service due to SSL error...")
                        self.service = None  # Clear existing service
                        self.authenticate()
                    except Exception as auth_error:
                        print(f"⚠️  Re-authentication failed: {auth_error}")
                        # Continue to next attempt even if re-auth fails
                else:
                    return f"❌ Email sending failed with SSL error after {max_retries} attempts: {ssl_error}"
            
            except HttpError as http_error:
                try:
                    error_details = json.loads(http_error.content.decode('utf-8'))
                    error_message = error_details.get('error', {}).get('message', str(http_error))
                except:
                    error_message = str(http_error)
                
                # Some HTTP errors are retryable (5xx), others are not (4xx)
                if http_error.resp.status >= 500 and attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"⚠️  HTTP 5xx error on attempt {attempt + 1}/{max_retries}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    return f"❌ Gmail API HTTP error: {error_message}"
                    
            except Exception as general_error:
                error_str = str(general_error)
                print(f"⚠️  General error on attempt {attempt + 1}/{max_retries}: {error_str}")
                
                # Check if it's a retryable error (expanded list for SSL issues)
                retryable_errors = [
                    'unexpected eof while reading',
                    'connection reset by peer',
                    'timeout',
                    'network',
                    'connection',
                    'ssl',
                    'eof',
                    'broken pipe',
                    'socket',
                    'certificate',
                    'handshake'
                ]
                
                is_retryable = any(retry_keyword in error_str.lower() for retry_keyword in retryable_errors)
                
                if is_retryable and attempt < max_retries - 1:
                    wait_time = min((attempt + 1) * 3, 15)  # Exponential backoff with 15s max
                    print(f"⏳ Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    
                    # Force service rebuild on connection errors
                    try:
                        print("🔄 Re-building Gmail service due to connection error...")
                        self.service = None  # Clear existing service
                        self.authenticate()
                    except Exception as auth_error:
                        print(f"⚠️  Re-authentication failed: {auth_error}")
                        # Continue to next attempt even if re-auth fails
                else:
                    return f"❌ Email sending failed with non-retryable error: {error_str}"
        
        return f"❌ Email sending failed after {max_retries} attempts with various errors"
    
    def test_connection(self):
        """Test Gmail API connection"""
        try:
            if not self.service:
                return "❌ Gmail service not initialized"
            
            profile = self.service.users().getProfile(userId='me').execute()
            email = profile.get('emailAddress', 'Unknown')
            return f"✅ Connected to Gmail API as: {email}"
            
        except Exception as e:
            return f"❌ Connection test failed: {str(e)}"
        
def send_html_gmail_api(to: str, subject: str, html_body: str, attachments: list = None) -> str:
    """Send HTML email with attachments using Gmail API"""
    try:
        # Create Gmail client
        client = GmailAPIClient()

        # Send email
        result = client.send_email(
            to=to,
            subject=subject,
            body=html_body,
            attachment_path=attachments[0] if attachments else None
        )
        return result

    except Exception as e:
        return f"❌ Gmail API email failed: {str(e)}"