import yt_dlp

def test_yt_formats(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])
        print(f"Total formats found: {len(formats)}")
        m3u8_urls = [f.get("url") for f in formats if f.get("url") and ".m3u8" in f.get("url")]
        progressive_mp4s = [f for f in formats if f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("ext") == "mp4"]
        
        print("M3U8 URLs count:", len(m3u8_urls))
        if m3u8_urls:
            print("Sample M3U8:", m3u8_urls[0][:100])
        print("Progressive MP4s count:", len(progressive_mp4s))
        if progressive_mp4s:
            print("Sample Progressive MP4 URL:", progressive_mp4s[0].get("url")[:100])

if __name__ == "__main__":
    test_yt_formats("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    print("--- Testing Shorts ---")
    test_yt_formats("https://www.youtube.com/shorts/300k6fW5Rfs")
