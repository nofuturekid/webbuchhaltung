#!/usr/bin/env bash
# Runs on Stop event. Updates memory/project_status.md with session summary.
# The orchestrator also updates .claude/state/ files directly.
set -euo pipefail

# Ensure state directory exists (gitignored but must exist locally)
mkdir -p .claude/state

TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
STATUS_FILE="memory/project_status.md"

if [ ! -f "$STATUS_FILE" ]; then
  echo "WARN: $STATUS_FILE not found — skipping memory update"
  exit 0
fi

# Append session end marker so orchestrator knows to update on next session start
echo "" >> "$STATUS_FILE"
echo "<!-- session-end: $TIMESTAMP -->" >> "$STATUS_FILE"

# Show recent git changes for context
echo ""
echo "=== Session end — recent changes ==="
git log --oneline -5 2>/dev/null || true
echo "Orchestrator: update memory/project_status.md and .claude/state/ files."
exit 0
