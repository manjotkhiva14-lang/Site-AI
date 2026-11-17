import json
from agent.generate_copy import generate_copy

with open("sample_intake.json", encoding="utf-8") as f:
    business = json.load(f)

result = generate_copy({"business": business})
print(json.dumps(result["site_data"], ensure_ascii=False, indent=2))

from agent.check_copy import check_copy

checked = check_copy({"business": business, "site_data": result["site_data"]})
print("ERRORS:", checked["copy_errors"])