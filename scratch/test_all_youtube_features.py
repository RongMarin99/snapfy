import asyncio
import os
import sys

# Ensure app package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.scraper import plugin_manager
from app.plugins.youtube import YouTubePlugin

async def test_youtube_integration():
    print("=== TEST 1: Plugin Detection ===")
    yt_url = "https://www.youtube.com/@Google"
    plugin = plugin_manager.detect_plugin(yt_url)
    print("Detected plugin:", plugin.name, "Key:", plugin.platform_key)
    assert plugin.platform_key == "YouTube", f"Expected YouTube, got {plugin.platform_key}"

    print("\n=== TEST 2: Scrape YouTube Shorts Profile ===")
    shorts_url = "https://www.youtube.com/@Google/shorts"
    res_shorts = await plugin_manager.scrape(shorts_url)
    print("Channel Title:", res_shorts["title"].encode("ascii", "ignore").decode("ascii"))
    print("Found Shorts Count:", len(res_shorts["episodes"]))
    assert len(res_shorts["episodes"]) > 0, "No shorts found!"

    first_short = res_shorts["episodes"][0]
    print("Sample Short Title:", first_short["title"].encode("ascii", "ignore").decode("ascii"))
    print("Sample Short URL:", first_short["url"])

    print("\n=== TEST 3: Scrape YouTube Videos Profile ===")
    videos_url = "https://www.youtube.com/@Google/videos"
    res_videos = await plugin_manager.scrape(videos_url)
    print("Channel Title:", res_videos["title"].encode("ascii", "ignore").decode("ascii"))
    print("Found Videos Count:", len(res_videos["episodes"]))
    assert len(res_videos["episodes"]) > 0, "No videos found!"

    first_video = res_videos["episodes"][0]
    print("Sample Video Title:", first_video["title"].encode("ascii", "ignore").decode("ascii"))
    print("Sample Video URL:", first_video["url"])

    print("\n=== TEST 4: Resolve Stream ===")
    resolved = await plugin_manager.resolve(first_video["url"])
    print("Resolved Media Type:", resolved["media_type"])
    print("Stream URL Available:", bool(resolved["stream_url"]))
    assert resolved["stream_url"], "Failed to resolve stream URL!"

    print("\n=== ALL TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(test_youtube_integration())
