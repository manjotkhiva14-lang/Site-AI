import copy
import json

from agent.config import SITE_DATA_PATH

MAX_SERVICES = 6  # the most the template layout looks good with


def load_sample(biz):
    """Load site-data.json and resize the service list to match the business."""
    sample = json.loads(SITE_DATA_PATH.read_text(encoding="utf-8"))
    catalog = sample["services"]["catalog"]
    n = min(len(biz["services"]), MAX_SERVICES)
    sample["services"]["catalog"] = [
        copy.deepcopy(catalog[min(i, len(catalog) - 1)]) for i in range(n)
    ]
    return sample