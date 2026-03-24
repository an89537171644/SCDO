from __future__ import annotations

from datetime import date
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.core.measurement_profiles import build_template_csv
from apps.core.measurement_profiles import get_measurement_profile
from apps.core.measurement_profiles import list_measurement_profiles
from apps.ui.api_client import APIClient
from apps.ui.api_client import APIError
from apps.ui.import_utils import parse_measurement_file
from apps.ui.import_utils import prepare_measurement_records
from apps.ui.import_utils import preview_rows


st.set_page_config(page_title="СКДО", layout="wide")

st.markdown(
    """
    <style>
    .main h1, .main h2, .main h3 { color: #16324f; }
    div.stButton > button, div[data-testid="stFormSubmitButton"] > button, div[data-testid="stDownloadButton"] > button {
        width: 100%;
        min-height: 52px;
        font-size: 18px;
        font-weight: 600;
        border-radius: 12px;
    }
    input, textarea, [data-baseweb="select"] { font-size: 17px !important; }
    [data-testid="stMetricValue"] { font-size: 30px; }
    </style>
    """,
    unsafe_allow_html=True,
)

DEFAULT_API_BASE_URL = os.getenv("SKDO_UI_API_BASE_URL", "http://127.0.0.1:8000")

if "api_base_url" not in st.session_state:
    st.session_state["api_base_url"] = DEFAULT_API_BASE_URL
if "selected_object_id" not in st.session_state:
    st.session_state["selected_object_id"] = None

FRIENDLY_HIERARCHY = {
    "system": "Система",
    "subsystem": "Подсистема",
    "element": "Элемент",
    "zone": "Зона",
}
READINESS_TEXT = {
    "ready": "Готово",
    "partial": "Частично готово",
    "not_ready": "Пока не готово",
}
TASK_STATUS_TEXT = {
    "identifiable": "Можно использовать",
    "qualitative_only": "Пока только качественно",
    "not_ready": "Пока нельзя",
}
REQUIREMENT_LABELS = {
    "object.identity": "Неполный паспорт объекта",
    "object.function_type": "Не указано назначение объекта",
    "element.tree": "Нет дерева элементов",
    "element.geometry": "Не хватает геометрии элементов",
    "element.material": "Не хватает данных о материале",
    "defect.registry": "Нет реестра дефектов",
    "observation.measurements": "Нет базовых измерений",
    "quality.traceability": "Нет сведений об источнике и качестве",
    "element.boundary_conditions": "Нет сведений об опирании и связях",
    "environment.effects": "Нет данных о среде",
    "intervention.history": "Нет истории ремонтов",
    "tests.ndt": "Нет результатов испытаний",
    "measurement.channel_metadata": "Не хватает описания каналов измерений",
}
PROFILE_OPTIONS = {f"{profile.label_ru} ({profile.code})": profile.code for profile in list_measurement_profiles()}
ROLE_CRITICALITY_OPTIONS = {
    "Не указано": None,
    "Высокая": "high",
    "Средняя": "medium",
    "Низкая": "low",
}
ROLE_CRITICALITY_TEXT = {
    "A": "Высокая",
    "high": "Высокая",
    "critical": "Высокая",
    "medium": "Средняя",
    "B": "Средняя",
    "low": "Низкая",
    "C": "Низкая",
}
CONSEQUENCE_CLASS_OPTIONS = {
    "Не указано": None,
    "CC3 / KS-3": "CC3",
    "CC2 / KS-2": "CC2",
    "CC1 / KS-1": "CC1",
}
CONSEQUENCE_CLASS_TEXT = {
    "CC3": "CC3 / KS-3",
    "KS-3": "CC3 / KS-3",
    "CC2": "CC2 / KS-2",
    "KS-2": "CC2 / KS-2",
    "CC1": "CC1 / KS-1",
    "KS-1": "CC1 / KS-1",
}
IDENTIFICATION_PRIORITY_OPTIONS = {
    "Не указано": None,
    "Сначала собрать": "high",
    "Обычный": "medium",
    "Низкий": "low",
}
IDENTIFICATION_PRIORITY_TEXT = {
    "high": "Сначала собрать",
    "critical": "Сначала собрать",
    "medium": "Обычный",
    "normal": "Обычный",
    "low": "Низкий",
}
DEGRADATION_MECHANISM_OPTIONS = {
    "Коррозия": "corrosion",
    "Усталость": "fatigue",
    "Трещины": "cracking",
    "Потеря жёсткости": "stiffness_loss",
    "Износ": "wear",
    "Влага и среда": "environment",
}
DEGRADATION_MECHANISM_TEXT = {value: key for key, value in DEGRADATION_MECHANISM_OPTIONS.items()}
MATERIAL_FAMILY_OPTIONS = {
    "Не указано": None,
    "Сталь": "steel",
    "Железобетон": "concrete",
    "Другое": "other",
}
MATERIAL_FAMILY_TEXT = {
    "steel": "Сталь",
    "concrete": "Железобетон",
    "other": "Другое",
}
BOOL_OPTIONS = {
    "Не указано": None,
    "Да": True,
    "Нет": False,
}


ELEMENT_TEMPLATES: dict[str, dict[str, Any]] = {
    "Без шаблона": {},
    "Стальная балка": {
        "hierarchy_type": "element",
        "element_type": "beam",
        "geometry_type": "line",
        "material_type": "steel",
        "structural_role": "girder",
        "section_family": "I-beam",
        "support_type": "hinged",
        "role_criticality": "high",
        "consequence_class": "CC3",
        "identification_priority": "high",
        "degradation_mechanisms": ["corrosion", "fatigue"],
    },
    "Стальная колонна": {
        "hierarchy_type": "element",
        "element_type": "column",
        "geometry_type": "line",
        "material_type": "steel",
        "structural_role": "column",
        "section_family": "box_or_I",
        "support_type": "fixed",
        "role_criticality": "high",
        "consequence_class": "CC3",
        "identification_priority": "high",
        "degradation_mechanisms": ["corrosion", "stiffness_loss"],
    },
    "Стальная ферма": {
        "hierarchy_type": "element",
        "element_type": "truss",
        "geometry_type": "line",
        "material_type": "steel",
        "structural_role": "truss",
        "section_family": "truss_member",
        "support_type": "hinged",
        "role_criticality": "high",
        "consequence_class": "CC3",
        "identification_priority": "high",
        "degradation_mechanisms": ["fatigue", "corrosion"],
    },
    "Ж/б балка": {
        "hierarchy_type": "element",
        "element_type": "beam",
        "geometry_type": "line",
        "material_type": "concrete",
        "structural_role": "girder",
        "section_family": "rectangular",
        "support_type": "hinged",
        "role_criticality": "high",
        "consequence_class": "CC3",
        "identification_priority": "high",
        "degradation_mechanisms": ["cracking", "environment"],
    },
    "Ж/б плита": {
        "hierarchy_type": "element",
        "element_type": "slab",
        "geometry_type": "surface",
        "material_type": "concrete",
        "structural_role": "slab",
        "section_family": "plate",
        "support_type": "continuous",
        "role_criticality": "medium",
        "consequence_class": "CC2",
        "identification_priority": "medium",
        "degradation_mechanisms": ["cracking", "environment"],
    },
    "Ж/б стена": {
        "hierarchy_type": "element",
        "element_type": "wall",
        "geometry_type": "surface",
        "material_type": "concrete",
        "structural_role": "wall",
        "section_family": "wall",
        "support_type": "fixed",
        "role_criticality": "medium",
        "consequence_class": "CC2",
        "identification_priority": "medium",
        "degradation_mechanisms": ["cracking", "environment"],
    },
    "Опора": {
        "hierarchy_type": "element",
        "element_type": "support",
        "geometry_type": "point",
        "material_type": "concrete",
        "structural_role": "support",
        "section_family": "support",
        "support_type": "fixed",
        "role_criticality": "high",
        "consequence_class": "CC3",
        "identification_priority": "high",
        "degradation_mechanisms": ["environment", "settlement"],
    },
}
ELEMENT_COMPLETENESS_TEXT = {
    "good": "Хорошо заполнен",
    "partial": "Нужно дополнить",
    "poor": "Критически мало данных",
}


def make_client() -> APIClient:
    return APIClient(st.session_state["api_base_url"])


