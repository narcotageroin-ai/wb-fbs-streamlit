import io, os, time, json
from datetime import datetime, timedelta
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
import wb_api

load_dotenv()

st.set_page_config(page_title="WB FBS Assistant (oShip-like)", layout="wide")

st.title("Wildberries FBS — тестовое приложение (oShip-подход)")

with st.sidebar:
    st.header("Настройки")
    token = st.text_input("WB API Token", value=os.getenv("WB_API_TOKEN", ""), type="password", key="sidebar_token", help="Токен категории Marketplace")
    env = st.selectbox("Среда", ["prod", "sandbox"], index=0 if os.getenv("WB_ENV","prod")=="prod" else 1, key="sidebar_env",
                       help="Sandbox доступен при токене с Test Scope")
    st.caption("Подсказка: переменные можно положить в файл .env")
    if token:
        os.environ["WB_API_TOKEN"] = token

tab_pipeline, tab_orders, tab_supply, tab_labels, tab_meta, tab_pass = st.tabs(["Конвейер (сканер)", "Сборочные задания", "Поставка", "Стикеры", "Маркировка/метаданные", "Пропуска"])

# ---------- PIPELINE (oShip-like) ----------
with tab_pipeline:
    st.subheader("Поток упаковки: скан → добавить в поставку → маркировка → стикер")
    st.caption("Вводите отсканированные значения. Поддерживаются форматы: "
               "`<orderId>`, `<orderId>|<SGTIN>`, `<orderId>|<IMEI>`, `<orderId>|<UIN>`, `<orderId>|<GTIN>`.")

    if "active_supply" not in st.session_state:
        st.session_state["active_supply"] = ""
    st.session_state["active_supply"] = st.text_input("Текущая поставка (supplyId)", value=st.session_state["active_supply"], key="pipeline_supply")

    auto_print = st.checkbox("Автогенерация стикера (PNG 58x40)", value=True, key="pipeline_auto_print")
    auto_meta_before_add = st.checkbox("Сначала записывать метаданные, затем добавлять заказ в поставку", value=True, key="pipeline_meta_before")

    scan_val = st.text_input("Поле для сканера", value="", key="pipeline_scan", help="Сфокусируйте курсор и сканируйте штрихкод/строку")

    def _parse_scan(s: str):
        parts = [p.strip() for p in s.split("|")]
        order_id = int(parts[0]) if parts and parts[0].isdigit() else None
        meta = {}
        if len(parts) > 1:
            payload = parts[1]
            if len(payload) in (14, 15, 16) and payload.isdigit():
                meta["imei"] = payload
            elif len(payload) in (31, 44) and payload.isdigit():
                meta["uin"] = payload
            elif len(payload) > 22:
                meta["sgtin"] = payload
            else:
                meta["gtin"] = payload
        return order_id, meta

    if scan_val:
        order_id, meta = _parse_scan(scan_val)
        if not order_id:
            st.error("Не распознан orderId в начале строки. Формат: <orderId>|<метка>", icon="⚠️")
        else:
            try:
                if auto_meta_before_add and meta:
                    if "sgtin" in meta: wb_api.add_sgtin(order_id, meta["sgtin"])
                    if "uin" in meta: wb_api.add_uin(order_id, meta["uin"])
                    if "imei" in meta: wb_api.add_imei(order_id, meta["imei"])
                    if "gtin" in meta: wb_api.add_gtin(order_id, meta["gtin"])
                    st.success(f"Метаданные записаны: {meta}")
                if st.session_state["active_supply"]:
                    wb_api.add_order_to_supply(st.session_state["active_supply"], order_id)
                    st.success(f"Заказ {order_id} добавлен в поставку {st.session_state['active_supply']} (confirm)")
                else:
                    st.warning("Укажите supplyId, чтобы добавить заказ в поставку")
                if not auto_meta_before_add and meta:
                    if "sgtin" in meta: wb_api.add_sgtin(order_id, meta["sgtin"])
                    if "uin" in meta: wb_api.add_uin(order_id, meta["uin"])
                    if "imei" in meta: wb_api.add_imei(order_id, meta["imei"])
                    if "gtin" in meta: wb_api.add_gtin(order_id, meta["gtin"])
                    st.success(f"Метаданные записаны: {meta}")
                if auto_print:
                    content = wb_api.get_stickers([order_id], fmt="png", width=58, height=40)
                    st.download_button("Скачать стикер (PNG)", data=content, file_name=f"{order_id}_sticker.png", key=f"pipeline_download_{order_id}")
                    st.image(content, caption=f"Стикер заказа {order_id}")
            except Exception as e:
                st.error(str(e))

