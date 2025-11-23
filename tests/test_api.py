import pytest

from ad_api_client import AdApiClient


def assert_item_body(body: dict, payload: dict) -> None:
    assert "item" in body, "Ответ должен содержать ключ 'item'"
    item = body["item"]
    for field in ["id", "title", "description", "price", "sellerId", "createdAt"]:
        assert field in item, f"Отсутствует поле {field}"
    assert item["title"] == payload["title"]
    assert item["description"] == payload["description"]
    assert item["price"] == payload["price"]
    assert item["sellerId"] == payload["sellerId"]


def test_create_item_success(client: AdApiClient, sample_payload: dict):
    result = client.create_item(sample_payload)
    assert result.status in (200, 201)
    assert_item_body(result.body, sample_payload)


def test_get_existing_item(client: AdApiClient, sample_payload: dict):
    created = client.create_item(sample_payload)
    item_id = created.body["item"]["id"]

    fetched = client.get_item(item_id)
    assert fetched.status == 200
    assert fetched.body["item"]["id"] == item_id
    assert fetched.body["item"]["title"] == sample_payload["title"]


def test_list_items_by_seller(client: AdApiClient, sample_payload: dict):
    payload_a1 = dict(sample_payload)
    payload_a2 = dict(sample_payload)
    payload_b = dict(sample_payload)
    payload_b["sellerId"] = payload_a1["sellerId"] + 1

    created_a1 = client.create_item(payload_a1)
    created_a2 = client.create_item(payload_a2)
    client.create_item(payload_b)

    response = client.list_items(payload_a1["sellerId"])
    assert response.status == 200
    items = response.body.get("items", [])
    ids = {i["id"] for i in items}
    assert created_a1.body["item"]["id"] in ids
    assert created_a2.body["item"]["id"] in ids
    assert len(items) == 2
    assert items == sorted(items, key=lambda x: x["createdAt"])


def test_statistics_existing_item(client: AdApiClient, sample_payload: dict):
    created = client.create_item(sample_payload)
    item_id = created.body["item"]["id"]

    stats = client.get_statistics(item_id)
    assert stats.status == 200
    stats_body = stats.body.get("statistics") or stats.body.get("stats")
    assert stats_body is not None, "Ответ статистики должен содержать тело"
    assert stats_body["itemId"] == item_id
    for field in ["views", "contacts", "favorites"]:
        assert field in stats_body
        assert isinstance(stats_body[field], int)
        assert stats_body[field] >= 0


def test_create_item_missing_field(client: AdApiClient, sample_payload: dict):
    bad_payload = dict(sample_payload)
    bad_payload.pop("title")
    response = client.create_item(bad_payload)
    assert response.status == 400
    assert any("title" in err for err in response.body.get("errors", []))


def test_create_item_invalid_price(client: AdApiClient, sample_payload: dict):
    bad_payload = dict(sample_payload)
    bad_payload["price"] = 0
    response = client.create_item(bad_payload)
    assert response.status == 400


def test_create_item_invalid_seller_id(client: AdApiClient, sample_payload: dict):
    bad_payload = dict(sample_payload)
    bad_payload["sellerId"] = 100
    response = client.create_item(bad_payload)
    assert response.status == 400


def test_list_items_invalid_query(client: AdApiClient):
    response = client.list_items("abc")
    assert response.status == 400


def test_create_item_too_long(client: AdApiClient, long_payload: dict):
    response = client.create_item(long_payload)
    assert response.status == 400
    assert response.body.get("errors")


def test_get_missing_item(client: AdApiClient):
    result = client.get_item("99999")
    assert result.status == 404


def test_statistics_missing_item(client: AdApiClient):
    result = client.get_statistics("99999")
    assert result.status == 404
