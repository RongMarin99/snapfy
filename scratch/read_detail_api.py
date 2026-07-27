import json

with open("netshort_detail_api.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for url, val in data.items():
    print(f"URL: {url}")
    if isinstance(val, dict):
        print("Root keys:", list(val.keys()))
        data_obj = val.get("data")
        if isinstance(data_obj, dict):
            print("Data keys:", list(data_obj.keys()))
            for k, v in data_obj.items():
                if isinstance(v, list):
                    print(f" List key '{k}': length {len(v)}")
                    if v and isinstance(v[0], dict):
                        print(f" Sample item keys in '{k}':", list(v[0].keys()))
                elif isinstance(v, dict):
                    print(f" Dict key '{k}': keys {list(v.keys())}")
                else:
                    print(f" Key '{k}': {str(v)[:100]}")
