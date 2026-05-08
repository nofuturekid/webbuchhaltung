# Architecture Decisions

## 2026-05-08 — Agent-team model: Hybrid Orchestrator + Worktrees

**Decision:** Use a hybrid model — one root orchestrator that delegates to specialized
sub-agents; critical parallel paths (backend + frontend) use git worktrees.

**Alternatives considered:** Monolithic CLAUDE.md (rejected: too large to maintain);
pure parallel agents without orchestrator (rejected: no coordination).

**Rationale:** Balances flexibility with structure. Orchestrator keeps the big picture;
specialists keep domain knowledge focused.

---

## 2026-05-08 — CLAUDE.md strategy: Modular hierarchy

**Decision:** Root CLAUDE.md for orchestrator; domain CLAUDE.md files in source
directories (auto-loaded by Claude Code); agent prompt templates in agents/*.md.

**Rationale:** Claude Code natively supports CLAUDE.md hierarchy. Domain files load
automatically when Claude works in that directory — no manual loading needed.

---

## 2026-05-08 — Tax jurisdiction: Germany (HGB, GoBD, UStG)

**Decision:** Primary target is German tax law. SKR03 as default chart of accounts.

**Rationale:** User requirement. DATEV is the dominant accounting platform in Germany;
SKR03 covers ~80% of German SMEs.

---

## 2026-05-08 — Language rule: English for all code artifacts

**Decision:** All code, comments, commits, branch names, docstrings, and design
documents must be written in English. UI text and legal terms remain German.

**Rationale:** International codebase conventions; LLM tools work best with English
code. German legal terminology (HGB, GoBD) cannot be translated without losing meaning.
