// 발표 슬라이드 v3 — 컨설팅 보고서형 배치 (report_v8의 ①~⑥ 순서, 부록 제외, 13장)
// 사용: (agent 폴더에서) node tools/build_slides_v3.js drafts/slides_v3.pptx
// 발표자 노트: tools/slides_notes.json (v2와 같은 노트)
// 숫자는 모두 report_v8 본문(=inputs/results CSV)과 같은 값. 금액 표기: 억 원, 1천만 원 미만은 만 원
// 디자인 원칙: 왼쪽 정렬, 액션 타이틀 + 제목 아래 가로선, 상단 진행 표시, 왼쪽 근거(도표·표) / 오른쪽 시사점,
//             표는 가로선만, 텍스트는 숫자 오른쪽 정렬, 한국어는 어절 단위 줄바꿈(eaLnBrk=0)
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const JSZip = require(require.resolve("jszip", { paths: [path.dirname(require.resolve("pptxgenjs"))] }));
const OUT = process.argv[2] || "drafts/slides_v3.pptx";
const SKILL = process.env.PPTX_SKILL || ".";
const { applyTheme } = require(SKILL + "/scripts/apply_theme.js");
const NOTES = JSON.parse(fs.readFileSync(path.join(__dirname, "slides_notes.json"), "utf8"));

const THEME = {
  name: "궁능 C2",
  headFontFace: "Malgun Gothic",
  bodyFontFace: "Malgun Gothic",
  colors: { dk1: "1A1A1A", lt1: "FFFFFF", dk2: "1F3864", lt2: "F1F4F8",
    accent1: "2A78D6", accent2: "EB6834", accent3: "1BAF7A", accent4: "8A94A0", accent5: "86B6EF", accent6: "D5DAE0",
    hlink: "2A78D6", folHlink: "6250D6" },
};
const HEX = { navy: "1F3864", blue: "2A78D6", orange: "EB6834", aqua: "1BAF7A", grey: "A3ACB7", lgrey: "D5DAE0", ink: "1A1A1A", body: "374151", muted: "6B7280", tint: "F1F4F8", slate: "5B6878" };

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.author = "C2 팀 (최의환, 최주영, 정호성)";
pres.title = "궁·능 관람객 예측과 개소별 인력 배치";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const L = 0.55, CW = 12.23, RX = 8.75, RW = 4.03, LW = 7.85; // 왼쪽 근거 / 오른쪽 시사점

// ---------- 레이아웃 ----------
pres.defineSlideMaster({
  title: "TITLE",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.9, y: 2.0, w: 11.0, h: 1.4, fontSize: 38, bold: true, color: C.background1, align: "left", valign: "bottom" }, text: "" } },
    { placeholder: { options: { name: "body", type: "body", x: 0.9, y: 3.85, w: 11.0, h: 0.8, fontSize: 20, color: C.accent5, align: "left", valign: "top" }, text: "" } },
    { line: { x: 0.9, y: 3.62, w: 1.6, h: 0, line: { color: C.accent5, width: 2 } } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  margin: [0.4, 0.55, 0.6, 0.55],
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: L, y: 0.6, w: CW, h: 0.85, fontSize: 24, bold: true, color: C.text2, align: "left", valign: "middle", margin: 0 }, text: "" } },
    { line: { x: L, y: 1.52, w: CW, h: 0, line: { color: C.text2, width: 1.25 } } },
    { line: { x: L, y: 6.92, w: CW, h: 0, line: { color: C.accent6, width: 0.75 } } },
    { text: { text: "C2 팀", options: { x: 10.9, y: 7.0, w: 1.2, h: 0.3, fontSize: 9, color: C.accent4, align: "right", margin: 0 } } },
  ],
  slideNumber: { x: 12.28, y: 7.0, w: 0.5, h: 0.3, fontSize: 9, color: C.accent4, align: "right" },
});

