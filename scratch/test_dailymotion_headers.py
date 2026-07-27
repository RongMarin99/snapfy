import sys
import os
sys.path.insert(0, os.path.abspath("."))

import httpx
import asyncio
from app.plugins.dailymotion import DailymotionPlugin

async def test_headers():
    plugin = DailymotionPlugin()
    res = await plugin.resolve_stream("https://dai.ly/xafttpi")
    m3u8_url = res["stream_url"]

    print("Resolving stream URL:", m3u8_url)

    headers_options = [
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36", "Referer": "https://www.dailymotion.com/"},
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0", "Referer": "https://www.dailymotion.com/"},
        {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"}
    ]

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for idx, h in enumerate(headers_options, 1):
            r = await client.get(m3u8_url, headers=h)
            print(f"Option [{idx}] Status: {r.status_code} | Length: {len(r.text)} bytes")
            if r.status_code == 200:
                print("First 200 chars:\n", r.text[:200])
                break

asyncio.run(test_headers())
