"""Утилита для обращения к API объявлений.

По умолчанию используется базовый URL, заданный через переменную
окружения ``SERVICE_BASE_URL``. Если она не установлена, тесты
поднимают локальный мок-сервер и подают его URL в клиент.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


def _prepare_request(url: str, method: str, payload: Optional[Dict[str, Any]] = None) -> urllib.request.Request:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    return urllib.request.Request(url, data=data, headers=headers, method=method)


def _handle_response(response: urllib.request.HTTPResponse) -> Dict[str, Any]:
    body = response.read().decode("utf-8") if response.length is None or response.length > 0 else "{}"
    try:
        return json.loads(body) if body else {}
    except json.JSONDecodeError:
        return {"raw": body}


@dataclass
class ApiResult:
    status: int
    body: Dict[str, Any]


class AdApiClient:
    """Клиент для взаимодействия с сервисом объявлений."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (base_url or os.environ.get("SERVICE_BASE_URL") or "http://localhost:8000").rstrip("/")

    def _request(self, path: str, method: str, payload: Optional[Dict[str, Any]] = None) -> ApiResult:
        url = urllib.parse.urljoin(self.base_url + "/", path.lstrip("/"))
        req = _prepare_request(url, method, payload)
        try:
            with urllib.request.urlopen(req) as resp:  # type: ignore[arg-type]
                return ApiResult(status=resp.status, body=_handle_response(resp))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8") if exc.fp else ""
            parsed = {}
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = {"raw": body}
            return ApiResult(status=exc.code, body=parsed)

    def create_item(self, payload: Dict[str, Any]) -> ApiResult:
        return self._request("/api/1/item", "POST", payload)

    def get_item(self, item_id: str) -> ApiResult:
        return self._request(f"/api/1/item/{item_id}", "GET")

    def list_items(self, seller_id: Any) -> ApiResult:
        query = urllib.parse.urlencode({"sellerId": seller_id})
        return self._request(f"/api/1/items?{query}", "GET")

    def get_statistics(self, item_id: str) -> ApiResult:
        return self._request(f"/api/1/statistics/{item_id}", "GET")
