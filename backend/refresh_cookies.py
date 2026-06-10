"""
Run this script to refresh LinkedIn/Naukri cookies before running the agent.
Usage: python3 refresh_cookies.py linkedin
       python3 refresh_cookies.py naukri
       python3 refresh_cookies.py all
"""
import asyncio, json, sys
from playwright.async_api import async_playwright

async def save_cookies(portal):
    urls = {
        'linkedin': 'https://www.linkedin.com/login',
        'naukri': 'https://www.naukri.com/nlogin/login',
        'indeed': 'https://www.indeed.com/account/login'
    }
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(urls[portal])
        print(f'Log in to {portal.title()} manually, then press Enter...')
        input()
        cookies = await browser.contexts[0].cookies()
        open(f'{portal}_cookies.json','w').write(json.dumps(cookies))
        print(f'Saved {len(cookies)} {portal} cookies')
        await browser.close()

portals = sys.argv[1:] if len(sys.argv) > 1 else ['linkedin', 'naukri']
if portals == ['all']:
    portals = ['linkedin', 'naukri', 'indeed']

for portal in portals:
    asyncio.run(save_cookies(portal))
