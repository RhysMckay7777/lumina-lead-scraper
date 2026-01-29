"""Telegram automation using Telethon"""

import asyncio
import logging
import re
from typing import Optional, List, Dict
from datetime import datetime
import csv
import os

from telethon import TelegramClient, functions
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, PeerFloodError, UsernameInvalidError
from telethon.tl.types import User, Channel, Chat, ChannelParticipantsAdmins

import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self):
        self.client = TelegramClient(
            config.TELEGRAM_SESSION_FILE,
            config.TELEGRAM_API_ID,
            config.TELEGRAM_API_HASH
        )
        self.joins_count = 0
        self.dms_sent = 0
    
    async def start(self):
        """Start the Telegram client"""
        await self.client.start(phone=config.TELEGRAM_PHONE)
        logger.info("✓ Telegram client started")
        me = await self.client.get_me()
        logger.info(f"Logged in as: {me.first_name} (@{me.username})")
    
    async def stop(self):
        """Stop the Telegram client"""
        await self.client.disconnect()
        logger.info("Telegram client disconnected")
    
    def extract_telegram_username(self, url: str) -> Optional[str]:
        """Extract username from Telegram URL"""
        if not url:
            return None
        
        # Match patterns: t.me/username, https://t.me/username, @username
        patterns = [
            r't\.me/([a-zA-Z0-9_]+)',
            r'@([a-zA-Z0-9_]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def join_group(self, telegram_url: str) -> bool:
        """Join a Telegram group"""
        username = self.extract_telegram_username(telegram_url)
        if not username:
            logger.warning(f"Could not extract username from: {telegram_url}")
            return False
        
        try:
            # Check if we've hit the join limit
            if self.joins_count >= config.MAX_JOINS_PER_SESSION:
                logger.warning(f"⚠️  Hit max joins limit ({config.MAX_JOINS_PER_SESSION}). Stopping.")
                return False
            
            logger.info(f"Attempting to join: {username}")
            entity = await self.client.get_entity(username)
            
            # Check if already a member
            try:
                await self.client.get_participants(entity, limit=1)
                logger.info(f"Already a member of {username}")
            except:
                # Not a member, join now
                await self.client(functions.channels.JoinChannelRequest(entity))
                self.joins_count += 1
                logger.info(f"✓ Joined {username} ({self.joins_count}/{config.MAX_JOINS_PER_SESSION})")
                
                # Delay before next join
                logger.info(f"Waiting {config.JOIN_DELAY_SECONDS}s before next join...")
                await asyncio.sleep(config.JOIN_DELAY_SECONDS)
            
            return True
            
        except FloodWaitError as e:
            logger.error(f"⚠️  FloodWait: Must wait {e.seconds}s before joining again")
            return False
        except UsernameInvalidError:
            logger.error(f"Invalid username: {username}")
            return False
        except Exception as e:
            logger.error(f"Error joining {username}: {e}")
            return False
    
    async def get_group_admins(self, telegram_url: str) -> List[str]:
        """Get admin usernames from a group"""
        username = self.extract_telegram_username(telegram_url)
        if not username:
            return []
        
        try:
            entity = await self.client.get_entity(username)
            participants = await self.client.get_participants(entity, filter=ChannelParticipantsAdmins())
            
            admin_usernames = []
            for participant in participants:
                user = participant.participant
                # Skip bots and users without usernames
                if hasattr(user, 'user_id'):
                    user_entity = await self.client.get_entity(user.user_id)
                    if not user_entity.bot and user_entity.username:
                        admin_usernames.append(user_entity.username)
                        logger.info(f"  Admin found: @{user_entity.username}")
            
            return admin_usernames
            
        except Exception as e:
            logger.error(f"Error getting admins for {username}: {e}")
            return []
    
    async def send_dm(self, username: str, message: str) -> bool:
        """Send a DM to a user"""
        try:
            logger.info(f"Sending DM to @{username}")
            user = await self.client.get_entity(username)
            await self.client.send_message(user, message)
            self.dms_sent += 1
            logger.info(f"✓ DM sent to @{username}")
            
            # Delay before next DM
            logger.info(f"Waiting {config.DM_DELAY_SECONDS}s before next DM...")
            await asyncio.sleep(config.DM_DELAY_SECONDS)
            return True
            
        except UserPrivacyRestrictedError:
            logger.warning(f"⚠️  User @{username} has privacy settings that prevent DMs")
            return False
        except PeerFloodError:
            logger.error(f"⚠️  FLOOD ERROR: Too many requests. Account may be temporarily restricted.")
            return False
        except FloodWaitError as e:
            logger.error(f"⚠️  FloodWait: Must wait {e.seconds}s before sending more messages")
            return False
        except Exception as e:
            logger.error(f"Error sending DM to @{username}: {e}")
            return False


def read_leads_csv():
    """Read leads from CSV - supports both scraper format and processed format"""
    if not os.path.exists(config.CSV_FILE):
        logger.warning(f"CSV file not found: {config.CSV_FILE}")
        return []
    
    leads = []
    with open(config.CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip TEST entries
            if row.get('symbol') == 'TEST':
                continue
            
            # Skip if no telegram link
            telegram = row.get('telegram', '').strip()
            if not telegram or 'http' not in telegram:
                continue
            
            # Skip if already processed
            dm_status = row.get('dm_status', '').strip()
            if dm_status in ['dm_sent', 'dm_failed', 'no_admins_found']:
                logger.info(f"Skipping {row.get('symbol')} - already processed ({dm_status})")
                continue
            
            leads.append(row)
    
    return leads


def update_lead_in_csv(symbol: str, admin_username: Optional[str], dm_status: str):
    """Update a lead's status in the CSV"""
    if not os.path.exists(config.CSV_FILE):
        return
    
    # Read all rows
    rows = []
    with open(config.CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    # Ensure required columns exist
    if 'admin_username' not in fieldnames:
        fieldnames = list(fieldnames) + ['admin_username']
    if 'dm_status' not in fieldnames:
        fieldnames = list(fieldnames) + ['dm_status']
    if 'timestamp' not in fieldnames:
        fieldnames = list(fieldnames) + ['timestamp']
    
    # Update the matching row
    for row in rows:
        if row['symbol'] == symbol:
            row['admin_username'] = admin_username or ''
            row['dm_status'] = dm_status
            row['timestamp'] = datetime.now().isoformat()
    
    # Write back
    with open(config.CSV_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    logger.info(f"✓ Updated CSV for {symbol}: {dm_status}")


async def process_leads():
    """Process all leads from CSV"""
    leads = read_leads_csv()
    
    if not leads:
        logger.warning("No leads to process (all may be already processed or no valid Telegram links)")
        return
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Found {len(leads)} leads to process")
    logger.info(f"{'='*60}")
    
    bot = TelegramBot()
    await bot.start()
    
    try:
        for i, lead in enumerate(leads, 1):
            symbol = lead.get('symbol')
            name = lead.get('name')
            telegram = lead.get('telegram')
            
            logger.info(f"\n{'='*60}")
            logger.info(f"[{i}/{len(leads)}] Processing: {name} ({symbol})")
            logger.info(f"Telegram: {telegram}")
            logger.info(f"{'='*60}")
            
            # Join the group
            if not await bot.join_group(telegram):
                update_lead_in_csv(symbol, None, 'failed_to_join')
                continue
            
            # Get admins
            admins = await bot.get_group_admins(telegram)
            if not admins:
                logger.warning(f"No admins found for {name}")
                update_lead_in_csv(symbol, None, 'no_admins_found')
                continue
            
            # Send DM to first admin
            first_admin = admins[0]
            message = config.DM_TEMPLATE.format(token_name=name)
            
            dm_success = await bot.send_dm(first_admin, message)
            status = 'dm_sent' if dm_success else 'dm_failed'
            update_lead_in_csv(symbol, first_admin, status)
            
            # Check if we should stop
            if bot.joins_count >= config.MAX_JOINS_PER_SESSION:
                logger.warning(f"\n⚠️  Reached join limit. Processed {i}/{len(leads)} leads.")
                break
    
    finally:
        await bot.stop()
        logger.info(f"\n{'='*60}")
        logger.info(f"Session complete:")
        logger.info(f"  Groups joined: {bot.joins_count}")
        logger.info(f"  DMs sent: {bot.dms_sent}")
        logger.info(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(process_leads())
