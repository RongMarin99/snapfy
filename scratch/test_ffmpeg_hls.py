import sys
import os
sys.path.insert(0, os.path.abspath("."))

import subprocess
import asyncio
from app.plugins.dailymotion import DailymotionPlugin
from app.core.ffmpeg import ffmpeg_manager

async def test_ffmpeg_hls():
    plugin = DailymotionPlugin()
    res = await plugin.resolve_stream("https://dai.ly/xafttpi")
    m3u8_url = res["stream_url"]

    out_file = os.path.abspath("Dailymotion_Test_FFmpeg.mp4")
    print("Testing FFmpeg download for HLS stream:", m3u8_url[:80])
    
    success = ffmpeg_manager.convert_hls_to_mp4(m3u8_url, out_file, headers=res.get("headers"))
    print("FFmpeg Conversion Success:", success)

    if success and os.path.exists(out_file):
        size_mb = os.path.getsize(out_file) / (1024 * 1024)
        print(f"[SUCCESS] Downloaded full Dailymotion video file! Size: {size_mb:.2f} MB")

asyncio.run(test_ffmpeg_hls())
