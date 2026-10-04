"""
Snapfy Core Multi-Threaded Async Downloader Engine (MP4 + HLS Multi-Segment Engine)
"""

import os
import re
import time
import asyncio
import urllib.parse
import httpx
from typing import Callable, Optional
from app.core.logger import logger
from app.core.settings import settings_manager
from app.core.proxy_pool import proxy_pool

# Hosts that rate-limit hard (e.g. the DramaBox decrypt-stream proxy endpoint) -
# direct downloads from these get proxy rotation + 429 retry; everything else
# (regular CDNs) downloads straight through, unproxied, as before.
RATE_LIMITED_HOSTS = {"api.sansekai.my.id"}

def sanitize_url(url: str) -> str:
    """
    Sanitizes URL string by stripping non-printable ASCII control characters (ASCII 0-31 and 127).
    Does not re-encode existing percent-encoded query parameters so signatures (e.g. YouTube sig/lsig) remain valid.
    """
    if not url:
        return ""
    return re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(url).strip())

class DownloadEngine:
    def __init__(self):
        self.is_paused = False
        self.is_cancelled = False

    async def download_direct(
        self,
        url: str,
        output_path: str,
        headers: dict = None,
        progress_callback: Optional[Callable[[float, float, str, str], None]] = None
    ) -> bool:
        """
        Downloads direct MP4/file resource with resume (Range header) and progress reports.
        progress_callback signature: (progress_percent, bytes_downloaded_mb, speed_str, eta_str)
        """
        url = sanitize_url(url)
        output_path = os.path.normpath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        base_headers = dict(headers or {})
        base_headers.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        base_headers.setdefault("Referer", "https://netshort.com/")

        verify = settings_manager.get("ssl_verify", True)
        is_rate_limited_host = urllib.parse.urlparse(url).hostname in RATE_LIMITED_HOSTS
        max_attempts = 6 if is_rate_limited_host else 1
        delay = 1.5

        for attempt in range(1, max_attempts + 1):
            request_headers = dict(base_headers)
            downloaded_bytes = 0
            if os.path.exists(output_path):
                downloaded_bytes = os.path.getsize(output_path)
                if downloaded_bytes > 0:
                    request_headers["Range"] = f"bytes={downloaded_bytes}-"

            start_time = time.time()
            last_time = start_time
            last_bytes = downloaded_bytes

            proxy = proxy_pool.get() if is_rate_limited_host else None

            try:
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True, verify=verify, proxy=proxy) as client:
                    async with client.stream("GET", url, headers=request_headers) as response:
                        if response.status_code == 429 and is_rate_limited_host:
                            if attempt == max_attempts:
                                logger.error(f"HTTP 429 while downloading {url} (out of retries)")
                                return False
                            retry_after = response.headers.get("Retry-After")
                            wait_s = float(retry_after) if retry_after and retry_after.isdigit() else delay
                            logger.warning(f"HTTP 429 downloading (rate limited), rotating proxy and retrying in {wait_s:.1f}s ({attempt}/{max_attempts})")
                            await asyncio.sleep(wait_s)
                            delay *= 1.7
                            continue

                        if response.status_code == 416 and "Range" in request_headers:
                            logger.warning(f"HTTP 416 Range Not Satisfiable for {url}. Restarting download without Range.")
                            request_headers.pop("Range", None)
                            downloaded_bytes = 0
                            if os.path.exists(output_path):
                                try:
                                    os.remove(output_path)
                                except Exception:
                                    pass
                            # Re-request fresh stream
                            async with client.stream("GET", url, headers=request_headers) as fresh_resp:
                                if fresh_resp.status_code not in (200, 206):
                                    logger.error(f"HTTP {fresh_resp.status_code} while downloading {url}")
                                    return False
                                response = fresh_resp
                                mode = "wb"
                                content_length = response.headers.get("content-length")
                                total_bytes = int(content_length) if content_length else 0
                        elif response.status_code not in (200, 206):
                            logger.error(f"HTTP {response.status_code} while downloading {url}")
                            return False

                        content_length = response.headers.get("content-length")
                        total_bytes = int(content_length) + downloaded_bytes if content_length else 0

                        mode = "ab" if downloaded_bytes > 0 and response.status_code == 206 else "wb"
                        if mode == "wb":
                            downloaded_bytes = 0

                        with open(output_path, mode) as f:
                            async for chunk in response.aiter_bytes(chunk_size=65536):
                                while self.is_paused:
                                    await asyncio.sleep(0.5)
                                    if self.is_cancelled:
                                        return False

                                if self.is_cancelled:
                                    return False

                                f.write(chunk)
                                downloaded_bytes += len(chunk)

                                now = time.time()
                                dt = now - last_time
                                if dt >= 0.5:
                                    speed_bps = (downloaded_bytes - last_bytes) / dt
                                    speed_mb = speed_bps / (1024 * 1024)
                                    speed_str = f"{speed_mb:.1f} MB/s" if speed_mb >= 1 else f"{speed_bps/1024:.1f} KB/s"

                                    if total_bytes > 0:
                                        progress = (downloaded_bytes / total_bytes * 100.0)
                                        remaining_bytes = max(0, total_bytes - downloaded_bytes)
                                        eta_secs = int(remaining_bytes / speed_bps) if speed_bps > 0 else 0
                                        eta_str = f"{eta_secs // 60:02d}:{eta_secs % 60:02d}"
                                    else:
                                        progress = 50.0
                                        eta_str = "Downloading"

                                    if progress_callback:
                                        progress_callback(
                                            progress,
                                            downloaded_bytes / (1024 * 1024),
                                            speed_str,
                                            eta_str
                                        )

                                    last_time = now
                                    last_bytes = downloaded_bytes

                if progress_callback:
                    progress_callback(100.0, downloaded_bytes / (1024 * 1024), "Finished", "00:00")
                return downloaded_bytes > 0 and os.path.exists(output_path)

            except httpx.HTTPError as e:
                if is_rate_limited_host:
                    proxy_pool.report_failure(proxy)
                    if attempt < max_attempts:
                        logger.warning(f"Proxy connect error downloading: {e}. Rotating proxy ({attempt}/{max_attempts})")
                        await asyncio.sleep(0.5)
                        continue
                logger.error(f"Direct download error: {e}")
                return False
            except Exception as e:
                logger.error(f"Direct download error: {e}")
                return False

        return False

    async def download_hls(
        self,
        m3u8_url: str,
        output_mp4: str,
        headers: dict = None,
        progress_callback: Optional[Callable[[float, float, str, str], None]] = None
    ) -> bool:
        """
        Downloads HLS .m3u8 stream by resolving segments and stitching into output_mp4.
        """
        m3u8_url = sanitize_url(m3u8_url)
        output_mp4 = os.path.normpath(output_mp4)
        os.makedirs(os.path.dirname(output_mp4), exist_ok=True)

        headers = headers or {}
        headers.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        headers.setdefault("Referer", "https://www.dailymotion.com/")

        logger.info(f"Starting HLS download for: {m3u8_url[:80]}")
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=settings_manager.get("ssl_verify", True)) as client:
                r = await client.get(m3u8_url, headers=headers)
                if r.status_code != 200 or not r.text.strip():
                    logger.error(f"HLS manifest request failed. Status: {r.status_code}")
                    return False

                playlist_text = r.text
                lines = [line.strip() for line in playlist_text.splitlines() if line.strip()]

                # Check if master playlist containing sub-playlists
                sub_playlists = [line for line in lines if not line.startswith("#") and (".m3u8" in line or "manifest" in line)]
                target_playlist = m3u8_url

                if sub_playlists:
                    last_sub = sanitize_url(sub_playlists[-1])
                    target_playlist = urllib.parse.urljoin(m3u8_url, last_sub)
                    r_sub = await client.get(sanitize_url(target_playlist), headers=headers)
                    if r_sub.status_code == 200:
                        playlist_text = r_sub.text

                base_cdn = target_playlist.rsplit('/', 1)[0]
                seg_lines = [line.strip() for line in playlist_text.splitlines() if line.strip() and not line.startswith("#")]
                
                # Check init.mp4 segment if fmp4 format
                has_init = any("init.mp4" in line for line in playlist_text.splitlines())

                segments = []
                for s in seg_lines:
                    clean_s = sanitize_url(s)
                    if clean_s.startswith("http"):
                        segments.append(clean_s)
                    else:
                        full_u = urllib.parse.urljoin(target_playlist, clean_s)
                        segments.append(sanitize_url(full_u))

                total_segments = len(segments)
                logger.info(f"HLS Stream Discovered {total_segments} segment(s)")

                if total_segments == 0:
                    logger.error("No segments found in HLS playlist.")
                    return False

                # Prepare output file
                with open(output_mp4, "wb") as outfile:
                    # Write init.mp4 header if available
                    if has_init:
                        init_url = sanitize_url(f"{base_cdn}/init.mp4")
                        try:
                            init_res = await client.get(init_url, headers=headers)
                            if init_res.status_code == 200:
                                outfile.write(init_res.content)
                        except Exception as e:
                            logger.warning(f"Could not fetch HLS init.mp4: {e}")

                    downloaded_bytes = 0
                    last_time = time.time()
                    last_bytes = 0

                    for idx, seg_url in enumerate(segments, 1):
                        while self.is_paused:
                            await asyncio.sleep(0.5)
                            if self.is_cancelled:
                                return False

                        if self.is_cancelled:
                            return False

                        clean_seg_url = sanitize_url(seg_url)
                        seg_fetched = False
                        for seg_attempt in range(1, 4):
                            try:
                                res_seg = await client.get(clean_seg_url, headers=headers)
                                if res_seg.status_code in (200, 206):
                                    outfile.write(res_seg.content)
                                    downloaded_bytes += len(res_seg.content)
                                    seg_fetched = True
                                    break
                            except Exception as e:
                                if seg_attempt < 3:
                                    await asyncio.sleep(0.3 * seg_attempt)
                                else:
                                    logger.warning(f"Error fetching segment {idx}: {e}")

                        # Report progress
                        now = time.time()
                        dt = now - last_time
                        if dt >= 0.5 or idx == total_segments:
                            speed_bps = (downloaded_bytes - last_bytes) / dt if dt > 0 else 0
                            speed_mb = speed_bps / (1024 * 1024)
                            speed_str = f"{speed_mb:.1f} MB/s" if speed_mb >= 1 else f"{speed_bps/1024:.1f} KB/s"
                            
                            progress_pct = (idx / total_segments) * 100.0
                            rem_segs = max(0, total_segments - idx)
                            avg_sec_per_seg = (now - start_time) / idx if idx > 0 else 0
                            eta_secs = int(rem_segs * avg_sec_per_seg)
                            eta_str = f"{eta_secs // 60:02d}:{eta_secs % 60:02d}"

                            if progress_callback:
                                progress_callback(
                                    progress_pct,
                                    downloaded_bytes / (1024 * 1024),
                                    speed_str,
                                    eta_str
                                )

                            last_time = now
                            last_bytes = downloaded_bytes

            final_size = os.path.getsize(output_mp4) if os.path.exists(output_mp4) else 0
            logger.info(f"HLS Download finished: {output_mp4} ({final_size / (1024*1024):.2f} MB)")
            
            if progress_callback:
                progress_callback(100.0, final_size / (1024 * 1024), "Finished", "00:00")
            
            return final_size > 0

        except Exception as e:
            logger.error(f"HLS download fatal error: {e}")
            return False