// ---------- 공통 도우미 ----------
const tx = (s, text, o) => s.addText(text, { isTextBox: true, fontSize: 12, color: C.text1, align: "left", valign: "top", margin: 0, ...o });
const hline = (s, x, y, w, color = HEX.lgrey, width = 0.75) => s.addShape(pres.shapes.LINE, { x, y, w, h: 0, line: { color, width } });
// 진행 표시 (상단)
const SEC = ["권고 요약", "질문과 범위", "선택과 이유", "근거", "오차와 한계", "추가 발견과 다음 할 일"];
const NUM = ["①", "②", "③", "④", "⑤", "⑥"];
function tracker(s, cur) {
  let x = L;
  SEC.forEach((name, i) => {
    const label = `${NUM[i]} ${name}`;
    const w = 0.12 + [...label].reduce((a, ch) => a + (/[가-힣①-⑥]/.test(ch) ? 0.128 : 0.065), 0);
    const on = i === cur;
    tx(s, label, { x, y: 0.2, w, h: 0.26, fontSize: 9, bold: on, color: on ? C.text2 : C.accent4, valign: "middle" });
    if (on) s.addShape(pres.shapes.RECTANGLE, { x, y: 0.47, w, h: 0.04, fill: { color: C.text2 }, line: { color: C.text2 }, objectName: "tracker current" });
    x += w + 0.32;
  });
}
// 출처·주석 (왼쪽 아래)
const source = (s, text) => tx(s, text, { x: L, y: 6.97, w: 10.1, h: 0.4, fontSize: 8.5, color: C.accent4 });
// 소제목 + 밑줄
function header(s, text, x, y, w) {
  tx(s, text, { x, y, w, h: 0.32, fontSize: 13, bold: true, color: C.text2, valign: "bottom" });
  hline(s, x, y + 0.38, w, HEX.navy, 0.75);
}
// 번호 사각형
function numBox(s, n, x, y, color = C.text2) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.3, h: 0.3, fill: { color }, line: { color }, objectName: "num " + n });
  tx(s, String(n), { x, y, w: 0.3, h: 0.3, fontSize: 11, bold: true, color: C.background1, align: "center", valign: "middle" });
}
// 시사점 항목: { big?, bigColor?, lead, body? }
function points(s, items, x, y, w, rowH, opt = {}) {
  const hs = Array.isArray(rowH) ? rowH : items.map(() => rowH);
  items.forEach((it, i) => {
    const yy = y + hs.slice(0, i).reduce((a, b) => a + b, 0);
    const rh = hs[i];
    let cy = yy;
    if (opt.numbered) numBox(s, i + 1, x, yy + 0.02);
    const tx0 = opt.numbered ? x + 0.45 : x, tw = opt.numbered ? w - 0.45 : w;
    if (it.big) { tx(s, it.big, { x: tx0, y: cy, w: tw, h: 0.5, fontSize: 24, bold: true, color: it.bigColor || C.text2, valign: "middle" }); cy += 0.55; }
    tx(s, it.lead, { x: tx0, y: cy, w: tw, h: 0.32, fontSize: 13, bold: true, color: C.text1, valign: "top", fit: "none" });
    if (it.body) tx(s, it.body, { x: tx0, y: cy + (it.leadH || 0.34), w: tw, h: rh - (cy - yy) - 0.45, fontSize: 11.5, color: HEX.body });
    if (i < items.length - 1 && opt.rule !== false) hline(s, x, yy + rh - 0.12, w);
  });
}
// 컨설팅형 표: 가로선만, 머리글 아래 남색 선
function ctable(s, head, body, o) {
  const none = { type: "none" };
  const thin = { type: "solid", pt: 0.5, color: HEX.lgrey };
  const strong = { type: "solid", pt: 1.25, color: HEX.navy };
  const al = o.align || head.map(() => "left");
  const rows = [head.map((h, j) => ({ text: h, options: { bold: true, color: HEX.navy, align: al[j], valign: "bottom", border: [none, none, strong, none], fontSize: o.headSize || o.fontSize } }))];
  body.forEach((r) => rows.push(r.map((c, j) => {
    const cell = typeof c === "string" ? { text: c, options: {} } : c;
    return { text: cell.text, options: { align: al[j], valign: "middle", border: [none, none, thin, none], ...cell.options } };
  })));
  s.addTable(rows, { x: o.x, y: o.y, w: o.w, colW: o.colW, fontSize: o.fontSize || 12, fontFace: "Malgun Gothic", color: HEX.ink,
    rowH: o.rowH, margin: [0.04, 0.08, 0.04, 0.08], objectName: o.name });
}
const chartBase = {
  catAxisLabelColor: HEX.ink, valAxisLabelColor: HEX.muted, catAxisLabelFontSize: 11, valAxisLabelFontSize: 10,
  catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt", legendFontFace: "+mn-lt", titleFontFace: "+mn-lt",
  dataLabelFontSize: 11, dataLabelColor: HEX.ink, valGridLine: { style: "none" }, catGridLine: { style: "none" },
  catAxisLineShow: true, catAxisLineColor: HEX.lgrey, valAxisLineShow: false,
};
const hide0 = '#,##0.00;-#,##0.00;;';

let s;
const addContent = (cur, title, i) => {
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: `${NUM[cur]} ${SEC[cur]}` });
  tracker(s, cur);
  s.addText(title, { placeholder: "title" });
  s.addNotes(NOTES[i - 1]);
  return s;
};
const section = (cur) => pres.addSection({ title: `${NUM[cur]} ${SEC[cur]}` });

// ================= 1. 표지 =================
pres.addSection({ title: "표지" });
s = pres.addSlide({ masterName: "TITLE", sectionTitle: "표지" });
s.addText("궁·능 관람객 예측과 개소별 인력 배치", { placeholder: "title" });
s.addText("무료 개방일·명절을 반영한 앙상블 예측과 2026년 1월 권고", { placeholder: "body" });
tx(s, [{ text: "C2 팀  ·  최의환, 최주영, 정호성", options: { breakLine: true } }, { text: "데이터 분석 부트캠프 프로젝트 3 (D052)  ·  2026년 10월 19일" }],
  { x: 0.9, y: 5.9, w: 11.0, h: 0.75, fontSize: 14, color: C.background1, paraSpaceAfter: 4 });
s.addNotes(NOTES[0]);

