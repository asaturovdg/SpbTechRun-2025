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
    expert_embedding: Optional[NDArray[Shape["1024"], np.float32]]
    expert_reason: Optional[str]

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


class ScoreBreakdown(BaseModel):
    """Score breakdown for visualization"""
    base_score: Optional[float] = None
    thompson_weight: Optional[float] = None
    price_factor: Optional[float] = None
    mode: Optional[str] = None
    feedback_count: Optional[int] = None
    gamma: Optional[float] = None


class RetrievalTrace(BaseModel):
    """Retrieval trace for visualization"""
    channels: Optional[List[str]] = None
    vector_rank: Optional[int] = None
    llm_rank: Optional[int] = None
    rrf_score: Optional[float] = None
    vector_similarity: Optional[float] = None
    llm_match_score: Optional[float] = None


class RecommendationRead(BaseModel):
    """
    Одна строка выдачи /recommendations/{product_id}.
    """

    id: int
    similarity_score: float
    final_score: Optional[float] = None
    created_at: Optional[str] = None  
    rank: Optional[int] = None
    selected_by_mmr: Optional[bool] = None

    recommended_product: ProductRead
    
    # Score breakdown for frontend visualization
    score_breakdown: Optional[ScoreBreakdown] = None
    
    # Retrieval trace for frontend visualization
    retrieval_trace: Optional[RetrievalTrace] = None

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