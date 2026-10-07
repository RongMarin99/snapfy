import re

dm_clean = '''
<AdaptationSet mimeType="audio/mp4">
  <Representation id="101" bandwidth="128000" codecs="mp4a.40.2">
    <BaseURL>https://video.fbcdn.net/hphotos-ak-xpf1/v/t39.2365-6/12345_audio.mp4?bytestart=0&amp;byteend=1000</BaseURL>
  </Representation>
</AdaptationSet>
'''

audio_reps = re.findall(r'<Representation[^>]*mimeType="audio/[^"]*"[^>]*>.*?<BaseURL>(.*?)</BaseURL>', dm_clean, re.DOTALL)
if not audio_reps:
    audio_reps = re.findall(r'<Representation[^>]*codecs="mp4a[^"]*"[^>]*>.*?<BaseURL>(.*?)</BaseURL>', dm_clean, re.DOTALL)

print("Found audio reps:", audio_reps)
