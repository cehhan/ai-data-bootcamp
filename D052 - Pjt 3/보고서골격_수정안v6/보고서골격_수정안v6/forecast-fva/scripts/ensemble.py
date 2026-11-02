"""앙상블 예측 만들기: Chronos-2 + 달력 과 Prophet 예측을 50:50 으로 평균하고 평가합니다.

    python scripts/ensemble.py

필요한 입력 (먼저 만들어 두세요)
- output/pred_chronos.csv  : python scripts/run_chronos.py 의 결과
- output/pred_prophet.csv  : python scripts/run_stat.py --prophet 의 결과 중 Prophet 만 (Colab 에서 실행하는 것을 권장)

결과
- output/pred_ensemble.csv : 앙상블 예측 (모형 이름: 앙상블(Chronos+Prophet))
- 화면: 총 비용, WAPE, 적중률 (2025년 원점 12개, 실제 휴관 제외)

두 예측을 같은 비율(50:50)로 평균합니다. 비율은 결과를 보고 바꾸지 않았습니다.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from forecast_fva.config import OUTPUT_DIR  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402
from forecast_fva.evaluation import evaluate, hit_rate  # noqa: E402

ENSEMBLE_NAME = "앙상블(Chronos+Prophet)"


def load_members():
    chronos_path = OUTPUT_DIR / "pred_chronos.csv"
    prophet_path = OUTPUT_DIR / "pred_prophet.csv"
    for p in (chronos_path, prophet_path):
        if not p.exists():
            sys.exit(f"입력 파일이 없습니다: {p.name}. 안내의 실행 순서를 먼저 따르세요.")

    chronos = pd.read_csv(chronos_path, parse_dates=["origin", "date"])
    chronos = chronos[chronos.model == "Chronos-2 + 달력"][["origin", "site", "date", "pred"]]
    prophet = pd.read_csv(prophet_path, parse_dates=["origin", "date"])
    prophet = prophet[prophet.model == "Prophet"][["origin", "site", "date", "pred"]]
    return chronos.rename(columns={"pred": "c"}), prophet.rename(columns={"pred": "p"})


def main():
    chronos, prophet = load_members()
    m = chronos.merge(prophet, on=["origin", "site", "date"], how="inner")
    if len(m) == 0:
        sys.exit("두 예측이 겹치는 행이 없습니다. 같은 원점(2025년)으로 만든 파일인지 확인하세요.")

    ens = m.assign(pred=(m.c + m.p) / 2)[["origin", "site", "date", "pred"]]
    ens.insert(0, "model", ENSEMBLE_NAME)
    OUTPUT_DIR.mkdir(exist_ok=True)
    ens.to_csv(OUTPUT_DIR / "pred_ensemble.csv", index=False, encoding="utf-8-sig")

    summary, _ = evaluate(ens, load_train())
    data = load_train()
    ev = ens.merge(data[["site", "date", "total", "actual_closed", "planned_closed"]], on=["site", "date"])
    ev = ev[ev.actual_closed == 0].copy()
    hit = hit_rate(ev, "pred")

    row = summary.iloc[0]
    print(f"모형: {ENSEMBLE_NAME}")
    print(f"총 비용(소수 인원 기준): {int(row.total_cost):,}원")
    print(f"WAPE: {row.wape}%")
    print(f"적중률 (전체): {hit}%")
    print(f"원점 수: {int(row.origins)}, 행 수: {len(ens):,}")
    print(f"\n저장: {OUTPUT_DIR / 'pred_ensemble.csv'}")


if __name__ == "__main__":
    main()
