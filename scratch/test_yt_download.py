import yt_dlp

def resolve_youtube_stream(video_url: str) -> dict:
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        formats = info.get("formats", [])
        
        # 1. Prefer m3u8 stream manifest if available (works natively with Snapfy HLS downloader)
        m3u8_urls = [f.get("url") for f in formats if f.get("url") and ".m3u8" in f.get("url")]
        if m3u8_urls:
            return {
                "stream_url": m3u8_urls[-1], # highest quality m3u8
                "media_type": "hls",
                "headers": {"User-Agent": "Mozilla/5.0"},
                "subtitles": []
            }
            
        # 2. Fallback to combined video+audio format URL if available
        combined = [f for f in formats if f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("url")]
        if combined:
            return {
                "stream_url": combined[-1]["url"],
                "media_type": "mp4",
                "headers": {"User-Agent": "Mozilla/5.0"},
                "subtitles": []
            }

        # 3. Fallback to best format URL
        if formats:
            for f in reversed(formats):
                if f.get("url"):
                    return {
                        "stream_url": f["url"],
                        "media_type": "hls" if ".m3u8" in f["url"] else "mp4",
                        "headers": {"User-Agent": "Mozilla/5.0"},
                        "subtitles": []
                    }

    return {"stream_url": "", "media_type": "mp4", "headers": {}, "subtitles": []}

if __name__ == "__main__":
    res = resolve_youtube_stream("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    print("Resolved YouTube stream info:")
    print("Media type:", res["media_type"])
    print("Stream URL:", res["stream_url"][:120])
