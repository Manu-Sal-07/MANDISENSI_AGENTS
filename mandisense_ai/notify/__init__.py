"""
Farmer notifications: a daily market digest built from the ingested data, delivered over Telegram.

    digest.py    - what a farmer is told (prices with their date, best place to sell, reliability warning)
    store.py     - subscribers and the append-only log of everything sent
    telegram.py  - Bot API client and the conversation (onboarding, /today, questions, /stop)

Scripts: `scripts/telegram_bot.py` runs the bot; `scripts/send_daily_digest.py` sends the 7 am digest.
"""
