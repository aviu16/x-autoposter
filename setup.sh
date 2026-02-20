#!/bin/bash
# X Autoposter - Setup Script
# Run this once to set everything up

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=================================="
echo "  X AUTOPOSTER SETUP"
echo "=================================="

# 1. Create virtual environment
echo ""
echo "[1/4] Creating Python virtual environment..."
cd "$SCRIPT_DIR"
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
echo "[2/4] Installing dependencies..."
pip install -r requirements.txt

# 3. Create .env if needed
if [ ! -f .env ]; then
    echo "[3/4] Creating .env from template..."
    cp .env.example .env
    echo ""
    echo "!!! IMPORTANT: Edit .env with your API keys !!!"
    echo "    nano $SCRIPT_DIR/.env"
    echo ""
else
    echo "[3/4] .env already exists, skipping..."
fi

# 4. Create macOS launchd plist for background running
echo "[4/4] Creating macOS background service..."

PLIST_PATH="$HOME/Library/LaunchAgents/com.avantika.x-autoposter.plist"

cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.avantika.x-autoposter</string>
    <key>ProgramArguments</key>
    <array>
        <string>${SCRIPT_DIR}/venv/bin/python</string>
        <string>${SCRIPT_DIR}/run.py</string>
        <string>start</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${SCRIPT_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${SCRIPT_DIR}/logs/autoposter.log</string>
    <key>StandardErrorPath</key>
    <string>${SCRIPT_DIR}/logs/autoposter_error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

mkdir -p "$SCRIPT_DIR/logs"

echo ""
echo "=================================="
echo "  SETUP COMPLETE!"
echo "=================================="
echo ""
echo "Next steps:"
echo ""
echo "  1. Edit your API keys:"
echo "     nano $SCRIPT_DIR/.env"
echo ""
echo "  2. Test your setup:"
echo "     cd $SCRIPT_DIR && source venv/bin/activate"
echo "     python run.py setup"
echo ""
echo "  3. Generate content queue:"
echo "     python run.py generate"
echo ""
echo "  4. Preview what will be posted:"
echo "     python run.py preview"
echo ""
echo "  5. Test with a single post:"
echo "     python run.py post"
echo ""
echo "  6. Start the background daemon (runs even when you're in lab):"
echo "     launchctl load $PLIST_PATH"
echo ""
echo "  To stop the daemon:"
echo "     launchctl unload $PLIST_PATH"
echo ""
echo "  View logs:"
echo "     tail -f $SCRIPT_DIR/logs/autoposter.log"
