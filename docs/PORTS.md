# Port Architecture

## 🚀 Quick Start

**Want to skip the details and just get it working?**

```bash
./scripts/quick-start-openclaw.sh
```

This script will:

- ✅ Start the proxy on port 8080
- ✅ Show you exactly what to change in OpenClaw config
- ✅ Monitor incoming requests

---

## � Critical Understanding

**Two programs CANNOT share the same port on the same machine.**

- OpenClaw Gateway runs on **18789** (its own port, always)
- SentineLLM Proxy runs on **8080** (different port)
- You configure OpenClaw to **send LLM requests** to port 8080

```
┌─────────────────────────────────────────────────────────────┐
│                         User/Client                          │
│                  (connects to OpenClaw)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ Port 18789 (OpenClaw Gateway)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    OpenClaw Application                      │
│                  (Gateway: port 18789)                       │
│                                                              │
│  Configuration:                                              │
│  llm.baseUrl = "http://localhost:8080/v1"  ← Change this!   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ Port 8080 (LLM requests)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              SentineLLM Proxy (port 8080)                    │
│                    Validates prompts                         │
│                    Detects secrets                           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ HTTPS (443)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│           LLM Provider (OpenAI/Gemini/Claude)                │
│               https://api.openai.com                         │
└─────────────────────────────────────────────────────────────┘
```

---

## �🔌 Port Assignment

**Important:** Two programs **CANNOT** use the same port simultaneously on the same interface. Each service needs its own unique port.

### Default Ports

| Service              | Port  | Description                                    |
| -------------------- | ----- | ---------------------------------------------- |
| **OpenClaw Gateway** | 18789 | OpenClaw's native gateway (runs independently) |
| **SentineLLM Proxy** | 8080  | Security proxy for validation                  |
| **SentineLLM API**   | 8000  | Direct validation API (standalone)             |

---

## 🏗️ Architecture Flow

### Setup 1: OpenClaw + SentineLLM Proxy

```
User → OpenClaw (Gateway: 18789) → SentineLLM Proxy (8080) → LLM Provider
```

**What runs:**

- OpenClaw Gateway on port **18789** (user connects here)
- SentineLLM Proxy on port **8080** (OpenClaw connects here)

**OpenClaw configuration:**

```yaml
llm:
  provider: openai
  baseUrl: http://localhost:8080/v1 # ← Points to SentineLLM Proxy
  apiKey: ${OPENAI_API_KEY}
```

**Important:** OpenClaw's gateway (18789) keeps running. You only change the **LLM provider URL** to point to the proxy (8080).

---

## 📝 Step-by-Step: Configure OpenClaw

### Step 1: Find OpenClaw configuration file

OpenClaw configuration is usually in one of these locations:

```bash
~/.config/openclaw/config.yaml
~/.openclaw/config.yaml
~/openclaw/config.yaml
./config/openclaw.yaml  # In OpenClaw directory
```

Or find it:

```bash
find ~ -name "config.yaml" -path "*openclaw*" 2>/dev/null
```

### Step 2: Edit the LLM configuration

Open the config file:

```bash
nano ~/.config/openclaw/config.yaml
# or
code ~/.config/openclaw/config.yaml
```

**Find the `llm:` section** and modify it:

#### Before (direct to OpenAI/Gemini):

```yaml
llm:
  provider: openai # or google, anthropic, etc.
  apiKey: sk-your-key-here
  baseUrl: https://api.openai.com/v1
```

#### After (through SentineLLM Proxy):

```yaml
llm:
  provider: openai # Keep your original provider
  apiKey: sk-your-key-here # Keep your API key
  baseUrl: http://localhost:8080/v1 # ← CHANGE THIS to proxy
  headers:
    X-Target-URL: https://api.openai.com # ← Original LLM URL
```

**For Google Gemini:**

```yaml
llm:
  provider: google
  apiKey: your-google-ai-studio-key
  baseUrl: http://localhost:8080/v1 # ← Proxy
  headers:
    X-Target-URL: https://generativelanguage.googleapis.com # ← Gemini URL
```

### Step 3: Start SentineLLM Proxy

**In a separate terminal:**

```bash
cd ~/Proyectos/SentineLLM  # or wherever SentineLLM is installed
source venv/bin/activate
python sentinellm.py proxy

# You should see:
# 🛡️  SentineLLM Proxy Server
#    Listening on: http://127.0.0.1:8080
#    Forwarding to: https://api.openai.com
```

