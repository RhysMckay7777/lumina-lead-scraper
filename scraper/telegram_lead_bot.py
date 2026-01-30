"""
Telegram Lead Bot - Handles joining groups, finding admins, sending DMs
Wraps existing TelegramBot functionality with batch operations
"""

import logging
import asyncio
import time
from typing import List, Dict
from telegram_bot import TelegramBot

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TelegramLeadBot:
    """High-level bot for lead generation workflow"""
    
    def __init__(self, api_id: int, api_hash: str, phone: str):
        """Initialize with Telegram credentials"""
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.bot = TelegramBot()
        self.loop = None
        
    def _run_async(self, coro):
        """Run async function synchronously"""
        if self.loop is None:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        return self.loop.run_until_complete(coro)
    
    def join_groups(self, tokens: List[Dict]) -> List[Dict]:
        """
        Join Telegram groups for tokens
        
        Args:
            tokens: List of token dicts with 'telegram' field
            
        Returns:
            List of tokens for which we successfully joined groups
        """
        logger.info(f"Joining {len(tokens)} Telegram groups...")
        
        async def _join_all():
            await self.bot.start()
            
            joined = []
            for i, token in enumerate(tokens, 1):
                telegram_url = token.get('telegram')
                if not telegram_url:
                    continue
                
                logger.info(f"[{i}/{len(tokens)}] Joining {token.get('name', 'Unknown')}...")
                
                success = await self.bot.join_group(telegram_url)
                if success:
                    joined.append(token)
                
                # Rate limiting delay
                if i < len(tokens):
                    await asyncio.sleep(3)
            
            return joined
        
        joined_groups = self._run_async(_join_all())
        logger.info(f"✅ Successfully joined {len(joined_groups)} groups")
        return joined_groups
    
    def find_admins(self, tokens: List[Dict]) -> List[Dict]:
        """
        Find admins in each group
        
        Args:
            tokens: List of token dicts with 'telegram' field
            
        Returns:
            List of dicts: {'token': token_data, 'admin_username': username}
        """
        logger.info(f"Finding admins in {len(tokens)} groups...")
        
        async def _find_all():
            admins_data = []
            
            for i, token in enumerate(tokens, 1):
                telegram_url = token.get('telegram')
                if not telegram_url:
                    continue
                
                logger.info(f"[{i}/{len(tokens)}] Getting admins for {token.get('name', 'Unknown')}...")
                
                admin_usernames = await self.bot.get_group_admins(telegram_url)
                
                for username in admin_usernames:
                    admins_data.append({
                        'token': token,
                        'admin_username': username
                    })
                
                # Rate limiting delay
                if i < len(tokens):
                    await asyncio.sleep(2)
            
            return admins_data
        
        admins_found = self._run_async(_find_all())
        logger.info(f"✅ Found {len(admins_found)} total admins")
        return admins_found
    
    def send_dms(self, admins_data: List[Dict], message_template: str) -> int:
        """
        Send DMs to admins
        
        Args:
            admins_data: List of dicts with 'token' and 'admin_username'
            message_template: Message template (can use {name}, {project} placeholders)
            
        Returns:
            Number of successfully sent DMs
        """
        logger.info(f"Sending DMs to {len(admins_data)} admins...")
        
        async def _send_all():
            sent_count = 0
            
            for i, admin_data in enumerate(admins_data, 1):
                username = admin_data['admin_username']
                token = admin_data['token']
                
                # Personalize message
                message = message_template.format(
                    name=username,
                    project=token.get('name', 'your project')
                )
                
                logger.info(f"[{i}/{len(admins_data)}] Sending DM to @{username}...")
                
                success = await self.bot.send_dm(username, message)
                if success:
                    sent_count += 1
                
                # Rate limiting delay (important!)
                if i < len(admins_data):
                    await asyncio.sleep(10)  # 10s between DMs
            
            await self.bot.stop()
            return sent_count
        
        sent_count = self._run_async(_send_all())
        logger.info(f"✅ Successfully sent {sent_count} DMs")
        return sent_count
    
    def __del__(self):
        """Cleanup"""
        if self.loop:
            try:
                self.loop.close()
            except:
                pass
