from sqlmodel import SQLModel, Field, Relationship, create_engine, Session, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from typing import Optional, List
from datetime import datetime
from enum import Enum
import json


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    MATCHED = "matched"
    APPLYING = "applying"
    APPLIED = "applied"
    FAILED = "failed"
    SKIPPED = "skipped"
    REVIEWING = "reviewing"  # Human review mode


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


# ─── User Profile ─────────────────────────────────────────────────────────────

class UserProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # CV metadata
    cv_filename: Optional[str] = None
    cv_path: Optional[str] = None
    cv_text: Optional[str] = None           # Raw extracted text

    # Parsed CV data (stored as JSON strings)
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    current_title: Optional[str] = None
    years_experience: Optional[int] = None
    skills_json: str = Field(default="[]")           # ["Python", "FastAPI", ...]
    experience_json: str = Field(default="[]")       # [{title, company, years}, ...]
    education_json: str = Field(default="[]")        # [{degree, institution, year}, ...]
    summary: Optional[str] = None

    # Job Preferences
    target_titles_json: str = Field(default="[]")   # ["Software Engineer", ...]
    preferred_locations_json: str = Field(default="[]")  # ["Bangalore", "Dubai", ...]
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    currency: str = "INR"
    remote_ok: bool = True
    notice_period_days: Optional[int] = None
    portals_json: str = Field(default="[]")          # ["linkedin", "indeed", ...]

    @property
    def skills(self) -> List[str]:
        return json.loads(self.skills_json)

    @property
    def preferred_locations(self) -> List[str]:
        return json.loads(self.preferred_locations_json)

    @property
    def target_titles(self) -> List[str]:
        return json.loads(self.target_titles_json)

    @property
    def portals(self) -> List[str]:
        return json.loads(self.portals_json)


# ─── Agent Session ────────────────────────────────────────────────────────────

class AgentSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    profile_id: int = Field(foreign_key="userprofile.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: AgentStatus = AgentStatus.IDLE
    portal: str = ""
    total_found: int = 0
    total_matched: int = 0
    total_applied: int = 0
    total_failed: int = 0
    log_json: str = Field(default="[]")  # Agent activity log


# ─── Job Application ─────────────────────────────────────────────────────────

class JobApplication(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="agentsession.id")
    profile_id: int = Field(foreign_key="userprofile.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    applied_at: Optional[datetime] = None

    # Job details
    portal: str = ""
    job_title: str = ""
    company: str = ""
    location: str = ""
    job_url: str = ""
    job_description: Optional[str] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None  # Full-time, Contract, etc.

    # Matching
    match_score: float = 0.0         # 0-100
    match_reasons_json: str = Field(default="[]")
    match_gaps_json: str = Field(default="[]")

    # Status
    status: ApplicationStatus = ApplicationStatus.PENDING
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None  # Screenshot after apply


# ─── Database Setup ───────────────────────────────────────────────────────────

from config import settings

engine = create_async_engine(settings.database_url, echo=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session():
    async with AsyncSession(engine) as session:
        yield session
