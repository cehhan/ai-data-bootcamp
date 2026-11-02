"""백테스트 비용: 과거 날짜에 같은 방법으로 인력을 정했을 때 모자란 비용과 남는 비용, 직전 7일 평균 대비 절감액.

    python scripts/backtest_cost.py

두 가지 인원 규칙으로 계산합니다.
- 소수: 예측 관람객 ÷ 2,000명 (기존 비교표와 같은 규칙)
- 권고 규칙: 올림, 영업일 최소 1명 (운영팀 근무표 규칙, scripts/forecast_2026.py 와 같음)

실제 휴관일은 평가에서 뺍니다. 예정 휴관은 0명 배치입니다.
입력: output/pred_ensemble.csv, output/pred_classic.csv (직전7일평균)
결과: results/백테스트_비용.csv
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from forecast_fva.config import CAP, CO, CU, OUTPUT_DIR  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402

RESULTS = ROOT / "results"
BASE = "직전7일평균"
ENS = "앙상블(Chronos+Prophet)"


def load_predictions():
    ens = pd.read_csv(OUTPUT_DIR / "pred_ensemble.csv", parse_dates=["origin", "date"])
    ens = ens[["origin", "site", "date", "pred"]].assign(model=ENS)
    classic = pd.read_csv(OUTPUT_DIR / "pred_classic.csv", parse_dates=["origin", "date"])
    base = classic[classic.model == BASE][["origin", "site", "date", "pred"]].assign(model=BASE)
    return pd.concat([ens, base], ignore_index=True)


def cost_parts(g, rule):
    """모자란 인원·비용, 남는 인원·비용을 나눠 합산합니다."""
    closed = g.planned_closed.values == 1
    if rule == "소수":
        staff = np.where(closed, 0.0, np.nan_to_num(g.pred.values) / CAP)
    else:  # 권고 규칙: 올림, 영업일 최소 1명
        staff = np.where(closed, 0.0, np.maximum(1, np.ceil(np.nan_to_num(g.pred.values) / CAP)))
    need = g.total.values / CAP
    short = np.maximum(need - staff, 0)
    spare = np.maximum(staff - need, 0)
    return {"모자란 인원(명)": round(short.sum(), 1), "모자란 비용(원)": int(round(CU * short.sum())),
            "남는 인원(명)": round(spare.sum(), 1), "남는 비용(원)": int(round(CO * spare.sum())),
            "총 비용(원)": int(round(CU * short.sum() + CO * spare.sum()))}


def main():
    tr = load_train()
    data = tr[["site", "date", "total", "actual_closed", "planned_closed"]]
    m = load_predictions().merge(data, on=["site", "date"])
    m = m[m.actual_closed == 0]

    rows = []
    for rule in ["소수", "권고 규칙"]:
        base_cost = None
        for name in [BASE, ENS]:
            r = cost_parts(m[m.model == name], rule)
            if name == BASE:
                base_cost = r["총 비용(원)"]
            r.update({"규칙": rule, "모형": name,
                      "절감액(원)": base_cost - r["총 비용(원)"] if name != BASE else 0,
                      "절감 비율(%)": round((base_cost - r["총 비용(원)"]) / base_cost * 100, 1) if name != BASE else 0.0})
            rows.append(r)

    table = pd.DataFrame(rows)[["규칙", "모형", "모자란 인원(명)", "모자란 비용(원)", "남는 인원(명)",
                                  "남는 비용(원)", "총 비용(원)", "절감액(원)", "절감 비율(%)"]]
    print(table.to_string(index=False))
    RESULTS.mkdir(exist_ok=True)
    table.to_csv(RESULTS / "백테스트_비용.csv", index=False, encoding="utf-8-sig")
    print(f"\n저장: {RESULTS / '백테스트_비용.csv'}")


if __name__ == "__main__":
    main()
