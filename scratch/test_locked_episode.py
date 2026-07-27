import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    url = "https://netshort.com/episode/the-daughter-they-buried-came-back-2074774809554599937-ep-9"
    print(f"Testing locked episode stream resolution for {url}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        captured_requests = []

        async def on_response(response):
            u = response.url
            ct = response.headers.get("content-type", "")
            if any(k in u for k in ["api", "short_play", "detail", "video", "mp4", "m3u8", "volc", "bytedance", "cfcdn"]):
                print(f"[RESPONSE] {response.status} ({ct}) -> {u[:120]}")
                captured_requests.append({"url": u, "status": response.status, "content_type": ct})

        page.on("response", on_response)

        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(5000)

        # Print video tag sources in DOM
        v_sources = await page.evaluate('''() => {
            const srcs = [];
            document.querySelectorAll("video, source").forEach(v => {
                if (v.src) srcs.push(v.src);
                if (v.currentSrc) srcs.push(v.currentSrc);
            });
            return srcs;
        }''')
        print("DOM Video sources:", v_sources)

        # Check if there is an iframe, modal, unlock button or next episode player
        page_html = await page.content()
        with open("locked_ep_9.html", "w", encoding="utf-8") as f:
            f.write(page_html)

        await browser.close()

asyncio.run(main())
