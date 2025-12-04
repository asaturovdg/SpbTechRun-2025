import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from app.database import async_session
from app.models import Product

MOCK_PATH = Path("recsys/product.json")

def to_payload(item: dict) -> dict:
    return {
        "name": item.get("name"),
        "category_name": item.get("category_name"),
        "vendor": item.get("vendor"),
        "price": float(item.get("price") or 0),

        "category_id": item.get("category_id"),
        "type": item.get("type"),
        "parent_id": item.get("parent_id"),
        "parent_name": item.get("parent_name"),

        "weight_kg": item.get("weight_kg"),
        "shipping_weight_kg": item.get("shipping_weight_kg"),
        "volume_l": item.get("volume_l"),
        "length_mm": item.get("length_mm"),

        "key_params": item.get("key_params"),

        "picture_url": item.get("picture_url"),
        "url": item.get("url"),
        "description": item.get("description"),
        "product_role": item.get("product_role"),
    }


async def load_mock():
    data = json.loads(MOCK_PATH.read_text(encoding="utf-8"))
    async with async_session() as session:
        for item in data:
            payload = to_payload(item)
            stmt = select(Product).where(Product.name == payload["name"])
            result = await session.execute(stmt)
            product = result.scalars().first()

            if product:
                for field, value in payload.items():
                    setattr(product, field, value)
            else:
                session.add(Product(**payload))

        await session.commit()

if __name__ == "__main__":
    asyncio.run(load_mock())
    print("Loaded Mock Data")