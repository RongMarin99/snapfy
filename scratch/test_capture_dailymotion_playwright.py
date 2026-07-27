import sys
import os
sys.path.insert(0, os.path.abspath("."))

import asyncio
from playwright.async_api import async_playwright

async def capture_dailymotion():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        page = await ctx.new_page()

        captured_urls = []

        async def on_res(res):
            u = res.url
            if ".m3u8" in u or ".ts" in u or "video" in res.headers.get("content-type", ""):
                print(f"[CAPTURED STREAM] {res.status} | {res.headers.get('content-type', '')} | {u[:100]}")
                captured_urls.append(u)

        page.on("response", on_res)

        print("Navigating to Dailymotion video page...")
        await page.goto("https://www.dailymotion.com/video/xafttpi", wait_until="domcontentloaded")
        await page.wait_for_timeout(6000)

        await browser.close()

asyncio.run(capture_dailymotion())