### Step 4: Start/Restart OpenClaw

```bash
# If OpenClaw is already running, restart it:
openclaw stop
openclaw start

# Or just:
openclaw restart
```

### Step 5: Verify it's working

Send a test message through OpenClaw. You should see the request appear in the SentineLLM proxy terminal.

**Test with a secret (should be blocked):**

```
My API key is sk-proj-1234567890abcdef
```

**Expected:** Proxy shows "Blocked request" and OpenClaw receives error 403.

**Test with normal message (should work):**

```
What is the capital of France?
```

**Expected:** Response from LLM (Paris).

---

## 🔧 Alternative: Environment Variables

If OpenClaw uses environment variables instead of config files:

```bash
# Set these before starting OpenClaw
export OPENAI_API_BASE="http://localhost:8080/v1"
export OPENAI_API_KEY="sk-your-real-key"  # pragma: allowlist secret

# Or for Gemini
export GOOGLE_API_BASE="http://localhost:8080/v1"
export GOOGLE_API_KEY="your-google-key"  # pragma: allowlist secret

# Then start OpenClaw
openclaw start
```

---

## 🔍 Troubleshooting OpenClaw Configuration

### Problem: OpenClaw doesn't connect to proxy

**Check 1: Is the proxy running?**

```bash
curl http://localhost:8080/health
# Should respond: {"status":"healthy","service":"sentinellm-proxy"}
```

**Check 2: Is OpenClaw using the right URL?**

```bash
# Check OpenClaw logs for the URL it's trying to connect to
tail -f ~/.openclaw/logs/openclaw.log
# You should see: Connecting to http://localhost:8080/v1
```

**Check 3: Check port conflicts**

```bash
# See what's listening on port 8080
lsof -i :8080
# Should show: python (sentinellm)

# See what's on 18789
lsof -i :18789
# Should show: openclaw (or node)
```

### Problem: Messages still go directly to OpenAI

**Cause:** OpenClaw is NOT using the proxy configuration.

**Fix:** Make sure you edited the RIGHT config file. OpenClaw might have multiple configs:

```bash
# Find all OpenClaw configs
find ~ -name "*.yaml" -o -name "*.yml" | grep -i openclaw

# Check which one is being used
openclaw status --verbose
```

### Problem: Proxy blocks everything / Nothing is blocked

**Check proxy logs:** The terminal running `python sentinellm.py proxy` shows all requests.

```bash
# In proxy terminal, you should see:
INFO:     127.0.0.1:52342 - "POST /v1/chat/completions HTTP/1.1" 200 OK  # ← Normal
WARNING:  Blocked request: secret_detector  # ← Blocked
```

**If you see nothing:** OpenClaw is NOT sending requests to the proxy.

---

### Setup 2: Direct App + SentineLLM Proxy

```
Your App → SentineLLM Proxy (8080) → LLM Provider
```

**What runs:**

- Your application
- SentineLLM Proxy on port **8080**

**App configuration:**

```python
openai.api_base = "http://localhost:8080"
```

---

### Setup 3: Direct API Validation

```
Your App → SentineLLM API (8000)
```

**What runs:**

- SentineLLM API on port **8000**

**Usage:**

```bash
curl -X POST http://localhost:8000/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{"text": "Your prompt here"}'
```

---

## ❌ Common Mistake: Port Conflict

### ❌ WRONG - Will fail:

```bash
# Terminal 1
python sentinellm.py proxy --port 8080

# Terminal 2
some-other-app --port 8080  # ❌ ERROR: Address already in use
```

### ✅ CORRECT - Different ports:

```bash
# Terminal 1
python sentinellm.py proxy --port 8080

# Terminal 2
openclaw start  # Uses its own port 18789 ✅
```

---

## 🔧 Troubleshooting

### Check what's using a port:

```bash
# Linux
lsof -i :8080

# Check all SentineLLM ports
lsof -i :8080 -i :8000 -i :18789
```

### Kill a process on a port:

```bash
# Find PID
lsof -t -i :8080

# Kill it
kill $(lsof -t -i :8080)
```

### Change SentineLLM Proxy port:

```bash
# Use a different port
python sentinellm.py proxy --port 9000
```

---

## 📝 Summary

- **OpenClaw Gateway (18789)**: Always runs, users connect here
- **SentineLLM Proxy (8080)**: Validation layer, OpenClaw connects here
- **Configuration**: OpenClaw → Proxy → LLM Provider
- **Never** try to run two services on the same port
