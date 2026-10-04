import yt_dlp

def test_resolve(url):
    # Test formats or direct download using yt-dlp
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': 'downloads_test/%(title)s.%(ext)s',
        'quiet': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print("Title:", info.get("title"))
        requested_formats = info.get("requested_formats")
        if requested_formats:
            print("Requested formats count:", len(requested_formats))
            for f in requested_formats:
                print(" - Format ID:", f.get("format_id"), "URL:", f.get("url")[:80])
        elif info.get("url"):
            print("Direct URL:", info.get("url")[:100])

if __name__ == "__main__":
    test_resolve("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
