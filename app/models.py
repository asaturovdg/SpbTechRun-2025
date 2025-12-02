from datetime import datetime
from typing import Optional, List

import numpy as np
from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Integer, String, Float, Boolean, ForeignKey, DateTime, JSON, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from numpydantic import NDArray, Shape

class Base(DeclarativeBase):
    pass

class Product(Base):
    """
    Товар из каталога (основной или сопутствующий).

    В реальном решении сюда можно положить больше атрибутов из YML-фида.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    category_name: Mapped[str] = mapped_column(String(256), nullable=False)
    vendor: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    category_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    parent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_name: Mapped[str] = mapped_column(String(128), nullable=False)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    shipping_weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume_l: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    length_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    key_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    picture_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    product_role: Mapped[str] = mapped_column(String(64), nullable=False)
    
    embedding: Mapped[Optional[NDArray[Shape["1024"], np.float32]]] = mapped_column(Vector(1024), nullable=True)


class Recommendation(Base):
    """
    Предрасчитанная рекомендация сопутствующего товара.

    product_id            — исходный товар
    recommended_product_id — рекомендованный сопутствующий товар
    similarity_score      — рейтинг/оценка схожести (чем выше, тем лучше)
    """

    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    recommended_product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )

    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Feedback(Base):
    """
    Фидбек пользователя по конкретной рекомендации
    (подошёл / не подошёл сопутствующий товар).
    """

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    recommended_product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )

    is_relevant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )