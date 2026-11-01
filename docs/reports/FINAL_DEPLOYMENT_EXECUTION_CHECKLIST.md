# Final Production Deployment Execution Checklist & Runbook

**Document ID:** `EIP-DEP-RUNBOOK-001`  
**Target Host OS:** Ubuntu 26.04.1 LTS  
**Target Host Instance:** AWS EC2 `t3.micro` (1 GiB RAM)  
**Target Database:** PostgreSQL 18.3 + pgvector on AWS RDS (`ap-south-1`)  
**Target Frontend:** React 18 + Vite on Vercel Edge CDN  
**Target Region:** `ap-south-1` (Mumbai)  
**Version:** 1.0.0 (Production Release Candidate)  
**Date:** November 1, 2026  
**Auditor / Integration Engineer:** Senior AI Systems Architect & QA Integration Engineer  

---

## 1. Executive Deployment Architecture

This runbook defines the exact execution sequence, commands, verification checklists, and operational runbook for deploying the **Engineering Intelligence Platform (EIP)** to production.

```
+----------------------------------------------------------------------------------------------------+
|                                    PRODUCTION ARCHITECTURE (ap-south-1)                           |
|                                                                                                    |
|   +------------------------------------+            HTTPS / WSS                                    |
|   |         Vercel Edge CDN            | <=======================================+                 |
|   |   (React 18 + Vite + Tailwind)     |                                         |                 |
|   |   SPA with vercel.json rewrite     |                                         |                 |
|   +------------------------------------+                                         |                 |
|                                                                                  v                 |
|   +--------------------------------------------------------------------------------------------+   |
|   |   AWS EC2 Instance: Ubuntu 26.04.1 LTS (t3.micro - 1 GiB RAM)                              |   |
|   |                                                                                            |   |
|   |   +------------------------------------------------------------------------------------+   |   |
|   |   |   Nginx Reverse Proxy (Host Level - Port 80 / 443)                                 |   |   |
|   |   |   - client_max_body_size: 55M (document uploads)                                   |   |   |
|   |   |   - Timeouts: 120s for LLM reasoning & agent loops                                 |   |   |
|   |   |   - SSL Termination / Certbot Let's Encrypt                                        |   |   |
|   |   +------------------------------------------------------------------------------------+   |   |
|   |                                             | proxy_pass                                   |   |
|   |                                             v                                              |   |
|   |   +------------------------------------------------------------------------------------+   |   |
|   |   |   Docker Container: eip_backend (FastAPI)                                          |   |   |
|   |   |   - Bound to internal loopback: 127.0.0.1:8000:8000 (No public exposure)          |   |   |
|   |   |   - Memory limit: 750M (reservations: 256M) for 1 GiB host safety                  |   |   |
|   |   |   - 1 Uvicorn Worker (WEB_CONCURRENCY=1) to prevent RAM exhaustion                 |   |   |
|   |   |   - start.sh: strictly enforces mandatory vars, rejects mock providers in prod     |   |   |
|   |   +-------------------------+----------------------------------------------------------+   |   |
|   |                             |                                                              |   |
|   |                             | Volume: document_storage (/app/storage/documents)            |   |
|   |                             v                                                              |   |
|   |                   +-------------------+                                                    |   |
|   |                   |  Host EBS Storage |                                                    |   |
|   |                   +-------------------+                                                    |   |
|   +--------------------------------------------------------------------------------------------+   |
|                                             |                                                      |
|                 SQL + pgvector (port 5432)  |                                                      |
|                                             v                                                      |
|   +--------------------------------------------------------------------------------------------+   |
|   |   AWS RDS PostgreSQL 18.3 + pgvector                                                       |   |
|   |   - Managed Automated Backups & Multi-AZ availability                                      |   |
|   |   - Security Group: Accepts port 5432 ingress only from EC2 Security Group                |   |
|   |   - Zero local PostgreSQL container in production                                          |   |
|   +--------------------------------------------------------------------------------------------+   |
|                                             |                                                      |
|   +-----------------------------------------+--------------------------------------------------+   |
|   |   External AI & Observability Providers:                                                   |   |
|   |   - OpenAI API (Primary: GPT-4o + text-embedding-3-small 1536-dim)                         |   |
|   |   - Anthropic Claude 3.5 Sonnet (Secondary fallback, optional)                             |   |
|   |   - Langfuse Cloud SDK v5.1.0 (Telemetry, tracing, latency & token usage, optional)       |   |
|   +--------------------------------------------------------------------------------------------+   |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Deployment Status & Responsibility Matrix

| Component / Task | Codebase Preparation Status | Live Execution Status | Responsible Party |
|---|:---:|:---:|:---:|
| **Frontend Production Build** | **COMPLETED** (0 errors, 4.37s) | Ready for Vercel push | Dev / Operations |
| **Frontend Vercel Config** | **COMPLETED** (`vercel.json`) | Ready for Vercel deploy | Operations |
| **API Trailing Slash Fix** | **COMPLETED** (`frontend/src/services/api.ts`) | Staged for commit | Development |
| **Backend Dockerfile Optimization** | **COMPLETED** (`backend/Dockerfile`) | Staged for commit | Development |
| **Backend Startup Script** | **COMPLETED** (`backend/start.sh`) | Staged for commit | Development |
| **Mandatory Environment Validation** | **COMPLETED** (No mock fallback) | Staged for commit | Development |
| **Production Docker Compose** | **COMPLETED** (`docker-compose.prod.yml`) | Staged for commit | Development |
| **Local DB Profile Exclusion** | **COMPLETED** (`docker-compose.yml`) | Staged for commit | Development |
| **Nginx Reverse Proxy Config** | **COMPLETED** (`nginx/eip.conf`) | Staged for commit | Development |
| **Host Secrets Retrieval Script** | **COMPLETED** (`scripts/fetch_production_secrets.sh`) | Staged for commit | Development |
| **Git Secret Ignorance (.gitignore)** | **COMPLETED** (`.env*` safe) | Staged for commit | Development |
| **AWS Secrets Manager Creation** | N/A (Cloud resource) | **PENDING** (In progress by OpenCode) | OpenCode |
| **EC2 IAM Instance Profile** | N/A (Cloud resource) | **PENDING** (In progress by OpenCode) | OpenCode |
| **AWS RDS pgvector Provisioning** | N/A (Cloud resource) | **COMPLETED** (PostgreSQL 18.3) | Cloud Architect |
| **EC2 Host Setup (Ubuntu 26.04)** | Documented below | **PENDING** | Cloud Operator |
| **Alembic Migrations on RDS** | Documented below | **PENDING** | Cloud Operator |
| **Vercel Frontend Deployment** | Documented below | **PENDING** | Cloud Operator |

---

## 3. Frontend Deployment Readiness (Vercel)

### 3.1 Build & Asset Verification
- **Build Command:** `npm run build` (`tsc && vite build`)
- **Output Directory:** `dist/`
- **Build Status:** **VERIFIED PASSING** (0 errors, 4.37s compilation)
- **Asset Bundle Breakdown:**
  - `dist/index.html`: `1.10 kB` (gzip: `0.57 kB`)
  - `dist/assets/index-*.css`: `33.43 kB` (gzip: `6.19 kB`)
  - `dist/assets/ui-*.js`: `19.03 kB` (gzip: `3.99 kB`)
  - `dist/assets/index-*.js`: `103.09 kB` (gzip: `23.28 kB`)
  - `dist/assets/vendor-*.js`: `162.78 kB` (gzip: `53.13 kB`)

### 3.2 Environment Variables (Vercel Project Settings)
The frontend requires exactly **one** environment variable in Vercel:

| Variable Name | Environment | Value Description | Example Value |
|---|---|---|---|
| `VITE_API_BASE_URL` | Production & Preview | Public URL of EC2 Nginx Reverse Proxy | `http://<EC2-PUBLIC-IP>` or `https://api.yourdomain.com` |

