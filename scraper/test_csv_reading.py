"""Test script to verify CSV reading works correctly"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from telegram_bot import read_leads_csv

def test_read():
    leads = read_leads_csv()
    
    print(f"\n{'='*60}")
    print(f"Found {len(leads)} leads to process:")
    print(f"{'='*60}\n")
    
    for i, lead in enumerate(leads, 1):
        print(f"{i}. {lead.get('name')} ({lead.get('symbol')})")
        print(f"   Telegram: {lead.get('telegram')}")
        print(f"   Status: {lead.get('dm_status', 'not processed')}")
        print()
    
    print(f"{'='*60}")
    print(f"Ready to process {len(leads)} leads")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_read()
