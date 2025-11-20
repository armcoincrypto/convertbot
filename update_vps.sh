#!/bin/bash
# Safe update script for VPS deployment

echo "🔄 Updating Convertbot on VPS..."

# Navigate to deployment directory
cd /root/Convertbot

# Show what files have local changes
echo ""
echo "📋 Local changes:"
git status --short

# Stash local changes temporarily
echo ""
echo "💾 Stashing local changes..."
git stash

# Pull latest code
echo ""
echo "⬇️  Pulling latest code from GitHub..."
git pull origin claude/fix-pending-deposits-error-0191kMkiRXVQ6ccEqu7DZHUz

# Try to re-apply stashed changes (should merge cleanly if same fixes)
echo ""
echo "🔀 Re-applying local changes..."
git stash pop || echo "⚠️  Stash pop had conflicts or no changes to apply"

# Show final status
echo ""
echo "📊 Final status:"
git status --short

# Restart services
echo ""
echo "🔄 Restarting services..."
sudo systemctl restart convertbot-worker
sudo systemctl restart convertbot-bot

# Wait a moment for services to start
sleep 3

# Show service status
echo ""
echo "✅ Worker status:"
sudo systemctl status convertbot-worker --no-pager | head -10

echo ""
echo "✅ Bot status:"
sudo systemctl status convertbot-bot --no-pager | head -10

echo ""
echo "🎉 Update complete!"
echo ""
echo "View logs:"
echo "  tail -f /root/Convertbot/logs/worker.log"
echo "  tail -f /root/Convertbot/logs/bot.log"
