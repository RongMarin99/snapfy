from app.core.ffmpeg import ffmpeg_manager

print("FFmpeg path:", ffmpeg_manager.get_ffmpeg_path())
print("FFprobe path:", ffmpeg_manager.get_ffprobe_path())
print("Is FFmpeg available:", ffmpeg_manager.is_available())
