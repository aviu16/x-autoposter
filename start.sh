#!/bin/bash
# Quick start/stop script for the X Autoposter daemon
cd "$(dirname "$0")"
PLIST="$HOME/Library/LaunchAgents/com.avantika.x-autoposter.plist"

case "${1:-start}" in
    start)
        echo "Starting X Autoposter daemon..."
        launchctl unload "$PLIST" 2>/dev/null
        launchctl load "$PLIST"
        sleep 2
        if pgrep -f "run.py start" > /dev/null; then
            echo "✅ Daemon running! (PID: $(pgrep -f 'run.py start'))"
            echo "📋 Logs: tail -f logs/autoposter.log"
        else
            echo "⚠️  launchd failed, starting with nohup..."
            PYTHONUNBUFFERED=1 nohup ./venv/bin/python run.py start >> logs/autoposter.log 2>&1 &
            echo "✅ Started with nohup (PID: $!)"
        fi
        ;;
    stop)
        echo "Stopping daemon..."
        launchctl unload "$PLIST" 2>/dev/null
        pkill -f "run.py start" 2>/dev/null
        echo "✅ Stopped"
        ;;
    status)
        if pgrep -f "run.py start" > /dev/null; then
            echo "✅ Running (PID: $(pgrep -f 'run.py start'))"
        else
            echo "❌ Not running"
        fi
        ;;
    logs)
        tail -f logs/autoposter.log
        ;;
    *)
        echo "Usage: ./start.sh [start|stop|status|logs]"
        ;;
esac
