#!/bin/bash
# ==============================================================================
# EIP Backend - Production Startup Script
# Handles container environment initialization, validation, and Uvicorn launch
# ==============================================================================
set -euo pipefail

log_info() {
    echo "[INFO] $1"
}

log_warn() {
    echo "[WARN] $1"
}

log_error() {
    echo "[ERROR] $1"
}

log_info "Initializing Enterprise Intelligence Platform Backend..."

# 1. Environment Acquisition
# Prefer secrets passed directly into container environment by Docker Compose.
# If mandatory variables are already present, bypass AWS CLI check.
if [ -n "${DATABASE_URL:-}" ] && [ -n "${SECRET_KEY:-}" ] && [ -n "${OPENAI_API_KEY:-}" ]; then
    log_info "Production configuration detected in container environment."
else
    # Secondary fallback: If AWS CLI is present in container, attempt retrieval
    if command -v aws >/dev/null 2>&1; then
        log_info "Attempting to retrieve secrets via container AWS CLI (eip/production/backend)..."
        SECRET_JSON=$(aws secretsmanager get-secret-value \
            --secret-id "eip/production/backend" \
            --region "${AWS_REGION:-ap-south-1}" \
            --query 'SecretString' \
            --output text 2>/dev/null || true)
        
        if [ -n "$SECRET_JSON" ] && [ "$SECRET_JSON" != "null" ]; then
            log_info "Successfully retrieved secrets from AWS Secrets Manager."
            export SECRET_KEY=$(echo "$SECRET_JSON" | jq -r '.SECRET_KEY // empty')
            export DATABASE_URL=$(echo "$SECRET_JSON" | jq -r '.DATABASE_URL // empty')
            export OPENAI_API_KEY=$(echo "$SECRET_JSON" | jq -r '.OPENAI_API_KEY // empty')
            export ANTHROPIC_API_KEY=$(echo "$SECRET_JSON" | jq -r '.ANTHROPIC_API_KEY // empty')
            export LANGFUSE_PUBLIC_KEY=$(echo "$SECRET_JSON" | jq -r '.LANGFUSE_PUBLIC_KEY // empty')
            export LANGFUSE_SECRET_KEY=$(echo "$SECRET_JSON" | jq -r '.LANGFUSE_SECRET_KEY // empty')
            export LANGFUSE_HOST=$(echo "$SECRET_JSON" | jq -r '.LANGFUSE_HOST // "https://cloud.langfuse.com"')
            export LANGFUSE_ENABLED=$(echo "$SECRET_JSON" | jq -r '.LANGFUSE_ENABLED // "false"')
            export CORS_ORIGINS=$(echo "$SECRET_JSON" | jq -r '.CORS_ORIGINS // empty')
        fi
    else
        log_info "Container running without AWS CLI; using injected environment variables."
    fi
fi

# 2. Validate MANDATORY Environment Variables
log_info "Validating mandatory environment configuration..."

if [ -z "${SECRET_KEY:-}" ]; then
    log_error "MANDATORY variable SECRET_KEY is not set."
    exit 1
fi
if [ ${#SECRET_KEY} -lt 32 ]; then
    log_error "SECRET_KEY must be at least 32 characters long."
    exit 1
fi
log_info "  ✓ SECRET_KEY is configured (valid length >= 32)"

if [ -z "${DATABASE_URL:-}" ]; then
    log_error "MANDATORY variable DATABASE_URL is not set."
    exit 1
fi
log_info "  ✓ DATABASE_URL is configured"

if [ -z "${OPENAI_API_KEY:-}" ]; then
    log_error "MANDATORY variable OPENAI_API_KEY is not set."
    exit 1
fi
log_info "  ✓ OPENAI_API_KEY is configured"

if [ -z "${CORS_ORIGINS:-}" ]; then
    log_error "MANDATORY variable CORS_ORIGINS is not set."
    exit 1
fi
if [[ "$CORS_ORIGINS" == *"*"* ]]; then
    log_error "CORS_ORIGINS must not contain wildcard '*' in production."
    exit 1
fi
log_info "  ✓ CORS_ORIGINS is configured (explicit origins)"

# 3. Validate OPTIONAL Integration Variables Conditionally
# Anthropic fallback provider
FALLBACK_PROVIDER="${FALLBACK_LLM_PROVIDER:-anthropic}"
if [ "$FALLBACK_PROVIDER" = "anthropic" ]; then
    if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
        log_info "  ✓ Anthropic API key provided (fallback enabled)"
    else
        log_info "  ℹ Anthropic API key not provided; secondary fallback disabled"
    fi
fi

# Langfuse observability telemetry
LANGFUSE_FLAG="${LANGFUSE_ENABLED:-false}"
if [ "$LANGFUSE_FLAG" = "true" ] || [ "$LANGFUSE_FLAG" = "1" ]; then
    if [ -z "${LANGFUSE_PUBLIC_KEY:-}" ] || [ -z "${LANGFUSE_SECRET_KEY:-}" ]; then
        log_error "LANGFUSE_ENABLED is true, but LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY is missing."
        exit 1
    fi
    log_info "  ✓ Langfuse observability telemetry enabled"
else
    log_info "  ℹ Langfuse tracing disabled (LANGFUSE_ENABLED=false)"
fi

# Production integrity check: prevent silent mock provider activation
if [ "${ENVIRONMENT:-production}" = "production" ]; then
    if [ "${USE_FAKE_LLM:-false}" = "true" ] || [ "${USE_FAKE_EMBEDDINGS:-false}" = "true" ]; then
        log_error "PRODUCTION INTEGRITY ERROR: USE_FAKE_LLM or USE_FAKE_EMBEDDINGS is true in production environment!"
        exit 1
    fi
fi

# 4. Start Application
# Default to 1 worker for t3.micro (1 GiB RAM) to prevent memory exhaustion
WORKERS="${WEB_CONCURRENCY:-1}"
log_info "Starting EIP Backend on 0.0.0.0:8000 (${WORKERS} worker)..."
exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers "$WORKERS"
