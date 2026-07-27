import httpx
import re
import json

url = "https://dai.ly/xafttpi"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

print(f"Testing Dailymotion URL resolution for {url}...")
r = httpx.get(url, headers=headers, follow_redirects=True)
print("Final URL:", r.url)
print("Status:", r.status_code)

# Extract video ID from URL: e.g. xafttpi
video_id_match = re.search(r'video/([a-zA-Z0-9]+)', str(r.url)) or re.search(r'dai\.ly/([a-zA-Z0-9]+)', url)
video_id = video_id_match.group(1) if video_id_match else "xafttpi"
print("Extracted Video ID:", video_id)

# Fetch API info
api_url = f"https://api.dailymotion.com/video/{video_id}?fields=title,thumbnail_720_url,duration"
r_api = httpx.get(api_url, headers=headers)
print("API Status:", r_api.status_code)
print("API Response:", r_api.json())

# Fetch Embed player page to extract m3u8 stream manifest
embed_url = f"https://www.dailymotion.com/embed/video/{video_id}"
r_embed = httpx.get(embed_url, headers=headers)
print("Embed Page Status:", r_embed.status_code)

# Search for m3u8 manifest in embed page
m3u8_matches = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', r_embed.text)
print(f"Found {len(m3u8_matches)} m3u8 stream manifests!")
for m in m3u8_matches[:5]:
    print(" ->", m)
