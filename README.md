# SpbTechRun 2025

Интеллектуальная система для подбора сопутствующих товаров к основным товарам этапа ремонта «White Box» (предчистовая отделка) с функцией непрерывного обучения на основе действий пользователей.

## Стек

- Backend: Python, FastAPI
- ORM и миграции: SQLAlchemy, Alembic
- БД: PostgreSQL
- Frontend: Vue
- Рекомендательная система: отдельный сервис `recsys` (LLM/эмбеддинги)
- Инфраструктура: Docker, docker-compose

## Структура проекта

- `app/` – backend
- `frontend/` – frontend
- `recsys/` – рекомендательная система
- `alembic/`, `alembic.ini` – миграции БД
- `Dockerfile`, `docker-compose.yml` – контейнеризация
- `.env.example` – пример конфигурации окружения
- `requirements.txt` – Python-зависимости backend/recsys

## Требования

- Docker и docker-compose
- NVIDIA Container Toolkit, настроенный для интеграции Docker с GPU

## Быстрый старт
1. `cp .env.example .env`
3. `docker-compose up --build`

- Backend: `http://localhost:8000`
- Swagger/OpenAPI: `http://localhost:8000/docs`
- Frontend: `http://localhost:80` (или `http://localhost`)
