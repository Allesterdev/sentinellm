# OpenClaw Configuration on Ubuntu VM

## Locate configuration file

OpenClaw usually stores its configuration in one of these locations:

```bash
# Search for OpenClaw configuration
~/.config/openclaw/config.json
~/.openclaw/config.json
~/openclaw/config.json
```

Or you can search for it:

```bash
find ~ -name "*config*" -path "*openclaw*" 2>/dev/null
```

## Configure OpenClaw to use the proxy

1. **Edit the configuration** (example with nano):

```bash
nano ~/.config/openclaw/config.json
```

2. **Change the provider URL**:

**BEFORE:**

<!-- pragma: allowlist secret -->

```json
{
  "providers": {
    "openai": {
      "apiUrl": "https://api.openai.com",
      "apiKey": "YOUR_OPENAI_API_KEY" <!-- pragma: allowlist secret -->
    }
  }
}
```

**AFTER:**

<!-- pragma: allowlist secret -->

```json
{
  "providers": {
    "openai": {
      "apiUrl": "http://127.0.0.1:8080",
      "apiKey": "YOUR_OPENAI_API_KEY" <!-- pragma: allowlist secret -->
    }
  }
}
```

3. **Save and restart OpenClaw**

## Verify it works

1. **Start the proxy in one terminal:**

```bash
cd ~/sentinellm  # or wherever it's installed
source venv/bin/activate
python sentinellm.py proxy
```

2. **In another terminal, run OpenClaw:**

```bash
openclaw
```

3. **Test with a message containing a secret:**

```
Hello, my API key is sk-proj-1234567890abcdefghijklmnopqrstuvwxyz
```

**Expected result:** The proxy should show a log blocking the message and OpenClaw should receive a 403 error.

## Troubleshooting

### If it still doesn't work:

1. **Verify the proxy is listening:**

```bash
curl http://127.0.0.1:8080/health
# Should respond: {"status":"healthy","service":"sentinellm-proxy"}
```

2. **Check proxy logs:**
   - Each incoming request should appear
   - If nothing appears = OpenClaw is not using the proxy

3. **Check environment variables:**

```bash
env | grep -i openai
# Make sure there is no OPENAI_API_URL overriding the config
```