// ================= 2. ① 핵심 요약 =================
section(0);
addContent(0, "근무표를 짤 때 이미 아는 달력 정보만으로 인력 비용을 49.2% 줄였다", 2);
header(s, "핵심 메시지", L, 1.75, LW);
points(s, [
  { lead: "지금 방식(직전 7일 평균)은 무료 개방일에 가장 크게 틀린다", body: "무료 개방일은 평가 행의 7.6%지만 비용의 30.0%(5.11억 원)를 만든다" },
  { lead: "달력 정보만으로 비용을 절반 가까이 줄였다", body: "17.03억 → 8.66억 원(−49.2%), 2025년 원점 12개 모두에서 더 쌌다" },
  { lead: "절감은 모자란 인원을 막아서 나왔다", body: "모자란 인원 2,159명 → 751명(−65%), 남는 인원은 2,715명 → 2,768명으로 거의 그대로" },
  { lead: "절감의 56%는 모형, 32%는 달력 정보, 12%는 서비스 수준 보정", body: "달력 정보 중에는 공휴일이 1.50억 원으로 가장 컸다" },
  { lead: "권고: 1월 28일 경복궁 13명, 근무표는 1단계 방식부터", body: "월 1회 + 공지 증원 + 수요일 하한. 주 1회보다 238만 원 싸고 근무자 부담은 그대로" },
], L, 2.3, LW, 0.9, { numbered: true });
header(s, "핵심 수치 (2025년 백테스트)", RX, 1.75, RW);
const kfig = [["8.37억 원", "절감액 (−49.2%)", C.text2], ["12 / 12", "더 싼 원점 수", C.text2], ["−65%", "모자란 인원", C.accent2], ["30.0%", "무료 개방일의 비용 비중 (지금 방식)", C.text2]];
kfig.forEach(([big, lab, col], i) => {
  const y = 2.3 + i * 1.12;
  tx(s, big, { x: RX, y, w: RW, h: 0.55, fontSize: 28, bold: true, color: col, valign: "middle" });
  tx(s, lab, { x: RX, y: y + 0.58, w: RW, h: 0.3, fontSize: 11.5, color: HEX.body });
  if (i < 3) hline(s, RX, y + 1.0, RW);
});
source(s, "주: 비용 = 60만 원 × 모자란 인원 + 15만 원 × 남는 인원 (소수 인원 기준, 가이드 기본값). 앙상블 = Chronos-2 + 달력과 Prophet의 0.8 분위수 50:50 평균\n출처: 모형_비교_전체.csv, 백테스트_비용.csv, 오차_유형별.csv, FVA_앙상블.csv, 운영방안_비교.csv");

// ================= 3. ① 권고 =================
addContent(0, "1월 권고: 경복궁은 1월 28일에 13명, 왕릉은 영업일마다 1명", 3);
header(s, "2026년 1월 개소별 권고 인원 (정수)", L, 1.75, LW);
const O = (t) => ({ text: t, options: { bold: true, color: HEX.orange } });
const B = (t) => ({ text: t, options: { bold: true } });
ctable(s, ["개소", "영업일 인원", "1월 28일", "예정 휴관일", "1월 합계"], [
  [B("경복궁"), "6~10명 (대부분 7~8명)", O("13명"), "화요일 0명", "212명"],
  [B("덕수궁"), "5~7명", "7명", "월요일 0명", "146명"],
  [B("창덕궁"), "2~3명", "3명", "월요일 0명", "67명"],
  [B("창경궁"), "1~2명", O("3명"), "월요일 0명", "42명"],
  [B("종묘"), "1~2명", O("3명"), "화요일 0명", "39명"],
  [B("왕릉 18곳"), "각 1명", "각 1명", "월요일 0명", "486명"],
  [B("합계"), "", "", "", B("992명")],
], { x: L, y: 2.25, w: LW, colW: [1.45, 2.6, 1.35, 1.3, 1.15], align: ["left", "left", "right", "left", "right"], rowH: 0.34, fontSize: 12, name: "recommendation table" });
header(s, "읽는 법", RX, 1.75, RW);
points(s, [
  { lead: "근무표 확정: 2025-12-31, 월 1회", body: "확정일까지의 데이터만 학습·예측에 썼다" },
  { lead: "정수로 바꾸는 규칙", body: "0.8 분위수 ÷ 2,000명을 올림\n영업일 최소 1명, 예정 휴관일 0명" },
  { lead: "1월 28일(수)은 마지막 수요일 하한 반영", body: "무료 개방일. 경복궁 11→13명,\n창경궁·종묘 2→3명" },
], RX, 2.3, RW, 0.93);
header(s, "권하는 근무표 확정 방식", L, 5.2, CW);
const chev = [["1단계 · 바로", "월 1회 + 공지 증원 + 수요일 하한", C.text2], ["2단계 · 3개월 뒤 시범", "비용의 81%인 궁·종묘 5곳만 주 1회", C.accent1], ["3단계 · 시범 결과를 보고", "전체 주 1회 확정", HEX.slate]];
chev.forEach(([h, b, col], i) => {
  const x = L + i * 4.1, w = 4.13;
  s.addShape(i === 0 ? pres.shapes.PENTAGON : pres.shapes.CHEVRON, { x, y: 5.75, w, h: 0.9, fill: { color: col }, line: { color: col }, objectName: "step " + (i + 1) });
  tx(s, [{ text: h, options: { bold: true, breakLine: true } }, { text: b }], { x: x + (i === 0 ? 0.2 : 0.5), y: 5.79, w: 3.3, h: 0.82, fontSize: 12, color: C.background1, valign: "middle", paraSpaceAfter: 2 });
});
source(s, "주: 1월 1~4일·31일 경복궁 9~10명, 나머지 영업일 21일 6~8명. 전체 권고표(정수 인원과 소수 배치 인원)는 보고서 부록 B\n출처: 권고표_2026_01_최종.csv (713행), 운영방안_비교.csv, 운영방안_비교_구분별.csv");

