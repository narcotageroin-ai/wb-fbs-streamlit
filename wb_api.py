import os
import time
import typing as t
from dataclasses import dataclass
import requests
from dotenv import load_dotenv

load_dotenv()

WB_ENV = os.getenv("WB_ENV", "prod").lower().strip()
WB_API_TOKEN = os.getenv("WB_API_TOKEN", "").strip()

BASE_URL = "https://marketplace-api.wildberries.ru"

def _headers() -> dict:
    return {
        "Authorization": WB_API_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

class WBApiError(Exception):
    def __init__(self, status: int, message: str, payload: dict | None = None):
        super().__init__(f"WB API error {status}: {message}")
        self.status = status
        self.payload = payload or {}

def set_token(token: str | None):
    """Update token at runtime (e.g., after user pastes it in Streamlit sidebar)."""
    global WB_API_TOKEN
    if token is None:
        token = ""
    WB_API_TOKEN = token.strip()

def _check_token():
    if not WB_API_TOKEN:
        raise WBApiError(401, "WB_API_TOKEN is not set. Put it in .env or environment variables.")

def _request(method: str, path: str, *, params: dict | None=None, json: dict | None=None, stream: bool=False):
    _check_token()
    url = f"{BASE_URL}{path}"
    resp = requests.request(method, url, headers=_headers(), params=params, json=json, timeout=60, stream=stream)
    if resp.status_code >= 400:
        try:
            err = resp.json()
            msg = err.get("message") or err
        except Exception:
            msg = resp.text[:1000]
        raise WBApiError(resp.status_code, str(msg))
    return resp

# -------- FBS Assembly Orders --------
def get_new_orders() -> dict:
    return _request("GET", "/api/v3/orders/new").json()

def get_orders(limit: int=1000, next_val: int=0, date_from: int|None=None, date_to: int|None=None) -> dict:
    params = {"limit": limit, "next": next_val}
    if date_from: params["dateFrom"] = date_from
    if date_to: params["dateTo"] = date_to
    return _request("GET", "/api/v3/orders", params=params).json()

def get_orders_status(order_ids: list[int]) -> dict:
    return _request("POST", "/api/v3/orders/status", json={"orders": order_ids}).json()

def cancel_order(order_id: int) -> None:
    _request("PATCH", f"/api/v3/orders/{order_id}/cancel")

def get_stickers(order_ids: list[int], *, fmt: str="png", width: int=58, height: int=40) -> bytes:
    params = {"type": fmt, "width": width, "height": height}
    resp = _request("POST", "/api/v3/orders/stickers", params=params, json={"orders": order_ids}, stream=True)
    return resp.content

def get_orders_with_client(order_ids: list[int]) -> dict:
    return _request("POST", "/api/v3/orders/client", json={"orders": order_ids}).json()

# -------- Metadata --------
def add_sgtin(order_id: int, sgtin: str):
    _request("PUT", f"/api/v3/orders/{order_id}/meta/sgtin", json={"sgtin": sgtin})

def add_uin(order_id: int, uin: str):
    _request("PUT", f"/api/v3/orders/{order_id}/meta/uin", json={"uin": uin})

def add_imei(order_id: int, imei: str):
    _request("PUT", f"/api/v3/orders/{order_id}/meta/imei", json={"imei": imei})

def add_gtin(order_id: int, gtin: str):
    _request("PUT", f"/api/v3/orders/{order_id}/meta/gtin", json={"gtin": gtin})

def add_expiration(order_id: int, expiration_date_iso: str):
    _request("PUT", f"/api/v3/orders/{order_id}/meta/expiration", json={"date": expiration_date_iso})

def get_order_meta(order_id: int) -> dict:
    return _request("GET", f"/api/v3/orders/{order_id}/meta").json()

# -------- Supplies workflow --------
def create_supply(destination_office_id: int | None=None) -> dict:
    payload = {}
    if destination_office_id is not None:
        payload["destinationOfficeId"] = destination_office_id
    return _request("POST", "/api/v3/supplies", json=payload).json()

def list_supplies(limit: int=100, next_val: int=0) -> dict:
    params = {"limit": limit, "next": next_val}
    return _request("GET", "/api/v3/supplies", params=params).json()

def add_order_to_supply(supply_id: str, order_id: int):
    _request("PATCH", f"/api/v3/supplies/{supply_id}/orders/{order_id}")

def get_supply(supply_id: str) -> dict:
    return _request("GET", f"/api/v3/supplies/{supply_id}").json()

def delete_supply(supply_id: str):
    _request("DELETE", f"/api/v3/supplies/{supply_id}")

def get_supply_orders(supply_id: str) -> dict:
    return _request("GET", f"/api/v3/supplies/{supply_id}/orders").json()

def deliver_supply(supply_id: str):
    _request("PATCH", f"/api/v3/supplies/{supply_id}/deliver")

def get_supply_qr(supply_id: str, fmt: str="png") -> bytes:
    params = {"type": fmt}
    return _request("GET", f"/api/v3/supplies/{supply_id}/barcode", params=params, stream=True).content

def get_supply_boxes(supply_id: str) -> dict:
    return _request("GET", f"/api/v3/supplies/{supply_id}/trbx").json()

def add_boxes(supply_id: str, amount: int) -> dict:
    return _request("POST", f"/api/v3/supplies/{supply_id}/trbx", json={"amount": amount}).json()

def delete_boxes(supply_id: str, trbx_ids: list[str]):
    _request("DELETE", f"/api/v3/supplies/{supply_id}/trbx", json={"trbxIds": trbx_ids})

def get_box_stickers(supply_id: str, trbx_ids: list[str], fmt: str="png") -> bytes:
    params = {"type": fmt}
    return _request("POST", f"/api/v3/supplies/{supply_id}/trbx/stickers", params=params, json={"trbxIds": trbx_ids}, stream=True).content

# -------- Passes --------
def get_pass_offices() -> dict:
    return _request("GET", "/api/v3/passes/offices").json()

def get_passes() -> dict:
    return _request("GET", "/api/v3/passes").json()

def create_pass(office_id: int, car_number: str, date_from_iso: str, date_to_iso: str, driver_name: str | None=None) -> dict:
    payload = {
        "officeId": office_id,
        "vehicleNumber": car_number,
        "dateFrom": date_from_iso,
        "dateTo": date_to_iso,
    }
    if driver_name:
        payload["driverName"] = driver_name
    return _request("POST", "/api/v3/passes", json=payload).json()

def update_pass(pass_id: int, payload: dict) -> dict:
    return _request("PUT", f"/api/v3/passes/{pass_id}", json=payload).json()

def delete_pass(pass_id: int):
    _request("DELETE", f"/api/v3/passes/{pass_id}")
