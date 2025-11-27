"""
Simple async seed script to load demo products, recommendations and feedback.

Usage (from project root, with venv activated and DB_* env vars set):

    python -m app.seed_demo

After this, you can call:
    GET /recommendations/{product_id}
    POST /feedback
"""

import asyncio
import random
from typing import List

from sqlalchemy import select

from .database import async_session
from .models import Product, Recommendation, Feedback
from .crud import demo_upsert_products, demo_save_recommendations


PRODUCT_COUNT = 100
RECOMMENDATIONS_PER_PRODUCT = 5
FEEDBACK_PER_PRODUCT = 3


async def seed() -> None:
    random.seed(42)

    async with async_session() as session:
        # 1) Создаём 100 демо-товаров.
        products_to_create: List[Product] = []
        categories = ["floor", "walls", "tools", "paint", "plumbing"]
        works = ["монтаж наливного пола", "монтаж перегородок", "выравнивание стен"]

        for i in range(1, PRODUCT_COUNT + 1):
            ext_id = f"WB-PROD-{i:03d}"
            category = random.choice(categories)
            work = random.choice(works)
            price = float(random.randint(300, 5000))

            products_to_create.append(
                Product(
                    external_id=ext_id,
                    name=f"Демо товар {i:03d}",
                    category_id=category,
                    price=price,
                    raw_attributes={
                        "stage": "white_box",
                        "work": work,
                        "source": "seed_demo",
                    },
                )
            )

        products = await demo_upsert_products(session, products_to_create)
        products_sorted = sorted(products, key=lambda p: p.id)

        # 2) Для каждого товара создаём несколько рекомендаций.
        for product in products_sorted:
            # Список кандидатов, исключая сам товар.
            candidates = [p for p in products_sorted if p.id != product.id]
            chosen = random.sample(
                candidates,
                k=min(RECOMMENDATIONS_PER_PRODUCT, len(candidates)),
            )

            recs = [
                Recommendation(
                    product_id=product.id,
                    recommended_product_id=other.id,
                    similarity_score=round(random.uniform(0.5, 1.0), 3),
                )
                for other in chosen
            ]

            await demo_save_recommendations(
                session,
                product_id=product.id,
                recommendations=recs,
            )

        # 3) Сгенерируем немного случайного фидбека по рекомендациям.
        all_feedback: List[Feedback] = []
        for product in products_sorted:
            stmt = (
                select(Recommendation)
                .where(Recommendation.product_id == product.id)
                .order_by(Recommendation.similarity_score.desc())
                .limit(FEEDBACK_PER_PRODUCT)
            )
            result = await session.execute(stmt)
            recs = result.scalars().all()

            for rec in recs:
                all_feedback.append(
                    Feedback(
                        product_id=product.id,
                        recommended_product_id=rec.recommended_product_id,
                        is_relevant=random.choice([True, False, True]),
                    )
                )

        session.add_all(all_feedback)
        await session.commit()

        example = products_sorted[0]
        print(
            f"Seed completed. Example product_id for testing /recommendations/: {example.id}"
        )


if __name__ == "__main__":
    try:
        asyncio.run(seed())
    except RuntimeError as exc:
        # In some environments (e.g. notebooks / debuggers) there might already
        # be a running or closed event loop; we don't want an ugly traceback
        # at the end of a successful seed run.
        message = str(exc).lower()
        if "event loop" in message:
            pass
        else:
            raise