#!/bin/bash
echo "🛑 Stopping Convertbot services..."

pkill -f "telegram_bot_improved.py"
pkill -f "app.worker"

sleep 2
echo "✅ Services stopped"
