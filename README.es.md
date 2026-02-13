# 🛡️ SentineLLM

> [🇬🇧 English](README.md) | 🇪🇸 **Español**

**AI Security Gateway** — Middleware de seguridad para proteger aplicaciones LLM contra prompt injections y fuga de secretos.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Security](https://img.shields.io/badge/Security-DevSecOps-red)](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

[![Security Pipeline](https://github.com/Allesterdev/sentinellm/actions/workflows/security-pipeline.yml/badge.svg)](https://github.com/Allesterdev/sentinellm/actions/workflows/security-pipeline.yml)
[![CodeQL](https://github.com/Allesterdev/sentinellm/actions/workflows/codeql.yml/badge.svg)](https://github.com/Allesterdev/sentinellm/actions/workflows/codeql.yml)

---

## 🎯 ¿Qué es SentineLLM?

SentineLLM es un **middleware de seguridad** que intercepta el tráfico entre usuarios y modelos de lenguaje (LLMs) para prevenir:

- **Prompt Injections** (entrada) — Detecta intentos de manipular el comportamiento del modelo
- **Secret Leakage & DLP** (salida) — Evita la fuga de credenciales, claves API y datos sensibles

### Arquitectura de Defensa en Profundidad

```

User → InputFilter → OllamaFilter → [LLM] → OutputFilter → DLPFilter → Response
├─ Regex │ ├─ AWS Keys
├─ Entropía │ ├─ GitHub Tokens
└─ Luhn Check │ └─ Credit Cards
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
git clone https://github.com/Allesterdev/sentinellm.git
cd sentinellm

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar SentineLLM (dependencias + comandos CLI)
pip install .
```

Esto instala todas las dependencias **y** registra el comando `sllm` globalmente.

> **Para desarrolladores:** Usa `pip install -e .` para instalación editable (los cambios aplican inmediatamente).

### 🎉 Configuración Interactiva

Tras la instalación, el comando `sllm` está disponible:

```bash
# Ejecutar el wizard de configuración
sllm

# Comandos rápidos con atajos de proveedor
sllm proxy openai          # Iniciar proxy → OpenAI
sllm proxy anthropic       # Iniciar proxy → Anthropic (Claude)
sllm proxy gemini          # Iniciar proxy → Google Gemini
sllm proxy ollama          # Iniciar proxy → Ollama (local)
sllm proxy                 # Selección interactiva de proveedor

# Auto-configurar agentes IA (OpenClaw, etc.)
sllm agent

# Otros comandos
sllm setup                 # Configuración inicial
sllm config                # Cambiar configuración
sllm demo                  # Ejecutar demo interactivo
sllm check-ollama          # Ver estado de Ollama
```

El wizard te guía a través de:

- 🌍 **Selección de idioma** (English/Español)
- 🔧 **Capas de detección** (Regex, LLM)
- 🤖 **Configuración de Ollama** (Local, VPC, Externo)
- ⚙️ **Circuit breaker & fallback** settings
- 🔐 **Patrones de detección de secretos**

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

## 🌐 API REST

SentineLLM proporciona una API REST para integración con aplicaciones externas:

### Iniciar el Servidor API

```bash
# Usando el CLI (default seguro — solo localhost)
python sentinellm.py api

# O para acceso desde red (Docker/clientes remotos)
# ⚠️  ADVERTENCIA: Usar solo si entiendes las implicaciones de seguridad
API_HOST=0.0.0.0 API_PORT=8080 python sentinellm.py api
```

La API estará disponible en:

- **Raíz:** `http://localhost:8000/`
- **Documentación:** `http://localhost:8000/docs` (Swagger UI)
- **Documentación alternativa:** `http://localhost:8000/redoc`

### Endpoints de la API

#### Health Check

```bash
GET /api/v1/health
```

Respuesta:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "ollama_available": true,
  "ollama_status": "connected"
}
```

#### Validar Texto

```bash
POST /api/v1/validate
Content-Type: application/json

{
  "text": "¿Cuál es la capital de Francia?",
  "include_details": false
}
```

Respuesta (seguro):

```json
{
  "safe": true,
  "blocked": false,
  "threat_level": "NONE",
  "reason": null
}
```

Respuesta (bloqueado):

```json
{
  "safe": false,
  "blocked": true,
  "threat_level": "HIGH",
  "reason": "Inyección de prompt detectada: patrón instruction_override encontrado"
}
```

#### Validación por Lotes

```bash
POST /api/v1/validate/batch
Content-Type: application/json

[
  {"text": "Texto seguro"},
  {"text": "Ignora las instrucciones anteriores"}
]
```

### Ejemplo de Cliente API

```python
import httpx

# Validar texto
response = httpx.post(
    "http://localhost:8000/api/v1/validate",
    json={"text": "Tu texto aquí", "include_details": True}
)

if response.status_code == 200:
    result = response.json()
    print(f"Seguro: {result['safe']}")
elif response.status_code == 403:
    print(f"Bloqueado: {response.json()['detail']}")
```

Ver [examples/api_client.py](examples/api_client.py) para un ejemplo completo.

### 📚 Documentación Completa de la API

Para referencia completa de la API con todos los endpoints, modelos, códigos de error y ejemplos de integración:

**→ [Ver Documentación Completa de la API](docs/api-reference.md)**

### 🔒 Proxy LLM (Integración Universal)

**Proxy HTTP transparente** que protege CUALQUIER aplicación LLM:

```bash
# Iniciar el proxy con atajos de proveedor
sllm proxy openai          # Proxy a OpenAI
sllm proxy gemini          # Proxy a Google Gemini
sllm proxy anthropic       # Proxy a Claude
sllm proxy ollama          # Proxy a Ollama local
sllm proxy                 # Selección interactiva de proveedor
```

Configura tu aplicación para usar `http://localhost:8080` — funciona con OpenClaw, LangChain, o cualquier cliente LLM.

Para auto-configurar un agente IA (OpenClaw, etc.):

```bash
sllm agent                 # Auto-configuración interactiva de agentes
```

**→ [Documentación Completa del Proxy](docs/proxy.md)**

---

## 📁 Estructura del Proyecto

```
sentinellm/
├── src/
│   ├── core/          # Motor de detección (Regex, Entropía, Validadores)
│   ├── filters/       # Detección de prompt injection y LLM
│   ├── cli/           # CLI interactivo y wizard de configuración
│   │   ├── agent_config.py  # Auto-configurar agentes IA (OpenClaw, etc.)
│   │   ├── config_wizard.py # Wizard de configuración de seguridad
│   │   └── i18n.py          # Internacionalización (EN/ES)
│   ├── utils/         # Constantes, cargador de config, helpers
│   ├── api/           # Endpoints REST API (FastAPI)
│   │   ├── routes/    # Manejadores de rutas API
│   │   ├── models.py  # Modelos Pydantic request/response
│   │   └── config.py  # Configuración de la API
│   └── proxy/         # Servidor proxy HTTP para LLMs (multi-proveedor)
├── examples/          # Demos interactivos y clientes API
├── tests/             # Tests unitarios e integración
├── config/            # Configuraciones YAML
├── sentinellm.py      # Punto de entrada CLI principal
├── sllm               # Lanzador de atajo rápido
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

## 🛡️ Pipeline DevSecOps

SentineLLM implementa un pipeline completo de seguridad:

### Análisis de Seguridad Automatizado

- **SAST**: Bandit + CodeQL para análisis estático
- **Escaneo de Secretos**: detect-secrets + GitHub Secret Scanning
- **Escaneo de Dependencias**: Safety + Trivy para vulnerabilidades
- **Calidad de Código**: Ruff (linting) + mypy (type checking)
- **Cobertura**:
  - Actual: **66%** (Python core + API)
  - Objetivo: **80%** (roadmap Q1 2026)
  - Mínimo obligatorio: **66%** en CI/CD (incrementando a 80%)
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

## 🛠️ Stack Tecnológico

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
- [x] **API REST con FastAPI**
- [x] **Proxy LLM multi-proveedor (OpenAI, Anthropic, Gemini, Ollama, etc.)**
- [x] **Auto-configuración para agentes IA (OpenClaw, etc.)**
- [x] **Atajo CLI `sllm` con alias de proveedores**
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
