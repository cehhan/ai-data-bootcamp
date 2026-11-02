"""자주 하는 실수 측정 (가이드 「자주 하는 실수」 1, 4, 5번).

    python scripts/mistakes.py

측정 1 (1번 실수): 휴관일의 0을 평균에 넣어 학습했을 때와 뺐을 때의 직전 7일 평균 WAPE 차이와 총 비용(소수 인원) 차이
측정 2 (4번 실수): 개소별로 평가할 때와 전체 합계로 평가할 때의 WAPE 차이 (앙상블, 2025년 원점)
측정 3 (5번 실수): 무료 개방일을 paid == 0 으로 정할 때와 달력 규칙으로 정할 때의 차이

결과: results/실수_측정.csv
입력: output/pred_classic.csv, output/pred_chronos.csv, output/pred_prophet.csv, data/train_2023_2025_core_v2.csv
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from forecast_fva.config import ORIGINS  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402
from forecast_fva.evaluation import staff_cost  # noqa: E402
from forecast_fva.config import CAP  # noqa: E402

OUT = ROOT / "output"
RESULTS = ROOT / "results"


def wape(actual, pred):
    return float(np.abs(actual - pred).sum() / actual.sum() * 100)


def measure_zero_handling(tr):
    """1번 실수: 직전 7일 평균을 계산할 때 휴관일 0을 넣는지 뺄지."""
    rows = []
    for origin in ORIGINS:
        end = origin + pd.offsets.MonthBegin(1)
        for site, g in tr.groupby("site"):
            g = g.sort_values("date")
            past = g[g.date < origin]
            last7 = past[past.date >= origin - pd.Timedelta(days=7)]
            with_zero = last7.total.mean()                                   # 0을 그대로 넣음
            without_zero = last7[(last7.actual_closed == 0) & (last7.total > 0)].total.mean()
            tgt = g[(g.date >= origin) & (g.date < end) & (g.actual_closed == 0)]
            for _, r in tgt.iterrows():
                if r.planned_closed == 1:
                    rows.append((r.total, 0.0, 0.0, 0))   # 예정 휴관: 0명 배치 (WAPE에서는 제외)
                    continue
                rows.append((r.total, with_zero, without_zero, 1))
    df = pd.DataFrame(rows, columns=["actual", "zero_in", "zero_out", "keep"])
    # 비용: 본 평가와 같은 규칙 (실제 휴관 제외, 예정 휴관 0명 배치, 소수 인원)
    closed = 1 - df.keep
    cost = {k: float(staff_cost(df[k], df.actual, closed).sum()) for k in ("zero_in", "zero_out")}
    short = {k: float(np.clip(df.actual / CAP - np.where(closed == 1, 0, df[k] / CAP), 0, None).sum())
             for k in ("zero_in", "zero_out")}
    df = df[df.keep == 1]
    return (wape(df.actual, df.zero_in), wape(df.actual, df.zero_out), len(df), cost, short)


def measure_aggregation(tr):
    """4번 실수: 개소별 WAPE 와 전체 합계 WAPE 의 차이 (앙상블)."""
    chronos = pd.read_csv(OUT / "pred_chronos.csv", parse_dates=["origin", "date"])
    chronos = chronos[chronos.model == "Chronos-2 + 달력"][["site", "date", "pred"]].rename(columns={"pred": "c"})
    prophet = pd.read_csv(OUT / "pred_prophet.csv", parse_dates=["origin", "date"])[["site", "date", "pred"]]
    prophet = prophet.rename(columns={"pred": "p"})
    m = chronos.merge(prophet, on=["site", "date"]).assign(f=lambda d: (d.c + d.p) / 2)
    m = m.merge(tr[["site", "date", "total", "actual_closed", "planned_closed"]], on=["site", "date"])
    m = m[(m.actual_closed == 0) & (m.planned_closed == 0)]
    site_level = wape(m.total, m.f)
    daily = m.groupby("date")[["total", "f"]].sum()
    total_level = wape(daily.total, daily.f)
    return site_level, total_level


def measure_free_day_rule(tr):
    """5번 실수: 무료 개방일을 paid == 0 으로 정하면 달력 규칙과 얼마나 달라지는가 (개방일 기준)."""
    op = tr[(tr.total > 0)].copy()
    op["rule"] = (op.is_myeongjeol == 1) | (op.is_last_wednesday == 1)
    op["paid0"] = op.paid == 0
    per = op.groupby("site").agg(
        개방일=("date", "size"),
        달력규칙=("rule", "sum"),
        paid0=("paid0", "sum"),
    )
    per["달력과 paid0 불일치"] = (per.달력규칙 - per.paid0).abs()
    return per.sort_values("달력과 paid0 불일치", ascending=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", default="", help="유료 관람객(paid)이 들어 있는 전체 학습 CSV 경로 (측정 3번용)")
    args = ap.parse_args()

    tr = load_train()
    rows = []

    w_zero_in, w_zero_out, n, cost, short = measure_zero_handling(tr)
    rows.append({"실수": "1. 휴관 0을 수요로 학습 (직전 7일 평균)",
                 "측정값": f"WAPE 휴관 0 포함 {w_zero_in:.1f}% vs 제외 {w_zero_out:.1f}%",
                 "차이": f"{w_zero_in - w_zero_out:+.1f}%p", "표본": f"{n}행"})
    d = cost["zero_in"] - cost["zero_out"]
    rows.append({"실수": "1. 휴관 0을 수요로 학습 (직전 7일 평균) - 비용",
                 "측정값": f"총 비용 소수 휴관 0 포함 {cost['zero_in']:,.0f}원 vs 제외 {cost['zero_out']:,.0f}원",
                 "차이": f"{d:+,.0f}원 ({d / cost['zero_out'] * 100:+.1f}%), 모자란 인원 {short['zero_in'] - short['zero_out']:+,.0f}명",
                 "표본": "실제 휴관 제외, 예정 휴관 0명"})

    site_w, total_w = measure_aggregation(tr)
    rows.append({"실수": "4. 합계로 평가 (앙상블)",
                 "측정값": f"WAPE 개소별 {site_w:.1f}% vs 합계 {total_w:.1f}%",
                 "차이": f"{total_w - site_w:+.1f}%p", "표본": "개소 × 날짜"})

    per = None
    if args.full:
        full = pd.read_csv(args.full, parse_dates=["date"], encoding="utf-8-sig")
        per = measure_free_day_rule(full)
        mismatch = int(per["달력과 paid0 불일치"].sum())
        rows.append({"실수": "5. 유료 0을 무료 개방일로 봄",
                     "측정값": f"불일치 날 {mismatch}일 (개소 {int((per['달력과 paid0 불일치'] > 0).sum())}곳)",
                     "차이": "개소별로 기준이 달라짐", "표본": "2023~2025 개방일"})
    else:
        print("측정 5번은 건너뜀: --full 로 유료 관람객 파일 경로를 주세요.")

    table = pd.DataFrame(rows)
    print(table.to_string(index=False))
    RESULTS.mkdir(exist_ok=True)
    table.to_csv(RESULTS / "실수_측정.csv", index=False, encoding="utf-8-sig")
    if per is not None:
        print("\n개소별 무료 개방일 판정 불일치 (상위 8곳)")
        print(per.head(8).to_string())
        per.to_csv(RESULTS / "실수_측정_무료개방_개소별.csv", encoding="utf-8-sig")
    print(f"\n저장: {RESULTS / '실수_측정.csv'}")


if __name__ == "__main__":
    main()
