"""
Enhanced Telegram Automation
- Auto-join groups from scraped data
- Find admins in groups
- Send customized outreach messages
- Rate limiting and flood protection
"""

import asyncio
import logging
import re
import os
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta

from telethon import TelegramClient, functions, types
from telethon.errors import (
    FloodWaitError, UserPrivacyRestrictedError, PeerFloodError,
    UsernameInvalidError, ChatAdminRequiredError, ChannelPrivateError,
    UserNotMutualContactError, UserBannedInChannelError
)
from telethon.tl.types import ChannelParticipantsAdmins, User, Channel, Chat

logger = logging.getLogger(__name__)


class TelegramAutomator:
    """Enhanced Telegram automation with rate limiting and tracking"""
    
    def __init__(self, 
                 api_id: int,
                 api_hash: str,
                 phone: str,
                 session_file: str = "lumina_session",
                 join_delay: int = 30,
                 dm_delay: int = 60,
                 max_joins_per_hour: int = 10,
                 max_dms_per_hour: int = 5):
        """
        Initialize the automator
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API hash
            phone: Phone number with country code
            session_file: Session file path
            join_delay: Seconds between group joins
            dm_delay: Seconds between DMs
            max_joins_per_hour: Max group joins per hour
            max_dms_per_hour: Max DMs per hour
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.session_file = session_file
        
        self.join_delay = join_delay
        self.dm_delay = dm_delay
        self.max_joins_per_hour = max_joins_per_hour
        self.max_dms_per_hour = max_dms_per_hour
        
        self.client = None
        
        # Rate limiting tracking
        self.join_times = []
        self.dm_times = []
        
        # Stats
        self.stats = {
            'groups_joined': 0,
            'join_failures': 0,
            'dms_sent': 0,
            'dm_failures': 0,
            'admins_found': 0
        }
    
    async def start(self):
        """Start the Telegram client"""
        if self.client and self.client.is_connected():
            return
        
        self.client = TelegramClient(
            self.session_file,
            self.api_id,
            self.api_hash
        )
        
        await self.client.start(phone=self.phone)
        me = await self.client.get_me()
        logger.info(f"✓ Telegram connected as: {me.first_name} (@{me.username})")
    
    async def stop(self):
        """Stop the Telegram client"""
        if self.client:
            await self.client.disconnect()
            logger.info("Telegram client disconnected")
    
    def _extract_username(self, url: str) -> Optional[str]:
        """Extract username from Telegram URL"""
        if not url:
            return None
        
        patterns = [
            r't\.me/([a-zA-Z0-9_]+)',
            r'telegram\.me/([a-zA-Z0-9_]+)',
            r'@([a-zA-Z0-9_]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                username = match.group(1)
                # Skip common non-group usernames
                if username.lower() in ['joinchat', 'share', 'addstickers']:
                    continue
                return username
        
        return None
    
    def _can_join(self) -> Tuple[bool, int]:
        """Check if we can join a group (rate limiting)"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Clean old entries
        self.join_times = [t for t in self.join_times if t > hour_ago]
        
        if len(self.join_times) >= self.max_joins_per_hour:
            # Calculate wait time
            oldest = min(self.join_times)
            wait_seconds = int((oldest + timedelta(hours=1) - now).total_seconds())
            return False, max(0, wait_seconds)
        
        return True, 0
    
    def _can_dm(self) -> Tuple[bool, int]:
        """Check if we can send a DM (rate limiting)"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        self.dm_times = [t for t in self.dm_times if t > hour_ago]
        
        if len(self.dm_times) >= self.max_dms_per_hour:
            oldest = min(self.dm_times)
            wait_seconds = int((oldest + timedelta(hours=1) - now).total_seconds())
            return False, max(0, wait_seconds)
        
        return True, 0
    
    async def join_group(self, telegram_url: str) -> Tuple[bool, Optional[str]]:
        """
        Join a Telegram group
        
        Args:
            telegram_url: Telegram group URL
            
        Returns:
            Tuple of (success, error_message)
        """
        username = self._extract_username(telegram_url)
        if not username:
            return False, f"Could not extract username from {telegram_url}"
        
        # Check rate limits
        can_join, wait_time = self._can_join()
        if not can_join:
            return False, f"Rate limited, wait {wait_time}s"
        
        try:
            logger.info(f"Joining group: @{username}")
            
            entity = await self.client.get_entity(username)
            
            # Check if it's a group/channel
            if not isinstance(entity, (Channel, Chat)):
                return False, "Not a group/channel"
            
            # Check if already a member
            try:
                await self.client.get_participants(entity, limit=1)
                logger.info(f"Already a member of @{username}")
                return True, None
            except ChatAdminRequiredError:
                # Not a member, need to join
                pass
            except:
                pass
            
            # Join the group
            await self.client(functions.channels.JoinChannelRequest(entity))
            
            self.join_times.append(datetime.now())
            self.stats['groups_joined'] += 1
            
            logger.info(f"✓ Joined @{username}")
            
            # Delay before next action
            await asyncio.sleep(self.join_delay)
            
            return True, None
            
        except FloodWaitError as e:
            logger.error(f"⚠️ FloodWait: Must wait {e.seconds}s")
            return False, f"FloodWait: {e.seconds}s"
        
        except ChannelPrivateError:
            return False, "Private channel"
        
        except UsernameInvalidError:
            return False, "Invalid username"
        
        except Exception as e:
            logger.error(f"Join error for @{username}: {e}")
            self.stats['join_failures'] += 1
            return False, str(e)
    
    async def get_group_admins(self, telegram_url: str) -> List[Dict]:
        """
        Get admins from a Telegram group
        
        Args:
            telegram_url: Telegram group URL
            
        Returns:
            List of admin dicts with username, user_id, first_name, is_owner
        """
        username = self._extract_username(telegram_url)
        if not username:
            return []
        
        try:
            entity = await self.client.get_entity(username)
            
            if not isinstance(entity, (Channel, Chat)):
                return []
            
            # Get admin participants
            admins = []
            async for participant in self.client.iter_participants(
                entity, 
                filter=ChannelParticipantsAdmins()
            ):
                # Skip bots
                if participant.bot:
                    continue
                
                # Skip users without username (can't DM them easily)
                if not participant.username:
                    continue
                
                admin_info = {
                    'username': participant.username,
                    'user_id': participant.id,
                    'first_name': participant.first_name or '',
                    'is_owner': hasattr(participant.participant, 'creator') and participant.participant.creator
                }
                
                admins.append(admin_info)
                self.stats['admins_found'] += 1
                logger.info(f"  Admin: @{participant.username}")
            
            return admins
            
        except ChatAdminRequiredError:
            logger.warning(f"Cannot get admins for @{username} - not a member or no permissions")
            return []
        except Exception as e:
            logger.error(f"Error getting admins for @{username}: {e}")
            return []
    
    async def send_dm(self, 
                      username: str, 
                      message: str,
                      project_name: str = None,
                      token_symbol: str = None) -> Tuple[bool, Optional[str]]:
        """
        Send a DM to a user
        
        Args:
            username: Telegram username (without @)
            message: Message to send
            project_name: Project name for personalization
            token_symbol: Token symbol for personalization
            
        Returns:
            Tuple of (success, error_message)
        """
        # Check rate limits
        can_dm, wait_time = self._can_dm()
        if not can_dm:
            return False, f"Rate limited, wait {wait_time}s"
        
        try:
            # Personalize message
            final_message = message
            
            # Add greeting with name if available
            admin_greeting = ""
            if '{admin_name_greeting}' in message:
                final_message = message.replace('{admin_name_greeting}', admin_greeting)
            
            if project_name:
                final_message = final_message.replace('{project_name}', project_name)
            if token_symbol:
                final_message = final_message.replace('{token_symbol}', token_symbol)
            
            logger.info(f"Sending DM to @{username}...")
            
            user = await self.client.get_entity(username)
            await self.client.send_message(user, final_message)
            
            self.dm_times.append(datetime.now())
            self.stats['dms_sent'] += 1
            
            logger.info(f"✓ DM sent to @{username}")
            
            # Delay before next DM
            await asyncio.sleep(self.dm_delay)
            
            return True, None
            
        except UserPrivacyRestrictedError:
            logger.warning(f"⚠️ @{username} has privacy restrictions")
            self.stats['dm_failures'] += 1
            return False, "Privacy restricted"
        
        except UserNotMutualContactError:
            logger.warning(f"⚠️ @{username} requires mutual contact")
            self.stats['dm_failures'] += 1
            return False, "Not mutual contact"
        
        except PeerFloodError:
            logger.error("⚠️ PEER FLOOD - Account may be restricted")
            self.stats['dm_failures'] += 1
            return False, "Peer flood"
        
        except FloodWaitError as e:
            logger.error(f"⚠️ FloodWait: Must wait {e.seconds}s")
            return False, f"FloodWait: {e.seconds}s"
        
        except Exception as e:
            logger.error(f"DM error for @{username}: {e}")
            self.stats['dm_failures'] += 1
            return False, str(e)
    
    async def process_project(self,
                              project: Dict,
                              message_template: str,
                              db=None) -> Dict:
        """
        Full workflow for a single project:
        1. Join group
        2. Get admins
        3. Send DM to first admin
        
        Args:
            project: Project dict with telegram_url, name, symbol
            message_template: Message template
            db: Database instance for recording
            
        Returns:
            Result dict with success status and details
        """
        result = {
            'project_id': project.get('id'),
            'name': project.get('name'),
            'symbol': project.get('symbol'),
            'joined': False,
            'admins_found': 0,
            'dm_sent': False,
            'error': None
        }
        
        telegram_url = project.get('telegram_url') or project.get('telegram')
        if not telegram_url:
            result['error'] = "No Telegram URL"
            return result
        
        # Step 1: Join group
        joined, join_error = await self.join_group(telegram_url)
        result['joined'] = joined
        
        if not joined:
            result['error'] = f"Join failed: {join_error}"
            if db:
                db.add_telegram_group(
                    project_id=project.get('id'),
                    telegram_url=telegram_url,
                    joined=False,
                    error=join_error
                )
            return result
        
        if db:
            group_id = db.add_telegram_group(
                project_id=project.get('id'),
                telegram_url=telegram_url,
                joined=True
            )
        else:
            group_id = None
        
        # Step 2: Get admins
        admins = await self.get_group_admins(telegram_url)
        result['admins_found'] = len(admins)
        
        if not admins:
            result['error'] = "No admins found"
            return result
        
        # Record admins
        if db and group_id:
            for admin in admins:
                db.add_admin(
                    project_id=project.get('id'),
                    group_id=group_id,
                    username=admin['username'],
                    user_id=str(admin['user_id']),
                    first_name=admin['first_name'],
                    is_owner=admin['is_owner']
                )
        
        # Step 3: Send DM to first admin (prefer owner)
        target_admin = next((a for a in admins if a['is_owner']), admins[0])
        
        sent, dm_error = await self.send_dm(
            username=target_admin['username'],
            message=message_template,
            project_name=project.get('name'),
            token_symbol=project.get('symbol')
        )
        
        result['dm_sent'] = sent
        if not sent:
            result['error'] = f"DM failed: {dm_error}"
        
        # Record message
        if db:
            admin_id = None
            # Get admin ID from DB
            uncontacted = db.get_uncontacted_admins(project.get('id'))
            for ua in uncontacted:
                if ua.get('username') == target_admin['username']:
                    admin_id = ua.get('id')
                    break
            
            db.add_message(
                project_id=project.get('id'),
                admin_id=admin_id,
                message_text=message_template,
                template_used='default',
                success=sent,
                error=dm_error
            )
        
        return result
    
    def get_stats(self) -> Dict:
        """Get current session stats"""
        return {
            **self.stats,
            'joins_remaining_this_hour': max(0, self.max_joins_per_hour - len(self.join_times)),
            'dms_remaining_this_hour': max(0, self.max_dms_per_hour - len(self.dm_times))
        }


# Synchronous wrapper for easier use
class TelegramAutomatorSync:
    """Synchronous wrapper for TelegramAutomator"""
    
    def __init__(self, *args, **kwargs):
        self.automator = TelegramAutomator(*args, **kwargs)
        self.loop = None
    
    def _get_loop(self):
        if self.loop is None or self.loop.is_closed():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
        return self.loop
    
    def start(self):
        return self._get_loop().run_until_complete(self.automator.start())
    
    def stop(self):
        return self._get_loop().run_until_complete(self.automator.stop())
    
    def join_group(self, telegram_url: str):
        return self._get_loop().run_until_complete(self.automator.join_group(telegram_url))
    
    def get_group_admins(self, telegram_url: str):
        return self._get_loop().run_until_complete(self.automator.get_group_admins(telegram_url))
    
    def send_dm(self, username: str, message: str, **kwargs):
        return self._get_loop().run_until_complete(
            self.automator.send_dm(username, message, **kwargs)
        )
    
    def process_project(self, project: Dict, message_template: str, db=None):
        return self._get_loop().run_until_complete(
            self.automator.process_project(project, message_template, db)
        )
    
    def get_stats(self):
        return self.automator.get_stats()


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Test with credentials from config
    from config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE
    
    async def test():
        automator = TelegramAutomator(
            api_id=TELEGRAM_API_ID,
            api_hash=TELEGRAM_API_HASH,
            phone=TELEGRAM_PHONE
        )
        
        await automator.start()
        
        # Test getting admins from a test group
        test_url = "https://t.me/solana"
        print(f"\nGetting admins from {test_url}...")
        admins = await automator.get_group_admins(test_url)
        print(f"Found {len(admins)} admins")
        
        await automator.stop()
        print(f"\nStats: {automator.get_stats()}")
    
    asyncio.run(test())
