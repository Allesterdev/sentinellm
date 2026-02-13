#!/bin/bash
# Quick start script for OpenClaw + SentineLLM integration
#
# Usage:
#   ./quick-start-openclaw.sh
#
# What it does:
#   1. Checks if SentineLLM is installed
#   2. Starts SentineLLM proxy on port 8080
#   3. Shows you how to configure OpenClaw
#   4. Waits for OpenClaw to connect

set -e

echo "🛡️  SentineLLM + OpenClaw Quick Start"
echo "======================================"
echo ""

# Check if we're in the right directory
if [ ! -f "sentinellm.py" ]; then
    echo "❌ Error: sentinellm.py not found"
    echo "Please run this script from the SentineLLM directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment not found"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Check if port 8080 is free
if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Warning: Port 8080 is already in use"
    echo "Checking what's using it:"
    lsof -i :8080
    echo ""
    read -p "Kill the process using port 8080? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill $(lsof -t -i:8080)
        echo "✓ Process killed"
    else
        echo "❌ Cannot start proxy on port 8080. Exiting."
        exit 1
    fi
fi

# Start proxy in background
echo "✓ Starting SentineLLM proxy on port 8080..."
python sentinellm.py proxy --host 127.0.0.1 --port 8080 > /tmp/sentinellm-proxy.log 2>&1 &
PROXY_PID=$!

# Wait for proxy to start
sleep 2

# Check if proxy is running
if ! curl -s http://localhost:8080/health >/dev/null; then
    echo "❌ Error: Proxy failed to start"
    echo "Check logs: cat /tmp/sentinellm-proxy.log"
    exit 1
fi

echo "✓ Proxy is running (PID: $PROXY_PID)"
echo ""

# Show configuration instructions
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 NEXT STEP: Configure OpenClaw"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Find your OpenClaw config file:"
echo "   ~/.config/openclaw/config.yaml"
echo ""
echo "2. Update the LLM configuration:"
echo ""
echo "   llm:"
echo "     provider: openai  # or google, anthropic, etc."
echo "     apiKey: \${OPENAI_API_KEY}"
echo "     baseUrl: http://localhost:8080/v1  # ← Add this!"
echo "     headers:"
echo "       X-Target-URL: https://api.openai.com  # ← Add this!"
echo ""
echo "3. Or use our example config:"
echo "   cp examples/openclaw-config.yaml ~/.config/openclaw/config.yaml"
echo ""
echo "4. Start/restart OpenClaw:"
echo "   openclaw restart"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Proxy Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Proxy running on: http://localhost:8080"
echo "✓ Logs: tail -f /tmp/sentinellm-proxy.log"
echo "✓ Health check: curl http://localhost:8080/health"
echo ""
echo "To stop the proxy:"
echo "  kill $PROXY_PID"
echo ""

# Monitor proxy logs
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "👀 Watching for requests (Ctrl+C to stop)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
tail -f /tmp/sentinellm-proxy.log

# Cleanup on exit
trap "echo ''; echo 'Stopping proxy...'; kill $PROXY_PID 2>/dev/null; exit" INT TERM
