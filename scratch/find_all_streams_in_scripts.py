import os
import re
import json
import httpx

url = "https://netshort.com/episode/the-daughter-they-buried-came-back-2074774809554599937"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

print("Fetching full SSR HTML for NetShort...")
r = httpx.get(url, headers=headers, follow_redirects=True)
html = r.text

print(f"Received HTML of size: {len(html)} bytes")

# Search for all mp4 URLs or cfcdn URLs in HTML
cfcdn_urls = re.findall(r'https?://[^\s\'"\\]*cfcdn\.netshort\.com[^\s\'"\\]*', html)
print(f"Found {len(cfcdn_urls)} cfcdn URLs in HTML!")
for u in set(cfcdn_urls[:10]):
    print(" ->", u[:120])

# Search for any json arrays containing video URLs or episode lists
json_matches = re.findall(r'\{[^{}]*"shortPlayId"[^{}]*\}', html)
print(f"Found {len(json_matches)} shortPlayId JSON snippets!")

# Also check for full episode page URL: /full-episodes/the-daughter-they-buried-came-back-2074774809554599937
full_ep_url = "https://netshort.com/full-episodes/the-daughter-they-buried-came-back-2074774809554599937"
print(f"\nFetching Full Episodes page HTML: {full_ep_url}")
r_full = httpx.get(full_ep_url, headers=headers, follow_redirects=True)
print(f"Full Episodes HTML size: {len(r_full.text)} bytes")

full_cfcdn = re.findall(r'https?://[^\s\'"\\]*cfcdn\.netshort\.com[^\s\'"\\]*', r_full.text)
print(f"Found {len(full_cfcdn)} cfcdn URLs in Full Episodes page!")
for u in set(full_cfcdn[:10]):
    print(" ->", u[:120])
