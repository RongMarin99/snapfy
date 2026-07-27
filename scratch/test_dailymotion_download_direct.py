import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath("."))

from app.core.scraper import plugin_manager
from app.core.downloader import DownloadEngine
from app.database.models import init_db

async def test_dailymotion_full_download():
    init_db()
    url = "https://dai.ly/xafttpi"

    print("Scraping Dailymotion video info...")
    scrape_res = await plugin_manager.scrape(url)
    print("Title:", scrape_res["title"])
    print("Platform:", scrape_res["platform"])

    print("Resolving stream URL...")
    stream_info = await plugin_manager.resolve(url)
    m3u8_url = stream_info["stream_url"]
    print("M3U8 Stream URL:", m3u8_url[:120] + "...")

    out_file = os.path.join(os.getcwd(), "Dailymotion_Test_Output.mp4")
    print(f"Downloading stream to {out_file}...")

    engine = DownloadEngine()
    
    def on_prog(pct, mb, spd, eta):
        print(f"Progress: {pct:.1f}% | {mb:.1f} MB | Speed: {spd} | ETA: {eta}")

    success = await engine.download_hls(
        m3u8_url,
        out_file,
        headers=stream_info.get("headers"),
        progress_callback=on_prog
    )

    print("Download Success:", success)
    if success and os.path.exists(out_file):
        print(f"[SUCCESS] Downloaded Dailymotion video file! Size: {os.path.getsize(out_file) / (1024*1024):.2f} MB")

asyncio.run(test_dailymotion_full_download())
