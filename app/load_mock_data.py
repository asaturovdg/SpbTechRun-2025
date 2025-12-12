import asyncio
import json
from pathlib import Path
import re
from urllib.parse import urljoin

import aiohttp
from aiohttp.client_exceptions import ConnectionTimeoutError
from selectolax.parser import HTMLParser
from sqlalchemy import select
from app.database import async_session
from app.models import Product

MOCK_PATH = Path("recsys/product.json")

async def get_maxidom_product_image_async(url: str) -> str | None:
    """
    Асинхронно извлекает URL фото товара с maxidom.ru из background-image.
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            html = await resp.text()

    tree = HTMLParser(html)

    # Ищем div с классом
    node = tree.css_first(".flypage__product-body-base-img-move")
    if not node:
        return None

    style = node.attributes.get("style", "")

    # regex для получения URL
    m = re.search(r'background-image:\s*url\(["\']?(.*?)["\']?\)', style)
    if not m:
        return None

    img_url = m.group(1)

    # Приводим к абсолютному
    return urljoin(url, img_url)

async def to_payload(item: dict) -> dict:

    url = item.get("url")
    try:
        picture_url = await get_maxidom_product_image_async(url)
        print("Loaded picture url:", picture_url)
    except ConnectionTimeoutError as e:
        print(f"Connection timed out for {url}: {e}")
        picture_url = item.get("picture_url")
        print(f"Loading from file:", picture_url)

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

        "picture_url": picture_url,
        "url": url,
        "description": item.get("description"),
        "product_role": item.get("product_role"),
    }


async def load_mock():
    data = json.loads(MOCK_PATH.read_text(encoding="utf-8"))
    async with async_session() as session:
        for item in data:
            payload = await to_payload(item)
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