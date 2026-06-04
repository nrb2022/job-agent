"""
job_matcher.py — Score job postings against a user profile using Claude AI.
"""
import json
import re
import anthropic
from typing import Optional

from config import settings
from models import UserProfile


client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


MATCH_SYSTEM_PROMPT = """You are an expert talent acquisition specialist.
Given a candidate profile and a job description, evaluate how well they match.
Return ONLY valid JSON with no markdown.

JSON schema:
{
  "score": 0-100,
  "recommendation": "apply" | "skip" | "review",
  "reasons": ["why this is a good match — list 2-4 points"],
  "gaps": ["missing skills or experience — list 0-3 points"],
  "tailoring_tips": ["quick tips to improve application — 1-2 points"],
  "estimated_fit_level": "strong" | "moderate" | "weak"
}

Scoring guide:
- 80-100: Strong match — recommend apply
- 60-79: Good match, minor gaps — recommend apply
- 40-59: Partial match, notable gaps — recommend review
- Below 40: Poor match — recommend skip"""


async def score_job_match(profile: UserProfile, job_title: str, company: str,
                          job_description: str, job_location: str) -> dict:
    """Score how well a job matches the candidate profile."""

    # Build a concise profile summary for the prompt
    profile_summary = f"""
Candidate: {profile.name}
Current Title: {profile.current_title}
Years Experience: {profile.years_experience}
Skills: {', '.join(profile.skills[:20])}
Summary: {profile.summary}
Target Titles: {', '.join(profile.target_titles)}
Preferred Locations: {', '.join(profile.preferred_locations)}
""".strip()

    job_text = f"""
Job Title: {job_title}
Company: {company}
Location: {job_location}
Description:
{job_description[:3000]}
""".strip()

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system=MATCH_SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"CANDIDATE PROFILE:\n{profile_summary}\n\nJOB POSTING:\n{job_text}"
            }
        ]
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    result = json.loads(raw)
    return result


def is_location_match(job_location: str, preferred_locations: list[str]) -> bool:
    """Check if job location matches any preferred location (fuzzy)."""
    if not preferred_locations:
        return True  # No preference = accept all

    job_loc_lower = job_location.lower()
    for pref in preferred_locations:
        if pref.lower() in job_loc_lower or job_loc_lower in pref.lower():
            return True
        # Handle abbreviations: "Bangalore" matches "Bengaluru", "BLR"
        aliases = {
            "bangalore": ["bengaluru", "blr"],
            "mumbai": ["bombay", "bom"],
            "delhi": ["new delhi", "ncr", "del"],
            "dubai": ["uae", "ae"],
            "remote": ["work from home", "wfh", "anywhere"],
        }
        for key, vals in aliases.items():
            if pref.lower() == key and any(v in job_loc_lower for v in vals):
                return True

    return False


async def filter_and_score_jobs(profile: UserProfile, jobs: list[dict],
                                 min_score: int = 60) -> list[dict]:
    """
    Filter jobs by location and score them. Returns sorted list of matches.
    """
    results = []
    for job in jobs:
        # Quick location filter before expensive AI call
        if not is_location_match(job.get("location", ""), profile.preferred_locations):
            continue

        try:
            match = await score_job_match(
                profile,
                job.get("title", ""),
                job.get("company", ""),
                job.get("description", ""),
                job.get("location", "")
            )
            score = match.get("score", 0)
            if score >= min_score and match.get("recommendation") != "skip":
                results.append({
                    **job,
                    "match_score": score,
                    "match_reasons": match.get("reasons", []),
                    "match_gaps": match.get("gaps", []),
                    "tailoring_tips": match.get("tailoring_tips", []),
                    "fit_level": match.get("estimated_fit_level", "moderate")
                })
        except Exception as e:
            print(f"[Matcher] Error scoring job {job.get('title')}: {e}")
            continue

    # Sort by score descending
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results
