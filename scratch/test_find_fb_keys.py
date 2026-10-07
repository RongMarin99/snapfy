import asyncio
import json
import re
import httpx

URL = "https://www.facebook.com/watch/?v=10159188451731729"

async def inspect():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        res = await client.get(URL)
        html = res.text
        
        # Look for mp4 URLs
        mp4s = re.findall(r'https?:\\?/\\?/[^\s\'"]*fbcdn\.net[^\s\'"]*\.mp4[^\s\'"]*', html)
        print(f"Total fbcdn .mp4 strings: {len(mp4s)}")
        for m in list(set(mp4s))[:10]:
            clean = m.replace(r"\/", "/").replace("\\/", "/").replace(r"\u0025", "%")
            print("  -", clean[:100])

        # Search for key names in html
        for key in ["dash_manifest", "audio", "representation", "mime_type", "codecs", "playable_url", "browser_native"]:
            matches = re.findall(rf'"{key}[^"]*"\s*:\s*"?[^",}}]+"?', html, re.IGNORECASE)
            print(f"Key '{key}': found {len(matches)} matches")
            for sample in matches[:3]:
                print(f"   sample: {sample[:80]}")

if __name__ == "__main__":
    asyncio.run(inspect())
