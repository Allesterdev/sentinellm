#!/bin/bash
# Script para ejecutar todos los tests con cobertura

set -e

echo "🧪 SentineLLM - Test Suite"
echo "============================"
echo ""

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Ejecutar tests con cobertura
echo "📊 Ejecutando tests con cobertura..."
pytest -v \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html \
    --tb=short

echo ""
echo "✅ Tests completados"
echo ""
echo "📈 Reporte de cobertura generado en: htmlcov/index.html"
echo ""
