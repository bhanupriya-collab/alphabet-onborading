"""
Google Drive template loader utility.
Downloads HTML templates from a shared Google Drive folder using service account.
"""
import os
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Cache directory for downloaded templates
TEMPLATE_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
    'templates_cache'
)

# Google Drive folder ID
DRIVE_FOLDER_ID = "1XCZpTcW_3F5gXeo2sRQzqMT7wuydwfIg"

# Service account key file path (place in project root)
SERVICE_ACCOUNT_FILE = os.getenv("DRIVE_SERVICE_ACCOUNT_KEY", "service-account-key.json")

def _get_drive_service():
    """Build Google Drive API service using service account credentials"""
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    # Get service account file path (check project root)
    service_account_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        SERVICE_ACCOUNT_FILE
    )
    
    if not os.path.exists(service_account_path):
        raise FileNotFoundError(
            f"Service account key file not found: {service_account_path}\n"
            f"Please download it from GCP Console and place it in the project root.\n"
            f"Make sure the service account has access to the Drive folder."
        )
    
    # Create credentials from service account
    creds = service_account.Credentials.from_service_account_file(
        service_account_path,
        scopes=SCOPES
    )
    
    return build('drive', 'v3', credentials=creds, cache_discovery=False)

def _ensure_cache_dir():
    """Create cache directory if it doesn't exist"""
    if not os.path.exists(TEMPLATE_CACHE_DIR):
        os.makedirs(TEMPLATE_CACHE_DIR)

def _list_drive_templates():
    """List all .htm files in the Drive folder"""
    try:
        service = _get_drive_service()
        
        query = f"'{DRIVE_FOLDER_ID}' in parents and mimeType='text/html' and trashed=false"
        results = service.files().list(
            q=query,
            fields="files(id, name, modifiedTime)",
            pageSize=100
        ).execute()
        
        files = results.get('files', [])
        return {file['name']: file['id'] for file in files}
        
    except Exception as e:
        print(f"⚠️ Error listing Drive templates: {e}")
        return {}

def _download_template_from_drive(file_name, file_id):
    """Download a template file from Drive to local cache"""
    try:
        service = _get_drive_service()
        
        request = service.files().get_media(fileId=file_id)
        file_handle = io.BytesIO()
        downloader = MediaIoBaseDownload(file_handle, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        # Save to cache
        _ensure_cache_dir()
        cache_path = os.path.join(TEMPLATE_CACHE_DIR, file_name)
        
        with open(cache_path, 'wb') as f:
            f.write(file_handle.getvalue())
        
        print(f"✅ Downloaded template: {file_name}")
        return cache_path
        
    except Exception as e:
        print(f"⚠️ Error downloading template {file_name}: {e}")
        return None

def load_template_from_drive(template_name, use_cache=True):
    """
    Load an HTML template from Google Drive.
    
    Args:
        template_name: Name of the template file (e.g., "Password Setup Reminder.htm")
        use_cache: If True, use cached version if available
    
    Returns:
        HTML content as string, or None if not found
    """
    # Check cache first
    cache_path = os.path.join(TEMPLATE_CACHE_DIR, template_name)
    if use_cache and os.path.exists(cache_path):
        print(f"📄 Using cached template: {template_name}")
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    # List files in Drive folder
    drive_files = _list_drive_templates()
    
    if template_name not in drive_files:
        print(f"⚠️ Template '{template_name}' not found in Drive folder")
        print(f"Available templates: {list(drive_files.keys())}")
        return None
    
    # Download template
    file_id = drive_files[template_name]
    downloaded_path = _download_template_from_drive(template_name, file_id)
    
    if downloaded_path and os.path.exists(downloaded_path):
        with open(downloaded_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    return None

def sync_all_templates():
    """
    Download all templates from Drive to local cache.
    Useful for initial setup or bulk refresh.
    """
    print("🔄 Syncing all templates from Google Drive...")
    _ensure_cache_dir()
    
    drive_files = _list_drive_templates()
    
    if not drive_files:
        print("⚠️ No templates found in Drive folder")
        return
    
    print(f"📋 Found {len(drive_files)} template(s)")
    
    for file_name, file_id in drive_files.items():
        _download_template_from_drive(file_name, file_id)
    
    print("✅ Template sync complete")

def clear_template_cache():
    """Clear all cached templates"""
    if os.path.exists(TEMPLATE_CACHE_DIR):
        import shutil
        shutil.rmtree(TEMPLATE_CACHE_DIR)
        print("✅ Template cache cleared")