# ---------- ORDERS ----------
with tab_orders:
    st.subheader("Новые сборочные задания")
    if st.button("Получить новые задания", key="orders_get_new"):
        try:
            data = wb_api.get_new_orders()
            st.json(data)
        except Exception as e:
            st.error(str(e))

    st.divider()
    st.subheader("Поиск заказов за период")
    col1, col2 = st.columns(2)
    with col1:
        date_from_orders = st.date_input("Дата с", datetime.utcnow().date()-timedelta(days=7), key="orders_date_from")
    with col2:
        date_to_orders = st.date_input("Дата по", datetime.utcnow().date(), key="orders_date_to")
    if st.button("Загрузить заказы", key="orders_load"):
        import time as _t
        ts_from = int(time.mktime(datetime(date_from_orders.year, date_from_orders.month, date_from_orders.day).timetuple()))
        ts_to = int(time.mktime(datetime(date_to_orders.year, date_to_orders.month, date_to_orders.day, 23,59,59).timetuple()))
        try:
            result = wb_api.get_orders(limit=1000, next_val=0, date_from=ts_from, date_to=ts_to)
            st.json(result)
        except Exception as e:
            st.error(str(e))

# ---------- SUPPLY ----------
with tab_supply:
    st.subheader("Поставка (создание, добавление заказов, отгрузка)")
    if "supply_id" not in st.session_state:
        st.session_state["supply_id"] = ""

    office_id_val = st.number_input("destinationOfficeId (опционально, обязательно с 01.09.2025 для совпадения officeID заказов)", min_value=0, value=0, key="supply_office_id")
    if st.button("Создать поставку", key="supply_create"):
        try:
            payload = {}
            if office_id_val:
                payload["destinationOfficeId"] = office_id_val
            data = wb_api.create_supply(destination_office_id=payload.get("destinationOfficeId"))
            st.session_state["supply_id"] = data.get("supplyId") or data.get("id") or data.get("supplyID") or ""
            st.success(f"Создана поставка: {st.session_state['supply_id']}")
            st.json(data)
        except Exception as e:
            st.error(str(e))

    supply_id = st.text_input("ID поставки", value=st.session_state.get("supply_id",""), key="supply_id_input")
    order_id_to_add = st.number_input("Добавить заказ (orderId)", min_value=0, value=0, step=1, key="supply_order_id_to_add")
    if st.button("Добавить заказ в поставку", key="supply_add_order"):
        try:
            wb_api.add_order_to_supply(supply_id, order_id_to_add)
            st.success("Заказ добавлен и переведен в статус confirm (На сборке)")
        except Exception as e:
            st.error(str(e))

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Показать заказы поставки", key="supply_show_orders"):
            try:
                st.json(wb_api.get_supply_orders(supply_id))
            except Exception as e:
                st.error(str(e))
    with c2:
        if st.button("Передать поставку в доставку", key="supply_deliver"):
            try:
                wb_api.deliver_supply(supply_id)
                st.success("Поставка закрыта и заказы переведены в complete (В доставке)")
            except Exception as e:
                st.error(str(e))
    with c3:
        if st.button("Получить QR поставки (png)", key="supply_get_qr"):
            try:
                img_bytes = wb_api.get_supply_qr(supply_id, fmt="png")
                st.download_button("Скачать QR поставки", data=img_bytes, file_name=f"{supply_id}_qr.png", key="supply_download_qr")
                st.image(img_bytes, caption="QR поставки")
            except Exception as e:
                st.error(str(e))

    st.markdown("#### Короба (для ПВЗ)")
    cols = st.columns(4)
    with cols[0]:
        amount = st.number_input("Добавить коровов", min_value=1, value=1, key="supply_trbx_amount")
        if st.button("Добавить короба", key="supply_trbx_add"):
            try:
                st.json(wb_api.add_boxes(supply_id, amount))
            except Exception as e:
                st.error(str(e))
    with cols[1]:
        if st.button("Список коробов", key="supply_trbx_list"):
            try:
                st.json(wb_api.get_supply_boxes(supply_id))
            except Exception as e:
                st.error(str(e))
    with cols[2]:
        trbx_ids_str = st.text_input("trbxIds через запятую", "", key="supply_trbx_ids")
        if st.button("Стикеры коробов (png)", key="supply_trbx_stickers"):
            try:
                trbx_ids = [x.strip() for x in trbx_ids_str.split(",") if x.strip()]
                content = wb_api.get_box_stickers(supply_id, trbx_ids, fmt="png")
                st.download_button("Скачать стикеры коробов", data=content, file_name=f"{supply_id}_trbx_stickers.png", key="supply_trbx_download")
                st.image(content, caption="Стикеры коробов")
            except Exception as e:
                st.error(str(e))
    with cols[3]:
        if st.button("Удалить короба (по trbxIds)", key="supply_trbx_delete"):
            try:
                trbx_ids = [x.strip() for x in st.session_state.get("supply_trbx_ids","").split(",") if x.strip()]
                wb_api.delete_boxes(supply_id, trbx_ids)
                st.success("Короба удалены")
            except Exception as e:
                st.error(str(e))

