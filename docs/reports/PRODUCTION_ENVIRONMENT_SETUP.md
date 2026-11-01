# Production Environment Setup Guide

## Overview
This document describes the complete production environment setup for the Enterprise Intelligence Platform (EIP) backend deployment on AWS EC2 with RDS PostgreSQL and Vercel frontend.

## 1. Required Environment Variables

The following environment variables must be configured for production deployment. All secrets must be stored in **AWS Secrets Manager** (secret name: `eip/production/backend`).

### Required Secrets (AWS Secrets Manager: `eip/production/backend`)

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `SECRET_KEY` | JWT signing key (32+ chars) | **Required** | `openssl rand -hex 32` |
| `DATABASE_URL` | PostgreSQL connection string | **Required** | `postgresql+psycopg2://user:pass@host:5432/db` |
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o | **Required** | `sk-proj-...` |
| `ANTHROPIC_API_KEY` | Anthropic API key for fallback | **Required** | `sk-ant-...` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | Required* | `pk-lf-...` |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | Required* | `sk-lf-...` |
| `CORS_ORIGINS` | JSON array of allowed origins | **Required** | `["https://app.example.com"]` |

*Langfuse keys required only if `LANGFUSE_ENABLED=true`

### Optional Secrets
| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Fallback LLM provider | Required if using fallback |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | Required if `LANGFUSE_ENABLED=true` |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | Required if `LANGFUSE_ENABLED=true` |
| `LANGFUSE_HOST` | Langfuse host URL | Optional (default: cloud.langfuse.com) |
| `LANGFUSE_ENABLED` | Enable Langfuse tracing | Optional (default: true) |
| `CORS_ORIGINS` | JSON array of allowed origins | **Required** |

### Application Configuration (Non-Secret)
These can be set via docker-compose environment or `.env` file:

```env
# Core
ENVIRONMENT=production
DEBUG=false
PROJECT_NAME="Enterprise Intelligence Platform"
VERSION=0.1.0
API_V1_STR=/api/v1
ENVIRONMENT=production
DEBUG=false

# Database
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname

# LLM Providers
PRIMARY_LLM_PROVIDER=openai
PRIMARY_LLM_MODEL=gpt-4o
FALLBACK_LLM_PROVIDER=anthropic
FALLBACK_LLM_MODEL=claude-3-5-sonnet-20241022

# Embeddings
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# LLM Settings
LLM_REQUEST_TIMEOUT=30.0
LLM_MAX_RETRIES=2
PRIMARY_LLM_PROVIDER=openai
PRIMARY_LLM_MODEL=gpt-4o
FALLBACK_LLM_PROVIDER=anthropic
FALLBACK_LLM_MODEL=claude-3-5-sonnet-20241022

# Embeddings
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# Rate Limiting
RATE_LIMIT_AUTH=10
RATE_LIMIT_AUTH_WINDOW=60
RATE_LIMIT_UPLOAD=5
RATE_LIMIT_UPLOAD_WINDOW=300
RATE_LIMIT_GENERAL=100
RATE_LIMIT_GENERAL_WINDOW=60

# Agent
AGENT_MAX_STEPS=5
AGENT_TIMEOUT_SECONDS=30

# Langfuse
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=

# CORS - MUST be explicit in production
CORS_ORIGINS=["https://your-frontend.vercel.app"]

# AWS
AWS_REGION=ap-south-1
AWS_DEFAULT_REGION=ap-south-1
```

## 2. AWS Secrets Manager Setup

