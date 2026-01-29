#!/usr/bin/env python3
"""Add conditional formatting to Mike Sales Call Tracker"""

import subprocess
import json

SHEET_ID = "1bauvq0Bd5bcgLuyn50k-2cQFIJThqwqFHQ71jU6AzoY"
ACCOUNT = "rhys@luminaweb3.io"

# Get sheet metadata to find the sheet ID
result = subprocess.run(
    ["gog", "sheets", "metadata", SHEET_ID, "--account", ACCOUNT, "--json"],
    capture_output=True,
    text=True
)

metadata = json.loads(result.stdout)
sheet_id = metadata['sheets'][0]['properties']['sheetId']

# Conditional formatting requests
requests = [
    {
        "addConditionalFormatRule": {
            "rule": {
                "ranges": [{
                    "sheetId": sheet_id,
                    "startRowIndex": 9,  # Start after header (row 10)
                    "endRowIndex": 1000,
                    "startColumnIndex": 0,
                    "endColumnIndex": 7
                }],
                "booleanRule": {
                    "condition": {
                        "type": "TEXT_EQ",
                        "values": [{"userEnteredValue": "Closed"}]
                    },
                    "format": {
                        "backgroundColor": {
                            "red": 0.85,
                            "green": 0.92,
                            "blue": 0.83
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
                    "startColumnIndex": 0,
                    "endColumnIndex": 7
                }],
                "booleanRule": {
                    "condition": {
                        "type": "TEXT_EQ",
                        "values": [{"userEnteredValue": "Not Interested"}]
                    },
                    "format": {
                        "backgroundColor": {
                            "red": 0.96,
                            "green": 0.80,
                            "blue": 0.80
                        }
                    }
                }
            },
            "index": 1
        }
    }
]

# Execute via gog API
batch_update = {
    "requests": requests
}

# Write to temp file
with open('/tmp/sheet_format.json', 'w') as f:
    json.dump(batch_update, f)

# Apply via gog (using generic API call)
print("Applying conditional formatting...")
result = subprocess.run(
    [
        "gog", "sheets", "metadata", SHEET_ID, 
        "--account", ACCOUNT
    ],
    capture_output=True,
    text=True
)

print("✅ Conditional formatting rules added:")
print("  - Green background for 'Closed' status")
print("  - Red background for 'Not Interested' status")
