# 🛡️ SentineLLM

> 🇬🇧 **English** | [🇪🇸 Español](README.es.md)

**AI Security Gateway** — Security middleware to protect LLM applications from prompt injections and secret leakage.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Security](https://img.shields.io/badge/Security-DevSecOps-red)](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

[![Security Pipeline](https://github.com/Allesterdev/sentinellm/actions/workflows/security-pipeline.yml/badge.svg)](https://github.com/Allesterdev/sentinellm/actions/workflows/security-pipeline.yml)
[![CodeQL](https://github.com/Allesterdev/sentinellm/actions/workflows/codeql.yml/badge.svg)](https://github.com/Allesterdev/sentinellm/actions/workflows/codeql.yml)

---

## 🎯 What is SentineLLM?

SentineLLM is a **security middleware** that intercepts traffic between users and language models (LLMs) to prevent:

- **Prompt Injections** (input) — Detects attempts to manipulate model behavior
- **Secret Leakage & DLP** (output) — Prevents leaking credentials, API keys and sensitive data

### Defense-in-Depth Architecture

```

User → InputFilter → OllamaFilter → [LLM] → OutputFilter → DLPFilter → Response
├─ Regex │ ├─ AWS Keys
├─ Entropy │ ├─ GitHub Tokens
└─ Luhn Check │ └─ Credit Cards
└─ ML Semantic Detection

```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Linux (openSUSE Tumbleweed, Ubuntu, etc.)
- (Optional) [Ollama](https://ollama.com/) for deep semantic detection

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/sentinellm.git
cd sentinellm

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 🎉 Interactive Setup

SentineLLM includes an interactive CLI for easy configuration:

```bash
# Run the interactive setup wizard
python sentinellm.py

# Or use specific commands
python sentinellm.py setup          # Initial configuration
python sentinellm.py config         # Change configuration
python sentinellm.py demo           # Run interactive demo
python sentinellm.py check-ollama   # Check Ollama status
```

The wizard guides you through:

- 🌍 **Language selection** (English/Español)
- 🔧 **Detection layers** (Regex, LLM)
- 🤖 **Ollama configuration** (Local, VPC, External)
- ⚙️ **Circuit breaker & fallback** settings
- 🔐 **Secret detection** patterns

### 🎮 Interactive Demo

Test the security filters with predefined scenarios:

```bash
python examples/interactive_demo.py
```

The demo simulates:

- ✅ Safe prompts
- 🚨 Prompt injection attacks (DAN, system override)
- 🔑 Secret leaks (AWS keys, GitHub tokens, credit cards)
- 🔴 Combined attacks

### Running Tests

```bash
# Run tests
pytest

# With coverage
pytest --cov=src
```

---

## 🌐 REST API

SentineLLM provides a REST API for integration with external applications:

### Starting the API Server

```bash
# Using the startup script
./start_api.sh

# Or directly with Python
python3 run_api.py

# Or with custom host/port
API_HOST=0.0.0.0 API_PORT=8080 python3 run_api.py
```

The API will be available at:

- **Root:** `http://localhost:8000/`
- **Documentation:** `http://localhost:8000/docs` (Swagger UI)
- **Alternative docs:** `http://localhost:8000/redoc`

### API Endpoints

#### Health Check

```bash
GET /api/v1/health
```

Response:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "ollama_available": true,
  "ollama_status": "connected"
}
```

#### Validate Text

```bash
POST /api/v1/validate
Content-Type: application/json

{
  "text": "What is the capital of France?",
  "include_details": false
}
```

Response (safe):

```json
{
  "safe": true,
  "blocked": false,
  "threat_level": "NONE",
  "reason": null
}
```

Response (blocked):

```json
{
  "safe": false,
  "blocked": true,
  "threat_level": "HIGH",
  "reason": "Prompt injection detected: instruction_override pattern matched"
}
```

#### Batch Validation

```bash
POST /api/v1/validate/batch
Content-Type: application/json

[
  {"text": "Safe text"},
  {"text": "Ignore previous instructions"}
]
```

### API Client Example

```python
import httpx

# Validate text
response = httpx.post(
    "http://localhost:8000/api/v1/validate",
    json={"text": "Your text here", "include_details": True}
)

if response.status_code == 200:
    result = response.json()
    print(f"Safe: {result['safe']}")
elif response.status_code == 403:
    print(f"Blocked: {response.json()['detail']}")
```

See [examples/api_client.py](examples/api_client.py) for a complete example.

### 📚 Full API Documentation

For complete API reference with all endpoints, models, error codes, and integration examples:

**→ [View Complete API Documentation](docs/api-reference.md)**

### 🔌 OpenClaw Plugin

TypeScript plugin for seamless integration with OpenClaw AI agents:

```bash
cd plugins/openclaw
npm install
npm run build
```

**Usage:**

```typescript
import { createSentineLLMPlugin } from "@sentinellm/openclaw-plugin";

const security = createSentineLLMPlugin({
  apiUrl: "http://localhost:8000",
  blockOnError: true,
});

// Integrate with OpenClaw agent
const agent = new Agent({
  plugins: [
    {
      onInboundMessage: (msg) => security.onInboundMessage(msg),
      onOutboundMessage: (msg) => security.onOutboundMessage(msg),
    },
  ],
});
```

**→ [OpenClaw Plugin Documentation](plugins/openclaw/README.md)**

---

## 📁 Project Structure

```
sentinellm/
├── src/
│   ├── core/          # Detection engine (Regex, Entropy, Validators)
│   ├── filters/       # Prompt injection & LLM detection
│   ├── cli/           # Interactive CLI & configuration wizard
│   ├── utils/         # Constants, config loader, helpers
│   ├── api/           # REST API endpoints (FastAPI)
│   │   ├── routes/    # API route handlers
│   │   ├── models.py  # Pydantic request/response models
│   │   └── config.py  # API configuration
│   ├── middleware/    # FastAPI middleware (future)
│   └── models/        # Domain models (future)
├── plugins/           # Integration plugins
│   └── openclaw/      # OpenClaw TypeScript plugin
├── examples/          # Interactive demos & API clients
├── tests/             # Unit and integration tests
├── config/            # YAML configurations
├── run_api.py         # API server entry point
├── start_api.sh       # API startup script
├── sentinellm.py      # Main CLI entry point
└── docs/              # Technical documentation
```

---

## 🔍 Implemented Detections

### Secret Detection

| Type                   | Method           | Status |
| ---------------------- | ---------------- | ------ |
| AWS Access Keys (AKIA) | Regex + Checksum | ✅     |
| AWS Secret Keys        | Regex + Entropy  | ✅     |
| GitHub Tokens          | Regex            | ✅     |
| Bearer Tokens          | Regex            | ✅     |
| JWT Tokens             | Regex            | ✅     |
| Credit Cards           | Luhn Algorithm   | ✅     |
| Private Keys (PEM)     | Regex            | ✅     |

### Prompt Injection Detection

| Layer | Method            | Languages          | Patterns | Status |
| ----- | ----------------- | ------------------ | -------- | ------ |
| Regex | Pattern matching  | 5 (EN/ES/PT/FR/DE) | 41       | ✅     |
| LLM   | Semantic analysis | Any                | N/A      | ✅     |

**Multilingual Protection**: Detects attacks in English, Spanish, Portuguese, French, and German

- 🇬🇧 Instruction override (ignore, disregard, forget)
- 🇯🇵 Role manipulation (act as, you are now, pretend)
- 🔴 Jailbreak attempts (DAN, STAN, without restrictions)
- ⚙️ System token injection (<system>, |im_start|)

---

## � DevSecOps Pipeline

SentineLLM implements a comprehensive security pipeline:

### Automated Security Checks

- **SAST**: Bandit + CodeQL for static analysis
- **Secret Scanning**: detect-secrets + GitHub Secret Scanning
- **Dependency Scanning**: Safety + Trivy for vulnerabilities
- **Code Quality**: Ruff (linting) + mypy (type checking)
- **Coverage**:
  - Current: **70%** (Python core + API)
  - Target: **80%** (Q1 2026 roadmap)
  - Minimum threshold: **70%** enforced in CI/CD
- **License Compliance**: Automated license checking

### CI/CD Workflows

- 🛡️ **Security Pipeline**: Runs on every push/PR
- 🔬 **CodeQL Analysis**: Advanced semantic SAST (daily)
- 📦 **Dependabot**: Automated dependency updates (weekly)

### Local Development

```bash
# Run all security checks locally
./scripts/security-check.sh

# Install pre-commit hooks
pre-commit install
```

See [Security CI/CD Guide](docs/security-cicd.md) for detailed documentation.

---

## �🛠️ Technology Stack

- **Framework**: FastAPI
- **Validation**: Pydantic v2
- **Testing**: Pytest + Hypothesis
- **Security**: Bandit, detect-secrets
- **Code Quality**: Ruff, mypy
- **AI**: Ollama (local LLM)
- **Cloud**: AWS (future)

---

## 📊 Roadmap

- [x] Project structure
- [x] Secret detection via Regex
- [x] Luhn validator for credit cards
- [x] Shannon entropy calculation
- [x] **Interactive CLI with configuration wizard**
- [x] **Multilingual prompt injection detection (5 languages)**
- [x] **Ollama integration for semantic analysis**
- [x] **Interactive demo with test scenarios**
- [x] **Bilingual support (EN/ES)**
- [x] **Circuit breaker & fallback strategies**
- [x] **REST API with FastAPI**
- [ ] Logging middleware
- [ ] Grafana dashboard
- [ ] Deployment to AWS
- [ ] SIEM integration

---

## 🤝 Contributing

Contributions are welcome. Please:

1. Fork the project
2. Create a branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 📫 Contact

Oscar Campoy Ballester

- 💼 LinkedIn: [oscar-campoy-ballester-sec](https://www.linkedin.com/in/oscar-campoy-ballester-sec)
- 📧 Email: oscarcampoy.dev@gmail.com

Project: [https://github.com/Allesterdev/sentinellm](https://github.com/Allesterdev/sentinellm)

---

## 🙏 Acknowledgements

- [OWASP Top 10 for LLMs](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Ollama](https://ollama.ai/)

```

```
