"""FVA 표 (요구사항 6): 최종 모형(앙상블 = Chronos-2 + Prophet 50:50) 기준.

정보를 한 줄씩 더하면서 같은 원점·같은 평가 규칙으로 비용을 다시 계산합니다.
행 1·2 는 운영팀 기준선(직전 7일 평균, 서비스 수준 보정)이고, 행 3 부터 앙상블입니다.

| 행 | 더한 정보                          | Chronos 공변량 추가                         | Prophet 외생변수 추가        |
|----|------------------------------------|---------------------------------------------|------------------------------|
| 3  | 과거 관람객만                       | (없음, 단변량)                              | (없음, 주간·연간 계절성만)   |
| 4  | + 예정 휴관 (②)                    | planned_closed                              | (없음 ※)                     |
| 5  | + 공휴일                           | is_holiday                                  | is_holiday                   |
| 6  | + 명절 연휴 (①)                    | is_myeongjeol                               | is_myeongjeol                |
| 7  | + 마지막 수요일 (①) = 최종 앙상블  | is_last_wednesday                           | is_last_wednesday            |
| 8  | + 휴관 이동·이웃 궁 휴관 (②③, 추가 실험) | closure_shifted, closed_wd_holiday, neighbor_closed_n | closed_wd_holiday, neighbor_closed_n |

※ Prophet 은 문을 연 날만 학습하므로(휴관일은 결측) 예정 휴관 정보가 이미 반영되어 있습니다.
  그래서 행 4 의 Prophet 예측은 행 3 과 같고, 행 4 의 변화는 Chronos 에서만 나옵니다.
  closure_shifted 는 그날 대부분 휴관(학습 결측)이라 Prophet 에는 넣지 않습니다.

행 7 은 팀의 최종 앙상블과 같은 설정이라, 비용이 865,671,727원(소수 인원 기준)(Chronos 계산 차이로 몇 원 오차 가능)이
나와야 합니다. 이 값이 맞으면 FVA 표가 최종 모형과 같은 조건으로 계산되었다는 검산이 됩니다.

모든 입력은 미리 아는 달력·휴관 정보이며, 원점 전날까지의 관람객만 씁니다.
"""
import logging
import warnings

import numpy as np
import pandas as pd

from .config import ORIGINS, QUANTILE
from .evaluation import staff_cost, hit_rate

warnings.filterwarnings("ignore")
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
logging.getLogger("prophet").setLevel(logging.WARNING)

# 팀 최종 모형의 공변량 순서 (chronos_model.COVS, stat_models.EXOG 와 같은 순서 → 행 7 재현용)
CHRONOS_ORDER = ["is_holiday", "is_myeongjeol", "is_last_wednesday", "planned_closed",
                 "closure_shifted", "closed_wd_holiday", "neighbor_closed_n"]
PROPHET_ORDER = ["is_holiday", "is_myeongjeol", "is_last_wednesday",
                 "closed_wd_holiday", "neighbor_closed_n"]

STEPS = [
    # (행, 더한 정보, Chronos 에 새로 더할 공변량, Prophet 에 새로 더할 외생변수)
    (3, "과거 관람객만", [], []),
    (4, "+ 예정 휴관 (②)", ["planned_closed"], []),
    (5, "+ 공휴일", ["is_holiday"], ["is_holiday"]),
    (6, "+ 명절 연휴 (①)", ["is_myeongjeol"], ["is_myeongjeol"]),
    (7, "+ 마지막 수요일 (①) = 최종 앙상블", ["is_last_wednesday"], ["is_last_wednesday"]),
    (8, "+ 휴관 이동·이웃 궁 휴관 (②③, 추가 실험)",
     ["closure_shifted", "closed_wd_holiday", "neighbor_closed_n"], ["closed_wd_holiday", "neighbor_closed_n"]),
]
FINAL_ROW = 7


def cumulative_inputs():
    """행마다 누적된 (Chronos 공변량, Prophet 외생변수) 목록을 팀 순서대로 돌려줍니다."""
    c, p, out = [], [], {}
    for row, label, add_c, add_p in STEPS:
        c, p = c + add_c, p + add_p
        out[row] = dict(label=label,
                        chronos=[x for x in CHRONOS_ORDER if x in c],
                        prophet=[x for x in PROPHET_ORDER if x in p])
    return out


