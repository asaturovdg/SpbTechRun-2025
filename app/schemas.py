from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
from numpydantic import NDArray, Shape
from pydantic import BaseModel, Field

class ProductBase(BaseModel):
    name: str
    category_id: Optional[str] = None
    price: Optional[float] = None
    raw_attributes: Optional[Dict[str, Any]] = None

    name: str
    category_name: str
    vendor: str
    price: Optional[float]
    category_id: Optional[str]
    type: str
    parent_id: str
    parent_name: str
    weight_kg: Optional[float]
    shipping_weight_kg: Optional[float]
    volume_l: Optional[float]
    length_mm: Optional[float]

    key_params: Optional[dict]

    picture_url: str
    url: str
    description: str
    product_role: str
    
    embedding: Optional[NDArray[Shape["1024"], np.float32]]

    model_config = {"arbitrary_types_allowed": True}


class ProductCreate(ProductBase):
    pass


class ProductRead(BaseModel):
    """
    Product schema for recommendation results (new)
    """
    id: int
    name: str
    price: Optional[float] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    vendor: Optional[str] = None
    picture_url: Optional[str] = None
    product_role: Optional[str] = None
    type: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    
    model_config = {"from_attributes": True}


class RecommendationRead(BaseModel):
    """
    Одна строка выдачи /recommendations/{product_id}.
    """

    id: int
    similarity_score: float
    created_at: Optional[str] = None  

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