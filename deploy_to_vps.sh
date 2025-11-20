#!/bin/bash
# Deploy ScalperBot updates to VPS
# Run this from your Mac: ./deploy_to_vps.sh

VPS_HOST="root@207.180.212.142"
VPS_PATH="/root/scalperbot"
LOCAL_PATH="scalperbot"

echo "🚀 Deploying ScalperBot Hybrid Approach features to VPS..."

# Copy updated files
echo "📦 Copying updated files..."
scp ${LOCAL_PATH}/position_manager.py ${VPS_HOST}:${VPS_PATH}/
scp ${LOCAL_PATH}/config.py ${VPS_HOST}:${VPS_PATH}/
scp ${LOCAL_PATH}/main.py ${VPS_HOST}:${VPS_PATH}/
scp ${LOCAL_PATH}/.env.example ${VPS_HOST}:${VPS_PATH}/

# Restart bot on VPS
echo "🔄 Restarting bot on VPS..."
ssh ${VPS_HOST} "cd ${VPS_PATH} && sudo systemctl restart scalperbot"

# Show status
echo "✅ Deployment complete! Checking status..."
ssh ${VPS_HOST} "sudo systemctl status scalperbot --no-pager -l"

echo ""
echo "📊 Follow logs with:"
echo "ssh ${VPS_HOST} 'tail -f /root/scalperbot/bot.log'"
