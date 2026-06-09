import re

def is_location_match(job_location, preferred_locations):
    if not preferred_locations: return True
    job_loc_lower = job_location.lower()
    for pref in preferred_locations:
        if pref.lower() in job_loc_lower or job_loc_lower in pref.lower():
            return True
    aliases = {"bangalore": ["bengaluru", "blr"], "remote": ["work from home", "wfh"]}
    for key, vals in aliases.items():
        for pref in preferred_locations:
            if pref.lower() == key and any(v in job_loc_lower for v in vals):
                return True
    return False

def keyword_score(profile, job_title, job_description):
    score = 50  # base
    title_lower = job_title.lower()
    desc_lower = job_description.lower()

    # Title matches
    for target in profile.target_titles:
        for word in target.lower().split():
            if len(word) > 3 and word in title_lower:
                score += 10

    # Skill matches in description
    for skill in profile.skills[:20]:
        if skill.lower() in desc_lower:
            score += 3

    return min(score, 99)

async def filter_and_score_jobs(profile, jobs, min_score=60):
    results = []
    for job in jobs[:20]:  # Max 20 jobs
        if not is_location_match(job.get("location", ""), profile.preferred_locations):
            continue
        score = keyword_score(profile, job.get("title", ""), job.get("description", ""))
        if score >= min_score:
            results.append({
                **job,
                "match_score": score,
                "match_reasons": [f"Title match: {job.get('title')}"],
                "match_gaps": [],
                "fit_level": "strong" if score >= 80 else "moderate"
            })
    results.sort(key=lambda x: x["match_score"], reverse=True)
    print(f"[Matcher] {len(results)} jobs matched from {len(jobs[:20])} checked")
    return results
