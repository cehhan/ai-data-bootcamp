"""「완벽한 예보 가정」 근사: 날씨를 미리 정확히 알았다면 앙상블 비용이 얼마나 줄었을까 (요구사항 6 보조).

    python scripts/weather_upper_bound.py --weather <weather_daily.parquet 경로>

방법 (모형을 다시 학습하지 않는 가벼운 근사)
1. 2025년 백테스트의 앙상블 예측(output/pred_ensemble.csv)과 그날의 실제 날씨(당일 실측)를 붙입니다.
2. 오차 = log(실제 관람객 ÷ 앙상블 예측) 을 날씨로 설명하는 선형 회귀를 만듭니다.
   - 날씨 변수: log(1+강수량), 강수 5mm 이상, 최고기온(그 개소·그 달 평균과의 차이)과 그 제곱, 주말 × log(1+강수량)
   - 기울기는 궁·종묘·왕릉마다 따로 둡니다.
3. 보정 = exp(날씨 효과 − 학습 구간의 평균 날씨 효과). 평균적인 날씨면 예측을 바꾸지 않으므로
   0.8 분위수(서비스 수준)는 그대로 두고 '날씨 때문에 생긴 오차'만 고칩니다.
4. 회귀 계수는 평가하는 달을 뺀 나머지 달로 학습합니다 (원점 하나 빼기, leave-one-origin-out).
   더 엄격한 확인으로 '앞선 원점만으로 학습'한 결과도 함께 냅니다 (1월 원점은 보정 없음).

주의: 당일 실측 날씨를 쓰므로 근무표를 짤 때는 알 수 없는 정보입니다. 반드시 「완벽한 예보 가정」으로 표시하고
다른 결과와 섞어 쓰지 않습니다 (가이드 7쪽). 날씨로 얻을 수 있는 개선의 '상한 근사'입니다.

결과: results/날씨_완벽예보_근사.csv
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from forecast_fva.config import OUTPUT_DIR  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402
from forecast_fva.evaluation import hit_rate, staff_cost  # noqa: E402

RESULTS = ROOT / "results"
GROUPS = ["궁", "종묘", "왕릉"]


def features(m):
    rain = np.log1p(m.precip_mm.clip(lower=0))
    tdev = m.t2m_max - m.groupby(["site", "month"]).t2m_max.transform("mean")
    base = pd.DataFrame({"rain": rain, "rain5": (m.precip_mm >= 5).astype(float),
                         "tdev": tdev, "tdev2": tdev ** 2, "wk_rain": m.is_weekend * rain})
    cols = {}
    for g in GROUPS:
        on = (m.group == g).astype(float)
        for c in base:
            cols[f"{g}:{c}"] = base[c] * on
        cols[f"{g}:const"] = on                       # 구분별 절편 (보정에는 쓰지 않음)
    return pd.DataFrame(cols, index=m.index)


def fit_apply(X, y, train, test):
    beta, *_ = np.linalg.lstsq(X[train].values, y[train].values, rcond=None)
    b = pd.Series(beta, index=X.columns)
    w = [c for c in X.columns if not c.endswith(":const")]
    eff = X[w] @ b[w]
    # 학습 구간에서 구분별 평균 날씨 효과를 빼서, 평균 날씨면 보정 1.0
    adj = eff.copy()
    for g in GROUPS:
        gmask = X[f"{g}:const"] == 1
        adj[gmask] = eff[gmask] - eff[train & gmask].mean()
    return np.exp(adj[test].clip(-1.5, 1.5))


def summarize(name, m, pred):
    c = staff_cost(pred, m.total, m.planned_closed)
    pe = np.where(m.planned_closed == 1, 0, pred)
    return {"방식": name, "총 비용 소수(원)": round(float(c.sum())),
            "WAPE(%)": round(float(np.abs(m.total - pe).sum() / m.total.sum() * 100), 1),
            "적중률(%)": hit_rate(m.assign(p=pred), "p")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weather", required=True)
    args = ap.parse_args()

    tr = load_train()
    w = pd.read_parquet(args.weather)
    e = pd.read_csv(OUTPUT_DIR / "pred_ensemble.csv", parse_dates=["origin", "date"])[["origin", "site", "date", "pred"]]
    m = e.merge(tr, on=["site", "date"]).merge(w[["site", "date", "t2m_max", "precip_mm"]], on=["site", "date"])
    m = m[m.actual_closed == 0].reset_index(drop=True)
    print(f"평가 행: {len(m)} (실제 휴관 제외)")

    X = features(m)
    ok = (m.planned_closed == 0) & (m.total > 0) & (m.pred > 0)
    y = pd.Series(np.where(ok, np.log(m.total.clip(lower=1) / m.pred.clip(lower=1)), np.nan), index=m.index)

    origins = sorted(m.origin.unique())
    loo = m.pred.copy()
    exp_ = m.pred.copy()
    for o in origins:
        test = m.origin == o
        tr_loo = ok & ~test
        loo[test] = m.pred[test] * fit_apply(X, y, tr_loo, test)
        tr_exp = ok & (m.origin < o)
        if tr_exp.sum() > 500:
            exp_[test] = m.pred[test] * fit_apply(X, y, tr_exp, test)

    rows = [summarize("앙상블 (최종, 날씨 없음)", m, m.pred),
            summarize("+ 날씨 (완벽한 예보 가정, 다른 달로 학습)", m, loo),
            summarize("+ 날씨 (완벽한 예보 가정, 앞선 달로만 학습)", m, exp_)]
    t = pd.DataFrame(rows)
    t["앙상블 대비 절감(원)"] = t["총 비용 소수(원)"].iloc[0] - t["총 비용 소수(원)"]

    # 전체 기간으로 한 번 학습한 계수 (해석용)
    beta, *_ = np.linalg.lstsq(X[ok].values, y[ok].values, rcond=None)
    coef = pd.Series(beta, index=X.columns).round(3)

    RESULTS.mkdir(exist_ok=True)
    t.to_csv(RESULTS / "날씨_완벽예보_근사.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 200)
    print(t.to_string(index=False))
    print("\n날씨 계수 (전체로 학습, log 관람객 기준, 해석용)\n" + coef[[c for c in coef.index if not c.endswith('const')]].to_string())
    print(f"\n저장: {RESULTS / '날씨_완벽예보_근사.csv'}")


if __name__ == "__main__":
    main()
