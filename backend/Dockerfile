# ==============================================================================
# Enterprise Intelligence Platform - Production Backend Dockerfile
# ==============================================================================

FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Create shared virtual environment for dependency installation
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final Runtime Image
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application source code
COPY backend /app/backend

# Copy startup script
COPY backend/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Create non-root system user and storage folder
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/storage/documents && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["/app/start.sh"]

