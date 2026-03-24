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

### Типизированный импорт измерений

Для `measurements` в версии 1.1 добавлена профильная валидация:

- поддерживаемые типы:
  - `deflection`
  - `displacement`
  - `strain`
  - `crack_width`
  - `settlement`
  - `tilt`
  - `frequency`
  - `acceleration`
  - `temperature`
  - `humidity`
- проверяются:
  - допустимые единицы;
  - диапазоны значений;
  - наличие `spatial_location` там, где это обязательно;
  - привязка измерения к своему каналу и элементу;
  - дубликаты `timestamp`;
  - крупные пропуски;
  - грубые выбросы.

## Экспорт

`GET /exports/objects/{object_id}/observation-package`

Возвращает JSON-пакет с:

- `export_version`
- паспортом объекта;
- деревом элементов;
- дефектами;
- наблюдениями;
- средой;
- вмешательствами;
- испытаниями;
- профилем качества;
- индексами и missing-data-отчётом.

### Новые блоки версии 1.1

- В `information_sufficiency_index` добавлены:
  - `domain_scores`
  - `level_scores`
  - `responsibility_factor`
  - `requirement_scores`
- В `identification_readiness_report` добавлены:
  - `geometry_ready`
  - `stiffness_ready`
  - `damage_ready`
  - `material_ready`
  - `boundary_ready`
  - `task_scores`
- В `element_state_observation_records` добавлены:
  - `actual_material`
  - `boundary_conditions`
  - `data_coverage`
  - `critical_missing_data_list`
  - `test_history`

### Additive-поля расширения A/G

В `StructuralElement` доступны новые поля:

- `role_criticality`
- `consequence_class`
- `identification_priority`
- `degradation_mechanisms`

В `Defect` доступны новые поля:

- `material_family`
- `element_classifier`
- `corrosion_depth`
- `section_loss_percent`
- `weld_damage_type`
- `bolt_condition`
- `local_buckling_flag`
- `fatigue_crack_length`
- `crack_type`
- `cover_loss_area`
- `rebar_corrosion_class`
- `carbonation_depth`
- `bond_loss_flag`

В `element_state_observation_records` дополнительно экспортируются:

- `role_criticality`
- `consequence_class`
- `identification_priority`
- `degradation_mechanisms`
