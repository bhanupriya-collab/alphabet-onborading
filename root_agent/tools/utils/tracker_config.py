"""Central configuration for onboarding Excel tracker.

All tools should import `get_tracker_path()` instead of hardcoding paths.
Allows future relocation or renaming with a single change.
"""
import os

# Directory where the tracker lives (stay constant unless user relocates)
TRACKER_DIR = r"C:\\Users\\bhangupta\\Downloads\\Alphabet Onboarding - v1.1"

# Current tracker filename (user recently renamed from 'Alphabet Followup Tracker.xlsx')
TRACKER_FILENAME = "Onboarding EMail Tracker.xlsx"

def get_tracker_path() -> str:
    """Return absolute path to the onboarding tracker Excel file."""
    return os.path.join(TRACKER_DIR, TRACKER_FILENAME)
