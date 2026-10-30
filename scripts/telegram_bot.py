"""
Run the MandiSense Telegram bot (long polling; no public URL needed).

    python scripts/telegram_bot.py

Farmers open the bot, press Start, choose language, district and crops, and receive today's digest. Leave this
running during the demo; stop it with Ctrl+C.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mandisense_ai.notify.telegram import run_polling  # noqa: E402

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        run_polling()
    except KeyboardInterrupt:
        print("stopped")
