"""재현 확인: 직전 7일 평균의 총 비용이 기준값(1,702,786,555원)과 같은지 봅니다.

    python tests/test_baseline.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from forecast_fva.baseline import predict_baseline  # noqa: E402
from forecast_fva.config import EXPECTED_BASELINE_COST  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402
from forecast_fva.evaluation import evaluate  # noqa: E402


def test_baseline_cost_reproduces():
    df = load_train()
    summary, _ = evaluate(predict_baseline(df), df)
    cost = int(summary.set_index("model").loc["직전7일평균", "total_cost"])
    assert cost == EXPECTED_BASELINE_COST, f"기준값과 다릅니다: {cost:,} != {EXPECTED_BASELINE_COST:,}"


if __name__ == "__main__":
    test_baseline_cost_reproduces()
    print("OK: 직전 7일 평균 비용이 기준값과 일치합니다.")
