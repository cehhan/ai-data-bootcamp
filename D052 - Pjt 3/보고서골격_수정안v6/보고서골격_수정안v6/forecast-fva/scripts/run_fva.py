"""FVA 표 (요구사항 6) — 최종 모형(앙상블) 기준. 정보를 한 줄씩 더하며 비용을 다시 계산합니다.

    python scripts/run_fva.py                      # 전체 (Prophet 1,100여 번 학습 → Colab 권장)
    python scripts/run_fva.py --reuse              # 이미 만든 예측 파일을 행 3·7 에 재사용 (권장, 시간 절약)
    python scripts/run_fva.py --jobs 4             # Prophet 을 개소 단위로 병렬 실행
    python scripts/run_fva.py --only chronos       # Chronos 만 (GPU 있는 곳에서)
    python scripts/run_fva.py --only prophet       # Prophet 만 (Colab 에서)
    python scripts/run_fva.py --only table         # 저장된 예측으로 표만 다시 만들기

필요한 입력
- output/pred_classic.csv   : 행 1·2 (python scripts/run_classic.py)
- (--reuse) output/pred_chronos.csv, output/pred_prophet.csv : 행 3(Chronos 단변량)·행 7(최종) 재사용

중간 결과는 output/fva/ 에 행마다 저장되므로, 끊겨도 다시 실행하면 이어서 계산합니다.
결과: results/FVA_앙상블.csv, results/FVA_앙상블_원점별.csv
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from forecast_fva.config import OUTPUT_DIR  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402
from forecast_fva.fva_ensemble import (FINAL_ROW, cumulative_inputs, member_cost, per_origin_cost,  # noqa: E402
                                       predict_chronos_covs, predict_prophet_exog, summarize_row)

FVA_DIR = OUTPUT_DIR / "fva"
RESULTS = ROOT / "results"
EXPECTED_FINAL = 865_671_727      # 팀 최종 앙상블 비용 (행 7 검산값)


def _path(model, row):
    return FVA_DIR / f"{model}_row{row}.csv"


def _load(model, row):
    p = _path(model, row)
    return pd.read_csv(p, parse_dates=["origin", "date"]) if p.exists() else None


def _save(df, model, row):
    FVA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(_path(model, row), index=False, encoding="utf-8-sig")


def _reuse(model, row):
    """--reuse: 팀이 이미 만든 예측을 행 3(Chronos 단변량)·행 7(최종 모형)에 씁니다."""
    if model == "chronos" and row in (3, FINAL_ROW):
        f, name = OUTPUT_DIR / "pred_chronos.csv", ("Chronos-2 (단변량)" if row == 3 else "Chronos-2 + 달력")
    elif model == "prophet" and row == FINAL_ROW:
        f, name = OUTPUT_DIR / "pred_prophet.csv", "Prophet"
    else:
        return None
    if not f.exists():
        return None
    d = pd.read_csv(f, parse_dates=["origin", "date"])
    return d[d.model == name][["origin", "site", "date", "pred"]]


def build_predictions(df, which, reuse, jobs):
    plan = cumulative_inputs()
    pipe = None
    prev_prophet_exog, prev_prophet_row = None, None
    for row, cfg in plan.items():
        if which in ("all", "chronos") and _load("chronos", row) is None:
            got = _reuse("chronos", row) if reuse else None
            if got is None:
                if pipe is None:
                    from forecast_fva.chronos_model import load_pipe
                    pipe = load_pipe()
                print(f"[행 {row}] Chronos 공변량: {cfg['chronos'] or '없음'}")
                got = predict_chronos_covs(df, cfg["chronos"], pipe)
            _save(got, "chronos", row)
        if which in ("all", "prophet") and _load("prophet", row) is None:
            got = _reuse("prophet", row) if reuse else None
            if got is None and cfg["prophet"] == prev_prophet_exog and prev_prophet_row is not None:
                got = _load("prophet", prev_prophet_row)          # 외생변수가 같으면 앞 행 결과를 그대로 씀 (행 4)
            if got is None:
                print(f"[행 {row}] Prophet 외생변수: {cfg['prophet'] or '없음'}")
                got = predict_prophet_exog(df, cfg["prophet"], n_jobs=jobs)
            _save(got, "prophet", row)
        prev_prophet_exog, prev_prophet_row = cfg["prophet"], row


def build_table(df):
    classic_path = OUTPUT_DIR / "pred_classic.csv"
    if not classic_path.exists():
        sys.exit("output/pred_classic.csv 가 없습니다. 먼저 python scripts/run_classic.py 를 실행하세요.")
    classic = pd.read_csv(classic_path, parse_dates=["origin", "date"])

    rows, per = [], {}
    for r, (name, label) in enumerate([("직전7일평균", "직전 7일 평균 (운영팀 현재 방식)"),
                                       ("서비스수준보정", "+ 서비스 수준 보정 (0.8)")], start=1):
        p = classic[classic.model == name][["origin", "site", "date", "pred"]]
        rows.append(summarize_row(r, label, p, df))
        per[f"행{r}"] = per_origin_cost(p, df)

    for row, cfg in cumulative_inputs().items():
        c, p = _load("chronos", row), _load("prophet", row)
        if c is None or p is None:
            print(f"  행 {row}: 예측 파일이 아직 없어 표에서 뺍니다 ({_path('chronos', row).name}, {_path('prophet', row).name})")
            continue
        m = c.merge(p, on=["origin", "site", "date"], suffixes=("_c", "_p"))
        ens = m.assign(pred=(m.pred_c + m.pred_p) / 2)[["origin", "site", "date", "pred"]]
        rows.append(summarize_row(row, cfg["label"], ens, df, member_cost(c, df), member_cost(p, df)))
        per[f"행{row}"] = per_origin_cost(ens, df)

    t = pd.DataFrame(rows)
    t["앞 행 대비 절감(원)"] = t["총 비용(원)"].shift(1) - t["총 비용(원)"]
    t["행 1 대비 절감(원)"] = t["총 비용(원)"].iloc[0] - t["총 비용(원)"]
    RESULTS.mkdir(exist_ok=True)
    t.to_csv(RESULTS / "FVA_앙상블.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(per).round(0).to_csv(RESULTS / "FVA_앙상블_원점별.csv", encoding="utf-8-sig")

    pd.set_option("display.width", 220)
    print(t.drop(columns=["평가 행 수"]).to_string(index=False))
    if (t["평가 행 수"].nunique() != 1):
        print("  경고: 행마다 평가 행 수가 다릅니다. 같은 날을 비교하고 있는지 확인하세요.")
    fin = t[t["행"] == FINAL_ROW]
    if len(fin):
        diff = int(fin["총 비용(원)"].iloc[0]) - EXPECTED_FINAL
        print(f"\n검산: 행 {FINAL_ROW} = {int(fin['총 비용(원)'].iloc[0]):,}원 "
              f"(팀 최종 앙상블 {EXPECTED_FINAL:,}원, 차이 {diff:+,}원)")
    print(f"저장: {RESULTS / 'FVA_앙상블.csv'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["all", "chronos", "prophet", "table"], default="all")
    ap.add_argument("--reuse", action="store_true", help="기존 pred_chronos.csv·pred_prophet.csv 재사용")
    ap.add_argument("--jobs", type=int, default=1, help="Prophet 병렬 작업 수")
    args = ap.parse_args()
    df = load_train()
    if args.only != "table":
        build_predictions(df, args.only, args.reuse, args.jobs)
    build_table(df)


if __name__ == "__main__":
    main()
