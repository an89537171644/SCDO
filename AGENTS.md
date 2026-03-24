# AGENTS

## Обязательные команды

### Запуск проекта

Целевой запуск:

```bash
docker compose up --build
```

Локальный запуск:

```bash
python -m venv .venv
pip install -e .[dev]
alembic upgrade head
uvicorn apps.api.main:app --reload
```

### Запуск тестов

```bash
pytest
```

### Миграции

```bash
alembic upgrade head
alembic downgrade base
```

## Demo dataset

Demo dataset лежит в `sample_data/demo_bundle.json`.

## Что обязательно проверить перед завершением задачи

- код проходит `pytest`;
- миграции применяются на чистой БД;
- OpenAPI поднимается;
- demo dataset импортируется;
- экспорт `observation_package` работает.

## Что не менять без отдельной задачи

- бизнес-смысл индекса `information_sufficiency_index`;
- формат `observation_package`;
- обязательность P0/P1-полей;
- схему audit log.

## Артефакты, которые агент должен оставлять

- код миграций;
- тесты;
- документацию в `docs/`;
- пример данных в `sample_data/`.

