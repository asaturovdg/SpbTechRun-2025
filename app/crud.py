from typing import Iterable, List, Optional

from sqlalchemy import select, String, cast, text
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import ProductRead, ProductRead, RecommendationRead
from recsys import RecommendationEngine
from .models import ArmStats, Product, Recommendation, Feedback

from .database import get_products, create_feedback, get_or_create_arm_stats, update_arm_stats

async def get_product(db: AsyncSession, product_id: int) -> Optional[Product]:
    return await db.get(Product, product_id)


async def get_products_by_role(
    db: AsyncSession,
    role: Optional[str] = None,
) -> List[Product]:
    """
    Получить список продуктов, отфильтрованных по роли.
    
    Если role указан, фильтрует продукты где product_role = role.
    Если role не указан, возвращает все продукты.
    """

    products = await get_products(db, role)
    return products

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

async def handle_feedback(
    db: AsyncSession,
    product_id: int,
    recommended_product_id: int,
    is_relevant: bool,
) -> Feedback:
    recommender = RecommendationEngine()

    feedback = await create_feedback(
        db,
        Feedback(
            product_id=product_id,
            recommended_product_id=recommended_product_id,
            is_relevant=is_relevant,
        )
    ) 
    
    
    arm = await get_or_create_arm_stats(
        db, 
        product_id,
        recommended_product_id
    )

    if is_relevant:
        arm.alpha += 1
    else:
        arm.beta += 1

    await update_arm_stats(db, arm)
    recommender.update_model(product_id, recommended_product_id, is_relevant)

    return feedback