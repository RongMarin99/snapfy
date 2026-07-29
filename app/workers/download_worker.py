"""
Snapfy Multi-Threaded Concurrent Download Worker Thread
"""

import os
import asyncio
from PySide6.QtCore import QThread, Signal
from app.core.downloader import DownloadEngine
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

                queue_manager.update_status(video_id, "Scraping Stream")

                # Resolve stream URL if missing
                stream_info = item.get("stream_info")
                if not stream_info or not stream_info.get("stream_url"):
                    stream_info = await plugin_manager.resolve(url)

                stream_url = stream_info.get("stream_url")
                media_type = stream_info.get("media_type", "mp4")

                if not stream_url:
                    logger.warning(f"Could not resolve stream URL for item {video_id}: {title}. (Episode may be locked/VIP)")
                    queue_manager.update_status(video_id, "🔒 Locked (Login Required)")
                    self.item_finished.emit(video_id, False)
                    return

                # Prepare safe output file path
                safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).rstrip()
                safe_title = safe_title or f"Video_{video_id}"
                out_filename = f"{safe_title}.mp4"
                output_file = os.path.join(download_dir, out_filename)

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

                if success:
                    logger.info(f"Successfully finished downloading item {video_id} -> {output_file}")
                    queue_manager.update_status(
                        video_id,
                        "Finished",
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