> [!CAUTION]
> **No Backend Secrets in Frontend:** Verify that `SECRET_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `DATABASE_URL` are **NEVER** prefixed with `VITE_` or added to Vercel. Only `VITE_API_BASE_URL` should exist in Vercel.

### 3.3 Vercel Deployment Instructions
1. Navigate to [vercel.com](https://vercel.com) and click **"Add New Project"**.
2. Import repository `iamshaneofc/enterprise-intelligence-platform`.
3. Set **Root Directory** to `frontend`.
4. Framework preset: **Vite**.
5. Add Environment Variable:
   - Name: `VITE_API_BASE_URL`
   - Value: `http://<EC2-PUBLIC-IP>` (or your domain/ALB URL)
6. Click **Deploy**.
7. Note the assigned deployment URL (e.g. `https://eip-frontend.vercel.app`).
8. Add this URL to `CORS_ORIGINS` in AWS Secrets Manager `eip/production/backend`:
   ```json
   "CORS_ORIGINS": "[\"https://eip-frontend.vercel.app\"]"
   ```

---

## 4. EC2 Ubuntu 26.04.1 LTS Host Setup Runbook

All commands in this section target **Ubuntu 26.04.1 LTS** on an AWS EC2 `t3.micro` instance (`ap-south-1`).

### Step 1: Connect to EC2 Host via AWS Systems Manager (SSM)
```bash
# Verify AWS CLI identity
aws sts get-caller-identity --region ap-south-1

# Start SSM interactive shell
aws ssm start-session --target <EC2-INSTANCE-ID> --region ap-south-1
```