// ================= 4. ② 질문과 범위 =================
section(1);
addContent(1, "지금 방식이 가장 크게 틀리는 무료 개방일·명절을 주제로 잡았다", 4);
header(s, "무료 개방일이 차지하는 비중 (%)", L, 1.75, LW);
s.addChart(pres.charts.BAR, [
  { name: "직전 7일 평균", labels: ["평가 행", "직전 7일 평균의 비용", "앙상블의 비용"], values: [7.6, 30.0, 0] },
  { name: "앙상블", labels: ["평가 행", "직전 7일 평균의 비용", "앙상블의 비용"], values: [0, 0, 21.5] },
], { ...chartBase, x: L, y: 2.25, w: LW, h: 2.2, barDir: "bar", barGrouping: "stacked", barGapWidthPct: 45,
  chartColors: [HEX.grey, HEX.blue], showValue: true, dataLabelPosition: "inEnd", dataLabelFormatCode: '0.0"%";;;', dataLabelColor: "FFFFFF", dataLabelFontSize: 12,
  showLegend: false, valAxisMinVal: 0, valAxisMaxVal: 32, catAxisOrientation: "maxMin", valAxisHidden: true, objectName: "free day share chart" });
header(s, "직전 7일 평균은 무료 개방일에 두 번 틀린다", L, 4.65, LW);
points(s, [
  { lead: "급증하는 당일: 평균이 낮아 인원이 모자란다", body: "모자람 1명은 하루 60만 원으로, 남음(15만 원)의 4배다" },
  { lead: "지난 뒤: 급증이 평균에 섞여 평상시 날에 인원이 남는다", body: "예: 2025-10-14(화) 창덕궁. 추석 3일이 섞여 12.9명 배치, 필요 3.6명 → 하루 139만 원 손실" },
], L, 5.2, LW, 0.82, { numbered: true });
header(s, "이 보고서가 정한 범위", RX, 1.75, RW);
ctable(s, ["항목", "정한 것"], [
  [B("예측 단위"), "개소별 23곳 (궁 4·종묘 1·왕릉 18)"],
  [B("예측 기간"), "백테스트: 원점부터 그달 끝까지\n권고: 2026-01-01~01-31"],
  [B("확정 시점"), "원점 전날 (권고표는 2025-12-31)"],
  [B("1순위 지표"), "비용(원), 소수 인원 기준"],
  [B("보조 지표"), "WAPE, 적중률 (MAPE는 쓰지 않음)"],
  [B("평가"), "2025년 매월 1일 원점 12개\n실제 휴관 제외 7,203행"],
  [B("지금 방식"), "직전 7일 평균 (프로젝트 가정)"],
], { x: RX, y: 2.25, w: RW, colW: [1.15, 2.88], rowH: [0.34, 0.42, 0.58, 0.42, 0.42, 0.42, 0.58, 0.42], fontSize: 11, name: "scope table" });
source(s, "주: 무료 개방일 = 명절 연휴 블록 + 매월 마지막 수요일 (551행 / 7,203행). 관람객이 적은 왕릉은 MAPE가 크게 흔들려 쓰지 않았다\n출처: 오차_유형별.csv, FVA_앙상블.csv, 가이드 검산 예시");

// ================= 5. ③ 선택과 이유 =================
section(2);
addContent(2, "모자람이 남음보다 4배 비싸서 0.8 분위수, 가장 싼 앙상블을 골랐다", 5);
header(s, "세 가지 선택과 포기한 것", L, 1.75, CW);
ctable(s, ["선택", "고른 것", "고른 이유", "포기한 것"], [
  [B("예측 단위"), "개소별 23곳", "근무표에 바로 옮길 수 있다.\n무료 개방 효과가 개소마다 1배 미만~7배 넘게 달라, 합치면 뭉개진다", "관람객이 적은 왕릉은 오차 비율이 크다 (WAPE 54.0%)"],
  [B("모형"), "Chronos-2 + 달력과 Prophet의 50:50 앙상블", "후보 중 총 비용이 가장 낮다 (8.66억 원).\n비율은 결과를 보고 조정하지 않았다", "계수로 설명하기 어렵고, 두 모형을 함께 돌려야 한다"],
  [B("서비스 수준"), "관람객 0.8 분위수", "모자람 60만 원 · 남음 15만 원의 임계비율\n60 ÷ (60 + 15) = 0.8이 기대 비용을 가장 작게 만든다", "평균적으로 5일 중 1일은 인력이 모자랄 수 있다"],
], { x: L, y: 2.25, w: CW, colW: [1.55, 2.75, 4.7, 3.23], rowH: [0.4, 0.95, 0.95, 0.95], fontSize: 12, name: "choice table" });
s.addShape(pres.shapes.RECTANGLE, { x: L, y: 5.6, w: CW, h: 1.15, fill: { color: C.background2 }, line: { color: C.background2 }, objectName: "why cost box" });
tx(s, "왜 비용이 1순위인가", { x: L + 0.25, y: 5.6, w: 2.4, h: 1.15, fontSize: 13, bold: true, color: C.text2, valign: "middle" });
tx(s, [{ text: "WAPE가 가장 낮은 LightGBM(34.7%)도 비용은 11.01억 원으로 앙상블보다 2.35억 원 컸다.", options: { breakLine: true } }, { text: "0.8 분위수를 낮게 잡아(적중률 69.4%) 인원이 자주 모자랐기 때문이다.", options: { breakLine: true } }, { text: "오차의 크기만 보고 고르면, 모자람 비용이 큰 이 문제에서 잘못된 모형을 고른다." }],
  { x: L + 2.75, y: 5.6, w: CW - 3.0, h: 1.15, fontSize: 12, color: HEX.body, valign: "middle", paraSpaceAfter: 3 });
