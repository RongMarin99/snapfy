"""
Snapfy Multi-Threaded Concurrent Download Worker Thread
"""

import os
import asyncio
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from app.core.downloader import DownloadEngine
from app.core.ffmpeg import ffmpeg_manager
from app.core.scraper import plugin_manager
from app.core.queue import queue_manager
from app.core.settings import settings_manager
from app.core.logger import logger

class DownloadWorker(QThread):
    item_finished = Signal(int, bool)  # (video_id, is_success)
    all_finished = Signal()

    def __init__(self, video_items: list[dict]):
        super().__init__()
        self.video_items = video_items
        self.is_running = True

    def stop(self):
        self.is_running = False

    def run(self):
        logger.info(f"Starting download worker for {len(self.video_items)} queued item(s)...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self._process_queue_concurrently())
        except Exception as e:
            logger.error(f"Download worker fatal exception: {e}")
        finally:
            loop.close()
            self.all_finished.emit()

    async def _process_queue_concurrently(self):
        download_dir = settings_manager.get("download_dir")
        max_threads = settings_manager.get("max_threads", 4)
        semaphore = asyncio.Semaphore(max_threads)

        async def download_single_item(item: dict):
            async with semaphore:
                if not self.is_running:
                    return

                video_id = item["id"]
                url = item["url"]
                title = item.get("title", f"Video_{video_id}")
                episode_num = item.get("episode_num")

                queue_manager.update_status(video_id, "Scraping Stream")

                # Always resolve stream URL fresh before downloading to prevent HTTP 403 link expiration
                stream_info = await plugin_manager.resolve(url)
                stream_url = stream_info.get("stream_url")
                media_type = stream_info.get("media_type", "mp4")

                if not stream_url:
                    logger.warning(f"Could not resolve stream URL for item {video_id}: {title}. (Episode may be locked/VIP)")
                    queue_manager.update_status(video_id, "🔒 Locked (Login Required)")
                    self.item_finished.emit(video_id, False)
                    return

                # Prepare safe output file path
                if settings_manager.get("simple_episode_filename", False) and episode_num:
                    out_filename = f"{int(episode_num):02d}.mp4"
                else:
                    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).rstrip()
                    safe_title = safe_title or f"Video_{video_id}"
                    out_filename = f"{safe_title}.mp4"
                
                output_file = os.path.join(download_dir, out_filename)

                # Uniquify output path if file already exists to avoid replacing existing videos
                counter = 1
                base_stem, ext = os.path.splitext(output_file)
                while os.path.exists(output_file):
                    output_file = f"{base_stem}_{counter}{ext}"
                    counter += 1

                queue_manager.update_status(video_id, "Downloading", progress=0.0, speed="0 KB/s")

                engine = DownloadEngine()

                def on_progress(progress_pct, bytes_mb, speed_str, eta_str):
                    queue_manager.update_status(
                        video_id,
                        "Downloading",
                        progress=progress_pct,
                        speed=speed_str,
                        eta=eta_str,
                        file_size=bytes_mb
                    )

                success = False
                audio_url = stream_info.get("audio_url")
                audio_headers = stream_info.get("headers")
                if media_type == "hls":
                    success = await engine.download_hls(
                        stream_url,
                        output_file,
                        headers=stream_info.get("headers"),
                        progress_callback=on_progress
                    )
                else:
                    success = await engine.download_direct(
                        stream_url,
                        output_file,
                        headers=stream_info.get("headers"),
                        progress_callback=on_progress
                    )

                # Auto-retry with a fresh stream resolution if first attempt failed (e.g. HTTP 403 expired manifest)
                if not success:
                    logger.warning(f"Download initial attempt failed for item {video_id} ({title}). Attempting fresh re-resolution...")
                    fresh_info = await plugin_manager.resolve(url)
                    fresh_stream_url = fresh_info.get("stream_url")
                    if fresh_stream_url:
                        fresh_media_type = fresh_info.get("media_type", "mp4")
                        # Old audio URL expired too; use the fresh pair.
                        media_type = fresh_media_type
                        audio_url = fresh_info.get("audio_url")
                        audio_headers = fresh_info.get("headers")
                        if fresh_media_type == "hls":
                            success = await engine.download_hls(
                                fresh_stream_url,
                                output_file,
                                headers=fresh_info.get("headers"),
                                progress_callback=on_progress
                            )
                        else:
                            success = await engine.download_direct(
                                fresh_stream_url,
                                output_file,
                                headers=fresh_info.get("headers"),
                                progress_callback=on_progress
                            )

                # Video-only source (e.g. YouTube adaptive): fetch audio track separately and mux.
                if success and audio_url and media_type != "hls":
                    audio_file = output_file + ".audio"
                    muxed_file = output_file + ".muxed.mp4"
                    audio_ok = await engine.download_direct(
                        audio_url, audio_file,
                        headers=audio_headers,
                        progress_callback=on_progress
                    )
                    if audio_ok:
                        queue_manager.update_status(video_id, "Finalizing", progress=100.0, speed="Merging audio...", eta="--:--")
                        merged = await asyncio.to_thread(ffmpeg_manager.mux_video_audio, output_file, audio_file, muxed_file)
                        if merged:
                            os.replace(muxed_file, output_file)
                        else:
                            logger.warning(f"Audio mux failed for item {video_id}; file has no sound.")
                    else:
                        logger.warning(f"Audio download failed for item {video_id}; file has no sound.")
                    for tmp in (audio_file, muxed_file):
                        if os.path.exists(tmp):
                            try:
                                os.remove(tmp)
                            except OSError:
                                pass

                if success:
                    logger.info(f"Successfully finished downloading item {video_id} -> {output_file}")

                    # Fix up container duration metadata: HLS downloads are built by
                    # writing raw concatenated segments to disk, which many players
                    # can play but show no duration/seek bar for (no proper moov index).
                    queue_manager.update_status(video_id, "Finalizing", progress=100.0, speed="Fixing metadata...", eta="--:--")
                    await asyncio.to_thread(ffmpeg_manager.fix_duration_metadata, output_file)

                    final_status = "Finished"
                    if settings_manager.get("clip_enabled", False):
                        clip_seconds = max(1, int(settings_manager.get("clip_duration_minutes", 5))) * 60
                        clip_ratio = settings_manager.get("clip_aspect_ratio", "9:16")
                        clip_dir = os.path.join(os.path.dirname(output_file), f"{Path(output_file).stem}_clips")

                        def on_clip_progress(done: int, total: int):
                            queue_manager.update_status(
                                video_id,
                                f"Clipping ({done}/{total})",
                                progress=(done / total) * 100.0 if total else 0.0,
                                speed="Clipping...",
                                eta="--:--"
                            )

                        queue_manager.update_status(video_id, "Clipping (0/?)", progress=0.0, speed="Clipping...", eta="--:--")
                        clip_paths = await asyncio.to_thread(
                            ffmpeg_manager.split_video_into_clips,
                            output_file, clip_dir, clip_seconds, clip_ratio, on_clip_progress
                        )
                        if clip_paths:
                            logger.info(f"Created {len(clip_paths)} clip(s) for item {video_id} -> {clip_dir}")
                            final_status = f"Finished ({len(clip_paths)} clips)"
                        else:
                            logger.warning(f"Clipping produced no output for item {video_id}; keeping original file only.")

                    queue_manager.update_status(
                        video_id,
                        final_status,
                        progress=100.0,
                        speed="Finished",
                        eta="00:00",
                        file_path=output_file
                    )
                    self.item_finished.emit(video_id, True)
                else:
                    logger.error(f"Download failed for item {video_id}")
                    queue_manager.update_status(video_id, "Failed")
                    self.item_finished.emit(video_id, False)

        tasks = [download_single_item(item) for item in self.video_items]
        await asyncio.gather(*tasks)
