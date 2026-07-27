import asyncio
from playwright.async_api import async_playwright

async def main():
    url = "https://netshort.com/episode/the-daughter-they-buried-came-back-2074774809554599937-ep-2"
    print(f"Intercepting all media & XHR network requests for {url}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        all_requests = []

        async def on_response(response):
            u = response.url
            ct = response.headers.get("content-type", "")
            # Intercept video, m3u8, mp4, volccdn, or json responses
            if any(k in u for k in [".m3u8", ".mp4", "volc", "bytedance", "video", "play", "detail"]):
                print(f"[MEDIA/API] {response.status} ({ct}) -> {u}")
                all_requests.append({"url": u, "status": response.status, "content_type": ct})

        page.on("response", on_response)

        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        
        # Click play button if present
        try:
            play_btn = await page.query_selector("video, svg, button[class*='play']")
            if play_btn:
                await play_btn.click()
                print("Clicked play button on page!")
        except Exception:
            pass

        await page.wait_for_timeout(8000)

        # Evaluate html <video> src or <source> src
        video_sources = await page.evaluate('''() => {
            const srcs = [];
            document.querySelectorAll("video, source").forEach(el => {
                if (el.src) srcs.push(el.src);
                if (el.currentSrc) srcs.push(el.currentSrc);
            });
            return srcs;
        }''')
        print("DOM <video> sources found:", video_sources)

        await browser.close()

asyncio.run(main())
