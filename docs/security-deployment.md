# 🔐 Security Deployment Guide

## Network Binding Security

### Default: Localhost Only (127.0.0.1)

By default, SentineLLM binds to **127.0.0.1** (localhost) for security:

```bash
python sentinellm.py proxy  # Listens on 127.0.0.1:8080
python sentinellm.py api    # Listens on 127.0.0.1:8000
```

**Why?**

- ✅ Only accessible from local machine
- ✅ Protected from network attacks
- ✅ No accidental exposure to internet
- ✅ Safe default for development

### When to Use 0.0.0.0 (All Interfaces)

Only bind to `0.0.0.0` in these scenarios:

#### ✅ Safe: Docker Containers

```bash
# In Docker, 0.0.0.0 is safe because of container isolation
API_HOST=0.0.0.0 python sentinellm.py api
```

#### ✅ Safe: Behind Reverse Proxy

```nginx
# nginx forwards to 127.0.0.1:8080
upstream sentinellm {
    server 127.0.0.1:8080;
}
```

#### ⚠️ Caution: Internal Network

```bash
# Only if firewall protects the service
API_HOST=0.0.0.0 python sentinellm.py api
```

#### 🔴 Dangerous: Public Internet

```bash
# NEVER expose directly to internet without authentication
# Use nginx/Apache with SSL + auth instead
```

## Security Checklist

### Development

- [x] Use `127.0.0.1` by default
- [x] `DEBUG=false` in production
- [x] No secrets in code or git
- [x] Use `.env` for configuration

### Production Deployment

#### Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Security: non-root user
RUN useradd -m -u 1000 sentinellm
USER sentinellm

# Bind to all interfaces (safe in container)
ENV API_HOST=0.0.0.0
ENV API_PORT=8000

EXPOSE 8000
CMD ["python", "sentinellm.py", "api"]
```

```yaml
# docker-compose.yml
services:
  sentinellm:
    build: .
    ports:
      - "127.0.0.1:8000:8000" # ← Bind to localhost only
    environment:
      - API_HOST=0.0.0.0
      - DEBUG=false
    restart: unless-stopped
```

#### Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/sentinellm
server {
    listen 443 ssl http2;
    server_name sentinellm.example.com;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    location / {
        proxy_pass http://127.0.0.1:8000;  # ← Proxy to localhost
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Systemd Service

```ini
# /etc/systemd/system/sentinellm.service
[Unit]
Description=SentineLLM Security Gateway
After=network.target

[Service]
Type=simple
User=sentinellm
Group=sentinellm
WorkingDirectory=/opt/sentinellm
Environment="API_HOST=127.0.0.1"
Environment="API_PORT=8000"
Environment="DEBUG=false"
ExecStart=/opt/sentinellm/.venv/bin/python sentinellm.py api
Restart=on-failure
RestartSec=5s

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/sentinellm/logs

[Install]
WantedBy=multi-user.target
```

## Environment Variables Security

### ✅ Good Practice

```bash
# .env (add to .gitignore)
API_HOST=127.0.0.1
API_PORT=8000
DEBUG=false
OLLAMA_API_KEY=your-key-here  # pragma: allowlist secret
```

### ❌ Bad Practice

```python
# NEVER hardcode secrets in code
API_KEY = "sk-1234567890abcdef"  # ← NO!  # pragma: allowlist secret
```

## Firewall Configuration

### UFW (Ubuntu/Debian)

```bash
# Block all by default
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow 22/tcp

# Don't expose SentineLLM directly
# Use nginx on port 443 instead
sudo ufw allow 443/tcp

sudo ufw enable
```

### iptables

```bash
# Drop all incoming by default
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Allow loopback
iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow SSH
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow HTTPS (nginx)
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

## Monitoring & Auditing

### Log Security Events

```python
# SentineLLM logs blocked threats
tail -f logs/sentinellm.log | grep "Blocked request"
```

### Monitor Network Connections

```bash
# Check what's listening
netstat -tlnp | grep python

# Should see:
# 127.0.0.1:8080  (proxy - localhost only)
# 127.0.0.1:8000  (api - localhost only)
```

### Fail2Ban Integration

```ini
# /etc/fail2ban/filter.d/sentinellm.conf
[Definition]
failregex = Blocked request from <HOST>
ignoreregex =
```

## Security Updates

```bash
# Keep dependencies updated
pip install --upgrade -r requirements.txt

# Check for vulnerabilities
pip-audit
safety check
trivy fs .
```

## Incident Response

If you suspect exposure:

1. **Immediate**: Stop the service

   ```bash
   systemctl stop sentinellm
   ```

2. **Investigate**: Check who connected

   ```bash
   journalctl -u sentinellm | grep "connection"
   ```

3. **Remediate**:
   - Change all API keys
   - Review logs for data exfiltration
   - Update firewall rules
   - Restart with secure config

4. **Report**: Document the incident

## Security Contact

Report vulnerabilities: [SECURITY.md](../SECURITY.md)
