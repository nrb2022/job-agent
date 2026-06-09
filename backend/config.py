from pydantic_settings import BaseSettings
from typing import Optional
import secrets

class Settings(BaseSettings):
    anthropic_api_key: str
    database_url: str = "sqlite+aiosqlite:///./jobagent.db"
    encryption_key: str = secrets.token_urlsafe(32)
    secret_key: str = secrets.token_urlsafe(32)
    linkedin_email: Optional[str] = None
    linkedin_password: Optional[str] = None
    indeed_email: Optional[str] = None
    indeed_password: Optional[str] = None
    naukri_email: Optional[str] = None
    naukri_password: Optional[str] = None
    agent_delay_min: float = 2.0
    agent_delay_max: float = 5.0
    max_applications_per_day: int = 20
    human_review_mode: bool = False
    headless_browser: bool = False
    redis_url: str = "redis://localhost:6379"
    gemini_api_key: Optional[str] = None
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
