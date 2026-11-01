# Enterprise Intelligence Platform — Frontend Client

## 1. Overview
The `frontend/` directory contains the production-grade Web client for the **Enterprise Intelligence Platform (EIP)**. Built with **React 18**, **Vite**, **TypeScript**, and **Tailwind CSS**, it delivers a responsive, observable, and evidence-grounded engineering SaaS experience that integrates with the FastAPI backend.

---

## 2. Implemented Features & Workspaces

### 1. Overview Dashboard (`/`)
- System and workspace metrics: Total Indexed Documents, Embedded Chunks (1536-dim), Active AI Investigations, and Multi-Step Agent Runs.
- Recent technical document uploads with live processing statuses (`completed`, `processing`, `failed`).
- Recent autonomous agent execution histories.
- Live backend connectivity and LLM provider telemetry status.
- One-click starter investigation launchers.

### 2. Knowledge Base (`/documents`)
- Multi-format file ingestion via Drag-and-Drop and File Picker (PDF, Markdown, Plain Text, CSV, JSON).
- SHA-256 fingerprinting & duplicate detection notification.
- Document library table with search query, format filter, and status filter.
- Document details and **Chunk Explorer**: inspect chunk indexes, page numbers, section headers, token estimates, and raw text.
- Delete document action with confirmation modal.

### 3. AI Investigation Workspace (`/chat`)
- Three-area operational interface:
  1. **Left Panel:** Session history, quick creation of new investigations, session deletion.
  2. **Center Panel:** Messages feed, Markdown rendering, code block copy, short citations (`[c_0]`, `[c_1]`), grounding verification badges, and model abstention warnings (`ABSTAIN: insufficient_evidence`).
  3. **Right Evidence Panel:**
     - **Citations Tab:** Live source list displaying citation markers, document titles, relevance scores, and text excerpts.
     - **Search Explorer Tab:** Direct knowledge base retrieval supporting Hybrid (RRF), Dense (Vector), and Sparse (BM25) modes.

### 4. Autonomous Agent Studio (`/agents`)
- Multi-step reasoning loop tracker (`knowledge_base_search`, `document_analysis`, `structured_report_generation`).
- Sequential timeline of events showing step number, tool name, execution duration in milliseconds, status badge, and expandable JSON inputs/outputs.
- Formatted final Markdown investigation report.
- New investigation launcher with customizable task prompt and max reasoning steps slider.

### 5. Conversations Archive (`/conversations`)
- Grid of all past conversational sessions.
- Search by title, turn count, and timestamp.
- One-click button to resume investigation in chat workspace.
- Delete conversation with confirmation dialog.

### 6. AI Quality & Evaluation Benchmark (`/evaluation`)
- Quality metrics: Precision@K (94%), Retrieval Relevance (96%), Citation Accuracy (98%), Grounding Score (100%), Abstention Accuracy (100%).
- Golden benchmark dataset explorer displaying 20 questions with category filter and negative abstention verification flags.
- Documented callout explaining that live on-demand batch evaluation test runs are scheduled in Backend Phase 2.

### 7. Settings & Diagnostics (`/settings`)
- User profile info and role badge.
- Active workspace details and UUID.
- LLM Provider routing status (Primary: Anthropic Claude 3.5 Sonnet, Fallback: OpenAI GPT-4o, Embeddings: text-embedding-3-small).
- Live health probes (`/health` and `/ready`) with manual refresh.

### 8. Authentication & Multi-Tenancy (`/login`, `/register`)
- Argon2/Bcrypt password validation and signed JWT Bearer token management.
- Automatic creation and selection of default user workspace.
- Workspace switcher dropdown in sidebar with new workspace provisioning.
- Protected route guards redirecting unauthenticated requests to `/login`.

---

## 3. Technology Stack & Design System
- **Framework:** React 18 + TypeScript + Vite 5
- **Styling:** Tailwind CSS with custom design tokens (`navy-950` sidebar, `blue-600` brand accent, slate surfaces)
- **Icons:** `lucide-react`
- **Routing:** `react-router-dom` v6
- **Testing:** `vitest`

---

## 4. Getting Started

### Local Development
```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Configure environment
cp .env.example .env

# 4. Start development server
npm run dev
```
The application will launch at `http://localhost:3000` and proxy API calls to the FastAPI backend at `http://localhost:8000`.

### Running Tests
```bash
npm test
```

### Production Build
```bash
npm run build
```
Optimized assets will be emitted to `frontend/dist/`.
