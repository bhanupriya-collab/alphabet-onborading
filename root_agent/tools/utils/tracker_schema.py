"""Canonical column schema for the onboarding Excel tracker.

All indices are 1-based (openpyxl cell(row, column) uses 1-based indexing).
Update here if the workbook structure changes. Keep comments mapping letter to meaning.
"""
from datetime import datetime, timezone
from typing import Iterable

# Core identity columns
COLUMN_NAME = 1                         # A - Name
COLUMN_EMAIL_ID = 2                     # B - Email ID
COLUMN_WORKORDER_ID = 3                 # C - Workorder ID
COLUMN_LOCATION = 4                     # D - Location
COLUMN_TIMEZONE = 5                     # E - Timezone
COLUMN_CHROMEBOOK_SERIAL_NUMBER = 6     # F - Chromebook Serial Number
COLUMN_FIELDGLASS_PROFILE_CREATED = 7   # G - Fieldglass Profile Created (Yes/No/Date)
COLUMN_COMPLIANCE_DOCUMENT_ACK = 8      # H - Compliance Document Acknowledgment (Yes/No/Date)
COLUMN_PARTNER_DOMAIN_ACCOUNT_CREATION = 9  # I - Partner Domain Account Creation (Yes/No/Date)
COLUMN_START_DATE = 10                  # J - Start Date
COLUMN_MOMA_ACCOUNT_ACTIVATED = 11      # K - MOMA Account Activated (Yes/No/Date)
COLUMN_HARDWARE_CONFIRMATION_NEXT_STEPS = 12  # L - Hardware Confirmation and next steps
COLUMN_ID_VERIFICATION_COMPLETED = 13   # M - ID Verification Completed (Yes/No/Date)
COLUMN_PASSWORD_SETUP_APPT_SCHEDULED = 14  # N - Password Setup Appointment Scheduled (Yes/No)
COLUMN_PASSWORD_SETUP_APPT_TIME = 15       # O - Password Setup Appointment Time (datetime/string)
COLUMN_CHROMEBOOK_ASSIGNED_LDAP = 16    # P - Chromebook Assigned to the LDAP (Yes/No/Date)
COLUMN_NEXT_EMAIL_TYPE = 17             # Q - Next Email Type (string)
COLUMN_NEXT_EMAIL_AT = 18               # R - Next Email At (timestamp UTC)
COLUMN_EMAIL_STATUS = 19                # S - Email Status (e.g., Pending/Sent/Skipped)
COLUMN_OVERALL_STATUS = 20              # T - Overall Status (aggregate pipeline state)

# Convenience groups (adjust as workflows evolve)
IDENTITY_REQUIRED_COLS: Iterable[int] = (
    COLUMN_NAME,
    COLUMN_EMAIL_ID,
    COLUMN_WORKORDER_ID,
    COLUMN_LOCATION,
    COLUMN_TIMEZONE,
)

PASSWORD_APPT_REQUIRED_COLS: Iterable[int] = (
    COLUMN_NAME,
    COLUMN_EMAIL_ID,
    COLUMN_PASSWORD_SETUP_APPT_SCHEDULED,
    COLUMN_PASSWORD_SETUP_APPT_TIME,
)

COMPLIANCE_REQUIRED_COLS: Iterable[int] = (
    COLUMN_NAME,
    COLUMN_EMAIL_ID,
    COLUMN_FIELDGLASS_PROFILE_CREATED,
    COLUMN_COMPLIANCE_DOCUMENT_ACK,
)

