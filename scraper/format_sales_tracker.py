#!/usr/bin/env python3
"""Add conditional formatting to Mike Sales Call Tracker using Google Sheets API"""

import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SHEET_ID = "1bauvq0Bd5bcgLuyn50k-2cQFIJThqwqFHQ71jU6AzoY"
ACCOUNT = "rhys@luminaweb3.io"

# gog stores tokens in ~/.config/gog/tokens/
GOG_CONFIG = os.path.expanduser("~/.config/gog")
TOKEN_FILE = f"{GOG_CONFIG}/tokens/default/{ACCOUNT}/oauth.json"

print(f"Looking for token at: {TOKEN_FILE}")

# Load credentials from gog's token storage
if not os.path.exists(TOKEN_FILE):
    print("❌ Token file not found. Run: gog auth add")
    exit(1)

with open(TOKEN_FILE, 'r') as f:
    token_data = json.load(f)

creds = Credentials(
    token=token_data.get('access_token'),
    refresh_token=token_data.get('refresh_token'),
    token_uri='https://oauth2.googleapis.com/token',
    client_id=token_data.get('client_id'),
    client_secret=token_data.get('client_secret'),
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)

# Build Sheets API service
service = build('sheets', 'v4', credentials=creds)

# Get sheet metadata to find sheetId
spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
sheet_id = spreadsheet['sheets'][0]['properties']['sheetId']

print(f"Found sheet ID: {sheet_id}")

# Conditional formatting requests
requests = [
    {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{
                    "sheetId": sheet_id,
                    "startRowIndex": 9,  # Row 10 onwards (after header)
                    "endRowIndex": 1000,
                    "startColumnIndex": 4,  # Column E (Status)
                    "endColumnIndex": 5
                }],
                "booleanRule": {
                    "condition": {
                        "type": "TEXT_EQ",
                        "values": [{"userEnteredValue": "Closed"}]
                    },
                    "format": {
                        "backgroundColor": {
                            "red": 0.72,
                            "green": 0.88,
                            "blue": 0.73
                        }
                    }
                }
            },
            "index": 0
        }
    },
    {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{
                    "sheetId": sheet_id,
                    "startRowIndex": 9,
                    "endRowIndex": 1000,
                    "startColumnIndex": 4,  # Column E (Status)
                    "endColumnIndex": 5
                }],
                "booleanRule": {
                    "condition": {
                        "type": "TEXT_EQ",
                        "values": [{"userEnteredValue": "Not Interested"}]
                    },
                    "format": {
                        "backgroundColor": {
                            "red": 0.96,
                            "green": 0.73,
                            "blue": 0.73
                        }
                    }
                }
            },
            "index": 1
        }
    }
]

# Apply conditional formatting
print("Applying conditional formatting...")
body = {"requests": requests}
response = service.spreadsheets().batchUpdate(
    spreadsheetId=SHEET_ID,
    body=body
).execute()

print(f"✅ Added {len(response.get('replies', []))} formatting rules:")
print("  🟢 Green highlight for 'Closed' status")
print("  🔴 Red highlight for 'Not Interested' status")
print(f"\nView sheet: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
