from __future__ import annotations

from datetime import datetime, timezone

from albion_bot.db.connection import get_db


DEFAULT_IS_PREMIUM = False
_GLOBAL_CONFIG_ID = "global"


def get_sell_settings() -> dict:
    """Load global sell settings from DB, creating defaults if missing.

    Current settings:
    - is_premium: bool
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    doc = db.bot_config.find_one({"_id": _GLOBAL_CONFIG_ID})
    if doc is None:
        doc = {
            "_id": _GLOBAL_CONFIG_ID,
            "is_premium": DEFAULT_IS_PREMIUM,
            "created_at": now,
            "updated_at": now,
        }
        db.bot_config.insert_one(doc)

    is_premium = bool(doc.get("is_premium", DEFAULT_IS_PREMIUM))
    return {"is_premium": is_premium}


def set_is_premium(value: bool) -> None:
    """Utility function for scripts/tests to update global premium status."""
    db = get_db()
    now = datetime.now(timezone.utc)
    db.bot_config.update_one(
        {"_id": _GLOBAL_CONFIG_ID},
        {
            "$set": {
                "is_premium": bool(value),
                "updated_at": now,
            },
            "$setOnInsert": {
                "created_at": now,
            },
        },
        upsert=True,
    )
