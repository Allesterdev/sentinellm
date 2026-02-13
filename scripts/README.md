# 🛠️ SentineLLM Scripts

Collection of useful scripts for development, testing, and deployment.

## 🚀 Quick Start & Deployment

### `quick-start-openclaw.sh`

**One-command setup for OpenClaw integration**

```bash
./scripts/quick-start-openclaw.sh
```

**What it does:**

- ✅ Validates SentineLLM installation
- ✅ Checks if port 8080 is available
- ✅ Starts the proxy on port 8080
- ✅ Shows you exactly what to configure in OpenClaw
- ✅ Monitors incoming requests in real-time
- ✅ Automatically cleans up on exit (Ctrl+C)

**Perfect for:**

- First-time OpenClaw setup
- Quick testing
- Troubleshooting connection issues

---

## 🧪 Development & Testing

### `setup_dev.sh`

Set up the development environment with all dependencies:

```bash
./scripts/setup_dev.sh
```

**What it does:**

- Creates Python virtual environment
- Installs all dependencies (dev + production)
- Sets up pre-commit hooks
- Validates installation

### `run_tests.sh`

Run the complete test suite:

```bash
./scripts/run_tests.sh
```

**What it does:**

- Unit tests with pytest
- Code coverage report
- Integration tests
- Generates HTML coverage report in `htmlcov/`

**Options:**

```bash
./scripts/run_tests.sh --verbose    # Show detailed output
./scripts/run_tests.sh --fast       # Skip slow tests
```

---

## 🔒 Security

### `security-check.sh`

Run security scans and vulnerability checks:

```bash
./scripts/security-check.sh
```

**What it does:**

- Scans dependencies for known vulnerabilities (safety)
- Static code analysis (bandit)
- Configuration security checks
- Generates security report

**Perfect for:**

- CI/CD pipelines
- Pre-deployment validation
- Security audits

---

## 📝 Usage Tips

### Make all scripts executable

```bash
chmod +x scripts/*.sh
```

### Run from project root

All scripts are designed to be run from the project root directory:

```bash
cd /path/to/SentineLLM
./scripts/quick-start-openclaw.sh
```

### Integration with CI/CD

Example GitHub Actions workflow:

```yaml
- name: Setup environment
  run: ./scripts/setup_dev.sh

- name: Run tests
  run: ./scripts/run_tests.sh

- name: Security check
  run: ./scripts/security-check.sh
```

---

## 🐛 Troubleshooting

### Script fails with "permission denied"

```bash
chmod +x scripts/*.sh
```

### Script fails with "not found"

Make sure you're running from the project root:

```bash
pwd  # Should show: /home/oscar/Proyectos/SentineLLM
```

### Port conflicts in quick-start

The quick-start script will detect and offer to kill processes using port 8080. If you want manual control:

```bash
# Check what's using port 8080
lsof -i :8080

# Kill process manually
kill $(lsof -t -i:8080)

# Then run script
./scripts/quick-start-openclaw.sh
```

---

## 📚 See Also

- [Main Documentation](../docs/README.md)
- [OpenClaw Integration Guide](../docs/openclaw-integration.md)
- [Port Architecture](../docs/PORTS.md)
- [Security Deployment](../docs/security-deployment.md)
