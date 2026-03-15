# 🛡️ SentineLLM

> 🇬🇧 **English** | [🇪🇸 Español](README.es.md)

**AI Security Gateway** — Security middleware to protect LLM applications from prompt injections and secret leakage.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Security](https://img.shields.io/badge/Security-DevSecOps-red)](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

[![Security Pipeline](https://github.com/Allesterdev/sentinellm/actions/workflows/security-pipeline.yml/badge.svg)](https://github.com/Allesterdev/sentinellm/actions/workflows/security-pipeline.yml)
[![CodeQL](https://github.com/Allesterdev/sentinellm/actions/workflows/codeql.yml/badge.svg)](https://github.com/Allesterdev/sentinellm/actions/workflows/codeql.yml)
[![Status](https://img.shields.io/badge/Status-MVP%20%2F%20PoC-orange)](https://github.com/Allesterdev/sentinellm)

> ⚠️ **MVP / Proof of Concept** — Core features (proxy, secret redaction, prompt injection detection) are functional and tested. Ollama semantic analysis is experimental and pending full validation. Not recommended for production use without additional testing.
>
> 🧪 **Provider compatibility** — Currently only tested with **Google Gemini** (via OpenClaw). The proxy is designed to be compatible with OpenAI, Anthropic, Ollama and other providers, but these have not been verified in practice due to API costs. Contributions and test reports welcome.

---

## 🎯 What is SentineLLM?

SentineLLM is a **security middleware** that intercepts traffic between users and language models (LLMs) to prevent:

- **Prompt Injections** (input) — Detects attempts to manipulate model behavior
- **Secret Leakage & DLP** (output) — Prevents leaking credentials, API keys and sensitive data

### 🔐 Automatic Secret Redaction

Every secret detected in a message is **automatically replaced** with a descriptive placeholder before it ever reaches the LLM — no configuration required, always active:

```
User:     "My key is AIzaSyB-abc123..."
                ↓  SentineLLM intercepts
LLM gets: "My key is [GOOGLE_API_KEY_REMOVED_BY_SECURITY]"
```

This ensures the secret **never enters the LLM context or conversation history**, eliminating the cascading block problem on subsequent turns. Each unique secret triggers exactly one WARNING log entry — no spam.

### Defense-in-Depth Architecture

```
User → SecretRedactor → InputFilter → OllamaFilter → [LLM] → OutputFilter → DLPFilter → Response
         │               ├─ Regex                              ├─ AWS / GitHub / Credit Cards
         │               ├─ Entropy                           ├─ Google / OpenAI / Anthropic
         │               └─ Luhn Check                       ├─ Stripe / Slack / SendGrid
         │                                                    ├─ Groq / OpenRouter / HuggingFace
         ├─ Replace with placeholder                         └─ Generic high-entropy keys
         └─ Log once per unique secret (no spam)
                                       └─ ML Semantic Detection
```

---

## � Screenshots & Demo

> Screenshots and demo GIF will be added here once the UI stabilises.

<!-- To embed a screenshot:
![Description](docs/images/screenshot-name.png)

To embed an animated demo (GIF — supported by GitHub Markdown):
![Demo](docs/images/demo.gif)
-->

---

## �🚀 Quick Start

### Prerequisites

- Python 3.10+
- Linux (openSUSE Tumbleweed, Ubuntu, etc.)
- (Optional) [Ollama](https://ollama.com/) for deep semantic detection

### Installation

```bash
# Clone the repository
git clone https://github.com/Allesterdev/sentinellm.git
cd sentinellm

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install SentineLLM (dependencies + CLI commands)
pip install .
```

This installs all dependencies **and** registers the `sllm` command globally.

Once installed, run the interactive wizard to complete the setup:

```bash
sllm
```

The wizard will guide you through language, detection layers, provider, model, API key, and optionally configure your AI agent (OpenClaw, etc.).

> **For developers:** Use `pip install -e .` for editable install (changes take effect immediately).

### 🚀 First Steps: Proxy + Agent Setup

The main use case: route all AI agent traffic through SentineLLM.

1. **Start the proxy** — the wizard will ask for provider, model and API key:

   ```bash
   sllm proxy gemini        # or: openai, anthropic, ollama
   ```

   > The API key is stored in `~/.sentinellm.env` — never committed to the repo.

2. **Restart the agent gateway** so it picks up the new route:

   ```bash
   openclaw gateway restart
   ```

   > **Note:** `openclaw gateway restart` must run **after** the agent has been configured. The proxy can be started before or after — OpenClaw will route through it on the next gateway restart.

All traffic now flows: `OpenClaw → SentineLLM proxy → LLM` ✅

> **Agent not configured yet?** If you skipped agent setup during the `sllm` wizard, run `sllm agent` at any time to configure it, then restart the gateway.

> From this point, **all agent configuration is managed through SentineLLM**, not directly in OpenClaw.

### 📋 All Available Commands

```bash
sllm                       # Interactive setup wizard
sllm proxy openai          # Start proxy → OpenAI
sllm proxy anthropic       # Start proxy → Anthropic (Claude)
sllm proxy gemini          # Start proxy → Google Gemini
sllm proxy ollama          # Start proxy → Ollama (local, experimental)
sllm proxy                 # Interactive provider selection
sllm agent                 # Auto-configure AI agents
sllm setup                 # Initial configuration
sllm config                # Change configuration
sllm demo                  # Run interactive demo
sllm check-ollama          # Check Ollama status
```

The setup wizard also guides you through:

- 🌍 **Language selection** (English/Español)
- 🔧 **Detection layers** (Regex, LLM)
- 🤖 **Ollama configuration** (Local, VPC, External) _(experimental)_
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
# Using the CLI (secure default - localhost only)
python sentinellm.py api

# Or for network access (Docker/remote clients)
# ⚠️  WARNING: Only use if you understand security implications
API_HOST=0.0.0.0 API_PORT=8080 python sentinellm.py api
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

### 🔒 LLM Proxy

Configure your app to point to `http://localhost:8080` — compatible with OpenClaw, LangChain, or any LLM client. See [First Steps](#-first-steps-proxy--agent-setup) above for the full setup guide.

#### ⚙️ Environment Variables

| Variable                     | Values                                 | Default  | Description                                     |
| ---------------------------- | -------------------------------------- | -------- | ----------------------------------------------- |
| `SENTINELLM_MIN_BLOCK_LEVEL` | `LOW` / `MEDIUM` / `HIGH` / `CRITICAL` | `MEDIUM` | Minimum threat level to block prompt injections |
| `SENTINELLM_VALIDATE_OUTPUT` | `true` / `false`                       | `true`   | Also validate LLM responses (DLP)               |

**→ [Complete Proxy Documentation](docs/proxy.md)**

---

## 📁 Project Structure

```
sentinellm/
├── src/
│   ├── core/          # Detection engine (Regex, Entropy, Validators)
│   ├── filters/       # Prompt injection & LLM detection
│   ├── cli/           # Interactive CLI & configuration wizard
│   │   ├── agent_config.py  # Auto-configure AI agents (OpenClaw, etc.)
│   │   ├── config_wizard.py # Security configuration wizard
│   │   └── i18n.py          # Internationalization (EN/ES)
│   ├── utils/         # Constants, config loader, helpers
│   ├── api/           # REST API endpoints (FastAPI)
│   │   ├── routes/    # API route handlers
│   │   ├── models.py  # Pydantic request/response models
│   │   └── config.py  # API configuration
│   ├── proxy/         # HTTP proxy server for LLMs (multi-provider)
│   ├── middleware/    # FastAPI middleware (future)
│   └── models/        # Domain models (future)
├── examples/          # Interactive demos & API clients
├── tests/             # Unit and integration tests
├── config/            # YAML configurations
├── sentinellm.py      # Main CLI entry point
├── sllm               # Short alias launcher
└── docs/              # Technical documentation
```

---

## 🔍 Implemented Detections

### Secret Detection

| Type                       | Method           | Status |
| -------------------------- | ---------------- | ------ |
| AWS Access Keys (AKIA)     | Regex + Checksum | ✅     |
| AWS Secret Keys            | Regex + Entropy  | ✅     |
| GitHub Tokens              | Regex            | ✅     |
| Bearer Tokens              | Regex            | ✅     |
| JWT Tokens                 | Regex            | ✅     |
| Credit Cards               | Luhn Algorithm   | ✅     |
| Private Keys (PEM)         | Regex            | ✅     |
| Google API Keys (AIzaSy…)  | Regex            | ✅     |
| OpenAI API Keys (sk-…)     | Regex            | ✅     |
| Anthropic API Keys         | Regex            | ✅     |
| HuggingFace Tokens (hf\_…) | Regex            | ✅     |
| Stripe Keys                | Regex            | ✅     |
| Slack Tokens (xox…)        | Regex            | ✅     |
| SendGrid Keys (SG.…)       | Regex            | ✅     |
| Groq API Keys (gsk\_…)     | Regex            | ✅     |
| OpenRouter API Keys        | Regex            | ✅     |
| Generic high-entropy keys  | Shannon Entropy  | ✅     |

All detected secrets are **automatically redacted** and replaced with a descriptive placeholder (e.g. `[GOOGLE_API_KEY_REMOVED_BY_SECURITY]`) before the request reaches the LLM. Each unique secret triggers a single WARNING log entry — no repeated spam.

### Prompt Injection Detection

| Layer    | Method                      | Languages          | Coverage        | Status |
| -------- | --------------------------- | ------------------ | --------------- | ------ |
| Regex    | Pattern matching            | 5 (EN/ES/PT/FR/DE) | 41 patterns     | ✅     |
| Keywords | Weighted scoring (95 terms) | 5 (EN/ES/PT/FR/DE) | Accent-agnostic | ✅     |
| LLM      | Semantic analysis           | Any                | N/A             | ✅     |

**Multilingual Protection**: Detects attacks in English, Spanish, Portuguese, French, and German

The keyword layer uses **accent-normalized scoring** (`unicodedata.NFKD`) so `"instrucción"` and `"instruccion"` are treated identically. Score thresholds:

- `>= 4` → `LOW` (logged, allowed by default)
- `>= 8` → `MEDIUM` (blocked by default)
- `>= 14` → `HIGH`

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
  - Current: **82%** (Python core + API + CLI + Proxy)
  - Minimum threshold: **80%** enforced in CI/CD
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
- [x] **Multilingual prompt injection detection (5 languages) — regex + keyword scoring + accent normalization**
- [~] **Ollama integration for semantic analysis** _(experimental — pending full validation)_
- [x] **Interactive demo with test scenarios**
- [x] **Bilingual support (EN/ES)**
- [x] **Circuit breaker & fallback strategies**
- [x] **REST API with FastAPI**
- [x] **Multi-provider LLM proxy (OpenAI, Anthropic, Gemini, Ollama, etc.)**
- [x] **Auto-configuration for AI agents (OpenClaw, etc.)**
- [x] **CLI shortcut `sllm` with provider aliases**
- [x] **Automatic secret redaction with descriptive placeholder** (no config required, always active)
- [x] **Provider-specific patterns** (Google, OpenAI, Anthropic, HuggingFace, Stripe, Slack, SendGrid, Groq, OpenRouter)
- [x] **Deduplication of secret warnings** (one log entry per unique secret, no spam)
- [ ] Structured JSON logging _(prerequisite for Grafana + SIEM)_
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
