from root_agent.tools.utils.drive_templates import sync_all_templates, load_template_from_drive

# Sync all templates
sync_all_templates()

# Test loading a specific template
content = load_template_from_drive("Password Setup Reminder.htm")
if content:
    print(f"✅ Template loaded: {len(content)} characters")
else:
    print("❌ Failed to load template")