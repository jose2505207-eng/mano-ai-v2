# Qoder Notes — Mano AI v2

## Architecture Decisions

- **FastAPI + static frontend**: The backend serves the built Next.js static export directly via `StaticFiles`, keeping deployment simple (single port, single container).
- **Agent pipeline is sequential**: Each agent (Intent → Search → Browser Loop → Summary) runs in order. This keeps the flow predictable and debuggable. Future versions may parallelize independent sub-tasks.
- **Browser provider abstraction**: `BrowserManager` wraps both Actionbook (cloud) and Playwright (local) behind a common interface. The active provider is selected at runtime based on configuration, with automatic fallback.
- **LLM router pattern**: All LLM calls go through a single router that can direct requests to OpenAI, TokenRouter, Qwen, or Z.ai based on the `LLM_PROVIDER` setting and key availability.
- **In-memory task store**: Tasks are stored in a Python dict for simplicity. This means task state is lost on restart. A database migration path is planned.

## Known Limitations

- **No persistent task history**: Task state is in-memory and lost on server restart.
- **CAPTCHA walls**: The agent detects CAPTCHAs and stops, but cannot solve them.
- **Login walls**: The agent pauses when it encounters login requirements and asks the user to take over.
- **Anti-bot detection**: Some sites block Playwright's automated browser. Actionbook's cloud browser may help in some cases.
- **Payment fields blocked by design**: The agent will never auto-fill credit card numbers, CVV, or complete payment flows.
- **Single-tab operation**: The agent works on one page at a time. Multi-tab support is on the roadmap.
- **No WebSocket/SSE streaming**: Task steps update via polling. Real-time streaming is planned.

## Future Improvements

1. **Persistent task history** — SQLite or PostgreSQL backend for task state
2. **WebSocket streaming** — Real-time task step updates to the frontend
3. **Actionbook full SDK** — Replace stubs with real Actionbook SDK calls once API docs/keys are available
4. **AgentField external orchestration** — Delegate multi-agent coordination to AgentField when `AGENTFIELD_API_KEY` is set
5. **EverMind memory integration** — Cross-session profile learning and context persistence
6. **Multi-tab support** — Agent can work across multiple browser tabs
7. **Mobile-responsive UI** — Responsive layout for smaller screens
8. **Session replay** — Record and replay browser sessions for debugging
9. **Screenshot diffing** — Detect meaningful page changes vs. dynamic content shifts
10. **Task cancellation mid-run** — Gracefully stop the agent loop at any step

## How to Add New Agents

1. Create a new file in `backend/app/agents/` (e.g., `my_agent.py`)
2. Define an async function that takes the task context and returns a structured result
3. Import and call your agent from `backend/app/agents/orchestrator.py` in the appropriate step
4. Add any new Pydantic schemas to `backend/app/schemas/`
5. Add any new LLM prompts to `backend/app/llm/prompts.py`
6. Write tests in `backend/tests/`

Agent function signature pattern:

```python
async def my_agent(task: str, context: AgentContext) -> AgentResult:
    """Describe what this agent does."""
    # 1. Gather inputs from context
    # 2. Call LLM or tools
    # 3. Return structured result
    pass
```

## How to Add New Sponsors

1. Add the API key field to `backend/app/core/config.py` (Settings class)
2. Add the key to `.env.example` with an empty default
3. Add the sponsor entry in `backend/app/main.py` (`sponsor_status` endpoint)
4. Create an adapter/provider in the appropriate module (e.g., `backend/app/browser/`, `backend/app/llm/`, `backend/app/tools/`)
5. Wire the adapter into the relevant agent or manager
6. Add the sponsor to the README sponsor table
7. Test with and without the key configured
