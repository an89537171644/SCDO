# Domain Model

СКДО строится вокруг объекта эксплуатации и его наблюдаемого состояния.

## Сущности

- `AssetObject` — паспорт объекта.
- `StructuralElement` — иерархия система → подсистема → элемент → зона.
- `Defect` — дефекты и повреждения с локализацией.
- `ObservationChannel` и `Measurement` — каналы и наблюдения/временные ряды.
- `EnvironmentRecord` — среда и эксплуатационные воздействия.
- `Intervention` — ремонты, усиления, замены и ограничения.
- `TestRecord` — испытания и НК.
- `MediaAsset` — метаданные файлов и привязка к сущностям.
- `DataQualityRecord` — точность, полнота, повторяемость, трассируемость.
- `AuditLog` — журнал изменений и импортов.

## ER-диаграмма

```mermaid
erDiagram
    AssetObject ||--o{ StructuralElement : contains
    StructuralElement ||--o{ StructuralElement : parent_of
    StructuralElement ||--o{ Defect : has
    StructuralElement ||--o{ ObservationChannel : has
    ObservationChannel ||--o{ Measurement : records
    StructuralElement ||--o{ EnvironmentRecord : exposed_to
    StructuralElement ||--o{ Intervention : changed_by
    StructuralElement ||--o{ TestRecord : tested_by
    AssetObject ||--o{ MediaAsset : documents
    StructuralElement ||--o{ MediaAsset : documents
    AssetObject ||--o{ DataQualityRecord : assessed_by
    StructuralElement ||--o{ DataQualityRecord : assessed_by
    AssetObject ||--o{ AuditLog : changes
```

## Ключевые доменные правила

- любая запись должна иметь временную метку;
- любая запись должна иметь источник и единицы измерения, если это измерение;
- дефекты и наблюдения должны быть привязаны к элементу;
- для подготовки к идентификации обязательны P0-параметры и желательно P1;
- сырые наблюдения и производные дескрипторы разделяются типом `measurement_class`.

