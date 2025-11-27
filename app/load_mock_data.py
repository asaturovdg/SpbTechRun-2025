import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from app.database import async_session
from app.models import Product

MOCK_PATH = Path("recsys/MOCK_DB.json")

def to_payload(item: dict) -> dict:
    return {
        "external_id": str(item["id"]),
        "name": item["name"],
        "category_id": item.get("category_id"),
        "price": float(item.get("price") or 0),
        "raw_attributes": {
            "picture_url": item.get("picture_url"),
            "vendor": item.get("vendor"),
            "white_box_type": item.get("white_box_type"),
            "product_role": item.get("product_role"),
            "category_name": item.get("category_name"),
            "int_id": item.get("int_id"),
        },
    }

async def load_mock():
    data = json.loads(MOCK_PATH.read_text(encoding="utf-8"))
    async with async_session() as session:
        for item in data:
            payload = to_payload(item)
            stmt = select(Product).where(Product.external_id == payload["external_id"])
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