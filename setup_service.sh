#!/bin/bash
# Setup script to run Convertbot worker as a systemd service

echo "🔧 Setting up Convertbot Worker Service..."

# Create logs directory
mkdir -p /root/Convertbot/logs

# Create systemd service file
cat > /etc/systemd/system/convertbot-worker.service << 'EOF'
[Unit]
Description=Convertbot Worker - Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Convertbot
Environment="PATH=/root/Convertbot/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/root/Convertbot/venv/bin/python -m app.worker
Restart=always
RestartSec=10
StandardOutput=append:/root/Convertbot/logs/worker.log
StandardError=append:/root/Convertbot/logs/worker-error.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
echo "📋 Reloading systemd daemon..."
systemctl daemon-reload

# Enable service to start on boot
echo "✅ Enabling service to start on boot..."
systemctl enable convertbot-worker

# Start the service
echo "🚀 Starting convertbot-worker service..."
systemctl start convertbot-worker

# Show status
echo ""
echo "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "="
echo "📊 Service Status:"
echo "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "=" "="
systemctl status convertbot-worker --no-pager

echo ""
echo "✅ Setup complete!"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status convertbot-worker   # Check status"
echo "  sudo systemctl stop convertbot-worker     # Stop service"
echo "  sudo systemctl start convertbot-worker    # Start service"
echo "  sudo systemctl restart convertbot-worker  # Restart service"
echo "  sudo journalctl -u convertbot-worker -f   # View live logs"
echo "  tail -f /root/Convertbot/logs/worker.log  # View worker output"