ALL_TRACKER_COLUMNS = {
    'NAME': COLUMN_NAME,
    'EMAIL_ID': COLUMN_EMAIL_ID,
    'WORKORDER_ID': COLUMN_WORKORDER_ID,
    'LOCATION': COLUMN_LOCATION,
    'TIMEZONE': COLUMN_TIMEZONE,
    'CHROMEBOOK_SERIAL_NUMBER': COLUMN_CHROMEBOOK_SERIAL_NUMBER,
    'FIELDGLASS_PROFILE_CREATED': COLUMN_FIELDGLASS_PROFILE_CREATED,
    'COMPLIANCE_DOCUMENT_ACK': COLUMN_COMPLIANCE_DOCUMENT_ACK,
    'PARTNER_DOMAIN_ACCOUNT_CREATION': COLUMN_PARTNER_DOMAIN_ACCOUNT_CREATION,
    'START_DATE': COLUMN_START_DATE,
    'MOMA_ACCOUNT_ACTIVATED': COLUMN_MOMA_ACCOUNT_ACTIVATED,
    'HARDWARE_CONFIRMATION_NEXT_STEPS': COLUMN_HARDWARE_CONFIRMATION_NEXT_STEPS,
    'ID_VERIFICATION_COMPLETED': COLUMN_ID_VERIFICATION_COMPLETED,
    'PASSWORD_SETUP_APPT_SCHEDULED': COLUMN_PASSWORD_SETUP_APPT_SCHEDULED,
    'PASSWORD_SETUP_APPT_TIME': COLUMN_PASSWORD_SETUP_APPT_TIME,
    'CHROMEBOOK_ASSIGNED_LDAP': COLUMN_CHROMEBOOK_ASSIGNED_LDAP,
    'NEXT_EMAIL_TYPE': COLUMN_NEXT_EMAIL_TYPE,
    'NEXT_EMAIL_AT': COLUMN_NEXT_EMAIL_AT,
    'EMAIL_STATUS': COLUMN_EMAIL_STATUS,
    'OVERALL_STATUS': COLUMN_OVERALL_STATUS,
}

MAX_COLUMN_INDEX = max(ALL_TRACKER_COLUMNS.values())

def set_timestamp(ws, row: int, column: int, dt: datetime | None = None) -> None:
    """Write UTC timestamp string to given cell."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    ws.cell(row=row, column=column, value=dt.strftime('%Y-%m-%d %H:%M:%S UTC'))

def assert_min_columns(ws) -> None:
    """Ensure worksheet has at least MAX_COLUMN_INDEX columns in header row.
    Raises ValueError if insufficient columns.
    """
    header = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
    if len(header) < MAX_COLUMN_INDEX:
        raise ValueError(f"Worksheet has {len(header)} columns; expected >= {MAX_COLUMN_INDEX}. Update tracker or schema.")

def is_cell_filled(value) -> bool:
    """Basic filled check treating non-empty strings and non-None values as filled."""
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == '':
        return False
    return True

__all__ = [
    'COLUMN_NAME',
    'COLUMN_EMAIL_ID',
    'COLUMN_WORKORDER_ID',
    'COLUMN_LOCATION',
    'COLUMN_TIMEZONE',
    'COLUMN_CHROMEBOOK_SERIAL_NUMBER',
    'COLUMN_FIELDGLASS_PROFILE_CREATED',
    'COLUMN_COMPLIANCE_DOCUMENT_ACK',
    'COLUMN_PARTNER_DOMAIN_ACCOUNT_CREATION',
    'COLUMN_START_DATE',
    'COLUMN_MOMA_ACCOUNT_ACTIVATED',
    'COLUMN_HARDWARE_CONFIRMATION_NEXT_STEPS',
    'COLUMN_ID_VERIFICATION_COMPLETED',
    'COLUMN_PASSWORD_SETUP_APPT_SCHEDULED',
    'COLUMN_PASSWORD_SETUP_APPT_TIME',
    'COLUMN_CHROMEBOOK_ASSIGNED_LDAP',
    'COLUMN_NEXT_EMAIL_TYPE',
    'COLUMN_NEXT_EMAIL_AT',
    'COLUMN_EMAIL_STATUS',
    'COLUMN_OVERALL_STATUS',
    'IDENTITY_REQUIRED_COLS',
    'PASSWORD_APPT_REQUIRED_COLS',
    'COMPLIANCE_REQUIRED_COLS',
    'ALL_TRACKER_COLUMNS',
    'MAX_COLUMN_INDEX',
    'set_timestamp',
    'assert_min_columns',
    'is_cell_filled'
]
