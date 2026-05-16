from __future__ import annotations

from pymongo.database import Database

from albion_bot.db.items import upsert_item
from albion_bot.db.models import Item

_WEAPON_ITEMS_BY_CATEGORY = {
    "bow": [
        "Bow",
        "Longbow",
        "Warbow",
        "Whispering Bow",
        "Wailing Bow",
        "Bow of Badon",
        "Mistpiercer",
        "Skystrider Bow",
    ],
    "crossbow": [
        "Crossbow",
        "Heavy Crossbow",
        "Light Crossbow",
        "Weeping Repeater",
        "Boltcasters",
        "Siegebow",
        "Energy Shaper",
        "Arclight Blasters",
    ],
    "axe": [],
    "dagger": [],
    "hammer": [],
    "war gloves": [],
    "mace": [],
    "quarterstaff": [],
    "spear": [],
    "sword": [],
    "arcane staff": [],
    "cursed staff": [],
    "fire staff": [],
    "frost staff": [],
    "holy staff": [],
    "nature staff": [],
    "shapeshifter staff": [],
}

_TIERS = [4, 5, 6, 7, 8]
_ENCHANTMENTS = [0, 1, 2, 3]
_QUALITY = 1


# Seed weapon items using the category structure extracted from the market screenshots.
def seed_bows(db: Database) -> int:
    count = 0
    for category2, item_names in _WEAPON_ITEMS_BY_CATEGORY.items():
        for name in item_names:
            for tier in _TIERS:
                for enchantment in _ENCHANTMENTS:
                    item = Item(
                        name=name,
                        category1="weapons",
                        category2=category2,
                        tier=tier,
                        enchantment=enchantment,
                        quality=_QUALITY,
                    )
                    upsert_item(db, item)
                    count += 1
    return count
