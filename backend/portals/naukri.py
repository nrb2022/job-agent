"""
naukri.py — Naukri.com job search and apply automation.
"""
from playwright.async_api import TimeoutError as PwTimeout
from portals.base_portal import BasePortalAgent


class NaukriAgent(BasePortalAgent):

    portal_name = "naukri"
    BASE_URL = "https://www.naukri.com"

    async def login(self) -> bool:
        try:
            await self.page.goto("https://www.naukri.com/nlogin/login", wait_until="domcontentloaded", timeout=15000)
            await self.page.wait_for_timeout(2000)
            await self.page.fill("#usernameField", self.email)
            await self.page.wait_for_timeout(500)
            await self.page.fill("#passwordField", self.password)
            await self.page.wait_for_timeout(500)
            await self.page.keyboard.press("Enter")
            await self.page.wait_for_timeout(5000)
            if "naukri.com" in self.page.url and "login" not in self.page.url:
                self.is_logged_in = True
                self.log("Naukri login successful")
                return True
            self.log(f"Naukri login failed - URL: {self.page.url}", "error")
            return False
        except Exception as e:
            self.log(f"Naukri login error: {e}", "error")
            return False

    async def search_jobs(self, keywords: list[str],
                          locations: list[str]) -> list[dict]:
        all_jobs = []
        for keyword in keywords[:3]:
            for location in locations[:3]:
                jobs = await self._search_one(keyword, location)
                all_jobs.extend(jobs)
                await self.human_delay(2, 4)

        seen = set()
        unique = []
        for j in all_jobs:
            if j["url"] not in seen:
                seen.add(j["url"])
                unique.append(j)
        return unique

    async def _search_one(self, keyword: str, location: str) -> list[dict]:
        jobs = []
        try:
            kw = keyword.replace(" ", "-")
            loc = location.replace(" ", "-")
            url = f"{self.BASE_URL}/{kw}-jobs-in-{loc}?sort=1"

            await self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await self.human_delay(2, 3)

            job_cards = await self.page.query_selector_all('[data-job-id]')
            self.log(f"Found {len(job_cards)} jobs for '{keyword}' in '{location}'")

            for card in job_cards[:20]:
                try:
                    title_el = await card.query_selector('a.title')
                    company_el = await card.query_selector('a.comp-name')
                    exp_el = await card.query_selector('.expwdth')
                    loc_el = await card.query_selector('.location')
                    link_el = await card.query_selector('a.title')

                    title = await title_el.inner_text() if title_el else ""
                    company = await company_el.inner_text() if company_el else ""
                    loc_text = await loc_el.inner_text() if loc_el else location
                    href = await link_el.get_attribute("href") if link_el else ""

                    if title and href:
                        jobs.append({
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": loc_text.strip(),
                            "url": href,
                            "description": "",
                            "portal": "naukri"
                        })
                except Exception:
                    continue

        except Exception as e:
            self.log(f"Naukri search error: {e}", "warning")

        return jobs

    async def apply_to_job(self, job: dict, profile_data: dict) -> dict:
        """Apply to a Naukri job."""
        try:
            await self.page.goto(job["url"], wait_until="domcontentloaded", timeout=15000)
            await self.human_delay(1.5, 2.5)

            # Get description
            desc_el = await self.page.query_selector('.job-desc')
            if desc_el:
                job["description"] = await desc_el.inner_text()

            # Click Apply button
            apply_btn = await self.page.query_selector('button#apply-button, .apply-button')
            if not apply_btn:
                return {"success": False, "error": "No apply button found"}

            await apply_btn.click()
            await self.human_delay(1.5, 2.5)

            # Naukri apply modal
            # Check if CV upload required
            file_input = await self.page.query_selector('input[type="file"]')
            if file_input:
                await file_input.set_input_files(self.cv_path)
                await self.human_delay(1, 2)

            # Submit application
            # Check for screening questions
            questions = await self.page.query_selector_all('.question, input[type="radio"], textarea, select')
            if questions:
                self.log(f"Screening questions found: {len(questions)} - attempting to answer", "warning")
                for q in questions:
                    tag = await q.evaluate("el => el.tagName")
                    qtype = await q.get_attribute("type") or ""
                    if tag == "TEXTAREA":
                        val = await q.input_value()
                        if not val:
                            await q.fill("Experienced professional with 20+ years in software development and architecture.")
                    elif qtype == "radio":
                        await q.check()
                await self.human_delay(1, 2)
            submit_btn = await self.page.query_selector(
                'button.apply-btn, button[type="submit"]'
            )
            if submit_btn:
                await submit_btn.click()
                await self.human_delay(1.5, 2)
                screenshot = await self.take_screenshot(f"applied_{job['company']}")
                return {"success": True, "screenshot_path": screenshot}

            return {"success": False, "error": "Submit button not found"}

        except Exception as e:
            return {"success": False, "error": str(e)}
