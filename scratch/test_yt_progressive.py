import yt_dlp
import httpx

def test_progressive(video_url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        formats = info.get("formats", [])
        
        # Check format 18 / 22 or any combined progressive mp4
        prog = [f for f in formats if f.get("format_id") in ("18", "22", "59", "78") or (f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("ext") == "mp4")]
        print(f"Found {len(prog)} progressive MP4 format(s)")
        for p in prog:
            print(f"Format ID: {p.get('format_id')}, Res: {p.get('height')}p, Ext: {p.get('ext')}, Size: {p.get('filesize') or p.get('filesize_approx')}")
            print("URL:", p.get("url")[:100])

if __name__ == "__main__":
    print("=== Testing Short ===")
    test_progressive("https://www.youtube.com/shorts/HtEhfvVWNr0")
    print("\n=== Testing Regular Video ===")
    test_progressive("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
