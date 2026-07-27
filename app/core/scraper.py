"""
Snapfy Plugin Registry & Auto-Detection Scraper Manager
"""

from typing import List, Optional
from app.plugins.base import BasePlugin
from app.plugins.netshort import NetShortPlugin
from app.plugins.dramabox import DramaBoxPlugin
from app.plugins.dailymotion import DailymotionPlugin
from app.plugins.generic import GenericPlugin
from app.core.logger import logger

class PluginManager:
    def __init__(self):
        self.plugins: List[BasePlugin] = []
        self.register_default_plugins()

    def register_default_plugins(self):
        self.register(NetShortPlugin())
        self.register(DramaBoxPlugin())
        self.register(DailymotionPlugin())
        # GenericPlugin is handled as fallback

    def register(self, plugin: BasePlugin):
        logger.info(f"Registered plugin: {plugin.name} [{plugin.platform_key}]")
        self.plugins.append(plugin)

    def detect_plugin(self, url: str) -> BasePlugin:
        for plugin in self.plugins:
            if plugin.can_handle(url):
                logger.info(f"Detected plugin {plugin.name} for URL: {url}")
                return plugin
        
        logger.info(f"No specific plugin matched. Falling back to GenericPlugin for URL: {url}")
        return GenericPlugin()

    async def scrape(self, url: str, page=None) -> dict:
        plugin = self.detect_plugin(url)
        return await plugin.scrape_series(url, page=page)

    async def resolve(self, episode_url: str, page=None) -> dict:
        plugin = self.detect_plugin(episode_url)
        return await plugin.resolve_stream(episode_url, page=page)

plugin_manager = PluginManager()
