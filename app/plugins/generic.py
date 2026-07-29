"""
Snapfy Generic / Universal Scraper Plugin with Robust Multi-Platform Resolver
"""

import re
import urllib.parse
import httpx
from bs4 import BeautifulSoup
from app.plugins.base import BasePlugin
from app.core.logger import logger
from app.core.browser import browser_manager
from app.core.settings import settings_manager

class GenericPlugin(BasePlugin):
    name = "Universal / Generic Video Scraper"
    platform_key = "Universal"
    domain_patterns = []  # Catch-all fallback plugin

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return True

    async def scrape_series(self, url: str, page=None) -> dict:
        logger.scraper(f"Scraping Generic / Universal URL: {url}")
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.replace("www.", "").capitalize() or "Web Media"

        title = f"{domain} Video"
        thumbnail = ""
        stream_url = ""
        media_type = "mp4"

        # Check if direct video link
        if ".mp4" in url:
            stream_url = url
            media_type = "mp4"
            title = f"{domain} - Direct MP4 Video"
        elif ".m3u8" in url:
            stream_url = url
            media_type = "hls"
            title = f"{domain} - Direct HLS Stream"

        # Special handling for Dailymotion in generic plugin fallback
        if "dailymotion.com" in url or "dai.ly" in url:
            m = re.search(r'video/([a-zA-Z0-9]+)', url) or re.search(r'dai\.ly/([a-zA-Z0-9]+)', url)
            if m:
                video_id = m.group(1)
                try:
                    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, verify=settings_manager.get("ssl_verify", True)) as client:
                        api_res = await client.get(f"https://api.dailymotion.com/video/{video_id}?fields=title,thumbnail_720_url")
                        if api_res.status_code == 200:
                            d = api_res.json()
                            title = d.get("title", title)
                            thumbnail = d.get("thumbnail_720_url", thumbnail)
                except Exception:
                    pass

        if not stream_url and page:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(2000)
                
                p_title = await page.title()
                if p_title:
                    title = p_title.strip()

                og_image = await page.query_selector("meta[property='og:image']")
                if og_image:
                    thumbnail = await og_image.get_attribute("content") or ""
            except Exception as e:
                logger.warning(f"Generic page scrape warning: {e}")

        if not stream_url:
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, verify=settings_manager.get("ssl_verify", True)) as client:
                    resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "lxml")
                        og_title = soup.find("meta", property="og:title")
                        if og_title and og_title.get("content"):
                            title = og_title["content"]

                        og_img = soup.find("meta", property="og:image")
                        if og_img and og_img.get("content"):
                            thumbnail = og_img["content"]

                        # Search for m3u8 or mp4
                        m3u8 = re.search(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', resp.text)
                        if m3u8:
                            stream_url = m3u8.group(0)
                            media_type = "hls"
                        else:
                            mp4 = re.search(r'https?://[^\s\'"]+\.mp4[^\s\'"]*', resp.text)
                            if mp4:
                                stream_url = mp4.group(0)
                                media_type = "mp4"
            except Exception as e:
                logger.error(f"HTTP fetch error in GenericPlugin: {e}")

        episodes = [{
            "title": title,
            "episode_num": 1,
            "url": url,
            "stream_url": stream_url,
            "media_type": media_type,
            "thumbnail": thumbnail or "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=500"
        }]

        return {
            "title": title,
            "thumbnail": thumbnail or "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=500",
            "platform": domain,
            "episodes": episodes
        }

    async def resolve_stream(self, episode_url: str, page=None) -> dict:
        if ".mp4" in episode_url:
            return {"stream_url": episode_url, "media_type": "mp4", "headers": {}, "subtitles": []}
        elif ".m3u8" in episode_url:
            return {"stream_url": episode_url, "media_type": "hls", "headers": {}, "subtitles": []}

        # Dailymotion fallback
        if "dailymotion.com" in episode_url or "dai.ly" in episode_url:
            m = re.search(r'video/([a-zA-Z0-9]+)', episode_url) or re.search(r'dai\.ly/([a-zA-Z0-9]+)', episode_url)
            if m:
                video_id = m.group(1)
                try:
                    meta_url = f"https://www.dailymotion.com/player/metadata/video/{video_id}"
                    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, verify=settings_manager.get("ssl_verify", True)) as client:
                        resp = await client.get(meta_url, headers={"User-Agent": "Mozilla/5.0"})
                        if resp.status_code == 200:
                            data = resp.json()
                            qualities = data.get("qualities", {})
                            for q_list in qualities.values():
                                if isinstance(q_list, list) and q_list:
                                    if "url" in q_list[0]:
                                        return {
                                            "stream_url": q_list[0]["url"],
                                            "media_type": "hls",
                                            "headers": {"User-Agent": "Mozilla/5.0", "Referer": "https://www.dailymotion.com/"},
                                            "subtitles": []
                                        }
                except Exception as e:
                    logger.error(f"Error in GenericPlugin Dailymotion resolve: {e}")

        # Browser network interception fallback
        captured_stream = ""
        media_type = "mp4"

        if page:
            async def on_resp(resp):
                nonlocal captured_stream, media_type
                u = resp.url
                ct = resp.headers.get("content-type", "")
                if ".m3u8" in u:
                    captured_stream = u
                    media_type = "hls"
                elif ".mp4" in u or "video/mp4" in ct:
                    if not captured_stream:
                        captured_stream = u
                        media_type = "mp4"

            page.on("response", on_resp)
            try:
                await page.goto(episode_url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(3000)
            except Exception:
                pass

        return {
            "stream_url": captured_stream,
            "media_type": media_type,
            "headers": {"User-Agent": "Mozilla/5.0"},
            "subtitles": []
        }
