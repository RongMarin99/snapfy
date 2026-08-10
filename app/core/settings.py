"""
Snapfy Core Settings Manager
"""

import os
import json
from pathlib import Path
from PySide6.QtCore import QObject

DEFAULT_SETTINGS = {
    "download_dir": str(Path.home() / "Downloads" / "Snapfy"),
    "max_threads": 4,
    "max_retries": 3,
    "timeout": 30,
    "proxy": "",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "cookies": {},
    "browser_headless": True,
    "gpu_acceleration": True,
    "ffmpeg_path": "ffmpeg",
    "auto_shutdown": False,
    "language": "EN",
    "theme": "Dark",
    "auto_convert_mp4": True,
    "download_subtitles": True,
    "netshort_api_key": "TRIAL-ANICHIN-2026",
    "ssl_verify": True,
    "auto_check_updates": True,
    "skipped_update_version": "",
    "simple_episode_filename": False,
    "clip_enabled": False,
    "clip_duration_minutes": 5,
    "clip_aspect_ratio": "9:16"
}

class SettingsManager(QObject):
    def __init__(self, config_dir: str = None):
        super().__init__()
        if config_dir is None:
            self.config_dir = Path.home() / ".snapfy"
        else:
            self.config_dir = Path(config_dir)
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "settings.json"
        self._settings = DEFAULT_SETTINGS.copy()
        self.load_settings()

    def load_settings(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._settings.update(data)
            except Exception as e:
                print(f"[SettingsManager] Failed to load config: {e}")

        # Ensure download directory exists
        os.makedirs(self._settings["download_dir"], exist_ok=True)

    def save_settings(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[SettingsManager] Failed to save config: {e}")

    def get(self, key: str, default=None):
        return self._settings.get(key, default)

    def set(self, key: str, value):
        self._settings[key] = value
        self.save_settings()

    def update(self, new_settings: dict):
        self._settings.update(new_settings)
        self.save_settings()

settings_manager = SettingsManager()