# ---------- LABELS ----------
with tab_labels:
    st.subheader("Печать стикеров заказов")
    st.caption("Доступно для заказов в статусе confirm (На сборке). Размеры: 58x40 или 40x30. Форматы: png, svg, zplv/zplh")
    order_ids_str = st.text_area("orderIds (через запятую)", key="labels_order_ids")
    fmt = st.selectbox("Формат", ["png", "svg", "zplv", "zplh"], index=0, key="labels_fmt")
    size = st.selectbox("Размер", ["58x40", "40x30"], index=0, key="labels_size")
    if st.button("Сгенерировать стикеры", key="labels_generate"):
        try:
            width, height = (58,40) if size=="58x40" else (40,30)
            order_ids = [int(x.strip()) for x in order_ids_str.split(",") if x.strip()]
            content = wb_api.get_stickers(order_ids, fmt=fmt, width=width, height=height)
            ext = "png" if fmt in ("png","svg") else "zpl"
            st.download_button("Скачать стикеры", data=content, file_name=f"stickers.{ext}", key="labels_download")
            if fmt == "png" or fmt == "svg":
                st.image(content, caption="Превью стикеров")
        except Exception as e:
            st.error(str(e))

# ---------- META ----------
with tab_meta:
    st.subheader("Маркировка и дополнительные данные (аналог oShip сканирования)")
    st.caption("Добавление SGTIN/UIN/IMEI/GTIN и срока годности в метаданные заказа")
    order_id = st.number_input("orderId", min_value=0, value=0, step=1, key="meta_order_id")
    colm = st.columns(5)
    with colm[0]:
        sgtin = st.text_input("SGTIN", key="meta_sgtin_in")
        if st.button("Добавить SGTIN", key="meta_sgtin_btn"):
            try:
                wb_api.add_sgtin(order_id, sgtin)
                st.success("SGTIN добавлен")
            except Exception as e:
                st.error(str(e))
    with colm[1]:
        uin = st.text_input("UIN", key="meta_uin_in")
        if st.button("Добавить UIN", key="meta_uin_btn"):
            try:
                wb_api.add_uin(order_id, uin)
                st.success("UIN добавлен")
            except Exception as e:
                st.error(str(e))
    with colm[2]:
        imei = st.text_input("IMEI", key="meta_imei_in")
        if st.button("Добавить IMEI", key="meta_imei_btn"):
            try:
                wb_api.add_imei(order_id, imei)
                st.success("IMEI добавлен")
            except Exception as e:
                st.error(str(e))
    with colm[3]:
        gtin = st.text_input("GTIN", key="meta_gtin_in")
        if st.button("Добавить GTIN", key="meta_gtin_btn"):
            try:
                wb_api.add_gtin(order_id, gtin)
                st.success("GTIN добавлен")
            except Exception as e:
                st.error(str(e))
    with colm[4]:
        exp = st.text_input("Срок годности (YYYY-MM-DD)", key="meta_exp_in")
        if st.button("Добавить срок годности", key="meta_exp_btn"):
            try:
                wb_api.add_expiration(order_id, exp)
                st.success("Срок годности добавлен/обновлен")
            except Exception as e:
                st.error(str(e))

    if st.button("Показать метаданные заказа", key="meta_show_btn"):
        try:
            st.json(wb_api.get_order_meta(order_id))
        except Exception as e:
            st.error(str(e))

# ---------- PASSES ----------
with tab_pass:
    st.subheader("Пропуска на офисы WB")
    if st.button("Получить офисы, где требуется пропуск", key="pass_offices_btn"):
        try:
            st.json(wb_api.get_pass_offices())
        except Exception as e:
            st.error(str(e))

    st.divider()
    st.subheader("Мои пропуска")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Список пропусков", key="pass_list_btn"):
            try:
                st.json(wb_api.get_passes())
            except Exception as e:
                st.error(str(e))
    with c2:
        st.caption("Создать пропуск")
        office_id = st.number_input("officeId", min_value=0, value=0, key="pass_office_id")
        car = st.text_input("Госномер", "", key="pass_car")
        date_from = st.date_input("Дата с", datetime.utcnow().date(), key="pass_date_from")
        date_to = st.date_input("Дата по", datetime.utcnow().date(), key="pass_date_to")
        driver = st.text_input("Водитель (опционально)", "", key="pass_driver")
        if st.button("Создать пропуск", key="pass_create_btn"):
            try:
                res = wb_api.create_pass(office_id, car, date_from.isoformat(), date_to.isoformat(), driver_name=driver or None)
                st.json(res)
            except Exception as e:
                st.error(str(e))
