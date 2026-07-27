import asyncio
import json
import sys
from playwright.async_api import async_playwright

async def main():
    url = "https://netshort.com/episode/the-daughter-they-buried-came-back-2074774809554599937"
    print("Launching Playwright Chromium...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        api_logs = []

        async def on_response(response):
            req_url = response.url
            if "netshort" in req_url and ("api" in req_url or "detail" in req_url or "query" in req_url or "play" in req_url or "short_play" in req_url):
                try:
                    text = await response.text()
                    api_logs.append({
                        "url": req_url,
                        "status": response.status,
                        "data": json.loads(text) if "json" in response.headers.get("content-type", "") else text[:500]
                    })
                    print(f"Captured API: {req_url}")
                except Exception as e:
                    pass

        page.on("response", on_response)

        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(6000)

        title = await page.title()
        print("PAGE TITLE:", title.encode('utf-8', errors='ignore').decode('utf-8'))

        with open("netshort_api_logs.json", "w", encoding="utf-8") as f:
            json.dump(api_logs, f, indent=2, ensure_ascii=False)
        print("Saved API logs to netshort_api_logs.json successfully!")

        # Evaluate episode DOM structure directly inside browser context
        episodes_info = await page.evaluate('''() => {
            const results = [];
            // Find episode items or buttons
            const items = document.querySelectorAll("a, button, div.ep-item, div[class*='episode']");
            items.forEach((el, idx) => {
                const text = el.innerText || "";
                const href = el.getAttribute("href") || "";
                if (text.length > 0 && text.length < 50) {
                    results.push({ idx, text: text.trim(), href });
                }
            });
            return results;
        }''')

        with open("netshort_dom_episodes.json", "w", encoding="utf-8") as f:
            json.dump(episodes_info, f, indent=2, ensure_ascii=False)
        print(f"Found {len(episodes_info)} DOM elements, saved to netshort_dom_episodes.json")

        await browser.close()

asyncio.run(main())
