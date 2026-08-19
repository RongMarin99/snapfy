import asyncio
import re
import json
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

TEST_URL = "https://www.facebook.com/TheShadoowsOfficial/reels/"

async def test_httpx():
    print("--- TESTING HTTPX ---")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        res = await client.get(TEST_URL)
        print(f"Status: {res.status_code}, Length: {len(res.text)}")
        soup = BeautifulSoup(res.text, "html.parser")
        print("Title:", soup.title.string if soup.title else "No title")
        
        # Check for scripts containing video data or links
        scripts = soup.find_all("script")
        print(f"Found {len(scripts)} script tags")

async def test_playwright():
    print("--- TESTING PLAYWRIGHT ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US"
        )
        page = await context.new_page()
        
        # Log network requests for graphql or video streams
        captured_urls = []
        page.on("response", lambda r: captured_urls.append(r.url))
        
        print(f"Navigating to {TEST_URL}...")
        try:
            await page.goto(TEST_URL, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(5000)
            
            p_title = await page.title()
            print(f"Page Title: {p_title}")
            
            # Scroll down to load more content if any
            await page.evaluate("window.scrollBy(0, 1000)")
            await page.wait_for_timeout(3000)
            
            content = await page.content()
            print(f"Rendered Content Length: {len(content)}")
            
            # Find links to reels / videos
            links = await page.query_selector_all("a[href]")
            reel_links = set()
            for l in links:
                href = await l.get_attribute("href")
                if href and ("/reel/" in href or "/videos/" in href or "watch" in href):
                    reel_links.add(href)
            
            print(f"Found {len(reel_links)} video/reel links:")
            for link in list(reel_links)[:10]:
                print("  -", link)

        except Exception as e:
            print("Playwright error:", e)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_httpx())
    asyncio.run(test_playwright())
