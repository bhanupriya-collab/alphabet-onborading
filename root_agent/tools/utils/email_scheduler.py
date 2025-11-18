"""Email scheduling service (polling version) for Google Sheets.

Cloud Scheduler triggers this (via Cloud Run) every N minutes. We poll a Google Sheet
to find rows whose Next Email At is due, send the appropriate email, then update the
four state columns: Next Email Type, Next Email At, Email Status, Overall Status.

High-level flow per run:
1. Fetch sheet values for identity + state ranges.
2. Build in-memory row objects.
3. Filter rows that are due (next_email_at <= now UTC) and not already sent (idempotency check).
4. For each due row: send email, compute next transition, stage update.
5. Batch write updates back to the sheet.
6. Emit structured summary (counts, failures).

Idempotency: Email Status cell stores a token pattern:
    <email_type>|<planned_at_iso>|<result>|<sent_at_iso>|<attempt>
Before sending we verify no existing successful token with same (<email_type>, <planned_at_iso>).

Environment Variables (expected):
    SHEET_ID               -> Google Sheet ID
    IDENTITY_RANGE         -> Range for identity columns (e.g. 'Sheet1!A:P')
    STATE_RANGE            -> Range for last four state columns (e.g. 'Sheet1!Q:T')
    ENABLE_SENDING         -> 'true' or 'false' (dry-run if false)
    GMAIL_SENDER           -> Optional sender identity
    DEFAULT_TIMEZONE       -> Fallback timezone (e.g. 'UTC')

Dependencies (see requirements.txt):
    google-api-python-client, google-auth, google-auth-httplib2, google-auth-oauthlib

NOTE: Actual Gmail sending is delegated to existing tool functions (e.g., welcome_mail) or
a future unified send function. Placeholder send_email() provided below for integration.
"""
from __future__ import annotations

import os
import time
import json
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
import google.auth

# Transition definitions: map current email_type to (next_email_type, delta_timedelta)
TRANSITIONS: Dict[str, Tuple[str, timedelta]] = {
    'welcome': ('compliance_reminder', timedelta(days=3)),
    'compliance_reminder': ('password_setup', timedelta(days=2)),
    'password_setup': ('hardware_followup', timedelta(days=2)),
    # Terminal stage: hardware_followup -> None
}

TERMINAL_TYPES = {'hardware_followup'}
ALLOWED_EMAIL_TYPES = set(TRANSITIONS.keys()) | TERMINAL_TYPES

@dataclass
class RowState:
    row_index: int               # 1-based sheet row number
    identity: Dict[str, Any]     # Arbitrary identity data (name, email, etc.)
    next_email_type: Optional[str]
    next_email_at: Optional[datetime]
    email_status: str            # Raw status cell
    overall_status: str          # Raw overall status cell

    def is_due(self, now: datetime) -> bool:
        if not self.next_email_type or not self.next_email_at:
            return False
        return self.next_email_at <= now

    def already_sent(self) -> bool:
        # Basic idempotency: a successful token contains '|sent|' marker after type & planned time.
        if not self.email_status:
            return False
        parts = self.email_status.split('|')
        if len(parts) < 3:
            return False
        email_type, planned_at_iso, result = parts[0], parts[1], parts[2]
        if result == 'sent' and email_type == (self.next_email_type or '') and planned_at_iso == iso_or_empty(self.next_email_at):
            return True
        return False

def iso_or_empty(dt: Optional[datetime]) -> str:
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ') if dt else ''

def _load_credentials() -> service_account.Credentials:
    """Load credentials.
    Prefer application default credentials (workload identity) when GOOGLE_APPLICATION_CREDENTIALS
    is not set, so we can avoid embedding key files in Cloud Run.
    """
    key_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/gmail.send',
    ]
    if key_path and os.path.exists(key_path):
        return service_account.Credentials.from_service_account_file(key_path, scopes=scopes)
    # Fallback to ADC
    creds, _ = google.auth.default(scopes=scopes)
    return creds

def _build_sheets_service(creds) -> Any:
    return build('sheets', 'v4', credentials=creds, cache_discovery=False)

def fetch_sheet_values(svc, sheet_id: str, ranges: List[str]) -> Dict[str, List[List[Any]]]:
    request = svc.spreadsheets().values().batchGet(spreadsheetId=sheet_id, ranges=ranges, majorDimension='ROWS')
    response = request.execute()
    data = {}
    for rng, value_range in zip(ranges, response.get('valueRanges', [])):
        data[rng] = value_range.get('values', [])
    return data

