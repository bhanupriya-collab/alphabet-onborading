"""
Test script for action_required_mail._load_html_template()
Tests Drive template loading with local fallback.
"""

import sys
import os

# Add root_agent to path so we can import from tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'root_agent'))

from .root_agent.tools.action_required_mail import _load_html_template

def test_load_template():
    """Test loading the Action Required template"""
    print("=" * 60)
    print("Testing _load_html_template() from action_required_mail.py")
    print("=" * 60)
    
    try:
        # Call the function
        template_content = _load_html_template()
        
        # Validate the result
        if not template_content:
            print("❌ FAILED: Template content is empty")
            return False
        
        print(f"✅ SUCCESS: Loaded template ({len(template_content)} characters)")
        
        # Check if it's HTML
        if '<html>' in template_content.lower() or '<!doctype' in template_content.lower():
            print("✅ Valid HTML structure detected")
        else:
            print("⚠️  WARNING: Content doesn't appear to be HTML")
        
        # Show preview
        print("\n" + "-" * 60)
        print("Template Preview (first 500 characters):")
        print("-" * 60)
        print(template_content[:500])
        print("...")
        print("-" * 60)
        
        # Check for expected placeholders
        placeholders = ['{Candidate_Name}', '{Deadline_Date}']
        found_placeholders = [p for p in placeholders if p in template_content]
        
        if found_placeholders:
            print(f"\n✅ Found placeholders: {', '.join(found_placeholders)}")
        else:
            print(f"\n⚠️  No expected placeholders found (looking for: {', '.join(placeholders)})")
        
        return True
        
    except FileNotFoundError as e:
        print(f"❌ FAILED: Template file not found - {e}")
        print("\nThis could mean:")
        print("1. Template not in Drive folder")
        print("2. Template not in local templates/ directory")
        print("3. Service account doesn't have access to Drive folder")
        return False
        
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🔍 Starting template loading test...\n")
    
    # Show environment info
    print("Environment Check:")
    print(f"  - Working Directory: {os.getcwd()}")
    print(f"  - Service Account Key: {os.getenv('DRIVE_SERVICE_ACCOUNT_KEY', 'service-account-key.json')}")
    print(f"  - GCP Environment: {os.getenv('GCP_ENVIRONMENT', 'false')}")
    print()
    
    success = test_load_template()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TEST PASSED: Template loading works correctly")
    else:
        print("❌ TEST FAILED: See errors above")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
