import yt_dlp
import json

def test_extract(url):
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'playlistend': 5 # just test 5 items
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            print(f"Title: {info.get('title')}")
            print(f"Type: {info.get('_type', 'video')}")
            entries = info.get('entries', [])
            if entries:
                print(f"Found {len(list(entries))} entries (flat)")
                for idx, entry in enumerate(entries, 1):
                    if entry:
                        print(f"  {idx}. {entry.get('title')} -> https://www.youtube.com/watch?v={entry.get('id')}")
            else:
                print("Single video or empty entries")
        except Exception as e:
            print("Extract error:", e)

if __name__ == "__main__":
    # Test a public YouTube channel or test URL
    test_extract("https://www.youtube.com/@Google/shorts")
