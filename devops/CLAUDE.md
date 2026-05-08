# DevOps Context

You are working on the infrastructure of WebBuchhaltung (German accounting software).

## Stack
- Docker — containerization, multi-stage builds
- Kubernetes — orchestration (production)
- GitHub Actions — CI/CD pipeline (primary)
- GitLab CI — CI/CD pipeline (mirror)
- Helm — Kubernetes package management

## Project Layout (to be created)
```
devops/
├── docker/
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
├── kubernetes/
│   ├── base/              # Kustomize base
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── ingress.yaml
│   └── overlays/
│       ├── dev/
│       ├── staging/
│       └── prod/
├── helm/
│   └── webbuchhaltung/
└── .github/
    └── workflows/
        ├── ci.yml
        └── deploy.yml
```

## Docker Standards
- Multi-stage builds: `builder` stage (with dev deps) → `runtime` stage (minimal)
- Never run containers as root — use a non-root user in the final stage
- No secrets in Dockerfiles or images — use build args for non-sensitive config only
- Pin base image versions: `python:3.12.3-slim-bookworm`, not `python:3.12`
- `.dockerignore` must exclude: `.git`, `__pycache__`, `*.pyc`, `node_modules`, `.env`

## Kubernetes Standards
- Always set resource `requests` and `limits` — no unbounded containers
- Use `ConfigMap` for non-sensitive config, `Secret` for credentials
- Never commit secrets to git — use external secrets operator or sealed secrets
- Liveness and readiness probes required on all deployments
- Use `RollingUpdate` strategy with `maxUnavailable: 0`

## Environment Separation
Three environments, each in its own Kubernetes namespace:
- `dev` — deployed on every push to `develop`
- `staging` — deployed on release branch creation
- `prod` — deployed on tag push `v*.*.*` after manual approval gate

## CI/CD Pipeline Structure
Every PR triggers:
1. Lint + type check (ruff, mypy, tsc)
2. Unit tests (pytest, vitest)
3. Security scan (bandit, npm audit, trivy)
4. Build Docker images
5. E2E tests against dev environment (Playwright)

Merges to main additionally trigger:
6. Staging deployment
7. Smoke test against staging
8. Manual approval gate
9. Production deployment
