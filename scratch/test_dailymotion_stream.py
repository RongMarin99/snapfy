import httpx
import json
import re

video_id = "xafttpi"
meta_url = f"https://www.dailymotion.com/player/metadata/video/{video_id}"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

print(f"Fetching Dailymotion player metadata from {meta_url}...")
r = httpx.get(meta_url, headers=headers)
print("Status:", r.status_code)

if r.status_code == 200:
    data = r.json()
    print("Metadata keys:", list(data.keys()))
    qualities = data.get("qualities", {})
    print("Qualities keys:", list(qualities.keys()))
    
    # Extract m3u8 playlist URL
    for q_name, q_val in qualities.items():
        if isinstance(q_val, list) and q_val:
            print(f"Quality '{q_name}' sample:", q_val[0])
            if "url" in q_val[0]:
                print(f"FOUND M3U8 STREAM MANIFEST: {q_val[0]['url']}")
