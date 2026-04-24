import json
import os
from pathlib import Path

log_path = r"C:\Users\groot\.gemini\antigravity\brain\e0e5508a-566d-4f99-a115-8e74384894b4\.system_generated\logs\overview.txt"
project_root = Path(r"c:\Users\groot\Music\Vibe-Auditor")
output_dir = project_root / "patchbuddy"

# Ensure analyzer dir exists
(output_dir / "analyzer").mkdir(parents=True, exist_ok=True)

# Track the latest content for each file
recovered_content = {}

with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get("type") == "PLANNER_RESPONSE" and "tool_calls" in data:
                for call in data["tool_calls"]:
                    name = call.get("name")
                    args = call.get("args", {})
                    
                    target = args.get("TargetFile", "").replace("\"", "")
                    if not target: continue
                    
                    # Normalize target path to relative
                    # It could be audit\something or patchbuddy\something
                    if "Vibe-Auditor\\" in target:
                        rel_path = target.split("Vibe-Auditor\\")[-1]
                    else:
                        rel_path = target
                        
                    rel_path = rel_path.replace("audit\\", "patchbuddy\\")
                    
                    if not rel_path.startswith("patchbuddy\\"):
                        continue
                        
                    rel_path = rel_path.replace("patchbuddy\\", "")
                    
                    if name == "write_to_file":
                        content = args.get("CodeContent", "")
                        if content.startswith("\"") and content.endswith("\""):
                            content = content[1:-1]
                        
                        # Fix escaping
                        content = content.encode('utf-8').decode('unicode_escape')
                        recovered_content[rel_path] = content
        except Exception as e:
            continue

for path, content in recovered_content.items():
    out_path = output_dir / path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Recovered {path} ({len(content)} bytes)")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)
