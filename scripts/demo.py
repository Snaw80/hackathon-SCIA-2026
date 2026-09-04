"""Record complete natural-command games through the public API, with no private state."""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4


def request(base, route, body=None):
    req = Request(
        base + route,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=60) as response:
        return json.load(response)


def finish_run(base, game):
    deadline = time.monotonic() + 90
    answered = False
    while time.monotonic() < deadline:
        game = request(base, f"/games/{game['id']}")
        run = game.get("active_run")
        if run and run["phase"] == "complete":
            return game, answered
        if run and run["phase"] == "awaiting_answers":
            game = request(
                base,
                f"/games/{game['id']}/runs/{run['id']}/answers",
                {
                    "request_id": str(uuid4()),
                    "answers": [
                        {
                            "question_id": question["id"],
                            "text": "I will provide a secure core demonstration and share progress evidence.",
                        }
                        for question in run["questions"]
                    ],
                },
            )
            answered = True
        elif run and run["phase"] in ("needs_confirmation", "failed"):
            raise RuntimeError(f"Demo run stopped in {run['phase']}: {run.get('error')}")
        time.sleep(0.1)
    raise TimeoutError("Demo run did not complete")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:3000/api")
    parser.add_argument("--output", type=Path, default=Path("docs/evidence"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    strategies = {
        "negotiated-delivery": [
            "Audit the defect and prioritize the security fix",
            "Clarify the client needs and share a status update",
            "Reduce the delivery scope and reduce the team workload",
            "Continue the current work",
            "Continue the current work",
            "Release the version",
        ],
        "no-intervention": ["Continue the current work"] * 6,
        "interactive-delay": [
            "Continue the current work",
            "Continue the current work",
            "Continue the current work",
            "Continue the current work",
            "Request an extension",
            "Continue the current work",
        ],
    }
    summaries = []
    for name, commands in strategies.items():
        game = request(args.url, "/games", {})
        turns = []
        answered = False
        for command in commands:
            game = request(
                args.url,
                f"/games/{game['id']}/turns",
                {
                    "request_id": str(uuid4()),
                    "expected_version": game["version"],
                    "command": command,
                },
            )
            game, turn_answered = finish_run(args.url, game)
            answered = answered or turn_answered
            turns.append(
                {
                    "turn": game["turn"],
                    "command": command,
                    "interpretation": game["active_run"]["interpretation"],
                    "metrics": game["metrics"],
                    "run": game["last_run"],
                }
            )
        assert game["status"] == "finished"
        if name == "interactive-delay":
            assert answered, "The interactive demo must exercise the question pause."
        evidence = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "strategy": name,
            "mode": game["mode"],
            "turns": turns,
            "answered_agent_question": answered,
            "final_public_state": game,
        }
        (args.output / f"{name}.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n"
        )
        summary = {
            "strategy": name,
            "outcome": game["outcome"],
            "metrics": game["metrics"],
            "turns": game["turn"],
            "answered_agent_question": answered,
            "agent_calls": sum(t["run"]["agent_calls"] for t in turns),
            "fallbacks": sum(t["run"]["fallbacks"] for t in turns),
        }
        summaries.append(summary)
        print(json.dumps(summary, ensure_ascii=False))
    assert summaries[0]["outcome"]["code"] != summaries[1]["outcome"]["code"]


if __name__ == "__main__":
    main()
