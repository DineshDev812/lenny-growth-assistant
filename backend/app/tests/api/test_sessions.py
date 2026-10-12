from fastapi.testclient import TestClient


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


def test_message_persistence_and_response(client: TestClient) -> None:
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
    assert len(payload["assistant_message"]["content"]) > 0
    assert payload["assistant_message"]["provider"]
    assert payload["assistant_message"]["model"]

    again = client.get(f"/api/sessions/{session_id}")
    assert again.status_code == 200
    detail = again.json()
    assert detail["title"] == "What is product-led growth?"
    assert len(detail["messages"]) == 2
    assert detail["messages"][0]["content"] == "What is product-led growth?"
    assert detail["messages"][1]["content"] == payload["assistant_message"]["content"]

    second = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "follow-up"},
    )
    assert second.status_code == 201
    persisted = client.get(f"/api/sessions/{session_id}")
    assert len(persisted.json()["messages"]) == 4
    assert persisted.json()["title"] == "What is product-led growth?"


def test_messages_ordered_by_monotonic_seq(client: TestClient) -> None:
    created = client.post("/api/sessions", json={})
    session_id = created.json()["id"]

    for i in range(3):
        res = client.post(
            f"/api/sessions/{session_id}/messages",
            json={"content": f"Message {i}"},
        )
        assert res.status_code == 201

    res = client.get(f"/api/sessions/{session_id}")
    assert res.status_code == 200
    messages = res.json()["messages"]
    assert len(messages) == 6
    seqs = [m["seq"] for m in messages if m.get("seq") is not None]
    assert len(seqs) == 6
    assert seqs == sorted(seqs)


def test_session_rename(client: TestClient) -> None:
    created = client.post("/api/sessions", json={})
    session_id = created.json()["id"]

    renamed = client.patch(f"/api/sessions/{session_id}", json={"title": "Updated Title"})
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Updated Title"

    got = client.get(f"/api/sessions/{session_id}")
    assert got.json()["title"] == "Updated Title"


def test_streaming_sse_messages(client: TestClient) -> None:
    created = client.post("/api/sessions", json={})
    session_id = created.json()["id"]

    res = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "What is activation?"},
        headers={"Accept": "text/event-stream"},
    )
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    text = res.text
    assert "event: start" in text
    assert "event: sources" in text
    assert "event: token" in text
    assert "event: done" in text

    # Verify streaming persistence (1.1 bug fix verification):
    # Both user and assistant messages must be saved in the database!
    get_res = client.get(f"/api/sessions/{session_id}")
    assert get_res.status_code == 200
    session_data = get_res.json()
    assert len(session_data["messages"]) == 2
    assert session_data["messages"][0]["role"] == "user"
    assert session_data["messages"][0]["content"] == "What is activation?"
    assert session_data["messages"][1]["role"] == "assistant"
    assert len(session_data["messages"][1]["content"]) > 0
    assert session_data["messages"][1]["provider"]
    assert session_data["messages"][1]["model"]


def test_essay_and_artifact_flow(client: TestClient) -> None:
    created = client.post("/api/sessions", json={})
    session_id = created.json()["id"]

    res = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "Write a ship 30 essay on retention", "intent": "essay"},
    )
    assert res.status_code == 201
    payload = res.json()
    assert payload["artifact"] is not None
    art_id = payload["artifact"]["id"]
    assert payload["artifact"]["format"] == "markdown"

    art_res = client.get(f"/api/artifacts/{art_id}")
    assert art_res.status_code == 200
    art = art_res.json()
    assert art["id"] == art_id
    assert art["format"] == "markdown"
    assert len(art["content"]) > 0

    # Test artifact isolation: unauthorized client gets 404
    client.cookies.clear()
    denied = client.get(f"/api/artifacts/{art_id}")
    assert denied.status_code == 404
    assert denied.json()["error"]["code"] == "not_found"


def test_delete_session_and_cascade(client: TestClient) -> None:
    created = client.post("/api/sessions", json={})
    session_id = created.json()["id"]

    client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "Hello to be deleted"},
    )

    del_res = client.delete(f"/api/sessions/{session_id}")
    assert del_res.status_code == 204

    get_res = client.get(f"/api/sessions/{session_id}")
    assert get_res.status_code == 404
    assert get_res.json()["error"]["code"] == "not_found"

    # Delete non-existent or other user session returns 404
    client.cookies.clear()
    del_other = client.delete(f"/api/sessions/{session_id}")
    assert del_other.status_code == 404


def test_message_too_long(client: TestClient) -> None:
    created = client.post("/api/sessions", json={})
    session_id = created.json()["id"]

    long_text = "a" * 4001
    res = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": long_text},
    )
    assert res.status_code == 400
    body = res.json()
    assert body["error"]["code"] == "message_too_long"


def test_rate_limiting(client: TestClient) -> None:
    from app.core.middleware import reset_rate_limits
    reset_rate_limits()

    created = client.post("/api/sessions", json={})
    assert created.status_code == 201

    responses = [client.get("/api/sessions") for _ in range(25)]
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes
    rate_limited_res = next(r for r in responses if r.status_code == 429)
    assert rate_limited_res.headers.get("retry-after") == "60"
    assert rate_limited_res.json()["error"]["code"] == "rate_limited"

    reset_rate_limits()
