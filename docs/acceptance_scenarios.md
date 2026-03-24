# Acceptance Scenarios

## Scenario 1. Demo object export remains mechanically meaningful

- Load `sample_data/demo_bundle.json`.
- Request `GET /exports/objects/{object_id}/observation-package`.
- Verify that `export_version` is `v1.1`.
- Verify that each `element_state_observation_record` contains:
  - `boundary_conditions`
  - `actual_material`
  - `data_coverage`
  - `critical_missing_data_list`

## Scenario 2. Sufficiency index is coverage-weighted

- Load the demo object.
- Request `GET /analytics/objects/{object_id}/information-sufficiency`.
- Verify that response contains:
  - `domain_scores`
  - `level_scores`
  - `responsibility_factor`
  - `requirement_scores`
- Verify that missing items include `coverage`, `scope`, and optional element linkage.

## Scenario 3. Readiness report is task-oriented

- Request `GET /analytics/objects/{object_id}/identification-readiness`.
- Verify that response contains:
  - `geometry_ready`
  - `stiffness_ready`
  - `damage_ready`
  - `material_ready`
  - `boundary_ready`
  - `task_scores`

## Scenario 4. Existing endpoints remain backward-compatible

- Existing routes `/objects`, `/elements`, `/defects`, `/channels`, `/measurements`, `/analytics`, `/exports` continue to answer.
- `GET /exports/objects/{object_id}/observation-package` remains on the same URL.
- Existing fields `total_score`, `p0_score`, `p1_score`, `readiness_level`, `recommended_parameters`, `next_measurements` remain in responses.

## Scenario 5. UI still works for engineer-first flow

- Open the Streamlit UI.
- Verify that the object list still loads.
- Verify that the engineer can:
  - create or edit an object;
  - load measurements;
  - open sufficiency and readiness views;
  - export `observation_package`.

## Scenario 6. Typed measurement import rejects mechanically invalid data

- Create a channel with one of the supported types, for example `deflection`.
- Try to import measurements with an invalid unit, for example `kN`.
- Verify that API returns `400` with a clear validation error.
- Try to import measurements with duplicate `timestamp`.
- Verify that API returns `400` and import is not written to the database.

## Scenario 7. Structural meaning and defect parameterization survive round-trip

- Create an element with:
  - `role_criticality`
  - `consequence_class`
  - `identification_priority`
  - `degradation_mechanisms`
- Create a defect for the same element with:
  - `material_family`
  - `section_loss_percent`
  - `weld_damage_type` or `bolt_condition`
- Request `GET /exports/objects/{object_id}/observation-package`.
- Verify that:
  - the element fields survive in `/elements` and in `element_state_observation_records`;
  - the defect fields survive in `/defects`;
  - existing API routes and old fields continue to work without renaming.
