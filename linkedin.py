"""
linkedin.py — LinkedIn job search and Easy Apply automation.
"""
import json
import asyncio
from typing import Optional
from playwright.async_api import TimeoutError as PwTimeout

from portals.base_portal import BasePortalAgent


class LinkedInAgent(BasePortalAgent):

    portal_name = "linkedin"
    BASE_URL = "https://www.linkedin.com"

    async def login(self) -> bool:
        try:
            await self.page.goto(f"{self.BASE_URL}/login", wait_until="networkidle")
            await self.human_delay(1, 2)

            await self.safe_fill("#username", self.email)
            await self.safe_fill("#password", self.password)
            await self.safe_click('button[type="submit"]')

            # Wait for feed to confirm login
            await self.page.wait_for_url("**/feed/**", timeout=15000)
            self.is_logged_in = True
            self.log("Login successful")
            return True

        except PwTimeout:
            # Check for CAPTCHA or 2FA
            if "checkpoint" in self.page.url or "challenge" in self.page.url:
                self.log("LinkedIn requires CAPTCHA/2FA — manual intervention needed", "warning")
            else:
                self.log("Login timed out", "error")
            return False

        except Exception as e:
            self.log(f"Login error: {e}", "error")
            return False

    async def search_jobs(self, keywords: list[str],
                          locations: list[str]) -> list[dict]:
        all_jobs = []

        for keyword in keywords[:3]:        # Limit keywords
            for location in locations[:3]:  # Limit locations
                jobs = await self._search_one(keyword, location)
                all_jobs.extend(jobs)
                await self.human_delay(2, 4)

        # Deduplicate by URL
        seen = set()
        unique_jobs = []
        for job in all_jobs:
            if job["url"] not in seen:
                seen.add(job["url"])
                unique_jobs.append(job)

        self.log(f"Total unique jobs found: {len(unique_jobs)}")
        return unique_jobs

    async def _search_one(self, keyword: str, location: str) -> list[dict]:
        """Search LinkedIn Jobs for one keyword/location combo."""
        jobs = []
        try:
            # Build search URL with Easy Apply filter
            encoded_kw = keyword.replace(" ", "%20")
            encoded_loc = location.replace(" ", "%20")
            url = (
                f"{self.BASE_URL}/jobs/search/"
                f"?keywords={encoded_kw}&location={encoded_loc}"
                f"&f_LF=f_AL"   # Easy Apply filter
                f"&sortBy=DD"   # Most recent
            )

            await self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await self.human_delay(2, 3)

            # Wait for job list
            await self.page.wait_for_selector(".jobs-search__results-list", timeout=10000)

            # Scroll to load more results
            for _ in range(3):
                await self.page.evaluate("window.scrollBy(0, 800)")
                await self.human_delay(1, 2)

            # Extract job cards
            job_cards = await self.page.query_selector_all(".job-card-container")
            self.log(f"Found {len(job_cards)} job cards for '{keyword}' in '{location}'")

            for card in job_cards[:20]:  # Limit per search
                try:
                    title_el = await card.query_selector(".job-card-list__title")
                    company_el = await card.query_selector(".job-card-container__company-name")
                    location_el = await card.query_selector(".job-card-container__metadata-item")
                    link_el = await card.query_selector("a.job-card-list__title")

                    title = await title_el.inner_text() if title_el else ""
                    company = await company_el.inner_text() if company_el else ""
                    loc = await location_el.inner_text() if location_el else location
                    href = await link_el.get_attribute("href") if link_el else ""

                    if title and href:
                        jobs.append({
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": loc.strip(),
                            "url": f"{self.BASE_URL}{href.split('?')[0]}",
                            "description": "",
                            "portal": "linkedin",
                            "easy_apply": True
                        })
                except Exception:
                    continue

        except Exception as e:
            self.log(f"Search error for '{keyword}' / '{location}': {e}", "warning")

        return jobs

    async def _get_job_description(self, job_url: str) -> str:
        """Navigate to a job and extract description."""
        try:
            await self.page.goto(job_url, wait_until="domcontentloaded", timeout=15000)
            await self.human_delay(1, 2)
            desc_el = await self.page.query_selector(".jobs-description__content")
            if desc_el:
                return await desc_el.inner_text()
        except Exception:
            pass
        return ""

    async def apply_to_job(self, job: dict, profile_data: dict) -> dict:
        """Apply using LinkedIn Easy Apply."""
        try:
            await self.page.goto(job["url"], wait_until="domcontentloaded", timeout=15000)
            await self.human_delay(1.5, 3)

            # Get full description
            job["description"] = await self._get_job_description(job["url"])

            # Click Easy Apply button
            easy_apply_btn = await self.page.query_selector(
                'button.jobs-apply-button[aria-label*="Easy Apply"]'
            )
            if not easy_apply_btn:
                return {"success": False, "error": "No Easy Apply button found"}

            await easy_apply_btn.click()
            await self.human_delay(1, 2)

            # Handle multi-step Easy Apply modal
            max_steps = 8
            for step in range(max_steps):
                await self.human_delay(0.5, 1.5)

                # Fill any visible phone field
                phone_input = await self.page.query_selector('input[id*="phoneNumber"]')
                if phone_input:
                    val = await phone_input.input_value()
                    if not val:
                        await self.safe_fill('input[id*="phoneNumber"]',
                                             profile_data.get("phone", ""))

                # Upload CV if prompted
                file_input = await self.page.query_selector('input[type="file"]')
                if file_input:
                    await file_input.set_input_files(self.cv_path)
                    await self.human_delay(1, 2)

                # Check for Submit button (final step)
                submit_btn = await self.page.query_selector(
                    'button[aria-label="Submit application"]'
                )
                if submit_btn:
                    if settings.human_review_mode:
                        screenshot = await self.take_screenshot(f"review_{job['company']}")
                        return {
                            "success": False,
                            "error": "Human review required",
                            "screenshot_path": screenshot,
                            "review_needed": True
                        }
                    await submit_btn.click()
                    await self.human_delay(1, 2)
                    screenshot = await self.take_screenshot(f"applied_{job['company']}")
                    return {"success": True, "screenshot_path": screenshot}

                # Click Next/Continue
                next_btn = await self.page.query_selector(
                    'button[aria-label="Continue to next step"]'
                )
                if not next_btn:
                    next_btn = await self.page.query_selector(
                        'button[aria-label="Review your application"]'
                    )
                if next_btn:
                    await next_btn.click()
                else:
                    break  # No next, no submit — something unexpected

            return {"success": False, "error": "Could not complete Easy Apply flow"}

        except Exception as e:
            return {"success": False, "error": str(e)}
