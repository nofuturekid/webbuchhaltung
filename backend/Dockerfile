FROM python:3.12-slim
WORKDIR /app

# System libraries required by weasyprint (PDF rendering via Cairo/Pango)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    libffi8 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install uv via the official installer to avoid polluting system Python.
# Pin the version so builds are reproducible.
COPY --from=ghcr.io/astral-sh/uv:0.6.14 /uv /usr/local/bin/uv

# Copy dependency manifest + lockfile first so Docker can cache this layer.
COPY pyproject.toml uv.lock ./

# Install production dependencies only, using the exact locked versions.
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
