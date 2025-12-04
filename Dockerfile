FROM python:3.11-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходники приложения
COPY ./app /app/app
COPY ./alembic /app/alembic
COPY ./recsys /app/recsys
COPY alembic.ini /app/alembic.ini

# Дефолтная команда (может быть перезаписана в docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
