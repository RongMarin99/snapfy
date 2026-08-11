"""
Snapfy DramaBox Platform Plugin (sansekai API backed)
"""

import re
import asyncio
import time
import httpx
from urllib.parse import urlparse, parse_qs
from collections import defaultdict
from app.plugins.base import BasePlugin
from app.core.logger import logger
from app.core.settings import settings_manager
from app.core.proxy_pool import proxy_pool

API_BASE = "https://api.sansekai.my.id/api/dramabox/allepisode"
DECRYPT_API = "https://api.sansekai.my.id/api/dramabox/decrypt"
BOOK_ID_RE = re.compile(r'/movie/(\d+)')
FALLBACK_ID_RE = re.compile(r'(\d{6,25})')
CACHE_TTL_SECONDS = 600
MAX_RETRIES = 5
DECRYPT_MIN_INTERVAL = 1.5


class DramaBoxPlugin(BasePlugin):
    name = "DramaBox Scraper"
    platform_key = "DramaBox"
    domain_patterns = ["dramabox.db", "dramaboxdb.com", "dramabox.com", "dramabox"]

    def __init__(self):
        # Per-bookId cache so every episode of the same drama shares one
        # API call instead of each concurrent download re-fetching the
        # full chapter list (which trips the upstream 429 rate limit).
        self._chapter_cache: dict[str, tuple[float, list]] = {}
        self._book_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        # The decrypt endpoint is rate limited hard; serialize every call
        # through one lock so concurrent episode downloads decrypt one-by-one.
        self._decrypt_lock = asyncio.Lock()
        self._last_decrypt_ts = 0.0

    @staticmethod
    def extract_book_id(url: str) -> str:
        """Extract bookId from a pasted DramaBox URL, e.g.
        https://www.dramaboxdb.com/movie/42000014893/fear-her-my-mom-s-the-lady-boss
        -> 42000014893
        """
        m = BOOK_ID_RE.search(url)
        if m:
            return m.group(1)
        matches = FALLBACK_ID_RE.findall(url)
        return matches[-1] if matches else ""

    def _headers(self) -> dict:
        return {"User-Agent": settings_manager.get("user_agent", "Mozilla/5.0")}

    async def _fetch_chapters_raw(self, book_id: str) -> list:
        verify = settings_manager.get("ssl_verify", True)
        delay = 1.5
        data = None

        for attempt in range(1, MAX_RETRIES + 1):
            proxy = proxy_pool.get()
            async with httpx.AsyncClient(timeout=20.0, verify=verify, proxy=proxy) as client:
                try:
                    resp = await client.get(API_BASE, params={"bookId": book_id}, headers={"accept": "*/*"})
                except httpx.HTTPError as e:
                    if attempt == MAX_RETRIES:
                        raise
                    logger.warning(f"DramaBox API request error via proxy (bookId {book_id}): {e}. Retrying with a new proxy ({attempt}/{MAX_RETRIES})")
                    await asyncio.sleep(min(delay, 3.0))
                    delay *= 2
                    continue

                if resp.status_code == 429:
                    if attempt == MAX_RETRIES:
                        resp.raise_for_status()
                    retry_after = resp.headers.get("Retry-After")
                    wait_s = float(retry_after) if retry_after and retry_after.isdigit() else delay
                    logger.warning(f"DramaBox API rate limited (bookId {book_id}), rotating proxy and retrying in {wait_s:.1f}s ({attempt}/{MAX_RETRIES})")
                    await asyncio.sleep(wait_s)
                    delay *= 2
                    continue

                resp.raise_for_status()
                data = resp.json()
                break

        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("data", "list", "chapterList", "episodes"):
                v = data.get(key)
                if isinstance(v, list):
                    return v
            for v in data.values():
                if isinstance(v, list):
                    return v
        return []

    async def _fetch_chapters(self, book_id: str) -> list:
        cached = self._chapter_cache.get(book_id)
        if cached and (time.monotonic() - cached[0]) < CACHE_TTL_SECONDS:
            return cached[1]

        async with self._book_locks[book_id]:
            # Another task may have populated the cache while we waited on the lock.
            cached = self._chapter_cache.get(book_id)
            if cached and (time.monotonic() - cached[0]) < CACHE_TTL_SECONDS:
                return cached[1]

            chapters = await self._fetch_chapters_raw(book_id)
            self._chapter_cache[book_id] = (time.monotonic(), chapters)
            return chapters

    async def _decrypt_url_raw(self, encrypted_url: str) -> str:
        verify = settings_manager.get("ssl_verify", True)
        delay = 1.5
        data = None

        for attempt in range(1, MAX_RETRIES + 1):
            proxy = proxy_pool.get()
            async with httpx.AsyncClient(timeout=20.0, verify=verify, proxy=proxy) as client:
                try:
                    resp = await client.get(DECRYPT_API, params={"url": encrypted_url}, headers={"accept": "*/*"})
                except httpx.HTTPError as e:
                    if attempt == MAX_RETRIES:
                        raise
                    logger.warning(f"DramaBox decrypt request error via proxy: {e}. Retrying with a new proxy ({attempt}/{MAX_RETRIES})")
                    await asyncio.sleep(min(delay, 3.0))
                    delay *= 2
                    continue

                if resp.status_code == 429:
                    if attempt == MAX_RETRIES:
                        resp.raise_for_status()
                    retry_after = resp.headers.get("Retry-After")
                    wait_s = float(retry_after) if retry_after and retry_after.isdigit() else delay
                    logger.warning(f"DramaBox decrypt API rate limited, rotating proxy and retrying in {wait_s:.1f}s ({attempt}/{MAX_RETRIES})")
                    await asyncio.sleep(wait_s)
                    delay *= 2
                    continue

                resp.raise_for_status()
                data = resp.json()
                break

        if not data.get("success"):
            logger.error(f"DramaBox decrypt failed: {data.get('message')}")
            return ""
        return data.get("streamUrl", "")

    async def _decrypt_url(self, encrypted_url: str) -> str:
        """Serializes every decrypt call (one-by-one, spaced out) since the
        decrypt endpoint rate limits much harder than the episode list API."""
        async with self._decrypt_lock:
            elapsed = time.monotonic() - self._last_decrypt_ts
            if elapsed < DECRYPT_MIN_INTERVAL:
                await asyncio.sleep(DECRYPT_MIN_INTERVAL - elapsed)
            try:
                return await self._decrypt_url_raw(encrypted_url)
            finally:
                self._last_decrypt_ts = time.monotonic()

    @staticmethod
    def _qualities_for_chapter(chapter: dict) -> list:
        """Flattens the default (or first) CDN's videoPathList into a simple
        quality -> url list, sorted from highest to lowest quality."""
        cdn_list = chapter.get("cdnList") or []
        if not cdn_list:
            return []
        cdn = next((c for c in cdn_list if c.get("isDefault")), cdn_list[0])
        qualities = [
            {
                "quality": v.get("quality"),
                "url": v.get("videoPath"),
                "isDefault": bool(v.get("isDefault"))
            }
            for v in (cdn.get("videoPathList") or [])
            if v.get("videoPath")
        ]
        qualities.sort(key=lambda q: q.get("quality") or 0, reverse=True)
        return qualities

    async def scrape_series(self, url: str, page=None) -> dict:
        logger.scraper(f"Scraping DramaBox URL via API: {url}")

        book_id = self.extract_book_id(url)
        match = re.search(r'/([^/]+)/?$', url.rstrip('/'))
        slug_title = match.group(1).replace('-', ' ').title() if match else "Drama"

        if not book_id:
            logger.error(f"Could not extract DramaBox bookId from URL: {url}")
            return {"title": slug_title, "thumbnail": "", "platform": self.platform_key, "episodes": []}

        try:
            chapters = await self._fetch_chapters(book_id)
        except Exception as e:
            logger.error(f"DramaBox API allepisode request failed: {e}")
            return {"title": slug_title, "thumbnail": "", "platform": self.platform_key, "episodes": []}

        if not chapters:
            logger.error(f"DramaBox API returned no chapters for bookId {book_id}")
            return {"title": slug_title, "thumbnail": "", "platform": self.platform_key, "episodes": []}

        logger.info(f"DramaBox API found '{slug_title}' | Total Episodes: {len(chapters)}")

        thumbnail = chapters[0].get("chapterImg", "")
        episodes = []
        for ch in chapters:
            chapter_id = ch.get("chapterId")
            ep_num = (ch.get("chapterIndex") or 0) + 1
            qualities = self._qualities_for_chapter(ch)
            episodes.append({
                "title": ch.get("chapterName") or f"{slug_title} - Episode {ep_num}",
                "episode_num": ep_num,
                "url": f"https://dramaboxdb.com/api-episode?bookId={book_id}&chapterId={chapter_id}",
                "thumbnail": ch.get("chapterImg", thumbnail),
                "platform": self.platform_key,
                "qualities": [q["quality"] for q in qualities],
                "status": "Locked" if ch.get("isCharge") else "Waiting"
            })

        return {
            "title": slug_title,
            "thumbnail": thumbnail,
            "platform": self.platform_key,
            "episodes": episodes
        }

    async def resolve_stream(self, episode_url: str, page=None) -> dict:
        logger.scraper(f"Resolving DramaBox stream via API: {episode_url}")

        parsed = urlparse(episode_url)
        query = parse_qs(parsed.query)
        book_id = (query.get("bookId") or [""])[0] or self.extract_book_id(episode_url)
        chapter_id = (query.get("chapterId") or [""])[0]

        if not book_id:
            logger.error(f"Could not resolve DramaBox bookId from episode URL: {episode_url}")
            return {"stream_url": "", "media_type": "mp4", "headers": self._headers(), "subtitles": [], "qualities": []}

        try:
            chapters = await self._fetch_chapters(book_id)
        except Exception as e:
            logger.error(f"DramaBox API allepisode request failed: {e}")
            return {"stream_url": "", "media_type": "mp4", "headers": self._headers(), "subtitles": [], "qualities": []}

        chapter = next((c for c in chapters if str(c.get("chapterId")) == str(chapter_id)), None)
        if chapter is None and chapters:
            chapter = chapters[0]

        if chapter is None:
            logger.error(f"DramaBox chapter {chapter_id} not found for bookId {book_id}")
            return {"stream_url": "", "media_type": "mp4", "headers": self._headers(), "subtitles": [], "qualities": []}

        qualities = self._qualities_for_chapter(chapter)
        if not qualities:
            logger.error(f"DramaBox chapter {chapter_id} has no playable video paths")
            return {"stream_url": "", "media_type": "mp4", "headers": self._headers(), "subtitles": [], "qualities": []}

        preferred = str(settings_manager.get("dramabox_quality", "1080"))
        chosen = None
        if preferred.isdigit():
            chosen = next((q for q in qualities if q.get("quality") == int(preferred)), None)
        if not chosen:
            chosen = next((q for q in qualities if q.get("isDefault")), qualities[0])

        decrypted_url = await self._decrypt_url(chosen["url"])
        if not decrypted_url:
            logger.error(f"DramaBox decrypt returned no stream for chapter {chapter_id}")
            return {"stream_url": "", "media_type": "mp4", "headers": self._headers(), "subtitles": [], "qualities": qualities}

        subtitles = [
            {"lang": s.get("captionLanguage", ""), "url": s.get("url", "")}
            for s in (chapter.get("subLanguageVoList") or [])
            if s.get("url")
        ]

        media_type = "hls" if chapter.get("isM3u8") else "mp4"

        logger.info(f"Resolved DramaBox stream (chapter {chapter_id}): SUCCESS -> {chosen['quality']}p (decrypted)")

        return {
            "stream_url": decrypted_url,
            "media_type": media_type,
            "headers": self._headers(),
            "subtitles": subtitles,
            "qualities": qualities
        }