### Step 2: System Packages & Dependencies
```bash
# Update package repositories
sudo apt-get update && sudo apt-get upgrade -y

# Install prerequisite tools (AWS CLI, jq, curl, git, Nginx)
sudo apt-get install -y ca-certificates curl gnupg git jq awscli nginx
```

### Step 3: Install Official Docker Engine & Compose Plugin
```bash
# Setup Docker GPG keyring
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine, containerd, and Compose plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Enable and start Docker service
sudo systemctl enable --now docker

# Grant non-root user docker permissions
sudo usermod -aG docker ubuntu || sudo usermod -aG docker ssm-user

# Verify Docker and Compose installations
docker --version
docker compose version
```

### Step 4: Configure Nginx Reverse Proxy
```bash
# Navigate to repository directory after cloning (see Step 5)
# Copy the verified EIP Nginx configuration
sudo cp /opt/eip/nginx/eip.conf /etc/nginx/sites-available/eip

# Enable the EIP site configuration
sudo ln -sf /etc/nginx/sites-available/eip /etc/nginx/sites-enabled/eip

# Remove the default Ubuntu welcome page
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx syntax
sudo nginx -t

# Restart and enable Nginx service
sudo systemctl restart nginx
sudo systemctl enable nginx
```

> [!NOTE]
> **Optional HTTPS with Certbot (Recommended for Custom Domains):**
> If pointing a domain name to the EC2 IP, configure Let's Encrypt SSL:
> ```bash
> sudo apt-get install -y certbot python3-certbot-nginx
> sudo certbot --nginx -d api.yourdomain.com
> ```

---

## 5. Backend Deployment & Container Lifecycle

### Step 5: Clone or Update Application Repository
```bash
# Target application directory
sudo mkdir -p /opt/eip
sudo chown -R $USER:$USER /opt/eip
cd /opt/eip

# Clone if first deployment, or pull latest main branch
if [ ! -d ".git" ]; then
  git clone https://github.com/iamshaneofc/enterprise-intelligence-platform.git .
else
  git fetch origin
  git checkout main
  git pull origin main
fi

# Make scripts executable
chmod +x scripts/fetch_production_secrets.sh backend/start.sh

# Verify latest commit
git log -1 --format="%H - %s"
```

### Step 6: Fetch Secrets from AWS Secrets Manager
The EC2 host uses its assigned IAM role to retrieve `eip/production/backend` and write a local, permission-restricted `.env.production` file.
```bash
cd /opt/eip

# Execute secret retrieval script
./scripts/fetch_production_secrets.sh

# Verify .env.production exists with strict permissions (0600)
ls -la .env.production
```

> [!IMPORTANT]
> **Security Guarantee:** `.env.production` is ignored by `.gitignore` and has file permission `0600` (readable only by the deployment owner). Secrets are **never** logged to stdout or committed to Git.

### Step 7: Build & Launch Production Container
We use `docker-compose.prod.yml`, which starts **only** the `eip_backend` container and connects directly to AWS RDS (no local PostgreSQL container is created).
```bash
cd /opt/eip

# Build image and start backend container in detached mode
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# Inspect container status and health
docker compose -f docker-compose.prod.yml ps
```

### Step 8: Apply Alembic Migrations to AWS RDS
```bash
# Run database migrations up to head
docker compose -f docker-compose.prod.yml exec backend python -m alembic -c backend/alembic.ini upgrade head

# Confirm current revision
docker compose -f docker-compose.prod.yml exec backend python -m alembic -c backend/alembic.ini current
```

### Step 9: Verify Container Logs
```bash
# View backend startup logs (confirm 1 worker launched, environment validated)
docker compose -f docker-compose.prod.yml logs --tail=50 backend
```

---

## 6. Health & Smoke Test Execution Plan

### Step 10: Local Health Checks
```bash
# 1. Direct container probe on loopback (8000)
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/ready

# 2. Probe through Nginx reverse proxy (Port 80)
curl -i http://127.0.0.1/health
curl -i http://127.0.0.1/ready
```
Both `/health` and `/ready` must return HTTP `200 OK` with JSON bodies:
```json
{"status": "ok", "service": "Enterprise Intelligence Platform", "version": "0.1.0", "environment": "production"}
```
```json
{"status": "ready", "database": "connected"}
```

### Step 11: End-to-End Automated Smoke Test Script
Save and run on the EC2 host to verify complete user and AI functionality against the live RDS database and OpenAI API:

