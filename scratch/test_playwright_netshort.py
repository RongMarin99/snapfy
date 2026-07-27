import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    url = "https://netshort.com/episode/the-daughter-they-buried-came-back-2074774809554599937"
    print("Launching Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        api_responses = []

        async def handle_response(response):
            r_url = response.url
            if "api" in r_url or "episode" in r_url or "detail" in r_url or "list" in r_url or ".json" in r_url or "m3u8" in r_url:
                print(f"[NETWORK RESPONSE] {response.status} -> {r_url}")
                try:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        body = await response.json()
                        api_responses.append({"url": r_url, "json": body})
                except Exception as e:
                    pass

        page.on("response", handle_response)

        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(5000)

        title = await page.title()
        print(f"Page Title: {title}")

        # Check DOM elements for episodes
        buttons = await page.query_selector_all("button, a, div[class*='episode'], div[class*='item']")
        print(f"Total clickable elements found: {len(buttons)}")

        with open("api_responses.json", "w", encoding="utf-8") as f:
            json.dump(api_responses, f, indent=2, ensure_ascii=False)
        print("Saved API responses to api_responses.json")

        await browser.close()

asyncio.run(main())
