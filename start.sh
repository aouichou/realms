#!/bin/bash
set -e

echo "🎮 Mistral Realms - Quick Start"
echo "================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚙️  Creating .env file..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Please add your Mistral API key to .env"
    echo "   Edit .env and set: MISTRAL_API_KEY=your_key_here"
    echo ""
    echo "   Get your API key from: https://console.mistral.ai/"
    echo ""
    read -p "Press Enter after adding your API key..."
fi

# Check if API key is set
if ! grep -q "MISTRAL_API_KEY=.*[a-zA-Z0-9]" .env; then
    echo "❌ Error: MISTRAL_API_KEY not set in .env"
    echo "   Please edit .env and add your Mistral API key"
    exit 1
fi

echo "🐳 Starting Docker containers..."
echo ""

# Start services
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Wait for backend health check
echo "   Checking backend..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "   ✓ Backend is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "   ❌ Backend failed to start"
        echo "   Check logs with: docker-compose logs backend"
        exit 1
    fi
    sleep 1
done

# Wait for frontend
echo "   Checking frontend..."
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "   ✓ Frontend is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "   ❌ Frontend failed to start"
        echo "   Check logs with: docker-compose logs frontend"
        exit 1
    fi
    sleep 1
done

echo ""
echo "✨ Mistral Realms is running!"
echo ""
echo "📍 Access points:"
echo "   Frontend:   http://localhost:3000"
echo "   Backend:    http://localhost:8000"
echo "   API Docs:   http://localhost:8000/docs"
echo ""
echo "📝 Useful commands:"
echo "   View logs:  docker-compose logs -f"
echo "   Stop:       docker-compose down"
echo "   Restart:    docker-compose restart"
echo ""
echo "🎲 Ready to start your adventure!"
echo ""
