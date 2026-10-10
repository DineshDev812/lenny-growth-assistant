from fastapi.testclient import TestClient

from app.services.messages import PLACEHOLDER_ASSISTANT_CONTENT


def test_create_and_list_sessions(client: TestClient) -> None:
    created = client.post(
        "/api/sessions",
        json={"title": "Activation", "user_metadata": {"display_name": "Reviewer"}},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["title"] == "Activation"
    assert body["user_metadata"]["display_name"] == "Reviewer"
    assert body["id"]
    assert "Set-Cookie" in created.headers or client.cookies

    listed = client.get("/api/sessions")
    assert listed.status_code == 200
    ids = [item["id"] for item in listed.json()]
    assert body["id"] in ids


def test_session_isolation(client: TestClient) -> None:
    created = client.post("/api/sessions", json={})
    assert created.status_code == 201
    session_id = created.json()["id"]

    posted = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "secret from client a"},
    )
    assert posted.status_code == 201
    owner_cookies = dict(client.cookies)

    client.cookies.clear()
    other_list = client.get("/api/sessions")
    assert other_list.status_code == 200
    assert other_list.json() == []

    other_get = client.get(f"/api/sessions/{session_id}")
    assert other_get.status_code == 404
    assert other_get.json()["error"]["code"] == "not_found"

    steal = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "hijack"},
    )
    assert steal.status_code == 404

    client.cookies.clear()
    for name, value in owner_cookies.items():
        client.cookies.set(name, value)

    owner = client.get(f"/api/sessions/{session_id}")
    assert owner.status_code == 200
    contents = [message["content"] for message in owner.json()["messages"]]
    assert "secret from client a" in contents
    assert "hijack" not in contents


def test_validation_errors(client: TestClient) -> None:
    created = client.post("/api/sessions", json={})
    session_id = created.json()["id"]

    missing = client.post(f"/api/sessions/{session_id}/messages", json={})
    assert missing.status_code == 422
    error = missing.json()["error"]
    assert error["code"] == "validation_error"
    assert error["request_id"]

    empty = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "   "},
    )
    assert empty.status_code == 422
    assert empty.json()["error"]["code"] == "validation_error"

    bad_id = client.get("/api/sessions/not-a-uuid")
    assert bad_id.status_code == 422
    assert bad_id.json()["error"]["code"] == "validation_error"


def test_message_persistence_and_placeholder(client: TestClient) -> None:
    created = client.post("/api/sessions", json={})
    session_id = created.json()["id"]

    posted = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "What is product-led growth?"},
    )
    assert posted.status_code == 201
    payload = posted.json()
    assert payload["user_message"]["role"] == "user"
    assert payload["user_message"]["content"] == "What is product-led growth?"
    assert payload["assistant_message"]["role"] == "assistant"
    assert "[PLACEHOLDER]" in payload["assistant_message"]["content"]
    assert payload["assistant_message"]["content"] == PLACEHOLDER_ASSISTANT_CONTENT
    assert payload["assistant_message"]["provider"]
    assert payload["assistant_message"]["model"]

    again = client.get(f"/api/sessions/{session_id}")
    assert again.status_code == 200
    detail = again.json()
    assert detail["title"] == "What is product-led growth?"
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["content"] == "What is product-led growth?"
    assert detail["messages"][1]["content"] == PLACEHOLDER_ASSISTANT_CONTENT

    second = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "follow-up"},
    )
    assert second.status_code == 201
    persisted = client.get(f"/api/sessions/{session_id}")
    assert len(persisted.json()["messages"]) == 4
    assert persisted.json()["title"] == "What is product-led growth?"
