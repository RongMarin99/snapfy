import asyncio
import httpx
import os
import sys
sys.path.insert(0, os.path.abspath("."))

from app.core.scraper import plugin_manager

async def test_download():
    url = "https://netshort.com/episode/the-daughter-they-buried-came-back-2074774809554599937"
    print("Resolving stream for EP 1...")
    info = await plugin_manager.resolve(url)
    stream_url = info["stream_url"]
    headers = info.get("headers", {})
    headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    headers["Referer"] = "https://netshort.com/"

    print("Stream URL:", stream_url[:120])
    
    print("Downloading video stream with headers...")
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        r = await client.get(stream_url, headers=headers)
        print("Response Status Code:", r.status_code)
        print("Response Headers Content-Type:", r.headers.get("content-type"))
        print("Downloaded Bytes:", len(r.content))

        out_path = os.path.join(os.getcwd(), "EP1_Full_Video.mp4")
        with open(out_path, "wb") as f:
            f.write(r.content)
        
        print(f"Saved to {out_path}! Size: {os.path.getsize(out_path) / (1024*1024):.2f} MB")

asyncio.run(test_download())
