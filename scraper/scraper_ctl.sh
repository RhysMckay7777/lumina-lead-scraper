#!/bin/bash
# Lumina Lead Scraper Control Script
# Usage: ./scraper_ctl.sh [start|stop|restart|status|logs|test|report]

PLIST_PATH="$HOME/Library/LaunchAgents/com.lumina.lead-scraper.plist"
SCRAPER_DIR="$HOME/lumina-lead-scraper-v2/scraper"
LOG_DIR="$HOME/clawd/scraper-logs"
VENV_PYTHON="$SCRAPER_DIR/venv/bin/python"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

case "$1" in
    start)
        echo -e "${GREEN}Starting Lumina Lead Scraper...${NC}"
        launchctl load "$PLIST_PATH" 2>/dev/null || launchctl start com.lumina.lead-scraper
        sleep 2
        if launchctl list | grep -q "com.lumina.lead-scraper"; then
            echo -e "${GREEN}✓ Scraper started${NC}"
        else
            echo -e "${RED}✗ Failed to start scraper${NC}"
        fi
        ;;
    
    stop)
        echo -e "${YELLOW}Stopping Lumina Lead Scraper...${NC}"
        launchctl stop com.lumina.lead-scraper 2>/dev/null
        launchctl unload "$PLIST_PATH" 2>/dev/null
        echo -e "${GREEN}✓ Scraper stopped${NC}"
        ;;
    
    restart)
        echo -e "${YELLOW}Restarting Lumina Lead Scraper...${NC}"
        $0 stop
        sleep 2
        $0 start
        ;;
    
    status)
        echo -e "${GREEN}Lumina Lead Scraper Status${NC}"
        echo "=========================="
        if launchctl list | grep -q "com.lumina.lead-scraper"; then
            echo -e "Service: ${GREEN}Running${NC}"
            launchctl list com.lumina.lead-scraper 2>/dev/null
        else
            echo -e "Service: ${RED}Stopped${NC}"
        fi
        echo ""
        echo "Recent log entries:"
        tail -20 "$LOG_DIR/daemon.stdout.log" 2>/dev/null || echo "No logs found"
        ;;
    
    logs)
        echo -e "${GREEN}Following scraper logs...${NC}"
        echo "Press Ctrl+C to exit"
        echo ""
        tail -f "$LOG_DIR"/scraper_*.log "$LOG_DIR/daemon.stdout.log" 2>/dev/null
        ;;
    
    test)
        echo -e "${GREEN}Running single scrape cycle (test mode)...${NC}"
        cd "$SCRAPER_DIR"
        $VENV_PYTHON autonomous_scraper.py --once
        ;;
    
    report)
        echo -e "${GREEN}Generating reports...${NC}"
        cd "$SCRAPER_DIR"
        echo ""
        echo "=== Daily Report ==="
        $VENV_PYTHON daily_report.py --type daily
        echo ""
        echo "=== Overall Stats ==="
        $VENV_PYTHON daily_report.py --type overall
        ;;
    
    install)
        echo -e "${GREEN}Installing dependencies...${NC}"
        cd "$SCRAPER_DIR"
        
        # Create venv if not exists
        if [ ! -d "venv" ]; then
            python3 -m venv venv
        fi
        
        # Install dependencies
        source venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        
        # Create log directory
        mkdir -p "$LOG_DIR"
        
        # Make scripts executable
        chmod +x autonomous_scraper.py
        chmod +x daily_report.py
        chmod +x scraper_ctl.sh
        
        echo -e "${GREEN}✓ Installation complete${NC}"
        echo ""
        echo "To start the daemon:"
        echo "  ./scraper_ctl.sh start"
        ;;
    
    db)
        echo -e "${GREEN}Database Stats${NC}"
        cd "$SCRAPER_DIR"
        $VENV_PYTHON -c "
from database import LeadDatabase
db = LeadDatabase()
stats = db.get_summary_stats()
print('Projects:', stats.get('total_projects', 0))
print('With Telegram:', stats.get('projects_with_telegram', 0))
print('Contacted:', stats.get('projects_contacted', 0))
print('DMs Sent:', stats.get('total_dms_sent', 0))
print('Responses:', stats.get('responses_received', 0))
print('Response Rate:', stats.get('response_rate', 0), '%')
db.close()
"
        ;;
    
    *)
        echo "Lumina Lead Scraper Control"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|test|report|install|db}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the background daemon"
        echo "  stop     - Stop the daemon"
        echo "  restart  - Restart the daemon"
        echo "  status   - Show daemon status and recent logs"
        echo "  logs     - Follow live logs"
        echo "  test     - Run single scrape cycle (foreground)"
        echo "  report   - Generate and display reports"
        echo "  install  - Install dependencies and setup"
        echo "  db       - Show database statistics"
        exit 1
        ;;
esac
