---
name: run-pipeline
description: 데이터 파일과 00_context.md를 받아 7단계 분석 파이프라인을 순서대로 실행하고 대시보드와 임원 보고서를 만든다. 체크포인트가 있어 완료된 단계는 건너뛴다.
argument-hint: (없음 — runs/latest/input/에 데이터와 00_context.md가 있어야 한다)
---

# /run-pipeline

## 실행 전 체크 — 셋 다 통과해야 시작한다

### 1. 실행 폴더 준비

작업 폴더는 **항상 `runs/latest/`** 다. 데이터와 컨텍스트는 여기에 넣는다.
경로를 하나만 기억하게 하려는 의도다.

먼저 사용자의 의도를 구분한다.

- 보통의 `/run-pipeline` 요청: 기존 `.run_id`가 있으면 **재개**한다.
- "처음부터 다시", "새 실행"처럼 명시한 요청: 기존 결과를 보관하고 **새로 시작**한다.
- `.run_id`가 없는 첫 실행: 새로 시작한다. 결과 파일이 이미 있으면 먼저 보관한다.

재개할 때는 기존 산출물과 `.run_id`를 그대로 둔다. 새로 시작할 때만 아래 순서로
이전 결과를 보관하고 `.run_id`를 만든다.

```bash
RUN="runs/latest"
mkdir -p "$RUN/outputs" "$RUN/queries"
```

위 두 줄은 재개와 새 실행 모두에서 실행한다. 다음 블록은 **새 실행일 때만** 실행한다.

```bash

# 새 실행이고 이전 결과가 있으면 타임스탬프 폴더로 보관한다 (input은 복사한다)
if find "$RUN/outputs" "$RUN/queries" -type f ! -name '.gitkeep' -print -quit 2>/dev/null | grep -q .; then
  ARCHIVE="runs/$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$ARCHIVE"
  cp -R "$RUN/input" "$ARCHIVE/" 2>/dev/null || true
  mv "$RUN/outputs" "$ARCHIVE/"
  mv "$RUN/queries" "$ARCHIVE/" 2>/dev/null || true
  mkdir -p "$RUN/outputs" "$RUN/queries"
  touch "$RUN/outputs/.gitkeep" "$RUN/queries/.gitkeep"
  echo "이전 실행을 $ARCHIVE에 보관했습니다"
fi

date +%s > "$RUN/.run_id"
```

보관된 폴더는 지우지 않는다. 두 실행을 나란히 비교하는 것이
같은 킷에 데이터만 갈아 끼웠을 때 무엇이 달라지는지 보는 유일한 방법이다.

**재개 요청에서는 위 보관 코드와 `.run_id` 갱신을 실행하지 않는다.** 출력 폴더만
확인한 뒤 체크포인트 판정으로 이동한다.

### 2. 데이터 파일 확인

`$RUN/input/`에 데이터 파일(CSV·TSV·XLSX·JSON)이 있는지 확인한다.
없으면 아래를 출력하고 **즉시 중단**한다.

> `runs/latest/input/`에 데이터 파일을 넣어 주세요. (CSV, TSV, Excel, JSON)

### 3. `00_context.md` 확인 — 이게 이 킷의 차이다

`$RUN/input/00_context.md`가 있는지 확인한다. 없으면 **즉시 중단**한다.

> ⛔ `00_context.md`가 없습니다.
>
> 데이터만으로는 "무엇을 해결해야 하는가" 를 알 수 없습니다.
> 데이터에서 문제를 역산하면 그럴싸하지만 아무 결정과도 무관한 분석이 나옵니다.
>
> `runs/latest/input/00_context.md.template`을 복사해 `00_context.md`로 만들고
> 다섯 항목을 채워 주세요. 15줄이면 충분합니다.

파일이 있으면 **"어떤 결정을 앞두고 있는가"** 항목이 비어 있지 않은지 확인한다.
비어 있으면 경고하고, 진행할지 사용자에게 묻는다.
(비어 있어도 01·02는 의미가 있다. 03에서 `@problem`이 다시 막는다.)

## 체크포인트

각 단계 실행 **전** 확인한다.
산출물이 **자기 입력 전부보다 새것일 때만** 건너뛴다.

한 단계의 입력은 넷이다. 하나라도 산출물보다 새것이면 그 산출물은 낡았다.

