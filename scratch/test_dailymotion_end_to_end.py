import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath("."))

from app.core.scraper import plugin_manager
from app.core.queue import queue_manager
from app.core.downloader import DownloadEngine
from app.database.models import init_db

async def test_dailymotion_pipeline():
    init_db()
    url = "https://dai.ly/xafttpi"

    print("--- 1. Testing Dailymotion Scraper ---")
    res = await plugin_manager.scrape(url)
    print("Detected Platform:", res["platform"])
    print("Title:", res["title"])
    print("Episodes found:", len(res["episodes"]))
    assert res["platform"] == "Dailymotion", "Platform should be Dailymotion!"
    print("[SUCCESS] Dailymotion Scraper OK!")

    print("\n--- 2. Testing Dailymotion Stream Resolver ---")
    stream_info = await plugin_manager.resolve(url)
    m3u8_url = stream_info["stream_url"]
    print("Resolved M3U8 Stream URL:", m3u8_url[:100] + "...")
    assert m3u8_url.startswith("http"), "M3U8 Stream URL should be a valid HTTP URL!"
    print("[SUCCESS] Dailymotion Stream Resolver OK!")

    print("\nDAILYMOTION INTEGRATION PASSED 100% PERFECTLY!")

asyncio.run(test_dailymotion_pipeline())
