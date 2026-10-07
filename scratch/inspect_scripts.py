import re
import json

with open("scratch/fb_page.html", "r", encoding="utf-8") as f:
    html = f.read()

def clean_url(u):
    u = u.replace(r"\/", "/").replace("\\/", "/").replace(r"\u0025", "%")
    u = re.sub(r'\\u([0-9a-fa-f]{4})', lambda m: chr(int(m.group(1), 16)), u)
    u = u.replace("\\", "")
    return u

scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
for idx in [38, 62]:
    if idx < len(scripts):
        s = scripts[idx]
        print(f"=== SCRIPT {idx} ===")
        # search for any http/https URL in script
        urls = re.findall(r'https?:[^\s\'"]*', s)
        print(f"Found {len(urls)} URLs in script {idx}")
        for u in urls[:15]:
            cu = clean_url(u)
            if "fbcdn" in cu:
                print("  FBCDN URL:", cu[:120])
            elif "http" in cu:
                print("  URL:", cu[:80])

        # search for keys like "src", "url", "stream", "video", "audio", "dash", "playlist", "representation"
        for key in ["src", "url", "playable", "hd", "sd", "audio", "video", "manifest", "dash"]:
            m = re.findall(rf'"{key}[^"]*"\s*:\s*"([^"]+)"', s, re.IGNORECASE)
            if m:
                print(f"Key pattern '{key}': {len(m)} matches")
                for sample in m[:3]:
                    print(f"  sample: {clean_url(sample)[:100]}")
