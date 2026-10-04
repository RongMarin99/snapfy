import re
import urllib.parse
import httpx
import asyncio

def sanitize_url(url: str) -> str:
    if not url:
        return ""
    # Strip any non-printable ASCII control characters (\x00-\x1f, \x7f-\x9f)
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', url.strip())
    try:
        parsed = urllib.parse.urlparse(cleaned)
        safe_path = urllib.parse.quote(parsed.path, safe="/:[]")
        safe_query = urllib.parse.quote(parsed.query, safe="=&%+!*,;:@$-_.~'/[]")
        return urllib.parse.urlunparse((
            parsed.scheme,
            parsed.netloc,
            safe_path,
            parsed.params,
            safe_query,
            parsed.fragment
        ))
    except Exception:
        return urllib.parse.quote(cleaned, safe=":/%?&=#+[]@!$'()*;,~-")

async def test_segment_fetching():
    # Simulate a segment URL with non-printable characters as shown in user log
    bad_segment_urls = [
        "https://httpbin.org/get?seg=5816&token=\x11at_pos_1238",
        "https://httpbin.org/get?seg=5817&token=\x0fat_pos_1252",
        "https://httpbin.org/get?seg=3571&token=\x08at_pos_1253",
        "https://httpbin.org/get?seg=3572&token=\x18at_pos_1257",
        "https://httpbin.org/get?seg=2804&token=\x00at_pos_1248"
    ]

    async with httpx.AsyncClient(timeout=10.0) as client:
        for idx, raw_url in enumerate(bad_segment_urls, 1):
            clean_url = sanitize_url(raw_url)
            print(f"Segment {idx} raw: {repr(raw_url)}")
            print(f"Segment {idx} clean: {repr(clean_url)}")
            try:
                res = await client.get(clean_url)
                print(f" -> Fetch Result: HTTP {res.status_code} SUCCESS!")
            except Exception as e:
                print(f" -> Fetch Result: FAILED with error: {e}")

if __name__ == "__main__":
    asyncio.run(test_segment_fetching())
