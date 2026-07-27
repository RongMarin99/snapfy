import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    url = "https://netshort.com/episode/the-daughter-they-buried-came-back-2074774809554599937"
    print(f"Inspecting detail_info/cascade_label API response payload...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        api_payloads = {}

        async def on_response(resp):
            u = resp.url
            if "detail_info" in u or "short_play" in u:
                try:
                    data = await resp.json()
                    api_payloads[u] = data
                    print("Captured API Payload from:", u)
                except Exception as e:
                    pass

        page.on("response", on_response)

        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(5000)

        with open("netshort_detail_api.json", "w", encoding="utf-8") as f:
            json.dump(api_payloads, f, indent=2, ensure_ascii=False)
        print("Saved API response to netshort_detail_api.json")

        await browser.close()

asyncio.run(main())
