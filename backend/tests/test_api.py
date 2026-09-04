import time

from fastapi.testclient import TestClient
from meltdown.api import create_app
from meltdown.agents import RulesPolicy
from meltdown.models import AgentIntent


def poll_phase(client, game_id, *phases):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        game = client.get(f"/api/games/{game_id}").json()
        run = game.get("active_run")
        if run and run["phase"] in phases:
            return game
        time.sleep(0.01)
    raise AssertionError(f"Game did not reach one of {phases}")


def test_public_api_rejects_stale_turn_and_exports_no_private_data(tmp_path):
    with TestClient(create_app(tmp_path / "api.sqlite")) as client:
        response = client.post("/api/games")
        assert response.status_code == 201
        game = response.json()
        url = f"/api/games/{game['id']}"
        request = {"request_id": "api-1", "expected_version": 0, "command": "Audit the defect"}
        first = client.post(url + "/turns", json=request)
        assert first.status_code == 202
        assert client.post(url + "/turns", json=request).json()["active_run"]["id"] == first.json()[
            "active_run"
        ]["id"]
        completed = poll_phase(client, game["id"], "complete")
        assert completed["turn"] == 1
        assert completed["active_run"]["interpretation"]["actions"] == ["audit"]
        stale = client.post(url + "/turns", json={**request, "request_id": "api-2"})
        assert stale.status_code == 409
        exported = client.get(url + "/export")
        assert exported.status_code == 200
        assert "demo_acceptable" not in exported.text
        assert "private_goal" not in exported.text
        assert client.get("/api/games/missing").status_code == 404


def test_ambiguous_command_waits_for_confirmation_without_advancing(tmp_path):
    with TestClient(create_app(tmp_path / "ambiguous.sqlite")) as client:
        game = client.post("/api/games").json()
        accepted = client.post(
            f"/api/games/{game['id']}/turns",
            json={"request_id": "ambiguous-1", "expected_version": 0, "command": "Handle it"},
        )
        assert accepted.status_code == 202
        waiting = poll_phase(client, game["id"], "needs_confirmation")
        run = waiting["active_run"]
        assert waiting["turn"] == 0
        assert run["interpretation"]["confidence"] == "ambiguous"

        replacement = client.post(
            f"/api/games/{game['id']}/runs/{run['id']}/confirmation",
            json={"request_id": "confirmation-1", "command": "Audit the defect"},
        )
        assert replacement.status_code == 202
        completed = poll_phase(client, game["id"], "complete")
        assert completed["turn"] == 1


class QuestionPolicy(RulesPolicy):
    def decide(self, context):
        if context["actor"] == "client" and "ask_player" in context["allowed_actions"]:
            return AgentIntent(
                action="ask_player",
                question="What will the smaller demo contain?",
                question_reason="I need scope clarity.",
            )
        return super().decide(context)


def test_agent_questions_are_answered_through_the_active_run(tmp_path):
    with TestClient(create_app(tmp_path / "questions.sqlite", policy=QuestionPolicy())) as client:
        game = client.post("/api/games").json()
        first = client.post(
            f"/api/games/{game['id']}/turns",
            json={"request_id": "clarify-1", "expected_version": 0, "command": "Clarify client needs"},
        )
        assert first.status_code == 202
        game = poll_phase(client, game["id"], "complete")

        second = client.post(
            f"/api/games/{game['id']}/turns",
            json={
                "request_id": "scope-1",
                "expected_version": 1,
                "command": "Reduce the delivery scope",
            },
        )
        assert second.status_code == 202
        waiting = poll_phase(client, game["id"], "awaiting_answers")
        run = waiting["active_run"]
        assert waiting["turn"] == 1
        assert [question["actor"] for question in run["questions"]] == ["client"]

        answered = client.post(
            f"/api/games/{game['id']}/runs/{run['id']}/answers",
            json={
                "request_id": "answer-1",
                "answers": [
                    {
                        "question_id": run["questions"][0]["id"],
                        "text": "The secure core workflow.",
                    }
                ],
            },
        )
        assert answered.status_code == 202
        completed = poll_phase(client, game["id"], "complete")
        assert completed["turn"] == 2
        assert any(event["type"] == "player_answer" for event in completed["events"])