# ---------------------------------------------------------------- Chronos-2
def predict_chronos_covs(df, covs, pipe, origins=ORIGINS):
    """chronos_model.predict_chronos 와 같은 방식, 공변량 목록만 바꿀 수 있게 한 버전."""
    out = []
    for origin in origins:
        end = origin + pd.offsets.MonthBegin(1)
        n_days = (end - origin).days
        hist = df[df.date < origin].sort_values(["site", "date"])
        ctx = pd.DataFrame({
            "item_id": hist.site.values,
            "timestamp": hist.date.values,
            "target": hist.total.where((hist.actual_closed == 0) & (hist.total > 0)).values,
        })
        fut = None
        if covs:
            for c in covs:
                ctx[c] = hist[c].values
            src = df[(df.date >= origin) & (df.date < end)].sort_values(["site", "date"])
            fut = pd.DataFrame({"item_id": src.site.values, "timestamp": src.date.values})
            for c in covs:
                fut[c] = src[c].values
        pred = pipe.predict_df(ctx, future_df=fut, id_column="item_id", timestamp_column="timestamp",
                               target="target", prediction_length=n_days,
                               quantile_levels=[QUANTILE], freq="D")
        out.append(pd.DataFrame({"origin": origin, "site": pred.item_id.values,
                                 "date": pd.to_datetime(pred.timestamp.values),
                                 "pred": pred[str(QUANTILE)].values}))
    return pd.concat(out, ignore_index=True)


# ---------------------------------------------------------------- Prophet
def _prophet_one(hist, tgt, exog):
    """stat_models._prophet 와 같은 설정, 외생변수 목록만 바꿀 수 있게 한 버전."""
    from prophet import Prophet
    op = hist[hist.y.notna()].reset_index().rename(columns={"date": "ds"})
    p = Prophet(weekly_seasonality=True, yearly_seasonality=True, daily_seasonality=False)
    for c in exog:
        p.add_regressor(c)
    p.fit(op[["ds", "y"] + exog])
    fut = tgt.reset_index().rename(columns={"date": "ds"})[["ds"] + exog]
    fc = p.predict(fut)["yhat"].values
    insample = p.predict(op[["ds"] + exog])["yhat"].values
    return fc, op.y.values - insample


def _prophet_site(g, site, exog, origins):
    rows, n_clip = [], 0
    for origin in origins:
        end = origin + pd.offsets.MonthBegin(1)
        hist = g[g.index < origin]
        tgt = g[(g.index >= origin) & (g.index < end)]
        if tgt.empty or hist.y.notna().sum() < 60:
            continue
        try:
            fc, resid = _prophet_one(hist, tgt, exog)
        except Exception as e:                       # 수렴 실패 등: 그 조합만 건너뜀 (stat_models 와 같음)
            print(f"  경고 Prophet {site} {origin.date()}: {e}")
            continue
        q = float(np.quantile(resid, QUANTILE)) if len(resid) >= 10 else 0.0
        pred = np.exp(np.asarray(fc, dtype=float) + q)
        cap = float(np.exp(hist.y.max()) * 2)        # 안전장치: stat_models 와 같은 상한
        bad = ~np.isfinite(pred) | (pred > cap)
        n_clip += int(bad.sum())
        rows.append(pd.DataFrame({"origin": origin, "site": site, "date": tgt.index,
                                  "pred": np.where(bad, cap, pred)}))
    return rows, n_clip


def predict_prophet_exog(df, exog, origins=ORIGINS, n_jobs=1):
    frames = {}
    for site in sorted(df.site.unique()):
        g = df[df.site == site].sort_values("date").set_index("date")
        g["y"] = np.log(g.total.where((g.actual_closed == 0) & (g.total > 0)))
        frames[site] = g
    if n_jobs == 1:
        res = [_prophet_site(g, s, exog, origins) for s, g in frames.items()]
    else:
        from joblib import Parallel, delayed
        res = Parallel(n_jobs=n_jobs)(delayed(_prophet_site)(g, s, exog, origins) for s, g in frames.items())
    parts = [p for rows, _ in res for p in rows]
    print(f"  상한으로 제한된 예측값: {sum(n for _, n in res)}개")
    return pd.concat(parts, ignore_index=True)


# ---------------------------------------------------------------- 평가
def _eval_frame(pred, data):
    d = data[["site", "date", "total", "actual_closed", "planned_closed",
              "is_myeongjeol", "is_last_wednesday"]]
    m = pred.merge(d, on=["site", "date"])
    m = m[m.actual_closed == 0].copy()
    m["cost"] = staff_cost(m.pred, m.total, m.planned_closed)
    return m


def summarize_row(row, label, pred, data, chronos_cost=None, prophet_cost=None):
    m = _eval_frame(pred, data)
    pe = np.where(m.planned_closed == 1, 0, np.nan_to_num(m.pred))
    free = (m.is_myeongjeol == 1) | (m.is_last_wednesday == 1)
    return {"행": row, "더한 정보": label,
            "Chronos 비용(원)": chronos_cost, "Prophet 비용(원)": prophet_cost,
            "총 비용(원)": int(round(m.cost.sum())),
            "무료 개방일 비용(원)": int(round(m.cost[free].sum())),
            "WAPE(%)": round(float(np.abs(m.total - pe).sum() / m.total.sum() * 100), 1),
            "적중률(%)": hit_rate(m, "pred"),
            "평가 행 수": len(m)}


def member_cost(pred, data):
    return int(round(_eval_frame(pred, data).cost.sum()))


def per_origin_cost(pred, data):
    return _eval_frame(pred, data).groupby("origin").cost.sum()
