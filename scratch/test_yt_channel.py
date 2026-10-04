import yt_dlp

def scrape_youtube_channel(url: str, max_items: int = 50):
    ydl_opts = {
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'playlistend': max_items,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        title = info.get("title") or info.get("uploader") or "YouTube Channel"
        entries = info.get("entries", [])
        
        episodes = []
        for idx, entry in enumerate(entries, 1):
            if not entry:
                continue
            video_id = entry.get("id")
            v_title = entry.get("title") or f"Video {idx}"
            v_url = entry.get("url") or f"https://www.youtube.com/watch?v={video_id}"
            if not v_url.startswith("http"):
                v_url = f"https://www.youtube.com/watch?v={video_id}"
            
            thumbnails = entry.get("thumbnails") or []
            thumb = thumbnails[-1].get("url") if thumbnails else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            duration = entry.get("duration") or 0.0

            episodes.append({
                "title": v_title,
                "episode_num": idx,
                "url": v_url,
                "thumbnail": thumb,
                "duration": duration,
                "platform": "YouTube",
                "status": "Waiting"
            })
            
        return {
            "title": title,
            "thumbnail": f"https://i.ytimg.com/vi/{entries[0].get('id')}/hqdefault.jpg" if entries and entries[0] else "",
            "platform": "YouTube",
            "episodes": episodes
        }

if __name__ == "__main__":
    print("--- Scraping Videos Tab ---")
    res_videos = scrape_youtube_channel("https://www.youtube.com/@Google/videos", 5)
    print("Channel Title:", res_videos["title"])
    print("Found episodes count:", len(res_videos["episodes"]))
    for ep in res_videos["episodes"]:
        print(f" - #{ep['episode_num']}: {ep['title']} ({ep['url']})")

    print("\n--- Scraping Shorts Tab ---")
    res_shorts = scrape_youtube_channel("https://www.youtube.com/@Google/shorts", 5)
    print("Channel Title:", res_shorts["title"])
    print("Found shorts count:", len(res_shorts["episodes"]))
    for ep in res_shorts["episodes"]:
        print(f" - #{ep['episode_num']}: {ep['title']} ({ep['url']})")
