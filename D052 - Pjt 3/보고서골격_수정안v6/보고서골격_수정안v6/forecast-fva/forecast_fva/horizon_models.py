"""예측 길이를 바꿀 수 있는 Chronos-2·Prophet 예측과, 개소별 무료 개방 배율.

요구사항 7(보정 규칙)과 요구사항 8(근무표 확정 시점별 비용)에서 같이 씁니다.
- predict_chronos_h / predict_prophet_h : chronos_model·stat_models 와 같은 설정에 '예측 길이(일)'만 바꿀 수 있게 함
  horizon=None 이면 원점이 속한 달의 말일까지 (기존 월 1회 설정과 같음)
- free_day_multipliers : 원점 전날까지의 기록만으로 개소별 '무료 개방일 배율'을 계산
"""
import numpy as np
import pandas as pd

from .config import QUANTILE
from .fva_ensemble import _prophet_one

# 팀 최종 모형과 같은 입력 (chronos_model.COVS, stat_models.EXOG)
FINAL_CHRONOS_COVS = ["is_holiday", "is_myeongjeol", "is_last_wednesday", "planned_closed"]
FINAL_PROPHET_EXOG = ["is_holiday", "is_myeongjeol", "is_last_wednesday"]


def horizon_end(origin, horizon):
    """예측 기간의 끝(포함하지 않음)."""
    if horizon is None:
        return origin + pd.offsets.MonthBegin(1)
    return origin + pd.Timedelta(days=int(horizon))


# ---------------------------------------------------------------- Chronos-2
def predict_chronos_h(df, pipe, origins, horizon=None, covs=FINAL_CHRONOS_COVS):
    last = df.date.max() + pd.Timedelta(days=1)          # 데이터(달력)가 끝나는 날을 넘지 않게
    out = []
    for origin in origins:
        end = min(horizon_end(origin, horizon), last)
        n_days = (end - origin).days
        if n_days <= 0:
            continue
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
def _prophet_site_h(g, site, exog, origins, horizon):
    rows, n_clip = [], 0
    for origin in origins:
        end = horizon_end(origin, horizon)
        hist = g[g.index < origin]
        tgt = g[(g.index >= origin) & (g.index < end)]
        if tgt.empty or hist.y.notna().sum() < 60:
            continue
        try:
            fc, resid = _prophet_one(hist, tgt, exog)
        except Exception as e:
            print(f"  경고 Prophet {site} {origin.date()}: {e}")
            continue
        q = float(np.quantile(resid, QUANTILE)) if len(resid) >= 10 else 0.0
        pred = np.exp(np.asarray(fc, dtype=float) + q)
        cap = float(np.exp(hist.y.max()) * 2)            # stat_models 와 같은 안전장치
        bad = ~np.isfinite(pred) | (pred > cap)
        n_clip += int(bad.sum())
        rows.append(pd.DataFrame({"origin": origin, "site": site, "date": tgt.index,
                                  "pred": np.where(bad, cap, pred)}))
    return rows, n_clip


def predict_prophet_h(df, origins, horizon=None, exog=FINAL_PROPHET_EXOG, n_jobs=1):
    frames = {}
    for site in sorted(df.site.unique()):
        g = df[df.site == site].sort_values("date").set_index("date")
        g["y"] = np.log(g.total.where((g.actual_closed == 0) & (g.total > 0)))
        frames[site] = g
    if n_jobs == 1:
        res = [_prophet_site_h(g, s, exog, origins, horizon) for s, g in frames.items()]
    else:
        from joblib import Parallel, delayed
        res = Parallel(n_jobs=n_jobs)(delayed(_prophet_site_h)(g, s, exog, origins, horizon)
                                      for s, g in frames.items())
    print(f"  상한으로 제한된 예측값: {sum(n for _, n in res)}개")
    return pd.concat([p for rows, _ in res for p in rows], ignore_index=True)


# ---------------------------------------------------------------- 무료 개방 배율
def free_day_multipliers(df, origin, kind="last_wednesday", window=28, min_cases=3):
    """원점 전날까지의 기록으로 개소별 무료 개방일 배율을 계산합니다.

    배율 = 무료 개방일 관람객 ÷ (같은 개소·같은 요일·±window일 안의 평상시 개방일 평균) 의 중앙값
    평상시 = 실제로 문을 열었고 공휴일·명절·마지막 수요일·예정 휴관이 아닌 날
    kind = "last_wednesday" (마지막 수요일, 공휴일이 아닌 무료 개방) 또는 "myeongjeol" (명절 연휴)
    사례가 min_cases 건 미만인 개소는 같은 구분(궁·종묘·왕릉)의 중앙값을 씁니다.
    """
    h = df[(df.date < origin) & (df.actual_closed == 0) & (df.total > 0)].copy()
    h["dow"] = h.date.dt.weekday
    normal = h[(h.is_holiday == 0) & (h.is_myeongjeol == 0) & (h.is_last_wednesday == 0) & (h.planned_closed == 0)]
    if kind == "last_wednesday":
        free = h[(h.is_last_wednesday == 1) & (h.is_holiday == 0) & (h.is_myeongjeol == 0)]
    else:
        free = h[h.is_myeongjeol == 1]
    m = free[["site", "group", "date", "dow", "total"]].merge(
        normal[["site", "date", "dow", "total"]], on=["site", "dow"], suffixes=("", "_n"))
    m = m[(m.date_n - m.date).abs().dt.days <= window]
    base = m.groupby(["site", "group", "date", "total"]).total_n.agg(["mean", "size"]).reset_index()
    base = base[base["size"] >= 2]
    base["ratio"] = base.total / base["mean"]
    site = base.groupby(["site", "group"]).ratio.agg(["median", "size"]).reset_index()
    grp = base.groupby("group").ratio.median()
    site["mult"] = np.where(site["size"] >= min_cases, site["median"], site.group.map(grp))
    out = site.set_index("site").mult
    # 사례가 아예 없는 개소는 구분 중앙값 → 그것도 없으면 1.0
    allsites = df[["site", "group"]].drop_duplicates().set_index("site").group
    return pd.Series({s: out.get(s, grp.get(g, 1.0)) for s, g in allsites.items()}).fillna(1.0)
