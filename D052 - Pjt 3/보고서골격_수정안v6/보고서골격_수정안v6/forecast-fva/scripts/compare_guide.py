"""가이드 형식 비교표: 베이스라인 3개 + 후보 모형을 같은 원점·같은 지표로 나란히 놓습니다.

    python scripts/compare_guide.py

두 가지로 나눠 계산합니다.
- 전체: 실제 휴관일을 뺀 모든 날
- 무료 개방일·공휴일 제외: 공휴일, 명절 연휴, 마지막 수요일을 뺀 날

결과: output/guide_table.csv (전체·제외 비용과 WAPE), output/guide_per_origin_wape.csv (원점별 WAPE)
먼저 run_classic.py, run_stat.py, run_chronos.py 로 예측 파일을 만들어야 합니다.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RESULTS = ROOT / "results"

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from forecast_fva.config import CAP, OUTPUT_DIR  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402
from forecast_fva.evaluation import staff_cost  # noqa: E402

# 가이드의 베이스라인 3개 (같은 원점·같은 지표로 비교)
BASELINES = ["나이브", "계절나이브7", "직전7일평균"]
# 비교할 후보 모형 (저장된 예측 이름과 맞춰야 함)
CANDIDATES = ["앙상블(Chronos+Prophet)", "Chronos-2 + 달력", "LightGBM 0.8 분위수", "배율+월 (행6)", "Prophet"]


def _metrics(g):
    cost = int(staff_cost(g.pred, g.total, g.planned_closed).sum())
    fc = np.where(g.planned_closed == 1, 0, np.nan_to_num(g.pred))
    wape = round(np.abs(g.total - fc).sum() / g.total.sum() * 100, 1)
    return cost, wape


def _hit_rate(g):
    """적중률: 필요 인력(실제 ÷ 2,000)이 배치 인력(예측 ÷ 2,000) 이하였던 날의 비율.
    예정 휴관은 배치 0명으로 계산합니다."""
    staff = np.where(g.planned_closed == 1, 0.0, np.nan_to_num(g.pred) / CAP)
    need = g.total.values / CAP
    return round(float((need <= staff).mean() * 100), 1)


def main():
    files = sorted(OUTPUT_DIR.glob("pred_*.csv"))
    if not files:
        sys.exit("예측 파일이 없습니다. run_classic.py 등을 먼저 실행하세요.")
    pred = pd.concat([pd.read_csv(f, parse_dates=["origin", "date"]) for f in files], ignore_index=True)

    data = load_train()
    data = data[["site", "date", "total", "actual_closed", "planned_closed",
                 "is_holiday", "is_myeongjeol", "is_last_wednesday"]]
    m = pred.merge(data, on=["site", "date"])
    m = m[m.actual_closed == 0].copy()
    m["special"] = (m.is_holiday == 1) | (m.is_myeongjeol == 1) | (m.is_last_wednesday == 1)

    rows = []
    for name in BASELINES + CANDIDATES:
        g = m[m.model == name]
        if g.empty:
            continue
        cost_all, wape_all = _metrics(g)
        cost_ex, wape_ex = _metrics(g[~g.special])
        rows.append({"모형": name, "구분": "베이스라인" if name in BASELINES else "후보",
                     "총비용 전체(원)": cost_all, "WAPE 전체(%)": wape_all,
                     "적중률 전체(%)": _hit_rate(g),
                     "총비용 제외(원)": cost_ex, "WAPE 제외(%)": wape_ex,
                     "적중률 제외(%)": _hit_rate(g[~g.special])})
    table = pd.DataFrame(rows)
    print(table.to_string(index=False))
    table.to_csv(OUTPUT_DIR / "guide_table.csv", index=False, encoding="utf-8-sig")

    # 원점별 WAPE (가이드: 지표 값은 원점별로도 보고)
    per = {}
    for name in BASELINES + CANDIDATES:
        g = m[m.model == name]
        if g.empty:
            continue
        per[name] = g.groupby(g.origin.dt.strftime("%Y-%m")).apply(lambda x: _metrics(x)[1])
    per_df = pd.DataFrame(per)
    print("\n원점별 WAPE(%)")
    print(per_df.to_string())
    per_df.to_csv(OUTPUT_DIR / "guide_per_origin_wape.csv", encoding="utf-8-sig")

    # 전체 모형 비교표 (엑셀에서 열 수 있는 CSV, 비용 순)
    all_rows = []
    for name, g in m.groupby("model"):
        cost_all, wape_all = _metrics(g)
        cost_ex, wape_ex = _metrics(g[~g.special])
        all_rows.append({"모형": name, "구분": _category(name),
                         "총 비용 전체(원)": cost_all, "WAPE 전체(%)": wape_all,
                         "적중률 전체(%)": _hit_rate(g),
                         "총 비용 제외(원)": cost_ex, "WAPE 제외(%)": wape_ex,
                         "적중률 제외(%)": _hit_rate(g[~g.special])})
    all_table = pd.DataFrame(all_rows).sort_values("총 비용 전체(원)").reset_index(drop=True)
    RESULTS.mkdir(exist_ok=True)
    all_table.to_csv(RESULTS / "모형_비교_전체.csv", index=False, encoding="utf-8-sig")
    print(f"\n저장: {RESULTS / '모형_비교_전체.csv'}")


def _category(name):
    if name.startswith("앙상블"):
        return "앙상블 (최종)"
    if name.startswith("Chronos"):
        return "사전학습"
    if name in ("Prophet", "ETS", "ARIMA", "SARIMA"):
        return "통계"
    if name.startswith("LightGBM"):
        return "머신러닝"
    if name.startswith("배율"):
        return "배율 모형"
    if name == "서비스수준보정":
        return "기준 보정"
    return "베이스라인"


if __name__ == "__main__":
    main()
