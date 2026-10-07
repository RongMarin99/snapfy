import re
import json

test_html = '''
"representations":[{"base_url":"https:\\/\\/video.fbcdn.net\\/audio.mp4", "mime_type":"audio/mp4", "codecs":"mp4a.40.2", "bandwidth":128000, "segment_durations":[10,10,10]}]
'''

# Current regex in facebook.py:
match1 = re.findall(r'"representations"\s*:\s*(\[[^\]]+\])', test_html)
print("Current regex match:", match1)
if match1:
    try:
        json.loads(match1[0].replace(r'\"', '"'))
        print("JSON parse SUCCESS")
    except Exception as e:
        print("JSON parse FAILED:", e)
