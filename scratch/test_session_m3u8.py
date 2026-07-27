import sys
import os
sys.path.insert(0, os.path.abspath("."))

import httpx
import asyncio

async def test_session():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Referer": "https://www.dailymotion.com/"
    }

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
        # Step 1: Request video page or embed page to get session cookies
        r_init = await client.get("https://www.dailymotion.com/embed/video/xafttpi")
        print("Embed page cookies:", dict(client.cookies))

        # Step 2: Request player metadata
        meta_res = await client.get("https://www.dailymotion.com/player/metadata/video/xafttpi")
        print("Metadata Status:", meta_res.status_code)
        
        data = meta_res.json()
        qualities = data.get("qualities", {})
        m3u8_url = qualities["auto"][0]["url"]
        print("Stream URL:", m3u8_url[:80])

        # Step 3: Request m3u8 manifest using same client session
        m3u8_res = await client.get(m3u8_url)
        print("M3U8 Manifest Status:", m3u8_res.status_code)
        print("M3U8 Content Length:", len(m3u8_res.text))
        if m3u8_res.status_code == 200:
            print("First 300 chars of playlist:\n", m3u8_res.text[:300])

asyncio.run(test_session())
