#!/bin/bash
# Development setup script for SentineLLM

set -e

echo "🛡️  SentineLLM - Development Setup"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

echo "✓ Python $(python3 --version) found"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip -q

# Install SentineLLM in editable mode + dev dependencies
echo "📚 Installing SentineLLM (editable) + dev dependencies..."
pip install -e . -q
pip install -r requirements-dev.txt -q

# Copy .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
else
    echo "✓ .env file already exists"
fi

# Install pre-commit hooks
echo "🪝 Installing pre-commit hooks..."
pre-commit install

# Run tests
echo ""
echo "🧪 Running tests..."
pytest -v --tb=short

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "To activate the virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "To run tests:"
echo "  pytest"
echo ""
echo "To start the proxy:"
echo "  sllm proxy openai"
echo ""
