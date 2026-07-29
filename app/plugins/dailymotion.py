"""
Snapfy Dailymotion Scraper Plugin (High Performance Direct CDN Stream & Segment Resolver)
"""

import re
import httpx
from app.plugins.base import BasePlugin
from app.core.logger import logger
from app.core.browser import browser_manager
from app.core.settings import settings_manager

class DailymotionPlugin(BasePlugin):
    name = "Dailymotion Scraper"
    platform_key = "Dailymotion"
    domain_patterns = ["dailymotion.com", "dai.ly", "dailymotion"]

    def extract_video_id(self, url: str) -> str:
        m = re.search(r'video/([a-zA-Z0-9]+)', url) or re.search(r'dai\.ly/([a-zA-Z0-9]+)', url)
        return m.group(1) if m else ""

    async def scrape_series(self, url: str, page=None) -> dict:
        logger.scraper(f"Scraping Dailymotion URL: {url}")
        video_id = self.extract_video_id(url)
        
        title = "Dailymotion Video"
        thumbnail = ""
        duration = 0.0

        if video_id:
            try:
                api_url = f"https://api.dailymotion.com/video/{video_id}?fields=title,thumbnail_720_url,duration"
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, verify=settings_manager.get("ssl_verify", True)) as client:
                    resp = await client.get(api_url, headers={"User-Agent": "Mozilla/5.0"})
                    if resp.status_code == 200:
                        data = resp.json()
                        title = data.get("title", title)
                        thumbnail = data.get("thumbnail_720_url", "")
                        duration = float(data.get("duration", 0))
            except Exception as e:
                logger.error(f"Error fetching Dailymotion video metadata: {e}")

        episodes = [{
            "title": title,
            "episode_num": 1,
            "url": url,
            "thumbnail": thumbnail or "https://images.unsplash.com/photo-1574375927938-d5a98e8ffe85?w=500",
            "duration": duration,
            "platform": self.platform_key,
            "status": "Waiting"
        }]

        return {
            "title": title,
            "thumbnail": thumbnail,
            "platform": self.platform_key,
            "episodes": episodes
        }

    async def resolve_stream(self, episode_url: str, page=None) -> dict:
        logger.scraper(f"Resolving Dailymotion stream: {episode_url}")
        video_id = self.extract_video_id(episode_url)
        cdn_manifest_url = ""
        close_page = False

        if video_id:
            embed_url = f"https://www.dailymotion.com/embed/video/{video_id}"

            if not page:
                try:
                    page = await browser_manager.new_page()
                    close_page = True
                except Exception as e:
                    logger.warning(f"Could not open Playwright page for Dailymotion embed: {e}")

            if page:
                async def on_resp(res):
                    nonlocal cdn_manifest_url
                    u = res.url
                    # Target direct VOD stream URLs (vod3.cf.dmcdn.net) over director URLs
                    if "vod" in u and ".m3u8" in u:
                        cdn_manifest_url = u
                    elif "cdndirector" in u and ".m3u8" in u and not cdn_manifest_url:
                        cdn_manifest_url = u

                page.on("response", on_resp)
                try:
                    await page.goto(embed_url, wait_until="networkidle", timeout=15000)
                    await page.wait_for_timeout(3000)
                except Exception as e:
                    logger.error(f"Playwright navigation error for Dailymotion embed: {e}")
                finally:
                    if close_page and page:
                        try:
                            await page.close()
                        except Exception:
                            pass

        # Fallback API request if Playwright didn't capture vod URL
        if not cdn_manifest_url and video_id:
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
                                    cdn_manifest_url = q_list[0]["url"]
                                    break
            except Exception as e:
                logger.error(f"Fallback Dailymotion player metadata error: {e}")

        logger.info(f"Resolved Dailymotion stream: {'SUCCESS' if cdn_manifest_url else 'FAILED'} -> {cdn_manifest_url[:100]}")

        return {
            "stream_url": cdn_manifest_url,
            "media_type": "hls",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.dailymotion.com/"
            },
            "subtitles": []
        }
