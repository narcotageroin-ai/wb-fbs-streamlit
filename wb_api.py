import os
import requests

class WBApiError(Exception):
    pass

WB_API_TOKEN = os.getenv("WB_API_TOKEN", "").strip()
WB_ENV = os.getenv("WB_ENV", "prod").lower().strip()

if WB_ENV == "sandbox":
    BASE_URL = "https://suppliers-api-sandbox.wildberries.ru"
else:
    BASE_URL = "https://suppliers-api.wildberries.ru"


def set_token(token: str | None):
    global WB_API_TOKEN
    WB_API_TOKEN = (token or "").strip()


def _headers():
    return {
        "Authorization": WB_API_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _request(method: str, path: str, **kwargs):
    if not WB_API_TOKEN:
        raise WBApiError("WB_API_TOKEN is not set. Put it in .env, secrets or environment variables.")
    url = f"{BASE_URL}{path}"
    resp = requests.request(method, url, headers=_headers(), **kwargs)
    if resp.status_code >= 400:
        raise WBApiError(f"WB API error {resp.status_code}: {resp.text}")
    return resp.json()


def get_new_orders():
    return _request("GET", "/api/v3/orders/new")


def get_orders(date_from: str, date_to: str):
    return _request("GET", f"/api/v3/orders?dateFrom={date_from}&dateTo={date_to}")
