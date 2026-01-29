#!/bin/bash

# 🛡️ SentineLLM - Local Security Checks Runner
# Run all security and quality checks before pushing to CI/CD

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Emoji support
CHECK="✅"
CROSS="❌"
WARNING="⚠️"
INFO="ℹ️"
ROCKET="🚀"
SHIELD="🛡️"

echo -e "${BLUE}${SHIELD} SentineLLM Security Check Runner${NC}"
echo "========================================"
echo ""

# Check if virtual environment is activated
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo -e "${WARNING} ${YELLOW}Warning: Virtual environment not detected${NC}"
    echo "Run: source venv/bin/activate"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Function to run a check
run_check() {
    local name=$1
    local command=$2
    
    echo -e "\n${BLUE}Running: ${name}${NC}"
    echo "----------------------------------------"
    
    if eval "$command"; then
        echo -e "${GREEN}${CHECK} ${name} passed${NC}"
        return 0
    else
        echo -e "${RED}${CROSS} ${name} failed${NC}"
        return 1
    fi
}

# Track failures
FAILED_CHECKS=0

# ═══════════════════════════════════════════════════════════════════
# 1. Code Formatting Check
# ═══════════════════════════════════════════════════════════════════
if ! run_check "Ruff Format Check" "ruff format --check src/ tests/"; then
    echo -e "${INFO} Run: ${YELLOW}ruff format src/ tests/${NC} to fix"
    ((FAILED_CHECKS++))
fi

# ═══════════════════════════════════════════════════════════════════
# 2. Linting
# ═══════════════════════════════════════════════════════════════════
if ! run_check "Ruff Linter" "ruff check src/ tests/"; then
    echo -e "${INFO} Run: ${YELLOW}ruff check src/ tests/ --fix${NC} to auto-fix"
    ((FAILED_CHECKS++))
fi

# ═══════════════════════════════════════════════════════════════════
# 3. Type Checking
# ═══════════════════════════════════════════════════════════════════
if ! run_check "mypy Type Checker" "mypy src/ --ignore-missing-imports"; then
    echo -e "${INFO} Fix type hints or add '# type: ignore' comments"
    ((FAILED_CHECKS++))
fi

# ═══════════════════════════════════════════════════════════════════
# 4. SAST - Bandit Security Scanner
# ═══════════════════════════════════════════════════════════════════
if ! run_check "Bandit SAST" "bandit -r src/ -ll"; then
    echo -e "${INFO} Review security findings above"
    ((FAILED_CHECKS++))
fi

# ═══════════════════════════════════════════════════════════════════
# 5. Secret Detection
# ═══════════════════════════════════════════════════════════════════
if command -v detect-secrets &> /dev/null; then
    if ! run_check "Detect Secrets" "detect-secrets scan --baseline .secrets.baseline 2>&1 | grep -q 'No secrets detected'"; then
        echo -e "${WARNING} ${YELLOW}Potential secrets detected!${NC}"
        echo -e "${INFO} Run: ${YELLOW}detect-secrets scan > .secrets.baseline${NC}"
        echo -e "${INFO} Then audit: ${YELLOW}detect-secrets audit .secrets.baseline${NC}"
        ((FAILED_CHECKS++))
    fi
else
    echo -e "${WARNING} ${YELLOW}detect-secrets not installed, skipping...${NC}"
fi

# ═══════════════════════════════════════════════════════════════════
# 6. Dependency Vulnerabilities
# ═══════════════════════════════════════════════════════════════════
if command -v safety &> /dev/null; then
    if ! run_check "Safety Check" "safety check --json 2>&1 | jq -e '.vulnerabilities | length == 0' > /dev/null 2>&1"; then
        echo -e "${WARNING} ${YELLOW}Vulnerabilities found in dependencies${NC}"
        echo -e "${INFO} Review with: ${YELLOW}safety check${NC}"
        ((FAILED_CHECKS++))
    fi
else
    echo -e "${WARNING} ${YELLOW}safety not installed, skipping...${NC}"
fi

# ═══════════════════════════════════════════════════════════════════
# 7. Unit Tests
# ═══════════════════════════════════════════════════════════════════
if ! run_check "Pytest Unit Tests" "pytest --tb=short -q"; then
    echo -e "${INFO} Fix failing tests before committing"
    ((FAILED_CHECKS++))
fi

# ═══════════════════════════════════════════════════════════════════
# 8. Code Coverage
# ═══════════════════════════════════════════════════════════════════
echo -e "\n${BLUE}Running: Code Coverage Check${NC}"
echo "----------------------------------------"
COVERAGE=$(pytest --cov=src --cov-report=term-missing --tb=short -q 2>&1 | grep "^TOTAL" | awk '{print $4}' | sed 's/%//')

if [[ -n "$COVERAGE" ]]; then
    echo -e "Current coverage: ${BLUE}${COVERAGE}%${NC}"
    
    if (( $(echo "$COVERAGE < 80" | bc -l) )); then
        echo -e "${RED}${CROSS} Coverage below 80% threshold${NC}"
        ((FAILED_CHECKS++))
    else
        echo -e "${GREEN}${CHECK} Coverage meets 80% threshold${NC}"
    fi
else
    echo -e "${YELLOW}${WARNING} Could not determine coverage${NC}"
fi

# ═══════════════════════════════════════════════════════════════════
# 9. Trivy Filesystem Scan (if available)
# ═══════════════════════════════════════════════════════════════════
if command -v trivy &> /dev/null; then
    echo -e "\n${BLUE}Running: Trivy Filesystem Scan${NC}"
    echo "----------------------------------------"
    trivy fs . --severity HIGH,CRITICAL --exit-code 0
    echo -e "${GREEN}${CHECK} Trivy scan completed${NC}"
else
    echo -e "\n${INFO} ${YELLOW}Trivy not installed, skipping...${NC}"
    echo "Install: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
fi

# ═══════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════
echo ""
echo "========================================"
echo -e "${BLUE}${SHIELD} Security Check Summary${NC}"
echo "========================================"

if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}${ROCKET} All checks passed! Ready to push.${NC}"
    echo ""
    echo "Next steps:"
    echo "  git add ."
    echo "  git commit -m 'feat: your changes'"
    echo "  git push origin your-branch"
    exit 0
else
    echo -e "${RED}${CROSS} ${FAILED_CHECKS} check(s) failed${NC}"
    echo ""
    echo "Please fix the issues above before pushing."
    echo ""
    echo "Quick fixes:"
    echo "  ruff format src/ tests/        # Auto-format code"
    echo "  ruff check src/ tests/ --fix   # Auto-fix linting"
    echo "  pytest -v                      # Run tests verbosely"
    exit 1
fi
