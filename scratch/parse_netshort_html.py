import os
import re
import json

# Inspect script files extracted from NetShort HTML
for fname in sorted(os.listdir(".")):
    if fname.startswith("script_") and fname.endswith(".js"):
        with open(fname, "r", encoding="utf-8") as f:
            content = f.read()
            if "total" in content or "episode" in content or "chapter" in content or "drama" in content or "play" in content:
                print(f"=== File {fname} ({len(content)} bytes) ===")
                # Look for JSON arrays or objects inside
                json_matches = re.findall(r'(\{\"id\":.*?|\{\"drama.*?)', content)
                if json_matches:
                    print(f"Found {len(json_matches)} potential JSON objects in {fname}")
                    print("Sample:", json_matches[0][:200])