source(s, "주: 모형과 앙상블 비율은 2025년 백테스트 결과를 보고 골랐다 (한계는 ⑤)\n출처: REPORT_SPEC 1-1 팀 결정, 모형_비교_전체.csv");

// ================= 6. ④ 모형 비교 =================
section(3);
addContent(3, "앙상블은 후보 중 비용이 가장 낮고, 적중률은 82.0%로 목표 근처다", 6);
header(s, "모형별 총 비용 (억 원, 2025년 원점 12개 합)", L, 1.75, LW);
const mLab = ["나이브", "계절 나이브 7일", "직전 7일 평균 (지금 방식)", "+ 서비스 수준 보정", "LightGBM (0.8)", "Prophet", "Chronos-2 + 달력", "앙상블 (최종)"];
const mVal = [18.42, 18.04, 17.03, 16.00, 11.01, 9.40, 9.32, 8.66];
s.addChart(pres.charts.BAR, [
  { name: "후보·베이스라인", labels: mLab, values: mVal.map((v, i) => (i === 7 ? 0 : v)) },
  { name: "앙상블", labels: mLab, values: mVal.map((v, i) => (i === 7 ? v : 0)) },
], { ...chartBase, x: L, y: 2.25, w: LW, h: 4.45, barDir: "bar", barGrouping: "stacked", barGapWidthPct: 40,
  chartColors: [HEX.lgrey, HEX.blue], showValue: true, dataLabelPosition: "inEnd", dataLabelFormatCode: hide0,
  showLegend: false, catAxisOrientation: "maxMin", valAxisMinVal: 0, valAxisMaxVal: 19, valAxisHidden: true, objectName: "model cost chart" });
header(s, "시사점", RX, 1.75, RW);
points(s, [{ lead: "앙상블이 8.66억 원으로 가장 쌌다", body: "베이스라인 3개는 모두 17억 원 이상" }], RX, 2.3, RW, 0.85, { rule: false });
header(s, "적중률 (목표 80%)", RX, 3.15, RW);
ctable(s, ["모형", "적중률"], [
  [B("앙상블"), { text: "82.0%", options: { bold: true, color: HEX.blue } }], ["Chronos-2 + 달력", "80.6%"], ["Prophet", "78.2%"], ["LightGBM (0.8)", "69.4%"], ["직전 7일 평균", "60.2%"],
], { x: RX, y: 3.65, w: RW, colW: [2.9, 1.13], align: ["left", "right"], rowH: 0.33, fontSize: 11.5, name: "hit table" });
tx(s, "적중률은 높을수록 좋은 지표라고 볼 수 없다. 80%에 가장 가까운 것은 Chronos-2 + 달력이고, 앙상블은 약간 넉넉한 쪽이다. 앙상블을 고른 기준은 비용이다.", { x: RX, y: 5.75, w: RW, h: 0.95, fontSize: 11, color: HEX.muted });
source(s, "주: 소수 인원 기준. 18개 모형 전체는 보고서 부록 A\n출처: 모형_비교_전체.csv");

// ================= 7. ④ 원점별 =================
addContent(3, "앙상블은 2025년 12개 달 모두 직전 7일 평균보다 쌌다", 7);
header(s, "원점별 총 비용 (억 원)", L, 1.75, LW);
const months = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"];
s.addChart(pres.charts.LINE, [
  { name: "직전 7일 평균", labels: months, values: [1.40, 1.27, 0.94, 1.55, 1.24, 0.66, 0.51, 0.71, 1.20, 4.61, 2.50, 0.44] },
  { name: "앙상블", labels: months, values: [0.54, 0.37, 0.45, 0.86, 0.89, 0.44, 0.35, 0.31, 0.46, 1.82, 1.88, 0.29] },
], { ...chartBase, x: L, y: 2.25, w: LW, h: 4.45, chartColors: [HEX.grey, HEX.blue], lineSize: 2.25, lineDataSymbol: "circle", lineDataSymbolSize: 6,
  showLegend: true, legendPos: "t", legendFontSize: 11, valGridLine: { color: "EEF0F3", size: 0.5 },
  valAxisMinVal: 0, valAxisMaxVal: 5, valAxisLabelFormatCode: "0.0", objectName: "monthly cost chart" });
header(s, "시사점", RX, 1.75, RW);
points(s, [
  { big: "2.79억 원", bigColor: C.accent2, lead: "10월의 차이가 가장 컸다", body: "추석 연휴가 든 달\n직전 7일 평균 4.61억 → 앙상블 1.82억 원" },
  { big: "42.7%", lead: "10·11월이 앙상블 비용에서 차지하는 몫", body: "추석 연휴와 코리아 그랜드 페스티벌\n무료입장이 든 달. 남은 오차는\n특별한 날에 몰려 있다 (⑤)" },
], RX, 2.3, RW, 2.2);
source(s, "주: 소수 인원 기준. 원점 = 2025년 매월 1일, 예측 = 그달 끝까지\n출처: compare_per_origin.csv");

