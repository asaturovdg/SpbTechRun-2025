# SpbTechRun-2025

## Подготовка
- Создаем .env согласно .env.example
- Поднимаем бд локально
- ```alembic revision --autogenerate -m "Сообщение коммита"```
- ```alembic upgrade head```

## Демо данные
```python -m app.seed_demo```

## Запуск 
- ```alembic upgrade head```
- ```uvicorn app.main:app --reload```

Swagger Docs:
```http://localhost:8000/docs```