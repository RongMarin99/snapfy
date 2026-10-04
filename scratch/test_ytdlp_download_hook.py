import yt_dlp
import time

def progress_hook(d):
    if d['status'] == 'downloading':
        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
        downloaded = d.get('downloaded_bytes', 0)
        speed = d.get('speed') or 0
        eta = d.get('eta') or 0
        
        pct = (downloaded / total * 100.0) if total > 0 else 0.0
        speed_mb = speed / (1024 * 1024) if speed else 0.0
        speed_str = f"{speed_mb:.1f} MB/s" if speed_mb >= 1 else f"{(speed or 0)/1024:.1f} KB/s"
        eta_str = f"{eta // 60:02d}:{eta % 60:02d}" if eta else "--:--"

        print(f"\rProgress: {pct:.1f}% | Size: {downloaded/(1024*1024):.1f}MB | Speed: {speed_str} | ETA: {eta_str}", end="")

def download_youtube_video(video_url: str, output_path: str):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [progress_hook],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
        print("\nDownload complete!")

if __name__ == "__main__":
    download_youtube_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "downloads_test/rickroll.mp4")
