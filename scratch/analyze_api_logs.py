import json

with open("netshort_api_logs.json", "r", encoding="utf-8") as f:
    logs = json.load(f)

print(f"Total API logs captured: {len(logs)}")
for i, item in enumerate(logs):
    url = item["url"]
    data = item["data"]
    print(f"\n--- [{i}] {url} ---")
    if isinstance(data, dict):
        print("Keys:", list(data.keys()))
        # Check if data contains episode or shortPlayInfo
        data_obj = data.get("data") or data
        if isinstance(data_obj, dict):
            print("Data Keys:", list(data_obj.keys()))
            for k in ["episodeList", "shortPlayEpisodeList", "episodeInfoList", "shortPlayInfo", "episodeNum", "totalEpisode"]:
                if k in data_obj:
                    val = data_obj[k]
                    print(f"  --> FOUND {k}:", type(val), len(val) if isinstance(val, list) else val)
    else:
        print("Data snippet:", str(data)[:200])
