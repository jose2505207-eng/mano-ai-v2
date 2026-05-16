from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Mano AI"
    app_env: str = "development"
    app_url: str = "http://localhost:8000"
    port: int = 8000

    # Browser / ActionBook (sponsor)
    browser_provider: str = "playwright"
    browser_headless: bool = False
    actionbook_api_key: str = ""
    actionbook_cli_path: str = "actionbook"

    # Bright Data (sponsor) — SERP / scraping
    brightdata_api_token: str = ""
    brightdata_zone: str = ""

    # Primary LLM — OpenAI
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # TokenRouter (sponsor) — LLM routing proxy
    tokenrouter_api_key: str = ""

    # Qwen Cloud (sponsor) — LLM provider
    qwen_api_key: str = ""

    # Z.ai (sponsor) — LLM provider
    zai_api_key: str = ""

    # AgentField (sponsor) — AI agent platform
    agentfield_api_key: str = ""

    # Nosana (sponsor) — GPU compute
    nosana_api_key: str = ""

    # EverMind (sponsor) — Memory / context
    evermind_api_key: str = ""

    # Zeabur (sponsor) — deployment platform (no API key needed in backend;
    # listed here for completeness / future use)
    zeabur_api_key: str = ""

    # Qoder (sponsor) — AI coding assistant (no API key needed in backend;
    # listed here for completeness / future use)
    qoder_api_key: str = ""

    # AgentField context key (legacy alias)
    acontext_api_key: str = ""

    # Agent safety limits
    max_agent_steps: int = 30
    require_approval_for_pii: bool = True
    require_approval_for_submit: bool = True
    require_approval_for_payment: bool = True

    # Butterbase (sponsor) — Backend-as-a-service data persistence
    butterbase_api_key: str = ""

    class Config:
        env_file = ("../../.env", "../.env", ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
