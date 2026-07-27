import httpx
import re

url = "https://netshort.com/episode/the-daughter-they-buried-came-back-2074774809554599937"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

r = httpx.get(url, headers=headers, follow_redirects=True)
html = r.text

cfcdn_urls = list(set(re.findall(r'https?://[^\s\'"\\]*cfcdn\.netshort\.com[^\s\'"\\]*', html)))
print(f"Found {len(cfcdn_urls)} distinct video stream URLs embedded directly in HTML!")

for i, stream_u in enumerate(cfcdn_urls, 1):
    # Test HTTP HEAD or GET request to inspect content-length & type
    try:
        res = httpx.head(stream_u, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://netshort.com/"}, timeout=5.0)
        cl = res.headers.get("content-length", "0")
        ct = res.headers.get("content-type", "unknown")
        mb = int(cl) / (1024 * 1024) if cl.isdigit() else 0
        print(f"[{i}] {stream_u[:80]}... | Status: {res.status_code} | Size: {mb:.2f} MB | Type: {ct}")
    except Exception as e:
        print(f"[{i}] Error: {e}")
