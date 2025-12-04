from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator, List, Optional

from app.models import ArmStats, Feedback, Product
from .config.config import settings

# Async SQLAlchemy engine used by the application.
# 
# `echo` is controlled by settings.database_echo so that
# developers can toggle SQL logging via environment (DB_ECHO).
engine = create_async_engine(
    settings.database_url_async,
    echo=settings.database_echo,
)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_products(
        session: AsyncSession,
        role: Optional[str] = None,
) -> List[Product] :
    stmt = select(Product)
    
    if role:
        stmt = stmt.where(Product.product_role == role)
    
    result = await session.execute(stmt)
    products = list(result.scalars().all())
    return products

async def create_feedback(
        session: AsyncSession,
        feedback: Feedback
) -> Feedback:
    session.add(feedback)
    await session.commit()
    await session.refresh(feedback)
    return feedback

async def get_or_create_arm_stats(
        session: AsyncSession,
        product_id: int,
        recommended_product_id: int
) -> ArmStats:
    stmt = select(ArmStats).where(and_(
        ArmStats.product_id == product_id, 
        ArmStats.recommended_product_id == recommended_product_id
    ))

    result = await session.execute(stmt)
    instance = result.scalar_one_or_none()

    if instance is None:
        instance = ArmStats(
            product_id=product_id,
            recommended_product_id=recommended_product_id
        )
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
    return instance
    
async def update_arm_stats(
        session: AsyncSession, 
        arm: ArmStats
) -> ArmStats:
    stmt = update(ArmStats).where(and_(
        ArmStats.product_id == arm.product_id,
        ArmStats.recommended_product_id == arm.recommended_product_id
    )).values(
        alpha=arm.alpha,
        beta=arm.beta
    )
    await session.execute(stmt)
    return arm
    