// ================= 8. ④ FVA =================
addContent(3, "절감의 56%는 모형, 32%는 달력 정보, 12%는 서비스 수준 보정에서 왔다", 8);
header(s, "정보를 한 단계씩 더할 때 줄어든 비용 (억 원)", L, 1.75, LW);
const fLab = ["서비스 수준 보정", "모형: 과거 관람객만", "+ 예정 휴관", "+ 공휴일", "+ 명절 연휴", "+ 마지막 수요일"];
const fVal = [1.03, 4.68, 0.44, 1.50, 0.44, 0.28];
const grp = [0, 1, 2, 2, 2, 2];
s.addChart(pres.charts.BAR, [0, 1, 2].map((g) => ({ name: ["보정 (12%)", "모형 (56%)", "달력 정보 (32%)"][g], labels: fLab, values: fVal.map((v, i) => (grp[i] === g ? v : 0)) })),
  { ...chartBase, x: L, y: 2.25, w: LW, h: 4.45, barDir: "bar", barGrouping: "stacked", barGapWidthPct: 40,
    chartColors: [HEX.grey, HEX.blue, HEX.aqua], showValue: true, dataLabelPosition: "inEnd", dataLabelFormatCode: hide0, dataLabelColor: "FFFFFF",
    showLegend: true, legendPos: "t", legendFontSize: 11, catAxisOrientation: "maxMin", valAxisMinVal: 0, valAxisMaxVal: 5, valAxisHidden: true, objectName: "fva chart" });
header(s, "시사점", RX, 1.75, RW);
points(s, [
  { big: "8.37억 원", lead: "17.03억 → 8.66억 원", body: "직전 7일 평균에서 출발해 정보를 하나씩\n더했다 (FVA). 달력 정보 중에는 공휴일\n(1.50억 원)이 가장 컸다" },
  { lead: "휴관 이동·이웃 궁 휴관은 뺐다", body: "더하면 비용이 153만 원 늘었다" },
  { lead: "날씨는 쓰지 않았다", body: "[완벽한 예보 가정]에도 절감 상한이\n약 0.20억 원(2.3%), 달력 정보의 10분의 1 미만" },
], RX, 2.3, RW, [2.15, 1.1, 1.3]);
source(s, "주: 소수 인원 기준. 비중 = 각 몫 ÷ 전체 절감 837,114,828원. 날씨 값은 근무표 확정 시점에 알 수 없는 정보를 쓴 사후 근사\n출처: FVA_앙상블.csv, 날씨_완벽예보_근사.csv");

// ================= 9. ④ 확정 시점 =================
addContent(3, "월 1회 확정에 공지 증원과 수요일 하한만 더해도 주 1회 확정보다 싸다", 9);
header(s, "근무표 확정 방안별 총 비용 (억 원)", L, 1.75, LW);
const pLab = ["1. 월 1회 (지금)", "2. 월 1회 + 공지 증원", "3. 월 1회 + 공지 증원 + 수요일 하한  [1단계]", "4. 주 1회", "6. 궁·종묘 주 1회 + 왕릉 월 1회", "7. 6 + 공지 증원 + 수요일 하한  [2단계]", "5. 주 1회 + 공지 증원 + 수요일 하한  [3단계]"];
const pVal = [8.60, 7.90, 7.81, 7.83, 8.08, 7.26, 6.97];
const rec = [false, false, true, false, false, true, true];
s.addChart(pres.charts.BAR, [
  { name: "다른 방안", labels: pLab, values: pVal.map((v, i) => (rec[i] ? 0 : v)) },
  { name: "권고 단계", labels: pLab, values: pVal.map((v, i) => (rec[i] ? v : 0)) },
], { ...chartBase, x: L, y: 2.25, w: LW, h: 4.45, barDir: "bar", barGrouping: "stacked", barGapWidthPct: 40, catAxisLabelFontSize: 10.5,
  chartColors: [HEX.lgrey, HEX.blue], showValue: true, dataLabelPosition: "inEnd", dataLabelFormatCode: hide0,
  showLegend: false, catAxisOrientation: "maxMin", valAxisMinVal: 6, valAxisMaxVal: 8.8, valAxisHidden: true, objectName: "plan chart" });
header(s, "시사점", RX, 1.75, RW);
points(s, [
  { big: "238만 원", bigColor: C.accent1, lead: "1단계가 주 1회보다 싸다", body: "방안 3 (7.81억 원) vs 방안 4 (7.83억 원)" },
  { lead: "근무자 부담은 지금과 같다", body: "근무자가 일정을 아는 시점\n월 1회: 평균 약 16일 전 / 주 1회: 평균 4일 전" },
  { lead: "2단계는 월 1회보다 1.34억 원 절감", body: "비용의 81%가 나오는 궁·종묘 5곳만\n주 1회로 확정" },
], RX, 2.3, RW, [1.85, 1.25, 1.25]);
source(s, "주: 소수 인원 기준, 막대는 6억 원부터. 공통 평가일 2025-01-06~12-31 (7,088행), 공지 후 증원 준비 14일. 공지 증원 몫 0.70억 원은 2025년 행사 하나의 값\n출처: 운영방안_비교.csv, 운영방안_비교_구분별.csv");

