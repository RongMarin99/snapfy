import httpx
import yt_dlp

def debug_manifest_fetch():
    video_url = "https://www.youtube.com/shorts/G22BVF0U-XA"
    ydl_opts = {'quiet': True, 'no_warnings': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        formats = info.get("formats", [])
        m3u8_urls = [f.get("url") for f in formats if f.get("url") and ".m3u8" in f.get("url")]
        m3u8_url = m3u8_urls[-1]

    print("M3U8 URL:", m3u8_url)

    # Test 1: Standard httpx AsyncClient / get
    r1 = httpx.get(m3u8_url)
    print("Test 1 (No headers):", r1.status_code)

    # Test 2: With User-Agent
    r2 = httpx.get(m3u8_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    print("Test 2 (User-Agent):", r2.status_code)

    # Test 3: With http2=True
    try:
        r3 = httpx.get(m3u8_url, http2=True, headers={"User-Agent": "Mozilla/5.0"})
        print("Test 3 (http2=True):", r3.status_code)
    except Exception as e:
        print("Test 3 (http2 error):", e)

    # Test 4: Check urllib / requests
    import urllib.request
    req = urllib.request.Request(m3u8_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req) as resp:
            print("Test 4 (urllib):", resp.status)
    except Exception as e:
        print("Test 4 (urllib error):", e)

if __name__ == "__main__":
    debug_manifest_fetch()
