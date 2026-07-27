import asyncio
from playwright.async_api import async_playwright

async def main():
    url = "https://netshort.com/episode/the-daughter-they-buried-came-back-2074774809554599937-ep-9"
    print("Launching Chromium headfully for NetShort login/cookie check...")
    async with async_playwright() as p:
        # Launch visible browser window
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        video_urls = []

        async def on_resp(resp):
            u = resp.url
            if ("cfcdn.netshort.com" in u or "video/mp4" in resp.headers.get("content-type", "")) and "lic" not in u:
                print("--- CAPTURED STREAM ---", u)
                video_urls.append(u)

        page.on("response", on_resp)

        await page.goto(url, wait_until="domcontentloaded")
        print("Navigated to episode 9 page. Waiting for user or page interaction...")
        await page.wait_for_timeout(10000)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
