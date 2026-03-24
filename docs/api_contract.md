# API Contract

## Базовые разделы API

- `/objects`
- `/elements`
- `/defects`
- `/channels`
- `/measurements`
- `/environment-records`
- `/interventions`
- `/tests`
- `/media-assets`
- `/imports`
- `/analytics`
- `/exports`

## Канонический импорт

Импорт приводит входной формат к внутренним схемам `Create*`.

- JSON: список записей или объект с ключом `records`.
- CSV: табличный формат с колонками, совпадающими с полями схемы.
- XLSX: первый лист, первая строка — заголовки.

## Экспорт

`GET /exports/objects/{object_id}/observation-package`

Возвращает JSON-пакет с:

- паспортом объекта;
- деревом элементов;
- дефектами;
- наблюдениями;
- средой;
- вмешательствами;
- испытаниями;
- профилем качества;
- индексами и missing-data-отчётом.

