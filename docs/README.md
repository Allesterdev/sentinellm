# 📚 SentineLLM Documentation

Welcome to the SentineLLM documentation! This guide will help you understand, deploy, and integrate SentineLLM into your applications.

## 📖 Table of Contents

### Getting Started

- [Main README](../README.md) - Project overview and quick start
- [Spanish README](../README.es.md) - Documentación en español

### Architecture & Design

- [Architecture Overview](architecture.md) - System design and components
- [Security Pipeline](security-cicd.md) - CI/CD security workflow

### API Documentation

- **[API Reference](api-reference.md)** ⭐ - Complete REST API documentation
  - Endpoints
  - Request/Response models
  - Error codes
  - Integration examples (Python, JavaScript, Go, Ruby, cURL)
  - Rate limits and quotas

### Integration Guides

- 🚀 **[Quick Start Script](../scripts/quick-start-openclaw.sh)** - One-command setup for OpenClaw
- [OpenClaw Integration](openclaw-integration.md) - Connect with OpenClaw Gateway
- [Port Architecture](PORTS.md) - Understanding port usage and avoiding conflicts ⚠️
- [OpenClaw Config Example](../examples/openclaw-config.yaml) - Ready-to-use configuration 📋
- [Advanced API Client](../examples/advanced_api_client.py) - Production-ready Python client

### Examples

- [Interactive Demo](../examples/demo.py) - Command-line demo
- [Interactive CLI](../examples/interactive_demo.py) - Full interactive experience
- [Basic API Client](../examples/api_client.py) - Simple HTTP client
- [Advanced API Client](../examples/advanced_api_client.py) - Async, retry, monitoring

## 🚀 Quick Links

### For Developers

- **New to SentineLLM?** → Start with [README](../README.md)
- **Building an integration?** → Read [API Reference](api-reference.md)
- **Using Python?** → Check [Advanced API Client](../examples/advanced_api_client.py)
- **Using OpenClaw?** → See [OpenClaw Integration](openclaw-integration.md)

### For DevOps/Security

- **Setting up CI/CD?** → Follow [Security Pipeline](security-cicd.md)
- **Understanding architecture?** → Read [Architecture](architecture.md)
- **Deploying to production?** → See [API Reference - Production](api-reference.md#configuración-de-producción)

### For Product Managers

- **What does it do?** → [README - What is SentineLLM?](../README.md#-what-is-sentinellm)
- **How does it work?** → [Architecture](architecture.md)
- **Use cases?** → [API Reference - Integration Examples](api-reference.md#-ejemplos-de-integración)

## 📂 Documentation Structure

```
docs/
├── README.md                      # This file (documentation index)
├── api-reference.md               # Complete REST API reference ⭐
├── architecture.md                # System architecture
├── security-cicd.md               # Security pipeline
└── openclaw-integration.md        # OpenClaw integration guide

examples/
├── demo.py                        # Basic demo
├── interactive_demo.py            # Interactive CLI
├── api_client.py                  # Simple HTTP client
└── advanced_api_client.py         # Advanced async client ⭐
```

## 🎯 Use Cases

### 1. Protecting LLM Applications

```python
# Before calling LLM, validate user input
result = await client.validate(user_prompt)
if result.safe:
    llm_response = await openai.chat.completions.create(...)
```

### 2. API Gateway Integration

```
User → API Gateway → SentineLLM → LLM Service
                     ↓
                   Block if unsafe
```

### 3. Multi-Agent Systems

```python
# Validate communication between agents
for message in agent_messages:
    if not await validate(message):
        raise SecurityError("Malicious agent detected")
```

### 4. RAG Pipeline Security

```python
# Validate queries before vector search
if await validate_query(user_query):
    results = vector_db.search(user_query)
    context = build_context(results)
    response = llm.generate(context)
```

## 🔧 Configuration

### Basic Setup

```yaml
# config/security_config.yaml
prompt_injection:
  enabled: true
  layers:
    regex:
      enabled: true
    llm:
      enabled: true

secret_detection:
  enabled: true
  patterns:
    - aws
    - github
    - jwt
```

### API Configuration

```bash
# Environment variables
# Production settings (Docker/network access)
# ⚠️  Only expose to network if needed
export API_HOST=0.0.0.0  # Use 127.0.0.1 for localhost only
export API_PORT=8000
export API_WORKERS=4

# Start API
python sentinellm.py api
```

## 🛠️ Development

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific module
pytest tests/unit/test_detector.py
```

### Code Quality

```bash
# Linting
ruff check src/

# Type checking
mypy src/

# Security scan
bandit -r src/
```

## 📊 Monitoring

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### Metrics (Coming Soon)

- Request latency
- Validation throughput
- Detection rates by layer
- False positive rates

## 🤝 Contributing

We welcome contributions! Areas where we need help:

- [ ] Additional language clients (Java, C#, PHP)
- [ ] Kubernetes deployment manifests
- [ ] Terraform modules
- [ ] Grafana dashboards
- [ ] More integration examples

## 📞 Support

- **Documentation Issues**: Open an issue on [GitHub](https://github.com/yourusername/SentineLLM/issues)
- **API Questions**: See [API Reference](api-reference.md)
- **Integration Help**: Check [OpenClaw Integration](openclaw-integration.md)

## 📄 License

SentineLLM is licensed under the MIT License. See [LICENSE](../LICENSE) for details.

---

**Last Updated**: February 2026
**Version**: 0.1.0
