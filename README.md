# WB FBS Streamlit (Fixed Keys)

Эта версия исправляет ошибку DuplicateWidgetID в Streamlit —
для всех одинаковых виджетов добавлены уникальные ключи `key=`.

## Запуск локально
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Деплой на Streamlit Cloud
- Указать `streamlit_app.py` как главный файл
- Настроить Secrets:
```toml
WB_API_TOKEN="ваш_токен"
WB_ENV="prod"
```
