"""
Snapfy Export & File Utilities
"""

import csv
import json
import os
from typing import List, Dict

def export_to_csv(filepath: str, data: List[Dict]) -> bool:
    if not data:
        return False
    try:
        keys = list(data[0].keys())
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
        return True
    except Exception as e:
        print(f"[Export CSV Error] {e}")
        return False

def export_to_json(filepath: str, data: List[Dict]) -> bool:
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[Export JSON Error] {e}")
        return False

def export_to_txt(filepath: str, data: List[Dict]) -> bool:
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            for item in data:
                url = item.get("url") or item.get("stream_url") or ""
                title = item.get("title", "")
                f.write(f"{title} | {url}\n")
        return True
    except Exception as e:
        print(f"[Export TXT Error] {e}")
        return False
