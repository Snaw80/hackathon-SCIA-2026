import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "evaluate_models.py"
SPEC = importlib.util.spec_from_file_location("evaluate_models", SCRIPT)
evaluate_models = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluate_models)
Budget = evaluate_models.Budget


def test_evaluation_budget_reserves_both_provider_attempts():
    budget = Budget(1.0)

    budget.reserve("gpt-5.6-luna", [("human", "short prompt")], 384)

    assert budget.calls == 2
