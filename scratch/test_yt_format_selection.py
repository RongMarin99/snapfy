import yt_dlp
import httpx

def test_yt_formats(video_url):
    ydl_opts = {'quiet': True, 'no_warnings': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        formats = info.get("formats", [])

        print("--- Finding Progressive Combined MP4 Formats (vcodec!=none and acodec!=none) ---")
        progressive = [f for f in formats if f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("url") and not f.get("url").endswith(".m3u8")]
        for p in progressive:
            print(f"Format ID: {p.get('format_id')}, Ext: {p.get('ext')}, Res: {p.get('height')}p, URL: {p.get('url')[:100]}")

        print("\n--- Testing HLS Sub-Playlist Parsing ---")
        m3u8_urls = [f.get("url") for f in formats if f.get("url") and ".m3u8" in f.get("url")]
        if m3u8_urls:
            master_url = m3u8_urls[-1]
            r = httpx.get(master_url)
            lines = [l.strip() for l in r.text.splitlines() if l.strip()]
            sub_playlists = [l for l in lines if not l.startswith("#") and (".m3u8" in l or "manifest" in l or "index" in l)]
            print(f"Master playlist has {len(sub_playlists)} sub-playlists.")
            if sub_playlists:
                print("First sub-playlist line:", sub_playlists[0][:100])
                # Fetch sub playlist
                sub_url = sub_playlists[-1] if sub_playlists[-1].startswith("http") else master_url.rsplit('/', 1)[0] + '/' + sub_playlists[-1]
                r_sub = httpx.get(sub_url)
                sub_lines = [l.strip() for l in r_sub.text.splitlines() if l.strip() and not l.startswith("#")]
                print(f"Sub-playlist segment count: {len(sub_lines)}")

if __name__ == "__main__":
    test_yt_formats("https://www.youtube.com/shorts/HtEhfvVWNr0")
