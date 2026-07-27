import asyncio
from playwright.async_api import async_playwright

async def resolve_netshort_stream(episode_url: str):
    print(f"Resolving stream for episode: {episode_url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        video_stream_url = ""

        async def on_response(response):
            nonlocal video_stream_url
            u = response.url
            ct = response.headers.get("content-type", "")
            if ("video" in ct or "video/mp4" in ct or ".mp4" in u or "cfcdn.netshort.com" in u) and not video_stream_url:
                print(f"[SUCCESSFUL STREAM INTERCEPT] -> {u[:120]}...")
                video_stream_url = u

        page.on("response", on_response)

        try:
            await page.goto(episode_url, wait_until="domcontentloaded", timeout=20000)
            
            # Click play if needed
            play_btn = await page.query_selector("video, svg, button[class*='play']")
            if play_btn:
                try:
                    await play_btn.click()
                except Exception:
                    pass

            await page.wait_for_timeout(4000)

            # Check DOM video tag if not captured via network
            if not video_stream_url:
                v_src = await page.evaluate('''() => {
                    const v = document.querySelector("video");
                    return v ? (v.src || v.currentSrc || "") : "";
                }''')
                if v_src:
                    video_stream_url = v_src
                    print("Found video src in DOM:", video_stream_url[:120])
        except Exception as e:
            print("Error resolving stream:", e)
        finally:
            await browser.close()

        return video_stream_url

async def main():
    s1 = await resolve_netshort_stream("https://netshort.com/episode/the-daughter-they-buried-came-back-2074774809554599937")
    s2 = await resolve_netshort_stream("https://netshort.com/episode/the-daughter-they-buried-came-back-2074774809554599937-ep-2")
    print("\nResult Episode 1 Stream:", "FOUND" if s1 else "MISSING")
    print("Result Episode 2 Stream:", "FOUND" if s2 else "MISSING")

asyncio.run(main())
