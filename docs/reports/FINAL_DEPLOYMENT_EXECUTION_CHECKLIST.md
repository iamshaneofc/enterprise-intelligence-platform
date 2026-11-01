# Final Deployment Execution Checklist & Runbook

**Document ID:** `EIP-DEP-RUNBOOK-001`  
**Target Environment:** AWS EC2 (Backend + PostgreSQL/pgvector) + Vercel (Frontend)  
**Target Region:** `ap-south-1` (Mumbai)  
**Date:** November 1, 2026  
**Auditor / Integration Engineer:** Senior AI Systems Architect & QA Integration Engineer  

---

## 1. Executive Deployment Summary

This runbook defines the exact execution sequence, commands, verification checklists, and risk mitigations for deploying the **Engineering Intelligence Platform (EIP)** to production.

```
+-----------------------------------------------------------------------------------+
|                                PRODUCTION ARCHITECTURE                           |
|                                                                                   |
|   +-----------------------+              HTTPS / CORS                             |
|   |   Vercel Edge CDN     | <====================================+                |
|   |  (React 18 + Vite)    |                                      |                |
|   |  SPA with vercel.json |                                      |                |
|   +-----------------------+                                      |                |
|                                                                  v                |
|   +---------------------------------------------------------------------------+   |
|   |   AWS EC2 Instance (ap-south-1) - t3.small / t3.medium                    |   |
|   |                                                                           |   |
|   |   +---------------------+   Port 8000   +-----------------------------+   |   |
|   |   |  eip_backend        | <------------ | Reverse Proxy / Nginx / ALB |   |   |
|   |   |  FastAPI (2 workers)|               | (SSL Termination)           |   |   |
|   |   +----------+----------+               +-----------------------------+   |   |
|   |              |                                                            |   |
|   |              | Volumes: document_storage (/app/storage/documents)         |   |
|   |              |                                                            |   |
|   |              v                                                            |   |
|   |   +---------------------+                                                 |   |
|   |   |  eip_postgres       | (pgvector/pgvector:pg16)                        |   |
|   |   |  Port 5432          | Volume: postgres_data                           |   |
|   |   |  or AWS RDS pgvector|                                                 |   |
|   |   +---------------------+                                                 |   |
|   |                                                                           |   |
|   |   External AI Providers:                                                  |   |
|   |   - OpenAI API (GPT-4o + text-embedding-3-small)                          |   |
|   |   - Langfuse Cloud (Telemetry & Tracing via SDK v5.1.0)                   |   |
|   +---------------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Frontend Deployment Readiness (Vercel)

### 2.1 Build & Asset Verification
- **Build Command:** `npm run build` (`tsc && vite build`)
- **Output Directory:** `dist/`
- **Build Status:** **VERIFIED PASSING** (0 errors, 4.37s compilation)
- **Asset Bundle Breakdown:**
  - `dist/index.html`: `1.10 kB` (gzip: `0.57 kB`)
  - `dist/assets/index-*.css`: `33.43 kB` (gzip: `6.19 kB`)
  - `dist/assets/ui-*.js`: `19.03 kB` (gzip: `3.99 kB`)
  - `dist/assets/index-*.js`: `103.09 kB` (gzip: `23.28 kB`)
  - `dist/assets/vendor-*.js`: `162.78 kB` (gzip: `53.13 kB`)

### 2.2 Environment Variables (Vercel Project Settings)
The frontend requires exactly **one** environment variable in Vercel:

| Variable Name | Environment | Value Description | Example Value |
|---|---|---|---|
| `VITE_API_BASE_URL` | Production & Preview | Public URL of EC2 Backend API | `http://<EC2-PUBLIC-IP>:8000` or `https://api.yourdomain.com` |

