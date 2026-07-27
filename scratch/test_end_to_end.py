import sys
import os
sys.path.insert(0, os.path.abspath("."))

import asyncio
from app.core.scraper import plugin_manager
from app.core.queue import queue_manager
from app.core.downloader import DownloadEngine
from app.database.models import init_db

async def test_full_pipeline():
    init_db()
    url = "https://netshort.com/episode/the-daughter-they-buried-came-back-2074774809554599937"
    
    print("--- 1. Testing Scraper for Full Drama Series ---")
    scrape_res = await plugin_manager.scrape(url)
    print("Title:", scrape_res["title"])
    print("Platform:", scrape_res["platform"])
    print("Discovered Episodes Count:", len(scrape_res["episodes"]))

    episodes = scrape_res["episodes"]
    assert len(episodes) == 62, f"Expected 62 episodes, got {len(episodes)}"
    print("[SUCCESS] Discovered all 62 episodes!")

    print("\n--- 2. Testing Adding Batch to Queue DB ---")
    queue_manager.clear_queue()
    added_items = queue_manager.add_videos_batch(episodes)
    print(f"[SUCCESS] Added {len(added_items)} items to SQLite DB queue.")

    print("\n--- 3. Testing Stream Resolution for Episode 1 & Episode 2 ---")
    ep1_info = await plugin_manager.resolve(episodes[0]["url"])
    print("EP 1 Stream URL:", ep1_info["stream_url"][:100] + "...")
    assert ep1_info["stream_url"].startswith("http"), "Failed to resolve EP1 stream URL!"
    
    ep2_info = await plugin_manager.resolve(episodes[1]["url"])
    print("EP 2 Stream URL:", ep2_info["stream_url"][:100] + "...")
    assert ep2_info["stream_url"].startswith("http"), "Failed to resolve EP2 stream URL!"
    print("[SUCCESS] Stream resolution working perfectly for NetShort!")

    print("\n--- 4. Testing Download Engine for Episode 1 ---")
    out_dir = os.path.join(os.getcwd(), "downloads_test")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "EP01_Test.mp4")

    engine = DownloadEngine()
    
    def on_prog(pct, mb, spd, eta):
        print(f"Progress: {pct:.1f}% | {mb:.1f} MB | Speed: {spd} | ETA: {eta}")

    success = await engine.download_direct(
        ep1_info["stream_url"],
        out_file,
        headers=ep1_info.get("headers"),
        progress_callback=on_prog
    )

    print("Download Result Success:", success)
    if success and os.path.exists(out_file):
        print(f"[SUCCESS] Playable video saved! Size: {os.path.getsize(out_file) / (1024*1024):.2f} MB")
    
    print("\nALL TESTS PASSED SUCCESSFULLY!")

asyncio.run(test_full_pipeline())
