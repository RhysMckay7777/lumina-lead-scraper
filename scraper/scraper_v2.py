"""
Lead Scraper v2 - DEXScreener URL-based workflow
Workflow: Scrape DEXScreener URL → Join Telegram groups → Find admins → Send DMs
"""

import logging
import csv
import os
import time
from typing import List, Dict
from dexscreener_scraper_fixed import scrape_dexscreener_url
from telegram_lead_bot import TelegramLeadBot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LeadScraperV2:
    """Main lead scraper orchestrator"""
    
    def __init__(self, api_id: int, api_hash: str, phone: str):
        """Initialize scraper with Telegram credentials"""
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.telegram_bot = None
        self.scraped_tokens = []
        
    def run(self, dexscreener_url: str, output_csv: str = "leads.csv"):
        """
        Run full scraping workflow
        
        Args:
            dexscreener_url: DEXScreener filtered URL
            output_csv: Output CSV file for leads
        """
        logger.info("🚀 Starting Lead Scraper v2")
        logger.info(f"DEXScreener URL: {dexscreener_url}")
        
        # Step 1: Scrape tokens from DEXScreener
        logger.info("\n📊 STEP 1: Scraping DEXScreener...")
        # Limit to 150 tokens by default (can be adjusted)
        max_tokens = 150
        logger.info(f"Max tokens to scrape: {max_tokens}")
        self.scraped_tokens = scrape_dexscreener_url(dexscreener_url, headless=True, max_tokens=max_tokens)
        
        if not self.scraped_tokens:
            logger.error("❌ No tokens found. Check the URL and try again.")
            return
        
        logger.info(f"✅ Found {len(self.scraped_tokens)} tokens")
        
        # Filter tokens with Telegram groups
        tokens_with_telegram = [t for t in self.scraped_tokens if t.get('telegram')]
        logger.info(f"📱 {len(tokens_with_telegram)} tokens have Telegram groups")
        
        # Step 2: Save scraped data to CSV
        logger.info(f"\n💾 STEP 2: Saving to {output_csv}...")
        self._save_to_csv(output_csv)
        
        # Step 3: Initialize Telegram bot
        logger.info("\n🤖 STEP 3: Initializing Telegram bot...")
        self.telegram_bot = TelegramLeadBot(
            api_id=self.api_id,
            api_hash=self.api_hash,
            phone=self.phone
        )
        
        # Step 4: Join Telegram groups
        logger.info("\n👥 STEP 4: Joining Telegram groups...")
        joined_groups = self.telegram_bot.join_groups(tokens_with_telegram)
        logger.info(f"✅ Joined {len(joined_groups)} groups")
        
        # Step 5: Find admins in each group
        logger.info("\n🔍 STEP 5: Finding admins...")
        admins_found = self.telegram_bot.find_admins(joined_groups)
        logger.info(f"✅ Found {len(admins_found)} admins")
        
        # Step 6: Send DMs to admins
        logger.info("\n💬 STEP 6: Sending DMs...")
        dm_template = self._get_dm_template()
        sent_count = self.telegram_bot.send_dms(admins_found, dm_template)
        logger.info(f"✅ Sent {sent_count} DMs")
        
        # Step 7: Summary
        logger.info("\n" + "="*60)
        logger.info("📊 SCRAPING COMPLETE - SUMMARY")
        logger.info("="*60)
        logger.info(f"Tokens scraped:       {len(self.scraped_tokens)}")
        logger.info(f"With Telegram:        {len(tokens_with_telegram)}")
        logger.info(f"Groups joined:        {len(joined_groups)}")
        logger.info(f"Admins found:         {len(admins_found)}")
        logger.info(f"DMs sent:             {sent_count}")
        logger.info(f"Output CSV:           {output_csv}")
        logger.info("="*60)
        
    def _save_to_csv(self, filename: str):
        """Save scraped tokens to CSV"""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                if not self.scraped_tokens:
                    logger.warning("No tokens to save")
                    return
                
                fieldnames = ['name', 'symbol', 'address', 'telegram', 'twitter', 'website']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for token in self.scraped_tokens:
                    writer.writerow({
                        'name': token.get('name', ''),
                        'symbol': token.get('symbol', ''),
                        'address': token.get('address', ''),
                        'telegram': token.get('telegram', ''),
                        'twitter': token.get('twitter', ''),
                        'website': token.get('website', '')
                    })
            
            logger.info(f"✅ Saved {len(self.scraped_tokens)} tokens to {filename}")
        except Exception as e:
            logger.error(f"Error saving CSV: {e}")
    
    def _get_dm_template(self) -> str:
        """Get DM template (can be customized)"""
        return """Hey {name}!

Came across {project} - looks interesting.

We've helped similar Solana projects grow their communities and get listed on tier-1 exchanges.

Quick 10-min chat to discuss growth strategies?

Rhys
Lumina Web3 | @LuminaWeb3"""


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Lead Scraper v2 - DEXScreener URL-based')
    parser.add_argument('url', help='DEXScreener filtered URL')
    parser.add_argument('--output', default='leads.csv', help='Output CSV file')
    parser.add_argument('--api-id', type=int, required=True, help='Telegram API ID')
    parser.add_argument('--api-hash', required=True, help='Telegram API hash')
    parser.add_argument('--phone', required=True, help='Telegram phone number')
    
    args = parser.parse_args()
    
    scraper = LeadScraperV2(
        api_id=args.api_id,
        api_hash=args.api_hash,
        phone=args.phone
    )
    
    scraper.run(args.url, args.output)


if __name__ == "__main__":
    main()
