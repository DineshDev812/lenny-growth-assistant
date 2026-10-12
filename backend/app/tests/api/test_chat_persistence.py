from __future__ import annotations

from fastapi.testclient import TestClient


def test_streaming_persistence_single_and_multi_turn(client: TestClient) -> None:
    # 1. Create a fresh session
    create_res = client.post("/api/sessions", json={"title": "New chat"})
    assert create_res.status_code == 201
    session_id = create_res.json()["id"]

    # 2. Stream turn 1
    stream_res1 = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "What is product-led growth?"},
        headers={"Accept": "text/event-stream"},
    )
    assert stream_res1.status_code == 200
    assert "event: done" in stream_res1.text

    # 3. GET session to prove both messages persisted in DB
    get_res1 = client.get(f"/api/sessions/{session_id}")
    assert get_res1.status_code == 200
    data1 = get_res1.json()
    assert len(data1["messages"]) == 2

    user_msg1 = data1["messages"][0]
    assistant_msg1 = data1["messages"][1]

    assert user_msg1["role"] == "user"
    assert user_msg1["content"] == "What is product-led growth?"
    assert user_msg1["seq"] is not None

    assert assistant_msg1["role"] == "assistant"
    assert len(assistant_msg1["content"]) > 0
    assert assistant_msg1["provider"] is not None
    assert assistant_msg1["model"] is not None
    assert assistant_msg1["seq"] is not None
    assert assistant_msg1["seq"] > user_msg1["seq"]

    # 4. Stream turn 2 (follow-up)
    stream_res2 = client.post(
        f"/api/sessions/{session_id}/messages",
        json={"content": "What about for enterprise B2B?"},
        headers={"Accept": "text/event-stream"},
    )
    assert stream_res2.status_code == 200
    assert "event: done" in stream_res2.text

    # 5. GET session again to verify 4 messages monotonically ordered
    get_res2 = client.get(f"/api/sessions/{session_id}")
    assert get_res2.status_code == 200
    data2 = get_res2.json()
    assert len(data2["messages"]) == 4

    seqs = [m["seq"] for m in data2["messages"]]
    assert seqs == sorted(seqs)
    assert len(set(seqs)) == 4  # All distinct monotonic sequence numbers
