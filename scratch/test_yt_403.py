import httpx
import yt_dlp

def test_yt_manifest(video_url):
    ydl_opts = {'quiet': True, 'no_warnings': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        formats = info.get("formats", [])
        m3u8_urls = [f.get("url") for f in formats if f.get("url") and ".m3u8" in f.get("url")]
        if not m3u8_urls:
            print("No m3u8 URLs found")
            return

        m3u8_url = m3u8_urls[-1]
        print("M3U8 URL:", m3u8_url[:90])

        # Test WITHOUT Referer header
        headers_no_ref = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res1 = httpx.get(m3u8_url, headers=headers_no_ref, follow_redirects=True)
        print(f"Request WITHOUT Referer -> Status Code: {res1.status_code}")

        # Test WITH Referer header
        headers_with_ref = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.youtube.com/"
        }
        res2 = httpx.get(m3u8_url, headers=headers_with_ref, follow_redirects=True)
        print(f"Request WITH Referer -> Status Code: {res2.status_code}")

if __name__ == "__main__":
    test_yt_manifest("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
