#!/bin/bash
set -e

echo "================================================="
echo "  🚀 Starting MineIntel-AI Fullstack Platform   "
echo "================================================="

# Install Python requirements if needed
if ! python -c "import fastapi" &>/dev/null; then
  echo "📦 Installing backend dependencies..."
  pip install --upgrade pip
  pip install -r backend/requirements.txt
fi

# Install Frontend dependencies if needed
if [ ! -d "frontend/node_modules" ]; then
  echo "📦 Installing frontend dependencies..."
  cd frontend && npm install && cd ..
fi

# Kill any existing server processes on ports 8000 and 5173
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true

# Start FastAPI backend in the background
echo "⚡ Starting FastAPI Backend on http://0.0.0.0:8000 ..."
nohup uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &

sleep 2

# Start Vite Frontend
echo "🌐 Starting Vite Frontend on http://0.0.0.0:5173 ..."
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
