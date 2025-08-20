import streamlit as st
import os
import wb_api

st.title("WB FBS Sandbox Tester")

with st.sidebar:
    token_default = st.secrets.get("WB_API_TOKEN", os.getenv("WB_API_TOKEN", ""))
    token = st.text_input("WB API Token", value=token_default, type="password")
    env_default = st.secrets.get("WB_ENV", os.getenv("WB_ENV", "prod"))
    env = st.selectbox("Среда", ["prod", "sandbox"], index=0 if env_default=="prod" else 1)
    if token:
        wb_api.set_token(token)
    os.environ["WB_ENV"] = env

if st.button("Получить новые заказы"):
    try:
        data = wb_api.get_new_orders()
        st.json(data)
    except Exception as e:
        st.error(str(e))