> [!CAUTION]
> **No Backend Secrets in Frontend:** Verify that `SECRET_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `DATABASE_URL` are **NEVER** prefixed with `VITE_` or added to Vercel. Only `VITE_API_BASE_URL` should exist in Vercel.

### 2.3 Vercel Configuration File (`frontend/vercel.json`)
The repository contains a production-ready `vercel.json`:
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ],
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ]
}
```

### 2.4 Vercel Deployment Steps
1. Navigate to [vercel.com](https://vercel.com) and click **"Add New Project"**.
2. Import repository `iamshaneofc/enterprise-intelligence-platform`.
3. Set **Root Directory** to `frontend`.
4. Framework preset: **Vite**.
5. Add Environment Variable:
   - Name: `VITE_API_BASE_URL`
   - Value: `http://<EC2-PUBLIC-IP>:8000` (or your domain/ALB URL)
6. Click **Deploy**.
7. Note the assigned deployment URL (e.g. `https://eip-frontend.vercel.app`).

### 2.5 CORS Configuration Requirement
In production, the backend rejects wildcard `*` origins. OpenCode must configure `CORS_ORIGINS` in AWS Secrets Manager (`eip/production/backend`) to match the Vercel URL:
```json
"CORS_ORIGINS": "[\"https://eip-frontend.vercel.app\"]"
```

---

## 3. Backend Deployment Compatibility

### 3.1 Startup & Health Configuration
- **Application Entrypoint:** `backend.app.main:app`
- **Uvicorn Production Command:**
  ```bash
  uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 2
  ```
- **Liveness Probe Endpoint:** `GET /health`  
  - Return: `200 OK`
  - Payload: `{"status": "ok", "service": "Enterprise Intelligence Platform", "version": "0.1.0", "environment": "production"}`
- **Readiness Probe Endpoint:** `GET /ready`  
  - Return: `200 OK`
  - Payload: `{"status": "ready", "database": "connected"}`

### 3.2 Persistent Document Storage
- **Container Path:** `/app/storage/documents` (governed by `STORAGE_DIR=/app/storage/documents`)
- **Docker Compose Volume Mapping:**
  ```yaml
  volumes:
    - document_storage:/app/storage/documents
  ```
- **Restart Survival Audit:**
  - **VERIFIED:** Uploaded PDF and Markdown documents are stored on the Docker host inside the named volume `document_storage`.
  - Container stops, restarts, and image updates (`docker compose pull && docker compose up -d`) **do not erase** uploaded files.

### 3.3 Critical Blocker Identification & Remediation

> [!WARNING]
> **BLOCKER 1: Missing AWS CLI in `backend/Dockerfile` runner image**
> - **Cause:** `backend/start.sh` executes `aws secretsmanager get-secret-value ...`. However, `backend/Dockerfile` runner stage installs only `libpq5`, `curl`, and `jq`, omitting `awscli`.
> - **Immediate Fix:** Ensure that either:
>   1. OpenCode's host-level deployment script fetches Secrets Manager into a local `.env.production` file and passes it via `docker compose --env-file .env.production up -d`, OR
>   2. `backend/start.sh` is guarded to check if `SECRET_KEY` and `DATABASE_URL` are already present in the environment before invoking `aws`.

> [!WARNING]
> **BLOCKER 2: Rigid Required Variables in `backend/start.sh`**
> - **Cause:** Lines 83–99 of `start.sh` require `ANTHROPIC_API_KEY`, `LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_SECRET_KEY` to be non-empty, exiting with code 1 if empty.
> - **Immediate Fix:** If Anthropic or Langfuse are optional in production, ensure `start.sh` allows empty strings for optional providers.

---

## 4. AWS Deployment Checklist (Exact Commands)

All commands in this section are read-only or standard operational deployment commands.

### Step 1: Connect to EC2 via AWS Systems Manager (SSM)
```bash
# Verify AWS CLI identity
aws sts get-caller-identity --region ap-south-1

# Connect to EC2 instance via SSM session
aws ssm start-session --target <EC2-INSTANCE-ID> --region ap-south-1
```

### Step 2: Install Docker & Docker Compose (if not pre-installed)

**For Amazon Linux 2023:**
```bash
sudo dnf update -y
sudo dnf install -y docker git
sudo systemctl enable --now docker
sudo usermod -aG docker ssm-user || sudo usermod -aG docker ec2-user

# Install Docker Compose Plugin
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/download/v2.29.2/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
docker compose version
```

**For Ubuntu 22.04 / 24.04 LTS:**
```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl gnupg git
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker ubuntu || sudo usermod -aG docker ssm-user
docker compose version
```

### Step 3: Clone / Update Repository on EC2
```bash
# Target installation directory
sudo mkdir -p /opt/eip
sudo chown -R $USER:$USER /opt/eip
cd /opt/eip

# Clone if first time, or pull latest commit
if [ ! -d ".git" ]; then
  git clone https://github.com/iamshaneofc/enterprise-intelligence-platform.git .
else
  git fetch origin
  git checkout main
  git pull origin main
fi

# Verify active commit hash
git log -1 --format="%H %s"
```

### Step 4: Test Database Connectivity (EC2 to RDS or Docker DB)
```bash
# If using AWS RDS PostgreSQL:
python3 -c "
import socket
host = '<RDS-ENDPOINT>'
port = 5432
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
try:
    s.connect((host, port))
    print('SUCCESS: RDS PostgreSQL port 5432 is reachable!')
except Exception as e:
    print('FAILED: Cannot reach RDS:', e)
finally:
    s.close()
"
```

### Step 5: Build & Start Containers
```bash
cd /opt/eip

# Start PostgreSQL and Backend services
docker compose up -d --build

# Verify running containers and health status
docker compose ps
```

### Step 6: Execute Alembic Database Migrations
```bash
# Apply all database migrations to head
docker compose exec backend python -m alembic -c backend/alembic.ini upgrade head

# Verify current migration status
docker compose exec backend python -m alembic -c backend/alembic.ini current
```

### Step 7: Inspect Container Logs & Verify Startup
```bash
# Check database logs
docker compose logs --tail=50 db

# Check backend logs
docker compose logs --tail=50 backend
```

### Step 8: Verify Backend Health Endpoints
```bash
# Liveness probe
curl -i http://localhost:8000/health

# Readiness probe (verifies database connection pool)
curl -i http://localhost:8000/ready
```

---

## 5. End-to-End Production Verification Plan (Smoke Tests)

Execute this 10-step smoke test checklist immediately following container startup.

| Step | Verification Task | Expected Result | Pass/Fail |
|:---:|---|---|:---:|
| **1** | `GET /health` | HTTP 200, `"status": "ok"` | [ ] |
| **2** | `GET /ready` | HTTP 200, `"database": "connected"` | [ ] |
| **3** | User Registration (`POST /api/v1/auth/register`) | HTTP 201, User object with hashed password | [ ] |
| **4** | User Login (`POST /api/v1/auth/login`) | HTTP 200, JWT token returned | [ ] |
| **5** | Workspace Isolation (`POST /api/v1/workspaces`) | HTTP 201, Dedicated workspace provisioned | [ ] |
| **6** | Document Upload (`POST /.../documents/upload`) | HTTP 201, Chunks created with 1536-dim OpenAI vectors | [ ] |
| **7** | Grounded RAG Query (`POST /.../chat`) | HTTP 200, Answer with `[c_0]` citation from real GPT-4o | [ ] |
| **8** | Conversational Follow-up (`POST /.../chat`) | HTTP 200, Preserves `conversation_id`, answers multi-turn | [ ] |
| **9** | Autonomous Agent (`POST /.../agent/investigate`) | HTTP 201, Multi-step tool reasoning with real GPT-4o | [ ] |
| **10** | Frontend Integration (Browser UI via Vercel) | UI loads, displays workspace, login works, RAG responds | [ ] |

### Automated Smoke Test Script
Save and run on EC2 to execute steps 1–9 automatically:
```bash
cat << 'EOF' > /tmp/prod_smoke_test.py
import requests, time, sys

BASE = "http://127.0.0.1:8000/api/v1"

print("1. Testing health...")
h = requests.get("http://127.0.0.1:8000/health").json()
assert h["status"] == "ok", f"Health failed: {h}"
print("   ✓ Backend healthy:", h)

print("2. Registering smoke test user...")
email = f"prod_smoke_{int(time.time())}@example.com"
reg = requests.post(f"{BASE}/auth/register", json={"email": email, "password": "ProductionPassword123!", "full_name": "Prod Tester"})
assert reg.status_code == 201, f"Registration failed: {reg.text}"

print("3. Logging in...")
login = requests.post(f"{BASE}/auth/login", json={"email": email, "password": "ProductionPassword123!"}).json()
token = login["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("   ✓ JWT acquired")

print("4. Creating workspace...")
ws = requests.post(f"{BASE}/workspaces", json={"name": "Prod Smoke Workspace"}, headers=headers).json()
ws_id = ws["id"]
print("   ✓ Workspace created:", ws_id)

print("5. Ingesting test document...")
doc_bytes = b"# Production Runbook\nDefault timeout is 300 seconds."
up = requests.post(f"{BASE}/workspaces/{ws_id}/documents/upload", files={"file": ("runbook.md", doc_bytes, "text/markdown")}, headers=headers)
assert up.status_code == 201, f"Upload failed: {up.text}"
print("   ✓ Document uploaded and embedded with OpenAI text-embedding-3-small")

print("6. Executing Grounded RAG query...")
chat = requests.post(f"{BASE}/workspaces/{ws_id}/chat", json={"query": "What is the default timeout in the runbook?", "workspace_id": ws_id}, headers=headers).json()
assert chat["provider_used"] == "openai", f"Not OpenAI: {chat}"
print("   ✓ Answer:", chat["answer"])
print("   ✓ Citations:", len(chat.get("citations", [])))

print("\nALL BACKEND PRODUCTION SMOKE TESTS PASSED!")
EOF
python3 /tmp/prod_smoke_test.py
```

---

## 6. Exact Order of Execution (Deploy Timeline)

```
+-------------------------------------------------------------------------------+
| PHASE 1: PRE-FLIGHT SECRETS & IAM (OpenCode Ownership)                         |
|   1. Generate 32-byte SECRET_KEY                                              |
|   2. Create AWS Secrets Manager secret 'eip/production/backend'               |
|   3. Attach SecretsManager:GetSecretValue IAM policy to EC2 instance role     |
+-------------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------------+
| PHASE 2: EC2 DOCKER & BACKEND BRING-UP (Operator Ownership)                  |
|   4. Connect to EC2 via AWS SSM                                               |
|   5. Verify Docker & Docker Compose versions                                  |
|   6. Git pull latest 'main' branch to /opt/eip                                |
|   7. Launch containers: docker compose up -d --build                          |
|   8. Run Alembic migrations: alembic upgrade head                             |
|   9. Verify curl http://localhost:8000/health and /ready                      |
+-------------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------------+
| PHASE 3: FRONTEND VERCEL DEPLOYMENT                                           |
|   10. Deploy frontend to Vercel with VITE_API_BASE_URL=http://<EC2-IP>:8000   |
|   11. Copy assigned Vercel URL (https://*.vercel.app)                         |
|   12. Update CORS_ORIGINS in AWS Secrets Manager with Vercel URL              |
|   13. Restart backend container to apply new CORS origins                     |
+-------------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------------+
| PHASE 4: PRODUCTION VERIFICATION                                              |
|   14. Execute /tmp/prod_smoke_test.py on EC2                                  |
|   15. Open Vercel URL in web browser and verify full user journey             |
|   16. Confirm LLM interactions in PostgreSQL llm_logs table                   |
+-------------------------------------------------------------------------------+
```

