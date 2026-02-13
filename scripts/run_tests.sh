#!/bin/bash
# Run all tests with coverage

set -e

echo "🧪 SentineLLM - Test Suite"
echo "============================"
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run tests with coverage
echo "📊 Running tests with coverage..."
pytest -v \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html \
    --tb=short

echo ""
echo "✅ Tests completed"
echo ""
echo "📈 Coverage report generated at: htmlcov/index.html"
echo ""
