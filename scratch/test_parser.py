import re
import json

def parse_json_blocks(html: str, key: str = "representations"):
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
            except Exception as e:
                # Try unescaping unicode/slashes
                try:
                    data = json.loads(json_str.encode('utf-8').decode('unicode_escape'))
                    results.append(data)
                except Exception:
                    pass
    return results

test_html = '''
"representations": [{"base_url": "https:\\/\\/video.fbcdn.net\\/audio.mp4", "mime_type": "audio/mp4", "codecs": "mp4a.40.2", "bandwidth": 128000, "segment_durations": [10, 10, 10]}]
'''

blocks = parse_json_blocks(test_html, "representations")
print("Parsed blocks count:", len(blocks))
print("Block contents:", blocks)
