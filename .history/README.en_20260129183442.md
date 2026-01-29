```markdown
# 🛡️ SentineLLM

**AI Security Gateway** — Security middleware to protect LLM applications from prompt injections and secret leakage.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Security](https://img.shields.io/badge/Security-DevSecOps-red)](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

---

## 🎯 What is SentineLLM?

SentineLLM is a **security middleware** that intercepts traffic between users and language models (LLMs) to prevent:

- **Prompt Injections** (input) — Detects attempts to manipulate model behavior
- **Secret Leakage & DLP** (output) — Prevents leaking credentials, API keys and sensitive data

### Defense-in-Depth Architecture

```
User → InputFilter → OllamaFilter → [LLM] → OutputFilter → DLPFilter → Response
           ├─ Regex              │                  ├─ AWS Keys
           ├─ Entropy            │                  ├─ GitHub Tokens
           └─ Luhn Check         │                  └─ Credit Cards
                                 └─ ML Semantic Detection
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Linux (openSUSE Tumbleweed, Ubuntu, etc.)

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

# Copy environment variables example
cp .env.example .env

# Run tests
pytest

# Start the server (future)
# uvicorn src.main:app --reload
```

---

## 📁 Project Structure

```
sentinellm/
├── src/
│   ├── core/          # Detection engine (Regex, Entropy, Validators)
│   ├── filters/       # Input/output filters
│   ├── middleware/    # FastAPI middleware
│   ├── models/        # Pydantic models
│   └── api/           # REST endpoints
├── tests/             # Unit and integration tests
├── config/            # Environment configurations
└── docs/              # Technical documentation
```

---

## 🔍 Implemented Detections

| Type                   | Method           | Status |
| ---------------------- | ---------------- | ------ |
| AWS Access Keys (AKIA) | Regex + Checksum | ✅     |
| AWS Secret Keys        | Regex + Entropy  | ✅     |
| GitHub Tokens          | Regex            | ✅     |
| Bearer Tokens          | Regex            | ✅     |
| Credit Cards           | Luhn Algorithm   | ✅     |
| Prompt Injection ML    | Ollama           | 🔄     |

---

## 🛠️ Technology Stack

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
- [x] Luhn validator
- [x] Shannon entropy calculation
- [ ] REST API with FastAPI
- [ ] Ollama integration
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

Your Name - [@yourtwitter](https://twitter.com/yourtwitter)

Project: [https://github.com/yourusername/sentinellm](https://github.com/yourusername/sentinellm)

---

## 🙏 Acknowledgements

- [OWASP Top 10 for LLMs](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Ollama](https://ollama.ai/)

```
