import os
import random
import string
import sys
from pathlib import Path
from typing import Dict

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ad_api_client import AdApiClient  # noqa: E402
from mock_service import MockAdServer  # noqa: E402


@pytest.fixture(scope="session")
def base_url() -> str:
    live_url = os.environ.get("SERVICE_BASE_URL")
    if live_url:
        return live_url.rstrip("/")
    with MockAdServer() as server:
        yield server.base_url


@pytest.fixture()
def client(base_url: str) -> AdApiClient:
    return AdApiClient(base_url)


@pytest.fixture()
def sample_payload() -> Dict[str, object]:
    return {
        "title": "Велосипед",
        "description": "Горный, хорошее состояние",
        "price": 15000,
        "sellerId": random.randint(111111, 999999),
    }


def random_string(length: int) -> str:
    return "".join(random.choices(string.ascii_letters, k=length))


@pytest.fixture()
def long_payload(sample_payload):
    payload = dict(sample_payload)
    payload["title"] = random_string(260)
    payload["description"] = random_string(2100)
    return payload
