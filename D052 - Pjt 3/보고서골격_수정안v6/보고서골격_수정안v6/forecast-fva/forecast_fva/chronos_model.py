"""Chronos-2 (사전학습 모형, 학습 없이 예측 = 제로샷).

두 가지 버전
- Chronos-2 (단변량): 과거 관람객 기록만 입력
- Chronos-2 + 달력: 예측 기간의 공휴일·명절·마지막 수요일·예정 휴관을 공변량으로 함께 입력

예측값은 모델의 0.8 분위수 열을 그대로 씁니다.
휴관일은 target 을 결측으로 두고, 날짜는 빠짐없이 넣습니다(freq="D").
첫 실행 때 모델(약 480MB)을 내려받습니다.
"""
import pandas as pd

from .config import ORIGINS

COVS = ["is_holiday", "is_myeongjeol", "is_last_wednesday", "planned_closed"]
MODEL_NAMES = {False: "Chronos-2 (단변량)", True: "Chronos-2 + 달력"}


def load_pipe():
    from chronos import Chronos2Pipeline
    return Chronos2Pipeline.from_pretrained("amazon/chronos-2", device_map="cpu")


def predict_chronos(df, pipe=None, origins=ORIGINS):
    pipe = pipe or load_pipe()
    out = []
    for use_cov in [False, True]:
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
            if use_cov:
                for c in COVS:
                    ctx[c] = hist[c].values
                src = df[(df.date >= origin) & (df.date < end)].sort_values(["site", "date"])
                fut = pd.DataFrame({"item_id": src.site.values, "timestamp": src.date.values})
                for c in COVS:
                    fut[c] = src[c].values
            pred = pipe.predict_df(ctx, future_df=fut, id_column="item_id", timestamp_column="timestamp",
                                   target="target", prediction_length=n_days,
                                   quantile_levels=[0.8], freq="D")
            out.append(pd.DataFrame({"model": MODEL_NAMES[use_cov], "origin": origin,
                                     "site": pred.item_id.values,
                                     "date": pd.to_datetime(pred.timestamp.values),
                                     "pred": pred["0.8"].values}))
    return pd.concat(out, ignore_index=True)
