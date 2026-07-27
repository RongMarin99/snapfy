"""
Snapfy NetShort Platform Plugin (High Performance Scraper & Stream Resolver)
"""

import re
import asyncio
import httpx
from bs4 import BeautifulSoup
from app.plugins.base import BasePlugin
from app.core.logger import logger
from app.core.browser import browser_manager
from app.core.settings import settings_manager

class NetShortPlugin(BasePlugin):
    name = "NetShort Scraper"
    platform_key = "NetShort"
    domain_patterns = ["netshort.com", "netshort.app", "netshort"]

    def _get_headers(self) -> dict:
        headers = {
            "User-Agent": settings_manager.get("user_agent"),
            "Referer": "https://netshort.com/"
        }
        user_cookie = settings_manager.get("cookie_string", "").strip()
        if user_cookie:
            headers["Cookie"] = user_cookie
        return headers

    async def scrape_series(self, url: str, page=None) -> dict:
        logger.scraper(f"Scraping NetShort Series URL: {url}")
        
        # Normalize base URL (strip episode numbers like -ep-2)
        base_url = re.sub(r'-ep-\d+$', '', url.rstrip('/'))

        close_page = False
        if not page:
            try:
                page = await browser_manager.new_page()
                close_page = True
            except Exception as e:
                logger.warning(f"Could not launch browser for NetShort scrape: {e}")

        clean_title = "NetShort Drama"
        cover_url = ""
        max_ep = 1

        if page:
            try:
                # Add cookie header to page context if available
                user_cookie = settings_manager.get("cookie_string", "").strip()
                if user_cookie and page.context:
                    try:
                        await page.context.set_extra_http_headers({"Cookie": user_cookie})
                    except Exception:
                        pass

                await page.goto(base_url, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(3500)

                # Extract page title
                title_text = await page.title()
                if title_text:
                    clean_title = title_text.replace("Online Watch - NetShort", "").replace("- NetShort", "").strip()

                # Extract thumbnail cover
                og_img = await page.query_selector("meta[property='og:image']")
                if og_img:
                    cover_url = await og_img.get_attribute("content") or ""

                # Discover max episode count from DOM links & text
                body_text = await page.inner_text("body")
                
                # Check link hrefs
                links = await page.query_selector_all("a[href*='episode']")
                for link in links:
                    href = await link.get_attribute("href") or ""
                    m = re.search(r'-ep-(\d+)', href)
                    if m:
                        num = int(m.group(1))
                        if num > max_ep:
                            max_ep = num

                # Check text pagination ranges like "61 - 62" or "1 - 30"
                range_matches = re.findall(r'\b(\d+)\s*-\s*(\d+)\b', body_text)
                for _, r_end in range_matches:
                    if int(r_end) > max_ep and int(r_end) < 400:
                        max_ep = int(r_end)

            except Exception as e:
                logger.error(f"Playwright scrape error on NetShort: {e}")
            finally:
                if close_page and page:
                    try:
                        await page.close()
                    except Exception:
                        pass

        # Fallback HTTP scraping if max_ep is 1
        if max_ep == 1:
            try:
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                    resp = await client.get(base_url, headers=self._get_headers())
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "lxml")
                        og_t = soup.find("meta", property="og:title")
                        if og_t and og_t.get("content"):
                            clean_title = og_t["content"].replace("Online Watch - NetShort", "").replace("- NetShort", "").strip()

                        og_i = soup.find("meta", property="og:image")
                        if og_i and og_i.get("content"):
                            cover_url = og_i["content"]

                        matches = re.findall(r'-ep-(\d+)', resp.text)
                        for m in matches:
                            if int(m) > max_ep:
                                max_ep = int(m)
            except Exception as e:
                logger.error(f"HTTP fallback scrape error on NetShort: {e}")

        logger.info(f"NetShort Plugin Discovered Drama: '{clean_title}' | Total Episodes: {max_ep}")

        # Build episode items array (Ep 1 to Ep N)
        episodes = []
        for ep_i in range(1, max_ep + 1):
            ep_url = base_url if ep_i == 1 else f"{base_url}-ep-{ep_i}"
            episodes.append({
                "title": f"{clean_title} - EP {ep_i:02d}",
                "episode_num": ep_i,
                "url": ep_url,
                "thumbnail": cover_url,
                "platform": self.platform_key,
                "status": "Waiting"
            })

        return {
            "title": clean_title,
            "thumbnail": cover_url,
            "platform": self.platform_key,
            "episodes": episodes
        }

    async def resolve_stream(self, episode_url: str, page=None) -> dict:
        logger.scraper(f"Resolving NetShort stream: {episode_url}")
        video_stream_url = ""
        close_page = False

        if not page:
            try:
                page = await browser_manager.new_page()
                close_page = True
            except Exception as e:
                logger.warning(f"Could not open browser for NetShort stream resolve: {e}")

        if page:
            # Set extra headers / cookie if available
            user_cookie = settings_manager.get("cookie_string", "").strip()
            if user_cookie and page.context:
                try:
                    await page.context.set_extra_http_headers({"Cookie": user_cookie})
                except Exception:
                    pass

            async def on_response(response):
                nonlocal video_stream_url
                u = response.url
                ct = response.headers.get("content-type", "")
                
                # Exclude telemetry / text_plain / lic files
                if "lic" not in u and "text_plain" not in u and not u.endswith(".lic"):
                    if "video/mp4" in ct or "mime_type=video_mp4" in u or ("cfcdn.netshort.com" in u and "video" in ct):
                        if not video_stream_url:
                            video_stream_url = u

            page.on("response", on_response)

            try:
                await page.goto(episode_url, wait_until="domcontentloaded", timeout=20000)
                
                # Attempt to click play button if needed
                play_btn = await page.query_selector("video, svg, button[class*='play']")
                if play_btn:
                    try:
                        await play_btn.click()
                    except Exception:
                        pass

                await page.wait_for_timeout(3500)

                # Check DOM video tag if not captured via network
                if not video_stream_url:
                    v_src = await page.evaluate('''() => {
                        const v = document.querySelector("video");
                        return v ? (v.src || v.currentSrc || "") : "";
                    }''')
                    if v_src and v_src.startswith("http") and "lic" not in v_src and "text_plain" not in v_src:
                        video_stream_url = v_src
            except Exception as e:
                logger.error(f"Error resolving NetShort stream via Playwright: {e}")
            finally:
                if close_page and page:
                    try:
                        await page.close()
                    except Exception:
                        pass

        # Fallback HTTP regex scan if stream still missing
        if not video_stream_url:
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    resp = await client.get(episode_url, headers=self._get_headers())
                    mp4_match = re.search(r'https?://[^\s\'"]+\.mp4[^\s\'"]*', resp.text)
                    if mp4_match and "lic" not in mp4_match.group(0) and "text_plain" not in mp4_match.group(0):
                        video_stream_url = mp4_match.group(0)
            except Exception as e:
                logger.error(f"HTTP fallback resolve failed for NetShort stream: {e}")

        logger.info(f"Resolved NetShort stream: {'SUCCESS' if video_stream_url else 'FAILED'} -> {video_stream_url[:100]}")

        return {
            "stream_url": video_stream_url,
            "media_type": "mp4",
            "headers": self._get_headers(),
            "subtitles": []
        }
