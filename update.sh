#!/bin/bash

BOT_DIR="/mnt/user/appdata/discord-bot"
CONTAINER_NAME="discord-forum-bot"

echo "📦 Updating Discord Bot..."

# Navigate to bot directory
cd $BOT_DIR

# Pull latest changes if using git
if [ -d ".git" ]; then
    echo "📥 Pulling latest changes from git..."
    git pull
fi

# Stop the container
echo "🛑 Stopping bot..."
docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME

# Rebuild the image
echo "🔨 Building new image..."
docker build -t discord-forum-bot .

# Start the container
echo "🚀 Starting bot..."
docker run -d \
  --name $CONTAINER_NAME \
  --restart unless-stopped \
  --env-file .env \
  -v $BOT_DIR/logs:/app/logs \
  discord-forum-bot

echo "✅ Bot updated and running!"

# Show logs
echo "📜 Recent logs:"
docker logs --tail 20 $CONTAINER_NAME