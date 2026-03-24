# Quality Index v1.1

В `v1.1` `information_sufficiency_index` больше не бинарный. Он учитывает покрытие и качество данных.

## Новые выходы

- `coverage_by_critical_elements`
- `coverage_by_parameter_group`
- `quality_weighted_measurement_coverage`
- уровни готовности:
  - `descriptive_only`
  - `identification_ready`
  - `prediction_ready`

## Группы параметров

- `geometry_and_scheme`
- `materials`
- `damage_state`
- `boundary_conditions`
- `dynamic_response`
- `prognosis_preconditions`

## Что влияет на итог

- класс ответственности объекта;
- критичность элемента;
- полнота геометрии;
- полнота материала;
- параметризация дефектов;
- покрытие измерений;
- метаданные канала и измерения;
- среда, вмешательства, испытания, traceability.

## Identification Readiness Report

Отчет готовности теперь показывает состояние отдельно по классам:

- геометрия и схема;
- материалы;
- повреждения;
- закрепления;
- отклик;
- прогнозные предпосылки.

При этом старые совместимые поля (`geometry_ready`, `stiffness_ready` и т.д.) сохраняются.
