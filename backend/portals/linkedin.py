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
            import json, os
            cookie_file = os.path.join(os.path.dirname(__file__), "..", "linkedin_cookies.json")
            if os.path.exists(cookie_file):
                cookies = json.loads(open(cookie_file).read())
                # Fix cookie domains, skip problematic ones
                clean = []
                for c in cookies:
                    if c['name'].startswith('__Host-'):
                        continue
                    clean.append({
                        'name': c['name'],
                        'value': c['value'],
                        'domain': '.linkedin.com',
                        'path': c.get('path', '/'),
                        'httpOnly': c.get('httpOnly', False),
                        'secure': c.get('secure', False),
                        'sameSite': c.get('sameSite', 'Lax') or 'Lax',
                    })
                await self.context.add_cookies(clean)
                await self.page.goto("https://www.linkedin.com/", wait_until="domcontentloaded", timeout=15000)
                await self.page.wait_for_timeout(2000)
                if "feed" in self.page.url or "mynetwork" in self.page.url or "linkedin.com" in self.page.url:
                    self.is_logged_in = True
                    self.log("Login successful via saved cookies")
                    return True
            self.log("Cookie login failed", "error")
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
                f"&sortBy=DD&f_LF=f_AL"   # Most recent
            )

            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.human_delay(2, 3)
            # Dismiss any auth popup
            try:
                close = await self.page.query_selector("button.contextual-sign-in-modal__modal-dismiss, [aria-label*='Dismiss'], [data-tracking-control-name*='dismiss']")
                if close: await close.click()
                await self.page.keyboard.press("Escape")
            except Exception: pass
            await self.human_delay(0.5, 1)

            # Wait for job list
            await self.page.wait_for_selector(".base-card", timeout=15000)

            # Scroll to load more results
            for _ in range(3):
                await self.page.evaluate("window.scrollBy(0, 800)")
                await self.human_delay(1, 2)

            # Extract job cards
            job_cards = await self.page.query_selector_all(".base-card")
            self.log(f"Found {len(job_cards)} job cards for '{keyword}' in '{location}'")

            for card in job_cards[:20]:  # Limit per search
                try:
                    title_el = await card.query_selector(".base-search-card__title")
                    company_el = await card.query_selector(".base-search-card__subtitle")
                    location_el = await card.query_selector(".job-search-card__location")
                    link_el = await card.query_selector("a.base-card__full-link")

                    title = await title_el.inner_text() if title_el else ""
                    company = await company_el.inner_text() if company_el else ""
                    loc = await location_el.inner_text() if location_el else location
                    href = await link_el.get_attribute("href") if link_el else ""

                    if title and href:
                        jobs.append({
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": loc.strip(),
                            "url": href.split("?")[0] if href.startswith("http") else f"{self.BASE_URL}{href.split(chr(63))[0]}",
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

    async def _dismiss_popups(self):
        try:
            close = await self.page.query_selector("button.modal__dismiss, button[aria-label='Dismiss']")
            if close:
                await close.click(timeout=3000)
                await self.human_delay(0.5, 1)
        except Exception:
            pass

    async def apply_to_job(self, job: dict, profile_data: dict) -> dict:
        """Apply using LinkedIn Easy Apply."""
        try:
            # Convert public URL to logged-in URL
            job_url = job["url"].replace("https://in.linkedin.com", "https://www.linkedin.com")
            await self.page.goto(job_url, wait_until="domcontentloaded", timeout=15000)
            await self.human_delay(1.5, 3)
            # Dismiss any popups with Escape key
            await self.page.keyboard.press("Escape")
            # Dismiss LinkedIn app notification
            try:
                notif = await self.page.query_selector(".artdeco-toast-item__dismiss, button[aria-label*='Dismiss']")
                if notif: await notif.click(timeout=2000)
            except Exception: pass
            await self.human_delay(0.5, 1)
            await self._dismiss_popups()

            # Get full description
            job["description"] = await self._get_job_description(job["url"])

            # Click Easy Apply button
            easy_apply_btn = await self.page.query_selector(
                'button.jobs-apply-button'
            )
            if not easy_apply_btn:
                return {"success": False, "error": "No Easy Apply button found"}

            await easy_apply_btn.click(timeout=5000)
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
