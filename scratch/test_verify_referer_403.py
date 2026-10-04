import httpx
import yt_dlp

def test_referer():
    video_url = "https://www.youtube.com/shorts/G22BVF0U-XA"
    ydl_opts = {'quiet': True, 'no_warnings': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        formats = info.get("formats", [])
        m3u8_urls = [f.get("url") for f in formats if f.get("url") and ".m3u8" in f.get("url")]
        if not m3u8_urls:
            print("No m3u8 URLs found")
            return
        m3u8_url = m3u8_urls[-1]

    print("Testing M3U8 URL:", m3u8_url[:80])

    # 1. Test with Dailymotion referer (What downloader.py was using!)
    headers_dailymotion = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.dailymotion.com/"
    }
    r1 = httpx.get(m3u8_url, headers=headers_dailymotion)
    print("Response with Dailymotion Referer:", r1.status_code)

    # 2. Test with YouTube referer
    headers_youtube = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.youtube.com/"
    }
    r2 = httpx.get(m3u8_url, headers=headers_youtube)
    print("Response with YouTube Referer:", r2.status_code)

if __name__ == "__main__":
    test_referer()
