"""
Snapfy Chromium Automation & Playwright Browser Manager with Automatic Connection Healing & Cookie Import
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from app.core.logger import logger
from app.core.settings import settings_manager

class BrowserManager:
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    def get_storage_state_file(self) -> str:
        state_file = Path.home() / ".snapfy" / "storage_state.json"
        return str(state_file)

    def clear_session_storage(self):
        state_file = self.get_storage_state_file()
        if os.path.exists(state_file):
            try:
                os.remove(state_file)
                logger.info("Cleared browser session storage state.")
            except Exception as e:
                logger.error(f"Error clearing session storage: {e}")

    def import_cookies(self, cookie_input: str) -> bool:
        """
        Parses raw Cookie header string or JSON array and converts to Playwright storage_state.json.
        """
        state_file = self.get_storage_state_file()
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        cookie_list = []

        cookie_input = cookie_input.strip()

        # Check if JSON array
        if cookie_input.startswith("[") and cookie_input.endswith("]"):
            try:
                raw_json = json.loads(cookie_input)
                for item in raw_json:
                    if isinstance(item, dict) and "name" in item and "value" in item:
                        cookie_list.append({
                            "name": item["name"],
                            "value": str(item["value"]),
                            "domain": item.get("domain", ".netshort.com"),
                            "path": item.get("path", "/"),
                            "expires": item.get("expires", -1),
                            "httpOnly": item.get("httpOnly", False),
                            "secure": item.get("secure", True),
                            "sameSite": "Lax"
                        })
            except Exception as e:
                logger.error(f"Error parsing JSON cookies: {e}")

        # Check if Netscape or header key=val string
        if not cookie_list:
            pairs = cookie_input.split(";")
            for pair in pairs:
                if "=" in pair:
                    parts = pair.strip().split("=", 1)
                    k = parts[0].strip()
                    v = parts[1].strip()
                    if k:
                        cookie_list.append({
                            "name": k,
                            "value": v,
                            "domain": ".netshort.com",
                            "path": "/",
                            "expires": -1,
                            "httpOnly": False,
                            "secure": True,
                            "sameSite": "Lax"
                        })

        if cookie_list:
            storage_data = {
                "cookies": cookie_list,
                "origins": []
            }
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(storage_data, f, indent=2)
            logger.info(f"Successfully imported {len(cookie_list)} cookies into {state_file}")
            return True
        return False

    def is_active(self) -> bool:
        return (
            self.playwright is not None and
            self.browser is not None and
            self.browser.is_connected() and
            self.context is not None
        )

    async def start(self, force_headful: bool = False):
        if not self.is_active():
            # Reset stale handles
            self.context = None
            self.browser = None
            self.playwright = None

            try:
                self.playwright = await async_playwright().start()
                headless = False if force_headful else settings_manager.get("browser_headless", True)
                user_agent = settings_manager.get("user_agent")
                
                logger.info(f"Launching Playwright Chromium (headless={headless})...")
                
                args = [
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-web-security",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--ignore-certificate-errors"
                ]

                try:
                    self.browser = await self.playwright.chromium.launch(
                        headless=headless,
                        channel="chrome",
                        args=args
                    )
                except Exception:
                    self.browser = await self.playwright.chromium.launch(
                        headless=headless,
                        args=args
                    )

                storage_state = self.get_storage_state_file()
                loaded_state = False
                if os.path.exists(storage_state):
                    try:
                        logger.info("Loading saved browser session cookies & tokens...")
                        self.context = await self.browser.new_context(
                            storage_state=storage_state,
                            user_agent=user_agent,
                            viewport={"width": 1280, "height": 800}
                        )
                        loaded_state = True
                    except Exception as err:
                        logger.warning(f"Storage state invalid or corrupted: {err}. Starting clean context.")
                        self.clear_session_storage()

                if not loaded_state:
                    self.context = await self.browser.new_context(
                        user_agent=user_agent,
                        viewport={"width": 1280, "height": 800}
                    )

                await self.context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            except Exception as e:
                logger.error(f"Failed to launch Playwright Chromium: {e}")

    async def save_session(self):
        if self.is_active():
            try:
                state_file = self.get_storage_state_file()
                os.makedirs(os.path.dirname(state_file), exist_ok=True)
                await self.context.storage_state(path=state_file)
                logger.info(f"Saved browser session storage state to {state_file}")
            except Exception as e:
                logger.error(f"Failed to save session state: {e}")

    async def new_page(self, force_headful: bool = False) -> Optional[Page]:
        if not self.is_active():
            await self.start(force_headful=force_headful)

        if self.is_active():
            try:
                page = await self.context.new_page()
                await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                return page
            except Exception:
                # Connection dropped, heal & restart context
                self.context = None
                self.browser = None
                self.playwright = None
                await self.start(force_headful=force_headful)
                if self.is_active():
                    page = await self.context.new_page()
                    await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                    return page
        return None

    async def open_interactive_browser(self, url: str = "https://netshort.com"):
        """
        Opens a visible browser window for interactive session login.
        """
        logger.info(f"Opening interactive browser window for {url}...")
        p = None
        try:
            p = await async_playwright().start()
            args = [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars"
            ]

            try:
                browser = await p.chromium.launch(headless=False, channel="chrome", args=args)
            except Exception:
                browser = await p.chromium.launch(headless=False, args=args)

            storage_state = self.get_storage_state_file()
            if os.path.exists(storage_state):
                try:
                    ctx = await browser.new_context(
                        storage_state=storage_state,
                        user_agent=settings_manager.get("user_agent")
                    )
                except Exception:
                    ctx = await browser.new_context(user_agent=settings_manager.get("user_agent"))
            else:
                ctx = await browser.new_context(user_agent=settings_manager.get("user_agent"))

            await ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page = await ctx.new_page()
            await page.goto(url)

            # Wait until user closes the window
            try:
                while len(ctx.pages) > 0:
                    await asyncio.sleep(1.0)
            except Exception:
                pass

            # Save cookies before exit
            try:
                await ctx.storage_state(path=storage_state)
                logger.info("Interactive session saved successfully!")
            except Exception as e:
                logger.error(f"Error saving interactive session: {e}")

            await browser.close()
        except Exception as e:
            logger.error(f"Error in interactive browser session: {e}")
        finally:
            if p:
                try:
                    await p.stop()
                except Exception:
                    pass

browser_manager = BrowserManager()
