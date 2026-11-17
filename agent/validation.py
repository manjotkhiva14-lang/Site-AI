
import re

REQUIRED = ["name", "category", "phone", "address", "hours", "services"]


def normalize_phone(raw):
    """Return a clean 10-digit Indian mobile number, or None if invalid."""
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "6789":
        return digits
    return None


def make_slug(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "business"


def validate_business(business):
    """Return (cleaned_business, errors). Empty errors means the data is usable."""
    errors = []
    cleaned = dict(business)

    for field in REQUIRED:
        value = business.get(field)
        if value is None or (isinstance(value, str) and not value.strip()) or value == []:
            errors.append(f"Missing: {field}")

    if "Missing: phone" not in errors:
        phone = normalize_phone(business.get("phone"))
        if phone is None:
            errors.append("Invalid phone number")
        else:
            cleaned["phone"] = phone

    services = business.get("services")
    if isinstance(services, list):
        for i, s in enumerate(services):
            if not isinstance(s, dict) or not str(s.get("name", "")).strip():
                errors.append(f"Service {i + 1} has no name")
                continue
            if s.get("price") not in (None, ""):
                try:
                    if float(s["price"]) < 0:
                        errors.append(f"Service '{s['name']}' has a negative price")
                except (TypeError, ValueError):
                    errors.append(f"Service '{s['name']}' has an invalid price")

    if business.get("name"):
        cleaned["name"] = str(business["name"]).strip()
        cleaned["slug"] = make_slug(cleaned["name"])
    if business.get("category"):
        cleaned["category"] = str(business["category"]).strip().lower()

    return cleaned, errors
