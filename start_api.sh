#!/bin/bash
# SentineLLM API Server Startup Script

echo "🛡️ Starting SentineLLM API Server..."
echo ""
echo "📍 API will be available at:"
echo "   - Root: http://localhost:8000/"
echo "   - Docs: http://localhost:8000/docs"
echo "   - Health: http://localhost:8000/api/v1/health"
echo "   - Validate: http://localhost:8000/api/v1/validate"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")" || exit

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the API server
python3 run_api.py
