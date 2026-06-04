"""
agent_runner.py — Orchestrates job application agents across multiple portals.
Sends real-time status via WebSocket callbacks.
"""
import asyncio
import json
from datetime import datetime
from typing import Callable, Optional, AsyncGenerator

from models import UserProfile, AgentSession, JobApplication, AgentStatus, ApplicationStatus
from job_matcher import filter_and_score_jobs
from config import settings

# Portal imports
from portals.linkedin import LinkedInAgent
from portals.indeed import IndeedAgent
from portals.naukri import NaukriAgent


PORTAL_CLASSES = {
    "linkedin": LinkedInAgent,
    "indeed": IndeedAgent,
    "naukri": NaukriAgent,
}

PORTAL_CREDENTIALS = {
    "linkedin": (settings.linkedin_email, settings.linkedin_password),
    "indeed": (settings.indeed_email, settings.indeed_password),
    "naukri": (settings.naukri_email, settings.naukri_password),
}


async def run_agent_session(
    profile: UserProfile,
    session_id: int,
    on_update: Optional[Callable] = None,
    min_match_score: int = 65,
    max_applications: int = None
) -> dict:
    """
    Main entry point for running the job application agent.

    Args:
        profile: UserProfile with CV data and preferences
        session_id: DB session ID for tracking
        on_update: Async callback for real-time WebSocket updates
        min_match_score: Minimum AI match score to apply (0-100)
        max_applications: Cap on total applications (overrides settings)
    """

    max_apps = max_applications or settings.max_applications_per_day

    async def emit(event: str, data: dict):
        if on_update:
            await on_update({"event": event, "data": data, "ts": datetime.utcnow().isoformat()})

    await emit("session_start", {"session_id": session_id, "portals": profile.portals})

    summary = {
        "session_id": session_id,
        "portals_run": [],
        "total_found": 0,
        "total_matched": 0,
        "total_applied": 0,
        "total_failed": 0,
        "applications": []
    }

    portals_to_run = [p for p in profile.portals if p in PORTAL_CLASSES]

    for portal_name in portals_to_run:
        AgentClass = PORTAL_CLASSES[portal_name]
        email, password = PORTAL_CREDENTIALS.get(portal_name, (None, None))

        if not email or not password:
            await emit("portal_skip", {
                "portal": portal_name,
                "reason": "No credentials configured"
            })
            continue

        await emit("portal_start", {"portal": portal_name})

        agent = AgentClass(
            email=email,
            password=password,
            cv_path=profile.cv_path,
            headless=settings.headless_browser
        )

        try:
            await agent.start()

            # Login
            if not await agent.login():
                await emit("portal_error", {
                    "portal": portal_name,
                    "error": "Login failed"
                })
                await agent.stop()
                continue

            await emit("portal_logged_in", {"portal": portal_name})

            # Search
            await emit("searching", {
                "portal": portal_name,
                "keywords": profile.target_titles,
                "locations": profile.preferred_locations
            })

            raw_jobs = await agent.search_jobs(
                keywords=profile.target_titles,
                locations=profile.preferred_locations
            )

            summary["total_found"] += len(raw_jobs)
            await emit("jobs_found", {"portal": portal_name, "count": len(raw_jobs)})

            # AI Matching
            await emit("matching", {"portal": portal_name, "jobs": len(raw_jobs)})

            matched_jobs = await filter_and_score_jobs(
                profile, raw_jobs, min_score=min_match_score
            )
            summary["total_matched"] += len(matched_jobs)

            await emit("jobs_matched", {
                "portal": portal_name,
                "matched": len(matched_jobs),
                "jobs": [
                    {
                        "title": j["title"],
                        "company": j["company"],
                        "location": j["location"],
                        "score": j["match_score"]
                    }
                    for j in matched_jobs[:10]
                ]
            })

            # Apply
            apps_this_portal = 0
            for job in matched_jobs:
                if apps_this_portal >= max_apps:
                    break
                if summary["total_applied"] >= max_apps:
                    break

                await emit("applying", {
                    "portal": portal_name,
                    "title": job["title"],
                    "company": job["company"],
                    "score": job["match_score"]
                })

                profile_data = {
                    "name": profile.name,
                    "email": profile.email,
                    "phone": profile.phone,
                    "summary": profile.summary,
                }

                result = await agent.apply_to_job(job, profile_data)

                app_record = {
                    "portal": portal_name,
                    "title": job["title"],
                    "company": job["company"],
                    "location": job["location"],
                    "url": job["url"],
                    "match_score": job["match_score"],
                    "match_reasons": job.get("match_reasons", []),
                    "status": "applied" if result["success"] else "failed",
                    "error": result.get("error"),
                    "screenshot_path": result.get("screenshot_path"),
                    "applied_at": datetime.utcnow().isoformat()
                }

                summary["applications"].append(app_record)

                if result["success"]:
                    summary["total_applied"] += 1
                    apps_this_portal += 1
                    await emit("applied", {
                        "portal": portal_name,
                        "title": job["title"],
                        "company": job["company"],
                        "score": job["match_score"]
                    })
                else:
                    summary["total_failed"] += 1
                    await emit("apply_failed", {
                        "portal": portal_name,
                        "title": job["title"],
                        "error": result.get("error", "")
                    })

                # Respectful delay between applications
                await asyncio.sleep(5)

        except Exception as e:
            await emit("portal_error", {"portal": portal_name, "error": str(e)})
        finally:
            await agent.stop()
            summary["portals_run"].append(portal_name)
            await emit("portal_done", {
                "portal": portal_name,
                "applied": apps_this_portal
            })

    await emit("session_complete", {
        "session_id": session_id,
        "total_found": summary["total_found"],
        "total_matched": summary["total_matched"],
        "total_applied": summary["total_applied"],
        "total_failed": summary["total_failed"],
    })

    return summary
