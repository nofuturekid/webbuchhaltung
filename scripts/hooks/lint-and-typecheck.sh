#!/usr/bin/env bash
# Runs after Write/Edit tool calls. Detects file type and runs appropriate linter.
# Output is read by the orchestrator to decide whether to spawn a fix agent.
set -euo pipefail

# Claude Code passes the modified file path via CLAUDE_TOOL_OUTPUT or similar context.
# We scan recently modified tracked files as a fallback.
MODIFIED_FILES=$(git diff --name-only 2>/dev/null || echo "")

if [ -z "$MODIFIED_FILES" ]; then
  exit 0
fi

ERRORS=0

# Python files: run ruff + mypy
PY_FILES=$(echo "$MODIFIED_FILES" | grep '\.py$' || true)
if [ -n "$PY_FILES" ]; then
  echo "=== Ruff lint ==="
  if command -v ruff &>/dev/null; then
    ruff check $PY_FILES || ERRORS=$((ERRORS + 1))
  else
    echo "WARN: ruff not installed — skipping Python lint"
  fi

  echo "=== mypy type check ==="
  if command -v mypy &>/dev/null; then
    mypy $PY_FILES --ignore-missing-imports || ERRORS=$((ERRORS + 1))
  else
    echo "WARN: mypy not installed — skipping type check"
  fi
fi

# TypeScript/TSX files: run tsc
TS_FILES=$(echo "$MODIFIED_FILES" | grep -E '\.(ts|tsx)$' || true)
if [ -n "$TS_FILES" ] && [ -f "frontend/tsconfig.json" ]; then
  echo "=== TypeScript type check ==="
  if command -v npx &>/dev/null; then
    (cd frontend && npx tsc --noEmit 2>&1) || ERRORS=$((ERRORS + 1))
  else
    echo "WARN: npx not installed — skipping TypeScript check"
  fi
fi

if [ $ERRORS -gt 0 ]; then
  echo ""
  echo "LINT_ERRORS=$ERRORS — orchestrator should review and fix"
  exit 1
fi

echo "All checks passed."
exit 0
