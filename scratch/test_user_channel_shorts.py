import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.scraper import plugin_manager
from app.core.downloader import DownloadEngine

async def test_user_channel():
    url = "https://www.youtube.com/@diazconstruccion5053/shorts"
    print(f"1. Scraping channel shorts: {url}")
    
    scrape_res = await plugin_manager.scrape(url)
    title = scrape_res.get("title")
    episodes = scrape_res.get("episodes", [])
    
    print(f"Channel Title: {title.encode('ascii', 'ignore').decode('ascii')}")
    print(f"Total Shorts Discovered: {len(episodes)}")
    
    if not episodes:
        print("ERROR: No episodes found!")
        return

    for idx, ep in enumerate(episodes[:5], 1):
        safe_t = ep['title'].encode('ascii', 'ignore').decode('ascii')
        print(f"  #{idx}: {safe_t} -> {ep['url']}")

    # Pick the first short to test full download
    target_short = episodes[0]
    print(f"\n2. Resolving stream for short: {target_short['url']}")
    stream_info = await plugin_manager.resolve(target_short["url"])
    
    print("Media type:", stream_info.get("media_type"))
    print("Stream URL sample:", stream_info.get("stream_url")[:100])
    
    # Execute actual download
    print("\n3. Downloading video file...")
    engine = DownloadEngine()
    out_dir = "downloads_test"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "diaz_short_test.mp4")

    if os.path.exists(out_file):
        os.remove(out_file)

    start_t = time.time()

    def on_prog(pct, mb, spd, eta):
        print(f"  Progress: {pct:.1f}% | Size: {mb:.2f} MB | Speed: {spd} | ETA: {eta}")

    success = False
    if stream_info.get("media_type") == "hls":
        success = await engine.download_hls(
            stream_info.get("stream_url"), out_file, headers=stream_info.get("headers"), progress_callback=on_prog
        )
    else:
        success = await engine.download_direct(
            stream_info.get("stream_url"), out_file, headers=stream_info.get("headers"), progress_callback=on_prog
        )

    dur = time.time() - start_t
    print(f"\nDownload success: {success}")
    if success and os.path.exists(out_file):
        final_size_mb = os.path.getsize(out_file) / (1024 * 1024)
        print(f"Final downloaded file size: {final_size_mb:.2f} MB")
        print(f"Total download time: {dur:.2f} seconds")
        print("TEST PASSED 100% PERFECTLY!")

if __name__ == "__main__":
    asyncio.run(test_user_channel())
