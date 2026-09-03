from fastapi.testclient import TestClient
from meltdown.api import create_app


def test_public_api_rejects_stale_turn_and_exports_no_private_data(tmp_path):
    with TestClient(create_app(tmp_path / "api.sqlite")) as client:
        response = client.post("/api/games")
        assert response.status_code == 201
        game = response.json()
        url = f"/api/games/{game['id']}"
        request = {"request_id": "api-1", "expected_version": 0, "actions": ["audit"]}
        first = client.post(url + "/turns", json=request)
        assert first.status_code == 200
        assert client.post(url + "/turns", json=request).json() == first.json()
        stale = client.post(url + "/turns", json={**request, "request_id": "api-2"})
        assert stale.status_code == 409
        exported = client.get(url + "/export")
        assert exported.status_code == 200
        assert "demo_acceptable" not in exported.text
        assert "private_goal" not in exported.text
        assert client.get("/api/games/missing").status_code == 404
