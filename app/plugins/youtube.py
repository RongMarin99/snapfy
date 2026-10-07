"""
Snapfy YouTube Scraper Plugin (Channel Profile, Videos & Shorts Support via yt-dlp)
"""

import asyncio
import re
from typing import Dict, Any, List
import yt_dlp
from app.plugins.base import BasePlugin
from app.core.logger import logger
from app.core.ffmpeg import ffmpeg_manager

class YouTubePlugin(BasePlugin):
    name = "YouTube Scraper"
    platform_key = "YouTube"
    domain_patterns = ["youtube.com", "youtu.be"]

    @classmethod
    def can_handle(cls, url: str) -> bool:
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in cls.domain_patterns)

    async def scrape_series(self, url: str, page=None) -> Dict[str, Any]:
        """
        Scrapes metadata and video list for a YouTube channel, playlist, video, or short.
        """
        logger.scraper(f"Scraping YouTube URL: {url}")
        
        # Normalize /short to /shorts if present at end of channel URL
        clean_url = url.strip()
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
            'playlistend': 200,  # Batch limit for channel videos/shorts
        }

        title = "YouTube Content"
        thumbnail = ""
        episodes: List[Dict[str, Any]] = []

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise ValueError("Could not fetch YouTube video or channel information.")

                title = info.get("title") or info.get("uploader") or "YouTube Channel"
                entries = info.get("entries")

                if entries is not None:
                    # Channel or Playlist tab
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
                        v_duration = float(entry.get("duration") or 0.0)

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
                    # Single video or single short
                    v_id = info.get("id")
                    v_title = info.get("title") or "YouTube Video"
                    v_url = info.get("webpage_url") or url
                    thumbs = info.get("thumbnails") or []
                    thumbnail = thumbs[-1].get("url") if thumbs else f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg"
                    v_duration = float(info.get("duration") or 0.0)

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
            logger.error(f"YouTube scrape execution error: {e}")
            raise Exception(f"YouTube scrape error: {e}")

        logger.info(f"YouTube scrape complete: Found {len(episodes)} item(s) for '{title}'")
        return {
            "title": title,
            "thumbnail": thumbnail or "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=500",
            "platform": self.platform_key,
            "episodes": episodes
        }

    async def resolve_stream(self, episode_url: str, page=None) -> Dict[str, Any]:
        """
        Resolves YouTube stream URL using yt-dlp.
        """
        logger.scraper(f"Resolving YouTube stream for: {episode_url}")
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

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://www.youtube.com/"
                }

                # 1. First priority: Combined progressive MP4 (video + audio in single direct file)
                combined = [
                    f for f in formats 
                    if f.get("vcodec") != "none" 
                    and f.get("acodec") != "none" 
                    and f.get("url") 
                    and not f.get("url").endswith(".m3u8")
                    and f.get("protocol") in ("http", "https")
                ]
                # Progressive MP4 caps at ~360p/720p; adaptive video+audio gives HD but needs ffmpeg to mux.
                adaptive_h = max(
                    (f.get("height") or 0 for f in formats
                     if f.get("vcodec") not in (None, "none") and f.get("url")
                     and f.get("protocol") in ("http", "https") and not f.get("url").endswith(".m3u8")),
                    default=0,
                )
                best_comb = max(combined, key=lambda x: x.get("height") or 0) if combined else None
                if best_comb and not (adaptive_h > (best_comb.get("height") or 0) and ffmpeg_manager.is_available()):
                    logger.info(f"Resolved YouTube progressive MP4 stream for {episode_url} (res: {best_comb.get('height')}p)")
                    return {
                        "stream_url": best_comb["url"],
                        "media_type": "mp4",
                        "headers": headers,
                        "subtitles": []
                    }

                # 2. Second priority: Direct HTTPS video stream format (single direct file, fast direct download)
                direct_videos = [
                    f for f in formats 
                    if f.get("vcodec") != "none" 
                    and f.get("url") 
                    and not f.get("url").endswith(".m3u8")
                    and f.get("protocol") in ("http", "https")
                ]
                if direct_videos:
                    best_v = max(direct_videos, key=lambda x: x.get("height") or 0)
                    logger.info(f"Resolved YouTube direct HTTPS video stream for {episode_url} (res: {best_v.get('height')}p)")

                    # Video-only stream has no sound: pair it with best audio-only stream for muxing.
                    audio_url = ""
                    if best_v.get("acodec") in (None, "none"):
                        audio_only = [
                            f for f in formats
                            if f.get("acodec") not in (None, "none")
                            and f.get("vcodec") in (None, "none")
                            and f.get("url")
                            and f.get("protocol") in ("http", "https")
                        ]
                        if audio_only:
                            audio_url = max(audio_only, key=lambda x: x.get("abr") or 0)["url"]

                    return {
                        "stream_url": best_v["url"],
                        "audio_url": audio_url,
                        "media_type": "mp4",
                        "headers": headers,
                        "subtitles": []
                    }

                # 3. Third priority: Non-DVR m3u8 playlist fallback
                m3u8_urls = [f.get("url") for f in formats if f.get("url") and ".m3u8" in f.get("url")]
                if m3u8_urls:
                    logger.info(f"Resolved YouTube HLS fallback stream for {episode_url}")
                    return {
                        "stream_url": m3u8_urls[-1],
                        "media_type": "hls",
                        "headers": headers,
                        "subtitles": []
                    }
        except Exception as e:
            logger.error(f"YouTube stream resolution error: {e}")

        return {
            "stream_url": "",
            "media_type": "mp4",
            "headers": {},
            "subtitles": []
        }
