import sys
import os
sys.path.insert(0, os.path.abspath("."))

import httpx
from app.plugins.dailymotion import DailymotionPlugin
import asyncio

async def inspect_m3u8():
    plugin = DailymotionPlugin()
    res = await plugin.resolve_stream("https://dai.ly/xafttpi")
    m3u8_url = res["stream_url"]

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        r = await client.get(m3u8_url, headers=res["headers"])
        print("MASTER PLAYLIST TEXT:\n")
        print(r.text)

asyncio.run(inspect_m3u8())
