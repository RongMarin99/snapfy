"""
Snapfy Background Scrape QThread Worker
"""

import asyncio
from PySide6.QtCore import QThread, Signal
from app.core.scraper import plugin_manager
from app.core.browser import browser_manager
from app.core.logger import logger

class ScrapeWorker(QThread):
    scrape_started = Signal(str)
    scrape_finished = Signal(dict)
    scrape_failed = Signal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        self.scrape_started.emit(self.url)
        logger.info(f"Starting background scrape task for: {self.url}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            res = loop.run_until_complete(self._do_scrape())
            self.scrape_finished.emit(res)
        except Exception as e:
            logger.error(f"Scrape worker execution error: {e}")
            self.scrape_failed.emit(str(e))
        finally:
            loop.close()

    async def _do_scrape(self) -> dict:
        page = None
        try:
            # Try to get browser page if Playwright works
            page = await browser_manager.new_page()
        except Exception as e:
            logger.warning(f"Could not open browser page: {e}")

        try:
            return await plugin_manager.scrape(self.url, page=page)
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
