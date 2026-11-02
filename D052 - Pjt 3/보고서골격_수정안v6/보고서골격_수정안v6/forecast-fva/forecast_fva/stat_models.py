"""통계·시계열 모형: ETS(지수평활), ARIMA, SARIMA(외생변수 포함), Prophet.

공통 규칙
- 학습: 원점 전날까지, 실제로 문 연 날의 로그 관람객 (휴관일은 결측으로 두고 모형이 건너뜀)
- 예측: 원점 ~ 그달 말. 외생변수는 미리 아는 달력 정보만 사용
- 분위수: 학습 잔차의 0.8 분위수를 더해 "모자라지 않을 수준"으로 올림
- 안전장치: 개소 과거 최대 개방일 관람객의 2배를 넘거나 무한대인 값은 상한으로 제한 (모든 모형 동일)
"""
import warnings

import numpy as np
import pandas as pd

from .config import ORIGINS, QUANTILE

warnings.filterwarnings("ignore")

# planned_closed 는 목표가 결측인 날과 겹쳐 계수가 불안정하므로 뺐습니다 (예정 휴관은 비용 식에서 0명 처리)
EXOG = ["is_holiday", "is_myeongjeol", "is_last_wednesday"]


def _site_frame(df, site):
    g = df[df.site == site].sort_values("date").set_index("date")
    g["y"] = np.log(g.total.where((g.actual_closed == 0) & (g.total > 0)))
    return g


def _ets(hist, tgt):
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    y = hist.y.interpolate(limit_direction="both")
    m = ExponentialSmoothing(y, trend=None, seasonal="add", seasonal_periods=7).fit()
    resid = (hist.y - m.fittedvalues).dropna().values
    return m.forecast(len(tgt)).values, resid


def _arima(hist, tgt):
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    m = SARIMAX(hist.y, order=(1, 1, 1), enforce_stationarity=False,
                enforce_invertibility=False).fit(disp=False)
    return m.get_forecast(len(tgt)).predicted_mean.values, m.resid[hist.y.notna().values]


def _sarima(hist, tgt):
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    m = SARIMAX(hist.y, exog=hist[EXOG].astype(float), order=(1, 0, 0), seasonal_order=(1, 0, 0, 7),
                enforce_stationarity=False, enforce_invertibility=False).fit(disp=False, maxiter=100)
    fc = m.get_forecast(len(tgt), exog=tgt[EXOG].astype(float)).predicted_mean.values
    return fc, m.resid[hist.y.notna().values]


def _prophet(hist, tgt):
    from prophet import Prophet
    op = hist[hist.y.notna()].reset_index().rename(columns={"date": "ds"})
    p = Prophet(weekly_seasonality=True, yearly_seasonality=True, daily_seasonality=False)
    for c in EXOG:
        p.add_regressor(c)
    p.fit(op[["ds", "y"] + EXOG])
    fut = tgt.reset_index().rename(columns={"date": "ds"})[["ds"] + EXOG]
    fc = p.predict(fut)["yhat"].values
    insample = p.predict(op[["ds"] + EXOG])["yhat"].values
    return fc, op.y.values - insample


MODELS = {"ETS": _ets, "ARIMA": _arima, "SARIMA": _sarima, "Prophet": _prophet}


def predict_stat(df, models=None, origins=ORIGINS):
    """긴 표: 모형 이름, 원점, 개소, 날짜, 예측값."""
    models = models or list(MODELS)
    out, n_clip = [], 0
    for site in sorted(df.site.unique()):
        g = _site_frame(df, site)
        for origin in origins:
            end = origin + pd.offsets.MonthBegin(1)
            hist = g[g.index < origin]
            tgt = g[(g.index >= origin) & (g.index < end)]
            if tgt.empty or hist.y.notna().sum() < 60:
                continue
            for name in models:
                try:
                    fc, resid = MODELS[name](hist, tgt)
                except Exception as e:                     # 수렴 실패 등: 해당 조합만 건너뜀
                    print(f"  경고 {name} {site} {origin.date()}: {e}")
                    continue
                q = float(np.quantile(resid, QUANTILE)) if len(resid) >= 10 else 0.0
                pred = np.exp(np.asarray(fc, dtype=float) + q)
                cap = float(np.exp(hist.y.max()) * 2)
                bad = ~np.isfinite(pred) | (pred > cap)
                n_clip += int(bad.sum())
                pred = np.where(bad, cap, pred)
                out.append(pd.DataFrame({"model": name, "origin": origin, "site": site,
                                         "date": tgt.index, "pred": pred}))
    print(f"  상한으로 제한된 예측값: {n_clip}개")
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
