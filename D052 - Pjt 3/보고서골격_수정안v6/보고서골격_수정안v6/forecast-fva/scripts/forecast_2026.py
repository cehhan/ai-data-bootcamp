"""2026년 1월 인력 권고표 (앙상블 = Chronos-2 + 달력 과 Prophet 의 평균).

    python scripts/forecast_2026.py                 # Chronos + Prophet (Prophet 은 Colab 에서 권장)
    python scripts/forecast_2026.py --only-chronos  # Chronos 만 (로컬 테스트용, 앙상블 아님)

입력: data/train_2023_2025_core_v2.csv (과거), data/predict_2026_01_core_v2.csv (2026년 달력·휴관)
결과: results/권고표_2026_01.csv (날짜 × 개소 긴 표), results/권고표_2026_01_피벗.csv (개소 × 날짜)

인원 규칙
- 예정 휴관(정기 휴관 요일, 휴관 이동일)은 0명 (팀 결정)
- 그 밖의 날은 예측 관람객 ÷ 2,000명을 올림한 정수, 최소 1명 (최소 1명은 팀 결정, 올림은 구현 선택)
- 계산에 쓴 소수 인원(필요인원_소수)도 함께 적습니다
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from forecast_fva.chronos_model import load_pipe, predict_chronos  # noqa: E402
from forecast_fva.config import CAP  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402
from forecast_fva.stat_models import predict_stat  # noqa: E402

ORIGIN_2026 = [pd.Timestamp("2026-01-01")]
PRED_PATH = ROOT / "data" / "predict_2026_01_core_v2.csv"
RESULTS = ROOT / "results"
WEEKDAY = "월화수목금토일"


def load_all():
    tr = load_train()
    pr = pd.read_csv(PRED_PATH, parse_dates=["date"], encoding="utf-8-sig")
    # 과거(2023~2025)와 2026년 달력을 한 표로 이어 붙입니다. 2026년의 관람객과 휴관 여부는 비어 있습니다.
    return pd.concat([tr, pr], ignore_index=True), pr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-chronos", action="store_true", help="Chronos 만 계산 (앙상블 아님)")
    args = ap.parse_args()

    df, pr = load_all()
    pieces = []

    chronos = predict_chronos(df, load_pipe(), origins=ORIGIN_2026)
    chronos = chronos[chronos.model == "Chronos-2 + 달력"][["origin", "site", "date", "pred"]]
    pieces.append(chronos.assign(model="Chronos"))

    if not args.only_chronos:
        prophet = predict_stat(df, models=["Prophet"], origins=ORIGIN_2026)
        pieces.append(prophet[["origin", "site", "date", "pred"]].assign(model="Prophet"))

    long = pd.concat(pieces, ignore_index=True)
    wide = long.pivot_table(index=["site", "date"], columns="model", values="pred").reset_index()
    members = [c for c in ["Chronos", "Prophet"] if c in wide.columns]
    wide["예측관람객"] = wide[members].mean(axis=1)
    label = "앙상블(Chronos+Prophet 평균)" if len(members) == 2 else f"{members[0]} 단독 (앙상블 아님)"

    info = pr[["site", "date", "group", "planned_closed"]]
    out = wide.merge(info, on=["site", "date"], how="right")
    out["필요인원_소수"] = np.where(out.planned_closed == 1, 0.0, out["예측관람객"] / CAP)
    out["권고인원"] = np.where(out.planned_closed == 1, 0,
                               np.maximum(1, np.ceil(out["필요인원_소수"].fillna(0))).astype(int))
    out["요일"] = out.date.dt.weekday.map(lambda i: WEEKDAY[i])
    out["예정휴관"] = out.planned_closed.map({1: "휴관", 0: ""})

    table = out.rename(columns={"date": "날짜", "site": "개소", "group": "구분"})[
        ["날짜", "요일", "구분", "개소", "예정휴관", "예측관람객", "필요인원_소수", "권고인원"]
    ].sort_values(["날짜", "구분", "개소"])
    table.insert(0, "모형", label)
    table["날짜"] = table["날짜"].dt.strftime("%Y-%m-%d")
    table["예측관람객"] = table["예측관람객"].round(0)
    table["필요인원_소수"] = table["필요인원_소수"].round(2)

    RESULTS.mkdir(exist_ok=True)
    table.to_csv(RESULTS / "권고표_2026_01.csv", index=False, encoding="utf-8-sig")
    pivot = table.pivot(index="개소", columns="날짜", values="권고인원")
    pivot.to_csv(RESULTS / "권고표_2026_01_피벗.csv", encoding="utf-8-sig")

    print(f"모형: {label}")
    print(f"행 수: {len(table)} (23개소 × 31일 = 713 기대)")
    print(f"예정 휴관 날의 권고인원 합(0 이어야 함): {int(table.loc[table.예정휴관 == '휴관', '권고인원'].sum())}")
    print(f"최소 1명 규칙 위반 없음: {bool((table.loc[table.예정휴관 != '휴관', '권고인원'] >= 1).all())}")
    print(f"\n저장: {RESULTS / '권고표_2026_01.csv'}")
    print(f"저장: {RESULTS / '권고표_2026_01_피벗.csv'}")


if __name__ == "__main__":
    main()
