#!/bin/bash
# Script de setup para desarrollo local

set -e

echo "🛡️  SentineLLM - Setup de Desarrollo"
echo "========================================"
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado"
    exit 1
fi

echo "✓ Python $(python3 --version) encontrado"

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
else
    echo "✓ Entorno virtual ya existe"
fi

# Activar entorno virtual
echo "🔧 Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip
echo "⬆️  Actualizando pip..."
pip install --upgrade pip -q

# Instalar dependencias
echo "📚 Instalando dependencias..."
pip install -r requirements-dev.txt -q

# Copiar .env si no existe
if [ ! -f ".env" ]; then
    echo "📝 Creando archivo .env..."
    cp .env.example .env
else
    echo "✓ Archivo .env ya existe"
fi

# Instalar pre-commit hooks
echo "🪝 Instalando pre-commit hooks..."
pre-commit install

# Ejecutar tests
echo ""
echo "🧪 Ejecutando tests..."
pytest -v --tb=short

echo ""
echo "✅ Setup completado exitosamente!"
echo ""
echo "Para activar el entorno virtual:"
echo "  source venv/bin/activate"
echo ""
echo "Para ejecutar tests:"
echo "  pytest"
echo ""
echo "Para ejecutar el demo:"
echo "  python examples/demo.py"
echo ""
