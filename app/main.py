from fastapi import FastAPI
from .api.routes import router
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализацию схемы теперь выполняет Alembic миграциями,
    # здесь можно оставить только инициализацию/освобождение ресурсов.
    yield


app = FastAPI(lifespan=lifespan, debug=True)
app.include_router(router)
