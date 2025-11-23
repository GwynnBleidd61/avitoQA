"""Примитивный HTTP-мок, эмулирующий сервис объявлений."""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse


@dataclass
class Item:
    id: str
    title: str
    description: str
    price: int
    sellerId: int
    createdAt: str


@dataclass
class Stats:
    itemId: str
    views: int = 0
    contacts: int = 0
    favorites: int = 0


@dataclass
class Storage:
    items: Dict[str, Item] = field(default_factory=dict)
    stats: Dict[str, Stats] = field(default_factory=dict)
    counter: int = 0

    def next_id(self) -> str:
        self.counter += 1
        return str(self.counter)


class Handler(BaseHTTPRequestHandler):
    server_version = "MockAdServer/1.0"

    def _json_response(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> Optional[Dict[str, Any]]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    @property
    def storage(self) -> Storage:
        return self.server.storage  # type: ignore[attr-defined]

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") == "/api/1/item":
            self._handle_create_item()
        else:
            self.send_error(404, "Not Found")

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/1/item/"):
            item_id = parsed.path.split("/")[-1]
            self._handle_get_item(item_id)
        elif parsed.path.startswith("/api/1/items"):
            params = parse_qs(parsed.query)
            seller_ids = params.get("sellerId")
            seller = seller_ids[0] if seller_ids else None
            self._handle_list_items(seller)
        elif parsed.path.startswith("/api/1/statistics/"):
            item_id = parsed.path.split("/")[-1]
            self._handle_stats(item_id)
        else:
            self.send_error(404, "Not Found")

    def _validate_item(self, payload: Optional[Dict[str, Any]]) -> List[str]:
        errors: List[str] = []
        if payload is None:
            return ["body must be JSON"]
        for field_name in ["title", "description", "price", "sellerId"]:
            if field_name not in payload:
                errors.append(f"missing field: {field_name}")
        title = payload.get("title", "")
        if not isinstance(title, str) or not title:
            errors.append("title must be non-empty string")
        if isinstance(title, str) and len(title) > 255:
            errors.append("title too long")
        description = payload.get("description", "")
        if not isinstance(description, str) or not description:
            errors.append("description must be non-empty string")
        if isinstance(description, str) and len(description) > 2000:
            errors.append("description too long")
        price = payload.get("price")
        if not isinstance(price, int) or price <= 0:
            errors.append("price must be positive integer")
        seller_id = payload.get("sellerId")
        if not isinstance(seller_id, int) or not (111111 <= seller_id <= 999999):
            errors.append("sellerId must be int in range 111111-999999")
        return errors

    def _handle_create_item(self) -> None:
        payload = self._read_json()
        errors = self._validate_item(payload)
        if errors:
            self._json_response(400, {"errors": errors})
            return
        assert payload is not None
        item_id = self.storage.next_id()
        item = Item(
            id=item_id,
            title=payload["title"],
            description=payload["description"],
            price=payload["price"],
            sellerId=payload["sellerId"],
            createdAt=datetime.now(timezone.utc).isoformat(),
        )
        self.storage.items[item_id] = item
        self.storage.stats[item_id] = Stats(itemId=item_id)
        self._json_response(201, {"item": asdict(item)})

    def _handle_get_item(self, item_id: str) -> None:
        item = self.storage.items.get(item_id)
        if not item:
            self._json_response(404, {"error": "item not found"})
            return
        self._json_response(200, {"item": asdict(item)})

    def _handle_list_items(self, seller: Optional[str]) -> None:
        try:
            seller_id = int(seller) if seller is not None else None
        except ValueError:
            self._json_response(400, {"error": "sellerId must be integer"})
            return
        if seller_id is None:
            self._json_response(400, {"error": "sellerId is required"})
            return
        if not (111111 <= seller_id <= 999999):
            self._json_response(400, {"error": "sellerId must be in range 111111-999999"})
            return
        items = [asdict(item) for item in self.storage.items.values() if item.sellerId == seller_id]
        items.sort(key=lambda x: x["createdAt"])
        self._json_response(200, {"items": items})

    def _handle_stats(self, item_id: str) -> None:
        stats = self.storage.stats.get(item_id)
        if not stats:
            self._json_response(404, {"error": "stats not found"})
            return
        self._json_response(200, {"statistics": asdict(stats)})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


class MockAdServer:
    """Контекстный менеджер для запуска мок-сервера в фоновом потоке."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self.server = ThreadingHTTPServer((host, port), Handler)
        self.server.storage = Storage()  # type: ignore[attr-defined]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        host, port = self.server.server_address
        return f"http://{host}:{port}"

    def __enter__(self) -> "MockAdServer":
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.shutdown()
        self.thread.join(timeout=2)
