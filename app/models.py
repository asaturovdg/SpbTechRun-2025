from datetime import datetime
from typing import Optional, List

from sqlalchemy import Integer, String, Float, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass

class Product(Base):
    """
    Товар из каталога (основной или сопутствующий).

    В реальном решении сюда можно положить больше атрибутов из YML-фида.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    category_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Сырые атрибуты из YML (характеристики, параметры и т.п.)
    raw_attributes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    outgoing_recommendations: Mapped[List["Recommendation"]] = relationship(
        back_populates="source_product",
        foreign_keys="Recommendation.product_id",
        cascade="all, delete-orphan",
    )
    incoming_recommendations: Mapped[List["Recommendation"]] = relationship(
        back_populates="recommended_product",
        foreign_keys="Recommendation.recommended_product_id",
        cascade="all, delete-orphan",
    )


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

    source_product: Mapped["Product"] = relationship(
        back_populates="outgoing_recommendations",
        foreign_keys=[product_id],
    )
    recommended_product: Mapped["Product"] = relationship(
        back_populates="incoming_recommendations",
        foreign_keys=[recommended_product_id],
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

    # Для удобной навигации из ORM.
    source_product: Mapped["Product"] = relationship(
        foreign_keys=[product_id],
    )
    recommended_product: Mapped["Product"] = relationship(
        foreign_keys=[recommended_product_id],
    )
