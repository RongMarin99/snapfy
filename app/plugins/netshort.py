"""
Snapfy NetShort Platform Plugin (Anichin API backed)
"""

import re
import httpx
from urllib.parse import urlparse, parse_qs
from app.plugins.base import BasePlugin
from app.core.logger import logger
from app.core.settings import settings_manager

API_BASE = "https://api.anichin.bio/netshort"
DRAMA_ID_RE = re.compile(r'(\d{15,25})')


class NetShortPlugin(BasePlugin):
    name = "NetShort Scraper"
    platform_key = "NetShort"
    domain_patterns = ["netshort.com", "netshort.app", "netshort"]

    def _api_key(self) -> str:
        return settings_manager.get("netshort_api_key", "TRIAL-ANICHIN-2026").strip()

    def _headers(self) -> dict:
        return {"User-Agent": settings_manager.get("user_agent", "Mozilla/5.0")}

    def _auth_headers(self) -> dict:
        return {**self._headers(), "X-API-Key": self._api_key()}

    @staticmethod
    def extract_drama_id(url: str) -> str:
        """Extract the numeric drama id from a pasted NetShort URL, e.g.
        https://netshort.com/episode/swapped-to-a-beggar-but-he-is-apollo-2064962492549566465
        -> 2064962492549566465
        """
        matches = DRAMA_ID_RE.findall(url)
        return matches[-1] if matches else ""

    async def _api_get(self, path: str, params: dict) -> dict:
        verify = settings_manager.get("ssl_verify", True)
        url = f"{API_BASE}/{path}"

        async with httpx.AsyncClient(timeout=20.0, verify=verify) as client:
            # Primary: X-API-Key header (your documented flow)
            resp = await client.get(url, params=params, headers=self._auth_headers())
            if resp.status_code == 401:
                # Fallback: some deployments only accept the key as a query param
                resp = await client.get(url, params={**params, "key": self._api_key()}, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def scrape_series(self, url: str, page=None) -> dict:
        logger.scraper(f"Scraping NetShort URL via API: {url}")

        drama_id = self.extract_drama_id(url)
        if not drama_id:
            logger.error(f"Could not extract NetShort drama id from URL: {url}")
            return {"title": "NetShort Drama", "thumbnail": "", "platform": self.platform_key, "episodes": []}

        try:
            resp = await self._api_get("detail", {"id": drama_id})
        except Exception as e:
            logger.error(f"NetShort API detail request failed: {e}")
            return {"title": "NetShort Drama", "thumbnail": "", "platform": self.platform_key, "episodes": []}

        if resp.get("code") != 200:
            logger.error(f"NetShort API detail error: {resp.get('msg')}")
            return {"title": "NetShort Drama", "thumbnail": "", "platform": self.platform_key, "episodes": []}

        data = resp.get("data", {})
        title = data.get("title") or "NetShort Drama"
        cover = data.get("cover") or data.get("posterImg") or ""
        api_episodes = data.get("episodes", [])

        logger.info(f"NetShort API found drama '{title}' | Total Episodes: {len(api_episodes)}")

        episodes = []
        for ep in api_episodes:
            ep_num = ep.get("episodeNumber") or ep.get("number") or (len(episodes) + 1)
            episodes.append({
                "title": f"{title} - EP {ep_num:02d}",
                "episode_num": ep_num,
                "url": f"https://netshort.com/api-episode?id={drama_id}&ep={ep_num}",
                "thumbnail": cover,
                "platform": self.platform_key,
                "status": "Locked" if ep.get("locked") else "Waiting"
            })

        return {
            "title": title,
            "thumbnail": cover,
            "platform": self.platform_key,
            "episodes": episodes
        }

    async def resolve_stream(self, episode_url: str, page=None) -> dict:
        logger.scraper(f"Resolving NetShort stream via API: {episode_url}")

        parsed = urlparse(episode_url)
        query = parse_qs(parsed.query)
        drama_id = (query.get("id") or [""])[0] or self.extract_drama_id(episode_url)
        ep_num = (query.get("ep") or ["1"])[0]

        if not drama_id:
            logger.error(f"Could not resolve NetShort drama id from episode URL: {episode_url}")
            return {"stream_url": "", "media_type": "mp4", "headers": self._headers(), "subtitles": []}

        try:
            resp = await self._api_get("episode", {"id": drama_id, "ep": ep_num})
        except Exception as e:
            logger.error(f"NetShort API episode request failed: {e}")
            return {"stream_url": "", "media_type": "mp4", "headers": self._headers(), "subtitles": []}

        if resp.get("code") != 200:
            logger.error(f"NetShort API episode error (ep {ep_num}): {resp.get('msg')}")
            return {"stream_url": "", "media_type": "mp4", "headers": self._headers(), "subtitles": []}

        stream_url = resp.get("videoUrl") or ""
        quality_list = resp.get("qualityList") or []
        if quality_list:
            best = next((q for q in quality_list if q.get("isDefault")), quality_list[0])
            stream_url = best.get("url") or stream_url

        subtitles = [
            {"lang": s.get("lang") or s.get("language") or s.get("label", ""), "url": s.get("url", "")}
            for s in (resp.get("subtitles") or [])
        ]

        media_type = "hls" if ".m3u8" in stream_url else "mp4"

        logger.info(f"Resolved NetShort stream (ep {ep_num}): {'SUCCESS' if stream_url else 'FAILED'}")

        return {
            "stream_url": stream_url,
            "media_type": media_type,
            "headers": self._headers(),
            "subtitles": subtitles
        }
