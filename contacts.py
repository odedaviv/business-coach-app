"""
Reads client contact list from a Google Sheet tab named 'לקוחות'.
Expected columns (A-G):
  A: שם לקוח
  B: טלפון
  C: אימייל
  D: יום פגישה (ראשון/שני/...)
  E: שעת פגישה (HH:MM)
  F: הערות
  G: Google Sheets ID (ID של גיליון המעקב האישי)
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import urllib.parse
import os
from gauth import get_gc as _get_gc

CONTACTS_TAB = 'לקוחות'
CONTACTS_HEADERS = ['שם לקוח', 'טלפון', 'אימייל', 'יום פגישה', 'שעת פגישה', 'הערות', 'Google Sheets ID']


def get_contacts_sheet(sheets_id):
    gc = _get_gc()
    spreadsheet = gc.open_by_key(sheets_id)
    try:
        return spreadsheet.worksheet(CONTACTS_TAB)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=CONTACTS_TAB, rows=200, cols=6)
        ws.append_row(CONTACTS_HEADERS)
        ws.format('A1:F1', {'textFormat': {'bold': True},
                             'backgroundColor': {'red': 0.18, 'green': 0.33, 'blue': 0.59}})
        return ws


def extract_sheets_id(url_or_id):
    """
    Extract spreadsheet ID (and optional gid) from a full URL.
    Returns 'SPREADSHEET_ID:GID' if gid found, else just 'SPREADSHEET_ID'.
    """
    import re
    if not url_or_id:
        return ''
    url_or_id = url_or_id.strip()
    if 'spreadsheets/d/' in url_or_id:
        part = url_or_id.split('spreadsheets/d/')[1]
        spreadsheet_id = part.split('/')[0].split('?')[0]
        match = re.search(r'gid=(\d+)', url_or_id)
        if match:
            return f"{spreadsheet_id}:{match.group(1)}"
        return spreadsheet_id
    return url_or_id


def read_contacts(sheets_id):
    ws = get_contacts_sheet(sheets_id)
    all_values = ws.get_all_values()
    if len(all_values) < 2:
        return []
    headers = all_values[0]
    # Ensure we have 7 columns (add missing headers)
    while len(headers) < 7:
        headers.append('')
    results = []
    for row in all_values[1:]:
        while len(row) < 7:
            row.append('')
        name = row[0].strip()
        if not name:
            continue
        results.append({
            'שם לקוח': name,
            'טלפון': row[1],
            'אימייל': row[2],
            'יום פגישה': row[3],
            'שעת פגישה': row[4],
            'הערות': row[5],
            'Google Sheets ID': extract_sheets_id(row[6]),
        })
    return results


def save_contact(sheets_id, contact):
    ws = get_contacts_sheet(sheets_id)
    ws.append_row([
        contact.get('name', ''),
        contact.get('phone', ''),
        contact.get('email', ''),
        contact.get('meeting_day', ''),
        contact.get('meeting_time', ''),
        contact.get('notes', ''),
        extract_sheets_id(contact.get('sheets_id', '')),
    ])


def update_contact(sheets_id, row_index, contact):
    """row_index is 1-based (header=1, first data row=2)"""
    ws = get_contacts_sheet(sheets_id)
    ws.update(f'A{row_index}:G{row_index}', [[
        contact.get('name', ''),
        contact.get('phone', ''),
        contact.get('email', ''),
        contact.get('meeting_day', ''),
        contact.get('meeting_time', ''),
        contact.get('notes', ''),
        extract_sheets_id(contact.get('sheets_id', '')),
    ]])


# ---------- WhatsApp ----------

def whatsapp_link(phone, message):
    """Generate wa.me link that opens WhatsApp with pre-written message."""
    # Normalize Israeli number
    phone = phone.strip().replace('-', '').replace(' ', '')
    if phone.startswith('0'):
        phone = '972' + phone[1:]
    elif not phone.startswith('972'):
        phone = '972' + phone
    return f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"


# ---------- Email ----------

def send_email(to_email, subject, body_html):
    user = os.getenv('GMAIL_USER', '')
    password = os.getenv('GMAIL_APP_PASSWORD', '')
    if not user or not password:
        raise RuntimeError('GMAIL_USER ו-GMAIL_APP_PASSWORD לא מוגדרים ב-.env')

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = user
    msg['To'] = to_email
    msg.attach(MIMEText(body_html, 'html', 'utf-8'))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
        server.login(user, password)
        server.sendmail(user, to_email, msg.as_string())
