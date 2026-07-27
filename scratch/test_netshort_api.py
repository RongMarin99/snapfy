import httpx
import json

url = "https://netshort.com/prod-web-api/web/v4/short_play/detail_info/cascade_label"

# We extract shortPlayId from the drama URL: 2074774809554599937
drama_id = "2074774809554599937"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json",
    "Referer": f"https://netshort.com/episode/the-daughter-they-buried-came-back-{drama_id}"
}

payload = {
    "shortPlayId": drama_id,
    "episodeNum": 1
}

print(f"Testing POST request to NetShort API: {url} with payload {payload}...")
try:
    r = httpx.post(url, json=payload, headers=headers, timeout=15.0)
    print("Status:", r.status_code)
    print("Response JSON:", json.dumps(r.json(), indent=2, ensure_ascii=False)[:2000])
except Exception as e:
    print("POST failed:", e)
    print("Trying GET request...")
    r = httpx.get(f"{url}?shortPlayId={drama_id}", headers=headers, timeout=15.0)
    print("GET Status:", r.status_code)
    print("GET Response:", r.text[:1000])