def parse_datetime(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    raw = raw.strip()
    # Accept ISO8601 (with or without timezone Z) or fallback to '%Y-%m-%d %H:%M:%S UTC'
    try_formats = [
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%d %H:%M:%S UTC',
        '%Y-%m-%d %H:%M:%S',
    ]
    for fmt in try_formats:
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None

def build_rows(identity_values: List[List[Any]], state_values: List[List[Any]]) -> List[RowState]:
    rows: List[RowState] = []
    header_offset = 1  # assume both ranges include header row at index 0
    # Align by physical row number; identity/state ranges should cover same set of rows.
    for i in range(1, max(len(identity_values), len(state_values))):
        ident_row = identity_values[i] if i < len(identity_values) else []
        state_row = state_values[i] if i < len(state_values) else []
        # Identity extraction (example: adapt to actual columns)
        identity = {
            'name': safe_cell(ident_row, 0),
            'email': safe_cell(ident_row, 1),
            'workorder_id': safe_cell(ident_row, 2),
            'location': safe_cell(ident_row, 3),
            'timezone': safe_cell(ident_row, 4),
        }
        next_email_type = safe_cell(state_row, 0) or None
        next_email_at_raw = safe_cell(state_row, 1)
        next_email_at = parse_datetime(next_email_at_raw) if next_email_at_raw else None
        email_status = safe_cell(state_row, 2)
        overall_status = safe_cell(state_row, 3)
        row_state = RowState(
            row_index=i + header_offset,
            identity=identity,
            next_email_type=next_email_type,
            next_email_at=next_email_at,
            email_status=email_status,
            overall_status=overall_status,
        )
        rows.append(row_state)
    return rows

def safe_cell(row: List[Any], idx: int) -> str:
    if idx < len(row) and row[idx] is not None:
        return str(row[idx]).strip()
    return ''

def compute_next(current_type: str, identity: Dict[str, Any]) -> Tuple[Optional[str], Optional[datetime]]:
    if current_type in TERMINAL_TYPES:
        return None, None
    nxt = TRANSITIONS.get(current_type)
    if not nxt:
        return None, None
    next_type, delta = nxt
    next_at = datetime.now(timezone.utc) + delta
    return next_type, next_at

def send_email(email_type: str, identity: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder sending logic. Integrate actual Gmail / template dispatch here.
    Return structure: {'success': bool, 'transport_id': str | None, 'error': str | None}
    """
    # TODO: integrate with existing welcome_mail and other template functions.
    # For now simulate success.
    return {'success': True, 'transport_id': f"mock-{email_type}-{int(time.time())}", 'error': None}

def batch_write_updates(svc, sheet_id: str, state_range: str, rows: List[RowState], updates: Dict[int, RowState]) -> None:
    # Reconstruct state values; only rows in updates replaced.
    existing = svc.spreadsheets().values().get(spreadsheetId=sheet_id, range=state_range).execute().get('values', [])
    # Ensure existing has header; pad missing rows
    max_row = max(updates.keys(), default=0)
    while len(existing) <= max_row:
        existing.append(['', '', '', ''])
    for idx, state in updates.items():
        # idx here is 1-based row number; convert to index within state range: row_index-1
        range_idx = idx - 1
        if range_idx == 0:  # header row skip
            continue
        existing[range_idx] = [
            state.next_email_type or '',
            iso_or_empty(state.next_email_at),
            state.email_status,
            state.overall_status,
        ]
    body = {'values': existing}
    svc.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=state_range,
        valueInputOption='RAW',
        body=body
    ).execute()

def build_overall_status(rs: RowState) -> str:
    # Simple summary; expand with counters/history persistence as needed.
    sent_marker = 'sent' if rs.already_sent() else 'pending'
    return f"{rs.next_email_type or 'none'}:{sent_marker}|next={iso_or_empty(rs.next_email_at)}"

def process_run(now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    sheet_id = os.environ['SHEET_ID']
    identity_range = os.environ.get('IDENTITY_RANGE', 'Sheet1!A:P')
    state_range = os.environ.get('STATE_RANGE', 'Sheet1!Q:T')
    enable_sending = os.environ.get('ENABLE_SENDING', 'false').lower() == 'true'

    creds = _load_credentials()
    svc = _build_sheets_service(creds)

    data = fetch_sheet_values(svc, sheet_id, [identity_range, state_range])
    identity_values = data.get(identity_range, [])
    state_values = data.get(state_range, [])

    rows = build_rows(identity_values, state_values)
    due_rows = [r for r in rows if r.is_due(now) and not r.already_sent() and r.next_email_type in ALLOWED_EMAIL_TYPES]

    updates: Dict[int, RowState] = {}
    successes: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []

    for r in due_rows:
        if not r.identity.get('email'):
            failures.append({'row': r.row_index, 'email_type': r.next_email_type, 'error': 'missing email'})
            continue
        if not enable_sending:
            # Dry-run marking
            r.email_status = f"{r.next_email_type}|{iso_or_empty(r.next_email_at)}|dry_run|{iso_or_empty(datetime.now(timezone.utc))}|0"
            r.overall_status = build_overall_status(r)
            updates[r.row_index] = r
            successes.append({'row': r.row_index, 'email_type': r.next_email_type, 'transport_id': None, 'dry_run': True})
            continue
        result = send_email(r.next_email_type, r.identity)
        if result['success']:
            r.email_status = f"{r.next_email_type}|{iso_or_empty(r.next_email_at)}|sent|{iso_or_empty(datetime.now(timezone.utc))}|1"
            next_type, next_at = compute_next(r.next_email_type, r.identity)
            r.next_email_type = next_type
            r.next_email_at = next_at
            r.overall_status = build_overall_status(r)
            updates[r.row_index] = r
            successes.append({'row': r.row_index, 'email_type': r.next_email_type, 'transport_id': result['transport_id']})
        else:
            r.email_status = f"{r.next_email_type}|{iso_or_empty(r.next_email_at)}|error:{result['error']}|{iso_or_empty(datetime.now(timezone.utc))}|1"
            # Backoff: retry after 30 minutes
            r.next_email_at = datetime.now(timezone.utc) + timedelta(minutes=30)
            r.overall_status = build_overall_status(r)
            updates[r.row_index] = r
            failures.append({'row': r.row_index, 'email_type': r.next_email_type, 'error': result['error']})

    if updates:
        batch_write_updates(svc, sheet_id, state_range, rows, updates)

    return {
        'timestamp': iso_or_empty(now),
        'total_rows': len(rows),
        'due_rows': len(due_rows),
        'updated_rows': len(updates),
        'successes': successes,
        'failures': failures,
        'dry_run': not enable_sending,
    }

def main():  # Entry point for Cloud Run
    summary = process_run()
    print(json.dumps(summary))

if __name__ == '__main__':  # Local manual invocation
    print(json.dumps(process_run(), indent=2))

"""Polling email scheduler for Google Sheets.

This module implements the Cloud Scheduler + Cloud Run polling approach.

Polling = periodically (e.g. every 5 minutes) fetching the sheet state and
deciding which rows are due for an email based on the last four columns:
  - Next Email Type (COLUMN_NEXT_EMAIL_TYPE)
  - Next Email At   (COLUMN_NEXT_EMAIL_AT)  -> ISO 8601 UTC string
  - Email Status    (COLUMN_EMAIL_STATUS)   -> last action details
  - Overall Status  (COLUMN_OVERALL_STATUS) -> aggregate pipeline summary

High-level algorithm per invocation:
1. Fetch sheet ranges (identity columns + last four state columns).
2. Parse rows into structured objects.
3. Filter rows where next_email_at <= now and not already processed.
4. For each due row:
     a. Send appropriate email via existing tool function.
     b. Compute next stage (type + timestamp) or mark complete.
     c. Update Email Status & Overall Status strings.
5. Batch write updates back to the sheet.

Idempotency: Email Status includes a token "type|planned_at"; before sending we
check if this token already appears; if so we skip to avoid duplicates.

Environment variables expected (inject via Cloud Run):
  SHEET_ID                -> Google Sheet ID
  SHEET_RANGE_IDENTITY    -> A:P (or earlier columns containing candidate data)
  SHEET_RANGE_STATE       -> Q:T (four scheduling columns)
  GMAIL_SENDER_OVERRIDE   -> optional override sender
  DRY_RUN                 -> if set to '1' skip actual sends

To deploy:
  1. Build container with this module included.
  2. Grant service account access to Sheets + Gmail scopes.
  3. Share the Sheet with service account email.
  4. Create Cloud Scheduler job hitting /scheduler/run endpoint every 5 min.

Future extensions:
  - Replace polling with Cloud Tasks scheduling per row.
  - Mirror state to Firestore for richer queries.
"""

from __future__ import annotations

import os
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Dict

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

from ..welcome_mail import welcome_mail
from ..compliance_reminder import send_compliance_reminder  # optional
from ..password_setup_reminder import send_password_setup_reminder  # optional
from .tracker_schema import (
    COLUMN_NAME,
    COLUMN_EMAIL_ID,
    COLUMN_WORKORDER_ID,
    COLUMN_LOCATION,
    COLUMN_TIMEZONE,
    COLUMN_NEXT_EMAIL_TYPE,
    COLUMN_NEXT_EMAIL_AT,
    COLUMN_EMAIL_STATUS,
    COLUMN_OVERALL_STATUS,
    is_cell_filled,
)

STATE_RANGE_DEFAULT = os.getenv('SHEET_RANGE_STATE', 'Q:T')
IDENTITY_RANGE_DEFAULT = os.getenv('SHEET_RANGE_IDENTITY', 'A:P')

SHEET_ID = os.getenv('SHEET_ID')  # required
DRY_RUN = os.getenv('DRY_RUN', '0') == '1'

EMAIL_TYPES = {
    'welcome',
    'compliance_reminder',
    'password_setup_reminder',
    'complete',
}

TRANSITIONS: Dict[str, Tuple[Optional[str], int]] = {
    'welcome': ('compliance_reminder', 72),            # 3 days later
    'compliance_reminder': ('password_setup_reminder', 24),  # 1 day
    'password_setup_reminder': ('complete', 0),
}

@dataclass
class CandidateRow:
    row_number: int
    name: str
    email: str
    workorder_id: str
    location: str
    timezone_str: str
    next_email_type: str
    next_email_at: Optional[datetime]
    email_status: str
    overall_status: str
    raw_identity: List[str] = field(default_factory=list)
    raw_state: List[str] = field(default_factory=list)

    def idempotency_token(self) -> str:
        if not self.next_email_type or not self.next_email_at:
            return ''
        return f"{self.next_email_type}|{self.next_email_at.isoformat()}"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_credentials() -> service_account.Credentials:
    keyfile = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not keyfile or not os.path.exists(keyfile):
        raise RuntimeError('Service account key file missing for Sheets access.')
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/gmail.send',
    ]
    return service_account.Credentials.from_service_account_file(keyfile, scopes=scopes)


def _build_sheets_client():
    creds = _load_credentials()
    return build('sheets', 'v4', credentials=creds)


def fetch_sheet_values(sheet_id: str, identity_range: str, state_range: str) -> Tuple[List[List[str]], List[List[str]]]:
    """Batch fetch identity + state ranges from the Sheet."""
    svc = _build_sheets_client()
    try:
        resp = svc.spreadsheets().values().batchGet(
            spreadsheetId=sheet_id,
            ranges=[identity_range, state_range]
        ).execute()
    except HttpError as e:
        raise RuntimeError(f"Sheets API error: {e}")
    value_ranges = resp.get('valueRanges', [])
    if len(value_ranges) != 2:
        raise RuntimeError('Unexpected batchGet response structure.')
    identity_values = value_ranges[0].get('values', [])
    state_values = value_ranges[1].get('values', [])
    return identity_values, state_values


def parse_rows(identity_values: List[List[str]], state_values: List[List[str]]) -> List[CandidateRow]:
    """Merge identity + state arrays into CandidateRow objects. Assumes headers in first row of each range."""
    rows: List[CandidateRow] = []
    max_len = max(len(identity_values), len(state_values))
    for i in range(1, max_len):  # skip header (index 0)
        ident = identity_values[i] if i < len(identity_values) else []
        state = state_values[i] if i < len(state_values) else []
        row_number = i + 1
        name = ident[0] if len(ident) > 0 else ''
        email = ident[1] if len(ident) > 1 else ''
        workorder = ident[2] if len(ident) > 2 else ''
        location = ident[3] if len(ident) > 3 else ''
        timezone_str = ident[4] if len(ident) > 4 else 'UTC'
        next_email_type = state[0] if len(state) > 0 else ''
        next_email_at_raw = state[1] if len(state) > 1 else ''
        email_status = state[2] if len(state) > 2 else ''
        overall_status = state[3] if len(state) > 3 else ''

        dt_obj: Optional[datetime] = None
        if next_email_at_raw:
            try:
                dt_obj = datetime.fromisoformat(next_email_at_raw.replace('Z', '+00:00'))
            except Exception:
                dt_obj = None

        rows.append(CandidateRow(
            row_number=row_number,
            name=name,
            email=email,
            workorder_id=workorder,
            location=location,
            timezone_str=timezone_str,
            next_email_type=next_email_type,
            next_email_at=dt_obj,
            email_status=email_status,
            overall_status=overall_status,
            raw_identity=ident,
            raw_state=state,
        ))
    return rows


def is_due(row: CandidateRow, now: datetime) -> bool:
    if not row.email or not row.next_email_type or row.next_email_type not in EMAIL_TYPES:
        return False
    if not row.next_email_at:
        return False
    if row.next_email_type == 'complete':
        return False
    token = row.idempotency_token()
    if token and token in row.email_status:
        return False
    return row.next_email_at <= now


def _send_email(row: CandidateRow) -> Tuple[bool, str]:
    """Dispatch to appropriate email sender based on next_email_type."""
    if DRY_RUN:
        return True, '[DRY RUN] Skipped actual send.'
    try:
        typ = row.next_email_type
        if typ == 'welcome':
            res = welcome_mail(Candidate_Name=row.name, Location=row.location, candidateEmailID=row.email)
            ok = res.get('response') == 'Welcome Mail Sent'
            return ok, json.dumps(res)
        elif typ == 'compliance_reminder':
            result = send_compliance_reminder(candidate_name=row.name, deadline=_utcnow(), recipient_email=row.email, dry_run=False)
            ok = '✅' in result
            return ok, result
        elif typ == 'password_setup_reminder':
            result = send_password_setup_reminder(candidate_name=row.name, worker_id=row.workorder_id, appointment_time=_utcnow() + timedelta(hours=1), recipient_email=row.email, dry_run=False)
            ok = '✅' in result
            return ok, result
        else:
            return False, f'Unknown email type: {typ}'
    except Exception as e:
        return False, f'Exception: {e}'


def compute_next(row: CandidateRow, now: datetime, send_success: bool) -> Tuple[str, Optional[datetime]]:
    if not send_success:
        # retry same type in 2 hours
        return row.next_email_type, now + timedelta(hours=2)
    nxt, delta = TRANSITIONS.get(row.next_email_type, (None, 0))
    if not nxt:
        return 'complete', None
    if nxt == 'complete':
        return 'complete', None
    next_at = now + timedelta(hours=delta)
    return nxt, next_at


def format_status(row: CandidateRow, now: datetime, send_success: bool, detail: str) -> Tuple[str, str]:
    token = row.idempotency_token()
    outcome = 'sent' if send_success else 'failed'
    email_status = f"{token}|{outcome}|{now.isoformat()}"
    if detail:
        email_status += f"|{detail[:200]}"  # truncate detail
    overall_status = f"{row.next_email_type}->{outcome} at {now.strftime('%Y-%m-%d %H:%M')}"
    return email_status, overall_status


def build_write_requests(due_rows: List[CandidateRow]) -> List[Dict]:
    values = []
    ranges = []
    for r in due_rows:
        row_range = f"Q{r.row_number}:T{r.row_number}"  # assumes Q:T are the 4 state columns
        ranges.append(row_range)
        next_at_str = r.next_email_at.isoformat() if r.next_email_at else ''
        values.append([r.next_email_type, next_at_str, r.email_status, r.overall_status])
    return [{'range': rng, 'values': [vals]} for rng, vals in zip(ranges, values)]


def write_updates(sheet_id: str, data: List[Dict]) -> None:
    if not data:
        return
    svc = _build_sheets_client()
    body = {'valueInputOption': 'RAW', 'data': data}
    svc.spreadsheets().values().batchUpdate(spreadsheetId=sheet_id, body=body).execute()


def process_poll_cycle() -> Dict:
    if not SHEET_ID:
        return {'error': 'SHEET_ID missing'}
    now = _utcnow()
    identity_values, state_values = fetch_sheet_values(SHEET_ID, IDENTITY_RANGE_DEFAULT, STATE_RANGE_DEFAULT)
    rows = parse_rows(identity_values, state_values)
    due = [r for r in rows if is_due(r, now)]
    updated: List[CandidateRow] = []
    for r in due:
        ok, detail = _send_email(r)
        email_status, overall_status = format_status(r, now, ok, detail)
        next_type, next_at = compute_next(r, now, ok)
        r.email_status = email_status
        r.overall_status = overall_status
        r.next_email_type = next_type
        r.next_email_at = next_at
        updated.append(r)
    write_requests = build_write_requests(updated)
    if not DRY_RUN:
        write_updates(SHEET_ID, write_requests)
    return {
        'now': now.isoformat(),
        'checked': len(rows),
        'due': len(due),
        'updated': len(updated),
        'dry_run': DRY_RUN,
    }


def main():
    result = process_poll_cycle()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
