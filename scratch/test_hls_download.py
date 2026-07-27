import sys
import os
sys.path.insert(0, os.path.abspath("."))

import re
import urllib.parse
import httpx
import asyncio
import time
from app.core.ffmpeg import ffmpeg_manager

async def test_hls():
    url = "https://dai.ly/xafttpi"
    from app.plugins.dailymotion import DailymotionPlugin
    plugin = DailymotionPlugin()
    res = await plugin.resolve_stream(url)
    m3u8_url = res["stream_url"]
    headers = res.get("headers", {})

    print("Fetching master playlist:", m3u8_url[:80])
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        r = await client.get(m3u8_url, headers=headers)
        playlist_text = r.text
        
        # Check if master playlist containing sub-playlists
        lines = [line.strip() for line in playlist_text.splitlines() if line.strip()]
        sub_playlists = [line for line in lines if line.endswith(".m3u8") or ".m3u8?" in line]
        
        target_playlist = m3u8_url
        if sub_playlists:
            last_sub = sub_playlists[-1]  # Highest resolution playlist is usually last
            target_playlist = urllib.parse.urljoin(m3u8_url, last_sub)
            print("Selected sub-playlist:", target_playlist[:80])
            r_sub = await client.get(target_playlist, headers=headers)
            playlist_text = r_sub.text

        # Extract all segment URLs
        seg_lines = [line.strip() for line in playlist_text.splitlines() if line.strip() and not line.startswith("#")]
        segments = [urllib.parse.urljoin(target_playlist, line) for line in seg_lines]
        print(f"Discovered {len(segments)} segments!")

        if not segments:
            print("No segments found!")
            return

        # Create temporary segment directory
        temp_dir = os.path.abspath("temp_hls_test")
        os.makedirs(temp_dir, exist_ok=True)

        print("Downloading segments...")
        sem = asyncio.Semaphore(6)
        downloaded = 0

        async def fetch_seg(idx, seg_url):
            nonlocal downloaded
            async with sem:
                seg_path = os.path.join(temp_dir, f"seg_{idx:05d}.ts")
                try:
                    res_seg = await client.get(seg_url, headers=headers)
                    if res_seg.status_code == 200:
                        with open(seg_path, "wb") as f:
                            f.write(res_seg.content)
                        downloaded += 1
                        if downloaded % 5 == 0 or downloaded == len(segments):
                            print(f"Downloaded {downloaded}/{len(segments)} segments ({(downloaded/len(segments))*100:.1f}%)")
                except Exception as e:
                    print(f"Error downloading seg {idx}: {e}")

        tasks = [fetch_seg(i, s) for i, s in enumerate(segments[:10])]  # Download first 10 for quick test
        await asyncio.gather(*tasks)

        print(f"Successfully downloaded sample segments to {temp_dir}!")

asyncio.run(test_hls())
