import sys
import os
sys.path.insert(0, os.path.abspath("."))

import re
import urllib.parse
import httpx
import asyncio
from app.plugins.dailymotion import DailymotionPlugin

async def download_hls_python(m3u8_url: str, output_mp4: str, headers: dict = None):
    headers = headers or {}
    headers.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    headers.setdefault("Referer", "https://www.dailymotion.com/")

    os.makedirs(os.path.dirname(os.path.abspath(output_mp4)), exist_ok=True)

    print("Fetching HLS manifest:", m3u8_url[:80])
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        r = await client.get(m3u8_url, headers=headers)
        if r.status_code != 200 or not r.text.strip():
            print(f"Failed to fetch manifest. Status: {r.status_code}")
            return False

        playlist_text = r.text
        lines = [line.strip() for line in playlist_text.splitlines() if line.strip()]

        # Parse master playlist vs media playlist
        sub_playlists = [line for line in lines if not line.startswith("#") and (".m3u8" in line or "manifest" in line)]
        target_playlist = m3u8_url

        if sub_playlists:
            last_sub = sub_playlists[-1]
            target_playlist = urllib.parse.urljoin(m3u8_url, last_sub)
            print("Selected media playlist:", target_playlist[:80])
            r_sub = await client.get(target_playlist, headers=headers)
            playlist_text = r_sub.text

        # Extract media segments (.ts / .mp4 / .m4s / chunk URLs)
        seg_lines = [line.strip() for line in playlist_text.splitlines() if line.strip() and not line.startswith("#")]
        segments = [urllib.parse.urljoin(target_playlist, line) for line in seg_lines]
        print(f"Found {len(segments)} video segments!")

        if not segments:
            print("No video segments found in playlist!")
            return False

        # Download segments into memory / stream to output_mp4 directly!
        sem = asyncio.Semaphore(5)
        downloaded_count = 0
        total_count = len(segments)

        with open(output_mp4, "wb") as outfile:
            for idx, seg_url in enumerate(segments, 1):
                try:
                    res_seg = await client.get(seg_url, headers=headers)
                    if res_seg.status_code == 200:
                        outfile.write(res_seg.content)
                        downloaded_count += 1
                        if downloaded_count % 10 == 0 or downloaded_count == total_count:
                            pct = (downloaded_count / total_count) * 100.0
                            size_mb = os.path.getsize(output_mp4) / (1024 * 1024)
                            print(f"Downloaded {downloaded_count}/{total_count} segments ({pct:.1f}%) | Size: {size_mb:.1f} MB")
                except Exception as e:
                    print(f"Error downloading segment {idx}: {e}")

        final_size = os.path.getsize(output_mp4) / (1024 * 1024)
        print(f"[SUCCESS] Pure Python HLS Download Complete -> {output_mp4} ({final_size:.2f} MB)")
        return downloaded_count > 0

async def main():
    plugin = DailymotionPlugin()
    res = await plugin.resolve_stream("https://dai.ly/xafttpi")
    out_file = os.path.abspath("Dailymotion_Pure_Python.mp4")
    await download_hls_python(res["stream_url"], out_file, headers=res.get("headers"))

asyncio.run(main())
