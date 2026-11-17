"""Dry run: tests the REPLACING part only. No Gemini, no quota.

Every text in the site is replaced with "NEW <page>.<key>". Open the site and look:
- a text that says NEW ...  -> replacing works for that spot
- a text that still shows old words -> that spot is not connected
"""
import functools
import http.server
import json
import webbrowser

from agent.build_site import build_site
from agent.check_copy import check_copy
from agent.sample import load_sample
from agent.validation import validate_business

with open("sample_intake.json", encoding="utf-8") as f:
    raw = json.load(f)

business, errors = validate_business(raw)
if errors:
    raise SystemExit(f"Intake problems: {errors}")
business["slug"] = "fake-test"  # separate output folder, your real site is not touched

sample = load_sample(business)
pages = sample.pop("pages", {})


def fill(node, key=""):
    if isinstance(node, str):
        return "NEW TEXT" if key not in ("url", "id", "value", "fee", "period", "badge") else ""
    if isinstance(node, list):
        return [fill(x, key) for x in node]
    if isinstance(node, dict):
        return {k: fill(v, k) for k, v in node.items()}
    return node


site = fill(sample)
site["pages"] = {
    page: {key: f"NEW {page}.{key}" for key in texts} for page, texts in pages.items()
}

checked = check_copy({"business": business, "site_data": site})
built = build_site({"business": business, "site_data": checked["site_data"], "photos": []})
print("Built:", built["site_path"])

handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=built["site_path"])
print("Open http://localhost:8001  (press Ctrl+C to stop)")
webbrowser.open("http://localhost:8001")
http.server.ThreadingHTTPServer(("", 8001), handler).serve_forever()