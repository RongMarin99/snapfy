import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.plugins.youtube import YouTubePlugin
from app.core.downloader import DownloadEngine

async def debug_short():
    plugin = YouTubePlugin()
    video_url = "https://www.youtube.com/shorts/G22BVF0U-XA"
    
    print("1. Resolving stream for short...")
    res = await plugin.resolve_stream(video_url)
    print("Media type:", res["media_type"])
    print("Stream URL:", res["stream_url"])
    print("Headers:", res["headers"])
    
    print("\n2. Attempting HLS download...")
    engine = DownloadEngine()
    out_file = "downloads_test/debug_short_out.mp4"
    
    def on_prog(pct, mb, spd, eta):
        print(f"Prog: {pct:.1f}% | Size: {mb:.2f}MB | Speed: {spd} | ETA: {eta}")

    success = await engine.download_hls(
        res["stream_url"],
        out_file,
        headers=res["headers"],
        progress_callback=on_prog
    )
    print("Download result success:", success)

if __name__ == "__main__":
    asyncio.run(debug_short())