def safe_call(action: str, func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except APIError as exc:
        st.error(f"{action}: {exc}")
        return None


def object_label(item: dict[str, Any]) -> str:
    return f"{item.get('object_code', '')} - {item.get('object_name', '')}"


def format_score(value: float) -> str:
    return f"{value * 100:.0f}%"


def date_to_iso(value: date) -> str:
    return datetime.combine(value, datetime.min.time()).isoformat() + "Z"


def friendly_value(value: Any, labels: dict[str, str]) -> str:
    if value in (None, "", []):
        return ""
    return labels.get(str(value), str(value))


def friendly_values(values: list[str] | None, labels: dict[str, str]) -> str:
    if not values:
        return ""
    return ", ".join(labels.get(item, item) for item in values)


def summarize_defect_details(item: dict[str, Any]) -> str:
    parts: list[str] = []
    if item.get("severity_class"):
        parts.append(f"тяжесть: {item['severity_class']}")
    if item.get("damage_mechanism"):
        parts.append(f"механизм: {item['damage_mechanism']}")
    if item.get("section_loss_percent") is not None:
        parts.append(f"потеря сечения {item['section_loss_percent']}")
    if item.get("corrosion_depth") is not None:
        parts.append(f"коррозия {item['corrosion_depth']}")
    if item.get("weld_damage_type"):
        parts.append(f"сварка: {item['weld_damage_type']}")
    if item.get("bolt_condition"):
        parts.append(f"болты: {item['bolt_condition']}")
    if item.get("fatigue_crack_length") is not None:
        parts.append(f"усталостная трещина {item['fatigue_crack_length']}")
    if item.get("crack_type"):
        parts.append(f"трещина: {item['crack_type']}")
    if item.get("cover_loss_area") is not None:
        parts.append(f"защитный слой {item['cover_loss_area']}")
    if item.get("rebar_corrosion_class"):
        parts.append(f"арматура: {item['rebar_corrosion_class']}")
    if item.get("carbonation_depth") is not None:
        parts.append(f"карбонизация {item['carbonation_depth']}")
    if item.get("local_buckling_flag") is not None:
        parts.append("местная потеря устойчивости: да" if item["local_buckling_flag"] else "местная потеря устойчивости: нет")
    if item.get("bond_loss_flag") is not None:
        parts.append("потеря сцепления: да" if item["bond_loss_flag"] else "потеря сцепления: нет")
    if item.get("face_or_zone"):
        parts.append(f"зона: {item['face_or_zone']}")
    if item.get("local_coordinate"):
        parts.append(f"коорд.: {item['local_coordinate']}")
    return ", ".join(parts[:4])


def build_element_tree(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_parent: dict[str | None, list[dict[str, Any]]] = {}
    for item in elements:
        by_parent.setdefault(item.get("parent_id"), []).append(item)

    rows: list[dict[str, Any]] = []

    def walk(parent_id: str | None, level: int) -> None:
        for item in sorted(by_parent.get(parent_id, []), key=lambda row: row.get("name") or ""):
            rows.append(
                {
                    "Уровень": level,
                    "Тип узла": FRIENDLY_HIERARCHY.get(item.get("hierarchy_type"), item.get("hierarchy_type")),
                    "Название": ("    " * level) + (item.get("name") or ""),
                    "Роль": item.get("structural_role") or "",
                    "Важность": friendly_value(item.get("role_criticality") or item.get("criticality_group"), ROLE_CRITICALITY_TEXT),
                    "Класс последствий": friendly_value(item.get("consequence_class"), CONSEQUENCE_CLASS_TEXT),
                    "Приоритет": friendly_value(item.get("identification_priority"), IDENTIFICATION_PRIORITY_TEXT),
                    "Механизмы": friendly_values(item.get("degradation_mechanisms"), DEGRADATION_MECHANISM_TEXT),
                    "Материал": item.get("material_type") or "",
                }
            )
            walk(item.get("id"), level + 1)

    walk(None, 0)
    return rows


def element_options(elements: list[dict[str, Any]]) -> dict[str, str]:
    return {
        f"{item.get('name')} ({FRIENDLY_HIERARCHY.get(item.get('hierarchy_type'), item.get('hierarchy_type'))})": item["id"]
        for item in elements
    }


def channel_options(channels: list[dict[str, Any]], elements: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    element_names = {item["id"]: item.get("name") for item in elements}
    result: dict[str, dict[str, Any]] = {}
    for channel in channels:
        label = (
            f"{channel.get('channel_code')} - {channel.get('measured_quantity')} "
            f"({element_names.get(channel.get('element_id'), 'без элемента')})"
        )
        result[label] = channel
    return result


def completeness_status(value: float) -> str:
    if value >= 0.75:
        return "good"
    if value >= 0.45:
        return "partial"
    return "poor"


def build_element_completeness_rows(elements: list[dict[str, Any]], information_data: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not information_data:
        return []
    coverage_map = information_data.get("coverage_by_critical_elements") or {}
    rows: list[dict[str, Any]] = []
    for element in elements:
        score = coverage_map.get(element.get("id"))
        if score is None:
            continue
        status = completeness_status(score)
        rows.append(
            {
                "Элемент": element.get("name") or "",
                "Роль": element.get("structural_role") or "",
                "Заполненность": format_score(score),
                "Статус": ELEMENT_COMPLETENESS_TEXT[status],
            }
        )
    return rows


def show_sidebar(objects: list[dict[str, Any]]) -> None:
    st.sidebar.title("СКДО")
    st.sidebar.text_input("Адрес backend API", key="api_base_url", help="Обычно это http://127.0.0.1:8000")

    client = make_client()
    if st.sidebar.button("Проверить связь", use_container_width=True):
        result = safe_call("Не удалось проверить связь", client.health)
        if result:
            st.sidebar.success("Связь с API есть.")

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"[Открыть Swagger]({st.session_state['api_base_url'].rstrip('/')}/docs)")

    object_map = {object_label(item): item["id"] for item in objects}
    labels = ["Не выбран"] + list(object_map.keys())
    current_label = "Не выбран"
    for label, object_id in object_map.items():
        if object_id == st.session_state.get("selected_object_id"):
            current_label = label
            break
    selected_label = st.sidebar.selectbox("Текущий объект", labels, index=labels.index(current_label))
    st.session_state["selected_object_id"] = object_map.get(selected_label)


def show_objects_section(client: APIClient, objects: list[dict[str, Any]]) -> None:
    st.header("Объекты")
    col_list, col_form = st.columns([1.4, 1])

    with col_list:
        if objects:
            st.dataframe(
                [
                    {
                        "Код": item.get("object_code"),
                        "Название": item.get("object_name"),
                        "Адрес": item.get("address") or "",
                        "Назначение": item.get("function_type") or "",
                        "Режим": item.get("current_operational_mode") or "",
                    }
                    for item in objects
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Объектов пока нет. Справа можно создать первый объект.")

    with col_form:
        mode = st.radio(
            "Что сделать",
            ["Создать объект", "Редактировать выбранный объект"],
            horizontal=True,
        )
        current_object = next((item for item in objects if item["id"] == st.session_state.get("selected_object_id")), None)
        if mode == "Редактировать выбранный объект" and not current_object:
            st.warning("Сначала выберите объект слева.")
            return

        defaults = current_object or {}
        with st.form("object_form"):
            object_code = st.text_input("Код объекта", value=defaults.get("object_code", ""))
            object_name = st.text_input("Название объекта", value=defaults.get("object_name", ""))
            address = st.text_input("Адрес", value=defaults.get("address", ""))
            coordinates = st.text_input("Координаты", value=defaults.get("coordinates", ""))
            function_type = st.text_input("Назначение", value=defaults.get("function_type", ""))
            responsibility_class = st.text_input("Класс ответственности", value=defaults.get("responsibility_class", ""))
            year_built = st.number_input("Год постройки", min_value=1900, max_value=2100, value=defaults.get("year_built") or 2000)
            year_commissioned = st.number_input("Год ввода", min_value=1900, max_value=2100, value=defaults.get("year_commissioned") or 2000)
            design_service_life = st.number_input("Срок службы, лет", min_value=1, max_value=500, value=defaults.get("design_service_life") or 50)
            current_operational_mode = st.text_input("Текущий режим работы", value=defaults.get("current_operational_mode", ""))
            source_type = st.text_input("Источник данных", value=defaults.get("source_type", ""))
            submitted = st.form_submit_button("Сохранить", type="primary", use_container_width=True)

        if submitted:
            if not object_code.strip():
                st.error("Введите код объекта.")
                return
            if not object_name.strip():
                st.error("Введите название объекта.")
                return

            payload = {
                "object_code": object_code.strip(),
                "object_name": object_name.strip(),
                "address": address.strip() or None,
                "coordinates": coordinates.strip() or None,
                "function_type": function_type.strip() or None,
                "responsibility_class": responsibility_class.strip() or None,
                "year_built": int(year_built),
                "year_commissioned": int(year_commissioned),
                "design_service_life": int(design_service_life),
                "current_operational_mode": current_operational_mode.strip() or None,
                "source_type": source_type.strip() or None,
            }

            if mode == "Создать объект":
                created = safe_call("Не удалось создать объект", client.create_object, payload)
                if created:
                    st.session_state["selected_object_id"] = created["id"]
                    st.success("Объект создан.")
                    st.rerun()
            else:
                updated = safe_call("Не удалось обновить объект", client.update_object, current_object["id"], payload)
                if updated:
                    st.success("Объект обновлён.")
                    st.rerun()


def show_dashboard_section(
    current_object: dict[str, Any],
    elements: list[dict[str, Any]],
    defects: list[dict[str, Any]],
    channels: list[dict[str, Any]],
    measurements: list[dict[str, Any]],
    information_data: dict[str, Any] | None,
    readiness_data: dict[str, Any] | None,
) -> None:
    st.subheader("Панель объекта")
    left, right = st.columns([1.1, 1])

    with left:
        st.markdown("#### Карточка объекта")
        st.dataframe(
            [
                {"Поле": "Код объекта", "Значение": current_object.get("object_code")},
                {"Поле": "Название", "Значение": current_object.get("object_name")},
                {"Поле": "Назначение", "Значение": current_object.get("function_type") or ""},
                {"Поле": "Класс ответственности", "Значение": current_object.get("responsibility_class") or ""},
                {"Поле": "Режим", "Значение": current_object.get("current_operational_mode") or ""},
            ],
            use_container_width=True,
            hide_index=True,
        )

    with right:
        metric1, metric2, metric3, metric4 = st.columns(4)
        metric1.metric("Элементы", len(elements))
        metric2.metric("Дефекты", len(defects))
        metric3.metric("Каналы", len(channels))
        metric4.metric("Измерения", len(measurements))
        if information_data:
            st.metric("Полнота данных", format_score(information_data["total_score"]))
        if readiness_data:
            st.metric("Готовность", READINESS_TEXT.get(readiness_data["readiness_level"], readiness_data["readiness_level"]))

    if information_data and information_data.get("missing_items"):
        st.markdown("#### Что ещё стоит добавить")
        st.dataframe(
            [
                {
                    "Что не хватает": REQUIREMENT_LABELS.get(item.get("code"), item.get("description")),
                    "Покрытие": format_score(item.get("coverage") or 0.0),
                }
                for item in information_data["missing_items"][:8]
            ],
            use_container_width=True,
            hide_index=True,
        )


def show_elements_tab(client: APIClient, selected_object_id: str, elements: list[dict[str, Any]]) -> None:
    st.subheader("Дерево элементов")
    tree_rows = build_element_tree(elements)
    if tree_rows:
        st.dataframe(tree_rows, use_container_width=True, hide_index=True)
    else:
        st.info("Элементы пока не добавлены.")

    options = element_options(elements)
    with st.form("element_form"):
        st.markdown("#### Добавить элемент")
        parent_label = st.selectbox("Куда добавить", ["Без родителя"] + list(options.keys()))
        hierarchy_label = st.selectbox("Тип узла", list(FRIENDLY_HIERARCHY.values()), index=2)
        name = st.text_input("Название")
        structural_role = st.text_input("Роль элемента")
        role_criticality_label = st.selectbox("Насколько важен элемент", list(ROLE_CRITICALITY_OPTIONS.keys()))
        consequence_class_label = st.selectbox("Класс последствий", list(CONSEQUENCE_CLASS_OPTIONS.keys()))
        identification_priority_label = st.selectbox("Приоритет для расчёта", list(IDENTIFICATION_PRIORITY_OPTIONS.keys()))
        degradation_labels = st.multiselect("Что может ухудшать состояние", list(DEGRADATION_MECHANISM_OPTIONS.keys()))
        element_type = st.text_input("Тип элемента")
        material_type = st.text_input("Материал")
        material_grade_design = st.text_input("Марка материала")
        support_type = st.text_input("Тип опирания")
        col1, col2, col3 = st.columns(3)
        with col1:
            length = st.number_input("Длина", min_value=0.0, value=0.0)
        with col2:
            span = st.number_input("Пролёт", min_value=0.0, value=0.0)
        with col3:
            height = st.number_input("Высота", min_value=0.0, value=0.0)
        coordinates_global = st.text_input("Координаты")
        submitted = st.form_submit_button("Сохранить", type="primary", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("Введите название элемента.")
            return

        hierarchy_type = next(key for key, value in FRIENDLY_HIERARCHY.items() if value == hierarchy_label)
        role_criticality = ROLE_CRITICALITY_OPTIONS[role_criticality_label]
        payload = {
            "object_id": selected_object_id,
            "parent_id": options.get(parent_label),
            "hierarchy_type": hierarchy_type,
            "name": name.strip(),
            "structural_role": structural_role.strip() or None,
            "criticality_group": {"high": "A", "medium": "B", "low": "C"}.get(role_criticality),
            "role_criticality": role_criticality,
            "consequence_class": CONSEQUENCE_CLASS_OPTIONS[consequence_class_label],
            "identification_priority": IDENTIFICATION_PRIORITY_OPTIONS[identification_priority_label],
            "degradation_mechanisms": [DEGRADATION_MECHANISM_OPTIONS[label] for label in degradation_labels] or None,
            "element_type": element_type.strip() or None,
            "material_type": material_type.strip() or None,
            "material_grade_design": material_grade_design.strip() or None,
            "support_type": support_type.strip() or None,
            "length": length or None,
            "span": span or None,
            "height": height or None,
            "coordinates_global": coordinates_global.strip() or None,
        }
        created = safe_call("Не удалось добавить элемент", client.create_element, payload)
        if created:
            st.success("Элемент добавлен.")
            st.rerun()


def show_elements_tab(
    client: APIClient,
    selected_object_id: str,
    elements: list[dict[str, Any]],
    information_data: dict[str, Any] | None = None,
) -> None:
    st.subheader("Дерево элементов")
    tree_rows = build_element_tree(elements)
    if tree_rows:
        st.dataframe(tree_rows, use_container_width=True, hide_index=True)
    else:
        st.info("Элементы пока не добавлены.")

    completeness_rows = build_element_completeness_rows(elements, information_data)
    if completeness_rows:
        st.markdown("#### Заполненность по важным элементам")
        st.dataframe(completeness_rows, use_container_width=True, hide_index=True)

    options = element_options(elements)

    def option_label_by_value(options_map: dict[str, Any], target: Any) -> str:
        for label, value in options_map.items():
            if value == target:
                return label
        return next(iter(options_map.keys()))

    def optional_number(value: float) -> float | None:
        return value or None

    with st.form("element_form_v11"):
        st.markdown("#### Добавить элемент")
        template_name = st.selectbox("Шаблон элемента", list(ELEMENT_TEMPLATES.keys()))
        template = ELEMENT_TEMPLATES[template_name]
        parent_label = st.selectbox("Куда добавить", ["Без родителя"] + list(options.keys()))

        hierarchy_labels = list(FRIENDLY_HIERARCHY.values())
        hierarchy_default = FRIENDLY_HIERARCHY.get(template.get("hierarchy_type", "element"), FRIENDLY_HIERARCHY["element"])
        hierarchy_label = st.selectbox("Тип узла", hierarchy_labels, index=hierarchy_labels.index(hierarchy_default))
        name = st.text_input("Название", value=template.get("name", ""))
        structural_role = st.text_input("Роль элемента", value=template.get("structural_role", ""))

        role_criticality_label = st.selectbox(
            "Насколько важен элемент",
            list(ROLE_CRITICALITY_OPTIONS.keys()),
            index=list(ROLE_CRITICALITY_OPTIONS.keys()).index(option_label_by_value(ROLE_CRITICALITY_OPTIONS, template.get("role_criticality"))),
        )
        consequence_class_label = st.selectbox(
            "Класс последствий",
            list(CONSEQUENCE_CLASS_OPTIONS.keys()),
            index=list(CONSEQUENCE_CLASS_OPTIONS.keys()).index(option_label_by_value(CONSEQUENCE_CLASS_OPTIONS, template.get("consequence_class"))),
        )
        identification_priority_label = st.selectbox(
            "Приоритет для расчета",
            list(IDENTIFICATION_PRIORITY_OPTIONS.keys()),
            index=list(IDENTIFICATION_PRIORITY_OPTIONS.keys()).index(option_label_by_value(IDENTIFICATION_PRIORITY_OPTIONS, template.get("identification_priority"))),
        )
        default_deg = [label for label, value in DEGRADATION_MECHANISM_OPTIONS.items() if value in (template.get("degradation_mechanisms") or [])]
        degradation_labels = st.multiselect("Что может ухудшать состояние", list(DEGRADATION_MECHANISM_OPTIONS.keys()), default=default_deg)

        col_main_1, col_main_2, col_main_3 = st.columns(3)
        with col_main_1:
            element_type = st.text_input("Тип элемента", value=template.get("element_type", ""))
            geometry_type = st.text_input("Тип геометрии", value=template.get("geometry_type", ""))
            material_type = st.text_input("Материал", value=template.get("material_type", ""))
            section_name = st.text_input("Название сечения", value=template.get("section_name", ""))
            section_family = st.text_input("Семейство сечения", value=template.get("section_family", ""))
        with col_main_2:
            material_grade_design = st.text_input("Марка по проекту", value=template.get("material_grade_design", ""))
            material_grade_actual = st.text_input("Марка по факту", value=template.get("material_grade_actual", ""))
            steel_grade_design = st.text_input("Класс стали по проекту", value=template.get("steel_grade_design", ""))
            steel_grade_actual = st.text_input("Класс стали по факту", value=template.get("steel_grade_actual", ""))
            support_type = st.text_input("Тип опирания", value=template.get("support_type", ""))
        with col_main_3:
            joint_type = st.text_input("Тип узла", value=template.get("joint_type", ""))
            weld_type = st.text_input("Тип сварки", value=template.get("weld_type", ""))
            bolt_class = st.text_input("Класс болтов", value=template.get("bolt_class", ""))
            concrete_class_design = st.text_input("Класс бетона по проекту", value=template.get("concrete_class_design", ""))
            concrete_class_actual = st.text_input("Класс бетона по факту", value=template.get("concrete_class_actual", ""))

        dim_col1, dim_col2, dim_col3 = st.columns(3)
        with dim_col1:
            length = st.number_input("Длина", min_value=0.0, value=float(template.get("length", 0.0) or 0.0))
            span = st.number_input("Пролет", min_value=0.0, value=float(template.get("span", 0.0) or 0.0))
            height = st.number_input("Высота", min_value=0.0, value=float(template.get("height", 0.0) or 0.0))
        with dim_col2:
            thickness = st.number_input("Толщина", min_value=0.0, value=float(template.get("thickness", 0.0) or 0.0))
            area = st.number_input("Площадь", min_value=0.0, value=float(template.get("area", 0.0) or 0.0))
            material_density = st.number_input("Плотность материала", min_value=0.0, value=float(template.get("material_density", 0.0) or 0.0))
        with dim_col3:
            coordinates_global = st.text_input("Координаты", value=template.get("coordinates_global", ""))
            coordinates_local = st.text_input("Локальные координаты", value=template.get("coordinates_local", ""))
            source_type = st.text_input("Источник данных", value=template.get("source_type", ""))

        with st.expander("Дополнительные механические поля"):
            mech1, mech2, mech3 = st.columns(3)
            with mech1:
                inertia_x = st.number_input("Инерция Ix", min_value=0.0, value=float(template.get("inertia_x", 0.0) or 0.0))
                inertia_y = st.number_input("Инерция Iy", min_value=0.0, value=float(template.get("inertia_y", 0.0) or 0.0))
                section_modulus_x = st.number_input("Момент сопротивления Wx", min_value=0.0, value=float(template.get("section_modulus_x", 0.0) or 0.0))
                section_modulus_y = st.number_input("Момент сопротивления Wy", min_value=0.0, value=float(template.get("section_modulus_y", 0.0) or 0.0))
                torsion_constant = st.number_input("Крутильная постоянная", min_value=0.0, value=float(template.get("torsion_constant", 0.0) or 0.0))
                buckling_length_x = st.number_input("Расчетная длина по X", min_value=0.0, value=float(template.get("buckling_length_x", 0.0) or 0.0))
                buckling_length_y = st.number_input("Расчетная длина по Y", min_value=0.0, value=float(template.get("buckling_length_y", 0.0) or 0.0))
            with mech2:
                elastic_modulus_design = st.number_input("Модуль упругости по проекту", min_value=0.0, value=float(template.get("elastic_modulus_design", 0.0) or 0.0))
                elastic_modulus_actual = st.number_input("Модуль упругости по факту", min_value=0.0, value=float(template.get("elastic_modulus_actual", 0.0) or 0.0))
                strength_design = st.number_input("Прочность по проекту", min_value=0.0, value=float(template.get("strength_design", 0.0) or 0.0))
                strength_actual = st.number_input("Прочность по факту", min_value=0.0, value=float(template.get("strength_actual", 0.0) or 0.0))
                cover_thickness = st.number_input("Защитный слой", min_value=0.0, value=float(template.get("cover_thickness", 0.0) or 0.0))
                reinforcement_ratio = st.number_input("Коэффициент армирования", min_value=0.0, value=float(template.get("reinforcement_ratio", 0.0) or 0.0))
                rebar_area = st.number_input("Площадь арматуры", min_value=0.0, value=float(template.get("rebar_area", 0.0) or 0.0))
            with mech3:
                rebar_class = st.text_input("Класс арматуры", value=template.get("rebar_class", ""))
                carbonation_depth = st.number_input("Глубина карбонизации", min_value=0.0, value=float(template.get("carbonation_depth", 0.0) or 0.0))
                chloride_exposure_class = st.text_input("Класс хлоридного воздействия", value=template.get("chloride_exposure_class", ""))
                corrosion_loss_mm = st.number_input("Потеря толщины, мм", min_value=0.0, value=float(template.get("corrosion_loss_mm", 0.0) or 0.0))
                support_stiffness = st.number_input("Общая жесткость опирания", min_value=0.0, value=float(template.get("support_stiffness", 0.0) or 0.0))
                joint_flexibility = st.number_input("Общая податливость узла", min_value=0.0, value=float(template.get("joint_flexibility", 0.0) or 0.0))

            sup1, sup2, sup3 = st.columns(3)
            with sup1:
                support_kx = st.number_input("Kx", min_value=0.0, value=float(template.get("support_kx", 0.0) or 0.0))
                support_ky = st.number_input("Ky", min_value=0.0, value=float(template.get("support_ky", 0.0) or 0.0))
                support_kz = st.number_input("Kz", min_value=0.0, value=float(template.get("support_kz", 0.0) or 0.0))
            with sup2:
                support_rx = st.number_input("Rx", min_value=0.0, value=float(template.get("support_rx", 0.0) or 0.0))
                support_ry = st.number_input("Ry", min_value=0.0, value=float(template.get("support_ry", 0.0) or 0.0))
                support_rz = st.number_input("Rz", min_value=0.0, value=float(template.get("support_rz", 0.0) or 0.0))
            with sup3:
                joint_flexibility_x = st.number_input("Податливость узла X", min_value=0.0, value=float(template.get("joint_flexibility_x", 0.0) or 0.0))
                joint_flexibility_y = st.number_input("Податливость узла Y", min_value=0.0, value=float(template.get("joint_flexibility_y", 0.0) or 0.0))
                joint_flexibility_z = st.number_input("Податливость узла Z", min_value=0.0, value=float(template.get("joint_flexibility_z", 0.0) or 0.0))

        submitted = st.form_submit_button("Сохранить", type="primary", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("Введите название элемента.")
            return

        hierarchy_type = next(key for key, value in FRIENDLY_HIERARCHY.items() if value == hierarchy_label)
        role_criticality = ROLE_CRITICALITY_OPTIONS[role_criticality_label]
        payload = {
            "object_id": selected_object_id,
            "parent_id": options.get(parent_label),
            "hierarchy_type": hierarchy_type,
            "name": name.strip(),
            "structural_role": structural_role.strip() or None,
            "criticality_group": {"high": "A", "medium": "B", "low": "C"}.get(role_criticality),
            "role_criticality": role_criticality,
            "consequence_class": CONSEQUENCE_CLASS_OPTIONS[consequence_class_label],
            "identification_priority": IDENTIFICATION_PRIORITY_OPTIONS[identification_priority_label],
            "degradation_mechanisms": [DEGRADATION_MECHANISM_OPTIONS[label] for label in degradation_labels] or None,
            "element_type": element_type.strip() or None,
            "geometry_type": geometry_type.strip() or None,
            "material_type": material_type.strip() or None,
            "section_name": section_name.strip() or None,
            "section_family": section_family.strip() or None,
            "material_grade_design": material_grade_design.strip() or None,
            "material_grade_actual": material_grade_actual.strip() or None,
            "steel_grade_design": steel_grade_design.strip() or None,
            "steel_grade_actual": steel_grade_actual.strip() or None,
            "concrete_class_design": concrete_class_design.strip() or None,
            "concrete_class_actual": concrete_class_actual.strip() or None,
            "rebar_class": rebar_class.strip() or None,
            "weld_type": weld_type.strip() or None,
            "bolt_class": bolt_class.strip() or None,
            "support_type": support_type.strip() or None,
            "joint_type": joint_type.strip() or None,
            "coordinates_global": coordinates_global.strip() or None,
            "coordinates_local": coordinates_local.strip() or None,
            "source_type": source_type.strip() or None,
            "length": optional_number(length),
            "span": optional_number(span),
            "height": optional_number(height),
            "thickness": optional_number(thickness),
            "area": optional_number(area),
            "inertia_x": optional_number(inertia_x),
            "inertia_y": optional_number(inertia_y),
            "section_modulus_x": optional_number(section_modulus_x),
            "section_modulus_y": optional_number(section_modulus_y),
            "torsion_constant": optional_number(torsion_constant),
            "buckling_length_x": optional_number(buckling_length_x),
            "buckling_length_y": optional_number(buckling_length_y),
            "elastic_modulus_design": optional_number(elastic_modulus_design),
            "elastic_modulus_actual": optional_number(elastic_modulus_actual),
            "strength_design": optional_number(strength_design),
            "strength_actual": optional_number(strength_actual),
            "material_density": optional_number(material_density),
            "cover_thickness": optional_number(cover_thickness),
            "reinforcement_ratio": optional_number(reinforcement_ratio),
            "rebar_area": optional_number(rebar_area),
            "carbonation_depth": optional_number(carbonation_depth),
            "chloride_exposure_class": chloride_exposure_class.strip() or None,
            "corrosion_loss_mm": optional_number(corrosion_loss_mm),
            "support_stiffness": optional_number(support_stiffness),
            "support_kx": optional_number(support_kx),
            "support_ky": optional_number(support_ky),
            "support_kz": optional_number(support_kz),
            "support_rx": optional_number(support_rx),
            "support_ry": optional_number(support_ry),
            "support_rz": optional_number(support_rz),
            "joint_flexibility": optional_number(joint_flexibility),
            "joint_flexibility_x": optional_number(joint_flexibility_x),
            "joint_flexibility_y": optional_number(joint_flexibility_y),
            "joint_flexibility_z": optional_number(joint_flexibility_z),
        }
        created = safe_call("Не удалось добавить элемент", client.create_element, payload)
        if created:
            st.success("Элемент добавлен.")
            st.rerun()


def show_defects_tab(client: APIClient, selected_object_id: str, elements: list[dict[str, Any]], defects: list[dict[str, Any]]) -> None:
    st.subheader("Дефекты")
    element_names = {item["id"]: item.get("name") for item in elements}
    if defects:
        st.dataframe(
            [
                {
                    "Элемент": element_names.get(item.get("element_id"), ""),
                    "Тип дефекта": item.get("defect_type"),
                    "Материал": friendly_value(item.get("material_family"), MATERIAL_FAMILY_TEXT),
                    "Место": item.get("location_on_element"),
                    "Дата": item.get("detection_date"),
                    "Статус": item.get("defect_status") or "",
                    "Подробности": summarize_defect_details(item),
                }
                for item in defects
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Дефектов пока нет.")

    options = element_options(elements)
    if not options:
        st.warning("Сначала добавьте хотя бы один элемент.")
        return

    with st.form("defect_form"):
        st.markdown("#### Добавить дефект")
        element_label = st.selectbox("Элемент", list(options.keys()))
        material_family_label = st.selectbox("Материал элемента", list(MATERIAL_FAMILY_OPTIONS.keys()))
        defect_type = st.text_input("Тип дефекта")
        defect_subtype = st.text_input("Уточнение")
        element_classifier = st.text_input("Какой это элемент")
        location_on_element = st.text_input("Где находится дефект")
        detection_date = st.date_input("Дата обнаружения", value=date.today())
        defect_status = st.text_input("Статус")

        st.markdown("##### Основные размеры")
        col1, col2, col3 = st.columns(3)
        with col1:
            crack_width = st.number_input("Ширина трещины", min_value=0.0, value=0.0)
        with col2:
            corrosion_area = st.number_input("Площадь повреждения", min_value=0.0, value=0.0)
        with col3:
            corrosion_depth = st.number_input("Глубина коррозии", min_value=0.0, value=0.0)

        material_family = MATERIAL_FAMILY_OPTIONS[material_family_label]
        if material_family == "steel":
            st.caption("Для стали можно указать потерю сечения и состояние сварных или болтовых узлов.")
        elif material_family == "concrete":
            st.caption("Для железобетона можно указать тип трещины, состояние защитного слоя и арматуры.")

        col4, col5 = st.columns(2)
        with col4:
            section_loss_percent = st.number_input("Потеря сечения, %", min_value=0.0, max_value=100.0, value=0.0)
            weld_damage_type = st.text_input("Повреждение сварного шва")
            fatigue_crack_length = st.number_input("Длина усталостной трещины", min_value=0.0, value=0.0)
            crack_type = st.text_input("Тип трещины")
            cover_loss_area = st.number_input("Площадь потери защитного слоя", min_value=0.0, value=0.0)
        with col5:
            bolt_condition = st.text_input("Состояние болтового узла")
            rebar_corrosion_class = st.text_input("Состояние арматуры")
            carbonation_depth = st.number_input("Глубина карбонизации", min_value=0.0, value=0.0)
            local_buckling_label = st.selectbox("Есть местная потеря устойчивости", list(BOOL_OPTIONS.keys()))
            bond_loss_label = st.selectbox("Есть потеря сцепления", list(BOOL_OPTIONS.keys()))

        source_document = st.text_input("Документ-источник")
        submitted = st.form_submit_button("Сохранить", type="primary", use_container_width=True)

    if submitted:
        if not defect_type.strip():
            st.error("Введите тип дефекта.")
            return
        if not location_on_element.strip():
            st.error("Введите место дефекта.")
            return

        payload = {
            "object_id": selected_object_id,
            "element_id": options[element_label],
            "defect_type": defect_type.strip(),
            "defect_subtype": defect_subtype.strip() or None,
            "material_family": material_family,
            "element_classifier": element_classifier.strip() or None,
            "location_on_element": location_on_element.strip(),
            "detection_date": date_to_iso(detection_date),
            "defect_status": defect_status.strip() or None,
            "crack_width": crack_width or None,
            "corrosion_area": corrosion_area or None,
            "corrosion_depth": corrosion_depth or None,
            "section_loss_percent": section_loss_percent or None,
            "weld_damage_type": weld_damage_type.strip() or None,
            "bolt_condition": bolt_condition.strip() or None,
            "local_buckling_flag": BOOL_OPTIONS[local_buckling_label],
            "fatigue_crack_length": fatigue_crack_length or None,
            "crack_type": crack_type.strip() or None,
            "cover_loss_area": cover_loss_area or None,
            "rebar_corrosion_class": rebar_corrosion_class.strip() or None,
            "carbonation_depth": carbonation_depth or None,
            "bond_loss_flag": BOOL_OPTIONS[bond_loss_label],
            "source_document": source_document.strip() or None,
        }
        created = safe_call("Не удалось добавить дефект", client.create_defect, payload)
        if created:
            st.success("Дефект добавлен.")
            st.rerun()


def show_defects_tab(client: APIClient, selected_object_id: str, elements: list[dict[str, Any]], defects: list[dict[str, Any]]) -> None:
    st.subheader("Дефекты")
    element_names = {item["id"]: item.get("name") for item in elements}
    if defects:
        st.dataframe(
            [
                {
                    "Элемент": element_names.get(item.get("element_id"), ""),
                    "Тип дефекта": item.get("defect_type"),
                    "Тяжесть": item.get("severity_class") or "",
                    "Зона": item.get("face_or_zone") or "",
                    "Место": item.get("location_on_element"),
                    "Дата": item.get("detection_date"),
                    "Статус": item.get("defect_status") or "",
                    "Подробности": summarize_defect_details(item),
                }
                for item in defects
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Дефектов пока нет.")

    options = element_options(elements)
    if not options:
        st.warning("Сначала добавьте хотя бы один элемент.")
        return

    with st.form("defect_form_v11"):
        st.markdown("#### Добавить дефект")
        element_label = st.selectbox("Элемент", list(options.keys()))
        material_family_label = st.selectbox("Материал элемента", list(MATERIAL_FAMILY_OPTIONS.keys()))
        defect_type = st.text_input("Тип дефекта")
        defect_subtype = st.text_input("Уточнение")
        damage_mechanism = st.text_input("Механизм повреждения")
        severity_class = st.text_input("Класс тяжести")
        element_classifier = st.text_input("Какой это элемент")
        location_on_element = st.text_input("Где находится дефект")
        face_or_zone = st.text_input("Грань или зона")
        local_coordinate = st.text_input("Локальная координата")
        inspection_method = st.text_input("Способ выявления", value="visual")
        detection_date = st.date_input("Дата обнаружения", value=date.today())
        defect_status = st.text_input("Статус")

        st.markdown("##### Основные размеры")
        col1, col2, col3 = st.columns(3)
        with col1:
            crack_width = st.number_input("Ширина трещины", min_value=0.0, value=0.0)
            section_loss_percent = st.number_input("Потеря сечения, %", min_value=0.0, max_value=100.0, value=0.0)
            fatigue_crack_length = st.number_input("Длина усталостной трещины", min_value=0.0, value=0.0)
            growth_rate_estimate = st.number_input("Оценка роста дефекта", min_value=0.0, value=0.0)
        with col2:
            corrosion_area = st.number_input("Площадь повреждения", min_value=0.0, value=0.0)
            corrosion_depth = st.number_input("Глубина коррозии", min_value=0.0, value=0.0)
            cover_loss_area = st.number_input("Площадь потери защитного слоя", min_value=0.0, value=0.0)
            confidence_severity = st.number_input("Уверенность в тяжести", min_value=0.0, max_value=1.0, value=0.0)
        with col3:
            carbonation_depth = st.number_input("Глубина карбонизации", min_value=0.0, value=0.0)
            crack_type = st.text_input("Тип трещины")
            weld_damage_type = st.text_input("Повреждение сварного шва")
            bolt_condition = st.text_input("Состояние болтового узла")

        col4, col5 = st.columns(2)
        with col4:
            rebar_corrosion_class = st.text_input("Состояние арматуры")
            local_buckling_label = st.selectbox("Есть местная потеря устойчивости", list(BOOL_OPTIONS.keys()))
        with col5:
            source_document = st.text_input("Документ-источник")
            bond_loss_label = st.selectbox("Есть потеря сцепления", list(BOOL_OPTIONS.keys()))

        submitted = st.form_submit_button("Сохранить", type="primary", use_container_width=True)

    if submitted:
        if not defect_type.strip():
            st.error("Введите тип дефекта.")
            return
        if not location_on_element.strip():
            st.error("Введите место дефекта.")
            return

        payload = {
            "object_id": selected_object_id,
            "element_id": options[element_label],
            "defect_type": defect_type.strip(),
            "defect_subtype": defect_subtype.strip() or None,
            "damage_mechanism": damage_mechanism.strip() or None,
            "severity_class": severity_class.strip() or None,
            "material_family": MATERIAL_FAMILY_OPTIONS[material_family_label],
            "element_classifier": element_classifier.strip() or None,
            "location_on_element": location_on_element.strip(),
            "face_or_zone": face_or_zone.strip() or None,
            "local_coordinate": local_coordinate.strip() or None,
            "inspection_method": inspection_method.strip() or None,
            "detection_date": date_to_iso(detection_date),
            "defect_status": defect_status.strip() or None,
            "crack_width": crack_width or None,
            "corrosion_area": corrosion_area or None,
            "corrosion_depth": corrosion_depth or None,
            "section_loss_percent": section_loss_percent or None,
            "weld_damage_type": weld_damage_type.strip() or None,
            "bolt_condition": bolt_condition.strip() or None,
            "local_buckling_flag": BOOL_OPTIONS[local_buckling_label],
            "fatigue_crack_length": fatigue_crack_length or None,
            "crack_type": crack_type.strip() or None,
            "cover_loss_area": cover_loss_area or None,
            "rebar_corrosion_class": rebar_corrosion_class.strip() or None,
            "carbonation_depth": carbonation_depth or None,
            "growth_rate_estimate": growth_rate_estimate or None,
            "confidence_severity": confidence_severity or None,
            "bond_loss_flag": BOOL_OPTIONS[bond_loss_label],
            "source_document": source_document.strip() or None,
        }
        created = safe_call("Не удалось добавить дефект", client.create_defect, payload)
        if created:
            st.success("Дефект добавлен.")
            st.rerun()


def show_measurements_tab(
    client: APIClient,
    selected_object_id: str,
    elements: list[dict[str, Any]],
    channels: list[dict[str, Any]],
    measurements: list[dict[str, Any]],
) -> None:
    st.subheader("Измерения")
    options = element_options(elements)
    if not options:
        st.warning("Сначала добавьте элемент.")
        return

    st.markdown("#### 1. Канал измерений")
    with st.form("channel_form"):
        element_label = st.selectbox("Для какого элемента канал", list(options.keys()))
        channel_code = st.text_input("Код канала")
        measurement_type_label = st.selectbox("Тип измерения", list(PROFILE_OPTIONS.keys()), index=0)
        measurement_type = PROFILE_OPTIONS[measurement_type_label]
        profile = get_measurement_profile(measurement_type)
        unit = st.selectbox("Единица измерения", list(profile.allowed_units))
        sensor_type = st.text_input("Прибор", value="LVDT")
        spatial_location = st.text_input("Где установлен датчик", value="midspan")
        st.caption(
            f"Диапазон для {profile.label_ru}: {profile.unit_ranges[unit][0]} .. {profile.unit_ranges[unit][1]} {unit}. "
            f"Правило ресемплинга: {profile.resampling_rule}."
        )
        create_channel = st.form_submit_button("Сохранить", type="primary", use_container_width=True)

    if create_channel:
        if not channel_code.strip():
            st.error("Введите код канала.")
            return
        created = safe_call(
            "Не удалось создать канал",
            client.create_channel,
            {
                "object_id": selected_object_id,
                "element_id": options[element_label],
                "channel_code": channel_code.strip(),
                "sensor_type": sensor_type.strip() or None,
                "measured_quantity": measurement_type,
                "unit": unit,
                "measurement_class": "raw",
                "spatial_location": spatial_location.strip() or None,
            },
        )
        if created:
            st.success("Канал сохранён.")
            st.rerun()

    st.markdown("#### 2. Загрузка файла CSV/XLSX")
    channel_map = channel_options(channels, elements)
    if not channel_map:
        st.info("Сначала создайте канал измерений.")
    else:
        selected_channel_label = st.selectbox("Канал для загрузки", list(channel_map.keys()))
        selected_channel = channel_map[selected_channel_label]
        try:
            channel_profile = get_measurement_profile(selected_channel.get("measured_quantity", ""))
            st.caption(
                f"Тип: {channel_profile.label_ru}. Разрешённые единицы: {', '.join(channel_profile.allowed_units)}. "
                f"Правило ресемплинга: {channel_profile.resampling_rule}."
            )
            st.download_button(
                f"Скачать шаблон для типа {channel_profile.code}",
                data=build_template_csv(channel_profile.code),
                file_name=f"{channel_profile.code}_template.csv",
                mime="text/csv",
                use_container_width=True,
            )
        except Exception:
            st.warning("Для выбранного канала не найден профиль измерения. Проверьте тип канала.")

        st.caption(
            "Допустимые колонки: дата/время, значение, единица, источник, статус, метод, точность, место. "
            "Можно использовать русские или английские названия."
        )
        upload_file = st.file_uploader("Файл с измерениями", type=["csv", "xlsx"])
        if upload_file is not None:
            try:
                rows = parse_measurement_file(upload_file.name, upload_file.getvalue())
                if not rows:
                    st.warning("Файл пустой.")
                else:
                    st.write("Предпросмотр")
                    st.dataframe(preview_rows(rows), use_container_width=True, hide_index=True)
                    if st.button("Загрузить измерения", type="primary", use_container_width=True):
                        prepared = prepare_measurement_records(
                            rows,
                            object_id=selected_object_id,
                            element_id=selected_channel["element_id"],
                            channel_id=selected_channel["id"],
                            default_unit=selected_channel["unit"],
                        )
                        imported = safe_call(
                            "Не удалось загрузить измерения",
                            client.import_json,
                            "measurements",
                            prepared,
                        )
                        if imported is not None:
                            st.success(f"Загружено записей: {len(imported)}")
                            st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    st.markdown("#### 3. Последние загруженные измерения")
    if measurements:
        chart_rows = sorted(
            [
                {"timestamp": item.get("timestamp"), "value": item.get("value")}
                for item in measurements
                if item.get("timestamp") and item.get("value") is not None
            ],
            key=lambda item: item["timestamp"],
        )
        if chart_rows:
            chart_df = pd.DataFrame(chart_rows)
            chart_df["timestamp"] = pd.to_datetime(chart_df["timestamp"])
            chart_df = chart_df.set_index("timestamp")
            st.line_chart(chart_df)

        st.dataframe(
            [
                {
                    "Дата": item.get("timestamp"),
                    "Значение": item.get("value"),
                    "Ед.": item.get("unit"),
                    "Источник": item.get("source_type") or "",
                }
                for item in measurements[:20]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Измерения пока не загружены.")


def show_measurements_tab(
    client: APIClient,
    selected_object_id: str,
    elements: list[dict[str, Any]],
    channels: list[dict[str, Any]],
    measurements: list[dict[str, Any]],
) -> None:
    st.subheader("Измерения")
    options = element_options(elements)
    if not options:
        st.warning("Сначала добавьте элемент.")
        return

    st.markdown("#### 1. Канал измерений")
    with st.form("channel_form_v11"):
        element_label = st.selectbox("Для какого элемента канал", list(options.keys()))
        channel_code = st.text_input("Код канала")
        measurement_type_label = st.selectbox("Тип измерения", list(PROFILE_OPTIONS.keys()), index=0)
        measurement_type = PROFILE_OPTIONS[measurement_type_label]
        profile = get_measurement_profile(measurement_type)
        unit = st.selectbox("Единица измерения", list(profile.allowed_units))
        sensor_type = st.text_input("Прибор", value="LVDT")
        spatial_location = st.text_input("Где установлен датчик", value="midspan")
        axis_direction = st.text_input("Направление оси", value="Z")
        sign_convention = st.text_input("Правило знака", value="downward_positive" if measurement_type == "deflection" else "")
        load_case_reference = st.text_input("Сценарий нагрузки", value="normal_operation")
        aggregation_method = st.text_input("Агрегация", value=profile.resampling_rule)
        device_id = st.text_input("Код прибора")
        calibration_reference = st.text_input("Калибровка")
        temperature_compensated_label = st.selectbox("Есть температурная компенсация", list(BOOL_OPTIONS.keys()))
        st.caption(
            f"Диапазон для {profile.label_ru}: {profile.unit_ranges[unit][0]} .. {profile.unit_ranges[unit][1]} {unit}. "
            f"Правило ресемплинга: {profile.resampling_rule}."
        )
        create_channel = st.form_submit_button("Сохранить", type="primary", use_container_width=True)

    if create_channel:
        if not channel_code.strip():
            st.error("Введите код канала.")
            return
        created = safe_call(
            "Не удалось создать канал",
            client.create_channel,
            {
                "object_id": selected_object_id,
                "element_id": options[element_label],
                "channel_code": channel_code.strip(),
                "sensor_type": sensor_type.strip() or None,
                "measured_quantity": measurement_type,
                "unit": unit,
                "measurement_class": "raw",
                "spatial_location": spatial_location.strip() or None,
                "axis_direction": axis_direction.strip() or None,
                "sign_convention": sign_convention.strip() or None,
                "load_case_reference": load_case_reference.strip() or None,
                "temperature_compensated": BOOL_OPTIONS[temperature_compensated_label],
                "aggregation_method": aggregation_method.strip() or None,
                "device_id": device_id.strip() or None,
                "calibration_reference": calibration_reference.strip() or None,
            },
        )
        if created:
            st.success("Канал сохранен.")
            st.rerun()

    st.markdown("#### 2. Загрузка файла CSV/XLSX")
    channel_map = channel_options(channels, elements)
    if not channel_map:
        st.info("Сначала создайте канал измерений.")
    else:
        selected_channel_label = st.selectbox("Канал для загрузки", list(channel_map.keys()))
        selected_channel = channel_map[selected_channel_label]
        try:
            channel_profile = get_measurement_profile(selected_channel.get("measured_quantity", ""))
            st.caption(
                f"Тип: {channel_profile.label_ru}. Разрешенные единицы: {', '.join(channel_profile.allowed_units)}. "
                f"Правило ресемплинга: {channel_profile.resampling_rule}."
            )
            st.download_button(
                f"Скачать шаблон для типа {channel_profile.code}",
                data=build_template_csv(channel_profile.code),
                file_name=f"{channel_profile.code}_template.csv",
                mime="text/csv",
                use_container_width=True,
            )
        except Exception:
            st.warning("Для выбранного канала не найден профиль измерения. Проверьте тип канала.")

        st.caption(
            "Допустимые колонки: дата/время, значение, единица, источник, статус, метод, точность, место, ось, знак, сценарий нагрузки, компенсация, агрегация, прибор, калибровка."
        )
        upload_file = st.file_uploader("Файл с измерениями", type=["csv", "xlsx"])
        if upload_file is not None:
            try:
                rows = parse_measurement_file(upload_file.name, upload_file.getvalue())
                if not rows:
                    st.warning("Файл пустой.")
                else:
                    st.write("Предпросмотр")
                    st.dataframe(preview_rows(rows), use_container_width=True, hide_index=True)
                    if st.button("Загрузить измерения", type="primary", use_container_width=True):
                        prepared = prepare_measurement_records(
                            rows,
                            object_id=selected_object_id,
                            element_id=selected_channel["element_id"],
                            channel_id=selected_channel["id"],
                            default_unit=selected_channel["unit"],
                        )
                        imported = safe_call(
                            "Не удалось загрузить измерения",
                            client.import_json,
                            "measurements",
                            prepared,
                        )
                        if imported is not None:
                            st.success(f"Загружено записей: {len(imported)}")
                            st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    st.markdown("#### 3. Последние загруженные измерения")
    if measurements:
        chart_rows = sorted(
            [
                {"timestamp": item.get("timestamp"), "value": item.get("value")}
                for item in measurements
                if item.get("timestamp") and item.get("value") is not None
            ],
            key=lambda item: item["timestamp"],
        )
        if chart_rows:
            chart_df = pd.DataFrame(chart_rows)
            chart_df["timestamp"] = pd.to_datetime(chart_df["timestamp"])
            chart_df = chart_df.set_index("timestamp")
            st.line_chart(chart_df)

        st.dataframe(
            [
                {
                    "Дата": item.get("timestamp"),
                    "Значение": item.get("value"),
                    "Ед.": item.get("unit"),
                    "Ось": item.get("axis_direction") or "",
                    "Нагрузка": item.get("load_case_reference") or "",
                    "Источник": item.get("source_type") or "",
                }
                for item in measurements[:20]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Измерения пока не загружены.")


def show_environment_tab(environment_records: list[dict[str, Any]]) -> None:
    st.subheader("Среда")
    if not environment_records:
        st.info("Данные среды пока не загружены.")
        return
    st.dataframe(
        [
            {
                "Дата": item.get("timestamp"),
                "Температура": item.get("temperature"),
                "Влажность": item.get("humidity"),
                "Агрессивность": item.get("corrosion_aggressiveness") or "",
                "Нагрузка": item.get("load_summary") or "",
            }
            for item in environment_records
        ],
        use_container_width=True,
        hide_index=True,
    )


def show_interventions_tab(interventions: list[dict[str, Any]]) -> None:
    st.subheader("Ремонты и усиления")
    if not interventions:
        st.info("Записей о ремонтах пока нет.")
        return
    st.dataframe(
        [
            {
                "Дата": item.get("date"),
                "Тип": item.get("intervention_type"),
                "Описание": item.get("description") or "",
                "Качество": item.get("quality_of_execution") or "",
            }
            for item in interventions
        ],
        use_container_width=True,
        hide_index=True,
    )


def show_tests_tab(tests: list[dict[str, Any]]) -> None:
    st.subheader("Испытания и НК")
    if not tests:
        st.info("Испытаний пока нет.")
        return
    st.dataframe(
        [
            {
                "Дата": item.get("date"),
                "Тип": item.get("test_type"),
                "Свойство": item.get("measured_property"),
                "Значение": item.get("test_value"),
                "Единица": item.get("unit"),
            }
            for item in tests
        ],
        use_container_width=True,
        hide_index=True,
    )


def show_media_tab(
    client: APIClient,
    selected_object_id: str,
    elements: list[dict[str, Any]],
    media_assets: list[dict[str, Any]],
) -> None:
    st.subheader("Медиа")
    element_names = {item["id"]: item.get("name") for item in elements}
    if media_assets:
        st.dataframe(
            [
                {
                    "Файл": item.get("filename"),
                    "Элемент": element_names.get(item.get("element_id"), ""),
                    "Описание": item.get("description") or "",
                    "Дата": item.get("captured_at") or "",
                    "Источник": item.get("source_type") or "",
                }
                for item in media_assets
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Медиафайлов пока нет.")

    options = element_options(elements)
    with st.form("media_upload_form"):
        element_label = st.selectbox("К какому элементу относится файл", ["Не выбрано"] + list(options.keys()))
        description = st.text_input("Короткое описание")
        source_type = st.text_input("Источник", value="inspection")
        upload = st.file_uploader("Файл", type=["jpg", "jpeg", "png", "pdf"], key="media_upload")
        submitted = st.form_submit_button("Сохранить", type="primary", use_container_width=True)

    if submitted:
        if upload is None:
            st.error("Выберите файл.")
            return
        created = safe_call(
            "Не удалось загрузить файл",
            client.upload_media_asset,
            object_id=selected_object_id,
            file_name=upload.name,
            content=upload.getvalue(),
            content_type=upload.type,
            element_id=options.get(element_label),
            description=description.strip() or None,
            source_type=source_type.strip() or None,
        )
        if created:
            st.success("Файл загружен.")
            st.rerun()


def show_quality_tab(quality_records: list[dict[str, Any]]) -> None:
    st.subheader("Качество данных")
    if not quality_records:
        st.info("Записей о качестве пока нет.")
        return
    st.dataframe(
        [
            {
                "Сущность": item.get("entity_type"),
                "Источник": item.get("source_type"),
                "Полнота": item.get("completeness_score"),
                "Повторяемость": item.get("repeatability_score"),
                "Трассируемость": item.get("traceability_score"),
                "Пригодность": item.get("identification_suitability_score"),
            }
            for item in quality_records
        ],
        use_container_width=True,
        hide_index=True,
    )


def show_timeline_tab(
    defects: list[dict[str, Any]],
    interventions: list[dict[str, Any]],
    tests: list[dict[str, Any]],
) -> None:
    st.subheader("Хронология событий")
    rows: list[dict[str, Any]] = []
    for item in defects:
        rows.append({"Дата": item.get("detection_date"), "Событие": "Дефект", "Описание": item.get("defect_type")})
    for item in interventions:
        rows.append({"Дата": item.get("date"), "Событие": "Ремонт/усиление", "Описание": item.get("intervention_type")})
    for item in tests:
        rows.append({"Дата": item.get("date"), "Событие": "Испытание/НК", "Описание": item.get("test_type")})
    if rows:
        st.dataframe(sorted(rows, key=lambda item: item.get("Дата") or ""), use_container_width=True, hide_index=True)
    else:
        st.info("Событий пока нет.")


def show_information_tab(data: dict[str, Any] | None) -> None:
    st.subheader("Оценка полноты данных")
    st.caption("Это экран information_sufficiency_index")
    if not data:
        st.info("Данные пока недоступны.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Общая оценка", format_score(data["total_score"]))
    col2.metric("Обязательные данные", format_score(data["p0_score"]))
    col3.metric("Важные данные", format_score(data["p1_score"]))

    if data.get("domain_scores"):
        st.markdown("#### Частные индексы")
        st.dataframe(
            [
                {"Показатель": "Паспорт объекта", "Оценка": format_score(data["domain_scores"]["object_passport_score"])},
                {"Показатель": "Расчётная модель", "Оценка": format_score(data["domain_scores"]["structural_model_score"])},
                {"Показатель": "Реестр дефектов", "Оценка": format_score(data["domain_scores"]["defect_registry_score"])},
                {"Показатель": "Измерения", "Оценка": format_score(data["domain_scores"]["measurement_score"])},
                {"Показатель": "Закрепления и связи", "Оценка": format_score(data["domain_scores"]["boundary_conditions_score"])},
                {"Показатель": "Среда", "Оценка": format_score(data["domain_scores"]["environment_score"])},
                {"Показатель": "Ремонты и усиления", "Оценка": format_score(data["domain_scores"]["intervention_history_score"])},
                {"Показатель": "Испытания и НК", "Оценка": format_score(data["domain_scores"]["testing_score"])},
                {"Показатель": "Качество и трассируемость", "Оценка": format_score(data["domain_scores"]["quality_traceability_score"])},
            ],
            use_container_width=True,
            hide_index=True,
        )

    if data.get("coverage_by_parameter_group"):
        st.markdown("#### Покрытие по классам параметров")
        st.dataframe(
            [
                {"Группа": "Геометрия и схема", "Покрытие": format_score(data["coverage_by_parameter_group"].get("geometry_and_scheme", 0.0))},
                {"Группа": "Материалы", "Покрытие": format_score(data["coverage_by_parameter_group"].get("materials", 0.0))},
                {"Группа": "Повреждения", "Покрытие": format_score(data["coverage_by_parameter_group"].get("damage_state", 0.0))},
                {"Группа": "Закрепления", "Покрытие": format_score(data["coverage_by_parameter_group"].get("boundary_conditions", 0.0))},
                {"Группа": "Отклик", "Покрытие": format_score(data["coverage_by_parameter_group"].get("dynamic_response", 0.0))},
                {"Группа": "Прогнозные предпосылки", "Покрытие": format_score(data["coverage_by_parameter_group"].get("prognosis_preconditions", 0.0))},
            ],
            use_container_width=True,
            hide_index=True,
        )

    if data.get("coverage_by_critical_elements"):
        st.markdown("#### Покрытие по важным элементам")
        st.dataframe(
            [
                {"ID элемента": element_id, "Покрытие": format_score(score)}
                for element_id, score in data["coverage_by_critical_elements"].items()
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            f"Качество измерений с учетом traceability: {format_score(data.get('quality_weighted_measurement_coverage', 0.0))}"
        )

    missing_items = data.get("missing_items") or []
    if missing_items:
        st.dataframe(
            [
                {
                    "Что не хватает": REQUIREMENT_LABELS.get(item.get("code"), item.get("description")),
                    "Приоритет": item.get("priority"),
                    "Покрытие": format_score(item.get("coverage") or 0.0),
                }
                for item in missing_items
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("Все ключевые данные на месте.")


def show_readiness_tab(data: dict[str, Any] | None) -> None:
    st.subheader("Готовность к дальнейшему расчёту")
    st.caption("Это экран identification_readiness_report")
    if not data:
        st.info("Отчёт пока недоступен.")
        return

    readiness_label = READINESS_TEXT.get(data["readiness_level"], data["readiness_level"])
    if data["readiness_level"] == "ready":
        st.success(readiness_label)
    elif data["readiness_level"] == "partial":
        st.warning(readiness_label)
    else:
        st.error(readiness_label)

    st.metric("Общая готовность", format_score(data["total_score"]))

    if data.get("task_scores"):
        st.markdown("#### Готовность по классам задач")
        st.dataframe(
            [
                {
                    "Класс": "Геометрия",
                    "Статус": TASK_STATUS_TEXT.get(data.get("geometry_ready"), data.get("geometry_ready")),
                    "Оценка": format_score(data["task_scores"]["geometry_ready"]),
                },
                {
                    "Класс": "Жёсткость",
                    "Статус": TASK_STATUS_TEXT.get(data.get("stiffness_ready"), data.get("stiffness_ready")),
                    "Оценка": format_score(data["task_scores"]["stiffness_ready"]),
                },
                {
                    "Класс": "Повреждения",
                    "Статус": TASK_STATUS_TEXT.get(data.get("damage_ready"), data.get("damage_ready")),
                    "Оценка": format_score(data["task_scores"]["damage_ready"]),
                },
                {
                    "Класс": "Материал",
                    "Статус": TASK_STATUS_TEXT.get(data.get("material_ready"), data.get("material_ready")),
                    "Оценка": format_score(data["task_scores"]["material_ready"]),
                },
                {
                    "Класс": "Закрепления",
                    "Статус": TASK_STATUS_TEXT.get(data.get("boundary_ready"), data.get("boundary_ready")),
                    "Оценка": format_score(data["task_scores"]["boundary_ready"]),
                },
            ],
            use_container_width=True,
            hide_index=True,
        )

    if data.get("recommended_parameters"):
        st.markdown("#### Что уже можно использовать")
        for item in data["recommended_parameters"]:
            st.write(f"- {item}")

    if data.get("blocked_parameters"):
        st.markdown("#### Что мешает")
        for item in data["blocked_parameters"]:
            st.write(f"- {REQUIREMENT_LABELS.get(item, item)}")

    if data.get("next_measurements"):
        st.markdown("#### Что добавить дальше")
        for item in data["next_measurements"]:
            st.write(f"- {item}")


def show_readiness_tab(data: dict[str, Any] | None) -> None:
    st.subheader("Готовность к дальнейшему расчету")
    st.caption("Это экран identification_readiness_report")
    if not data:
        st.info("Отчет пока недоступен.")
        return

    readiness_label = READINESS_TEXT.get(data["readiness_level"], data["readiness_level"])
    if data["readiness_level"] == "ready":
        st.success(readiness_label)
    elif data["readiness_level"] == "partial":
        st.warning(readiness_label)
    else:
        st.error(readiness_label)

    st.metric("Общая готовность", format_score(data["total_score"]))

    if data.get("task_scores"):
        st.markdown("#### Готовность по механическим классам")
        st.dataframe(
            [
                {
                    "Класс": "Геометрия и схема",
                    "Статус": TASK_STATUS_TEXT.get(data.get("geometry_and_scheme_ready"), data.get("geometry_and_scheme_ready")),
                    "Оценка": format_score(data["task_scores"].get("geometry_and_scheme", 0.0)),
                },
                {
                    "Класс": "Материалы",
                    "Статус": TASK_STATUS_TEXT.get(data.get("materials_ready"), data.get("materials_ready")),
                    "Оценка": format_score(data["task_scores"].get("materials", 0.0)),
                },
                {
                    "Класс": "Повреждения",
                    "Статус": TASK_STATUS_TEXT.get(data.get("damage_state_ready"), data.get("damage_state_ready")),
                    "Оценка": format_score(data["task_scores"].get("damage_state", 0.0)),
                },
                {
                    "Класс": "Закрепления",
                    "Статус": TASK_STATUS_TEXT.get(data.get("boundary_conditions_ready"), data.get("boundary_conditions_ready")),
                    "Оценка": format_score(data["task_scores"].get("boundary_conditions", 0.0)),
                },
                {
                    "Класс": "Отклик",
                    "Статус": TASK_STATUS_TEXT.get(data.get("dynamic_response_ready"), data.get("dynamic_response_ready")),
                    "Оценка": format_score(data["task_scores"].get("dynamic_response", 0.0)),
                },
                {
                    "Класс": "Прогнозные предпосылки",
                    "Статус": TASK_STATUS_TEXT.get(data.get("prognosis_preconditions_ready"), data.get("prognosis_preconditions_ready")),
                    "Оценка": format_score(data["task_scores"].get("prognosis_preconditions", 0.0)),
                },
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### Совместимость со старой шкалой")
        st.dataframe(
            [
                {
                    "Класс": "Геометрия",
                    "Статус": TASK_STATUS_TEXT.get(data.get("geometry_ready"), data.get("geometry_ready")),
                    "Оценка": format_score(data["task_scores"].get("geometry_ready", 0.0)),
                },
                {
                    "Класс": "Жесткость",
                    "Статус": TASK_STATUS_TEXT.get(data.get("stiffness_ready"), data.get("stiffness_ready")),
                    "Оценка": format_score(data["task_scores"].get("stiffness_ready", 0.0)),
                },
                {
                    "Класс": "Повреждения",
                    "Статус": TASK_STATUS_TEXT.get(data.get("damage_ready"), data.get("damage_ready")),
                    "Оценка": format_score(data["task_scores"].get("damage_ready", 0.0)),
                },
                {
                    "Класс": "Материал",
                    "Статус": TASK_STATUS_TEXT.get(data.get("material_ready"), data.get("material_ready")),
                    "Оценка": format_score(data["task_scores"].get("material_ready", 0.0)),
                },
                {
                    "Класс": "Закрепления",
                    "Статус": TASK_STATUS_TEXT.get(data.get("boundary_ready"), data.get("boundary_ready")),
                    "Оценка": format_score(data["task_scores"].get("boundary_ready", 0.0)),
                },
            ],
            use_container_width=True,
            hide_index=True,
        )

    if data.get("recommended_parameters"):
        st.markdown("#### Что уже можно использовать")
        for item in data["recommended_parameters"]:
            st.write(f"- {item}")

    if data.get("blocked_parameters"):
        st.markdown("#### Что мешает")
        for item in data["blocked_parameters"]:
            st.write(f"- {REQUIREMENT_LABELS.get(item, item)}")

    if data.get("next_measurements"):
        st.markdown("#### Что добавить дальше")
        for item in data["next_measurements"]:
            st.write(f"- {item}")


def show_package_tab(client: APIClient, selected_object_id: str) -> None:
    st.subheader("Выгрузка пакета")
    if st.button("Сформировать пакет", type="primary", use_container_width=True):
        data = safe_call("Не удалось сформировать пакет", client.export_observation_package, selected_object_id)
        if data:
            package_text = json.dumps(data, ensure_ascii=False, indent=2)
            st.success("Пакет сформирован.")
            st.download_button(
                "Скачать observation_package.json",
                data=package_text,
                file_name=f"observation_package_{selected_object_id}.json",
                mime="application/json",
                use_container_width=True,
            )
            st.code(package_text[:3000] + ("\n..." if len(package_text) > 3000 else ""), language="json")


def main() -> None:
    st.title("СКДО")
    st.write("Простой интерфейс для инженера. Здесь можно работать без Swagger и без ручных запросов.")

    client = make_client()
    objects = safe_call("Не удалось получить список объектов", client.list_objects) or []
    show_sidebar(objects)
    show_objects_section(client, objects)

    selected_object_id = st.session_state.get("selected_object_id")
    if not selected_object_id:
        st.info("Выберите объект слева или создайте новый.")
        return

    current_object = next((item for item in objects if item["id"] == selected_object_id), None)
    elements = safe_call("Не удалось загрузить элементы", client.list_elements, selected_object_id) or []
    defects = safe_call("Не удалось загрузить дефекты", client.list_defects, selected_object_id) or []
    channels = safe_call("Не удалось загрузить каналы", client.list_channels, selected_object_id) or []
    measurements = safe_call("Не удалось загрузить измерения", client.list_measurements, selected_object_id) or []
    environment_records = safe_call("Не удалось загрузить среду", client.list_environment_records, selected_object_id) or []
    interventions = safe_call("Не удалось загрузить ремонты", client.list_interventions, selected_object_id) or []
    tests = safe_call("Не удалось загрузить испытания", client.list_tests, selected_object_id) or []
    quality_records = safe_call("Не удалось загрузить качество", client.list_quality_records, selected_object_id) or []
    information_data = safe_call("Не удалось получить оценку данных", client.get_information_sufficiency, selected_object_id)
    readiness_data = safe_call("Не удалось получить отчёт", client.get_identification_readiness, selected_object_id)

    tabs = st.tabs(
        [
            "Обзор",
            "Элементы",
            "Дефекты",
            "Измерения",
            "Среда",
            "Ремонты",
            "Испытания",
            "Качество",
            "Хронология",
            "Оценка данных",
            "Готовность",
            "Пакет",
        ]
    )

    with tabs[0]:
        if current_object:
            show_dashboard_section(current_object, elements, defects, channels, measurements, information_data, readiness_data)
    with tabs[1]:
        show_elements_tab(client, selected_object_id, elements)
    with tabs[2]:
        show_defects_tab(client, selected_object_id, elements, defects)
    with tabs[3]:
        show_measurements_tab(client, selected_object_id, elements, channels, measurements)
    with tabs[4]:
        show_environment_tab(environment_records)
    with tabs[5]:
        show_interventions_tab(interventions)
    with tabs[6]:
        show_tests_tab(tests)
    with tabs[7]:
        show_quality_tab(quality_records)
    with tabs[8]:
        show_timeline_tab(defects, interventions, tests)
    with tabs[9]:
        show_information_tab(information_data)
    with tabs[10]:
        show_readiness_tab(readiness_data)
    with tabs[11]:
        show_package_tab(client, selected_object_id)


def main() -> None:
    st.title("СКДО")
    st.write("Простой интерфейс для инженера. Здесь можно работать без Swagger и без ручных запросов.")

    client = make_client()
    objects = safe_call("Не удалось получить список объектов", client.list_objects) or []
    show_sidebar(objects)
    show_objects_section(client, objects)

    selected_object_id = st.session_state.get("selected_object_id")
    if not selected_object_id:
        st.info("Выберите объект слева или создайте новый.")
        return

    current_object = next((item for item in objects if item["id"] == selected_object_id), None)
    elements = safe_call("Не удалось загрузить элементы", client.list_elements, selected_object_id) or []
    defects = safe_call("Не удалось загрузить дефекты", client.list_defects, selected_object_id) or []
    channels = safe_call("Не удалось загрузить каналы", client.list_channels, selected_object_id) or []
    measurements = safe_call("Не удалось загрузить измерения", client.list_measurements, selected_object_id) or []
    environment_records = safe_call("Не удалось загрузить среду", client.list_environment_records, selected_object_id) or []
    interventions = safe_call("Не удалось загрузить ремонты", client.list_interventions, selected_object_id) or []
    tests = safe_call("Не удалось загрузить испытания", client.list_tests, selected_object_id) or []
    media_assets = safe_call("Не удалось загрузить медиа", client.list_media_assets, selected_object_id) or []
    quality_records = safe_call("Не удалось загрузить качество", client.list_quality_records, selected_object_id) or []
    information_data = safe_call("Не удалось получить оценку данных", client.get_information_sufficiency, selected_object_id)
    readiness_data = safe_call("Не удалось получить отчет", client.get_identification_readiness, selected_object_id)

    tabs = st.tabs(
        [
            "Обзор",
            "Элементы",
            "Дефекты",
            "Измерения",
            "Среда",
            "Ремонты",
            "Испытания",
            "Медиа",
            "Качество",
            "Хронология",
            "Оценка данных",
            "Готовность",
            "Пакет",
        ]
    )

    with tabs[0]:
        if current_object:
            show_dashboard_section(current_object, elements, defects, channels, measurements, information_data, readiness_data)
    with tabs[1]:
        show_elements_tab(client, selected_object_id, elements, information_data)
    with tabs[2]:
        show_defects_tab(client, selected_object_id, elements, defects)
    with tabs[3]:
        show_measurements_tab(client, selected_object_id, elements, channels, measurements)
    with tabs[4]:
        show_environment_tab(environment_records)
    with tabs[5]:
        show_interventions_tab(interventions)
    with tabs[6]:
        show_tests_tab(tests)
    with tabs[7]:
        show_media_tab(client, selected_object_id, elements, media_assets)
    with tabs[8]:
        show_quality_tab(quality_records)
    with tabs[9]:
        show_timeline_tab(defects, interventions, tests)
    with tabs[10]:
        show_information_tab(information_data)
    with tabs[11]:
        show_readiness_tab(readiness_data)
    with tabs[12]:
        show_package_tab(client, selected_object_id)


if __name__ == "__main__":
    main()
