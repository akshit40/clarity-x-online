#!/bin/bash
# Clarity Rx All-in-One Launcher

echo "========================================="
echo "   Starting Clarity Rx Services...       "
echo "========================================="

# 1. Start FastAPI Backend on Port 8000
./venv/bin/uvicorn server:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!
echo "Backend running (PID: $BACKEND_PID) at http://127.0.0.1:8000"

# 2. Start React Frontend on Port 5173
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!
echo "Frontend running (PID: $FRONTEND_PID) at http://localhost:5173"

echo ""
echo "App is LIVE! Open: http://localhost:5173 in your browser."
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
