import functools
import http.server
import json
import webbrowser
from pathlib import Path

from agent.graph import make_graph

with open("sample_intake.json", encoding="utf-8") as f:
    raw = json.load(f)

photo_paths = [str(p) for p in sorted(Path("sample_photos").glob("*")) if p.is_file()]

result = {}
print("Starting... this takes a few minutes.", flush=True)
for update in make_graph().stream({"raw": raw, "photo_paths": photo_paths}, stream_mode="updates"):
    for node, data in update.items():
        print(f"Done: {node}", flush=True)
        result.update(data or {})

if result.get("errors"):
    print("Intake problems:", result["errors"])
    raise SystemExit

print("Photo problems:", result.get("photo_problems"))
print("Copy warnings:", result.get("copy_errors"))
print("Site built in:", result["site_path"])

handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                            directory=result["site_path"])
url = "http://localhost:8000"
print("Open", url, "(press Ctrl+C to stop)")
webbrowser.open(url)
http.server.ThreadingHTTPServer(("", 8000), handler).serve_forever()