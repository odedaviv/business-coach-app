"""
Unified Google auth — reads credentials.json from file OR from
GOOGLE_CREDENTIALS_JSON env var (base64-encoded JSON, for Railway/cloud).
"""
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import base64
import tempfile

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

_gc = None


def get_gc():
    global _gc
    if _gc is not None:
        return _gc

    creds_json_b64 = os.getenv('GOOGLE_CREDENTIALS_JSON', '')
    creds_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')

    if creds_json_b64:
        # Railway / cloud: credentials stored as base64 env var
        creds_data = json.loads(base64.b64decode(creds_json_b64).decode())
        creds = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
    elif os.path.exists(creds_file):
        # Local: read from file
        creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    else:
        raise RuntimeError(
            'Google credentials חסרים — הוסף credentials.json או GOOGLE_CREDENTIALS_JSON ל-.env'
        )

    _gc = gspread.authorize(creds)
    return _gc
