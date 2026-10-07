import yt_dlp
import json

def test_facebook(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print("Title:", info.get("title"))
        print("Duration:", info.get("duration"))
        formats = info.get("formats", [])
        print(f"Total formats found: {len(formats)}")
        for f in formats:
            print(f"Format ID: {f.get('format_id')}, Ext: {f.get('ext')}, Resolution: {f.get('resolution')}, Vcodec: {f.get('vcodec')}, Acodec: {f.get('acodec')}, URL: {f.get('url')[:60]}...")

if __name__ == "__main__":
    import sys
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.facebook.com/watch/?v=10159188451731729"
    test_facebook(test_url)
