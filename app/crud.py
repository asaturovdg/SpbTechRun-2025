from typing import Iterable, List, Optional

from sqlalchemy import select, String, cast, text
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import ProductRead, RecommendationRead
from recsys import RecommendationEngine
from .models import Product, Recommendation, Feedback


async def get_product(db: AsyncSession, product_id: int) -> Optional[Product]:
    return await db.get(Product, product_id)


async def get_products_by_role(
    db: AsyncSession,
    role: Optional[str] = None,
) -> List[Product]:
    """
    Получить список продуктов, отфильтрованных по роли.
    
    Если role указан, фильтрует продукты где raw_attributes->>'product_role' = role.
    Если role не указан, возвращает все продукты.
    """
    stmt = select(Product)
    
    if role:
        # Фильтруем по product_role в JSON поле raw_attributes
        # Для PostgreSQL используем оператор ->> для получения текстового значения из JSON
        # Сначала проверяем что raw_attributes не NULL и содержит ключ product_role
        # Используем text() с параметризованным запросом для безопасности
        stmt = stmt.where(
            Product.raw_attributes.isnot(None)
        ).where(
            text("raw_attributes->>'product_role' = :role").params(role=role)
        )
    
    result = await db.execute(stmt)
    products = list(result.scalars().all())
    return products


# async def get_recommendations(
#     db: AsyncSession,
#     product_id: int,
#     limit: int = 20,
# ) -> List[Recommendation]:
#     """
#     Вернуть top-N рекомендованных товаров по product_id.

#     Рекомендации загружаются вместе с recommended_product,
#     чтобы избежать ленивых запросов внутри async-контекста.
#     """
#     stmt = (
#         select(Recommendation)
#         .options(selectinload(Recommendation.recommended_product))
#         .where(Recommendation.product_id == product_id)
#         .order_by(Recommendation.similarity_score.desc())
#         .limit(limit)
#     )
#     result = await db.execute(stmt)
#     return result.scalars().all()

async def get_recommendations(
    db: AsyncSession,    
    product_id: int,
    limit: int = 20,
) -> List[RecommendationRead]:
    """
    Вернуть top-N рекомендованных товаров по product_id.

    Рекомендации загружаются вместе с recommended_product,
    чтобы избежать ленивых запросов внутри async-контекста.
    """
    recommender = RecommendationEngine()
    recommendations = recommender.get_ranking(product_id=product_id)


    return [
        RecommendationRead(
            id=r["id"],
            similarity_score=r["similarity_score"],
            created_at=r["created_at"],
            recommended_product=ProductRead.model_validate(r["recommended_product"]),
        )
        for r in recommendations
    ]

# async def create_feedback(
#     db: AsyncSession,
#     product_id: int,
#     recommended_product_id: int,
#     is_relevant: bool,
# ) -> Feedback:
#     feedback = Feedback(
#         product_id=product_id,
#         recommended_product_id=recommended_product_id,
#         is_relevant=is_relevant,
#     )
#     db.add(feedback)
#     await db.commit()
#     await db.refresh(feedback)
#     return feedback

async def create_feedback(
    db: AsyncSession,
    product_id: int,
    recommended_product_id: int,
    is_relevant: bool,
) -> Feedback:
    recommender = RecommendationEngine()

    recommender.update_model(product_id, recommended_product_id, is_relevant)
    feedback = Feedback(
        product_id=product_id,
        recommended_product_id=recommended_product_id,
        is_relevant=is_relevant,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback


###ДЛЯ ДЕМО###


async def demo_save_recommendations(
    db: AsyncSession,
    product_id: int,
    recommendations: Iterable[Recommendation],
) -> List[Recommendation]:
    """
    Сохранить предрасчитанные рекомендации для товара.

    В простейшем варианте мы удаляем старые рекомендации и записываем новые.
    """
    # удалить старые
    stmt = select(Recommendation).where(Recommendation.product_id == product_id)
    result = await db.execute(stmt)
    existing = result.scalars().all()
    for rec in existing:
        await db.delete(rec)

    # добавить новые
    saved: List[Recommendation] = []
    for rec in recommendations:
        rec.product_id = product_id
        db.add(rec)
        saved.append(rec)

    await db.commit()
    for rec in saved:
        await db.refresh(rec)
    return saved

async def demo_upsert_products(db: AsyncSession, products: Iterable[Product]) -> List[Product]:
    """
    Массовое сохранение/обновление сущностей Product.

    Предполагается, что external_id уникален и используется как бизнес-ключ.
    """
    saved: List[Product] = []
    for incoming in products:
        stmt = select(Product).where(Product.external_id == incoming.external_id)
        result = await db.execute(stmt)
        existing: Optional[Product] = result.scalars().first()

        if existing:
            existing.name = incoming.name
            existing.category_id = incoming.category_id
            existing.price = incoming.price
            existing.raw_attributes = incoming.raw_attributes
            saved.append(existing)
        else:
            db.add(incoming)
            saved.append(incoming)

    await db.commit()
    for p in saved:
        await db.refresh(p)
    return saved