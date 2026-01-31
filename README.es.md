# 🛡️ SentineLLM

> [🇬🇧 English](README.md) | 🇪🇸 **Español**

**AI Security Gateway** - Middleware de seguridad para proteger aplicaciones LLM contra prompt injections y fuga de secretos.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Security](https://img.shields.io/badge/Security-DevSecOps-red)](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

[![Security Pipeline](https://github.com/Allesterdev/sentinellm/actions/workflows/security-pipeline.yml/badge.svg)](https://github.com/Allesterdev/sentinellm/actions/workflows/security-pipeline.yml)
[![CodeQL](https://github.com/Allesterdev/sentinellm/actions/workflows/codeql.yml/badge.svg)](https://github.com/Allesterdev/sentinellm/actions/workflows/codeql.yml)
[![codecov](https://codecov.io/gh/Allesterdev/sentinellm/branch/main/graph/badge.svg)](https://codecov.io/gh/Allesterdev/sentinellm)

---

## 🎯 ¿Qué es SentineLLM?

SentineLLM es un **middleware de seguridad** que intercepta el tráfico entre usuarios y modelos de lenguaje (LLMs) para prevenir:

- **Prompt Injections** (entrada) - Detecta intentos de manipular el comportamiento del modelo
- **Secret Leakage & DLP** (salida) - Evita la fuga de credenciales, claves API y datos sensibles

### Arquitectura de Defensa en Profundidad

```
Usuario → InputFilter → OllamaFilter → [LLM] → OutputFilter → DLPFilter → Response
           ├─ Regex              │                  ├─ AWS Keys
           ├─ Entropía           │                  ├─ GitHub Tokens
           └─ Luhn Check         │                  └─ Credit Cards
                                 └─ ML Semantic Detection
```

---

## 🚀 Quick Start

### Prerequisitos

- Python 3.10+
- Linux (openSUSE Tumbleweed, Ubuntu, etc.)

### Instalación

```bash
# Clonar el repositorio
git clone https://github.com/yourusername/sentinellm.git
cd sentinellm

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env

# Ejecutar tests
pytest

# Iniciar el servidor (futuro)
# uvicorn src.main:app --reload
```

---

## 📁 Estructura del Proyecto

```
sentinellm/
├── src/
│   ├── core/          # Motor de detección (Regex, Entropía, Validadores)
│   ├── filters/       # Filtros de entrada/salida
│   ├── middleware/    # FastAPI middleware
│   ├── models/        # Modelos Pydantic
│   └── api/           # Endpoints REST
├── tests/             # Tests unitarios e integración
├── config/            # Configuración por entorno
└── docs/              # Documentación técnica
```

---

## 🔍 Detección Implementada

| Tipo                   | Método           | Estado |
| ---------------------- | ---------------- | ------ |
| AWS Access Keys (AKIA) | Regex + Checksum | ✅     |
| AWS Secret Keys        | Regex + Entropía | ✅     |
| GitHub Tokens          | Regex            | ✅     |
| Bearer Tokens          | Regex            | ✅     |
| Tarjetas de Crédito    | Luhn Algorithm   | ✅     |
| Prompt Injection ML    | Ollama           | 🔄     |

---

## � Pipeline DevSecOps

SentineLLM implementa un pipeline completo de seguridad:

### Análisis de Seguridad Automatizado

- **SAST**: Bandit + CodeQL para análisis estático
- **Escaneo de Secretos**: detect-secrets + GitHub Secret Scanning
- **Escaneo de Dependencias**: Safety + Trivy para vulnerabilidades
- **Calidad de Código**: Ruff (linting) + mypy (type checking)
- **Cobertura**: Umbral mínimo del 80% obligatorio
- **Cumplimiento de Licencias**: Verificación automática de licencias

### Workflows CI/CD

- 🛡️ **Security Pipeline**: Se ejecuta en cada push/PR
- 🔬 **CodeQL Analysis**: SAST semántico avanzado (diario)
- 📦 **Dependabot**: Actualizaciones automáticas de dependencias (semanal)

### Desarrollo Local

```bash
# Ejecutar todos los checks de seguridad localmente
./scripts/security-check.sh

# Instalar hooks de pre-commit
pre-commit install
```

Consulta la [Guía de CI/CD de Seguridad](docs/security-cicd.md) para documentación detallada.

---

## �🛠️ Stack Tecnológico

- **Framework**: FastAPI
- **Validación**: Pydantic v2
- **Testing**: Pytest + Hypothesis
- **Security**: Bandit, detect-secrets
- **Code Quality**: Ruff, mypy
- **AI**: Ollama (local LLM)
- **Cloud**: AWS (futuro)

---

## 📊 Roadmap

- [x] Estructura del proyecto
- [x] Detección de secretos por Regex
- [x] Validador Luhn
- [x] Cálculo de entropía Shannon
- [ ] API REST con FastAPI
- [ ] Integración con Ollama
- [ ] Middleware de logging
- [ ] Dashboard Grafana
- [ ] Deployment en AWS
- [ ] Integración SIEM

---

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## 📝 Licencia

Distribuido bajo la licencia MIT. Ver `LICENSE` para más información.

---

## 📫 Contacto

Tu Nombre - [@yourtwitter](https://twitter.com/yourtwitter)

Proyecto: [https://github.com/yourusername/sentinellm](https://github.com/yourusername/sentinellm)

---

## 🙏 Agradecimientos

- [OWASP Top 10 for LLMs](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Ollama](https://ollama.ai/)