// ================= 10. ⑤ 부족 상위 10건 =================
section(4);
addContent(4, "가장 많이 모자란 10건은 모두 미리 알 수 있던 행사·추석이었다", 10);
header(s, "인력이 가장 많이 모자란 10건 (앙상블, 2025년)", L, 1.75, LW);
const top = [
  ["11/08 (토)", "덕수궁", "66,257", "26,551", "19.9", "코리아 그랜드 페스티벌"],
  ["05/04 (일)", "종묘", "44,337", "5,607", "19.4", "종묘대제"],
  ["10/08 (수)", "창경궁", "58,122", "26,264", "15.9", "추석 연휴"],
  ["10/08 (수)", "창덕궁", "56,508", "27,783", "14.4", "추석 연휴"],
  ["11/04 (화)", "창덕궁", "45,452", "18,032", "13.7", "코리아 그랜드 페스티벌"],
  ["10/08 (수)", "종묘", "35,524", "9,146", "13.2", "추석 연휴"],
  ["11/08 (토)", "창덕궁", "44,669", "19,482", "12.6", "코리아 그랜드 페스티벌"],
  ["11/08 (토)", "경복궁", "62,517", "37,947", "12.3", "코리아 그랜드 페스티벌"],
  ["10/09 (목)", "종묘", "31,131", "8,074", "11.5", "추석 연휴 (한글날)"],
  ["11/09 (일)", "덕수궁", "42,187", "19,651", "11.3", "코리아 그랜드 페스티벌"],
];
ctable(s, ["날짜", "개소", "실제 (명)", "예측 (명)", "부족 (명)", "원인"],
  top.map((r) => [r[0], r[1], r[2], r[3], B(r[4]), { text: r[5], options: { bold: true, color: r[5].startsWith("추석") ? HEX.aqua : HEX.orange } }]),
  { x: L, y: 2.25, w: LW, colW: [1.2, 0.95, 1.1, 1.1, 1.0, 2.5], align: ["left", "left", "right", "right", "right", "left"], rowH: 0.39, fontSize: 11.5, name: "top10 table" });
header(s, "시사점", RX, 1.75, RW);
points(s, [
  { big: "−0.78억 원", bigColor: C.accent3, lead: "보정 규칙 A + B로 9.0% 더 줄였다", body: "A: 확정 전 공지된 임시 무료 개방일 × 배율\nB: 마지막 수요일 하한" },
  { lead: "남은 오차가 몰린 곳", body: "궁 4곳이 비용의 72.6%\n무료 개방일: 행 7.6%, 비용 21.5%\n공휴일 적중률 55.6%로 가장 낮음" },
  { lead: "추석은 입력에 있었지만 증가 폭을 작게 잡았다", body: "행사는 입력에 없던 정보였다" },
], RX, 2.3, RW, [1.9, 1.5, 1.0]);
source(s, "주: 관람객 단위 명, 부족 단위 인력(명). 행사 6건 · 추석 연휴 4건. 보정 효과는 같은 원점에서 다시 계산\n출처: 오차_상위10건.csv, 오차_유형별.csv, 보정규칙_전후.csv, 궁능유적본부·국가유산청 공지");

// ================= 11. ⑤ 가정과 한계 =================
addContent(4, "가정을 바꿔도 앙상블이 더 쌌지만, 검증은 2025년 한 해뿐이다", 11);
header(s, "가정별 총 비용 (억 원)과 절감률", L, 1.75, LW);
const aLab = ["기본\n절감 49.2%", "무료 개방일 모자람 2배\n절감 56.6%", "1명당 1,500명\n절감 49.2%", "둘 다\n절감 56.6%"];
s.addChart(pres.charts.BAR, [
  { name: "직전 7일 평균", labels: aLab, values: [17.03, 22.05, 22.70, 29.39] },
  { name: "앙상블", labels: aLab, values: [8.66, 9.57, 11.54, 12.77] },
], { ...chartBase, x: L, y: 2.25, w: LW, h: 4.45, barDir: "col", barGrouping: "clustered", barGapWidthPct: 70, catAxisLabelFontSize: 10.5,
  chartColors: [HEX.grey, HEX.blue], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00",
  showLegend: true, legendPos: "t", legendFontSize: 11, valAxisMinVal: 0, valAxisMaxVal: 33, valAxisHidden: true, objectName: "assumption chart" });
header(s, "남은 한계", RX, 1.75, RW);
points(s, [
  { lead: "모형을 2025년 결과를 보고 골랐다", body: "2위와 차이는 0.66억 원이라 순위는 바뀔 수 있다. 다만 후보 모두 직전 7일 평균보다 크게 쌌다" },
  { lead: "공지 증원 효과는 행사 하나에서 나왔다", body: "규칙 A의 절감 0.69억 원은 참고 값" },
  { lead: "왕릉 최소 1명은 과배치를 만든다", body: "1월 약 0.63억 원 (정수 규칙 기준)" },
  { lead: "가정 1·3은 비용만 다시 계산했다", body: "예측(0.8 분위수)은 다시 맞추지 않았다" },
], RX, 2.3, RW, 1.1, { numbered: true });
source(s, "주: 소수 인원 기준. 가정 1 = 무료 개방일 모자람 비용 60만 → 120만 원, 가정 2 = 1명당 관람객 2,000 → 1,500명\n출처: 가정_바꾸기.csv, 모형_비교_전체.csv, 보정규칙_전후.csv, 권고표_2026_01_최종.csv");

