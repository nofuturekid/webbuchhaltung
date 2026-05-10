#!/usr/bin/env bash
# Runs after Bash tool calls. Detects git push and runs security + tax-relevance checks.
# Exit code 1 blocks the operation and requires orchestrator intervention.
set -euo pipefail

# Only activate on git push commands
BASH_CMD="${CLAUDE_TOOL_INPUT:-}"
if ! echo "$BASH_CMD" | grep -q "git push"; then
  exit 0
fi

echo "=== Security Gate: running pre-push checks ==="
ERRORS=0
TAX_RELEVANT=0

# Check for accounting-relevant file changes (triggers Tax-Agent)
CHANGED=$(git diff --cached --name-only 2>/dev/null || git diff HEAD~1 --name-only 2>/dev/null || echo "")
if echo "$CHANGED" | grep -qiE "(booking|account|tax|transaction|ledger|journal|invoice|vat)"; then
  TAX_RELEVANT=1
  echo "TAX_RELEVANT=1 — changed files touch accounting logic"
  echo "Orchestrator must invoke Tax-Agent before push proceeds."
fi

# Secrets scan
echo "--- Secrets scan (gitleaks) ---"
if command -v gitleaks &>/dev/null; then
  gitleaks detect --source . --exit-code 1 2>&1 || {
    echo "BLOCKED: gitleaks found secrets in code"
    ERRORS=$((ERRORS + 1))
  }
else
  echo "WARN: gitleaks not installed — skipping secrets scan"
fi

# Python security scan
echo "--- Python security scan (bandit) ---"
if [ -d "src/backend" ] && command -v bandit &>/dev/null; then
  bandit -r src/backend/ -ll --quiet 2>&1 || {
    echo "BLOCKED: bandit found high-severity Python security issues"
    ERRORS=$((ERRORS + 1))
  }
else
  echo "WARN: bandit not installed or src/backend/ not found — skipping"
fi

# JS dependency audit
echo "--- JS dependency audit (npm audit) ---"
if [ -d "src/frontend" ] && [ -f "src/frontend/package.json" ] && command -v npm &>/dev/null; then
  AUDIT_OUT=$(cd src/frontend && npm audit --audit-level=high --json 2>&1) || true
  echo "$AUDIT_OUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
except json.JSONDecodeError:
    print('WARN: npm audit output was not valid JSON — skipping JS audit')
    sys.exit(0)
vulns = data.get('metadata', {}).get('vulnerabilities', {})
high = vulns.get('high', 0) + vulns.get('critical', 0)
if high > 0:
    print(f'BLOCKED: {high} high/critical npm vulnerabilities found')
    sys.exit(1)
print(f'npm audit: no high/critical vulnerabilities')
" || ERRORS=$((ERRORS + 1))
else
  echo "WARN: npm or src/frontend/package.json not found — skipping JS audit"
fi

echo ""
if [ $ERRORS -gt 0 ]; then
  echo "GATE_STATUS=BLOCKED errors=$ERRORS"
  echo "Orchestrator must invoke Security-Agent to review and fix findings."
  exit 1
fi

if [ $TAX_RELEVANT -eq 1 ]; then
  echo "GATE_STATUS=TAX_REVIEW_REQUIRED"
  echo "Orchestrator must invoke Tax-Agent before push proceeds."
  exit 1
fi

echo "GATE_STATUS=PASS — all security checks passed"
exit 0
