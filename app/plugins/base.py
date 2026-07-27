"""
Snapfy Base Plugin Interface
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class BasePlugin(ABC):
    """
    Abstract base class for all platform scrapers/plugins.
    """
    name: str = "BasePlugin"
    platform_key: str = "generic"
    domain_patterns: List[str] = []

    @classmethod
    def can_handle(cls, url: str) -> bool:
        """
        Returns True if this plugin supports the given URL.
        """
        url_lower = url.lower()
        return any(pattern.lower() in url_lower for pattern in cls.domain_patterns)

    @abstractmethod
    async def scrape_series(self, url: str, page=None) -> Dict[str, Any]:
        """
        Scrapes series metadata and list of available episodes.
        
        Returns format:
        {
            "title": "Drama Title",
            "thumbnail": "https://...",
            "platform": "Platform Name",
            "episodes": [
                {
                    "title": "Episode 1",
                    "episode_num": 1,
                    "url": "https://...",
                    "thumbnail": "https://..."
                },
                ...
            ]
        }
        """
        pass

    @abstractmethod
    async def resolve_stream(self, episode_url: str, page=None) -> Dict[str, Any]:
        """
        Resolves stream media URL (MP4 / HLS .m3u8), quality options, and subtitles.
        
        Returns format:
        {
            "stream_url": "https://.../index.m3u8",
            "media_type": "hls" | "mp4",
            "headers": {},
            "subtitles": [
                {"lang": "en", "url": "https://..."},
                ...
            ]
        }
        """
        pass