```python
cat << 'EOF' > /tmp/prod_smoke_test.py
import requests, time, sys

BASE = "http://127.0.0.1/api/v1"

print("==================================================================")
print("EIP Production Automated Smoke Test Suite")
print("==================================================================")

print("1. Testing Health & Readiness probes via Nginx...")
h = requests.get("http://127.0.0.1/health").json()
r = requests.get("http://127.0.0.1/ready").json()
assert h["status"] == "ok", f"Health failed: {h}"
assert r["database"] == "connected", f"Readiness failed: {r}"
print("   ✓ Health & DB Connectivity verified")

print("2. Registering production smoke test user...")
email = f"prod_smoke_{int(time.time())}@example.com"
reg = requests.post(
    f"{BASE}/auth/register",
    json={"email": email, "password": "ProductionPassword123!", "full_name": "Prod Smoke Tester"}
)
assert reg.status_code == 201, f"Registration failed ({reg.status_code}): {reg.text}"
print("   ✓ User registered successfully")

print("3. Logging in & generating JWT access token...")
login_resp = requests.post(
    f"{BASE}/auth/login",
    json={"email": email, "password": "ProductionPassword123!"}
)
assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("   ✓ JWT token obtained")

print("4. Creating disposable workspace...")
ws_resp = requests.post(
    f"{BASE}/workspaces",
    json={"name": "Prod Smoke Test Workspace"},
    headers=headers
)
assert ws_resp.status_code == 201, f"Workspace creation failed: {ws_resp.text}"
ws_id = ws_resp.json()["id"]
print(f"   ✓ Workspace provisioned: {ws_id}")

print("5. Ingesting test document & generating real OpenAI embeddings...")
doc_content = b"# Production Runbook\n\nDefault system worker count is 1 for t3.micro. Maximum upload size is 50MB."
upload_resp = requests.post(
    f"{BASE}/workspaces/{ws_id}/documents/upload",
    files={"file": ("runbook.md", doc_content, "text/markdown")},
    headers=headers
)
assert upload_resp.status_code == 201, f"Upload failed: {upload_resp.text}"
doc_data = upload_resp.json()
print(f"   ✓ Document indexed: {doc_data.get('title')} ({doc_data.get('total_chunks')} chunks embedded)")

print("6. Executing Grounded RAG query with OpenAI GPT-4o...")
chat_resp = requests.post(
    f"{BASE}/workspaces/{ws_id}/chat",
    json={"query": "What is the maximum upload size mentioned in the runbook?", "workspace_id": ws_id},
    headers=headers
)
assert chat_resp.status_code == 200, f"Chat failed: {chat_resp.text}"
chat_data = chat_resp.json()
assert chat_data.get("provider_used") == "openai", f"Expected OpenAI provider, got: {chat_data.get('provider_used')}"
assert len(chat_data.get("citations", [])) > 0, "Expected at least 1 citation for grounded query"
print(f"   ✓ Provider: {chat_data.get('provider_used')} ({chat_data.get('model_used')})")
print(f"   ✓ Answer: {chat_data.get('answer')[:120]}...")
print(f"   ✓ Citations: {len(chat_data.get('citations'))} grounded citation(s)")

print("\n==================================================================")
print("SUCCESS: ALL 6 BACKEND PRODUCTION SMOKE TESTS PASSED!")
print("==================================================================")
EOF
python3 /tmp/prod_smoke_test.py
```

---

## 7. Rollback & Troubleshooting Runbook

### Rollback Plan
If an issue occurs after launching a new Docker image:
```bash
cd /opt/eip

# 1. Rollback code to previous git commit
git checkout HEAD~1

# 2. Re-fetch secrets if needed
./scripts/fetch_production_secrets.sh

# 3. Rebuild and restart container
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# 4. If migration rollback is required:
docker compose -f docker-compose.prod.yml exec backend python -m alembic -c backend/alembic.ini downgrade -1
```

### Common Troubleshooting Scenarios
1. **Container exits immediately on startup:**
   - Run `docker compose -f docker-compose.prod.yml logs backend`.
   - If error is `MANDATORY variable SECRET_KEY is not set` or `OPENAI_API_KEY is not set`, re-run `./scripts/fetch_production_secrets.sh` and ensure the IAM role has access to `eip/production/backend`.
2. **502 Bad Gateway from Nginx:**
   - Verify container is running: `docker compose -f docker-compose.prod.yml ps`.
   - Test internal port: `curl http://127.0.0.1:8000/health`.
   - If port 8000 is unreachable, check container memory consumption (`docker stats`) to ensure `t3.micro` did not run out of RAM.
3. **CORS Error in Vercel Frontend:**
   - Check `CORS_ORIGINS` in AWS Secrets Manager. Ensure it contains the exact Vercel origin without trailing slashes (e.g. `["https://eip-frontend.vercel.app"]`).
   - Re-run `./scripts/fetch_production_secrets.sh` and restart the container: `docker compose -f docker-compose.prod.yml restart backend`.
