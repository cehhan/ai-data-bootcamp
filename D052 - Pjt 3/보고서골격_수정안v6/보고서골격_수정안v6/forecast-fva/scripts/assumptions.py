"""가정 바꾸기: 비용 가정을 바꿨을 때 앙상블과 직전 7일 평균의 결과가 얼마나 달라지는지 계산합니다.

    python scripts/assumptions.py

예측값(관람객)은 그대로 두고, 비용 가정만 바꿉니다.
- 비용 기준은 소수만 씁니다: 인원 = 예측 관람객 ÷ 1명당 담당 관람객 (비용 비교용)
- 기본: 모자람 60만, 남음 15만, 1명당 2,000명
- 가정 1: 무료 개방일(명절 연휴·마지막 수요일)의 모자람 비용을 2배(120만)로
- 가정 2: 1명당 담당 관람객을 2,000명에서 1,500명으로
- 가정 3: 가정 1 + 가정 2를 함께

입력: output/pred_classic.csv(직전 7일 평균), output/pred_ensemble.csv (먼저 run_classic, run_stat --prophet, run_chronos 등 필요)
결과: results/가정_바꾸기.csv
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from forecast_fva.config import CO, CU  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402

OUT = ROOT / "output"
RESULTS = ROOT / "results"


def load_predictions():
    classic = pd.read_csv(OUT / "pred_classic.csv", parse_dates=["origin", "date"])
    base = classic[classic.model == "직전7일평균"][["origin", "site", "date", "pred"]]
    ens = pd.read_csv(OUT / "pred_ensemble.csv", parse_dates=["origin", "date"])[["origin", "site", "date", "pred"]]
    return base, ens


def cost(frame, pred, cu, cap, rule):
    """하루 비용. 예정 휴관은 0명.
    rule 이 '소수'이면 인원 = 예측 ÷ cap (소수 그대로),
    '권고 규칙'이면 인원 = 올림, 영업일 최소 1명.
    cu 는 날마다 다를 수 있는 모자람 비용 배열."""
    closed = frame.planned_closed.values == 1
    raw = np.nan_to_num(frame.pred.values if pred is None else pred) / cap
    if rule == "권고 규칙":
        staff = np.where(closed, 0.0, np.maximum(1, np.ceil(raw)))
    else:
        staff = np.where(closed, 0.0, raw)
    need = frame.total.values / cap
    return cu * np.maximum(need - staff, 0) + CO * np.maximum(staff - need, 0)


def main():
    tr = load_train()
    base, ens = load_predictions()
    rows = []
    scenarios = [
        ("기본 가정", False, 2_000),
        ("가정 1: 무료 개방일 모자람 비용 2배", True, 2_000),
        ("가정 2: 1명당 1,500명", False, 1_500),
        ("가정 3: 가정 1 + 가정 2", True, 1_500),
    ]
    for rule in ["소수"]:
        for name, double_free, cap in scenarios:
            totals = {}
            for model, pred in [("직전 7일 평균", base), ("앙상블(Chronos+Prophet)", ens)]:
                m = pred.merge(tr[["site", "date", "total", "actual_closed", "planned_closed",
                                   "is_myeongjeol", "is_last_wednesday"]], on=["site", "date"])
                m = m[m.actual_closed == 0].copy()
                free = ((m.is_myeongjeol == 1) | (m.is_last_wednesday == 1)).values
                cu = np.where(free & double_free, 2 * CU, CU)
                totals[model] = int(cost(m, m.pred.values, cu, cap, rule).sum())
            saving = totals["직전 7일 평균"] - totals["앙상블(Chronos+Prophet)"]
            rows.append({"가정": name,
                         "직전 7일 평균 총 비용(원)": totals["직전 7일 평균"],
                         "앙상블 총 비용(원)": totals["앙상블(Chronos+Prophet)"],
                         "앙상블 절감액(원)": saving,
                         "절감 비율(%)": round(saving / totals["직전 7일 평균"] * 100, 1)})

    table = pd.DataFrame(rows)
    print(table.to_string(index=False))
    RESULTS.mkdir(exist_ok=True)
    table.to_csv(RESULTS / "가정_바꾸기.csv", index=False, encoding="utf-8-sig")
    print(f"\n저장: {RESULTS / '가정_바꾸기.csv'}")


if __name__ == "__main__":
    main()
