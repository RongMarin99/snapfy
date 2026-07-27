import json

with open("netshort_dom_episodes.json", "r", encoding="utf-8") as f:
    items = json.load(f)

print(f"Total DOM items saved: {len(items)}")
episodes = []
for item in items:
    txt = item.get("text", "")
    href = item.get("href", "")
    # Check if text is a number or contains episode numbers or buttons like 1-30, 31-60, etc.
    if txt.isdigit() or "-" in txt or "EP" in txt.upper() or "Episode" in txt or href.startswith("/episode"):
        episodes.append(item)

print(f"Filtered episode candidate items: {len(episodes)}")
for ep in episodes[:40]:
    print(f"Text: {ep['text']} | Href: {ep['href']}")
