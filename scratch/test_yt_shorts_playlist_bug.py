import yt_dlp
import httpx

def test_short_formats(url):
    ydl_opts = {'quiet': True, 'no_warnings': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])
        print(f"Total formats for {url}: {len(formats)}")
        for f in formats:
            f_id = f.get("format_id")
            ext = f.get("ext")
            vcodec = f.get("vcodec")
            acodec = f.get("acodec")
            protocol = f.get("protocol")
            height = f.get("height")
            f_url = f.get("url")
            is_m3u8 = ".m3u8" in f_url if f_url else False
            print(f"Format ID: {f_id:6s} | Ext: {ext:4s} | Res: {height}p | VCodec: {vcodec} | ACodec: {acodec} | Proto: {protocol} | M3U8: {is_m3u8}")
            if is_m3u8:
                print(" -> M3U8 URL sample:", f_url[:120])

if __name__ == "__main__":
    test_short_formats("https://www.youtube.com/shorts/HtEhfvVWNr0")
