# Arquitectura de SentineLLM

## 🎯 Visión General

SentineLLM es un **AI Security Gateway** que implementa el patrón de **Defensa en Profundidad** para proteger aplicaciones LLM contra dos amenazas principales:

1. **Prompt Injections** (entrada)
2. **Secret Leakage & DLP** (salida)

---

## 🏗️ Arquitectura de Capas

```
┌─────────────────────────────────────────────────────────────┐
│                         Usuario                              │
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
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │Secret Detect │→ │  Sanitizer   │→ │ Compliance Log  │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                         Usuario                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Componentes Principales

### 1. Core Detection Engine

**Ubicación:** `src/core/`

#### `detector.py` - Motor Principal

- **Clase:** `SecretDetector`
- **Responsabilidad:** Orquestar detección multicapa
- **Algoritmo:**
  1. **Fase 1:** Regex rápido (O(n)) sobre patrones conocidos
  2. **Fase 2:** Análisis de entropía Shannon para strings sospechosos
  3. **Fase 3:** Validación con checksums (Luhn, AWS)
  4. **Fase 4:** Scoring de confianza basado en contexto

#### `entropy.py` - Análisis de Entropía

- **Función:** `calculate_entropy(text) -> float`
- **Base teórica:** Entropía de Shannon
- **Fórmula:** H(X) = -Σ p(x) \* log₂(p(x))
- **Uso:** Detectar strings aleatorios típicos de tokens/claves

#### `validator.py` - Validadores Específicos

- `luhn_check()` - Algoritmo de Luhn para tarjetas de crédito
- `validate_aws_key()` - Validación de formato AWS Access Keys
- `validate_github_token()` - Validación de prefijos GitHub
- `validate_jwt()` - Validación de estructura JWT

---

## 🔍 Estrategia de Detección

### Niveles de Amenaza (ThreatLevel Enum)

```python
NONE = 0       # Sin amenaza
LOW = 1        # Patrón sospechoso, baja entropía
MEDIUM = 2     # Coincidencia parcial de regex
HIGH = 3       # Coincidencia exacta (AKIA, Bearer)
CRITICAL = 4   # Secreto válido confirmado + alta entropía
```

### Matriz de Decisión

| Regex Match | Validación | Entropía | Contexto | → Threat Level |
| ----------- | ---------- | -------- | -------- | -------------- |
| ✅          | ✅         | Alta     | ✅       | **CRITICAL**   |
| ✅          | ✅         | Alta     | ❌       | **HIGH**       |
| ✅          | ❌         | Alta     | ✅       | **MEDIUM**     |
| ✅          | ❌         | Baja     | ✅       | **LOW**        |
| ❌          | -          | Alta     | ✅       | **MEDIUM**     |

---

## 🛡️ Patrones Detectados (v0.1.0)

### Implementado

- ✅ AWS Access Keys (AKIA, ASIA, ABIA, ACCA)
- ✅ AWS Secret Keys
- ✅ GitHub Tokens (ghp*, gho*, ghs*, ghu*, ghr\_)
- ✅ Bearer Tokens
- ✅ JWT Tokens
- ✅ Tarjetas de Crédito (Visa, Mastercard, Amex, etc.)
- ✅ Generic API Keys (por entropía)

### Próximos

- 🔄 SSH Private Keys
- 🔄 Database Connection Strings
- 🔄 Slack Tokens
- 🔄 Google API Keys
- 🔄 Azure Keys

---

## 🧪 Testing Strategy

### Cobertura: 98%

```
src/core/detector.py    98%    (93 stmts, 2 miss)
src/core/entropy.py     100%   (26 stmts)
src/core/validator.py   95%    (37 stmts, 2 miss)
```

### Test Categories

1. **Unit Tests** - Funciones individuales
2. **Integration Tests** - Flujo end-to-end
3. **Property-based Tests** (Hypothesis) - Edge cases generados
4. **Performance Tests** - Benchmarking (futuro)

---

## 📊 Performance

### Benchmarks Iniciales (estimados)

| Operación        | Tiempo | Throughput   |
| ---------------- | ------ | ------------ |
| Regex Scan (1KB) | ~1ms   | 1M chars/s   |
| Entropy Calc     | ~0.5ms | 2M chars/s   |
| Full Scan (1KB)  | ~5ms   | 200K chars/s |

**Objetivo:** <10ms latencia para 99% de requests

---

## 🔐 Principios de Diseño

### SOLID

- **Single Responsibility:** Cada módulo tiene una única responsabilidad
- **Open/Closed:** Fácil añadir nuevos detectores sin modificar existentes
- **Liskov Substitution:** BaseFilter abstracto para filtros intercambiables
- **Interface Segregation:** Interfaces pequeñas y específicas
- **Dependency Inversion:** Depender de abstracciones, no implementaciones

### Defense in Depth

1. **Capa 1:** Regex (rápido, patrones conocidos)
2. **Capa 2:** Entropía (strings aleatorios)
3. **Capa 3:** Validadores (confirmación algorítmica)
4. **Capa 4:** ML/Ollama (detección semántica) - futuro

---

## 🚀 Roadmap Técnico

### Fase 1: Core Detection ✅ (ACTUAL)

- [x] Estructura del proyecto
- [x] Detección por Regex
- [x] Análisis de entropía
- [x] Validadores Luhn/AWS
- [x] Tests con 98% cobertura

### Fase 2: API REST (Semana 2)

- [ ] FastAPI endpoints
- [ ] Middleware de interceptación
- [ ] Request/Response schemas (Pydantic)
- [ ] Health checks
- [ ] Rate limiting

### Fase 3: ML Integration (Semana 3-4)

- [ ] Ollama local setup
- [ ] Prompt injection detection
- [ ] Semantic analysis
- [ ] Fine-tuning con datasets OWASP

### Fase 4: Observability (Semana 5)

- [ ] Structured logging (JSON)
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Alerting (PagerDuty/Slack)

### Fase 5: Cloud Deployment (Semana 6-7)

- [ ] Dockerfile optimizado
- [ ] Terraform para AWS
- [ ] ECS/Fargate deployment
- [ ] CloudWatch integration
- [ ] WAF rules

### Fase 6: Enterprise Features (Semana 8+)

- [ ] Multi-tenancy
- [ ] RBAC (Role-Based Access Control)
- [ ] Compliance reporting (SOC2, GDPR)
- [ ] SIEM integration (Splunk/ELK)
- [ ] Audit logs inmutables

---

## 🔧 Configuración

### Variables de Entorno (.env)

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

## 📈 Métricas de Éxito

### KPIs

- **Detection Rate:** >95% de secretos conocidos detectados
- **False Positive Rate:** <2%
- **Latency p99:** <10ms
- **Throughput:** >10k requests/segundo
- **Availability:** 99.9% uptime

---

## 🤝 Contribuciones

### Áreas de Mejora

1. **Más patrones:** Añadir detección de otros servicios
2. **Performance:** Optimizar regex con lazy evaluation
3. **ML Models:** Fine-tuning de modelos Ollama
4. **Documentación:** Swagger/OpenAPI completo

---

## 📚 Referencias

- [OWASP Top 10 for LLMs](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [Shannon Entropy](<https://en.wikipedia.org/wiki/Entropy_(information_theory)>)
- [Luhn Algorithm](https://en.wikipedia.org/wiki/Luhn_algorithm)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
