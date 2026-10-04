import httpx
import re
import urllib.parse

def sanitize_url(url: str) -> str:
    if not url:
        return ""
    # Strip any non-printable ASCII control characters (\x00-\x1f, \x7f-\x9f)
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', url)
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

async def test_httpx():
    bad_url = "https://httpbin.org/get?param=abc\x11def\x0fghi"
    clean_url = sanitize_url(bad_url)
    print("Testing clean URL with httpx:", clean_url)
    async with httpx.AsyncClient() as client:
        res = await client.get(clean_url)
        print("Response status:", res.status_code)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_httpx())
