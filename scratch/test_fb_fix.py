import json
import re

class FacebookPluginTest:
    def clean_fb_url(self, raw_url: str) -> str:
        if not raw_url:
            return ""
        u = raw_url.replace(r"\/", "/").replace("\\/", "/").replace(r"\u0025", "%")
        u = re.sub(r'\\u([0-9a-fa-f]{4})', lambda m: chr(int(m.group(1), 16)), u)
        u = u.replace("\\", "")
        return u

    def parse_json_blocks(self, html: str, key: str) -> list:
        results = []
        pattern = rf'"{key}"\s*:\s*\['
        for match in re.finditer(pattern, html):
            start_idx = match.end() - 1
            bracket_count = 0
            in_string = False
            escape = False
            end_idx = -1
            for i in range(start_idx, len(html)):
                char = html[i]
                if escape:
                    escape = False
                    continue
                if char == '\\':
                    escape = True
                    continue
                if char == '"':
                    in_string = not in_string
                    continue
                if not in_string:
                    if char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_idx = i + 1
                            break
            if end_idx != -1:
                json_str = html[start_idx:end_idx].replace(r'\"', '"')
                try:
                    data = json.loads(json_str)
                    results.append(data)
                except Exception:
                    try:
                        data = json.loads(json_str.encode('utf-8').decode('unicode_escape'))
                        results.append(data)
                    except Exception:
                        pass
        return results

    def extract_dash_audio_from_html(self, html: str) -> str:
        best_url, best_bw = "", -1

        for key_name in ["representations", "audio_representations"]:
            blocks = self.parse_json_blocks(html, key_name)
            for reps in blocks:
                if isinstance(reps, list):
                    for r in reps:
                        if not isinstance(r, dict):
                            continue
                        mime = (r.get("mime_type") or "").lower()
                        codecs = (r.get("codecs") or "").lower()
                        is_audio = mime.startswith("audio") or "mp4a" in codecs or (not r.get("height") and not r.get("width") and "video" not in mime)
                        b_url = r.get("base_url") or r.get("url")
                        bw = r.get("bandwidth") or 0
                        if is_audio and b_url and bw > best_bw:
                            best_bw, best_url = bw, self.clean_fb_url(b_url)

        if best_url:
            return best_url

        dash_manifests = re.findall(r'"dash_manifest"\s*:\s*"([^"]+)"', html)
        for dm in dash_manifests:
            dm_clean = dm.replace(r'\"', '"').replace(r'\/', '/').replace(r'\n', '\n').replace('&amp;', '&')
            audio_reps = re.findall(r'<Representation[^>]*mimeType="audio/[^"]*"[^>]*>.*?<BaseURL>(.*?)</BaseURL>', dm_clean, re.DOTALL)
            if not audio_reps:
                audio_reps = re.findall(r'<Representation[^>]*codecs="mp4a[^"]*"[^>]*>.*?<BaseURL>(.*?)</BaseURL>', dm_clean, re.DOTALL)
            if audio_reps:
                return self.clean_fb_url(audio_reps[0])

        audio_patterns = [
            r'"audio_representation_url"\s*:\s*"([^"]+)"',
            r'"playable_url_quality_hd_audio"\s*:\s*"([^"]+)"',
            r'"audio_src"\s*:\s*"([^"]+)"',
            r'"audio_url"\s*:\s*"([^"]+)"',
        ]
        for pattern in audio_patterns:
            matches = re.findall(pattern, html)
            if matches:
                clean_u = self.clean_fb_url(matches[0])
                if clean_u and "fbcdn.net" in clean_u:
                    return clean_u

        return ""

fb = FacebookPluginTest()

sample_fb_html = '''
"browser_native_hd_url": "https://video.xx.fbcdn.net/v/hd_progressive_preview.mp4",
"representations": [
    {"base_url": "https://video.xx.fbcdn.net/v/video_1080p.mp4", "mime_type": "video/mp4", "width": 1920, "height": 1080, "bandwidth": 5000000, "segment_durations": [10, 10]},
    {"base_url": "https://video.xx.fbcdn.net/v/audio_full_track.mp4", "mime_type": "audio/mp4", "codecs": "mp4a.40.2", "bandwidth": 256000, "segment_durations": [10, 10]}
]
'''

audio_url = fb.extract_dash_audio_from_html(sample_fb_html)
print("Extracted audio URL:", audio_url)
assert audio_url == "https://video.xx.fbcdn.net/v/audio_full_track.mp4"
print("TEST SUCCESSFUL!")