### Create the Secret
```bash
# Create the secret with all required values
aws secretsmanager create-secret \
    --name eip/production/backend \
    --description "EIP Production Backend Configuration" \
    --secret-string '{
  "SECRET_KEY": "your-generated-32-byte-hex-key",
  "DATABASE_URL": "postgresql+psycopg2://user:pass@host:5432/dbname",
  "OPENAI_API_KEY": "sk-proj-...",
  "ANTHROPIC_API_KEY": "sk-ant-...",
  "LANGFUSE_PUBLIC_KEY": "pk-lf-...",
  "LANGFUSE_SECRET_KEY": "sk-lf-...",
  "LANGFUSE_HOST": "https://cloud.langfuse.com",
  "LANGFUSE_ENABLED": "true",
  "CORS_ORIGINS": "[\"https://your-frontend.vercel.app\"]",
  "DATABASE_URL": "postgresql+psycopg2://user:pass@host:5432/dbname",
  "OPENAI_API_KEY": "sk-proj-...",
  "ANTHROPIC_API_KEY": "sk-ant-...",
  "LANGFUSE_PUBLIC_KEY": "pk-lf-...",
  "LANGFUSE_SECRET_KEY": "sk-lf-...",
  "LANGFUSE_HOST": "https://cloud.langfuse.com",
  "LANGFUSE_ENABLED": "true",
  "CORS_ORIGINS": "[\"https://your-frontend.vercel.app\"]",
  "DATABASE_URL": "postgresql+psycopg2://user:pass@host:5432/dbname",
  "OPENAI_API_KEY": "sk-proj-...",
  "ANTHROPIC_API_KEY": "sk-ant-...",
  "LANGFUSE_PUBLIC_KEY": "pk-lf-...",
  "LANGFUSE_SECRET_KEY": "sk-lf-...",
  "LANGFUSE_HOST": "https://cloud.langfuse.com",
  "LANGFUSE_ENABLED": "true",
  "CORS_ORIGINS": "[\"https://your-frontend.vercel.app\"]"
}'
```

### IAM Policy for EC2 Instance Role
Attach this policy to the EC2 instance role (or create a new role):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:ap-south-1:*:secret:eip/production/backend*"
    }
  ]
}
```

### Verify EC2 Can Retrieve Secret
```bash
# Test from EC2 instance
aws secretsmanager get-secret-value \
  --secret-id eip/production/backend \
  --region ap-south-1 \
  --query SecretString --output text
```

## 3. Generate Application Secret

Generate a cryptographically secure 32-byte SECRET_KEY:

```bash
# Option 1: openssl (recommended)
openssl rand -hex 32

# Option 2: Python
python3 -c "import secrets; print(secrets.token_hex(32))"

# Example output: f6872586465ebe666f9fe764b0decdb238c65048d4eab4a02014e4e9b9a22aab
```

**Store this securely in AWS Secrets Manager. Never commit to git or print in logs.**

## 4. Docker Deployment Configuration

### Docker Compose for Production
The `docker-compose.yml` has been updated to:
- Use environment variables for all secrets (no hardcoded values)
- Require `SECRET_KEY` and `POSTGRES_PASSWORD` at runtime
- Use AWS Secrets Manager via startup script
- Include health checks for both db and backend
- Use persistent volumes for PostgreSQL data and document storage
- Run as non-root user (appuser)
- Health checks for both services

### Docker Compose Commands

```bash
# Build and start services
docker compose up -d --build

# View logs
docker compose logs -f backend

# Run migrations
docker compose exec backend python -m alembic -c backend/alembic.ini upgrade head

# Check health
curl http://localhost:8000/health
curl http://localhost:8000/ready

# View logs
docker compose logs -f backend

# Stop services
docker compose down

# Stop and remove volumes (WARNING: deletes data)
docker compose down -v
```

### Backend Startup Script
The backend uses `backend/start.sh` which:
1. Fetches secrets from AWS Secrets Manager (`eip/production/backend`)
2. Validates all required environment variables
3. Starts the FastAPI application with uvicorn
2 workers for t3.micro (1 GiB RAM)

## 6. Git Security Verification

### Verified .gitignore Coverage
```bash
# Verified ignored patterns:
.env
.env.local
.env.*.local
*.pem
*.key
*.p12
*.pfx
*.key
credentials.json
*.key
```

### Files Verified NOT in Git
- `backend/.env` ✓ (ignored)
- `frontend/.env` ✓ (ignored)
- No secrets in Dockerfile, docker-compose.yml, or Git history

### Verify No Secrets in Git History
```bash
# Check for accidentally committed secrets
git log --all --full-history --oneline -- "**/.env" "**/*.pem" "**/*.key" "**/credentials*"
```

## Migration Commands

```bash
# Run migrations on fresh database
docker compose exec backend python -m alembic -c backend/alembic.ini upgrade head

# Check current migration
docker compose exec backend python -m alembic -c backend/alembic.ini current

# Show migration history
docker compose exec backend python -m alembic -c backend/alembic.ini history --verbose

