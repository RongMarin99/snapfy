import urllib.parse
import re

def sanitize_url(url: str) -> str:
    if not url:
        return ""
    # Remove non-printable control characters (\x00-\x1f, \x7f-\x9f)
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

if __name__ == "__main__":
    bad_url = "https://manifest.googlevideo.com/api/manifest/hls?param=abc\x11def\x0fghi"
    print("Original:", repr(bad_url))
    clean = sanitize_url(bad_url)
    print("Sanitized:", repr(clean))
