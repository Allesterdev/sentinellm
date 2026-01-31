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
- (Opcional) [Ollama](https://ollama.com/) para detección semántica profunda

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
```

### 🎉 Configuración Interactiva

SentineLLM incluye un CLI interactivo para configuración fácil:

```bash
# Ejecutar el wizard de configuración
python sentinellm.py

# O usar comandos específicos
python sentinellm.py setup          # Configuración inicial
python sentinellm.py config         # Cambiar configuración
python sentinellm.py demo           # Ejecutar demo interactivo
python sentinellm.py check-ollama   # Ver estado de Ollama
```

El wizard te guía a través de:

- 🌍 **Selección de idioma** (English/Español)
- 🔧 **Capas de detección** (Regex, LLM)
- 🤖 **Configuración de Ollama** (Local, VPC, Externo)
- ⚙️ **Circuit breaker & fallback** settings
- 🔐 **Detección de secretos** patrones

### 🎮 Demo Interactivo

Prueba los filtros de seguridad con escenarios predefinidos:

```bash
python examples/interactive_demo.py
```

El demo simula:

- ✅ Prompts seguros
- 🚨 Ataques de prompt injection (DAN, system override)
- 🔑 Fugas de secretos (claves AWS, tokens GitHub, tarjetas)
- 🔴 Ataques combinados

### Ejecutar Tests

```bash
# Ejecutar tests
pytest

# Con cobertura
pytest --cov=src
```

---

## 📁 Estructura del Proyecto

```
sentinellm/
├── src/
│   ├── core/          # Motor de detección (Regex, Entropía, Validadores)
│   ├── filters/       # Detección de prompt injection y LLM
│   ├── cli/           # CLI interactivo y wizard de configuración
│   ├── utils/         # Constantes, cargador de config, helpers
│   ├── middleware/    # FastAPI middleware (futuro)
│   ├── models/        # Modelos Pydantic (futuro)
│   └── api/           # Endpoints REST (futuro)
├── examples/          # Demos interactivos
├── tests/             # Tests unitarios e integración
├── config/            # Configuraciones YAML
├── sentinellm.py      # Punto de entrada CLI principal
└── docs/              # Documentación técnica
```

---

## 🔍 Detección Implementada

### Detección de Secretos

| Tipo                   | Método           | Estado |
| ---------------------- | ---------------- | ------ |
| AWS Access Keys (AKIA) | Regex + Checksum | ✅     |
| AWS Secret Keys        | Regex + Entropía | ✅     |
| GitHub Tokens          | Regex            | ✅     |
| Bearer Tokens          | Regex            | ✅     |
| JWT Tokens             | Regex            | ✅     |
| Tarjetas de Crédito    | Luhn Algorithm   | ✅     |
| Claves Privadas (PEM)  | Regex            | ✅     |

### Detección de Prompt Injection

| Capa  | Método             | Idiomas            | Patrones | Estado |
| ----- | ------------------ | ------------------ | -------- | ------ |
| Regex | Pattern matching   | 5 (EN/ES/PT/FR/DE) | 41       | ✅     |
| LLM   | Análisis semántico | Cualquiera         | N/A      | ✅     |

**Protección Multilingüe**: Detecta ataques en inglés, español, portugués, francés y alemán

- 🇬🇧 Sobreescritura de instrucciones (ignore, disregard, forget)
- 🇯🇵 Manipulación de rol (actúa como, ahora eres, finge)
- 🔴 Intentos de jailbreak (DAN, STAN, sin restricciones)
- ⚙️ Inyección de tokens de sistema (<system>, |im_start|)

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
- [x] Validador Luhn para tarjetas de crédito
- [x] Cálculo de entropía Shannon
- [x] **CLI interactivo con wizard de configuración**
- [x] **Detección multilingüe de prompt injection (5 idiomas)**
- [x] **Integración con Ollama para análisis semántico**
- [x] **Demo interactivo con escenarios de prueba**
- [x] **Soporte bilingüe (EN/ES)**
- [x] **Circuit breaker y estrategias de fallback**
- [ ] API REST con FastAPI
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

Oscar Campoy Ballester

- 💼 LinkedIn: [oscar-campoy-ballester-sec](https://www.linkedin.com/in/oscar-campoy-ballester-sec)
- 📧 Email: oscarcampoy.dev@gmail.com

Proyecto: [https://github.com/Allesterdev/sentinellm](https://github.com/Allesterdev/sentinellm)

---

## 🙏 Agradecimientos

- [OWASP Top 10 for LLMs](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Ollama](https://ollama.ai/)
