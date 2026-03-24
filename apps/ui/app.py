from __future__ import annotations

from datetime import date
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import Any
from typing import Optional

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
REQUIREMENT_LABELS = {
    "object.identity": "Нет полного паспорта объекта",
    "object.function_type": "Не указано назначение объекта",
    "element.tree": "Нет дерева элементов",
    "element.geometry": "Не хватает геометрии элементов",
    "element.material": "Не хватает данных о материале",
    "defect.registry": "Нет реестра дефектов",
    "observation.measurements": "Нет базовых измерений",
    "quality.traceability": "Нет данных о качестве и источнике",
    "element.boundary_conditions": "Нет сведений о закреплениях и связях",
    "environment.effects": "Нет данных о среде и воздействиях",
    "intervention.history": "Нет истории ремонтов и усилений",
    "tests.ndt": "Нет результатов испытаний",
    "measurement.channel_metadata": "Не хватает описания каналов измерений",
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
    return f"{item.get('object_code', '')} — {item.get('object_name', '')}"


def format_score(value: float) -> str:
    return f"{value * 100:.0f}%"


def date_to_iso(value: date) -> str:
    return datetime.combine(value, datetime.min.time()).isoformat() + "Z"


def build_element_tree(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_parent: dict[Optional[str], list[dict[str, Any]]] = {}
    for item in elements:
        by_parent.setdefault(item.get("parent_id"), []).append(item)
    rows: list[dict[str, Any]] = []

    def walk(parent_id: Optional[str], level: int) -> None:
        for item in sorted(by_parent.get(parent_id, []), key=lambda row: row.get("name") or ""):
            rows.append(
                {
                    "Уровень": level,
                    "Тип узла": FRIENDLY_HIERARCHY.get(item.get("hierarchy_type"), item.get("hierarchy_type")),
                    "Название": ("    " * level) + (item.get("name") or ""),
                    "Роль": item.get("structural_role") or "",
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
            f"{channel.get('channel_code')} — {channel.get('measured_quantity')} "
            f"({element_names.get(channel.get('element_id'), 'без элемента')})"
        )
        result[label] = channel
    return result


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
    col_list, col_form = st.columns([1.35, 1])
    with col_list:
        if objects:
            table = [
                {
                    "Код": item.get("object_code"),
                    "Название": item.get("object_name"),
                    "Адрес": item.get("address") or "",
                    "Назначение": item.get("function_type") or "",
                    "Режим": item.get("current_operational_mode") or "",
                }
                for item in objects
            ]
            st.dataframe(table, use_container_width=True, hide_index=True)
        else:
            st.info("Объектов пока нет. Справа можно создать первый объект.")

    with col_form:
        mode = st.radio("Что сделать", ["Создать объект", "Редактировать выбранный объект"], horizontal=True)
        current_object = next((item for item in objects if item["id"] == st.session_state.get("selected_object_id")), None)
        if mode == "Редактировать выбранный объект" and not current_object:
            st.warning("Сначала выберите объект слева в меню.")
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
        payload = {
            "object_id": selected_object_id,
            "parent_id": options.get(parent_label),
            "hierarchy_type": hierarchy_type,
            "name": name.strip(),
            "structural_role": structural_role.strip() or None,
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


def show_defects_tab(client: APIClient, selected_object_id: str, elements: list[dict[str, Any]], defects: list[dict[str, Any]]) -> None:
    st.subheader("Дефекты")
    element_names = {item["id"]: item.get("name") for item in elements}
    if defects:
        table = [
            {"Элемент": element_names.get(item.get("element_id"), ""), "Тип дефекта": item.get("defect_type"), "Место": item.get("location_on_element"), "Дата": item.get("detection_date"), "Статус": item.get("defect_status") or ""}
            for item in defects
        ]
        st.dataframe(table, use_container_width=True, hide_index=True)
    else:
        st.info("Дефектов пока нет.")

    options = element_options(elements)
    if not options:
        st.warning("Сначала добавьте хотя бы один элемент.")
        return

    with st.form("defect_form"):
        st.markdown("#### Добавить дефект")
        element_label = st.selectbox("Элемент", list(options.keys()))
        defect_type = st.text_input("Тип дефекта")
        defect_subtype = st.text_input("Уточнение")
        location_on_element = st.text_input("Где находится дефект")
        detection_date = st.date_input("Дата обнаружения", value=date.today())
        defect_status = st.text_input("Статус")
        crack_width = st.number_input("Ширина трещины", min_value=0.0, value=0.0)
        corrosion_area = st.number_input("Площадь повреждения", min_value=0.0, value=0.0)
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
            "location_on_element": location_on_element.strip(),
            "detection_date": date_to_iso(detection_date),
            "defect_status": defect_status.strip() or None,
            "crack_width": crack_width or None,
            "corrosion_area": corrosion_area or None,
            "source_document": source_document.strip() or None,
        }
        created = safe_call("Не удалось добавить дефект", client.create_defect, payload)
        if created:
            st.success("Дефект добавлен.")
            st.rerun()


def show_measurements_tab(client: APIClient, selected_object_id: str, elements: list[dict[str, Any]], channels: list[dict[str, Any]], measurements: list[dict[str, Any]]) -> None:
    st.subheader("Измерения")
    options = element_options(elements)
    if not options:
        st.warning("Сначала добавьте элемент.")
        return

    st.markdown("#### 1. Канал измерений")
    with st.form("channel_form"):
        element_label = st.selectbox("Для какого элемента канал", list(options.keys()))
        channel_code = st.text_input("Код канала")
        measured_quantity = st.text_input("Что измеряем", value="deflection")
        unit = st.text_input("Единица измерения", value="mm")
        sensor_type = st.text_input("Прибор", value="LVDT")
        spatial_location = st.text_input("Где установлен датчик", value="midspan")
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
                "measured_quantity": measured_quantity.strip() or None,
                "unit": unit.strip() or None,
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
        st.caption(
            "Допустимые колонки: дата/время, значение, единица, источник, статус, метод, "
            "точность, место. Можно использовать русские или английские названия."
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
                        imported = safe_call("Не удалось загрузить измерения", client.import_json, "measurements", prepared)
                        if imported is not None:
                            st.success(f"Загружено записей: {len(imported)}")
                            st.rerun()
            except ValueError as exc:
                st.error(str(exc))

    st.markdown("#### 3. Последние загруженные измерения")
    if measurements:
        table = [{"Дата": item.get("timestamp"), "Значение": item.get("value"), "Ед.": item.get("unit"), "Источник": item.get("source_type") or ""} for item in measurements[:20]]
        st.dataframe(table, use_container_width=True, hide_index=True)
    else:
        st.info("Измерения пока не загружены.")


def show_information_tab(client: APIClient, selected_object_id: str) -> None:
    st.subheader("Оценка полноты данных")
    st.caption("Это экран information_sufficiency_index")
    data = safe_call("Не удалось получить оценку данных", client.get_information_sufficiency, selected_object_id)
    if not data:
        return
    col1, col2, col3 = st.columns(3)
    col1.metric("Общая оценка", format_score(data["total_score"]))
    col2.metric("Обязательные данные", format_score(data["p0_score"]))
    col3.metric("Важные данные", format_score(data["p1_score"]))
    missing_items = data.get("missing_items") or []
    if missing_items:
        table = [{"Что не хватает": REQUIREMENT_LABELS.get(item.get("code"), item.get("description")), "Приоритет": item.get("priority")} for item in missing_items]
        st.dataframe(table, use_container_width=True, hide_index=True)
    else:
        st.success("Все ключевые данные на месте.")


def show_readiness_tab(client: APIClient, selected_object_id: str) -> None:
    st.subheader("Готовность к дальнейшему расчёту")
    st.caption("Это экран identification_readiness_report")
    data = safe_call("Не удалось получить отчёт", client.get_identification_readiness, selected_object_id)
    if not data:
        return
    readiness_label = READINESS_TEXT.get(data["readiness_level"], data["readiness_level"])
    if data["readiness_level"] == "ready":
        st.success(readiness_label)
    elif data["readiness_level"] == "partial":
        st.warning(readiness_label)
    else:
        st.error(readiness_label)
    st.metric("Общая готовность", format_score(data["total_score"]))
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
            st.download_button("Скачать observation_package.json", data=package_text, file_name=f"observation_package_{selected_object_id}.json", mime="application/json", use_container_width=True)
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
    elements = safe_call("Не удалось загрузить элементы", client.list_elements, selected_object_id) or []
    defects = safe_call("Не удалось загрузить дефекты", client.list_defects, selected_object_id) or []
    channels = safe_call("Не удалось загрузить каналы", client.list_channels, selected_object_id) or []
    measurements = safe_call("Не удалось загрузить измерения", client.list_measurements, selected_object_id) or []
    tabs = st.tabs(["Элементы", "Дефекты", "Измерения", "Оценка данных", "Готовность", "Пакет"])
    with tabs[0]:
        show_elements_tab(client, selected_object_id, elements)
    with tabs[1]:
        show_defects_tab(client, selected_object_id, elements, defects)
    with tabs[2]:
        show_measurements_tab(client, selected_object_id, elements, channels, measurements)
    with tabs[3]:
        show_information_tab(client, selected_object_id)
    with tabs[4]:
        show_readiness_tab(client, selected_object_id)
    with tabs[5]:
        show_package_tab(client, selected_object_id)


if __name__ == "__main__":
    main()
