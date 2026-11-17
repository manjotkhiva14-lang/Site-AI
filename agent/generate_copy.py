import hashlib
import json
import os
import re
import time

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

import agent.config as cfg
from agent.config import OUTPUT_DIR
from agent.sample import load_sample

try:
    import openai  # used for Mistral, Cerebras, Groq (all speak the OpenAI format)
except ImportError:
    openai = None

load_dotenv()

CHUNK = 40    # most texts asked in one request (fewer requests = less quota used)
PAUSE = 7     # seconds between requests (keeps you under about 8 requests a minute)
STOP = False  # becomes True when every provider is out of quota

DEFAULT_LIMIT = 80

LIMITS = {
    "tagline": 60, "heroEyebrow": 30, "heroTitle": 60, "heroSub": 120,
    "floatingBadges": 20, "primaryCtaText": 24, "secondaryCtaText": 24,
    "facilitiesEyebrow": 30, "facilitiesTitle": 60,
    "value": 8, "label": 30, "desc": 120, "story": 280,
    "title": 40, "tab": 20, "time": 20, "badge": 20, "features": 40,
    "category": 20, "tag": 20, "categories": 20, "name": 30,
}

# ---------------------------------------------------------------- providers
# Order = the order they are tried. A provider is used only if its key is in .env.
# Model names change over time: if a provider says "model not found", set
# <NAME>_MODEL in .env (for example MISTRAL_MODEL=...).
COMPAT = [
    {"name": "groq", "env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1",
     "model": "openai/gpt-oss-120b"},
    {"name": "openrouter", "env": "OPENROUTER_API_KEY", "base_url": "https://openrouter.ai/api/v1",
     "model": "meta-llama/llama-3.3-70b-instruct:free"},
    {"name": "mistral", "env": "MISTRAL_API_KEY", "base_url": "https://api.mistral.ai/v1",
     "model": "mistral-small-latest"},
    {"name": "cerebras", "env": "CEREBRAS_API_KEY", "base_url": "https://api.cerebras.ai/v1",
     "model": "gpt-oss-120b"},
]


class ProviderError(Exception):
    def __init__(self, code=None, daily=False, msg=""):
        super().__init__(msg)
        self.code, self.daily, self.msg = code, daily, msg


class AllDead(Exception):
    pass


def _is_daily(text):
    t = text.lower().replace(" ", "").replace("_", "")
    return "perday" in t or "daily" in t


def _gemini_call(model):
    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY"),
        http_options=types.HttpOptions(timeout=90_000),
    )

    def call(prompt):
        for thinking in (True, False):
            try:
                opts = dict(response_mime_type="application/json", max_output_tokens=8192)
                if thinking:
                    opts["thinking_config"] = types.ThinkingConfig(
                        thinking_level=types.ThinkingLevel.LOW)
                resp = client.models.generate_content(
                    model=model, contents=prompt,
                    config=types.GenerateContentConfig(**opts))
                return resp.text
            except errors.APIError as e:
                if e.code == 400 and thinking and "thinking" in str(e).lower():
                    continue  # this model does not accept the thinking setting
                raise ProviderError(e.code, _is_daily(str(e)), str(e))
            except httpx.TimeoutException as e:
                raise ProviderError("timeout", False, str(e))
    return call


PREFER = ["gpt-oss-120b", "llama-3.3-70b", "qwen3", "llama-4", "gemma", "mistral", "deepseek", "llama"]
BAD = ("whisper", "tts", "guard", "embed", "vision", "image", "audio", "orpheus", "safeguard",
       "allam", "moderation", "rerank", "compound", "-vl", "ocr", "coder", "code")


def pick_model(ids, only_free=False):
    """Choose a text model from a provider's own list (names change often)."""
    if only_free:
        ids = [i for i in ids if i.endswith(":free")]
    ids = [i for i in ids if not any(b in i.lower() for b in BAD)]
    for kw in PREFER:
        for i in ids:
            if kw in i.lower():
                return i
    return ids[0] if ids else None


