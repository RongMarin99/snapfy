import asyncio
import json
import re
from playwright.async_api import async_playwright

URL = "https://www.facebook.com/reel/1400619097782161"

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US"
        )
        page = await context.new_page()

        print(f"Navigating to {URL}...")
        try:
            await page.goto(URL, wait_until="networkidle", timeout=25000)
            await page.wait_for_timeout(3000)

            content = await page.content()
            print(f"Rendered HTML length: {len(content)}")

            with open("scratch/fb_page.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("Saved html to scratch/fb_page.html")

            # Search for all occurrences of audio, audio_representation, representations, etc.
            matches = re.findall(r'"audio[^\s"]*"\s*:\s*(\{[^}]+\}|"https?:[^"]+")', content)
            print(f"Audio matches: {len(matches)}")
            for m in matches[:5]:
                print("  Audio sample:", str(m)[:100])

            # Search for dash_manifest or representation or base_url
            for term in ["dash_manifest", "base_url", "representation", "audio_quality", "mime_type", "codecs"]:
                found = re.findall(rf'"{term}"\s*:\s*("[^"]+"|\d+|\[[^\]]+\]|\{{[^}}]+\}})', content)
                print(f"Term '{term}': {len(found)} occurrences")
                for item in found[:3]:
                    print(f"   sample: {str(item)[:100]}")

        except Exception as e:
            print("Playwright error:", e)
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
