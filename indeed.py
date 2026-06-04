"""
indeed.py — Indeed job search and apply automation.
"""
from playwright.async_api import TimeoutError as PwTimeout
from portals.base_portal import BasePortalAgent


class IndeedAgent(BasePortalAgent):

    portal_name = "indeed"
    BASE_URL = "https://www.indeed.com"

    async def login(self) -> bool:
        try:
            await self.page.goto(f"{self.BASE_URL}/account/login", wait_until="networkidle")
            await self.human_delay(1, 2)

            # Click "Continue with email"
            email_btn = await self.page.query_selector('button[data-tn-element="auth-page-google-sign-in-link"]')
            # Try direct email entry
            email_input = await self.page.query_selector('input[name="__email"]')
            if not email_input:
                email_input = await self.page.query_selector('input[type="email"]')

            if email_input:
                await email_input.fill(self.email)
                await self.safe_click('button[type="submit"]')
                await self.human_delay(1, 2)

                pwd_input = await self.page.query_selector('input[type="password"]')
                if pwd_input:
                    await self.safe_fill('input[type="password"]', self.password)
                    await self.safe_click('button[type="submit"]')
                    await self.page.wait_for_url("**/myjobs**", timeout=15000)
                    self.is_logged_in = True
                    self.log("Login successful")
                    return True

        except Exception as e:
            self.log(f"Login error: {e}", "error")

        return False

    async def search_jobs(self, keywords: list[str],
                          locations: list[str]) -> list[dict]:
        all_jobs = []
        for keyword in keywords[:3]:
            for location in locations[:3]:
                jobs = await self._search_one(keyword, location)
                all_jobs.extend(jobs)
                await self.human_delay(2, 4)

        # Deduplicate
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
            q = keyword.replace(" ", "+")
            l = location.replace(" ", "+")
            url = f"{self.BASE_URL}/jobs?q={q}&l={l}&sort=date&fromage=7"

            await self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await self.human_delay(2, 3)

            job_cards = await self.page.query_selector_all('[data-jk]')
            self.log(f"Found {len(job_cards)} cards for '{keyword}' in '{location}'")

            for card in job_cards[:20]:
                try:
                    jk = await card.get_attribute("data-jk")
                    title_el = await card.query_selector('h2.jobTitle span')
                    company_el = await card.query_selector('[data-testid="company-name"]')
                    loc_el = await card.query_selector('[data-testid="text-location"]')

                    title = await title_el.inner_text() if title_el else ""
                    company = await company_el.inner_text() if company_el else ""
                    loc = await loc_el.inner_text() if loc_el else location

                    if title and jk:
                        jobs.append({
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": loc.strip(),
                            "url": f"{self.BASE_URL}/viewjob?jk={jk}",
                            "description": "",
                            "portal": "indeed",
                            "job_key": jk
                        })
                except Exception:
                    continue

        except Exception as e:
            self.log(f"Search error: {e}", "warning")

        return jobs

    async def apply_to_job(self, job: dict, profile_data: dict) -> dict:
        """Apply to an Indeed job."""
        try:
            await self.page.goto(job["url"], wait_until="domcontentloaded", timeout=15000)
            await self.human_delay(1.5, 2.5)

            # Get description
            desc_el = await self.page.query_selector('#jobDescriptionText')
            if desc_el:
                job["description"] = await desc_el.inner_text()

            # Click Apply Now
            apply_btn = await self.page.query_selector(
                'button[id="indeedApplyButton"], a[id="applyButton"]'
            )
            if not apply_btn:
                return {"success": False, "error": "No apply button found"}

            await apply_btn.click()
            await self.human_delay(1, 2)

            # Handle Indeed's apply flow (may open new tab or modal)
            # Wait for resume upload step
            file_input = await self.page.query_selector('input[type="file"]')
            if file_input:
                await file_input.set_input_files(self.cv_path)
                await self.human_delay(1, 2)

            # Fill contact info if needed
            for field_id, key in [
                ('input[name="name.first"]', "name"),
                ('input[name="phoneNumber"]', "phone"),
            ]:
                el = await self.page.query_selector(field_id)
                if el:
                    val = profile_data.get(key, "")
                    if val:
                        await self.safe_fill(field_id, val.split()[0] if key == "name" else val)

            # Submit
            submit = await self.page.query_selector(
                'button[type="submit"][data-tn-element="submit-apply-button"]'
            )
            if submit:
                await submit.click()
                await self.human_delay(1.5, 2.5)
                screenshot = await self.take_screenshot(f"applied_{job['company']}")
                return {"success": True, "screenshot_path": screenshot}

            return {"success": False, "error": "Submit button not found"}

        except Exception as e:
            return {"success": False, "error": str(e)}
