from __future__ import annotations

import os
from pathlib import Path

from run_issue_request import main as issue_main


def body_from_env() -> str:
    real = "Yes, run real scrape" if os.getenv("DASHBOARD_REAL_SCRAPE", "false") == "true" else "No, dry-run only"
    ack = os.getenv("DASHBOARD_COMPLIANCE_ACK", "No")
    return f"""### City

{os.getenv('DASHBOARD_CITY', 'Bengaluru')}

### Country

{os.getenv('DASHBOARD_COUNTRY', 'India')}

### Area/neighborhood optional

{os.getenv('DASHBOARD_AREA') or '_No response_'}

### Category

{os.getenv('DASHBOARD_CATEGORY', 'plumber')}

### Coverage intensity

{os.getenv('DASHBOARD_COVERAGE', 'Street-level, many small squares')}

### Max areas to queue

{os.getenv('DASHBOARD_MAX_AREAS', '25')}

### Worker task limit this run

{os.getenv('DASHBOARD_WORKER_LIMIT', '1')}

### Run real scrape?

{real}

### Legal/compliance acknowledgement

{ack}
"""


if __name__ == "__main__":
    event = {
        "issue": {
            "body": body_from_env(),
            "number": 0,
            "title": "Dashboard request",
        }
    }
    event_path = Path("data/dashboard_event.json")
    event_path.parent.mkdir(parents=True, exist_ok=True)
    event_path.write_text(__import__("json").dumps(event), encoding="utf-8")
    os.environ["GITHUB_EVENT_PATH"] = str(event_path)
    issue_main()
