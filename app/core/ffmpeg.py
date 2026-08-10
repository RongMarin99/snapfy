"""
Snapfy FFmpeg Helper & Segment Merger
"""

import os
import json
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
    def get_ffprobe_path(cls) -> str:
        # ffprobe normally ships alongside ffmpeg in the same directory.
        ffmpeg_path = cls.get_ffmpeg_path()
        candidate = str(Path(ffmpeg_path).with_name(
            "ffprobe.exe" if os.name == "nt" else "ffprobe"
        ))
        if shutil.which(candidate) or os.path.isfile(candidate):
            return candidate

        system_ffprobe = shutil.which("ffprobe")
        return system_ffprobe or "ffprobe"

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

    @classmethod
    def fix_duration_metadata(cls, input_path: str) -> bool:
        """
        Remuxes input_path in place (stream copy, no re-encode) so the container
        carries a proper duration/moov atom. Needed because HLS downloads are built
        by concatenating raw .ts/fragmented-mp4 segments directly to disk - the
        result plays in permissive players but many show no duration/seek bar since
        there's no real moov index, just concatenated stream data. Direct CDN mp4
        downloads can have the same issue if the source serves fragmented mp4.
        No-op (returns False) if ffmpeg isn't available - original file is untouched.
        """
        if not cls.is_available():
            return False

        temp_path = input_path + ".remux.mp4"
        cmd = [
            cls.get_ffmpeg_path(), "-y",
            "-i", input_path,
            "-c", "copy",
            "-movflags", "+faststart",
            temp_path
        ]
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creation_flags)
            if proc.returncode == 0 and os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                os.replace(temp_path, input_path)
                logger.info(f"Fixed duration metadata for {input_path}")
                return True
            logger.warning(f"Duration-fix remux failed (code {proc.returncode}) for {input_path}; keeping original file.")
        except Exception as e:
            logger.error(f"Duration-fix remux error for {input_path}: {e}")

        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        return False

    @classmethod
    def get_video_info(cls, input_path: str) -> dict:
        """Returns {"duration": seconds(float), "width": int, "height": int} via ffprobe."""
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        cmd = [
            cls.get_ffprobe_path(), "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-show_entries", "format=duration",
            "-of", "json", input_path
        ]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=creation_flags)
            data = json.loads(proc.stdout)
            stream = (data.get("streams") or [{}])[0]
            duration = float(data.get("format", {}).get("duration", 0))
            return {
                "duration": duration,
                "width": int(stream.get("width", 0)),
                "height": int(stream.get("height", 0)),
            }
        except Exception as e:
            logger.error(f"ffprobe failed to read video info for {input_path}: {e}")
            return {"duration": 0.0, "width": 0, "height": 0}

    @classmethod
    def split_video_into_clips(
        cls,
        input_path: str,
        output_dir: str,
        clip_duration_seconds: int,
        aspect_ratio: str = "Original",
        progress_callback=None,
    ) -> list[str]:
        """
        Splits input_path into sequential clips of clip_duration_seconds each.
        If aspect_ratio is not "Original" (e.g. "9:16"), each clip is center-cropped
        to that ratio (requires re-encoding); otherwise clips are fast stream-copied.
        progress_callback(clips_done, clips_total), if given, fires after each clip
        so the caller can show real progress instead of a static "in progress" state.
        Returns the list of output clip file paths (empty list on failure).
        """
        info = cls.get_video_info(input_path)
        total_duration = info["duration"]
        if total_duration <= 0:
            logger.error(f"Could not determine duration for {input_path}; skipping clip split.")
            return []

        os.makedirs(output_dir, exist_ok=True)
        base_name = Path(input_path).stem
        ffmpeg_cmd = cls.get_ffmpeg_path()
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

        crop_filter = None
        if aspect_ratio and aspect_ratio != "Original":
            crop_filter = cls._build_crop_filter(info["width"], info["height"], aspect_ratio)

        import math
        num_clips = max(1, math.ceil(total_duration / clip_duration_seconds))
        output_paths = []

        for i in range(num_clips):
            start = i * clip_duration_seconds
            length = min(clip_duration_seconds, total_duration - start)
            if length <= 0:
                break

            out_path = os.path.join(output_dir, f"{base_name}_part{i + 1:02d}.mp4")
            cmd = [ffmpeg_cmd, "-y", "-ss", str(start), "-i", input_path, "-t", str(length)]

            if crop_filter:
                cmd += ["-vf", crop_filter, "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "aac"]
            else:
                cmd += ["-c", "copy"]

            cmd.append(out_path)

            try:
                proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creation_flags)
                if proc.returncode == 0 and os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                    output_paths.append(out_path)
                else:
                    logger.warning(f"Clip {i + 1}/{num_clips} failed (code {proc.returncode}) for {input_path}")
            except Exception as e:
                logger.error(f"Error creating clip {i + 1}/{num_clips}: {e}")

            if progress_callback:
                progress_callback(i + 1, num_clips)

        logger.info(f"Split {input_path} into {len(output_paths)}/{num_clips} clip(s) -> {output_dir}")
        return output_paths

    @staticmethod
    def _build_crop_filter(width: int, height: int, aspect_ratio: str) -> str:
        """Builds an ffmpeg center-crop filter string matching aspect_ratio (e.g. '9:16')."""
        try:
            target_w, target_h = (int(p) for p in aspect_ratio.split(":"))
        except (ValueError, AttributeError):
            return ""

        if not width or not height or not target_w or not target_h:
            return ""

        target_ratio = target_w / target_h
        src_ratio = width / height

        if src_ratio > target_ratio:
            new_h = height
            new_w = int(height * target_ratio)
        else:
            new_w = width
            new_h = int(width / target_ratio)

        new_w -= new_w % 2  # keep even dimensions (required by most encoders)
        new_h -= new_h % 2
        x = (width - new_w) // 2
        y = (height - new_h) // 2
        return f"crop={new_w}:{new_h}:{x}:{y}"

ffmpeg_manager = FFmpegManager()
