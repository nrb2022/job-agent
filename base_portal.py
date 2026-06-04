"""
base_portal.py — Abstract base class for all job portal agents.
All portal-specific agents extend this class.
"""
import asyncio
import random
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, AsyncGenerator
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from config import settings


class BasePortalAgent(ABC):
    """
    Abstract job portal agent. Each portal (LinkedIn, Indeed, etc.)
    implements scrape_jobs() and apply_to_job().
    """

    portal_name: str = "base"

    def __init__(self, email: str, password: str, cv_path: str,
                 headless: bool = True):
        self.email = email
        self.password = password
        self.cv_path = cv_path
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in: bool = False
        self.log_entries: list[dict] = []

    # ─── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self):
        """Launch browser and create context."""
        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )
        self.context = await self.browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
        )
        self.page = await self.context.new_page()
        self.log(f"Browser started for {self.portal_name}")

    async def stop(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()
        if hasattr(self, "_playwright"):
            await self._playwright.stop()
        self.log(f"Browser closed for {self.portal_name}")

    # ─── Abstract Methods ──────────────────────────────────────────────────────

    @abstractmethod
    async def login(self) -> bool:
        """Log into the portal. Returns True on success."""
        ...

    @abstractmethod
    async def search_jobs(self, keywords: list[str],
                          locations: list[str]) -> list[dict]:
        """
        Search for jobs. Returns list of job dicts:
        {title, company, location, url, description, salary_range, job_type}
        """
        ...

    @abstractmethod
    async def apply_to_job(self, job: dict, profile_data: dict) -> dict:
        """
        Apply to a specific job. Returns:
        {success: bool, screenshot_path: str|None, error: str|None}
        """
        ...

    # ─── Helpers ───────────────────────────────────────────────────────────────

    async def human_delay(self, min_s: float = None, max_s: float = None):
        """Sleep a random amount to mimic human behaviour."""
        lo = min_s or settings.agent_delay_min
        hi = max_s or settings.agent_delay_max
        await asyncio.sleep(random.uniform(lo, hi))

    async def safe_click(self, selector: str, timeout: int = 10000):
        """Click element, wait for it to appear first."""
        await self.page.wait_for_selector(selector, timeout=timeout)
        await self.human_delay(0.3, 0.8)
        await self.page.click(selector)

    async def safe_fill(self, selector: str, text: str):
        """Fill input field with human-like typing speed."""
        await self.page.wait_for_selector(selector)
        await self.page.click(selector)
        await self.human_delay(0.2, 0.5)
        await self.page.fill(selector, "")
        # Type with small delays between chars
        for char in text:
            await self.page.type(selector, char, delay=random.randint(30, 120))

    async def take_screenshot(self, name: str) -> str:
        """Take a screenshot and return path."""
        path = f"/tmp/jobagent_{self.portal_name}_{name}_{int(datetime.utcnow().timestamp())}.png"
        await self.page.screenshot(path=path)
        return path

    def log(self, message: str, level: str = "info"):
        entry = {
            "ts": datetime.utcnow().isoformat(),
            "portal": self.portal_name,
            "level": level,
            "message": message
        }
        self.log_entries.append(entry)
        icon = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}.get(level, "•")
        print(f"{icon} [{self.portal_name}] {message}")

    async def run_full_pipeline(self, keywords: list[str],
                                 locations: list[str],
                                 profile_data: dict,
                                 max_applications: int = 10) -> dict:
        """
        Full pipeline: login → search → apply.
        Returns summary dict.
        """
        summary = {
            "portal": self.portal_name,
            "found": 0,
            "applied": 0,
            "failed": 0,
            "jobs": []
        }

        await self.start()
        try:
            if not await self.login():
                self.log(f"Login failed for {self.portal_name}", "error")
                return summary

            jobs = await self.search_jobs(keywords, locations)
            summary["found"] = len(jobs)
            self.log(f"Found {len(jobs)} jobs")

            applied_count = 0
            for job in jobs:
                if applied_count >= max_applications:
                    break

                self.log(f"Applying to: {job['title']} at {job['company']}")
                result = await self.apply_to_job(job, profile_data)

                if result["success"]:
                    summary["applied"] += 1
                    applied_count += 1
                    job["status"] = "applied"
                    self.log(f"Applied ✓ — {job['title']}", "success")
                else:
                    summary["failed"] += 1
                    job["status"] = "failed"
                    job["error"] = result.get("error", "Unknown error")
                    self.log(f"Failed: {result.get('error')}", "error")

                summary["jobs"].append(job)
                await self.human_delay(3, 8)  # Pause between applications

        finally:
            await self.stop()

        return summary
