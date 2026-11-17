import re
from datetime import date

from agent.generate_copy import LIMITS, DEFAULT_LIMIT, page_limit
from agent.sample import load_sample
from agent.validation import make_slug

PAGES = [
    ("Home", "index.html", "home"),
    ("About", "about.html", "about"),
    ("Services", "services.html", "services"),
    ("Gallery", "gallery.html", "gallery"),
    ("Contact", "contact.html", "contact"),
]

# These fields may stay empty, because code or the template handles them.
EMPTY_OK = {
    "$schema", "state", "country", "landmark", "whatsapp", "whatsappLink",
    "instagram", "instagramUrl", "email", "establishedYear", "url", "id",
    "primaryCtaUrl", "secondaryCtaUrl", "value", "period", "fee", "badge",
}

# Code writes these, so Gemini's numbers are not checked here.
NO_NUMBER_CHECK = {"$schema", "phone", "phoneDisplay", "phoneTel", "whatsapp",
                   "whatsappLink", "copyright", "primaryCtaUrl", "secondaryCtaUrl"}


def fill_fixed(site, biz):
    """Overwrite fields that must come from real data, never from Gemini."""
    b = site["business"]
    hours = biz["hours"]
    digits = re.sub(r"\D", "", str(biz["phone"]))[-10:]  # validation gives 10 digits
    shown = f"{digits[:5]} {digits[5:]}"
    b.update({
        "name": biz["name"],
        "shortName": "".join(w[0] for w in biz["name"].split()[:2]).upper(),
        "phone": f"+91 {shown}",
        "phoneDisplay": shown,
        "phoneTel": "tel:+91" + digits,
        "whatsapp": f"+91 {shown}",
        "whatsappLink": "https://wa.me/91" + digits,
        "address": biz["address"],
        "hours": ", ".join(hours) if isinstance(hours, list) else str(hours),
        "state": biz.get("state", ""),
        "country": biz.get("country", ""),
        "landmark": biz.get("landmark", ""),
        "instagram": biz.get("instagram", ""),
        "instagramUrl": biz.get("instagramUrl", ""),
        "email": biz.get("email", ""),
        "establishedYear": str(biz.get("establishedYear", "")),
        "copyright": f"© {date.today().year} {biz['name']}. All rights reserved.",
    })
    site["navigation"] = [{"name": n, "url": u, "id": i} for n, u, i in PAGES]
    site["home"]["primaryCtaUrl"] = b["phoneTel"]
    site["home"]["secondaryCtaUrl"] = "services.html"

    for i, item in enumerate(site["gallery"]["items"], 1):
        item["id"] = i

    for slot, svc in zip(site["services"]["catalog"], biz["services"]):
        slot["label"] = svc["name"]
        slot["id"] = make_slug(svc["name"])
        slot["fee"] = str(svc["price"]) if svc.get("price") not in (None, "") else ""
        slot["badge"] = ""
        slot["period"] = ""
    return site


def same_shape(a, b, path=""):
    errs = []
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            errs.append(f"{path or 'root'}: keys differ {sorted(set(a) ^ set(b))}")
        for k in set(a) & set(b):
            errs += same_shape(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            errs.append(f"{path}: expected {len(b)} items, got {len(a)}")
        for i, (x, y) in enumerate(zip(a, b)):
            errs += same_shape(x, y, f"{path}[{i}]")
    elif type(a) is not type(b):
        errs.append(f"{path}: wrong type")
    return errs


def walk_texts(node, key="", path=""):
    if isinstance(node, str):
        yield path, key, node
    elif isinstance(node, list):
        for i, x in enumerate(node):
            yield from walk_texts(x, key, f"{path}[{i}]")
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from walk_texts(v, k, f"{path}.{k}")


def _limit(path, key, sample):
    """Max length for one field. Page texts are limited by the old text's length."""
    parts = path.split(".")
    if len(parts) == 4 and parts[1] == "pages":
        old = sample.get("pages", {}).get(parts[2], {}).get(parts[3])
        if old:
            return int(page_limit(old) * 1.25)
    return int(LIMITS.get(key, DEFAULT_LIMIT) * 1.3)


def check_copy(state):
    biz = state["business"]
    sample = load_sample(biz)
    site = fill_fixed(state["site_data"], biz)

    errors = same_shape(site, sample)
    facts = str(biz)

    for path, key, text in walk_texts(site):
        if not text.strip() and key not in EMPTY_OK:
            errors.append(f"{path}: empty")
        if len(text) > _limit(path, key, sample):
            errors.append(f"{path}: too long ({len(text)} characters)")
        if key not in NO_NUMBER_CHECK:
            plain = re.sub(r"<[^>]+>|&#?\w+;", " ", text)
            for num in re.findall(r"\d+", plain):
                if num not in facts:
                    errors.append(f"{path}: number {num} is not in the business data")

    return {"site_data": site, "copy_errors": errors}
