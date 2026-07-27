import re
import json

with open("script_48.js", "r", encoding="utf-8") as f:
    text = f.read()

print("Script 48 length:", len(text))

# Search for patterns like episode_list, episodeList, episodes, dramaInfo, etc.
keywords = ["episodeList", "chapterList", "episodes", "totalEpisode", "videoList", "dramaId", "drama_id"]
for kw in keywords:
    pos = text.find(kw)
    if pos != -1:
        print(f"Keyword '{kw}' found at position {pos}!")
        snippet = text[max(0, pos-100):min(len(text), pos+300)]
        print("Snippet:", snippet)
        print("-" * 50)
