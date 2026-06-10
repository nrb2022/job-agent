"""
indeed.py — Indeed job search and apply automation.
Uses saved cookies for login (same pattern as LinkedIn).
"""
import json
import os
from playwright.async_api import TimeoutError as PwTimeout
from portals.base_portal import BasePortalAgent
from config import settings


class IndeedAgent(BasePortalAgent):

    portal_name = "indeed"
    BASE_URL = "https://in.indeed.com"

    async def login(self) -> bool:
        try:
            cookie_file = os.path.join(os.path.dirname(__file__), "..", "indeed_cookies.json")
            if os.path.exists(cookie_file):
                cookies = json.loads(open(cookie_file).read())
                clean = []
                for c in cookies:
                    if c["name"].startswith("__Host-"):
                        continue
                    clean.append({
                        "name": c["name"],
                        "value": c["value"],
                        "domain": ".indeed.com",
                        "path": c.get("path", "/"),
                        "httpOnly": c.get("httpOnly", False),
                        "secure": c.get("secure", False),
                        "sameSite": c.get("sameSite", "Lax") or "Lax",
                    })
                await self.context.add_cookies(clean)
                await self.page.goto("https://in.indeed.com/", wait_until="domcontentloaded", timeout=15000)
                await self.page.wait_for_timeout(2000)
                self.is_logged_in = True
                self.log("Login via cookies (or unauthenticated scraping)")
                return True
            self.log("No Indeed cookies — scraping without login", "warning")
            self.is_logged_in = True
            return True
        except Exception as e:
            self.log(f"Login error: {e}", "error")
            return False

    async def search_jobs(self, keywords: list[str], locations: list[str]) -> list[dict]:
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
            q = keyword.replace(" ", "+")
            l = location.replace(" ", "+")
            url = f"{self.BASE_URL}/jobs?q={q}&l={l}&sort=date&fromage=14"
            await self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await self.human_delay(2, 3)
            try:
                await self.page.keyboard.press("Escape")
            except Exception:
                pass
            job_cards = await self.page.query_selector_all("[data-jk], .job_seen_beacon, .tapItem")
            self.log(f"Found {len(job_cards)} cards for '{keyword}' in '{location}'")
            for card in job_cards[:20]:
                try:
                    jk = await card.get_attribute("data-jk")
                    if not jk:
                        link = await card.query_selector("a[data-jk]")
                        if link:
                            jk = await link.get_attribute("data-jk")
                    title_el = await card.query_selector("h2.jobTitle a span, h2[class*=jobTitle] span, .jobTitle span")
                    company_el = await card.query_selector("[data-testid=company-name], .companyName")
                    loc_el = await card.query_selector("[data-testid=text-location], .companyLocation")
                    title = await title_el.inner_text() if title_el else ""
                    company = await company_el.inner_text() if company_el else ""
                    loc = await loc_el.inner_text() if loc_el else location
                    if title and jk:
                        jobs.append({
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": loc.strip(),
                            "url": f"https://in.indeed.com/viewjob?jk={jk}",
                            "description": "",
                            "portal": "indeed",
                            "job_key": jk
                        })
                except Exception:
                    continue
        except Exception as e:
            self.log(f"Search error for '{keyword}' / '{location}': {e}", "warning")
        return jobs

    async def apply_to_job(self, job: dict, profile_data: dict) -> dict:
        try:
            await self.page.goto(job["url"], wait_until="domcontentloaded", timeout=15000)
            await self.human_delay(1.5, 2.5)
            desc_el = await self.page.query_selector("#jobDescriptionText, [id*=jobDescription]")
            if desc_el:
                job["description"] = await desc_el.inner_text()
            apply_btn = await self.page.query_selector(
                "button[id=indeedApplyButton], a[id=applyButton], "
                "[data-testid=IndeedApplyButton], button[class*=apply-button]"
            )
            if not apply_btn:
                return {"success": False, "error": "No apply button found"}
            href = await apply_btn.get_attribute("href") or ""
            if href and "indeed.com" not in href and "indeedapply" not in href.lower():
                return {"success": False, "error": "External application — manual apply required"}
            await apply_btn.click()
            await self.human_delay(1.5, 2.5)
            for step in range(6):
                await self.human_delay(1, 2)
                file_input = await self.page.query_selector("input[type=file]")
                if file_input:
                    await file_input.set_input_files(self.cv_path)
                    await self.human_delay(1, 2)
                for selector in ["input[name=phoneNumber]", "input[id*=phone]", "input[type=tel]"]:
                    el = await self.page.query_selector(selector)
                    if el:
                        val = await el.input_value()
                        if not val:
                            await self.safe_fill(selector, profile_data.get("phone", ""))
                        break
                submit = await self.page.query_selector(
                    "button[type=submit][data-tn-element=submit-apply-button], "
                    "button[data-testid=ia-continueButton][aria-label*=Submit], "
                    "button[class*=ia-Submit]"
                )
                if submit:
                    if settings.human_review_mode:
                        screenshot = await self.take_screenshot(f"review_{job['company']}")
                        return {"success": False, "error": "Human review required",
                                "screenshot_path": screenshot, "review_needed": True}
                    await submit.click()
                    await self.human_delay(1.5, 2)
                    screenshot = await self.take_screenshot(f"applied_{job['company']}")
                    return {"success": True, "screenshot_path": screenshot}
                next_btn = await self.page.query_selector(
                    "button[data-testid=ia-continueButton], "
                    "button[class*=ia-Continue], button[type=button][class*=continue]"
                )
                if next_btn:
                    await next_btn.click()
                else:
                    break
            return {"success": False, "error": "Could not complete apply flow"}
        except Exception as e:
            return {"success": False, "error": str(e)}
