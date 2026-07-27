"""
Snapfy Core Multi-Threaded Async Downloader Engine (MP4 + HLS Multi-Segment Engine)
"""

import os
import time
import asyncio
import urllib.parse
import httpx
from typing import Callable, Optional
from app.core.logger import logger
from app.core.ffmpeg import ffmpeg_manager

class DownloadEngine:
    def __init__(self):
        self.is_paused = False
        self.is_cancelled = False

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def cancel(self):
        self.is_cancelled = True

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
        output_path = os.path.normpath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        headers = headers or {}
        headers.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        headers.setdefault("Referer", "https://netshort.com/")

        downloaded_bytes = 0
        if os.path.exists(output_path):
            downloaded_bytes = os.path.getsize(output_path)
            if downloaded_bytes > 0:
                headers["Range"] = f"bytes={downloaded_bytes}-"

        start_time = time.time()
        last_time = start_time
        last_bytes = downloaded_bytes

        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                async with client.stream("GET", url, headers=headers) as response:
                    if response.status_code not in (200, 206):
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

        except Exception as e:
            logger.error(f"Direct download error: {e}")
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
        output_mp4 = os.path.normpath(output_mp4)
        os.makedirs(os.path.dirname(output_mp4), exist_ok=True)

        headers = headers or {}
        headers.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        headers.setdefault("Referer", "https://www.dailymotion.com/")

        logger.info(f"Starting HLS download for: {m3u8_url[:80]}")
        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
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
                    last_sub = sub_playlists[-1]
                    target_playlist = urllib.parse.urljoin(m3u8_url, last_sub)
                    r_sub = await client.get(target_playlist, headers=headers)
                    if r_sub.status_code == 200:
                        playlist_text = r_sub.text

                base_cdn = target_playlist.rsplit('/', 1)[0]
                seg_lines = [line.strip() for line in playlist_text.splitlines() if line.strip() and not line.startswith("#")]
                
                # Check init.mp4 segment if fmp4 format
                has_init = any("init.mp4" in line for line in playlist_text.splitlines())

                segments = []
                for s in seg_lines:
                    if s.startswith("http"):
                        segments.append(s)
                    else:
                        segments.append(f"{base_cdn}/{s}")

                total_segments = len(segments)
                logger.info(f"HLS Stream Discovered {total_segments} segment(s)")

                if total_segments == 0:
                    logger.error("No segments found in HLS playlist.")
                    return False

                # Prepare output file
                with open(output_mp4, "wb") as outfile:
                    # Write init.mp4 header if available
                    if has_init:
                        init_url = f"{base_cdn}/init.mp4"
                        try:
                            init_res = await client.get(init_url, headers=headers)
                            if init_res.status_code == 200:
                                outfile.write(init_res.content)
                        except Exception as e:
                            logger.warning(f"Could not fetch HLS init.mp4: {e}")

                    downloaded_bytes = 0
                    last_time = time.time()
                    last_bytes = 0

                    sem = asyncio.Semaphore(6)

                    for idx, seg_url in enumerate(segments, 1):
                        while self.is_paused:
                            await asyncio.sleep(0.5)
                            if self.is_cancelled:
                                return False

                        if self.is_cancelled:
                            return False

                        try:
                            res_seg = await client.get(seg_url, headers=headers)
                            if res_seg.status_code == 200:
                                outfile.write(res_seg.content)
                                downloaded_bytes += len(res_seg.content)
                        except Exception as e:
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
