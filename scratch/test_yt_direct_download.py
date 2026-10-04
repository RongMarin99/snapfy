import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yt_dlp
from app.core.downloader import DownloadEngine

async def test_direct_mp4_download():
    video_url = "https://www.youtube.com/shorts/HtEhfvVWNr0"
    ydl_opts = {'quiet': True, 'no_warnings': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        formats = info.get("formats", [])
        
        # Filter direct HTTPS video formats (non-m3u8, vcodec != none)
        direct_videos = [
            f for f in formats 
            if f.get("protocol") in ("http", "https") 
            and not (f.get("url") or "").endswith(".m3u8")
            and f.get("vcodec") != "none"
            and f.get("ext") == "mp4"
        ]
        
        if not direct_videos:
            print("No direct MP4 video formats found!")
            return

        # Pick best resolution (e.g. 720p or 1080p)
        best_v = max(direct_videos, key=lambda x: x.get("height") or 0)
        print(f"Selected Best Direct Video Format: ID {best_v.get('format_id')}, Res: {best_v.get('height')}p")
        print("Direct Stream URL:", best_v.get("url")[:100])

        engine = DownloadEngine()
        out_path = "downloads_test/direct_short_video.mp4"
        
        def on_prog(pct, mb, spd, eta):
            print(f"Progress: {pct:.1f}% | Size: {mb:.2f} MB | Speed: {spd} | ETA: {eta}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.youtube.com/"
        }
        
        print("\nDownloading direct video file...")
        success = await engine.download_direct(best_v.get("url"), out_path, headers=headers, progress_callback=on_prog)
        print("Download Result Success:", success)
        if success and os.path.exists(out_path):
            file_size_mb = os.path.getsize(out_path) / (1024 * 1024)
            print(f"Final downloaded file size: {file_size_mb:.2f} MB")

if __name__ == "__main__":
    asyncio.run(test_direct_mp4_download())
