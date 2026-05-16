from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

from pymongo.database import Database
from pymongo import ASCENDING

from albion_bot.db.models import Item


def _ensure_index(db: Database) -> None:
    db["items"].create_index(
        [("name", ASCENDING), ("tier", ASCENDING), ("enchantment", ASCENDING), ("quality", ASCENDING)],
        unique=True,
    )


def upsert_item(db: Database, item: Item) -> str:
    _ensure_index(db)
    now = datetime.now(timezone.utc)
    doc = item.model_dump()
    doc.pop("created_at", None)
    doc.pop("updated_at", None)

    result = db["items"].find_one_and_update(
        {"name": item.name, "tier": item.tier, "enchantment": item.enchantment, "quality": item.quality},
        {
            "$set": {**doc, "updated_at": now},
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
        return_document=True,
    )
    return str(result["_id"])


def find_item(db: Database, name: str, tier: int, enchantment: int, quality: int) -> Optional[dict]:
    return db["items"].find_one(
        {"name": name, "tier": tier, "enchantment": enchantment, "quality": quality}
    )