def _compat_call(p):
    client = openai.OpenAI(api_key=os.getenv(p["env"]), base_url=p["base_url"],
                           timeout=90, max_retries=0)
    chosen = {"model": os.getenv(p["name"].upper() + "_MODEL", p["model"]), "auto": False}

    def once(prompt, use_json):
        kwargs = dict(model=chosen["model"], temperature=0.4, max_tokens=6000,
                      messages=[{"role": "user", "content": prompt}])
        if use_json:
            kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)
        text = resp.choices[0].message.content
        if not text or not text.strip():
            raise ProviderError("empty", False, "the model returned no text")
        return text

    def call(prompt):
        use_json = True
        for _ in range(4):
            try:
                return once(prompt, use_json)
            except openai.APIStatusError as e:
                if e.status_code == 400 and use_json:
                    use_json = False  # this model may not support JSON mode: try again without it
                    continue
                if e.status_code == 404 and not chosen["auto"]:
                    chosen["auto"] = True  # the model name is outdated: ask the provider for its list
                    try:
                        ids = [m.id for m in client.models.list().data]
                    except Exception:
                        raise ProviderError(404, False, str(e))
                    new_model = pick_model(ids, only_free=(p["name"] == "openrouter"))
                    if not new_model:
                        raise ProviderError(404, False, "no usable model found. " + str(e))
                    print(f"    ({p['name']}: model {chosen['model']} not available, using {new_model})", flush=True)
                    chosen["model"] = new_model
                    continue
                raise ProviderError(e.status_code, _is_daily(str(e)), str(e))
            except (openai.APITimeoutError, openai.APIConnectionError) as e:
                raise ProviderError("timeout", False, str(e))
        raise ProviderError(400, False, "request rejected")
    return call


_PROVIDERS = None
DEAD = set()


def providers():
    global _PROVIDERS
    if _PROVIDERS is None:
        _PROVIDERS = []
        if os.getenv("GEMINI_API_KEY"):
            for m in [cfg.GEMINI_MODEL] + list(getattr(cfg, "GEMINI_FALLBACKS", [])):
                _PROVIDERS.append({"name": f"gemini:{m}", "call": _gemini_call(m)})
        for p in COMPAT:
            if os.getenv(p["env"]):
                if openai is None:
                    print(f"  ({p['name']} key found but the openai package is missing: pip install openai)", flush=True)
                    continue
                _PROVIDERS.append({"name": p["name"], "call": _compat_call(p)})
        print("Providers in order:", [p["name"] for p in _PROVIDERS] or "NONE (add a key to .env)", flush=True)
    return _PROVIDERS


def call_llm(prompt, label):
    """Try each provider in order. Retry briefly on busy/timeouts, then move to the next one."""
    last = None
    for p in providers():
        if p["name"] in DEAD:
            continue
        attempt = 0
        while True:
            try:
                return p["call"](prompt)
            except ProviderError as e:
                last = e
                if e.daily or e.code in (401, 403, 404):
                    why = "daily quota used up" if e.daily else f"error {e.code}"
                    hint = " (set <NAME>_MODEL in .env if the model name is wrong)" if e.code == 404 else ""
                    print(f"  {label}: {p['name']} unavailable ({why}){hint}. Skipping it for this run.", flush=True)
                    print(f"    Provider said: {e.msg[:250]}", flush=True)
                    DEAD.add(p["name"])
                    break
                if e.code not in (429, 500, 502, 503, 504, "timeout"):
                    print(f"  {label}: {p['name']} error {e.code}: {e.msg[:200]}", flush=True)
                    break  # e.g. 400: try the next provider
                waits = [20, 40] if e.code == 429 else [5, 15]
                if attempt < len(waits):
                    print(f"  {label}: {p['name']} {e.code}, retrying in {waits[attempt]}s...", flush=True)
                    time.sleep(waits[attempt])
                    attempt += 1
                else:
                    print(f"  {label}: {p['name']} keeps failing, trying the next provider", flush=True)
                    break
    if not providers():
        raise RuntimeError("No API key found. Add GEMINI_API_KEY (or MISTRAL_API_KEY) to .env")
    if all(p["name"] in DEAD for p in providers()):
        raise AllDead()
    raise last or RuntimeError("all providers failed")


# ---------------------------------------------------------------- prompts
def page_limit(original):
    """Max length for a page text: a bit longer than the old text, so the layout still fits."""
    return max(20, int(len(original) * 1.15))


def length_guide(node, key="", in_pages=False):
    """Describe every field to the AI: what to write and how long."""
    if isinstance(node, str):
        if in_pages:
            return (f"REWRITE for the new business, max {page_limit(node)} characters. "
                    f"OLD TEXT (belongs to another business, do not reuse its facts): {node}")
        return f"text, max {LIMITS.get(key, DEFAULT_LIMIT)} characters"
    if isinstance(node, list):
        return [length_guide(x, key, in_pages) for x in node]
    if isinstance(node, dict):
        return {k: length_guide(v, k, in_pages) for k, v in node.items()}
    return node  # numbers and booleans stay as they are


