"""요구사항 7: 오차가 큰 날의 분석과 보정 규칙 (최종 모형 = 앙상블 기준).

    python scripts/error_analysis.py
    python scripts/error_analysis.py --raw "../../궁능_관람객_데이터/heritage_visitors_daily.parquet"   # 정황 열 보강(선택)

하는 일
 ① 유형별 표: 날짜 유형(평일·주말 / 공휴일 / 무료 개방일)과 개소 유형(궁·종묘·왕릉)별 비용·WAPE·적중률
 ② 상위 10건: 인력이 가장 많이 모자란 10건(개소 × 날짜)의 실제·예측·모자란 인원과 데이터상 정황
    → '원인' 열은 비워 둡니다. 국가유산청 궁능유적본부 공지 같은 지정 출처로 확인해 한 문장씩 채우세요.
 ③ 보정 규칙 적용 전후 비용 (같은 원점·같은 평가 규칙)
    규칙 A: 공지된 임시 무료 개방일(달력 규칙 밖)에는 예측 × 개소별 무료 개방 배율
    규칙 B: 마지막 수요일 하한 — 예측이 '같은 기간 같은 요일 평상시 예측 × 개소별 배율'보다 낮으면 그 값으로 올림
    배율은 원점 전날까지의 기록으로만 계산합니다(forecast_fva.horizon_models.free_day_multipliers).
 ④ 규칙 B 를 2026년 1월 권고표(1월 28일, 마지막 수요일)에 적용한 결과

입력: output/pred_ensemble.csv, results/권고표_2026_01.csv (④, 없으면 건너뜀)
결과: results/오차_유형별.csv, results/오차_상위10건.csv, results/보정규칙_전후.csv, results/권고표_2026_01_보정B.csv

※ 규칙 A 는 '그 무료 개방이 근무표 확정일(원점 전날) 전에 공지되었다'는 가정이 있어야 성립합니다.
   EVENT_DAYS 의 공지일을 확인해 announced 에 적으세요. 공지일이 원점보다 늦은 날은 규칙을 적용하지 않습니다.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from backtest_cost import cost_parts  # noqa: E402
from forecast_fva.config import CAP, CU, OUTPUT_DIR  # noqa: E402
from forecast_fva.data import load_train  # noqa: E402
from forecast_fva.evaluation import hit_rate, staff_cost  # noqa: E402
from forecast_fva.horizon_models import free_day_multipliers  # noqa: E402

RESULTS = ROOT / "results"
WEEKDAY = "월화수목금토일"

# 달력 규칙(명절 연휴·마지막 수요일) 밖에서 데이터상 무료 개방이 확인된 기간 (경복궁 유료 비중 15% 미만)
# announced: 공지일(YYYY-MM-DD). 확인 전에는 None → 근무표 확정 전에 공지되었다고 '가정'하고 계산하며 경고를 냅니다.
EVENT_DAYS = [
    # 궁능유적본부 공지 「코리아 그랜드 페스티벌 기간(10.29.~11.9.) 무료입장 안내」, 2025-10-16 게시
    # 대상: 4대궁, 종묘 및 조선왕릉, 세종유적 (창덕궁 후원 특별관람 제외, 종묘는 일반관람 전환)
    # 공지일이 10월 원점의 확정일(9/30)보다 늦고 11월 원점의 확정일(10/31)보다 빠르므로,
    # 규칙 A 는 11월 1~9일에만 적용되고 10월 29~31일에는 적용되지 않습니다.
    {"start": "2025-10-29", "end": "2025-11-09", "announced": "2025-10-16",
     "memo": "코리아 그랜드 페스티벌 기간 무료입장 (공지 2025-10-16)"},
]


# ---------------------------------------------------------------- 준비
def load_eval():
    p = OUTPUT_DIR / "pred_ensemble.csv"
    if not p.exists():
        sys.exit("output/pred_ensemble.csv 가 없습니다. 먼저 python scripts/ensemble.py 를 실행하세요.")
    ens = pd.read_csv(p, parse_dates=["origin", "date"])[["origin", "site", "date", "pred"]]
    tr = load_train()
    cols = ["site", "date", "group", "total", "actual_closed", "planned_closed",
            "is_holiday", "is_myeongjeol", "is_last_wednesday"]
    m = ens.merge(tr[cols], on=["site", "date"])
    m = m[m.actual_closed == 0].copy()
    m["date_type"] = np.select([(m.is_myeongjeol == 1) | (m.is_last_wednesday == 1), m.is_holiday == 1],
                               ["무료 개방일", "공휴일"], default="평일·주말")
    return m, tr


def event_dates():
    out = {}
    for e in EVENT_DAYS:
        for d in pd.date_range(e["start"], e["end"]):
            out[d] = e
    return out


def _metrics(g, col="pred"):
    pe = np.where(g.planned_closed == 1, 0, np.nan_to_num(g[col]))
    cost = staff_cost(g[col], g.total, g.planned_closed)
    staff = np.where(g.planned_closed == 1, 0, np.nan_to_num(g[col]) / CAP)
    short = np.maximum(g.total / CAP - staff, 0)
    return {"행 수": len(g), "총 비용(원)": int(round(cost.sum())),
            "모자란 비용(원)": int(round(CU * short.sum())),
            "WAPE(%)": round(float(np.abs(g.total - pe).sum() / g.total.sum() * 100), 1),
            "적중률(%)": hit_rate(g, col)}


# ---------------------------------------------------------------- ① 유형별
def by_type(m):
    rows = [{"구분": "전체", "유형": "전체", **_metrics(m)}]
    for t in ["평일·주말", "공휴일", "무료 개방일"]:
        rows.append({"구분": "날짜 유형", "유형": t, **_metrics(m[m.date_type == t])})
    for t in ["궁", "종묘", "왕릉"]:
        rows.append({"구분": "개소 유형", "유형": t, **_metrics(m[m.group == t])})
    t = pd.DataFrame(rows)
    t["비용 비중(%)"] = (t["총 비용(원)"] / t["총 비용(원)"].iloc[0] * 100).round(1)
    t["행 비중(%)"] = (t["행 수"] / t["행 수"].iloc[0] * 100).round(1)
    return t


# ---------------------------------------------------------------- ② 상위 10건
def paid_share_flags(raw_path):
    """(선택) 원자료로 '경복궁 유료 비중 15% 미만' 날짜를 찾습니다 (가이드의 분석용 무료 개방 정의)."""
    if not raw_path or not Path(raw_path).exists():
        return set()
    v = pd.read_parquet(raw_path)
    g = v[(v.site == "경복궁") & (v.total > 0)]
    return set(pd.to_datetime(g.loc[g.paid / g.total < 0.15, "date"]))


def top_shortages(m, n=10, raw_path=None):
    m = m.copy()
    staff = np.where(m.planned_closed == 1, 0, np.nan_to_num(m.pred) / CAP)
    m["배치 인원(소수)"] = staff
    m["필요 인원"] = m.total / CAP
    m["모자란 인원"] = np.maximum(m["필요 인원"] - staff, 0)
    m["모자란 비용(원)"] = (CU * m["모자란 인원"]).round(0)
    top = m.sort_values("모자란 인원", ascending=False).head(n).copy()

    ev, paid_free = event_dates(), paid_share_flags(raw_path)

    def hint(r):
        if r.date in ev:
            return ev[r.date]["memo"]
        if r.is_myeongjeol == 1:
            return "명절 연휴"
        if r.is_last_wednesday == 1:
            return "마지막 수요일 (무료 개방)"
        if r.is_holiday == 1:
            return "공휴일"
        if r.date in paid_free:
            return "경복궁 유료 비중 15% 미만 → 달력 밖 무료 개방 정황"
        return "특이 정보 없음 (수준 변화·행사 여부 확인)"

    top["데이터 정황"] = top.apply(hint, axis=1)
    top["원점부터 일수"] = (top.date - top.origin).dt.days + 1
    top["요일"] = top.date.dt.weekday.map(lambda i: WEEKDAY[i])
    top.insert(0, "순위", range(1, len(top) + 1))
    top["원인 (지정 출처로 확인해 한 문장)"] = ""
    out = top.rename(columns={"origin": "원점", "date": "날짜", "site": "개소", "group": "구분",
                              "total": "실제 관람객", "pred": "예측 관람객"})
    out["예측 관람객"] = out["예측 관람객"].round(0)
    for c in ["배치 인원(소수)", "필요 인원", "모자란 인원"]:
        out[c] = out[c].round(2)
    cols = ["순위", "원점", "날짜", "요일", "개소", "구분", "원점부터 일수", "실제 관람객", "예측 관람객",
            "배치 인원(소수)", "필요 인원", "모자란 인원", "모자란 비용(원)", "데이터 정황",
            "원인 (지정 출처로 확인해 한 문장)"]
    out["원점"] = out["원점"].dt.strftime("%Y-%m-%d")
    out["날짜"] = out["날짜"].dt.strftime("%Y-%m-%d")
    return out[cols]


# ---------------------------------------------------------------- ③ 보정 규칙
def _normal_mask(g):
    return (g.is_holiday == 0) & (g.is_myeongjeol == 0) & (g.is_last_wednesday == 0) & (g.planned_closed == 0)


def apply_rules(m_all, tr, use_a=True, use_b=True):
    """m_all: 예측 기간 전체(실제 휴관 포함) 행. 반환: pred_adj 열을 더한 표와 규칙이 바뀐 행 표시."""
    m = m_all.copy()
    m["pred_adj"] = m.pred
    m["rule_a"] = False
    m["rule_b"] = False
    ev = event_dates()
    for origin, g in m.groupby("origin"):
        mult = free_day_multipliers(tr, origin, kind="last_wednesday")
        idx = g.index
        if use_a:
            def allowed(d):
                e = ev.get(d)
                return e is not None and (e["announced"] is None or pd.Timestamp(e["announced"]) < origin)
            a = g.date.map(allowed) & (g.planned_closed == 0) & (g.is_last_wednesday == 0) & (g.is_myeongjeol == 0)
            ia = idx[a.values]
            m.loc[ia, "pred_adj"] = m.loc[ia, "pred"] * m.loc[ia, "site"].map(mult).clip(lower=1.0)
            m.loc[ia, "rule_a"] = True
        if use_b:
            g2 = m.loc[idx]
            g2 = g2.assign(dow=g2.date.dt.weekday)
            base = g2[_normal_mask(g2)].groupby(["site", "dow"]).pred.mean()
            lw = g2[(g2.is_last_wednesday == 1) & (g2.is_holiday == 0) & (g2.planned_closed == 0)]
            for i, r in lw.iterrows():
                b = base.get((r.site, r.dow))
                if b is None or not np.isfinite(b):
                    continue
                floor = b * max(1.0, float(mult.get(r.site, 1.0)))
                if m.at[i, "pred_adj"] < floor:
                    m.at[i, "pred_adj"] = floor
                    m.at[i, "rule_b"] = True
    return m


def compare_rules(tr):
    ens = pd.read_csv(OUTPUT_DIR / "pred_ensemble.csv", parse_dates=["origin", "date"])[["origin", "site", "date", "pred"]]
    cols = ["site", "date", "group", "total", "actual_closed", "planned_closed",
            "is_holiday", "is_myeongjeol", "is_last_wednesday"]
    full = ens.merge(tr[cols], on=["site", "date"])
    rows = []
    for name, a, b in [("보정 전 (앙상블)", False, False), ("규칙 A: 공지된 임시 무료 개방일 × 배율", True, False),
                       ("규칙 B: 마지막 수요일 하한", False, True), ("규칙 A + B", True, True)]:
        adj = apply_rules(full, tr, a, b) if (a or b) else full.assign(pred_adj=full.pred, rule_a=False, rule_b=False)
        ev = adj[adj.actual_closed == 0].copy()
        changed = ev.rule_a | ev.rule_b
        frac = cost_parts(ev.assign(pred=ev.pred_adj), "소수")
        rule = cost_parts(ev.assign(pred=ev.pred_adj), "권고 규칙")
        before_chg = staff_cost(ev.pred[changed], ev.total[changed], ev.planned_closed[changed]).sum()
        after_chg = staff_cost(ev.pred_adj[changed], ev.total[changed], ev.planned_closed[changed]).sum()
        rows.append({"규칙": name, "총 비용 소수(원)": frac["총 비용(원)"], "총 비용 권고 규칙(원)": rule["총 비용(원)"],
                     "바뀐 행 수": int(changed.sum()),
                     "바뀐 행의 비용 전(원)": int(round(before_chg)), "바뀐 행의 비용 후(원)": int(round(after_chg)),
                     "적중률(%)": hit_rate(ev.assign(p=ev.pred_adj), "p")})
    t = pd.DataFrame(rows)
    t["보정 전 대비 절감 소수(원)"] = t["총 비용 소수(원)"].iloc[0] - t["총 비용 소수(원)"]
    return t


# ---------------------------------------------------------------- ④ 2026년 1월
def rule_b_2026(tr):
    p = RESULTS / "권고표_2026_01.csv"
    if not p.exists():
        return None
    rec = pd.read_csv(p, parse_dates=["날짜"])
    cal = pd.read_csv(ROOT / "data" / "predict_2026_01_core_v2.csv", parse_dates=["date"], encoding="utf-8-sig")
    m = rec.rename(columns={"날짜": "date", "개소": "site", "예측관람객": "pred"})[["date", "site", "pred"]].merge(
        cal[["site", "date", "group", "planned_closed", "is_holiday", "is_myeongjeol", "is_last_wednesday"]],
        on=["site", "date"])
    m["origin"] = pd.Timestamp("2026-01-01")
    m["total"] = np.nan
    m["actual_closed"] = 0
    adj = apply_rules(m, tr, use_a=False, use_b=True)
    lw = adj[adj.is_last_wednesday == 1].copy()
    lw["전 인원(권고 규칙)"] = np.where(lw.planned_closed == 1, 0, np.maximum(1, np.ceil(lw.pred / CAP))).astype(int)
    lw["후 인원(권고 규칙)"] = np.where(lw.planned_closed == 1, 0, np.maximum(1, np.ceil(lw.pred_adj / CAP))).astype(int)
    out = lw.rename(columns={"date": "날짜", "site": "개소", "group": "구분", "pred": "보정 전 예측", "pred_adj": "보정 후 예측"})
    out["보정 전 예측"] = out["보정 전 예측"].round(0)
    out["보정 후 예측"] = out["보정 후 예측"].round(0)
    out["바뀜"] = out.rule_b.map({True: "예", False: ""})
    out["날짜"] = out["날짜"].dt.strftime("%Y-%m-%d")
    return out[["날짜", "개소", "구분", "보정 전 예측", "보정 후 예측", "전 인원(권고 규칙)", "후 인원(권고 규칙)", "바뀜"]] \
        .sort_values(["바뀜", "구분", "개소"], ascending=[False, True, True])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=None, help="(선택) heritage_visitors_daily.parquet 경로. 상위 10건 정황 보강")
    args = ap.parse_args()
    pd.set_option("display.width", 240)
    RESULTS.mkdir(exist_ok=True)

    m, tr = load_eval()

    t1 = by_type(m)
    t1.to_csv(RESULTS / "오차_유형별.csv", index=False, encoding="utf-8-sig")
    print("① 유형별 (앙상블, 실제 휴관 제외)\n" + t1.to_string(index=False))

    t2 = top_shortages(m, 10, args.raw)
    t2.to_csv(RESULTS / "오차_상위10건.csv", index=False, encoding="utf-8-sig")
    print("\n② 인력이 가장 많이 모자란 10건\n" + t2.drop(columns=["원인 (지정 출처로 확인해 한 문장)"]).to_string(index=False))

    if any(e["announced"] is None for e in EVENT_DAYS):
        print("\n  경고: EVENT_DAYS 의 공지일(announced)이 비어 있어, 규칙 A 는 '근무표 확정 전에 공지되었다'는 가정으로 계산합니다.")
    t3 = compare_rules(tr)
    t3.to_csv(RESULTS / "보정규칙_전후.csv", index=False, encoding="utf-8-sig")
    print("\n③ 보정 규칙 적용 전후\n" + t3.to_string(index=False))

    t4 = rule_b_2026(tr)
    if t4 is not None:
        t4.to_csv(RESULTS / "권고표_2026_01_보정B.csv", index=False, encoding="utf-8-sig")
        print("\n④ 규칙 B 를 2026-01-28 권고에 적용 (바뀐 개소)\n" + t4[t4["바뀜"] == "예"].to_string(index=False))
    print(f"\n저장: {RESULTS}")


if __name__ == "__main__":
    main()