# Create new migration (after model changes)
docker compose exec backend python -m alembic -c backend/alembic.ini revision --autogenerate -m "description"
```

## Backend Startup & Health Checks

### Startup Commands
```bash
# Start all services
docker compose up -d

# Check service status
docker compose ps

# View backend logs
docker compose logs -f backend

# View database logs
docker compose logs -f db
```

### Health Check Endpoints
```bash
# Liveness probe
curl -f http://localhost:8000/health
# Expected: {"status":"ok","service":"Enterprise Intelligence Platform"}

# Readiness probe
curl -f http://localhost:8000/ready
# Expected: {"status":"ready","database":"connected"}
```

### Health Check Configuration
- **Backend**: `HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD curl -f http://localhost:8000/health || exit 1`
- **Database**: `pg_isready -U postgres -d engineering_intelligence` every 10s

## 7. Final Output Summary

### Files Created/Modified

| File | Status | Description |
|------|--------|-------------|
| `backend/.env.production` | ✅ Created | Complete production environment template |
| `backend/start.sh` | ✅ Created | Startup script with AWS Secrets Manager integration |
| `backend/Dockerfile` | ✅ Modified | Added jq, startup script, health check |
| `docker-compose.yml` | ✅ Modified | Production-ready, no hardcoded secrets |
| `backend/.env.production` | ✅ Created | Complete production environment template |
| `docs/reports/PRODUCTION_ENVIRONMENT_SETUP.md` | ✅ Created | This document |

### Secrets to Configure in AWS Secrets Manager
| Secret Name | Key | Status |
|-------------|-----|--------|
| `eip/production/backend` | `SECRET_KEY` | ⏳ Pending (generate with `openssl rand -hex 32`) |
| | `DATABASE_URL` | ⏳ Pending (RDS endpoint) |
| | `OPENAI_API_KEY` | ⏳ Pending (your key) |
| | `ANTHROPIC_API_KEY` | ⏳ Pending (your key) |
| | `LANGFUSE_PUBLIC_KEY` | ⏳ Pending (your key) |
| | `LANGFUSE_SECRET_KEY` | ⏳ Pending (your key) |
| | `CORS_ORIGINS` | ⏳ Pending (Vercel frontend URL) |
| | `DATABASE_URL` | ⏳ Pending (RDS endpoint) |
| | `OPENAI_API_KEY` | ⏳ Pending (your key) |
| | `ANTHROPIC_API_KEY` | ⏳ Pending (your key) |
| | `CORS_ORIGINS` | ⏳ Pending (Vercel frontend URL) |

### IAM Policy for EC2 Instance Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:ap-south-1:*:secret:eip/production/backend*"
    }
  ]
}
```

## Deployment Sequence

1. **Generate SECRET_KEY**: `openssl rand -hex 32`
2. **Create RDS PostgreSQL** with pgvector extension
3. **Create AWS Secrets Manager secret** `eip/production/backend` with all required keys
3. **Attach IAM policy** to EC2 instance role for Secrets Manager access
4. **Configure EC2** with Docker, Docker Compose, AWS CLI
5. **Deploy**: `docker compose up -d --build`
4. **Run migrations**: `docker compose exec backend python -m alembic -c backend/alembic.ini upgrade head`
5. **Verify health**: `curl http://localhost:8000/health`
6. **Configure Vercel** with `VITE_API_BASE_URL=https://your-ec2-ip:8000`
7. **Update CORS_ORIGINS** in AWS Secrets Manager with Vercel URL
8. **Restart backend** to pick up new CORS settings

### Security Checklist
- [ ] SECRET_KEY generated and stored in AWS Secrets Manager
- [ ] Database password stored in AWS Secrets Manager
- [ ] API keys stored in AWS Secrets Manager
- [ ] CORS_ORIGINS set to explicit Vercel URL (no wildcards)
- [ ] .env files in .gitignore
- [ ] No secrets in Dockerfile or docker-compose.yml
- [ ] EC2 IAM role has SecretsManager:GetSecretValue permission
- [ ] Health checks configured for both services
- [ ] Automatic restart policies configured
- [ ] Persistent volumes for PostgreSQL and document storage

---
*Report generated: $(date)*
*Environment: Production*
*Region: ap-south-1*