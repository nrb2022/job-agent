"""
main.py — FastAPI application for JobAgent.
Endpoints: CV upload, preferences, agent control, WebSocket live status.
"""
import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import aiofiles

from config import settings
from models import init_db, UserProfile, AgentSession, JobApplication, AgentStatus
from cv_parser import process_cv_upload
from agent_runner import run_agent_session


# ─── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="JobAgent API",
    description="AI-powered job application automation",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory store (replace with Redis in production)
active_sessions: dict[int, dict] = {}
ws_connections: dict[int, List[WebSocket]] = {}


@app.on_event("startup")
async def startup():
    await init_db()
    print("✅ JobAgent API started")


# ─── Request/Response Models ─────────────────────────────────────────────────

class PreferencesRequest(BaseModel):
    profile_id: int
    target_titles: List[str]
    preferred_locations: List[str]
    portals: List[str]
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    currency: str = "INR"
    remote_ok: bool = True
    notice_period_days: Optional[int] = None
    min_match_score: int = 65
    max_applications_per_day: int = 10


class AgentStartRequest(BaseModel):
    profile_id: int
    min_match_score: int = 65
    max_applications: int = 10


# ─── CV Upload ────────────────────────────────────────────────────────────────

@app.post("/api/cv/upload")
async def upload_cv(file: UploadFile = File(...)):
    """Upload a CV (PDF or DOCX), parse it with Claude, return structured profile."""

    if not file.filename.endswith((".pdf", ".docx", ".doc")):
        raise HTTPException(400, "Only PDF and DOCX files are supported")

    # Save file
    filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = UPLOAD_DIR / filename

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    # Parse with Claude
    try:
        result = await process_cv_upload(str(file_path))
    except Exception as e:
        raise HTTPException(500, f"CV parsing failed: {str(e)}")

    parsed = result["parsed"]

    # Create user profile in DB
    from models import get_session
    from sqlmodel.ext.asyncio.session import AsyncSession

    profile = UserProfile(
        cv_filename=file.filename,
        cv_path=str(file_path),
        cv_text=result["cv_text"],
        name=parsed.get("name"),
        email=parsed.get("email"),
        phone=parsed.get("phone"),
        current_title=parsed.get("current_title"),
        years_experience=parsed.get("years_experience"),
        summary=parsed.get("summary"),
        skills_json=json.dumps(parsed.get("skills", [])),
        experience_json=json.dumps(parsed.get("experience", [])),
        education_json=json.dumps(parsed.get("education", [])),
        target_titles_json=json.dumps(parsed.get("inferred_target_titles", [])),
    )

    from sqlmodel import Session
    from models import engine
    from sqlalchemy.ext.asyncio import AsyncSession as ASession

    async with ASession(engine) as session:
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

    return {
        "profile_id": profile.id,
        "name": profile.name,
        "email": profile.email,
        "current_title": profile.current_title,
        "years_experience": profile.years_experience,
        "skills": json.loads(profile.skills_json),
        "summary": profile.summary,
        "inferred_target_titles": parsed.get("inferred_target_titles", []),
        "inferred_salary": parsed.get("inferred_salary_range", {}),
        "experience": parsed.get("experience", []),
        "education": parsed.get("education", []),
    }


# ─── Preferences ─────────────────────────────────────────────────────────────

