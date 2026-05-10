# Contributing

## Branching workflow

1. Branch from `develop`: `git checkout -b feature/<scope>-<short-description>`
2. Implement changes in `src/backend` and/or `src/frontend`
3. Write tests — all existing tests must continue to pass
4. Run pre-commit hooks: `pre-commit run --all-files`
5. Open a PR targeting `develop` (not `main`)
6. Gate agents (Tax/Compliance, Security) run automatically — PRs are blocked on violations
7. Merge to `main` only via `develop` after Review-Agent approval

Branch naming:

```
feature/<scope>-<ticket>   # feature work → PR to develop
hotfix/<ticket>            # urgent fix on main base → PR directly to main
release/<version>          # release prep → PR to main
```

---

## Commit format (Conventional Commits)

```
feat(backend): Add SEPA export endpoint
fix(frontend): Correct VAT calculation on line item delete
test(qa): Add period lock regression test
docs(changelog): Regenerate for v0.4.0
```

Format: `<type>(<scope>): <Description starting with uppercase, ≤ 50 chars>`

Types: `feat` `fix` `refactor` `test` `docs` `ci` `build` `perf` `chore` `revert`

Scopes: `backend` `frontend` `db` `devops` `qa` `security` `tax` `auth` `api` `memory`

---

## Running the full test suite

```bash
# Backend (requires PostgreSQL)
cd src/backend && \
  TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/webbuchhaltung_test" \
  uv run pytest tests/ -q

# Frontend
cd src/frontend && npm test -- --run
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for how to set up the test database.

---

## Gate agents

Two automated gates block merges on violations:

**Tax/Compliance-Agent** — triggered when changed files touch booking, account, tax,
invoice, or journal logic. Checks GoBD immutability (§14), VAT rates (UStG), and
SKR03/04 account validity. Violations reference the specific law (e.g. `GoBD §14`).

**Security-Agent** — runs before every push. Scans with Bandit (Python), gitleaks
(secrets), and npm audit (JS CVEs). CRITICAL/HIGH findings block the push.

---

## Architecture decisions

Significant architectural choices are documented as ADRs in `docs/decisions/`.
See existing records for format — file names follow `NNNN-<kebab-title>.md`.
