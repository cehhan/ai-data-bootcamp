"""요구사항 8: 근무표 확정 시점별 비용 — 월 1회 확정(현재 설계) vs 주 1회 확정.

    python scripts/run_weekly.py --jobs 4             # 주 1회 (Chronos + Prophet). Prophet 약 1,200번 학습 → Colab 권장
    python scripts/run_weekly.py --biweekly --jobs 4  # 2주 1회도 함께 계산 (선택)
    python scripts/run_weekly.py --only chronos       # Chronos 만 (GPU 있는 곳에서)
    python scripts/run_weekly.py --only prophet       # Prophet 만 (Colab 에서)
    python scripts/run_weekly.py --only table         # 저장된 예측으로 표만 다시 만들기

설계
- 월 1회: 원점 = 2025년 매월 1일 12개, 그달 전체 예측 (기존 output/pred_ensemble.csv, pred_classic.csv 사용)
- 주 1회: 원점 = 2025년 매주 월요일, 7일(월~일) 예측. 근무표를 전날(일요일)에 확정한다고 가정
- 2주 1회(선택): 격주 월요일, 14일 예측
- 모형: 직전 7일 평균(행 1), 서비스 수준 보정(행 2), 최종 앙상블(Chronos-2 + 달력 · Prophet 50:50) — 모두 같은 방식으로 다시 계산
- 비교는 '모든 방식이 예측한 같은 날짜'(2025-01-06 ~ 2025-12-31)에서만 합니다
- 평가 규칙은 동일: 실제 휴관 제외, 예정 휴관 0명, 비용은 소수 인원 기준 (권고 규칙 비용도 함께)

중간 결과: output/weekly/ (끊겨도 이어서 계산)
결과: results/확정시점_비교.csv, results/확정시점_비교_월별.csv
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
from forecast_fva.baseline import service_ratio  # noqa: E402
from forecast_fva.config import OUTPUT_DIR  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402
from forecast_fva.evaluation import hit_rate, staff_cost  # noqa: E402
from forecast_fva.horizon_models import predict_chronos_h, predict_prophet_h  # noqa: E402

WEEK_DIR = OUTPUT_DIR / "weekly"
RESULTS = ROOT / "results"
ENS = "앙상블(Chronos+Prophet)"

PLANS = {
    # 이름: (원점 목록, 예측 길이(일), 근무자가 일정을 아는 시점 설명)
    "주 1회": (pd.date_range("2025-01-06", "2025-12-29", freq="W-MON"), 7, "1~7일 전 (평균 4일 전)"),
    "2주 1회": (pd.date_range("2025-01-06", "2025-12-29", freq="2W-MON"), 14, "1~14일 전 (평균 7.5일 전)"),
}
MONTHLY_NOTICE = "1~31일 전 (평균 약 16일 전)"


def _p(name):
    return WEEK_DIR / f"{name}.csv"


def _load(name):
    return pd.read_csv(_p(name), parse_dates=["origin", "date"]) if _p(name).exists() else None


def _save(df, name):
    WEEK_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(_p(name), index=False, encoding="utf-8-sig")


def baseline_h(df, origins, horizon):
    """직전 7일 평균(원점 전 7일 중 문 연 날의 평균)과 서비스 수준 보정을 예측 길이만큼."""
    last = df.date.max()
    rows = []
    for origin in origins:
        hist = df[(df.date < origin) & (df.date >= origin - pd.Timedelta(days=7))
                  & (df.actual_closed == 0) & (df.total > 0)]
        last7 = hist.groupby("site").total.mean()
        ratio = pd.Series(service_ratio(df, origin))
        dates = pd.date_range(origin, min(origin + pd.Timedelta(days=horizon - 1), last))
        for s in df.site.unique():
            if s not in last7.index:
                continue
            for d in dates:
                rows.append((origin, s, d, last7[s], last7[s] * ratio.get(s, 1.0)))
    b = pd.DataFrame(rows, columns=["origin", "site", "date", "직전7일평균", "서비스수준보정"])
    return b.melt(id_vars=["origin", "site", "date"], var_name="model", value_name="pred")


def build(df, plan_names, only, jobs):
    pipe = None
    for name in plan_names:
        origins, h, _ = PLANS[name]
        key = name.replace(" ", "")
        if only in ("all", "baseline", "chronos", "prophet") and _load(f"baseline_{key}") is None:
            print(f"[{name}] 직전 7일 평균·서비스 수준 보정")
            _save(baseline_h(df, origins, h), f"baseline_{key}")
        if only in ("all", "chronos") and _load(f"chronos_{key}") is None:
            if pipe is None:
                from forecast_fva.chronos_model import load_pipe
                pipe = load_pipe()
            print(f"[{name}] Chronos-2 + 달력 (원점 {len(origins)}개)")
            _save(predict_chronos_h(df, pipe, origins, h), f"chronos_{key}")
        if only in ("all", "prophet") and _load(f"prophet_{key}") is None:
            print(f"[{name}] Prophet (원점 {len(origins)}개 × 23개소)")
            _save(predict_prophet_h(df, origins, h, n_jobs=jobs), f"prophet_{key}")


def monthly_predictions():
    ens_p, cls_p = OUTPUT_DIR / "pred_ensemble.csv", OUTPUT_DIR / "pred_classic.csv"
    if not ens_p.exists() or not cls_p.exists():
        sys.exit("output/pred_ensemble.csv 와 output/pred_classic.csv 가 필요합니다 (월 1회 결과).")
    ens = pd.read_csv(ens_p, parse_dates=["origin", "date"])[["origin", "site", "date", "pred"]].assign(model=ENS)
    cls = pd.read_csv(cls_p, parse_dates=["origin", "date"])
    cls = cls[cls.model.isin(["직전7일평균", "서비스수준보정"])][["origin", "site", "date", "pred", "model"]]
    return pd.concat([ens, cls], ignore_index=True)


def plan_predictions(name):
    key = name.replace(" ", "")
    b, c, p = _load(f"baseline_{key}"), _load(f"chronos_{key}"), _load(f"prophet_{key}")
    parts = [b] if b is not None else []
    if c is not None and p is not None:
        m = c.merge(p, on=["origin", "site", "date"], suffixes=("_c", "_p"))
        parts.append(m.assign(pred=(m.pred_c + m.pred_p) / 2, model=ENS)[["origin", "site", "date", "pred", "model"]])
    else:
        print(f"  {name}: Chronos 또는 Prophet 예측이 아직 없어 앙상블을 표에서 뺍니다.")
    return pd.concat(parts, ignore_index=True) if parts else None


def build_table(df, plan_names):
    data = df[["site", "date", "total", "actual_closed", "planned_closed"]]
    sets = {"월 1회": monthly_predictions()}
    for n in plan_names:
        p = plan_predictions(n)
        if p is not None:
            sets[n] = p

    # 공통 평가 날짜: 모든 방식이 예측한 (개소, 날짜)
    keys = None
    for pred in sets.values():
        k = set(map(tuple, pred[pred.model == "직전7일평균"][["site", "date"]].values))
        keys = k if keys is None else keys & k
    common = pd.DataFrame(list(keys), columns=["site", "date"])
    print(f"공통 평가 날짜: {common.date.min().date()} ~ {common.date.max().date()}")

    rows, monthly = [], []
    notice = {"월 1회": MONTHLY_NOTICE, **{n: PLANS[n][2] for n in plan_names}}
    for plan, pred in sets.items():
        m = pred.merge(common, on=["site", "date"]).merge(data, on=["site", "date"])
        m = m[m.actual_closed == 0]
        for model, g in m.groupby("model"):
            frac, rule = cost_parts(g, "소수"), cost_parts(g, "권고 규칙")
            pe = np.where(g.planned_closed == 1, 0, np.nan_to_num(g.pred))
            rows.append({"확정 방식": plan, "모형": model, "원점 수": g.origin.nunique(),
                         "근무자가 일정을 아는 시점": notice[plan],
                         "총 비용 소수(원)": frac["총 비용(원)"], "총 비용 권고 규칙(원)": rule["총 비용(원)"],
                         "WAPE(%)": round(float(np.abs(g.total - pe).sum() / g.total.sum() * 100), 1),
                         "적중률(%)": hit_rate(g, "pred"), "평가 행 수": len(g)})
            mm = g.assign(cost=staff_cost(g.pred, g.total, g.planned_closed), month=g.date.dt.month)
            monthly.append(mm.groupby("month").cost.sum().rename(f"{plan} | {model}"))

    t = pd.DataFrame(rows)
    order = {"직전7일평균": 0, "서비스수준보정": 1, ENS: 2}
    t = t.sort_values(["모형", "확정 방식"], key=lambda s: s.map(order) if s.name == "모형" else s).reset_index(drop=True)
    base = t[t["확정 방식"] == "월 1회"].set_index("모형")["총 비용 소수(원)"]
    t["월 1회 대비 차이 소수(원)"] = t["총 비용 소수(원)"] - t["모형"].map(base)
    RESULTS.mkdir(exist_ok=True)
    t.to_csv(RESULTS / "확정시점_비교.csv", index=False, encoding="utf-8-sig")
    pd.concat(monthly, axis=1).round(0).to_csv(RESULTS / "확정시점_비교_월별.csv", encoding="utf-8-sig")
    pd.set_option("display.width", 240)
    print(t.drop(columns=["평가 행 수"]).to_string(index=False))
    if t["평가 행 수"].nunique() != 1:
        print("  경고: 행마다 평가 행 수가 다릅니다. 같은 날짜를 비교하는지 확인하세요.")
    print(f"\n음수 = 월 1회보다 쌈. 저장: {RESULTS / '확정시점_비교.csv'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["all", "baseline", "chronos", "prophet", "table"], default="all")
    ap.add_argument("--biweekly", action="store_true", help="2주 1회 확정도 계산")
    ap.add_argument("--jobs", type=int, default=1, help="Prophet 병렬 작업 수")
    args = ap.parse_args()
    plans = ["주 1회"] + (["2주 1회"] if args.biweekly else [])
    df = load_train()
    if args.only != "table":
        build(df, plans, args.only, args.jobs)
    build_table(df, plans)


if __name__ == "__main__":
    main()
