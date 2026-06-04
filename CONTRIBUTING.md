# Contributing to JobAgent

Thank you for your interest in contributing! This is a community-driven project.

## Priority Contributions Needed

### 🔌 New Portal Adapters
The most impactful contributions are new job portal agents:
- **Wellfound** (AngelList) — startup jobs
- **Workday** — enterprise ATS (common at large companies)
- **Greenhouse** — widely used applicant tracking system
- **Lever** — common at tech startups
- **Internshala** — India internship platform

To add a portal, subclass `BasePortalAgent` in `backend/portals/`:
```python
from portals.base_portal import BasePortalAgent

class WellfoundAgent(BasePortalAgent):
    portal_name = "wellfound"
    BASE_URL = "https://wellfound.com"

    async def login(self) -> bool: ...
    async def search_jobs(self, keywords, locations) -> list[dict]: ...
    async def apply_to_job(self, job, profile_data) -> dict: ...
```

### 🧠 AI Enhancements
- **Cover letter generation** — per-job customised cover letters
- **CV tailoring** — rewrite CV bullets to match JD keywords
- **Salary negotiation hints** — analyse comp data from scraping
- **Interview prep** — generate likely questions based on JD

### 🧪 Testing
We need test coverage for:
- CV parser edge cases (scanned PDFs, unusual formats)
- Portal agent mock tests (using Playwright's `page.route()` for mocking)
- Job matcher scoring accuracy

## Development Setup

```bash
git clone https://github.com/yourusername/job-agent
cd job-agent/backend
pip install -r requirements.txt
pip install pytest pytest-asyncio
playwright install chromium
```

Run tests:
```bash
pytest tests/ -v
```

## Code Style
- Python: follow PEP 8, use type hints throughout
- Comments on non-obvious logic
- Each portal agent should be independently testable
- All async functions

## Pull Request Checklist
- [ ] New portal: login, search, apply all implemented
- [ ] Basic tests included
- [ ] `PORTALS` dict in `agent_runner.py` updated
- [ ] README portal table updated
- [ ] No hardcoded credentials

## Ethics Reminder
JobAgent is built with respect for job portals:
- Default delays mimic human speed (2-5s between actions)
- Rate limiting is configurable
- No bypassing of explicit bot detection systems
- Human Review Mode always available
