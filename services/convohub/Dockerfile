# syntax=docker/dockerfile:1.7
# ConvoHub Dockerfile: supervisor + tools + WAHA adapter
# Multi-stage for smaller final image

ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=on \
    POETRY_NO_INTERACTION=1

WORKDIR /app

# Install system deps (if needed for google / redis etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt ./requirements.txt
# Install dependencies system-wide (avoid --user so runtime non-root user sees packages)
RUN pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV APP_USER=appuser \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8080

WORKDIR /app

# Create non-root user
RUN useradd -m -u 10001 -s /bin/bash ${APP_USER}

# Copy only necessary python artifacts (site-packages and scripts)
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source
# Copy source into a package directory so module path convohub.waha_adapter.main works
COPY . ./convohub

# Ensure permissions
RUN chown -R ${APP_USER}:${APP_USER} /app
USER ${APP_USER}

EXPOSE 8080

# Healthcheck (optional, expects /healthz from FastAPI)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -fsS http://localhost:8080/healthz || exit 1

# Default command (can be overridden)
CMD ["python", "-m", "uvicorn", "convohub.waha_adapter.main:app", "--host", "0.0.0.0", "--port", "8080"]
