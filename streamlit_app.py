import streamlit as st
from datetime import datetime

st.title("WB FBS Streamlit App — Fixed Keys")

tab1, tab2 = st.tabs(["Заказы", "Поставки"])

with tab1:
    date_from = st.date_input("Дата с", datetime.utcnow().date(), key="orders_date_from")
    date_to = st.date_input("Дата по", datetime.utcnow().date(), key="orders_date_to")

with tab2:
    date_from = st.date_input("Дата с", datetime.utcnow().date(), key="supplies_date_from")
    date_to = st.date_input("Дата по", datetime.utcnow().date(), key="supplies_date_to")

st.write("✅ У всех date_input теперь уникальные ключи")
