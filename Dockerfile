FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY apps ./apps
COPY alembic.ini ./
COPY alembic ./alembic
COPY sample_data ./sample_data
COPY scripts ./scripts

RUN pip install --upgrade pip && pip install -e '.[ui]'

CMD ["sh", "-c", "alembic upgrade head && uvicorn apps.api.main:app --host 0.0.0.0 --port 8000"]
