from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

class ProductBase(BaseModel):
    external_id: str
    name: str
    category_id: Optional[str] = None
    price: Optional[float] = None
    raw_attributes: Optional[Dict[str, Any]] = None


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    id: int

    model_config = {"from_attributes": True}


class RecommendationRead(BaseModel):
    """
    Одна строка выдачи /recommendations/{product_id}.
    """

    id: int
    similarity_score: float

    recommended_product: ProductRead

    model_config = {"from_attributes": True}


class FeedbackCreate(BaseModel):
    """
    Тело запроса для POST /feedback.
    """

    product_id: int
    recommended_product_id: int
    is_relevant: bool


class FeedbackRead(FeedbackCreate):
    id: int

    model_config = {"from_attributes": True}
