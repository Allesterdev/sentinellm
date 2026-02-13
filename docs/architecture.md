# SentineLLM Architecture

## 🎯 Overview

SentineLLM is an **AI Security Gateway** that implements the **Defense in Depth** pattern to protect LLM applications against two main threats:

1. **Prompt Injections** (input)
2. **Secret Leakage & DLP** (output)

---

## 🏗️ Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Gateway                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │          Security Middleware (Interceptor)            │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Input Filters (Prompt)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ Regex Filter │→ │Entropy Check │→ │ Ollama ML Model │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      LLM Provider                            │
│              (OpenAI, Anthropic, Local)                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Output Filters (DLP)                        │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │Secret Detect │→ │  DLP Filter  │                         │
│  └──────────────┘  └──────────────┘                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                         User                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Main Components

### 1. Core Detection Engine

**Location:** `src/core/`

#### `detector.py` - Main Engine

- **Class:** `SecretDetector`
- **Responsibility:** Orchestrate multi-layer detection
- **Algorithm:**
  1. **Phase 1:** Fast regex (O(n)) on known patterns
  2. **Phase 2:** Shannon entropy analysis for suspicious strings
  3. **Phase 3:** Checksum validation (Luhn, AWS)
  4. **Phase 4:** Context-based confidence scoring

#### `entropy.py` - Entropy Analysis

- **Function:** `calculate_entropy(text) -> float`
- **Theoretical basis:** Shannon Entropy
- **Formula:** H(X) = -Σ p(x) \* log₂(p(x))
- **Usage:** Detect random strings typical of tokens/keys

#### `validator.py` - Specific Validators

- `luhn_check()` - Luhn algorithm for credit cards
- `validate_aws_key()` - AWS Access Keys format validation
- `validate_github_token()` - GitHub prefixes validation
- `validate_jwt()` - JWT structure validation

---

## 🔍 Detection Strategy

### Threat Levels (ThreatLevel Enum)

```python
NONE = "none"         # No threat
LOW = "low"           # Suspicious pattern, low entropy
MEDIUM = "medium"     # Partial regex match
HIGH = "high"         # Exact match (AKIA, Bearer)
CRITICAL = "critical" # Confirmed valid secret + high entropy
```

### Decision Matrix

| Regex Match | Validation | Entropy | Context | → Threat Level |
| ----------- | ---------- | ------- | ------- | -------------- |
| ✅          | ✅         | High    | ✅      | **CRITICAL**   |
| ✅          | ✅         | High    | ❌      | **HIGH**       |
| ✅          | ❌         | High    | ✅      | **MEDIUM**     |
| ✅          | ❌         | Low     | ✅      | **LOW**        |
| ❌          | -          | High    | ✅      | **MEDIUM**     |

---

## 🛡️ Detected Patterns (v0.1.0)

### Implemented

- ✅ AWS Access Keys (AKIA, ASIA, ABIA, ACCA)
- ✅ AWS Secret Keys
- ✅ GitHub Tokens (ghp*, gho*, ghs*, ghu*, ghr\_)
- ✅ Bearer Tokens
- ✅ JWT Tokens
- ✅ Credit Cards (Visa, Mastercard, Amex, etc.)
- ✅ Generic API Keys (by entropy)

### Upcoming

- 🔄 SSH Private Keys
- 🔄 Database Connection Strings
- 🔄 Slack Tokens
- 🔄 Google API Keys
- 🔄 Azure Keys

---

## 🧪 Testing Strategy

### Coverage: 98%

```
src/core/detector.py    98%    (93 stmts, 2 miss)
src/core/entropy.py     100%   (26 stmts)
src/core/validator.py   95%    (37 stmts, 2 miss)
```

### Test Categories

1. **Unit Tests** - Individual functions
2. **Integration Tests** - End-to-end flow
3. **Property-based Tests** (Hypothesis) - Generated edge cases
4. **Performance Tests** - Benchmarking (future)

---

## 📊 Performance

### Initial Benchmarks (estimated)

| Operation        | Time   | Throughput   |
| ---------------- | ------ | ------------ |
| Regex Scan (1KB) | ~1ms   | 1M chars/s   |
| Entropy Calc     | ~0.5ms | 2M chars/s   |
| Full Scan (1KB)  | ~5ms   | 200K chars/s |

**Target:** <10ms latency for 99% of requests

---

## 🔐 Design Principles

### SOLID

- **Single Responsibility:** Each module has a single responsibility
- **Open/Closed:** Easy to add new detectors without modifying existing ones
- **Liskov Substitution:** Composable detection layers with consistent interfaces
- **Interface Segregation:** Small and specific interfaces
- **Dependency Inversion:** Depend on abstractions, not implementations

### Defense in Depth

1. **Layer 1:** Regex (fast, known patterns)
2. **Layer 2:** Entropy (random strings)
3. **Layer 3:** Validators (algorithmic confirmation)
4. **Layer 4:** ML/Ollama (semantic detection) - future

---

## 🚀 Technical Roadmap

### Phase 1: Core Detection ✅

- [x] Project structure
- [x] Regex detection
- [x] Entropy analysis
- [x] Luhn/AWS validators
- [x] Tests with coverage

### Phase 2: REST API ✅

- [x] FastAPI endpoints
- [x] Request/Response schemas (Pydantic)
- [x] Health checks
- [ ] Rate limiting

### Phase 3: ML Integration ✅

- [x] Local Ollama setup
- [x] Prompt injection detection (regex + LLM)
- [x] Semantic analysis
- [ ] Fine-tuning with OWASP datasets

### Phase 4: LLM Proxy ✅

- [x] Multi-provider proxy (OpenAI, Anthropic, Gemini, Ollama)
- [x] Input + Output (DLP) validation
- [x] Agent auto-configuration (OpenClaw, etc.)
- [x] CLI shortcuts (`sllm proxy openai`, etc.)

### Phase 5: Observability (Planned)

- [ ] Structured logging (JSON)
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Alerting (PagerDuty/Slack)

### Phase 6: Cloud Deployment (Planned)

- [ ] Optimized Dockerfile
- [ ] Terraform for AWS
- [ ] ECS/Fargate deployment
- [ ] CloudWatch integration
- [ ] WAF rules

### Phase 6: Enterprise Features (Week 8+)

- [ ] Multi-tenancy
- [ ] RBAC (Role-Based Access Control)
- [ ] Compliance reporting (SOC2, GDPR)
- [ ] SIEM integration (Splunk/ELK)
- [ ] Immutable audit logs

---

## 🔧 Configuration

### Environment Variables (.env)

```bash
# API Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Detection Thresholds
ENTROPY_THRESHOLD=4.5
MIN_SECRET_LENGTH=16
THREAT_LEVEL_BLOCK=HIGH

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2

# AWS (deployment)
AWS_REGION=us-east-1
```

---

## 📈 Success Metrics

### KPIs

- **Detection Rate:** >95% of known secrets detected
- **False Positive Rate:** <2%
- **Latency p99:** <10ms
- **Throughput:** >10k requests/second
- **Availability:** 99.9% uptime

---

## 🤝 Contributions

### Areas for Improvement

1. **More patterns:** Add detection for other services
2. **Performance:** Optimize regex with lazy evaluation
3. **ML Models:** Fine-tuning Ollama models
4. **Documentation:** Complete Swagger/OpenAPI

---

## 📚 References

- [OWASP Top 10 for LLMs](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [Shannon Entropy](<https://en.wikipedia.org/wiki/Entropy_(information_theory)>)
- [Luhn Algorithm](https://en.wikipedia.org/wiki/Luhn_algorithm)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
