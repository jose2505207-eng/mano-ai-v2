# Mano AI

**The internet, guided step by step.**

## 🚀 Live Demo

**Deployed on Zeabur:** [https://mano-ai.zeabur.app](https://mano-ai.zeabur.app)

[![Deployed on Zeabur](https://img.shields.io/badge/Deployed%20on-Zeabur-7B61FF?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHZpZXdCb3g9IjAgMCAyMCAyMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNMTUgNEg1TDEwIDEwTDUgMTZIMTVMMTAgMTBMMTUgNFoiIGZpbGw9IndoaXRlIi8+PC9zdmc+)](https://mano-ai.zeabur.app)

---

Mano AI is a real, general-purpose browser-using AI web agent. You give it a task in plain language — "Book the cheapest flight from Miami to Bogotá next Friday" — and it searches the web, opens real websites, reads pages, clicks buttons, fills forms, and stops before anything sensitive or irreversible.

This is not a fake demo. This is not a hardcoded workflow. Mano AI is a real web operator that perceives, decides, and acts — with safety built in from the ground up.

**For people who need the internet but struggle with computers.** Mano AI was built for the millions of people who find the web overwhelming: seniors, non-native speakers, anyone who just wants to get something done without navigating complex sites alone. You describe what you need. Mano does the clicking, reading, and form-filling — and pauses when it matters.

---

## Quick Start

```bash
# Clone
git clone https://github.com/your-repo/mano-ai-v2.git
cd mano-ai-v2

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium --with-deps

# Frontend setup
cd ../frontend
npm install
npm run build

# Configure
cd ..
cp .env.example .env
# Edit .env with your API keys

# Run
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000` for the full app (backend serves the built frontend).

---

## Docker Quick Start

```bash
cp .env.example .env
# Edit .env with your API keys
docker-compose up --build
```

The production container builds the frontend and serves everything on port 8000.

To run frontend in dev mode alongside the containerized backend:

```bash
docker-compose --profile dev up --build
```

---

## Development Mode

Run backend and frontend separately for hot-reload during development:

```bash
# Terminal 1: Backend (with auto-reload)
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend (with hot reload)
cd frontend
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

- Backend: `http://localhost:8000`
- Frontend dev server: `http://localhost:3000`

---

## Architecture

### Agent Flow

```
User Task
  │
  ▼
Intent Agent ─── parse goal, determine start URL
  │
  ▼
Search Agent ─── query Bright Data SERP API, find official starting page
  │
  ▼
Browser Loop ────────────────────────────────────┐
  │                                              │
  ├─ Observe (URL, title, text, elements,       │
  │           screenshot)                        │
  │         │                                    │
  │         ▼                                    │
  ├─ LLM Decide (structured ActionDecision)     │
  │         │                                    │
  │         ▼                                    │
  ├─ Validate (safety risk classification)       │
  │         │                                    │
  │         ▼                                    │
  ├─ Execute (click / fill / navigate / stop)    │
  │         │                                    │
  │         └──────── repeat until done ─────────┘
  │
  ▼
Summary Agent ─── explain what happened
```

### Agents

| Agent | Role |
|---|---|
| **Intent Agent** | Parses the user's natural-language task into a structured goal with constraints and a suggested start URL |
| **Search Agent** | Uses Bright Data's SERP API to find the right starting page on the public web |
| **Browser Agent** | Observes the current page state (URL, title, interactive elements, screenshot) and decides the next action |
| **Safety Agent** | Classifies every proposed action by risk level before execution |
| **Critic Agent** | Detects loops, irrelevant actions, and stale page states to keep the agent on track |
| **Form Agent** | Specializes in filling complex forms with profile data while respecting safety boundaries |
| **Memory Agent** | Tracks what has been done and what remains across the task lifecycle |
| **Summary Agent** | Produces a human-readable summary of what the agent did, what it found, and where it stopped |

### Browser Provider Abstraction

Mano AI uses a provider pattern for browser control:

- **Actionbook** (primary) — Cloud browser action manuals and automation. Preferred when `ACTIONBOOK_API_KEY` is configured.
- **Playwright** (fallback) — Local Chromium browser via Playwright. Always available, no API key required.

The `BrowserManager` automatically selects the active provider and reports sponsor connection status.

### Safety System

Every action goes through a two-layer safety check:

1. **Risk Classifier** — Labels each action as `safe`, `caution`, `sensitive`, or `blocked`
2. **Action Validator** — Enforces approval gates based on the risk level and user configuration

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check — confirms the backend is running |
| `GET` | `/api/sponsor-status` | Returns connectivity status for all tech sponsors |
| `POST` | `/api/tasks` | Create and start a new web task |
| `GET` | `/api/tasks/{id}` | Get the current state of a task |
| `POST` | `/api/tasks/{id}/continue` | Continue a paused task (with input or approval) |
| `POST` | `/api/tasks/{id}/stop` | Stop a running task |
| `GET` | `/api/tasks/{id}/snapshot` | Get the latest browser screenshot for a task |
| `GET` | `/api/profile` | Get the user's saved profile |
| `POST` | `/api/profile` | Update the user's profile |
| `GET` | `/api/logs` | Get activity logs (task summaries) |

---

## Tech Sponsor Stack

Mano AI is powered by an incredible set of technology sponsors:

| # | Sponsor | What They Provide |
|---|---|---|
| 1 | **Bright Data** | Web data infrastructure & SERP API — powers web search and discovery |
| 2 | **AgentField** | AI agent orchestration platform — multi-agent coordination |
| 3 | **Nosana** | Decentralized GPU compute network — scalable inference |
| 4 | **Actionbook** | Browser action manuals & automation — cloud browser control |
| 5 | **EverMind** | Persistent AI memory & context — cross-session learning |
| 6 | **Qwen Cloud** | Large language model provider — alternative LLM backend |
| 7 | **Zeabur** | One-click cloud deployment — hosting and infrastructure |
| 8 | **Z.ai** | Advanced AI language models — alternative LLM backend |
| 9 | **Qoder** | AI-powered coding assistant — built this application |
| 10 | **TokenRouter** | Intelligent LLM request routing — model selection and failover |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your keys:

| Variable | Required | Description |
|---|---|---|
| `APP_NAME` | No | Application name (default: `Mano AI`) |
| `APP_ENV` | No | Environment: `development` or `production` |
| `APP_URL` | No | Public URL of the app |
| `PORT` | No | Server port (default: `8000`) |
| `BROWSER_PROVIDER` | No | `playwright` or `actionbook` (default: `playwright`) |
| `ACTIONBOOK_API_KEY` | No | Enables Actionbook browser control |
| `ACTIONBOOK_CLI_PATH` | No | Path to Actionbook CLI (default: `actionbook`) |
| `BRIGHTDATA_API_TOKEN` | No | Enables Bright Data web search |
| `BRIGHTDATA_ZONE` | No | Bright Data zone for SERP queries |
| `LLM_PROVIDER` | No | LLM backend: `openai`, `tokenrouter`, `qwen`, `zai` (default: `openai`) |
| `OPENAI_API_KEY` | **Yes** | Required for LLM decisions (primary provider) |
| `OPENAI_MODEL` | No | OpenAI model to use (default: `gpt-4o-mini`) |
| `TOKENROUTER_API_KEY` | No | Enables TokenRouter LLM routing |
| `QWEN_API_KEY` | No | Enables Qwen Cloud LLM |
| `ZAI_API_KEY` | No | Enables Z.ai LLM |
| `AGENTFIELD_API_KEY` | No | Enables AgentField orchestration |
| `NOSANA_API_KEY` | No | Enables Nosana GPU compute |
| `EVERMIND_API_KEY` | No | Enables EverMind persistent memory |
| `ACONTEXT_API_KEY` | No | Enables Acontext memory integration |
| `MAX_AGENT_STEPS` | No | Maximum steps per task (default: `30`) |
| `REQUIRE_APPROVAL_FOR_PII` | No | Ask before filling personal info (default: `true`) |
| `REQUIRE_APPROVAL_FOR_SUBMIT` | No | Ask before submitting forms (default: `true`) |
| `REQUIRE_APPROVAL_FOR_PAYMENT` | No | Ask before payment actions (default: `true`) |
| `NEXT_PUBLIC_API_URL` | No | Backend URL for frontend (default: `http://localhost:8000`) |

---

## Safety Design

Mano AI was designed around a core principle: **the agent should do the work, but the human stays in control.**

### Risk Levels

Every proposed browser action is classified into one of four risk levels:

| Level | Meaning | Examples | Behavior |
|---|---|---|---|
| **safe** | No risk of data exposure or irreversible action | Navigate, search, click menus, fill city/dates | Executed automatically |
| **caution** | Involves personal or semi-sensitive data | Fill name, email, phone, account creation | Warned — proceeds unless user opts out |
| **sensitive** | Irreversible or financially significant | Payment, submit, book, sign, government/medical forms | Requires explicit user approval before proceeding |
| **blocked** | Should never be automated | Card numbers, SSN, passport, CAPTCHA bypass, passwords | Agent stops and hands control back to the user |

### Approval Gates

Approval gates are triggered when:
- An action is classified as `sensitive` or `blocked`
- The action involves submitting a form with personal data
- The action would navigate to a payment page
- The agent detects a CAPTCHA or login wall

### What Is Never Automated

The following actions are **never** performed without explicit human intervention:

- Entering credit card numbers or CVV codes
- Filling in Social Security Numbers or national IDs
- Entering passport or driver's license numbers
- Submitting passwords
- Bypassing CAPTCHA challenges
- Confirming purchases or financial transactions

### "I got you this far — take over here."

When Mano AI reaches a sensitive step, it doesn't just stop — it explains exactly where it is, what it was about to do, and why it paused. The user can then complete the action manually, confident that everything up to that point was done correctly.

---

## Zeabur Deployment

1. Push your code to a GitHub repository.
2. Connect the repository in the [Zeabur dashboard](https://zeabur.com).
3. Set environment variables (`OPENAI_API_KEY`, etc.) in Zeabur project settings.
4. Zeabur auto-detects the `Dockerfile` and `zeabur.json` configuration.
5. Health check endpoint: `GET /api/health`

---

## Running Tests

```bash
cd backend
pytest
```

---

## Project Structure

```
mano-ai-v2/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI application, routes, static serving
│   │   ├── agents/           # Agent pipeline (intent, search, browser, safety, etc.)
│   │   ├── api/              # API route handlers (tasks, profile, logs)
│   │   ├── browser/          # Browser provider abstraction (Actionbook + Playwright)
│   │   ├── core/             # Configuration and settings
│   │   ├── llm/              # LLM router (OpenAI, TokenRouter, Qwen, Z.ai)
│   │   ├── memory/           # Profile persistence (local JSON)
│   │   ├── safety/           # Risk classifier and action validator
│   │   ├── schemas/          # Pydantic models
│   │   └── tools/            # Bright Data SERP tool
│   ├── requirements.txt
│   └── tests/
├── frontend/
│   ├── app/                  # Next.js pages
│   ├── components/           # React components (ChatPanel, BrowserPanel, etc.)
│   ├── lib/                  # Frontend utilities
│   └── package.json
├── data/
│   └── profile.template.json # Default user profile template
├── Dockerfile                # Multi-stage production build
├── docker-compose.yml        # Development Docker Compose
├── zeabur.json               # Zeabur deployment configuration
├── .env.example              # Environment variable template
└── .dockerignore             # Docker build exclusions
```

---

## License

MIT
