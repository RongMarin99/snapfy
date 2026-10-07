"""
Snapfy Facebook Video & Reels Scraper Plugin
Supports downloading single Facebook reels/videos and batch extraction from page/profile reels & video lists.
Prioritizes High Quality (HD) stream resolution.
"""

import re
import json
import urllib.parse
import httpx
from bs4 import BeautifulSoup
from app.plugins.base import BasePlugin
from app.core.logger import logger
from app.core.browser import browser_manager
from app.core.settings import settings_manager

class FacebookPlugin(BasePlugin):
    name = "Facebook Video & Reels Scraper"
    platform_key = "Facebook"
    domain_patterns = ["facebook.com", "fb.watch", "fb.gg", "fb.com"]

    @classmethod
    def can_handle(cls, url: str) -> bool:
        url_lower = url.lower()
        return any(pat in url_lower for pat in cls.domain_patterns)

    def is_list_url(self, url: str) -> bool:
        """
        Determines if the given URL is a profile/page video list or reels list.
        """
        u = url.lower()
        # Is it a single reel / video link?
        if re.search(r'/(?:reel|videos)/\d+', u) or re.search(r'[?&]v=\d+', u) or re.search(r'/share/[rv]/\w+', u):
            return False
        
        # Check explicit list patterns or profile/page URLs
        if any(pat in u for pat in ["/reels", "/videos", "sk=reels", "sk=videos", "profile.php"]):
            return True
            
        # Any other channel/page URL that is not a single video
        return True

    def clean_fb_url(self, raw_url: str) -> str:
        if not raw_url:
            return ""
        u = raw_url.replace(r"\/", "/").replace("\\/", "/").replace(r"\u0025", "%")
        u = re.sub(r'\\u([0-9a-fa-f]{4})', lambda m: chr(int(m.group(1), 16)), u)
        u = u.replace("\\", "")
        return u

    def is_just_metric(self, text: str) -> bool:
        if not text:
            return True
        t = text.strip()
        if re.fullmatch(r'^\d+(?:\.\d+)?[KMkm]?$', t):
            return True
        if re.fullmatch(r'^\d+(?:\.\d+)?[KMkm]?\s*(?:views?|reactions?|likes?|comments?)$', t, re.IGNORECASE):
            return True
        return False

    def clean_fb_title(self, raw_title: str, fallback_url: str = "", profile_name: str = "") -> str:
        if not raw_title:
            title = ""
        else:
            title = raw_title.strip()

        # Ignore generic preview labels
        if title.lower() in ["reel tile preview", "tile preview", "reel preview"]:
            title = ""

        # Remove Facebook branding suffix
        title = re.sub(r'\s*\|\s*Facebook$', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*-\s*Facebook$', '', title, flags=re.IGNORECASE)

        # Remove metrics prefixes (e.g. "79K views · 4K reactions | War? | The Shadoows")
        title = re.sub(r'^\d+(?:\.\d+)?[KMkm]?\s+views\s*[\s|·•\-]*', '', title, flags=re.IGNORECASE)
        title = re.sub(r'^\d+(?:\.\d+)?[KMkm]?\s+reactions\s*[\s|·•\-]*', '', title, flags=re.IGNORECASE)
        title = re.sub(r'^\d+(?:\.\d+)?[KMkm]?\s+likes\s*[\s|·•\-]*', '', title, flags=re.IGNORECASE)
        title = re.sub(r'^\d+(?:\.\d+)?[KMkm]?\s+comments\s*[\s|·•\-]*', '', title, flags=re.IGNORECASE)
        title = re.sub(r'^\d+(?:\.\d+)?[KMkm]?\s+reactions\s*[\s|·•\-]*', '', title, flags=re.IGNORECASE)

        title = title.strip(" |·•-")

        # Fallback if empty, metric-only (e.g. "70K"), or generic
        if self.is_just_metric(title) or title.lower() in ["facebook", "log into facebook", "reels", "watch", "video", ""]:
            reel_id_m = re.search(r'/(?:reel|videos)/(\d+)', fallback_url)
            reel_id = reel_id_m.group(1) if reel_id_m else ""

            prefix = profile_name or "Facebook Reel"
            if reel_id:
                title = f"{prefix} #{reel_id}"
            else:
                title = f"{prefix}"

        return title

    def parse_json_blocks(self, html: str, key: str) -> list:
        """
        Safely extracts JSON array blocks for a given key (e.g. representations)
        handling nested brackets, escaped characters, and multi-line script tags.
        """
        results = []
        pattern = rf'"{key}"\s*:\s*\['
        for match in re.finditer(pattern, html):
            start_idx = match.end() - 1
            bracket_count = 0
            in_string = False
            escape = False
            end_idx = -1
            for i in range(start_idx, len(html)):
                char = html[i]
                if escape:
                    escape = False
                    continue
                if char == '\\':
                    escape = True
                    continue
                if char == '"':
                    in_string = not in_string
                    continue
                if not in_string:
                    if char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_idx = i + 1
                            break
            if end_idx != -1:
                json_str = html[start_idx:end_idx].replace(r'\"', '"')
                try:
                    data = json.loads(json_str)
                    results.append(data)
                except Exception:
                    try:
                        data = json.loads(json_str.encode('utf-8').decode('unicode_escape'))
                        results.append(data)
                    except Exception:
                        pass
        return results

    def extract_dash_audio_from_html(self, html: str) -> str:
        """Best audio-only DASH representation URL (Facebook DASH video tracks are silent or have truncated sound)."""
        best_url, best_bw = "", -1

        # 1. Check JSON representation blocks
        for key_name in ["representations", "audio_representations"]:
            blocks = self.parse_json_blocks(html, key_name)
            for reps in blocks:
                if isinstance(reps, list):
                    for r in reps:
                        if not isinstance(r, dict):
                            continue
                        mime = (r.get("mime_type") or "").lower()
                        codecs = (r.get("codecs") or "").lower()
                        is_audio = mime.startswith("audio") or "mp4a" in codecs or (not r.get("height") and not r.get("width") and "video" not in mime)
                        b_url = r.get("base_url") or r.get("url")
                        bw = r.get("bandwidth") or 0
                        if is_audio and b_url and bw > best_bw:
                            best_bw, best_url = bw, self.clean_fb_url(b_url)

        if best_url:
            return best_url

        # 2. Check DASH XML manifest representations if embedded
        dash_manifests = re.findall(r'"dash_manifest"\s*:\s*"([^"]+)"', html)
        for dm in dash_manifests:
            dm_clean = dm.replace(r'\"', '"').replace(r'\/', '/').replace(r'\n', '\n').replace('&amp;', '&')
            audio_reps = re.findall(r'<Representation[^>]*mimeType="audio/[^"]*"[^>]*>.*?<BaseURL>(.*?)</BaseURL>', dm_clean, re.DOTALL)
            if not audio_reps:
                audio_reps = re.findall(r'<Representation[^>]*codecs="mp4a[^"]*"[^>]*>.*?<BaseURL>(.*?)</BaseURL>', dm_clean, re.DOTALL)
            if audio_reps:
                return self.clean_fb_url(audio_reps[0])

        # 3. Check explicit audio patterns in JSON / HTML
        audio_patterns = [
            r'"audio_representation_url"\s*:\s*"([^"]+)"',
            r'"playable_url_quality_hd_audio"\s*:\s*"([^"]+)"',
            r'"audio_src"\s*:\s*"([^"]+)"',
            r'"audio_url"\s*:\s*"([^"]+)"',
        ]
        for pattern in audio_patterns:
            matches = re.findall(pattern, html)
            if matches:
                clean_u = self.clean_fb_url(matches[0])
                if clean_u and "fbcdn.net" in clean_u:
                    return clean_u

        return ""

    def extract_hd_stream_from_html(self, html: str) -> str:
        """
        Extracts high quality HD stream URL from Facebook HTML/JSON structures.
        """
        # 1. Look for explicit HD keys
        hd_patterns = [
            r'"browser_native_hd_url"\s*:\s*"([^"]+)"',
            r'"playable_url_quality_hd"\s*:\s*"([^"]+)"',
            r'"hd_src"\s*:\s*"([^"]+)"',
            r'"hd_src_no_ratelimit"\s*:\s*"([^"]+)"',
        ]
        for pattern in hd_patterns:
            matches = re.findall(pattern, html)
            if matches:
                clean_url = self.clean_fb_url(matches[0])
                if clean_url and "fbcdn.net" in clean_url:
                    return clean_url

        # 2. Check JSON representation blocks for max resolution height
        for key_name in ["representations", "video_representations"]:
            blocks = self.parse_json_blocks(html, key_name)
            best_url = ""
            max_height = 0
            for reps in blocks:
                if isinstance(reps, list):
                    for r in reps:
                        if not isinstance(r, dict):
                            continue
                        b_url = r.get("base_url") or r.get("url")
                        height = r.get("height", 0)
                        if b_url and height > max_height:
                            max_height = height
                            best_url = self.clean_fb_url(b_url)
            if best_url:
                return best_url

        # 3. Fallback to SD keys
        sd_patterns = [
            r'"browser_native_sd_url"\s*:\s*"([^"]+)"',
            r'"playable_url"\s*:\s*"([^"]+)"',
            r'"sd_src"\s*:\s*"([^"]+)"',
            r'"sd_src_no_ratelimit"\s*:\s*"([^"]+)"',
        ]
        for pattern in sd_patterns:
            matches = re.findall(pattern, html)
            if matches:
                clean_url = self.clean_fb_url(matches[0])
                if clean_url:
                    return clean_url

        # 4. Fallback to any direct fbcdn .mp4 link
        fbcdn_mp4s = re.findall(r'https?://[^\s\'"]*fbcdn\.net[^\s\'"]*\.mp4[^\s\'"]*', html)
        if fbcdn_mp4s:
            return self.clean_fb_url(fbcdn_mp4s[0])

        return ""

    async def scrape_series(self, url: str, page=None) -> dict:
        logger.scraper(f"Scraping Facebook URL: {url}")
        
        if self.is_list_url(url):
            return await self._scrape_list_page(url, page=page)
        else:
            return await self._scrape_single_video(url, page=page)

    async def _scrape_list_page(self, url: str, page=None) -> dict:
        close_page = False
        if not page:
            try:
                page = await browser_manager.new_page()
                close_page = True
            except Exception as e:
                logger.warning(f"Could not open browser page for Facebook list scrape: {e}")

        series_title = "Facebook Video Collection"
        thumbnail = ""
        episodes = []

        if page:
            try:
                logger.info(f"Navigating to Facebook list page: {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(3000)

                raw_page_title = await page.title()
                profile_name = ""
                if raw_page_title:
                    series_title = self.clean_fb_title(raw_page_title, url)
                    profile_name = re.sub(r'\s*\|\s*Facebook$', '', raw_page_title, flags=re.IGNORECASE).strip()
                    profile_name = re.sub(r'\s*Reels$', '', profile_name, flags=re.IGNORECASE).strip()

                # Dismiss login / cookie overlays that lock page scrolling
                try:
                    close_btns = await page.query_selector_all("[aria-label='Close'], [aria-label='close'], [aria-label='Decline optional cookies'], [aria-label='Allow all cookies']")
                    for btn in close_btns:
                        try:
                            await btn.click()
                            await page.wait_for_timeout(500)
                        except Exception:
                            pass
                    await page.keyboard.press("Escape")
                    await page.evaluate("document.body.style.overflow = 'auto';")
                    await page.wait_for_timeout(1000)
                except Exception as e:
                    logger.warning(f"Error dismissing Facebook modal overlays: {e}")

                # Deep adaptive scroll loop to collect ALL reels/videos
                seen_urls = set()
                title_counts = {}
                scroll_attempts_without_new = 0
                max_scroll_iterations = 60  # High limit to scrape full profile lists

                for iteration in range(max_scroll_iterations):
                    prev_count = len(episodes)
                    links = await page.query_selector_all("a[href]")

                    for l in links:
                        href = await l.get_attribute("href")
                        if not href:
                            continue

                        if "/reel/" in href or "/videos/" in href or "/watch" in href or "/share/r/" in href or "/share/v/" in href:
                            full_url = urllib.parse.urljoin("https://www.facebook.com", href)
                            clean_url = full_url.split("?")[0].rstrip("/")

                            if clean_url in seen_urls or clean_url.endswith("/reels") or clean_url.endswith("/videos"):
                                continue
                            seen_urls.add(clean_url)

                            aria = await l.get_attribute("aria-label") or ""
                            text = (await l.inner_text() or "").strip()

                            img = await l.query_selector("img")
                            img_src = await img.get_attribute("src") if img else ""

                            # Pick non-metric title candidate
                            raw_candidate = ""
                            for cand in [aria, text]:
                                if cand and not self.is_just_metric(cand):
                                    raw_candidate = cand
                                    break

                            ep_title = self.clean_fb_title(raw_candidate, clean_url, profile_name=profile_name)

                            # Guarantee title uniqueness by appending index number if duplicate
                            if ep_title in title_counts:
                                title_counts[ep_title] += 1
                                final_title = f"{ep_title} ({title_counts[ep_title]})"
                            else:
                                title_counts[ep_title] = 1
                                final_title = ep_title

                            if not thumbnail and img_src:
                                thumbnail = img_src

                            episodes.append({
                                "title": final_title,
                                "episode_num": len(episodes) + 1,
                                "url": clean_url,
                                "thumbnail": img_src or "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=500",
                                "platform": self.platform_key,
                                "status": "Waiting"
                            })

                    logger.info(f"Facebook list scroll [{iteration + 1}/{max_scroll_iterations}]: extracted {len(episodes)} total reels.")

                    if len(episodes) == prev_count:
                        scroll_attempts_without_new += 1
                        if scroll_attempts_without_new >= 5:
                            logger.info(f"Reached end of Facebook list page. Total reels extracted: {len(episodes)}")
                            break
                    else:
                        scroll_attempts_without_new = 0

                    await page.keyboard.press("PageDown")
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1800)

            except Exception as e:
                logger.error(f"Error scraping Facebook list page with Playwright: {e}")
            finally:
                if close_page and page:
                    try:
                        await page.close()
                    except Exception:
                        pass

        # Fallback if list scraping didn't yield episodes
        if not episodes:
            episodes = [{
                "title": series_title,
                "episode_num": 1,
                "url": url,
                "thumbnail": thumbnail or "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=500",
                "platform": self.platform_key,
                "status": "Waiting"
            }]

        return {
            "title": series_title,
            "thumbnail": thumbnail or "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=500",
            "platform": self.platform_key,
            "episodes": episodes
        }

    async def _scrape_single_video(self, url: str, page=None) -> dict:
        title = "Facebook Video"
        thumbnail = ""
        html = ""

        # Phase 1: Fast HTTP GET
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=12.0, verify=settings_manager.get("ssl_verify", True)) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    html = resp.text
                    soup = BeautifulSoup(html, "html.parser")
                    og_title = soup.find("meta", property="og:title")
                    og_desc = soup.find("meta", property="og:description")
                    og_image = soup.find("meta", property="og:image")

                    if og_title and og_title.get("content"):
                        title = og_title["content"]
                    elif og_desc and og_desc.get("content"):
                        title = og_desc["content"]

                    if og_image and og_image.get("content"):
                        thumbnail = og_image["content"]
        except Exception as e:
            logger.warning(f"HTTP fetch error during Facebook single video metadata scrape: {e}")

        title = self.clean_fb_title(title, url)

        # Phase 2: Playwright fallback if title/metadata was generic or empty
        if (not html or title in ["Facebook Video", "Facebook"]) and page:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                await page.wait_for_timeout(2000)
                p_title = await page.title()
                if p_title:
                    title = self.clean_fb_title(p_title, url)
                og_image = await page.query_selector("meta[property='og:image']")
                if og_image:
                    thumbnail = await og_image.get_attribute("content") or thumbnail
            except Exception as e:
                logger.warning(f"Playwright fallback warning for Facebook single video: {e}")

        episodes = [{
            "title": title,
            "episode_num": 1,
            "url": url,
            "thumbnail": thumbnail or "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=500",
            "platform": self.platform_key,
            "status": "Waiting"
        }]

        return {
            "title": title,
            "thumbnail": thumbnail or "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=500",
            "platform": self.platform_key,
            "episodes": episodes
        }

    async def resolve_stream(self, episode_url: str, page=None) -> dict:
        logger.scraper(f"Resolving Facebook HD stream for: {episode_url}")
        
        hd_stream_url = ""
        audio_url = ""
        close_page = False
        title = ""
        thumbnail = ""

        # Phase 1: Fast HTTP GET extraction
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=12.0, verify=settings_manager.get("ssl_verify", True)) as client:
                resp = await client.get(episode_url)
                if resp.status_code == 200:
                    html = resp.text
                    hd_stream_url = self.extract_hd_stream_from_html(html)
                    audio_url = self.extract_dash_audio_from_html(html)
        except Exception as e:
            logger.warning(f"Fast HTTP stream extraction failed for Facebook: {e}")

        # Phase 2: Playwright fallback with network stream capture if HTTP phase didn't yield video or audio streams
        if not hd_stream_url or not audio_url:
            captured_video_stream = ""
            captured_audio_stream = ""
            if not page:
                try:
                    page = await browser_manager.new_page()
                    close_page = True
                except Exception as e:
                    logger.warning(f"Could not open Playwright page for Facebook stream resolution: {e}")

            if page:
                async def on_resp(res):
                    nonlocal captured_video_stream, captured_audio_stream
                    u = res.url
                    ct = (res.headers.get("content-type") or "").lower()
                    if "fbcdn.net" in u:
                        if "audio" in ct or "mime=audio" in u or "codecs=mp4a" in u or "audio" in u.lower():
                            if not captured_audio_stream:
                                captured_audio_stream = u
                        elif "video" in ct or ".mp4" in u or "bytestart" in u:
                            if not captured_video_stream or "bytestart" in u:
                                captured_video_stream = u

                page.on("response", on_resp)
                try:
                    await page.goto(episode_url, wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(3000)
                    content = await page.content()
                    if not hd_stream_url:
                        hd_stream_url = self.extract_hd_stream_from_html(content)
                    if not audio_url:
                        audio_url = self.extract_dash_audio_from_html(content)
                    if not hd_stream_url:
                        hd_stream_url = captured_video_stream
                    if not audio_url and captured_audio_stream and captured_audio_stream != hd_stream_url:
                        audio_url = captured_audio_stream
                except Exception as e:
                    logger.error(f"Playwright navigation error resolving Facebook stream: {e}")
                finally:
                    if close_page and page:
                        try:
                            await page.close()
                        except Exception:
                            pass

        logger.info(f"Resolved Facebook stream: {'SUCCESS' if hd_stream_url else 'FAILED'} -> {hd_stream_url[:100] if hd_stream_url else 'None'}")

        return {
            "stream_url": hd_stream_url,
            "audio_url": audio_url if audio_url != hd_stream_url else "",
            "media_type": "mp4",
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": "https://www.facebook.com/"
            },
            "subtitles": []
        }
