import yt_dlp
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.ffmpeg import ffmpeg_manager

def test_download_yt(video_url, output_path):
    ffmpeg_path = ffmpeg_manager.get_ffmpeg_path()
    print("FFmpeg path:", ffmpeg_path)
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': False,
        'no_warnings': True,
        'ffmpeg_location': os.path.dirname(ffmpeg_path) if os.path.isabs(ffmpeg_path) else ffmpeg_path,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
        print("Download finished cleanly!")

if __name__ == "__main__":
    test_download_yt("https://www.youtube.com/shorts/G22BVF0U-XA", "downloads_test/test_short.mp4")
