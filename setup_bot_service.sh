#!/bin/bash
# Setup script to run Convertbot Telegram Bot as a systemd service

echo "🤖 Setting up Convertbot Telegram Bot Service..."

# Create logs directory
mkdir -p /root/Convertbot/logs

# Create systemd service file for the bot
cat > /etc/systemd/system/convertbot-bot.service << 'EOF'
[Unit]
Description=Convertbot Telegram Bot - User Interface
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Convertbot
Environment="PATH=/root/Convertbot/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/root/Convertbot/venv/bin/python telegram_bot_improved.py
Restart=always
RestartSec=10
StandardOutput=append:/root/Convertbot/logs/bot.log
StandardError=append:/root/Convertbot/logs/bot-error.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo "📋 Reloading systemd daemon..."
systemctl daemon-reload

# Enable service to start on boot
echo "✅ Enabling bot service to start on boot..."
systemctl enable convertbot-bot

# Start the service
echo "🚀 Starting convertbot-bot service..."
systemctl start convertbot-bot

# Show status
echo ""
echo "================================================================================"
echo "📊 Telegram Bot Service Status:"
echo "================================================================================"
systemctl status convertbot-bot --no-pager

echo ""
echo "✅ Telegram Bot setup complete!"
echo ""
echo "Now you have TWO services running:"
echo "  1. convertbot-worker - Processes deposits"
echo "  2. convertbot-bot - Handles user commands"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status convertbot-bot      # Check bot status"
echo "  sudo systemctl status convertbot-worker   # Check worker status"
echo "  sudo systemctl restart convertbot-bot     # Restart bot"
echo "  sudo systemctl stop convertbot-bot        # Stop bot"
echo "  tail -f /root/Convertbot/logs/bot.log     # View bot logs"
echo "  tail -f /root/Convertbot/logs/worker.log  # View worker logs"
