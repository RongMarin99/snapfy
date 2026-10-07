import asyncio
import os
import shutil
import subprocess
from app.plugins.facebook import FacebookPlugin
from app.core.ffmpeg import ffmpeg_manager

def test_json_blocks():
    plugin = FacebookPlugin()
    sample_html = '''
    "browser_native_hd_url": "https://video.xx.fbcdn.net/v/hd_preview.mp4",
    "representations": [
        {"base_url": "https:\\/\\/video.xx.fbcdn.net\\/v\\/video_1080p.mp4", "mime_type": "video/mp4", "width": 1920, "height": 1080, "bandwidth": 5000000, "segment_durations": [10, 10, 10]},
        {"base_url": "https:\\/\\/video.xx.fbcdn.net\\/v\\/audio_full.mp4", "mime_type": "audio/mp4", "codecs": "mp4a.40.2", "bandwidth": 256000, "segment_durations": [10, 10, 10]}
    ]
    '''
    audio = plugin.extract_dash_audio_from_html(sample_html)
    video = plugin.extract_hd_stream_from_html(sample_html)
    print("Extracted Video URL:", video)
    print("Extracted Audio URL:", audio)
    assert "audio_full.mp4" in audio, f"Audio extraction failed: {audio}"
    assert "hd_preview.mp4" in video, f"Video extraction failed: {video}"
    print("FacebookPlugin extraction test PASSED!")

def test_ffmpeg_mux():
    ffmpeg = ffmpeg_manager.get_ffmpeg_path()
    if not shutil.which(ffmpeg):
        print("FFmpeg not found in PATH, skipping mux test.")
        return

    test_dir = "scratch/test_mux"
    os.makedirs(test_dir, exist_ok=True)
    v_file = os.path.join(test_dir, "video.mp4")
    a_file = os.path.join(test_dir, "audio.mp4")
    out_file = os.path.join(test_dir, "output.mp4")

    # Generate 10-second silent video
    subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=10", "-c:v", "libx264", v_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Generate 10-second sine wave audio
    subprocess.run([ffmpeg, "-y", "-f", "lavfi", "-i", "sine=f=440:d=10", "-c:a", "aac", a_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    success = ffmpeg_manager.mux_video_audio(v_file, a_file, out_file)
    print("Mux success:", success)
    assert success and os.path.exists(out_file) and os.path.getsize(out_file) > 0

    info = ffmpeg_manager.get_video_info(out_file)
    print("Muxed video info:", info)
    assert info["duration"] > 0
    print("FFmpeg muxing test PASSED!")

    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    test_json_blocks()
    test_ffmpeg_mux()
