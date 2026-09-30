# 구체 패턴 — HTML · CSS · SVG

**색상 값은 이 파일에 없다.** `.claude/rules/design-system.md` 를 Read 로 읽어
CSS 변수에 채운다. 아래는 구조와 계산식만 담는다.

---

## CSS 변수 골격

```css
:root{
  /* rules/design-system.md 의 라이트 값으로 채운다 */
  --page:      ;  --card:      ;  --line:      ;
  --ink:       ;  --ink-2:     ;  --ink-3:     ;
  --s1: ; --s2: ; --s3: ; --s4: ; --s5: ;   /* 계열색 1~5 */
  --good: ; --warn: ; --bad: ;
  --pad: 20px; --gap: 28px; --radius: 4px;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){ /* 다크 값으로 재정의 */ }
}
:root[data-theme="dark"]{ /* 같은 다크 값 */ }
```

모든 색은 bare `:root` 에 먼저 선언한다.
미디어 쿼리 안에만 있는 색은 시스템 설정이 없는 뷰어에서 적용되지 않는다.

---

## 레이아웃

```css
.dash-charts        { display:grid; grid-template-columns:1.5fr 1fr; gap:var(--gap); align-items:stretch; }
.dash-charts.three  { grid-template-columns:repeat(3,1fr); }
.dash-charts.full   { grid-template-columns:1fr; }
.chart-card         { display:flex; flex-direction:column; padding:var(--pad);
                      background:var(--card); border:1px solid var(--line); }
.chart-card.muted   { opacity:.75; }
.chart-card svg     { width:100%; height:auto; margin-top:8px; }
.scroll-x           { overflow-x:auto; }
@media (max-width:900px){ .dash-charts,.dash-charts.three{ grid-template-columns:1fr; } }
```

풀너비 차트는 탭당 1개. 모든 카드가 같은 너비인 배치는 지양한다.

---

## KPI 카드

```html
<div class="kpi">
  <span class="kpi-label">총 매출</span>
  <span class="kpi-val">—</span><!-- FROM: 04_kpi_summary.md -->
  <span class="kpi-unit">원</span>
  <span class="kpi-delta">▲ —</span>
</div>
```

```css
.kpi-val   { font-weight:600; font-variant-numeric:tabular-nums; color:var(--ink); }
.kpi-unit  { color:var(--ink-3); font-size:.8em; }
.kpi-delta { color:var(--ink-2); font-variant-numeric:tabular-nums; }
```

`.kpi-val` 에 계열색·상태색을 넣지 않는다.

---

## SVG 좌표 계산

viewBox 를 `0 0 W H` 로 두고 플롯 영역을 정한다.

```
padT = 10, padB = 24, padL = (축 레이블 있으면 40~70, 없으면 8), padR = 8
chartH = H - padT - padB
chartW = W - padL - padR
```

플롯 영역이 viewBox 면적의 80% 이상이어야 한다.

### 막대 (y=0이 상단)

```
y      = padT + (1 - v/max) * chartH
height = (v/max) * chartH
```

`chartH=160, v=75, max=100` → `y = padT + 40`, `height = 120`

막대 폭은 `chartW / n * 0.7`, 사이 간격 2px 이상.
막대 끝 4px 라운드는 `rx="4"` 로 두고 베이스라인 쪽은 각지게 유지한다.

### 라인 / 영역

```
x = padL + i * (chartW / (n - 1))
y = padT + (1 - v/max) * chartH
```

`stroke-width="2"`, `fill="none"`, 끝점만 `<circle r="4">` 로 강조.

### 코호트 삼각 히트맵

행 = 코호트, 열 = 경과기간. 셀 하나:

```
x = padL + col * cellW
y = padT + row * cellH
```

값은 순차색 단계로 매핑한다. 셀 사이 1px 표면색 간격.
데이터가 없는 삼각형 영역은 그리지 않는다 — 0으로 칠하지 않는다.

### 에러바 (판정형)

```
중앙값 y     = padT + (1 - v/max) * chartH
상한 y       = padT + (1 - hi/max) * chartH
하한 y       = padT + (1 - lo/max) * chartH
```

세로선 `stroke-width="2"` + 상하 캡 8px + 중앙 마커 `r="4"`.
**0 기준선을 반드시 그린다.** 구간이 0을 지나는지가 판정의 핵심이다.

---

## 모든 도형에 fill 을 명시한다

`fill` 을 비워 두면 브라우저 기본값(검정)이 적용되어 다크 모드에서 사라진다.
장식 도형도 `fill="none"` 을 명시한다.

---

## 차트 텍스트

```css
.svg-label { font-family: ui-monospace, monospace; font-size:11px; fill:var(--ink-3); }
.svg-value { font-family: ui-monospace, monospace; font-size:11px; fill:var(--ink-2); }
```

차트 안 텍스트는 계열색을 입지 않는다. 잉크 색을 쓴다.
축 레이블·범례는 viewBox 하단 여백 안에 배치한다.

---

## 탭

```html
<button class="method-btn active" onclick="switchPanel(0,this)">현황</button>
<section id="panel-0" class="dash-panel active"> … </section>
```

```js
function switchPanel(idx, btn){
  document.querySelectorAll('.method-btn').forEach((b,i)=>b.classList.toggle('active', i===idx));
  document.querySelectorAll('.dash-panel').forEach((p,i)=>p.classList.toggle('active', i===idx));
  window.scrollTo({top:0, behavior:'smooth'});
}
```

함수 이름을 바꾸지 않는다. 새 전환 함수를 만들지 않는다.

---

## 툴팁

```js
function showTip(e, html){
  const t = document.getElementById('tip');
  t.innerHTML = html; t.hidden = false;
  t.style.left = (e.pageX + 12) + 'px';
  t.style.top  = (e.pageY - 8)  + 'px';
}
function hideTip(){ document.getElementById('tip').hidden = true; }
```

숨김은 `hidden` 속성으로. `style.display` 로 토글하지 않는다.

---

## 메타 영역 — 빼지 않는다

```html
<p class="dash-meta">
  거래 단위 집계 · 취소 송장 제외 · 2010-12 ~ 2011-11 · n=—
  <!-- FROM: 04_kpi_summary.md 제외조건 -->
</p>
```

집계 단위와 제외조건이 화면에 없으면 보는 사람이 다른 숫자를 기대한다.
