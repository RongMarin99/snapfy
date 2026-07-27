import httpx
import json
import re

url = 'https://netshort.com/episode/the-daughter-they-buried-came-back-2074774809554599937'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

r = httpx.get(url, headers=headers, follow_redirects=True)
print("Status:", r.status_code)
print("Content-Length:", len(r.text))

# Search for __NEXT_DATA__
match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.DOTALL)
if match:
    data = json.loads(match.group(1))
    with open('next_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("Found __NEXT_DATA__ and saved to next_data.json!")
else:
    print("__NEXT_DATA__ not found. Searching for window.__INITIAL_STATE__ or json scripts...")
    scripts = re.findall(r'<script[^>]*>(.*?)</script>', r.text, re.DOTALL)
    print(f"Total script tags: {len(scripts)}")
    for i, s in enumerate(scripts):
        if "episode" in s.lower() or "video" in s.lower() or "m3u8" in s.lower() or "drama" in s.lower():
            print(f"Script {i} contains keywords! Length: {len(s)}")
            with open(f'script_{i}.js', 'w', encoding='utf-8') as f:
                f.write(s)
