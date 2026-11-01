# ADR-007: Practical Cloud Deployment and Infrastructure Strategy

## Status
ACCEPTED

## Context
Sections 6, 7, and 9 of the Technical Assessment state:
- *"The application must be developed end to end. Deployment instructions will not be provided. You are expected to independently select appropriate infrastructure, configure the environment, deploy your application, and resolve deployment-related issues."*
- *"A local-only application will not qualify as a completed submission."*
- Reviewers require publicly accessible Frontend and Backend URLs, complete with Swagger `/docs` and live functionality.

We must choose a cloud hosting and deployment strategy that guarantees high availability, automated SSL/HTTPS, secure secrets management, and reproducible container environments without introducing unnecessary operational overhead.

## Decision
We adopt a **Containerized Cloud PaaS / Managed Container Strategy**:

1. **Backend & Worker Layer:**
   - Multi-stage Docker container packaging Python 3.11, FastAPI, PyMuPDF, and application dependencies.
   - Deployed on **AWS App Runner** (or **AWS ECS Fargate** / **Render Managed Container**).
   - Exposes `/health` and `/ready` endpoints for automated container health checking.
2. **Frontend Layer:**
   - Single-Page Application (SPA) built with React 18, Vite, TypeScript, and Tailwind CSS.
   - Deployed on **Vercel** or **AWS S3 + CloudFront CDN**, providing automatic global edge caching, instant rollbacks, and managed HTTPS.
3. **Database & Vector Engine:**
   - Managed **PostgreSQL 16 with `pgvector`** enabled, hosted on **AWS RDS for PostgreSQL** (or **Supabase / Neon DB**).
   - Provides automated backups, connection pooling, and native `vector` extension support.
4. **Caching & Task Broker:**
   - Managed **Redis 7** hosted on **AWS ElastiCache** (or **Redis Cloud / Upstash**).
5. **Raw Document Storage:**
   - **AWS S3** bucket (with restricted private access and presigned URLs) or persistent encrypted object storage.
6. **Local Development Parity:**
   - A multi-container `docker-compose.yml` configuration mirrors the cloud topology locally (FastAPI, React, PostgreSQL 16 with `pgvector`, Redis 7).

## Alternatives Considered
- **Kubernetes (AWS EKS / GKE):**
  - *Pros:* Complete orchestration control.
  - *Cons:* Massive overkill for a single-developer 24-hour assessment. Incurs substantial configuration complexity (Ingress controllers, Helm charts, IAM role binding, CSI drivers) that distracts from core AI engineering requirements.
- **Bare Virtual Machine (Single AWS EC2 instance with manual SSH):**
  - *Pros:* Inexpensive.
  - *Cons:* Manual SSL setup (Certbot), no automated health recovery, high risk of environment drift, manual daemon supervision.

## Rationale
Managed container runtimes and managed databases provide production reliability with zero server maintenance:
- Automatic HTTPS certificates.
- Built-in health checks and container auto-restarts upon uncaught crashes.
- Seamless environment variable injection for API keys (Anthropic, OpenAI).
- Publicly accessible URLs accessible immediately to reviewers.

## Consequences
- **Positive:**
  - Satisfies the strict cloud deployment mandate without unnecessary operational risks.
  - Rapid, repeatable deployments via Docker and Git triggers.
  - Secure secrets management ensuring zero private credentials in source code.
- **Negative:**
  - Minor cold starts if using serverless container tiering (mitigated by configuring minimum provisioned instances or health pingers).

