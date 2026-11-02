"""모든 모형에 같은 방식으로 비용과 WAPE를 계산합니다.

평가 규칙
- 실제 휴관일(actual_closed == 1)은 평가에서 뺍니다.
- 예정 휴관(planned_closed == 1)은 예측과 상관없이 0명 배치로 계산합니다.
- 비용 = 60만 × 모자란 명 + 15만 × 남는 명 (하루 단위, 소수 그대로)
"""
import numpy as np
import pandas as pd

from .config import CAP, CO, CU
from .data import load_train


def staff_cost(pred, actual, planned_closed):
    """하루 비용. pred 는 관람객 예측값 (NaN 은 0으로 취급)."""
    pred = np.nan_to_num(np.asarray(pred, dtype=float))
    staff = np.where(np.asarray(planned_closed) == 1, 0.0, pred / CAP)
    need = np.asarray(actual, dtype=float) / CAP
    return CU * np.maximum(need - staff, 0) + CO * np.maximum(staff - need, 0)


def hit_rate(frame, pred_col):
    """적중률(%): 필요 인력(실제 ÷ 2,000)이 배치 인력(예측 ÷ 2,000) 이하였던 날의 비율.
    예정 휴관은 배치 0명으로 계산합니다. frame 은 실제 휴관을 뺀 날이어야 합니다."""
    staff = np.where(frame.planned_closed.values == 1, 0.0,
                     np.nan_to_num(np.asarray(frame[pred_col], dtype=float)) / CAP)
    need = frame.total.values / CAP
    return round(float((need <= staff).mean() * 100), 1)


def evaluate(pred_long, data=None):
    """pred_long: 열 model, origin, site, date, pred (긴 표).

    반환
    - summary: 모형별 총 비용, WAPE(%), 원점 수
    - per_origin: 원점 × 모형의 비용 (원)
    """
    if data is None:
        data = load_train()
    d = data[["site", "date", "total", "actual_closed", "planned_closed"]]
    m = pred_long.merge(d, on=["site", "date"])
    m = m[m.actual_closed == 0].copy()
    m["cost"] = staff_cost(m.pred, m.total, m.planned_closed)
    m["pred_eval"] = np.where(m.planned_closed == 1, 0, np.nan_to_num(m.pred))

    rows = []
    for name, g in m.groupby("model"):
        wape = np.abs(g.total - g.pred_eval).sum() / g.total.sum() * 100
        rows.append({"model": name, "total_cost": int(g.cost.sum()),
                     "wape": round(wape, 1), "origins": g.origin.nunique()})
    summary = pd.DataFrame(rows).sort_values("total_cost").reset_index(drop=True)
    per_origin = m.pivot_table(index="origin", columns="model", values="cost", aggfunc="sum")
    return summary, per_origin
