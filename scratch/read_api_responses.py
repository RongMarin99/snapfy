import json
import os

if os.path.exists("api_responses.json"):
    with open("api_responses.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"Total API responses captured: {len(data)}")
    for item in data:
        print("URL:", item["url"])
else:
    print("api_responses.json not created yet.")
