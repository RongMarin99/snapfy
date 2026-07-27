import asyncio
from playwright.async_api import async_playwright

async def main():
    url = "https://netshort.com/episode/the-daughter-they-buried-came-back-2074774809554599937-ep-2"
    print(f"Testing stream resolution for {url}...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        media_urls = []

        async def on_response(resp):
            u = resp.url
            if ".m3u8" in u or ".mp4" in u or "awscover" in u or "vod" in u:
                print(f"[FOUND MEDIA RESPONSE] {resp.status} -> {u}")
                media_urls.append(u)

        page.on("response", on_response)

        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(5000)

        print("\nCaptured Media URLs:")
        for m in media_urls:
            print(" ->", m)

        await browser.close()

asyncio.run(main())
