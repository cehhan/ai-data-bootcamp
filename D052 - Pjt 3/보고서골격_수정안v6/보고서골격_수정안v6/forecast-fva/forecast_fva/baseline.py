"""기준(직전 7일 평균)과 서비스 수준 보정, 나이브, 계절 나이브 (FVA 행 1·2 와 참고 기준)."""
import numpy as np
import pandas as pd

from .config import LOOKBACK_WEEKS, ORIGINS, QUANTILE


def base_forecasts(df, origin):
    """원점 전날까지의 기록으로 베이스라인 값을 계산합니다 (행: 원점 달의 날짜 × 개소)."""
    end = origin + pd.offsets.MonthBegin(1)
    out = []
    for site, g in df.groupby("site"):
        g = g.sort_values("date")
        hist = g[(g.date < origin) & (g.actual_closed == 0) & (g.total > 0)].set_index("date").total
        if hist.empty:
            continue
        last_open = hist.iloc[-1]
        last7 = hist[hist.index >= origin - pd.Timedelta(days=7)].mean()
        for d in g[(g.date >= origin) & (g.date < end)].date:
            k = (d - origin).days // 7 + 1
            snaive = np.nan
            for kk in range(k, k + 60):           # 같은 요일 중 원점 전 가장 가까운 개방일
                cand = d - pd.Timedelta(days=7 * kk)
                if cand in hist.index:
                    snaive = hist[cand]
                    break
            out.append(dict(origin=origin, site=site, date=d, naive=last_open,
                            snaive7=snaive, last7=last7))
    return pd.DataFrame(out)


def service_ratio(df, origin, weeks=LOOKBACK_WEEKS):
    """원점 전 N주 동안 (실제 ÷ 그 날 직전 7일 평균)의 0.8 분위수, 개소별."""
    ratios = {}
    for site, g in df.groupby("site"):
        s = g.sort_values("date").set_index("date")
        s = s.loc[s.index < origin]
        open_total = s.total.where((s.actual_closed == 0) & (s.total > 0))
        full = open_total.reindex(pd.date_range(s.index.min(), origin - pd.Timedelta(days=1)))
        m7 = full.shift(1).rolling(7, min_periods=1).mean()
        win = m7.iloc[-weeks * 7:]
        r = (full / m7).reindex(win.index).dropna()
        r = r[np.isfinite(r)]
        ratios[site] = float(r.quantile(QUANTILE)) if len(r) >= 10 else 1.0
    return ratios


def predict_baseline(df):
    """긴 표로 반환: 모형 이름 = 직전7일평균, 서비스수준보정, 나이브, 계절나이브7."""
    rows = []
    for origin in ORIGINS:
        bf = base_forecasts(df, origin)
        if bf.empty:
            continue
        ratio = service_ratio(df, origin)
        bf["서비스수준보정"] = bf.last7 * bf.site.map(ratio)
        bf = bf.rename(columns={"last7": "직전7일평균", "naive": "나이브", "snaive7": "계절나이브7"})
        rows.append(bf[["origin", "site", "date", "직전7일평균", "서비스수준보정", "나이브", "계절나이브7"]])
    wide = pd.concat(rows, ignore_index=True)
    return wide.melt(id_vars=["origin", "site", "date"], var_name="model", value_name="pred")