| 입력 | 왜 |
|---|---|
| `runs/latest/input/`의 데이터와 `00_context.md` | 사람이 컨텍스트를 보강했으면 다시 돌려야 한다 |
| **그 단계의 에이전트 파일** (`.claude/agents/*.md`) | 지시문을 고쳤으면 결과가 달라진다 |
| **`.claude/rules/`의 세 파일** | 모든 에이전트에 임포트되므로 전 단계에 영향 |
| **앞 단계의 산출물** | 상류가 바뀌면 하류는 낡은 근거 위에 서 있다 |

```bash
stale() {          # stale <산출물> <에이전트> [앞단계 산출물]
  OUT="$1"; AGENT="$2"; PREV="$3"
  [ -f "$OUT" ] || return 0
  [ "$OUT" -nt "$RUN/.run_id" ] || return 0
  [ "$OUT" -nt "$AGENT" ] || return 0
  for r in .claude/rules/*.md; do [ "$OUT" -nt "$r" ] || return 0; done
  for i in "$RUN"/input/*; do [ "$OUT" -nt "$i" ] || return 0; done
  [ -z "$PREV" ] || [ "$OUT" -nt "$PREV" ] || return 0
  return 1
}

O1="$RUN/outputs/01_dataset_profile.md"
if stale "$O1" .claude/agents/data-ingestion.md; then
  # 에이전트 실행
else
  echo "✅ STEP 1 — 완료 (skip)"
fi

O2="$RUN/outputs/02_eda_report.md"
if stale "$O2" .claude/agents/eda.md "$O1"; then …
```

건너뛸 때는 **왜 건너뛰는지**가 아니라 건너뛴다는 것만 적는다.
다시 돌릴 때는 **무엇이 새것이어서 다시 도는지** 한 줄 적는다.

```
🔄 STEP 2 — 재실행 (.claude/agents/eda.md가 산출물보다 새것)
```

이 한 줄이 없으면 사용자는 "왜 또 도는가" 를 알 수 없다.

**에이전트를 고쳤는데 건너뛴다면 체크포인트가 잘못된 것이다.**
D2에서 학습자가 에이전트를 고치고 다시 돌리는 것이 실습의 핵심이므로,
이 판정이 틀리면 실습이 성립하지 않는다.

**전체 재실행:** 사용자가 "처음부터 다시"라고 하면 기존 입력·산출물·계산
스크립트를 타임스탬프 폴더에 보관하고, 빈 `outputs/`·`queries/`와 새 `.run_id`를
만든 뒤 STEP 1부터 실행한다. 기존 결과를 삭제하거나 덮어쓰지 않는다.

## 실행 순서

병렬 실행 금지. 반드시 순서대로.

```
STEP 1 → @data-ingestion   01_dataset_profile.md
STEP 2 → @eda              02_eda_report.md
STEP 3 → @problem          03_problem_definition.md
STEP 4 → @metrics          04_kpi_summary.md   (+ queries/04_*.py|.out)
STEP 5 → @analysis         05_analysis_report.md (+ queries/05_*.py|.out)
STEP 6 → @dashboard        06_dashboard.html
STEP 7 → @report           07_executive_report.md
```

각 단계 후 산출물 파일 존재를 확인한다. 없으면 그 단계 실패로 보고 **중단**한다.
다음 단계로 넘어가지 않는다 — 없는 입력으로 만든 산출물이 더 나쁘다.

**STEP 3이 스스로 중단할 수 있다.** `@problem`이 "앞둔 결정 확인 안 됨" 으로
멈추면 그것은 실패가 아니다. 사용자에게 `00_context.md`를 채우도록 안내하고
파이프라인을 여기서 정상 종료한다.

## 완료 후

`queries/`에 스크립트가 하나도 없으면 경고한다.

> ⚠ `queries/`가 비어 있습니다. 문서의 수치를 재현할 수 없습니다.
> `/audit-analysis`가 검증할 대상이 없습니다.

## 완료 메시지

```
✅ 파이프라인 완료 — runs/latest

📄 outputs/01_dataset_profile.md   (cached)
📄 outputs/02_eda_report.md        (cached)
📄 outputs/03_problem_definition.md
📄 outputs/04_kpi_summary.md
📄 outputs/05_analysis_report.md
🌐 outputs/06_dashboard.html
📄 outputs/07_executive_report.md

🧮 queries/ 스크립트 N개

다음: /audit-analysis로 수치를 재계산해 대조하세요.
```
