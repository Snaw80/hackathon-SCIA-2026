"""Record two complete games through the public HTTP API, with no private state."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from uuid import uuid4


def request(base, route, body=None):
    req = Request(base + route, data=json.dumps(body).encode() if body is not None else None, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=60) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:3000/api")
    parser.add_argument("--output", type=Path, default=Path("docs/evidence"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    strategies = {
        "negotiated-delivery": [["audit", "prioritize_fix"], ["clarify", "communicate"], ["reduce_scope", "rest"], [], [], ["release"]],
        "no-intervention": [[], [], [], [], [], []],
    }
    summaries = []
    for name, decisions in strategies.items():
        game = request(args.url, "/games", {})
        turns = []
        for actions in decisions:
            game = request(args.url, f"/games/{game['id']}/turns", {"request_id": str(uuid4()), "expected_version": game["version"], "actions": actions})
            turns.append({"turn": game["turn"], "actions": actions, "metrics": game["metrics"], "run": game["last_run"]})
        assert game["status"] == "finished"
        evidence = {"recorded_at": datetime.now(timezone.utc).isoformat(), "strategy": name, "mode": game["mode"], "turns": turns, "final_public_state": game}
        (args.output / f"{name}.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
        summary = {"strategy": name, "outcome": game["outcome"], "metrics": game["metrics"], "turns": game["turn"], "agent_calls": sum(t["run"]["agent_calls"] for t in turns), "fallbacks": sum(t["run"]["fallbacks"] for t in turns)}
        summaries.append(summary)
        print(json.dumps(summary, ensure_ascii=False))
    assert summaries[0]["outcome"]["code"] != summaries[1]["outcome"]["code"]


if __name__ == "__main__":
    main()
