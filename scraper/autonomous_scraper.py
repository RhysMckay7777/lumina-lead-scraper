#!/usr/bin/env python3
"""
Autonomous Scraper Daemon
- Runs 24/7 as background service
- Monitors DEXScreener for new tokens
- Auto-processes: index check → join → message
- Respects rate limits and active hours
"""

import asyncio
import logging
import os
import sys
import signal
import time
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import traceback

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import LeadDatabase
from dex_api_scraper import DEXScreenerAPI  # Use API instead of web scraper
from google_index_checker import GoogleIndexChecker
from telegram_automator import TelegramAutomator

# Setup logging
def setup_logging(log_dir: str, log_level: str = "INFO"):
    """Setup logging to file and console"""
    log_dir = os.path.expanduser(log_dir)
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"scraper_{datetime.now().strftime('%Y-%m-%d')}.log")
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(getattr(logging, log_level))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, log_level))
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return logging.getLogger(__name__)


class AutonomousScraper:
    """Autonomous 24/7 scraper daemon"""
    
    def __init__(self, config_path: str = None):
        """
        Initialize the autonomous scraper
        
        Args:
            config_path: Path to config.yaml
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        
        self.config = self._load_config(config_path)
        
        # Setup logging
        log_dir = self.config.get('logging', {}).get('directory', '~/clawd/scraper-logs')
        log_level = self.config.get('logging', {}).get('log_level', 'INFO')
        self.logger = setup_logging(log_dir, log_level)
        
        # Initialize components
        self.db = LeadDatabase(self.config.get('database', {}).get('path'))
        
        # Telegram config
        tg_config = self.config.get('telegram', {}).get('credentials', {})
        tg_limits = self.config.get('telegram', {}).get('rate_limits', {})
        
        self.telegram = TelegramAutomator(
            api_id=tg_config.get('api_id'),
            api_hash=tg_config.get('api_hash'),
            phone=tg_config.get('phone'),
            session_file=tg_config.get('session_file', 'lumina_session'),
            join_delay=tg_limits.get('join_delay_seconds', 30),
            dm_delay=tg_limits.get('dm_delay_seconds', 60),
            max_joins_per_hour=tg_limits.get('max_joins_per_hour', 10),
            max_dms_per_hour=tg_limits.get('max_dms_per_hour', 5)
        )
        
        self.index_checker = GoogleIndexChecker(
            delay_seconds=self.config.get('google_index', {}).get('check_delay_seconds', 5)
        )
        
        self.dex_scraper = DEXScreenerAPI()  # Use API instead of Selenium
        
        # Message template
        self.message_template = self.config.get('telegram', {}).get('message_template', '')
        
        # Monitoring config
        self.monitoring_config = self.config.get('monitoring', {})
        self.check_interval = self.monitoring_config.get('check_interval_minutes', 30) * 60
        
        # State
        self.running = False
        self.error_count = 0
        self.last_check_time = None
        
        # Signal handlers
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML"""
        config_path = os.path.expanduser(config_path)
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _handle_signal(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def _is_active_hours(self) -> bool:
        """Check if we're within active hours"""
        active_hours = self.monitoring_config.get('active_hours', {})
        if not active_hours:
            return True
        
        start = active_hours.get('start', 0)
        end = active_hours.get('end', 24)
        current_hour = datetime.now().hour
        
        if start <= end:
            return start <= current_hour < end
        else:
            # Wraps around midnight
            return current_hour >= start or current_hour < end
    
    async def run(self):
        """Main run loop"""
        self.running = True
        self.logger.info("="*60)
        self.logger.info("🚀 Autonomous Scraper Starting")
        self.logger.info("="*60)
        
        # Start Telegram client
        await self.telegram.start()
        
        try:
            while self.running:
                try:
                    # Check active hours
                    if not self._is_active_hours():
                        self.logger.info("Outside active hours, sleeping...")
                        await asyncio.sleep(300)  # Check every 5 min
                        continue
                    
                    # Run scraping cycle
                    await self._scrape_cycle()
                    
                    # Reset error count on success
                    self.error_count = 0
                    
                    # Wait for next cycle
                    self.logger.info(f"Sleeping for {self.check_interval // 60} minutes...")
                    await asyncio.sleep(self.check_interval)
                    
                except Exception as e:
                    self.error_count += 1
                    self.logger.error(f"Error in scrape cycle: {e}")
                    self.logger.error(traceback.format_exc())
                    
                    # Log to database
                    self.db.log_error('scrape_cycle', str(e), traceback.format_exc())
                    
                    # Pause if too many errors
                    max_errors = self.monitoring_config.get('max_errors_before_pause', 5)
                    if self.error_count >= max_errors:
                        pause_minutes = self.monitoring_config.get('error_pause_minutes', 60)
                        self.logger.warning(f"Too many errors, pausing for {pause_minutes} minutes")
                        await asyncio.sleep(pause_minutes * 60)
                        self.error_count = 0
                    else:
                        await asyncio.sleep(60)  # Short pause before retry
        
        finally:
            await self.telegram.stop()
            self.db.close()
            self.logger.info("Scraper stopped")
    
    async def _scrape_cycle(self):
        """Single scrape cycle"""
        self.logger.info("\n" + "="*60)
        self.logger.info(f"🔄 Starting scrape cycle at {datetime.now()}")
        self.logger.info("="*60)
        
        # Get URLs to monitor
        urls = self.config.get('dexscreener', {}).get('urls_to_monitor', [])
        if not urls:
            self.logger.warning("No URLs configured to monitor")
            return
        
        # Get filter config
        filters = self.config.get('dexscreener', {}).get('filters', {})
        scraping_config = self.config.get('dexscreener', {}).get('scraping', {})
        
        # Get existing addresses to skip
        skip_addresses = set()
        # We skip tokens we've already contacted
        for project in self.db.get_uncontacted_projects(limit=1000, only_unindexed=False):
            if project.get('contract_address'):
                skip_addresses.add(project['contract_address'])
        
        self.logger.info(f"Skipping {len(skip_addresses)} already-known addresses")
        
        # Scrape new tokens using API
        new_tokens = []
        
        # Determine chain from URLs
        chains = set()
        for url in urls:
            if 'solana' in url:
                chains.add('solana')
            elif 'ethereum' in url:
                chains.add('ethereum')
            elif 'base' in url:
                chains.add('base')
        
        if not chains:
            chains = {'solana'}  # Default to Solana
        
        for chain in chains:
            self.logger.info(f"\n📡 Scraping {chain} via API...")
            
            tokens = self.dex_scraper.scrape_with_filters(
                chain=chain,
                min_volume=filters.get('min_volume_24h', 10000),
                min_liquidity=filters.get('min_liquidity', 5000),
                max_age_hours=filters.get('max_age_hours', 168),
                limit=scraping_config.get('max_tokens_per_session', 100)
            )
            
            for token in tokens:
                if token.get('address') not in skip_addresses:
                    new_tokens.append(token)
                    skip_addresses.add(token['address'])
        
        self.logger.info(f"\n✅ Found {len(new_tokens)} new tokens")
        
        if not new_tokens:
            return
        
        # Add to database
        for token in new_tokens:
            self.db.add_project(token)
        
        # Process tokens with Telegram
        tokens_with_telegram = [t for t in new_tokens if t.get('telegram')]
        self.logger.info(f"📱 {len(tokens_with_telegram)} tokens have Telegram groups")
        
        # Check Google index for tokens with websites
        if self.config.get('google_index', {}).get('enabled', True):
            await self._check_indexes(new_tokens)
        
        # Process based on config
        only_unindexed = self.config.get('google_index', {}).get('only_target_unindexed', True)
        
        # Get tokens to process
        to_process = self.db.get_uncontacted_projects(
            limit=20,  # Limit per cycle
            only_unindexed=only_unindexed
        )
        
        self.logger.info(f"\n🎯 Processing {len(to_process)} tokens for outreach")
        
        for i, project in enumerate(to_process, 1):
            self.logger.info(f"\n[{i}/{len(to_process)}] Processing: {project.get('name')}")
            
            result = await self.telegram.process_project(
                project=project,
                message_template=self.message_template,
                db=self.db
            )
            
            if result['error']:
                self.logger.warning(f"  ⚠️ {result['error']}")
            else:
                self.logger.info(f"  ✅ Success: joined={result['joined']}, dm_sent={result['dm_sent']}")
            
            # Cooldown
            if result['dm_sent']:
                cooldown = self.monitoring_config.get('cooldown_after_dm_minutes', 15)
                self.logger.info(f"  ⏱️ Cooldown: {cooldown} minutes")
                await asyncio.sleep(cooldown * 60)
            elif result['joined']:
                cooldown = self.monitoring_config.get('cooldown_after_join_minutes', 5)
                await asyncio.sleep(cooldown * 60)
        
        # Log stats
        stats = self.telegram.get_stats()
        self.logger.info(f"\n📊 Session Stats: {stats}")
    
    async def _check_indexes(self, tokens: List[Dict]):
        """Check Google index for tokens with websites"""
        tokens_with_website = [t for t in tokens if t.get('website')]
        
        if not tokens_with_website:
            return
        
        self.logger.info(f"\n🔍 Checking Google index for {len(tokens_with_website)} websites...")
        
        for token in tokens_with_website:
            website = token.get('website')
            address = token.get('address')
            
            # Get project from DB
            project = self.db.get_project(contract_address=address)
            if not project:
                continue
            
            is_indexed, count = self.index_checker.check_indexed(website)
            
            if is_indexed is not None:
                self.db.update_index_status(project['id'], is_indexed)
                
                status = "✓ INDEXED" if is_indexed else "✗ NOT INDEXED"
                self.logger.info(f"  {token.get('name')}: {status}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Autonomous Lead Scraper Daemon')
    parser.add_argument('--config', '-c', default=None, help='Path to config.yaml')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    args = parser.parse_args()
    
    scraper = AutonomousScraper(config_path=args.config)
    
    if args.once:
        # Run single cycle
        asyncio.run(scraper._scrape_cycle())
    else:
        # Run daemon
        asyncio.run(scraper.run())


if __name__ == "__main__":
    main()
