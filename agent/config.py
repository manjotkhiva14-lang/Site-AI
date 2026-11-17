from pathlib import Path
GEMINI_MODEL = "gemini-3.8-flash"

BASE_DIR = Path(__file__).resolve().parent.parent   # the ai_agent folder

TEMPLATE_DIR = BASE_DIR / "templates" / "template_3d"
SITE_DATA_PATH = TEMPLATE_DIR / "site-data.json"
OUTPUT_DIR = BASE_DIR / "output"