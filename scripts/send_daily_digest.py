"""
Send the morning digest to every Telegram subscriber.

    python scripts/send_daily_digest.py            # send now
    python scripts/send_daily_digest.py --dry-run  # print what would be sent

Every morning at 7 (Windows Task Scheduler):

    schtasks /create /tn "MandiSense 7am Digest" /sc daily /st 07:00 ^
      /tr "\"<repo>\\ms_env\\Scripts\\python.exe\" \"<repo>\\scripts\\send_daily_digest.py\"" /f

The laptop must be on at 7. Each attempt is appended to data/farmer/telegram_outbox.jsonl.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mandisense_ai.notify.telegram import broadcast  # noqa: E402

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    res = broadcast(dry_run=ap.parse_args().dry_run)
    print(res)
    sys.exit(1 if res["failed"] else 0)