// ================= 12. ⑥ 추가 발견 =================
section(5);
addContent(5, "같은 무료 개방이라도 개소에 따라 효과가 7배 넘게 다르다", 12);
header(s, "무료 개방일 관람객 배율 (평상시 = 1배)", L, 1.75, LW);
const xLab = ["종묘", "창경궁", "창덕궁", "경복궁", "덕수궁", "왕릉 중앙값"];
s.addChart(pres.charts.BAR, [
  { name: "마지막 수요일", labels: xLab, values: [4.84, 3.11, 2.08, 1.98, 1.53, 1.54] },
  { name: "명절 연휴", labels: xLab, values: [5.47, 4.99, 3.50, 4.40, 2.11, 2.40] },
], { ...chartBase, x: L, y: 2.25, w: LW, h: 3.75, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
  chartColors: [HEX.blue, HEX.orange], showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.00",
  showLegend: true, legendPos: "t", legendFontSize: 11, valAxisMinVal: 0, valAxisMaxVal: 6, valAxisHidden: true, objectName: "multiplier chart" });
tx(s, "왕릉은 수요일 0.85배(영휘원)부터 명절 7.63배(의릉)까지 퍼져 있다. 개소를 합치면 이 차이가 평균에 묻혀 배율이 큰 곳에서 인력이 모자란다. 개소별로 예측한 이유다.",
  { x: L, y: 6.1, w: LW, h: 0.65, fontSize: 11.5, color: HEX.body });
header(s, "그 밖의 발견", RX, 1.75, RW);
points(s, [
  { lead: "종묘대제는 달력에 없는 가장 큰 행사", body: "5월 첫 일요일, 평소의 11.61배\n2025년 부족 2위 (5/4 종묘)\n달력 열 하나로 넣을 수 있다" },
  { lead: "2026-05-27부터 수요일 무료 개방이 매주로", body: "왕릉부터 시작, 이번 권고 기간 밖이다\n적용 뒤 수요일 규칙과 배율을 바꿔야 한다" },
  { lead: "이웃 궁 휴관과 날씨는 효과가 작다", body: "이웃 궁 휴관은 비용 153만 원 증가\n먼저 모을 정보는 날씨보다 행사 공지다" },
], RX, 2.3, RW, 1.47, { numbered: true });
source(s, "주: 배율 = 무료 개방일 평균 ÷ 같은 요일 일반 개방일 평균 (2023~2025년 개방일). 명절 배율에는 연휴 자체의 효과가 섞여 있다\n출처: 무료개방_효과_개소별.csv, 가이드 3·7쪽, 국가유산청 공지");

// ================= 13. ⑥ 정할 것과 다음 할 일 =================
addContent(5, "1단계 확정 방식부터 승인하고, 매월 말 권고표를 다시 계산한다", 13);
header(s, "운영팀이 정할 것", L, 1.75, 6.0);
points(s, [
  { lead: "1단계 확정 방식 승인", body: "월 1회 + 공지 증원 + 수요일 하한. 주 1회보다 238만 원 쌈" },
  { lead: "3개월 뒤 궁·종묘 5곳 주 1회 시범 여부", body: "월 1회보다 1.34억 원 절감 (2025년 기준)" },
  { lead: "임시 무료 개방 공지 공유", body: "행사 14일 전까지 인력 담당에게 전달" },
  { lead: "왕릉 영업일 최소 1명 유지와 필요성 확인", body: "1월 과배치 추정 약 0.63억 원" },
  { lead: "임시 휴관일 인원의 업무", body: "관람객 응대 대신 정비·관리·직원 교육 (팀 방침)" },
], L, 2.3, 6.0, 0.86, { numbered: true });
header(s, "다음 할 일", 6.95, 1.75, 5.83);
ctable(s, ["시점", "할 일"], [
  [B("매월 말"), "다음 달 권고표를 다시 계산 (2월분은 2026-01-31)"],
  [B("바로"), "공지된 무료 개방일 증원, 마지막 수요일 하한 적용"],
  [B("3개월 뒤"), "궁·종묘 주 1회 시범, 근무자 부담과 실제 절감 비교"],
  [B("2026-05-27 전"), "수요일 무료 개방 확대 개소부터 달력 규칙 변경"],
  [B("상시"), "종묘대제 같은 정기 행사 열 추가, 공지 이력 수집"],
], { x: 6.95, y: 2.25, w: 5.83, colW: [1.55, 4.28], rowH: [0.34, 0.8, 0.8, 0.8, 0.8, 0.8], fontSize: 12, name: "next table" });
source(s, "출처: 운영방안_비교.csv, 운영방안_비교_구분별.csv, 권고표_2026_01_최종.csv, 가이드 7쪽");

// ---------- 저장 + 한국어 줄바꿈 설정 ----------
(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  // 한국어: 어절 단위 줄바꿈(eaLnBrk="0"), 언어 ko-KR
  const zip = await JSZip.loadAsync(fs.readFileSync(OUT));
  const names = Object.keys(zip.files).filter((n) => /^ppt\/(slides|slideLayouts|slideMasters)\/[^/]+\.xml$/.test(n));
  for (const n of names) {
    let x = await zip.file(n).async("string");
    x = x.replace(/<a:pPr(?![^>]*eaLnBrk)([^>]*?)(\/?)>/g, '<a:pPr eaLnBrk="0"$1$2>');
    x = x.replace(/<a:p>(?!<a:pPr)/g, '<a:p><a:pPr eaLnBrk="0"/>');
    x = x.replace(/lang="en-US"/g, 'lang="ko-KR"');
    zip.file(n, x);
  }
  fs.writeFileSync(OUT, await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" }));
  console.log("wrote", OUT);
})();
