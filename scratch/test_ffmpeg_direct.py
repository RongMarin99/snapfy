import sys
import os
sys.path.insert(0, os.path.abspath("."))

import subprocess
import asyncio
from app.plugins.dailymotion import DailymotionPlugin
from app.core.ffmpeg import ffmpeg_manager

async def test_ffmpeg_direct_hls():
    plugin = DailymotionPlugin()
    res = await plugin.resolve_stream("https://dai.ly/xafttpi")
    m3u8_url = res["stream_url"]

    out_file = os.path.abspath("Dailymotion_Test_Direct_FFmpeg.mp4")
    print("Testing direct FFmpeg download for HLS stream:", m3u8_url[:80])
    
    ffmpeg_cmd = ffmpeg_manager.get_ffmpeg_path()
    headers_dict = res.get("headers", {})
    headers_str = "".join([f"{k}: {v}\r\n" for k, v in headers_dict.items()])

    cmd = [
        ffmpeg_cmd,
        "-y",
        "-headers", headers_str,
        "-i", m3u8_url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        out_file
    ]

    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creation_flags)
    
    print("Return code:", proc.returncode)
    if os.path.exists(out_file):
        size_mb = os.path.getsize(out_file) / (1024 * 1024)
        print(f"[SUCCESS] Downloaded full Dailymotion video file! Size: {size_mb:.2f} MB")
    else:
        print("FFmpeg stderr output:", proc.stderr.decode("utf-8", errors="ignore"))

asyncio.run(test_ffmpeg_direct_hls())
