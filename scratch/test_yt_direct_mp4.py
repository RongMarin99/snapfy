import yt_dlp
import httpx

def test_direct_formats(video_url):
    ydl_opts = {'quiet': True, 'no_warnings': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        formats = info.get("formats", [])
        
        print(f"Total formats for {video_url}: {len(formats)}")
        
        # 1. Look for progressive formats (format 18, 22, etc.)
        for f in formats:
            f_id = f.get("format_id")
            ext = f.get("ext")
            vcodec = f.get("vcodec")
            acodec = f.get("acodec")
            protocol = f.get("protocol")
            height = f.get("height")
            url = f.get("url")
            filesize = f.get("filesize") or f.get("filesize_approx")
            size_mb = f"{filesize/(1024*1024):.1f}MB" if filesize else "Unknown"
            
            if protocol in ("http", "https") and not url.endswith(".m3u8"):
                print(f"ID: {f_id:6s} | Ext: {ext:4s} | Res: {str(height):5s}p | VCodec: {str(vcodec):15s} | ACodec: {str(acodec):12s} | Size: {size_mb:10s} | Proto: {protocol}")

if __name__ == "__main__":
    print("=== Testing Short Video ===")
    test_direct_formats("https://www.youtube.com/shorts/HtEhfvVWNr0")
    print("\n=== Testing Regular Video ===")
    test_direct_formats("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
