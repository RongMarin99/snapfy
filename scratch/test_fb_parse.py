import asyncio
import json
import re
import httpx

# A public Facebook video URL
URL = "https://www.facebook.com/watch/?v=10159188451731729"

def clean_fb_url(raw_url: str) -> str:
    if not raw_url:
        return ""
    u = raw_url.replace(r"\/", "/").replace("\\/", "/").replace(r"\u0025", "%")
    u = re.sub(r'\\u([0-9a-fa-f]{4})', lambda m: chr(int(m.group(1), 16)), u)
    u = u.replace("\\", "")
    return u

async def inspect_fb_html():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        res = await client.get(URL)
        html = res.text
        print(f"Status: {res.status_code}, Length: {len(html)}")

        # Check progressive keys
        hd_patterns = [
            r'"browser_native_hd_url"\s*:\s*"([^"]+)"',
            r'"playable_url_quality_hd"\s*:\s*"([^"]+)"',
            r'"hd_src"\s*:\s*"([^"]+)"',
            r'"browser_native_sd_url"\s*:\s*"([^"]+)"',
            r'"playable_url"\s*:\s*"([^"]+)"',
            r'"sd_src"\s*:\s*"([^"]+)"',
        ]
        for p in hd_patterns:
            matches = re.findall(p, html)
            if matches:
                print(f"Found match for {p}: {clean_fb_url(matches[0])[:80]}...")

        # Check representations
        rep_matches = re.findall(r'"representations"\s*:\s*(\[[^\]]+\])', html)
        print(f"Found {len(rep_matches)} representations blocks")
        for idx, rep_json_str in enumerate(rep_matches):
            try:
                cleaned_str = rep_json_str.replace(r'\"', '"')
                reps = json.loads(cleaned_str)
                print(f"--- Block {idx+1}: {len(reps)} representations ---")
                for r in reps:
                    mime = r.get("mime_type") or ""
                    codecs = r.get("codecs") or ""
                    bw = r.get("bandwidth") or 0
                    width = r.get("width") or 0
                    height = r.get("height") or 0
                    url = clean_fb_url(r.get("base_url") or r.get("url") or "")
                    print(f"  mime={mime}, codecs={codecs}, res={width}x{height}, bw={bw}, url={url[:60]}...")
            except Exception as e:
                print(f"  Error parsing block {idx+1}: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_fb_html())
