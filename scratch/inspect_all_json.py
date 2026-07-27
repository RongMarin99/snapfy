import json
import os

if os.path.exists("all_json_responses.json"):
    with open("all_json_responses.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Captured {len(data)} JSON responses:")
    for item in data:
        url = item["url"]
        body = item["data"]
        print("->", url)
        if isinstance(body, dict):
            print("   Keys:", list(body.keys()))
            if "data" in body and isinstance(body["data"], dict):
                print("   Sub-keys:", list(body["data"].keys()))
else:
    print("all_json_responses.json not created yet.")
