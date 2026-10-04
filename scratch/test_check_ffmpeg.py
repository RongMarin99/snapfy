import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.ffmpeg import ffmpeg_manager

if __name__ == "__main__":
    path = ffmpeg_manager.get_ffmpeg_path()
    avail = ffmpeg_manager.is_available()
    print("FFmpeg path:", path)
    print("Is FFmpeg available:", avail)
