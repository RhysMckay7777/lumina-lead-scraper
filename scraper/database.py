"""
SQLite Database for Lead Tracking
Tracks all projects found, contacted, responses, and metrics
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class LeadDatabase:
    """SQLite database for tracking leads and outreach"""
    
    def __init__(self, db_path: str = None):
        """Initialize database connection"""
        if db_path is None:
            db_path = os.path.expanduser("~/lumina-lead-scraper-v2/scraper/leads.db")
        
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.info(f"Database initialized at {self.db_path}")
    
    def _create_tables(self):
        """Create all required tables"""
        cursor = self.conn.cursor()
        
        # Projects/Tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_address TEXT UNIQUE NOT NULL,
                name TEXT,
                symbol TEXT,
                chain TEXT,
                website TEXT,
                telegram_url TEXT,
                twitter_url TEXT,
                dexscreener_url TEXT,
                
                -- Metrics at discovery
                volume_24h REAL,
                liquidity REAL,
                market_cap REAL,
                age_hours REAL,
                
                -- Google index status
                is_indexed BOOLEAN DEFAULT NULL,
                index_checked_at TIMESTAMP,
                
                -- Status tracking
                status TEXT DEFAULT 'discovered',  -- discovered, joined, contacted, responded, converted
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Source info
                source_url TEXT,
                source_page INTEGER
            )
        """)
        
        # Telegram groups table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telegram_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES projects(id),
                telegram_url TEXT NOT NULL,
                group_username TEXT,
                joined_at TIMESTAMP,
                join_success BOOLEAN,
                join_error TEXT,
                member_count INTEGER,
                
                UNIQUE(project_id, telegram_url)
            )
        """)
        
        # Admins table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES projects(id),
                group_id INTEGER REFERENCES telegram_groups(id),
                username TEXT NOT NULL,
                user_id TEXT,
                first_name TEXT,
                is_owner BOOLEAN DEFAULT FALSE,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(project_id, username)
            )
        """)
        
        # Outreach messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES projects(id),
                admin_id INTEGER REFERENCES admins(id),
                message_text TEXT NOT NULL,
                template_used TEXT,
                
                sent_at TIMESTAMP,
                send_success BOOLEAN,
                send_error TEXT,
                
                -- Response tracking
                response_received BOOLEAN DEFAULT FALSE,
                response_text TEXT,
                response_at TIMESTAMP,
                
                -- Conversion tracking
                converted BOOLEAN DEFAULT FALSE,
                conversion_notes TEXT
            )
        """)
        
        # Daily metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE NOT NULL,
                tokens_found INTEGER DEFAULT 0,
                tokens_with_telegram INTEGER DEFAULT 0,
                unindexed_sites_found INTEGER DEFAULT 0,
                groups_joined INTEGER DEFAULT 0,
                join_failures INTEGER DEFAULT 0,
                admins_found INTEGER DEFAULT 0,
                dms_sent INTEGER DEFAULT 0,
                dms_failed INTEGER DEFAULT 0,
                responses_received INTEGER DEFAULT 0,
                conversions INTEGER DEFAULT 0
            )
        """)
        
        # Error log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS error_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_type TEXT,
                error_message TEXT,
                context TEXT,
                resolved BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_contract ON projects(contract_address)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_discovered ON projects(discovered_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_sent ON messages(sent_at)")
        
        self.conn.commit()
        logger.info("Database tables created/verified")
    
    # ==========================================================================
    # Project Methods
    # ==========================================================================
    
    def add_project(self, token_data: Dict) -> int:
        """
        Add a new project to the database
        
        Args:
            token_data: Dict with token info from scraper
            
        Returns:
            Project ID
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO projects (
                    contract_address, name, symbol, chain, website,
                    telegram_url, twitter_url, dexscreener_url,
                    volume_24h, liquidity, market_cap, age_hours,
                    source_url, source_page
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                token_data.get('address', token_data.get('contract_address')),
                token_data.get('name'),
                token_data.get('symbol'),
                token_data.get('chain', 'solana'),
                token_data.get('website'),
                token_data.get('telegram'),
                token_data.get('twitter'),
                token_data.get('dexscreener_url'),
                token_data.get('volume_24h'),
                token_data.get('liquidity'),
                token_data.get('market_cap'),
                token_data.get('age_hours'),
                token_data.get('source_url'),
                token_data.get('source_page')
            ))
            self.conn.commit()
            project_id = cursor.lastrowid
            
            # Update daily metrics
            self._increment_daily_metric('tokens_found')
            if token_data.get('telegram'):
                self._increment_daily_metric('tokens_with_telegram')
            
            logger.info(f"Added project: {token_data.get('name')} (ID: {project_id})")
            return project_id
            
        except sqlite3.IntegrityError:
            # Already exists
            cursor.execute(
                "SELECT id FROM projects WHERE contract_address = ?",
                (token_data.get('address', token_data.get('contract_address')),)
            )
            row = cursor.fetchone()
            return row['id'] if row else None
    
    def get_project(self, project_id: int = None, contract_address: str = None) -> Optional[Dict]:
        """Get a project by ID or contract address"""
        cursor = self.conn.cursor()
        
        if project_id:
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        elif contract_address:
            cursor.execute("SELECT * FROM projects WHERE contract_address = ?", (contract_address,))
        else:
            return None
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def project_exists(self, contract_address: str) -> bool:
        """Check if a project already exists"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM projects WHERE contract_address = ?", (contract_address,))
        return cursor.fetchone() is not None
    
    def update_project_status(self, project_id: int, status: str):
        """Update project status"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE projects SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, project_id)
        )
        self.conn.commit()
    
    def update_index_status(self, project_id: int, is_indexed: bool):
        """Update Google index status for a project"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE projects SET is_indexed = ?, index_checked_at = CURRENT_TIMESTAMP WHERE id = ?",
            (is_indexed, project_id)
        )
        self.conn.commit()
        
        if not is_indexed:
            self._increment_daily_metric('unindexed_sites_found')
    
    def get_uncontacted_projects(self, limit: int = 50, only_unindexed: bool = True) -> List[Dict]:
        """Get projects that haven't been contacted yet"""
        cursor = self.conn.cursor()
        
        query = """
            SELECT * FROM projects 
            WHERE status = 'discovered' 
            AND telegram_url IS NOT NULL
        """
        
        if only_unindexed:
            query += " AND is_indexed = 0"
        
        query += " ORDER BY discovered_at DESC LIMIT ?"
        
        cursor.execute(query, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_projects_needing_index_check(self, limit: int = 50) -> List[Dict]:
        """Get projects that need Google index checking"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM projects 
            WHERE website IS NOT NULL 
            AND is_indexed IS NULL
            ORDER BY discovered_at DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    # ==========================================================================
    # Telegram Group Methods
    # ==========================================================================
    
    def add_telegram_group(self, project_id: int, telegram_url: str, 
                           joined: bool, error: str = None) -> int:
        """Record a Telegram group join attempt"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO telegram_groups (
                    project_id, telegram_url, joined_at, join_success, join_error
                ) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)
            """, (project_id, telegram_url, joined, error))
            self.conn.commit()
            
            if joined:
                self._increment_daily_metric('groups_joined')
                self.update_project_status(project_id, 'joined')
            else:
                self._increment_daily_metric('join_failures')
            
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
    
    # ==========================================================================
    # Admin Methods
    # ==========================================================================
    
    def add_admin(self, project_id: int, group_id: int, username: str,
                  user_id: str = None, first_name: str = None, is_owner: bool = False) -> int:
        """Add an admin to the database"""
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO admins (
                    project_id, group_id, username, user_id, first_name, is_owner
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (project_id, group_id, username, user_id, first_name, is_owner))
            self.conn.commit()
            self._increment_daily_metric('admins_found')
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Already exists
            cursor.execute(
                "SELECT id FROM admins WHERE project_id = ? AND username = ?",
                (project_id, username)
            )
            row = cursor.fetchone()
            return row['id'] if row else None
    
    def get_uncontacted_admins(self, project_id: int) -> List[Dict]:
        """Get admins for a project who haven't been contacted"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT a.* FROM admins a
            LEFT JOIN messages m ON a.id = m.admin_id AND m.send_success = 1
            WHERE a.project_id = ?
            AND m.id IS NULL
        """, (project_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    # ==========================================================================
    # Message Methods
    # ==========================================================================
    
    def add_message(self, project_id: int, admin_id: int, message_text: str,
                    template_used: str = None, success: bool = False, error: str = None) -> int:
        """Record a sent message"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO messages (
                project_id, admin_id, message_text, template_used,
                sent_at, send_success, send_error
            ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
        """, (project_id, admin_id, message_text, template_used, success, error))
        self.conn.commit()
        
        if success:
            self._increment_daily_metric('dms_sent')
            self.update_project_status(project_id, 'contacted')
        else:
            self._increment_daily_metric('dms_failed')
        
        return cursor.lastrowid
    
    def was_project_contacted(self, contract_address: str) -> bool:
        """Check if we've already contacted this project"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 1 FROM messages m
            JOIN projects p ON m.project_id = p.id
            WHERE p.contract_address = ?
            AND m.send_success = 1
        """, (contract_address,))
        return cursor.fetchone() is not None
    
    def record_response(self, message_id: int, response_text: str):
        """Record a response to a message"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE messages SET 
                response_received = 1,
                response_text = ?,
                response_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (response_text, message_id))
        self.conn.commit()
        self._increment_daily_metric('responses_received')
    
    # ==========================================================================
    # Metrics Methods
    # ==========================================================================
    
    def _increment_daily_metric(self, metric: str, amount: int = 1):
        """Increment a daily metric"""
        cursor = self.conn.cursor()
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Ensure today's row exists
        cursor.execute(
            "INSERT OR IGNORE INTO daily_metrics (date) VALUES (?)",
            (today,)
        )
        
        # Increment the metric
        cursor.execute(
            f"UPDATE daily_metrics SET {metric} = {metric} + ? WHERE date = ?",
            (amount, today)
        )
        self.conn.commit()
    
    def get_daily_metrics(self, date: str = None) -> Optional[Dict]:
        """Get metrics for a specific date"""
        cursor = self.conn.cursor()
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        cursor.execute("SELECT * FROM daily_metrics WHERE date = ?", (date,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_metrics_range(self, days: int = 7) -> List[Dict]:
        """Get metrics for the last N days"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM daily_metrics 
            WHERE date >= date('now', ?)
            ORDER BY date DESC
        """, (f'-{days} days',))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_summary_stats(self) -> Dict:
        """Get overall summary statistics"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Total projects
        cursor.execute("SELECT COUNT(*) FROM projects")
        stats['total_projects'] = cursor.fetchone()[0]
        
        # Projects with Telegram
        cursor.execute("SELECT COUNT(*) FROM projects WHERE telegram_url IS NOT NULL")
        stats['projects_with_telegram'] = cursor.fetchone()[0]
        
        # Unindexed sites
        cursor.execute("SELECT COUNT(*) FROM projects WHERE is_indexed = 0")
        stats['unindexed_sites'] = cursor.fetchone()[0]
        
        # Projects contacted
        cursor.execute("SELECT COUNT(DISTINCT project_id) FROM messages WHERE send_success = 1")
        stats['projects_contacted'] = cursor.fetchone()[0]
        
        # Total DMs sent
        cursor.execute("SELECT COUNT(*) FROM messages WHERE send_success = 1")
        stats['total_dms_sent'] = cursor.fetchone()[0]
        
        # Responses received
        cursor.execute("SELECT COUNT(*) FROM messages WHERE response_received = 1")
        stats['responses_received'] = cursor.fetchone()[0]
        
        # Response rate
        if stats['total_dms_sent'] > 0:
            stats['response_rate'] = round(stats['responses_received'] / stats['total_dms_sent'] * 100, 1)
        else:
            stats['response_rate'] = 0
        
        # Groups joined
        cursor.execute("SELECT COUNT(*) FROM telegram_groups WHERE join_success = 1")
        stats['groups_joined'] = cursor.fetchone()[0]
        
        return stats
    
    # ==========================================================================
    # Error Logging
    # ==========================================================================
    
    def log_error(self, error_type: str, error_message: str, context: str = None):
        """Log an error to the database"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO error_log (error_type, error_message, context)
            VALUES (?, ?, ?)
        """, (error_type, error_message, context))
        self.conn.commit()
    
    def get_recent_errors(self, limit: int = 20) -> List[Dict]:
        """Get recent errors"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM error_log 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    # ==========================================================================
    # Cleanup
    # ==========================================================================
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Convenience functions
def get_db() -> LeadDatabase:
    """Get a database instance"""
    return LeadDatabase()


if __name__ == "__main__":
    # Test the database
    logging.basicConfig(level=logging.INFO)
    
    db = LeadDatabase()
    
    # Add a test project
    test_token = {
        'address': 'TEST123456789',
        'name': 'Test Token',
        'symbol': 'TEST',
        'chain': 'solana',
        'telegram': 'https://t.me/testgroup',
        'website': 'https://testtoken.com'
    }
    
    project_id = db.add_project(test_token)
    print(f"Added project ID: {project_id}")
    
    # Check stats
    stats = db.get_summary_stats()
    print(f"Summary stats: {stats}")
    
    db.close()
