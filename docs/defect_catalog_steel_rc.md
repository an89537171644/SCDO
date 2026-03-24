# Defect Catalog for Steel and RC

Каталог дефектов в `v1.1` ориентирован на два основных семейства:

- сталь;
- железобетон.

## Общие поля дефекта

- `defect_type`
- `defect_subtype`
- `damage_mechanism`
- `severity_class`
- `location_on_element`
- `face_or_zone`
- `local_coordinate`
- `inspection_method`
- `confidence_severity`

## Поля для стали

- `section_loss_percent`
- `corrosion_depth`
- `weld_damage_type`
- `bolt_condition`
- `local_buckling_flag`
- `fatigue_crack_length`

## Поля для железобетона

- `crack_width`
- `crack_type`
- `cover_loss_area`
- `rebar_corrosion_class`
- `carbonation_depth`
- `bond_loss_flag`

## Практический смысл

Такой набор позволяет:

- отделять дефект от механизма повреждения;
- хранить локализацию в инженерно пригодном виде;
- поддерживать разные сценарии дальнейшей идентификации и актуализации расчетной схемы.
