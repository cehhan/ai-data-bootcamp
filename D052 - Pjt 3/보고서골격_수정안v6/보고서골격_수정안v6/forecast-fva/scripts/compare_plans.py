"""근무표 운영 방안 비교 (요구사항 8 보강): 월 1회 확정 + 공지 행사 증원 vs 주 1회 확정.

    python scripts/compare_plans.py              # 공지 후 증원에 필요한 최소 준비 기간 7일 (기본)
    python scripts/compare_plans.py --lead 14    # 준비 기간 14일로 바꿔 보기

비교하는 방안 (모두 같은 평가 날짜 2025-01-06 ~ 2025-12-31, 실제 휴관 제외, 예정 휴관 0명)
 1. 월 1회 확정                       : 현재 설계 (output/pred_ensemble.csv)
 2. 월 1회 + 공지 행사 증원 (A')      : 근무표는 월 1회로 확정하고, 임시 무료 개방 공지가 나오면
                                        그날로부터 lead 일 이상 남은 행사일만 인원을 추가 (개소별 무료 개방 배율)
 3. 월 1회 + 공지 행사 증원 + 마지막 수요일 하한 (A' + B)
 4. 주 1회 확정                       : output/weekly/ 의 주 1회 앙상블 예측 (run_weekly.py 결과)
 5. 주 1회 + A' + B
 6. 시범안: 궁·종묘 5곳만 주 1회, 왕릉 18곳은 월 1회
 7. 시범안 + A' + B

규칙 A(error_analysis.py)와 A'의 차이
 - A : 공지가 '근무표 확정일(원점 전날)' 전에 나와야 적용 → 월 1회에서는 10/29~31 에 못 씀
 - A': 근무표를 확정한 뒤라도 공지가 행사 lead 일 전에 나오면 그날만 증원 (현실의 '추가 배치')
       → 공지(10/16)가 10/29 보다 13일 앞서므로, lead=7 이면 10/29~11/9 전체에 적용
 배율은 두 규칙 모두 원점 전날까지의 기록으로만 계산합니다.

입력: output/pred_ensemble.csv (필수), output/weekly/chronos_주1회.csv·prophet_주1회.csv (4·5번용, 없으면 건너뜀)
결과: results/운영방안_비교.csv, results/운영방안_비교_구분별.csv
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from backtest_cost import cost_parts  # noqa: E402
from error_analysis import EVENT_DAYS, apply_rules  # noqa: E402
from forecast_fva.config import OUTPUT_DIR  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402
from forecast_fva.evaluation import hit_rate, staff_cost  # noqa: E402
from forecast_fva.horizon_models import free_day_multipliers  # noqa: E402

RESULTS = ROOT / "results"
COLS = ["site", "date", "group", "total", "actual_closed", "planned_closed",
        "is_holiday", "is_myeongjeol", "is_last_wednesday"]
NOTICE = {"월 1회": "1~31일 전 (평균 약 16일 전)", "주 1회": "1~7일 전 (평균 4일 전)",
          "혼합": "궁·종묘 1~7일 전 / 왕릉 1~31일 전"}


def load_monthly(tr):
    p = OUTPUT_DIR / "pred_ensemble.csv"
    if not p.exists():
        sys.exit("output/pred_ensemble.csv 가 없습니다. 먼저 python scripts/ensemble.py 를 실행하세요.")
    e = pd.read_csv(p, parse_dates=["origin", "date"])[["origin", "site", "date", "pred"]]
    return e.merge(tr[COLS], on=["site", "date"])


def load_weekly(tr):
    c, p = OUTPUT_DIR / "weekly" / "chronos_주1회.csv", OUTPUT_DIR / "weekly" / "prophet_주1회.csv"
    if not c.exists() or not p.exists():
        print("  output/weekly/ 의 주 1회 예측이 없어 4·5번 방안은 건너뜁니다 (python scripts/run_weekly.py 결과 필요).")
        return None
    c = pd.read_csv(c, parse_dates=["origin", "date"])
    p = pd.read_csv(p, parse_dates=["origin", "date"])
    m = c.merge(p, on=["origin", "site", "date"], suffixes=("_c", "_p"))
    m = m.assign(pred=(m.pred_c + m.pred_p) / 2)[["origin", "site", "date", "pred"]]
    return m.merge(tr[COLS], on=["site", "date"])


def apply_notice_uplift(frame, tr, lead):
    """A': 근무표 확정 뒤라도 공지일이 행사일보다 lead 일 이상 앞서면 그날 예측 × 개소별 무료 개방 배율."""
    f = frame.copy()
    f["uplift"] = False
    ev = {}
    for e in EVENT_DAYS:
        if e.get("announced") is None:
            continue
        for d in pd.date_range(e["start"], e["end"]):
            ev[d] = pd.Timestamp(e["announced"])
    for origin, g in f.groupby("origin"):
        ok = g.date.map(lambda d: d in ev and (d - ev[d]).days >= lead)
        ok &= (g.planned_closed == 0) & (g.is_last_wednesday == 0) & (g.is_myeongjeol == 0)
        idx = g.index[ok.values]
        if len(idx) == 0:
            continue
        mult = free_day_multipliers(tr, origin, kind="last_wednesday")
        f.loc[idx, "pred_adj"] = f.loc[idx, "pred_adj"] * f.loc[idx, "site"].map(mult).clip(lower=1.0)
        f.loc[idx, "uplift"] = True
    return f


