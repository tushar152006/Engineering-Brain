from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_repository_index_search_chat_and_summary() -> None:
    repo = Path("tests/fixtures/demo-repo").resolve()

    client = TestClient(app)

    index_response = client.post(
        "/api/repositories/index",
        json={"source": "local", "local_path": str(repo), "name": "demo-repo"},
    )
    assert index_response.status_code == 200
    repo_id = index_response.json()["repository"]["id"]

    search_response = client.post(
        "/api/search",
        json={"repo_id": repo_id, "query": "authentication indexing"},
    )
    assert search_response.status_code == 200
    assert search_response.json()["results"]

    chat_response = client.post(
        "/api/chat",
        json={"repo_id": repo_id, "question": "How does authentication work?"},
    )
    assert chat_response.status_code == 200
    assert chat_response.json()["citations"]

    summary_response = client.post("/api/architecture-summary", json={"repo_id": repo_id})
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert "demo-repo" in summary["summary"]
    assert summary["frameworks"]
    assert "main.py" in summary["entrypoints"]
