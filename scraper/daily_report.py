#!/usr/bin/env python3
"""
Daily Report Generator
Generates summary reports for Telegram delivery
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import LeadDatabase

logger = logging.getLogger(__name__)


class DailyReportGenerator:
    """Generate daily summary reports"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize the report generator
        
        Args:
            db_path: Path to the database
        """
        self.db = LeadDatabase(db_path)
    
    def generate_daily_report(self, date: str = None) -> str:
        """
        Generate a daily summary report
        
        Args:
            date: Date string (YYYY-MM-DD) or None for today
            
        Returns:
            Formatted report string for Telegram
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        metrics = self.db.get_daily_metrics(date)
        
        if not metrics:
            return f"📊 **Daily Report - {date}**\n\nNo activity recorded for this date."
        
        # Build report
        report = []
        report.append(f"📊 **Daily Report - {date}**")
        report.append("")
        report.append("**🔍 Discovery**")
        report.append(f"• Tokens found: {metrics.get('tokens_found', 0)}")
        report.append(f"• With Telegram: {metrics.get('tokens_with_telegram', 0)}")
        report.append(f"• Unindexed sites: {metrics.get('unindexed_sites_found', 0)}")
        report.append("")
        report.append("**📱 Telegram Activity**")
        report.append(f"• Groups joined: {metrics.get('groups_joined', 0)}")
        report.append(f"• Join failures: {metrics.get('join_failures', 0)}")
        report.append(f"• Admins found: {metrics.get('admins_found', 0)}")
        report.append("")
        report.append("**📨 Outreach**")
        report.append(f"• DMs sent: {metrics.get('dms_sent', 0)}")
        report.append(f"• DM failures: {metrics.get('dms_failed', 0)}")
        report.append(f"• Responses: {metrics.get('responses_received', 0)}")
        
        # Success rate
        total_dms = metrics.get('dms_sent', 0) + metrics.get('dms_failed', 0)
        if total_dms > 0:
            success_rate = (metrics.get('dms_sent', 0) / total_dms) * 100
            report.append(f"• DM success rate: {success_rate:.1f}%")
        
        responses = metrics.get('responses_received', 0)
        dms_sent = metrics.get('dms_sent', 0)
        if dms_sent > 0:
            response_rate = (responses / dms_sent) * 100
            report.append(f"• Response rate: {response_rate:.1f}%")
        
        return "\n".join(report)
    
    def generate_weekly_report(self) -> str:
        """Generate a weekly summary report"""
        metrics_list = self.db.get_metrics_range(days=7)
        
        if not metrics_list:
            return "📊 **Weekly Report**\n\nNo activity in the past 7 days."
        
        # Aggregate metrics
        totals = {
            'tokens_found': 0,
            'tokens_with_telegram': 0,
            'unindexed_sites_found': 0,
            'groups_joined': 0,
            'join_failures': 0,
            'admins_found': 0,
            'dms_sent': 0,
            'dms_failed': 0,
            'responses_received': 0
        }
        
        for metrics in metrics_list:
            for key in totals:
                totals[key] += metrics.get(key, 0) or 0
        
        # Build report
        report = []
        report.append("📊 **Weekly Report**")
        report.append(f"Period: {metrics_list[-1]['date']} to {metrics_list[0]['date']}")
        report.append("")
        report.append("**🔍 Discovery**")
        report.append(f"• Total tokens found: {totals['tokens_found']}")
        report.append(f"• With Telegram: {totals['tokens_with_telegram']}")
        report.append(f"• Unindexed sites: {totals['unindexed_sites_found']}")
        report.append("")
        report.append("**📱 Telegram**")
        report.append(f"• Groups joined: {totals['groups_joined']}")
        report.append(f"• Admins found: {totals['admins_found']}")
        report.append("")
        report.append("**📨 Outreach**")
        report.append(f"• Total DMs sent: {totals['dms_sent']}")
        report.append(f"• Responses: {totals['responses_received']}")
        
        if totals['dms_sent'] > 0:
            response_rate = (totals['responses_received'] / totals['dms_sent']) * 100
            report.append(f"• Response rate: {response_rate:.1f}%")
        
        return "\n".join(report)
    
    def generate_overall_report(self) -> str:
        """Generate overall summary of all-time stats"""
        stats = self.db.get_summary_stats()
        
        report = []
        report.append("📊 **Overall Statistics**")
        report.append("")
        report.append("**📈 All-Time Totals**")
        report.append(f"• Projects discovered: {stats.get('total_projects', 0)}")
        report.append(f"• With Telegram: {stats.get('projects_with_telegram', 0)}")
        report.append(f"• Unindexed sites: {stats.get('unindexed_sites', 0)}")
        report.append(f"• Groups joined: {stats.get('groups_joined', 0)}")
        report.append(f"• Projects contacted: {stats.get('projects_contacted', 0)}")
        report.append("")
        report.append("**📨 Outreach Performance**")
        report.append(f"• Total DMs sent: {stats.get('total_dms_sent', 0)}")
        report.append(f"• Responses received: {stats.get('responses_received', 0)}")
        report.append(f"• Response rate: {stats.get('response_rate', 0)}%")
        
        # Funnel analysis
        if stats.get('total_projects', 0) > 0:
            report.append("")
            report.append("**🎯 Funnel Analysis**")
            
            total = stats['total_projects']
            with_tg = stats.get('projects_with_telegram', 0)
            contacted = stats.get('projects_contacted', 0)
            responded = stats.get('responses_received', 0)
            
            report.append(f"• Discovery → Telegram: {with_tg/total*100:.1f}%")
            if with_tg > 0:
                report.append(f"• Telegram → Contacted: {contacted/with_tg*100:.1f}%")
            if contacted > 0:
                report.append(f"• Contacted → Response: {responded/contacted*100:.1f}%")
        
        return "\n".join(report)
    
    def get_recent_contacts(self, limit: int = 10) -> str:
        """Get list of recently contacted projects"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT p.name, p.symbol, p.telegram_url, m.sent_at, m.send_success,
                   a.username as admin_username
            FROM messages m
            JOIN projects p ON m.project_id = p.id
            LEFT JOIN admins a ON m.admin_id = a.id
            ORDER BY m.sent_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        
        if not rows:
            return "No recent contacts."
        
        report = []
        report.append("**📱 Recent Contacts**")
        report.append("")
        
        for row in rows:
            status = "✅" if row['send_success'] else "❌"
            admin = f"@{row['admin_username']}" if row['admin_username'] else "Unknown"
            report.append(f"{status} **{row['name']}** ({row['symbol']})")
            report.append(f"   Admin: {admin}")
            report.append(f"   Time: {row['sent_at']}")
            report.append("")
        
        return "\n".join(report)
    
    def close(self):
        """Close database connection"""
        self.db.close()


async def send_report_to_telegram(report: str, chat_id: int = None):
    """
    Send a report to Telegram
    
    Args:
        report: Report text
        chat_id: Telegram chat ID to send to
    """
    if not chat_id:
        logger.warning("No chat_id configured for report delivery")
        return
    
    import yaml
    
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    tg_config = config.get('telegram', {}).get('credentials', {})
    
    from telethon import TelegramClient
    
    client = TelegramClient(
        tg_config.get('session_file', 'lumina_session'),
        tg_config.get('api_id'),
        tg_config.get('api_hash')
    )
    
    await client.start(phone=tg_config.get('phone'))
    await client.send_message(chat_id, report, parse_mode='md')
    await client.disconnect()
    
    logger.info(f"Report sent to chat {chat_id}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate daily/weekly reports')
    parser.add_argument('--type', '-t', choices=['daily', 'weekly', 'overall', 'recent'],
                       default='daily', help='Report type')
    parser.add_argument('--date', '-d', default=None, help='Date for daily report (YYYY-MM-DD)')
    parser.add_argument('--send', '-s', action='store_true', help='Send to Telegram')
    parser.add_argument('--chat-id', type=int, default=None, help='Telegram chat ID')
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    generator = DailyReportGenerator()
    
    if args.type == 'daily':
        report = generator.generate_daily_report(args.date)
    elif args.type == 'weekly':
        report = generator.generate_weekly_report()
    elif args.type == 'overall':
        report = generator.generate_overall_report()
    elif args.type == 'recent':
        report = generator.get_recent_contacts()
    
    print(report)
    
    if args.send:
        import asyncio
        asyncio.run(send_report_to_telegram(report, args.chat_id))
    
    generator.close()


if __name__ == "__main__":
    main()