def plan_frames(monthly, weekly, tr, lead):
    plans = {}
    plans["1. 월 1회 확정"] = ("월 1회", monthly.assign(pred_adj=monthly.pred, uplift=False))
    a = apply_notice_uplift(monthly.assign(pred_adj=monthly.pred), tr, lead)
    plans[f"2. 월 1회 + 공지 행사 증원 (공지 {lead}일 전까지)"] = ("월 1회", a)
    b = apply_rules(monthly, tr, use_a=False, use_b=True)               # pred_adj = 규칙 B 적용값
    ab = apply_notice_uplift(b, tr, lead)
    plans["3. 월 1회 + 공지 행사 증원 + 마지막 수요일 하한"] = ("월 1회", ab)
    if weekly is not None:
        plans["4. 주 1회 확정"] = ("주 1회", weekly.assign(pred_adj=weekly.pred, uplift=False))
        wab = apply_notice_uplift(apply_rules(weekly, tr, use_a=False, use_b=True), tr, lead)
        plans["5. 주 1회 + 공지 행사 증원 + 마지막 수요일 하한"] = ("주 1회", wab)
        # 궁·종묘 5곳만 주 1회 시범 적용, 왕릉 18곳은 월 1회 유지
        core = weekly.group.isin(["궁", "종묘"])
        plans["6. 시범안: 궁·종묘 주 1회 + 왕릉 월 1회"] = ("혼합", pd.concat([
            weekly[core].assign(pred_adj=weekly[core].pred, uplift=False),
            monthly[monthly.group == "왕릉"].assign(pred_adj=monthly[monthly.group == "왕릉"].pred, uplift=False)],
            ignore_index=True))
        plans["7. 시범안 + 공지 행사 증원 + 마지막 수요일 하한"] = (
            "혼합", pd.concat([wab[wab.group.isin(["궁", "종묘"])], ab[ab.group == "왕릉"]], ignore_index=True))
    return plans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lead", type=int, default=7, help="공지 후 증원에 필요한 최소 준비 기간(일)")
    args = ap.parse_args()
    pd.set_option("display.width", 240)

    tr = load_train()
    monthly, weekly = load_monthly(tr), load_weekly(tr)

    # 공통 평가 날짜: 주 1회 예측이 있으면 그 범위(2025-01-06 ~), 없으면 월 1회 전체
    keys = set(map(tuple, monthly[["site", "date"]].values))
    if weekly is not None:
        keys &= set(map(tuple, weekly[["site", "date"]].values))
    common = pd.DataFrame(list(keys), columns=["site", "date"])
    print(f"공통 평가 날짜: {common.date.min().date()} ~ {common.date.max().date()}")

    rows, by_group = [], []
    for name, (kind, f) in plan_frames(monthly, weekly, tr, args.lead).items():
        g = f.merge(common, on=["site", "date"])
        g = g[g.actual_closed == 0]
        ev = g.assign(pred=g.pred_adj)
        frac, rule = cost_parts(ev, "소수"), cost_parts(ev, "권고 규칙")
        rows.append({"방안": name, "근무자가 일정을 아는 시점": NOTICE[kind],
                     "총 비용 소수(원)": frac["총 비용(원)"], "총 비용 권고 규칙(원)": rule["총 비용(원)"],
                     "적중률(%)": hit_rate(ev, "pred"), "증원한 행 수": int(g.uplift.sum()),
                     "평가 행 수": len(g)})
        c = ev.assign(cost=staff_cost(ev.pred, ev.total, ev.planned_closed))
        by_group.append(c.groupby("group").cost.sum().rename(name))

    t = pd.DataFrame(rows)
    base = t["총 비용 소수(원)"].iloc[0]
    t["월 1회 대비 절감 소수(원)"] = base - t["총 비용 소수(원)"]
    if "4. 주 1회 확정" in set(t["방안"]):
        weekly_gain = base - int(t.loc[t["방안"] == "4. 주 1회 확정", "총 비용 소수(원)"].iloc[0])
        if weekly_gain > 0:
            t["주 1회 절감의 몇 %(%)"] = (t["월 1회 대비 절감 소수(원)"] / weekly_gain * 100).round(1)
    RESULTS.mkdir(exist_ok=True)
    t.to_csv(RESULTS / "운영방안_비교.csv", index=False, encoding="utf-8-sig")
    pd.concat(by_group, axis=1).round(0).to_csv(RESULTS / "운영방안_비교_구분별.csv", encoding="utf-8-sig")

    print(t.drop(columns=["평가 행 수"]).to_string(index=False))
    if t["평가 행 수"].nunique() != 1:
        print("  경고: 방안마다 평가 행 수가 다릅니다.")
    print("\n구분별 비용 (소수, 원)\n" + pd.concat(by_group, axis=1).round(0).to_string())
    print(f"\n저장: {RESULTS / '운영방안_비교.csv'}")


if __name__ == "__main__":
    main()
