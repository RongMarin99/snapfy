"""
Snapfy FFmpeg Helper & Segment Merger
"""

import os
import shutil
import subprocess
from pathlib import Path
from app.core.logger import logger
from app.core.settings import settings_manager

class FFmpegManager:
    @staticmethod
    def get_ffmpeg_path() -> str:
        custom_path = settings_manager.get("ffmpeg_path", "ffmpeg")
        if custom_path and shutil.which(custom_path):
            return custom_path
        
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            return system_ffmpeg
        
        return "ffmpeg"  # Hope it's on system PATH

    @classmethod
    def is_available(cls) -> bool:
        path = cls.get_ffmpeg_path()
        try:
            res = subprocess.run([path, "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            return res.returncode == 0
        except Exception:
            return False

    @classmethod
    def merge_ts_segments(cls, ts_files: list[str], output_mp4: str) -> bool:
        """
        Merges a list of .ts segment files into a single .mp4 file.
        Uses FFmpeg concat demuxer if available, or direct binary concatenation as fallback.
        """
        if not ts_files:
            logger.error("No TS files to merge.")
            return False

        os.makedirs(os.path.dirname(output_mp4), exist_ok=True)
        ffmpeg_cmd = cls.get_ffmpeg_path()

        if cls.is_available():
            logger.info(f"Merging {len(ts_files)} TS segments using FFmpeg...")
            # Create a file list for concat demuxer
            concat_list_path = output_mp4 + ".concat.txt"
            try:
                with open(concat_list_path, "w", encoding="utf-8") as f:
                    for ts_file in ts_files:
                        abs_p = os.path.abspath(ts_file).replace("\\", "/")
                        f.write(f"file '{abs_p}'\n")

                cmd = [
                    ffmpeg_cmd,
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", concat_list_path,
                    "-c", "copy",
                    "-bsf:a", "aac_adtstoasc",
                    output_mp4
                ]
                
                creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creation_flags)
                
                # Cleanup concat file
                if os.path.exists(concat_list_path):
                    os.remove(concat_list_path)

                if proc.returncode == 0 and os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 0:
                    logger.info(f"FFmpeg merge successful -> {output_mp4}")
                    return True
                else:
                    logger.warning(f"FFmpeg returned non-zero code {proc.returncode}. Fallback to binary join.")
            except Exception as e:
                logger.error(f"FFmpeg execution error: {e}")

        # Fallback: Binary TS Concatenation
        logger.info("Executing binary TS segment join fallback...")
        try:
            with open(output_mp4, "wb") as outfile:
                for ts_file in ts_files:
                    if os.path.exists(ts_file):
                        with open(ts_file, "rb") as infile:
                            shutil.copyfileobj(infile, outfile)
            logger.info(f"Binary segment join finished -> {output_mp4}")
            return True
        except Exception as e:
            logger.error(f"Binary merge failed: {e}")
            return False

ffmpeg_manager = FFmpegManager()
