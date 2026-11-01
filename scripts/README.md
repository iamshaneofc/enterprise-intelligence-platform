# Automation & Utility Scripts (`scripts/`)

## 1. Folder Responsibility
The `scripts/` directory contains operational and developer utility scripts to automate development tasks, database seeding, document ingestion benchmarks, evaluation pipeline execution, and deployment verification.

## 2. Planned Modules and Scripts

- **`seed_data/` & Ingestion Utilities:**
  - Automated ingestion scripts for loading sample technical documents, policies, and test corpora into the platform.
  - Test user provisioning and role assignment scripts.
  - **Status:** PLANNED / NOT IMPLEMENTED.

- **`evaluation_runner/`:**
  - Standalone evaluation execution scripts that run the 20+ question benchmark dataset through the RAG and agent pipelines and generate summary reports.
  - **Status:** PLANNED / NOT IMPLEMENTED.

- **Smoke & Healthcheck Utilities:**
  - Verification scripts to validate health check endpoints, database connectivity, vector index readiness, and LLM provider availability in both local and cloud environments.
  - **Status:** PLANNED / NOT IMPLEMENTED.

## 3. Connection to the Overall Platform
These scripts interface directly with the backend APIs and database to provide repeatable, automated testing of system capabilities—specifically enabling the automated execution of Module G (AI Evaluation) and supporting rapid live technical verification.

