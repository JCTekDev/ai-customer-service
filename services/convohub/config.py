import logging
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    LOG_LEVEL: str = Field(default="INFO")
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8080)

    # Ollama shared base
    OLLAMA_BASE_URL: str = Field(default="http://ollama:11434")
    OLLAMA_TIMEOUT: int = Field(default=60)

    # Supervisor
    SUPERVISOR_MODEL: str = Field(default="llama3.1")
    SUPERVISOR_TEMPERATURE: float = Field(default=0.2)
    SUPERVISOR_MAX_STEPS: int = Field(default=6)
    SUPERVISOR_SYSTEM_PROMPT: str = Field(default="You are the Supervisor. Decide which tool to call based on the user's intent:\n- Use info_agent for FAQs or general company/customer information.\n- Use calendar_scheduler for availability checking and meeting scheduling.\nOutput: If a tool is needed, respond with: TOOL:<tool_name>:<user_query>. Otherwise answer directly.")

    # Info Agent
    INFO_AGENT_MODEL: str = Field(default="llama2.1")
    INFO_AGENT_SYSTEM_PROMPT: str = Field(default="You are an FAQ assistant. Answer clearly, concisely, and politely.")
    INFO_AGENT_RECENT_MESSAGES_WINDOW: int = Field(default=6)
    INFO_AGENT_TOKEN_BUDGET: int = Field(default=8192)
    INFO_AGENT_SUMMARY_TOKEN_BUDGET: int = Field(default=800)
    INFO_AGENT_MESSAGES_TO_SUMMARIZE: int = Field(default=8)
    INFO_AGENT_SUMMARIZATION_PROMPT_TOKENS: int = Field(default=100)
    INFO_AGENT_MESSAGE_SUMMARY_CHAR_LIMIT: int = Field(default=600)
    REDIS_URL: Optional[str] = Field(default=None)

    # Calendar Scheduler
    CALENDAR_ID: str = Field(default="primary")
    DEFAULT_MEETING_DURATION_MINUTES: int = Field(default=30)
    TIMEZONE: str = Field(default="UTC")
    GOOGLE_CALENDAR_CREDENTIALS_FILE: str = Field(default="./credentials.json")

    # WAHA integration (outbound)
    WAHA_API_KEY: str = Field(default="changeme")
    WAHA_BASE_URL: str = Field(default="http://waha:3000")
    WAHA_RESPONSE_TIMEOUT: int = Field(default=30)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

settings = Settings()
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
