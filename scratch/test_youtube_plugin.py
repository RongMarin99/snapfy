import asyncio
import re
import yt_dlp
from typing import Dict, Any, List

class YouTubePlugin:
    name = "YouTube Scraper"
    platform_key = "YouTube"
    domain_patterns = ["youtube.com", "youtu.be"]

    @classmethod
    def can_handle(cls, url: str) -> bool:
        url_lower = url.lower()
        return any(p in url_lower for p in cls.domain_patterns)

    async def scrape_series(self, url: str, page=None) -> Dict[str, Any]:
        # Normalize /short to /shorts
        clean_url = url
        if clean_url.rstrip('/').endswith('/short'):
            clean_url = clean_url.rstrip('/') + 's'

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_scrape, clean_url)

    def _sync_scrape(self, url: str) -> Dict[str, Any]:
        ydl_opts = {
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'playlistend': 100,  # Max items per channel scrape
        }

        title = "YouTube Content"
        thumbnail = ""
        episodes = []

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise ValueError("Failed to extract info from YouTube URL")

                title = info.get("title") or info.get("uploader") or "YouTube Channel"
                entries = info.get("entries")

                if entries is not None:
                    # Channel or Playlist
                    valid_entries = [e for e in entries if e]
                    for idx, entry in enumerate(valid_entries, 1):
                        v_id = entry.get("id")
                        if not v_id:
                            continue
                        
                        v_title = entry.get("title") or f"Video {idx}"
                        v_url = entry.get("url") or f"https://www.youtube.com/watch?v={v_id}"
                        if not v_url.startswith("http"):
                            v_url = f"https://www.youtube.com/watch?v={v_id}"

                        thumbs = entry.get("thumbnails") or []
                        v_thumb = thumbs[-1].get("url") if thumbs else f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg"
                        v_duration = entry.get("duration") or 0.0

                        episodes.append({
                            "title": v_title,
                            "episode_num": idx,
                            "url": v_url,
                            "thumbnail": v_thumb,
                            "duration": v_duration,
                            "platform": self.platform_key,
                            "status": "Waiting"
                        })
                        
                    if episodes:
                        thumbnail = episodes[0]["thumbnail"]
                else:
                    # Single video / short
                    v_id = info.get("id")
                    v_title = info.get("title") or "YouTube Video"
                    v_url = info.get("webpage_url") or url
                    thumbs = info.get("thumbnails") or []
                    thumbnail = thumbs[-1].get("url") if thumbs else f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg"
                    v_duration = info.get("duration") or 0.0

                    episodes.append({
                        "title": v_title,
                        "episode_num": 1,
                        "url": v_url,
                        "thumbnail": thumbnail,
                        "duration": v_duration,
                        "platform": self.platform_key,
                        "status": "Waiting"
                    })
        except Exception as e:
            print("YouTube Scrape Error:", e)

        return {
            "title": title,
            "thumbnail": thumbnail or "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=500",
            "platform": self.platform_key,
            "episodes": episodes
        }

    async def resolve_stream(self, episode_url: str, page=None) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_resolve, episode_url)

    def _sync_resolve(self, episode_url: str) -> Dict[str, Any]:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(episode_url, download=False)
                formats = info.get("formats", [])
                
                # 1. Look for m3u8 HLS manifests (native compatibility with DownloadEngine)
                m3u8_urls = [f.get("url") for f in formats if f.get("url") and ".m3u8" in f.get("url")]
                if m3u8_urls:
                    return {
                        "stream_url": m3u8_urls[-1],
                        "media_type": "hls",
                        "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                        "subtitles": []
                    }

                # 2. Look for combined video+audio formats
                combined = [f for f in formats if f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("url")]
                if combined:
                    # Pick highest quality combined
                    best_comb = max(combined, key=lambda x: x.get("height") or 0)
                    return {
                        "stream_url": best_comb["url"],
                        "media_type": "mp4",
                        "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                        "subtitles": []
                    }

                # 3. Fallback to any valid URL format
                for f in reversed(formats):
                    if f.get("url"):
                        return {
                            "stream_url": f["url"],
                            "media_type": "hls" if ".m3u8" in f["url"] else "mp4",
                            "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                            "subtitles": []
                        }
        except Exception as e:
            print("YouTube Stream Resolve Error:", e)

        return {
            "stream_url": "",
            "media_type": "mp4",
            "headers": {},
            "subtitles": []
        }

async def main():
    plugin = YouTubePlugin()
    print("Scraping Channel Shorts:")
    data = await plugin.scrape_series("https://www.youtube.com/@Google/shorts")
    print(f"Title: {data['title']}, Episodes: {len(data['episodes'])}")
    if data['episodes']:
        first_ep = data['episodes'][0]
        print("First Ep:", first_ep['title'], first_ep['url'])
        stream = await plugin.resolve_stream(first_ep['url'])
        print("Resolved stream media_type:", stream['media_type'])

if __name__ == "__main__":
    asyncio.run(main())
