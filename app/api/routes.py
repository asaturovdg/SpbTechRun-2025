from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud import (
    get_product,
    get_recommendations,
    handle_feedback,
    get_products_by_role,
)
from ..database import get_session
from ..schemas import RecommendationRead, FeedbackCreate, FeedbackRead, ProductRead

router = APIRouter()


@router.get(
    "/recommendations/{product_id}",
    response_model=List[RecommendationRead],
    summary="Получить сопутствующие товары",
)
async def get_recommendations_view(
    product_id: int,
    db: AsyncSession = Depends(get_session),
) -> List[RecommendationRead]:
    """
    Возвращает 20 самых похожих товаров для заданного product_id,
    отсортированных по similarity_score.
    """
    product = await get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    recommendations: List[RecommendationRead] = await get_recommendations(
        db, product_id=product_id, limit=20
    )

    return recommendations


@router.post(
    "/feedback",
    response_model=FeedbackRead,
    summary="Зафиксировать фидбек по рекомендации",
)
async def create_feedback_view(
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_session),
) -> FeedbackRead:
    """
    Принимает ID исходного товара и ID выбранного аналога,
    а также флаг «подошёл / не подошёл».
    """
    # При желании можно дополнительно проверять существование товаров.
    feedback = await handle_feedback(
        db=db,
        product_id=payload.product_id,
        recommended_product_id=payload.recommended_product_id,
        is_relevant=payload.is_relevant,
    )
    return feedback


@router.get(
    "/main-products",
    response_model=List[ProductRead],
    summary="Получить список основных товаров",
)
async def get_main_products_view(
    db: AsyncSession = Depends(get_session),
) -> List[ProductRead]:
    """
    Возвращает список всех основных товаров из БД.
    
    Фильтрует продукты по роли "основной товар" из поля raw_attributes->product_role.
    """
    products = await get_products_by_role(db, role="основной товар")
    return [ProductRead.model_validate(product) for product in products]
