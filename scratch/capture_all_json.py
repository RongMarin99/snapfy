import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    url = "https://netshort.com/episode/the-daughter-they-buried-came-back-2074774809554599937"
    print(f"Capturing all JSON responses from {url}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        all_json = []

        async def on_response(resp):
            u = resp.url
            ct = resp.headers.get("content-type", "")
            if "json" in ct or "netshort.com/prod-web-api" in u:
                try:
                    body = await resp.json()
                    all_json.append({"url": u, "data": body})
                    print("Captured JSON from:", u)
                except Exception:
                    pass

        page.on("response", on_response)

        await page.goto(url, wait_until="networkidle", timeout=30000)

        with open("all_json_responses.json", "w", encoding="utf-8") as f:
            json.dump(all_json, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(all_json)} JSON responses to all_json_responses.json")

        await browser.close()

asyncio.run(main())