@app.post("/api/preferences")
async def save_preferences(req: PreferencesRequest):
    """Save job search preferences for a profile."""
    from sqlalchemy.ext.asyncio import AsyncSession as ASession
    from models import engine
    from sqlmodel import select

    async with ASession(engine) as session:
        result = await session.execute(
            select(UserProfile).where(UserProfile.id == req.profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise HTTPException(404, "Profile not found")

        profile.target_titles_json = json.dumps(req.target_titles)
        profile.preferred_locations_json = json.dumps(req.preferred_locations)
        profile.portals_json = json.dumps(req.portals)
        profile.min_salary = req.min_salary
        profile.max_salary = req.max_salary
        profile.currency = req.currency
        profile.remote_ok = req.remote_ok
        profile.notice_period_days = req.notice_period_days
        profile.updated_at = datetime.utcnow()

        session.add(profile)
        await session.commit()

    return {"message": "Preferences saved", "profile_id": req.profile_id}


# ─── Agent Control ────────────────────────────────────────────────────────────

@app.post("/api/agent/start")
async def start_agent(req: AgentStartRequest):
    """Start the job application agent for a profile."""
    from sqlalchemy.ext.asyncio import AsyncSession as ASession
    from models import engine
    from sqlmodel import select

    async with ASession(engine) as session:
        result = await session.execute(
            select(UserProfile).where(UserProfile.id == req.profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise HTTPException(404, "Profile not found")

        if not profile.portals:
            raise HTTPException(400, "No portals selected in preferences")

        # Create agent session
        agent_session = AgentSession(
            profile_id=profile.id,
            status=AgentStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        session.add(agent_session)
        await session.commit()
        await session.refresh(agent_session)
        session_id = agent_session.id

    # Run agent in background
    asyncio.create_task(
        _run_agent_bg(profile, session_id, req.min_match_score, req.max_applications)
    )

    return {"session_id": session_id, "status": "started"}


async def _run_agent_bg(profile: UserProfile, session_id: int,
                        min_score: int, max_apps: int):
    """Background task for agent execution."""

    async def broadcast(msg: dict):
        """Broadcast to all WebSocket clients watching this session."""
        if session_id in ws_connections:
            dead = []
            for ws in ws_connections[session_id]:
                try:
                    await ws.send_json(msg)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                ws_connections[session_id].remove(ws)

    try:
        summary = await run_agent_session(
            profile=profile,
            session_id=session_id,
            on_update=broadcast,
            min_match_score=min_score,
            max_applications=max_apps
        )

        # Update session in DB
        from sqlalchemy.ext.asyncio import AsyncSession as ASession
        from models import engine
        from sqlmodel import select

        async with ASession(engine) as db:
            result = await db.execute(
                select(AgentSession).where(AgentSession.id == session_id)
            )
            sess = result.scalar_one_or_none()
            if sess:
                sess.status = AgentStatus.COMPLETED
                sess.completed_at = datetime.utcnow()
                sess.total_found = summary["total_found"]
                sess.total_matched = summary["total_matched"]
                sess.total_applied = summary["total_applied"]
                sess.total_failed = summary["total_failed"]
                db.add(sess)

            # Save applications
            for app_data in summary["applications"]:
                app = JobApplication(
                    session_id=session_id,
                    profile_id=profile.id,
                    portal=app_data["portal"],
                    job_title=app_data["title"],
                    company=app_data["company"],
                    location=app_data["location"],
                    job_url=app_data["url"],
                    match_score=app_data["match_score"],
                    match_reasons_json=json.dumps(app_data.get("match_reasons", [])),
                    status=(ApplicationStatus.APPLIED if app_data["status"] == "applied"
                            else ApplicationStatus.FAILED),
                    error_message=app_data.get("error"),
                    applied_at=(datetime.fromisoformat(app_data["applied_at"])
                                if app_data.get("applied_at") else None)
                )
                db.add(app)

            await db.commit()

    except Exception as e:
        print(f"[Agent BG Error] {e}")


@app.get("/api/agent/sessions/{profile_id}")
async def get_sessions(profile_id: int):
    """Get all agent sessions for a profile."""
    from sqlalchemy.ext.asyncio import AsyncSession as ASession
    from models import engine
    from sqlmodel import select

    async with ASession(engine) as session:
        result = await session.execute(
            select(AgentSession).where(AgentSession.profile_id == profile_id)
        )
        sessions = result.scalars().all()
        return [
            {
                "id": s.id,
                "status": s.status,
                "portal": s.portal,
                "total_found": s.total_found,
                "total_matched": s.total_matched,
                "total_applied": s.total_applied,
                "started_at": s.started_at,
                "completed_at": s.completed_at,
            }
            for s in sessions
        ]


@app.get("/api/applications/{profile_id}")
async def get_applications(profile_id: int, status: Optional[str] = None):
    """Get all job applications for a profile."""
    from sqlalchemy.ext.asyncio import AsyncSession as ASession
    from models import engine
    from sqlmodel import select

    async with ASession(engine) as session:
        query = select(JobApplication).where(JobApplication.profile_id == profile_id)
        if status:
            query = query.where(JobApplication.status == status)
        result = await session.execute(query.order_by(JobApplication.created_at.desc()))
        apps = result.scalars().all()
        return [
            {
                "id": a.id,
                "portal": a.portal,
                "title": a.job_title,
                "company": a.company,
                "location": a.location,
                "url": a.job_url,
                "match_score": a.match_score,
                "match_reasons": json.loads(a.match_reasons_json),
                "status": a.status,
                "error": a.error_message,
                "applied_at": a.applied_at,
            }
            for a in apps
        ]


# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: int):
    """Real-time agent status updates via WebSocket."""
    await websocket.accept()

    if session_id not in ws_connections:
        ws_connections[session_id] = []
    ws_connections[session_id].append(websocket)

    try:
        while True:
            await asyncio.sleep(30)  # Keep alive ping
            await websocket.send_json({"event": "ping"})
    except WebSocketDisconnect:
        ws_connections[session_id].remove(websocket)


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
