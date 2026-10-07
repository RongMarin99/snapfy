import re
import json

with open("scratch/fb_page.html", "r", encoding="utf-8") as f:
    html = f.read()

# Clean escaped URLs function
def clean_url(u):
    u = u.replace(r"\/", "/").replace("\\/", "/").replace(r"\u0025", "%")
    u = re.sub(r'\\u([0-9a-fa-f]{4})', lambda m: chr(int(m.group(1), 16)), u)
    u = u.replace("\\", "")
    return u

# Search for any URL containing fbcdn.net
urls = re.findall(r'https?:[^\s\'"]*fbcdn\.net[^\s\'"]*', html)
print(f"Total fbcdn URLs found: {len(urls)}")

mp4_urls = set()
audio_urls = set()
for u in urls:
    cu = clean_url(u)
    if ".mp4" in cu or "bytestart" in cu:
        mp4_urls.add(cu)
    if "audio" in cu:
        audio_urls.add(cu)

print(f"Found {len(mp4_urls)} .mp4/video URLs:")
for u in list(mp4_urls)[:10]:
    print("  MP4:", u[:120])

print(f"Found {len(audio_urls)} audio URLs:")
for u in list(audio_urls)[:10]:
    print("  AUDIO:", u[:120])

# Search for json keys in script tags
print("\n--- Searching JSON structures in HTML ---")
# Find all script contents
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(f"Total script tags: {len(scripts)}")
for idx, s in enumerate(scripts):
    if "playable_url" in s or "hd_src" in s or "sd_src" in s or "browser_native" in s or "video" in s:
        print(f"Script {idx} has video keywords, length {len(s)}")
        # find keys
        for key in ["browser_native_hd_url", "browser_native_sd_url", "playable_url_quality_hd", "playable_url", "hd_src", "sd_src"]:
            m = re.search(rf'"{key}"\s*:\s*"([^"]+)"', s)
            if m:
                print(f"  -> Key '{key}': {clean_url(m.group(1))[:100]}")
