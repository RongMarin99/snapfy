import asyncio
import re
from playwright.async_api import async_playwright

async def scrape_netshort_full(url: str):
    print(f"Scraping NetShort drama: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded", timeout=25000)
        await page.wait_for_timeout(4000)

        # 1. Get Page Title
        title_text = await page.title()
        clean_title = title_text.replace("Online Watch - NetShort", "").replace("- NetShort", "").strip()
        print("Clean Drama Title:", clean_title)

        # 2. Extract cover image
        cover = ""
        og_img = await page.query_selector("meta[property='og:image']")
        if og_img:
            cover = await og_img.get_attribute("content") or ""

        # 3. Extract episode count from pagination tabs or DOM elements
        # Tabs often have text like "61-62" or "1-30" or "Full episodes"
        all_text = await page.inner_text("body")
        
        # Find highest episode number in text or links
        ep_numbers = re.findall(r'-ep-(\d+)', all_text)
        
        # Also check hrefs of all links
        links = await page.query_selector_all("a[href*='episode']")
        ep_urls = []
        max_ep = 1

        base_url = url.split("-ep-")[0].rstrip("/")

        for link in links:
            href = await link.get_attribute("href") or ""
            if href:
                m = re.search(r'-ep-(\d+)', href)
                if m:
                    num = int(m.group(1))
                    if num > max_ep:
                        max_ep = num

        # Also search for tab ranges like 61 - 62 or 1 - 30 in body text
        range_matches = re.findall(r'\b(\d+)\s*-\s*(\d+)\b', all_text)
        for r_start, r_end in range_matches:
            if int(r_end) > max_ep and int(r_end) < 300:
                max_ep = int(r_end)

        print(f"Discovered Total Episodes: {max_ep}")

        # Build list of all episode dictionaries (Ep 1 to Ep N)
        episodes = []
        for ep_i in range(1, max_ep + 1):
            if ep_i == 1:
                ep_url = base_url
            else:
                ep_url = f"{base_url}-ep-{ep_i}"

            episodes.append({
                "title": f"{clean_title} - EP {ep_i:02d}",
                "episode_num": ep_i,
                "url": ep_url,
                "thumbnail": cover,
                "platform": "NetShort",
                "status": "Waiting"
            })

        print(f"Successfully generated {len(episodes)} episodes!")
        print("Sample Ep 1:", episodes[0]["url"])
        print("Sample Ep 2:", episodes[1]["url"])
        print(f"Sample Ep {max_ep}:", episodes[-1]["url"])

        await browser.close()
        return episodes

asyncio.run(scrape_netshort_full("https://netshort.com/episode/the-daughter-they-buried-came-back-2074774809554599937"))
