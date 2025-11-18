"""
Upload HTML email templates to Google Drive using OAuth authentication.
"""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
# DRIVE_FOLDER_ID = "14X272jpFyWtLIMqSefRWtuT-niXdZbQX"  # Replace with your Drive folder ID
DRIVE_FOLDER_ID = "1XCZpTcW_3F5gXeo2sRQzqMT7wuydwfIg"  # Replace with your Drive folder ID
TEMPLATES_DIR = "root_agent/templates"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_authenticated_service():
    """
    Get Drive service using OAuth credentials.
    Reuses token.json if available, otherwise prompts for login.
    """
    creds = None
    token_file = 'drive_token.json'
    
    # Load existing token if available
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Token refresh failed: {e}")
                if os.path.exists(token_file):
                    os.remove(token_file)
                creds = None
        
        if not creds:
            # Load OAuth credentials from environment variables
            client_id = os.getenv("GOOGLE_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
            
            if not client_id or not client_secret:
                raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in environment variables or .env file")
            
            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://localhost:8001"]
                }
            }
            
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(
                port=8080,
                access_type='offline',
                prompt='consent'
            )
            
            # Save credentials for next run
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
    
    # Build Drive service
    service = build('drive', 'v3', credentials=creds)
    return service

def upload_file(service, file_path, folder_id):
    """
    Upload a single file to Google Drive folder.
    
    Args:
        service: Google Drive service instance
        file_path: Local path to the file
        folder_id: Google Drive folder ID
    
    Returns:
        File ID of uploaded file
    """
    file_name = os.path.basename(file_path)
    
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    
    media = MediaFileUpload(
        file_path,
        mimetype='text/html',
        resumable=True
    )
    
    print(f"📤 Uploading: {file_name}...")
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, webViewLink'
    ).execute()
    
    print(f"   ✅ Uploaded: {file.get('name')}")
    print(f"   📄 File ID: {file.get('id')}")
    print(f"   🔗 Link: {file.get('webViewLink')}\n")
    
    return file.get('id')

def list_existing_files(service, folder_id):
    """List files already in the Drive folder."""
    query = f"'{folder_id}' in parents and trashed=false"
    results = service.files().list(
        q=query,
        fields='files(id, name)',
        pageSize=100
    ).execute()
    
    files = results.get('files', [])
    return {f['name']: f['id'] for f in files}

def update_file(service, file_id, file_path):
    """Update an existing file in Drive."""
    file_name = os.path.basename(file_path)
    
    media = MediaFileUpload(
        file_path,
        mimetype='text/html',
        resumable=True
    )
    
    print(f"🔄 Updating: {file_name}...")
    
    file = service.files().update(
        fileId=file_id,
        media_body=media,
        fields='id, name, webViewLink'
    ).execute()
    
    print(f"   ✅ Updated: {file.get('name')}")
    print(f"   🔗 Link: {file.get('webViewLink')}\n")
    
    return file.get('id')

def upload_all_templates(folder_id, update_existing=True):
    """
    Upload all HTML templates from the templates directory to Drive.
    
    Args:
        folder_id: Google Drive folder ID
        update_existing: If True, updates existing files instead of creating duplicates
    """
    # Get authenticated service
    print("🔐 Authenticating with Google Drive...")
    service = get_authenticated_service()
    print("✅ Authentication successful!\n")
    
    # Get templates directory
    templates_path = os.path.join(
        os.path.dirname(__file__),
        TEMPLATES_DIR
    )
    
    if not os.path.exists(templates_path):
        print(f"❌ Templates directory not found: {templates_path}")
        return
    
    # Get list of HTML files
    html_files = [
        f for f in os.listdir(templates_path)
        if f.endswith('.htm') or f.endswith('.html')
    ]
    
    if not html_files:
        print(f"❌ No HTML files found in {templates_path}")
        return
    
    print(f"📋 Found {len(html_files)} template file(s)\n")
    
    # Check existing files in Drive folder
    existing_files = {}
    if update_existing:
        print("🔍 Checking for existing files in Drive folder...")
        existing_files = list_existing_files(service, folder_id)
        print(f"   Found {len(existing_files)} existing file(s)\n")
    
    # Upload or update each template
    uploaded = 0
    updated = 0
    failed = 0
    
    for file_name in html_files:
        file_path = os.path.join(templates_path, file_name)
        
        try:
            if update_existing and file_name in existing_files:
                # Update existing file
                update_file(service, existing_files[file_name], file_path)
                updated += 1
            else:
                # Upload new file
                upload_file(service, file_path, folder_id)
                uploaded += 1
        except Exception as e:
            print(f"   ❌ Error with {file_name}: {str(e)}\n")
            failed += 1
    
    # Summary
    print("=" * 60)
    print("📊 Upload Summary:")
    print(f"   ✅ Uploaded: {uploaded}")
    print(f"   🔄 Updated: {updated}")
    print(f"   ❌ Failed: {failed}")
    print("=" * 60)

if __name__ == "__main__":
    print("=" * 60)
    print("  Google Drive Template Upload Script")
    print("=" * 60)
    print()
    
    # Check if folder ID is set
    if DRIVE_FOLDER_ID == "YOUR_FOLDER_ID_HERE":
        print("❌ Error: Please set DRIVE_FOLDER_ID in the script")
        print()
        print("To get your folder ID:")
        print("1. Open the Google Drive folder in your browser")
        print("2. Copy the ID from the URL:")
        print("   https://drive.google.com/drive/folders/FOLDER_ID_HERE")
        print()
    else:
        # Run upload
        upload_all_templates(
            folder_id=DRIVE_FOLDER_ID,
            update_existing=True  # Set to False to always create new files
        )