def build_prompt(node, business, in_pages):
    return f"""You write website text for a local business.

BUSINESS INFORMATION (the only facts you may use):
{json.dumps(business, ensure_ascii=False, indent=2)}

Return JSON with exactly this structure and the same keys.
Each value tells you what to write and the maximum length:
{json.dumps(length_guide(node, in_pages=in_pages), ensure_ascii=False, indent=2)}

Rules:
- Write fresh, original text for every field. Do not leave a text field empty.
- A value that starts with "REWRITE" shows the OLD text of a template made for a
  different business. Write a NEW text with the same role and a similar length for
  the business above. Never reuse the old text's facts (names, numbers, prices,
  times, equipment, places). If the business has no equivalent fact, write a
  short, neutral sentence about what the business does.
- Keep simple HTML tags (<small>, <br>, <em>) only where the old text has them.
- Use only the facts above. Do not invent prices, awards, reviews, years,
  numbers, or services that are not listed.
- Do not mention pickup, delivery, ordering in advance, baking methods,
  ingredients, or "daily/morning" freshness unless it is in the business info.
- Do not state a price in a sentence. Prices go only in the fee field.
- Leave these empty (""): url, id, instagram, instagramUrl, whatsapp,
  whatsappLink, email, establishedYear, copyright, and stats value.
- Keep each text within its maximum length.
- Do not change keys or the number of items in a list.
- Return JSON only."""


# ---------------------------------------------------------------- main
def ask(label, node, business, in_pages, cache_dir):
    """One request for one part of the site. Returns a dict, or None if it failed.
    Finished parts are saved, so a rerun asks only for what is missing."""
    global STOP
    prompt = build_prompt(node, business, in_pages)
    cache_file = cache_dir / (hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:16] + ".json")
    if cache_file.exists():
        print(f"Saved earlier, skipping: {label}", flush=True)
        return json.loads(cache_file.read_text(encoding="utf-8"))
    if STOP:
        return None  # every provider is out of quota: send nothing more
    print(f"Writing {label}...", flush=True)
    try:
        text = call_llm(prompt, label)
        text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
        data = json.loads(text)
        if not isinstance(data, dict) or not all(k in data for k in node):
            raise ValueError("answer is missing some keys")
    except AllDead:
        STOP = True
        print("  No provider is available right now (quota used up or model not found). Stopping. Saved parts are kept; run again later.", flush=True)
        return None
    except Exception as e:  # network, quota, bad JSON: never crash the whole run
        print(f"  {label}: FAILED ({type(e).__name__}): {str(e)[:300]}", flush=True)
        print("  Run again to retry only this part.", flush=True)
        return None

    cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    time.sleep(PAUSE)
    return data


def generate_copy(state):
    """Write all website text in small requests. Never crashes on a failed part."""
    biz = state["business"]
    sample = load_sample(biz)
    pages = sample.pop("pages", {})
    cache_dir = OUTPUT_DIR / "_cache" / biz["slug"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    missing = []

    site = {"$schema": sample.get("$schema", ""), "navigation": sample["navigation"]}
    for key in ("business", "home", "about", "services", "gallery", "contact"):
        if key not in sample:
            continue
        got = ask(key, {key: sample[key]}, biz, False, cache_dir)
        if got:
            site.update(got)
        else:
            site[key] = sample[key]  # fallback: the template's own values
            missing.append(key)

    site["pages"] = {}
    for name, texts in pages.items():
        items = list(texts.items())
        site["pages"][name] = {}
        for i in range(0, len(items), CHUNK):
            part = dict(items[i:i + CHUNK])
            label = f"{name} page ({i + 1}-{i + len(part)} of {len(items)})"
            got = ask(label, part, biz, True, cache_dir)
            for k, old in part.items():
                value = (got or {}).get(k)
                if isinstance(value, str) and value.strip():
                    site["pages"][name][k] = value
                else:
                    site["pages"][name][k] = old  # fallback: old template text
                    missing.append(f"{name}.{k}")

    if missing:
        print(f"\nWARNING: {len(missing)} texts could not be written. They show the template's old "
              f"text. Run again: only these parts will be asked again.\n", flush=True)
    return {"site_data": site}