// drafts/01~07_*.md 를 합쳐 Word 보고서를 만든다.
// 사용: (agent 폴더에서) node tools/build_report_docx.js drafts/report_v9.docx (버전을 올려 저장)
// 서식은 CLAUDE.md 「출력 형식: Word」를 따른다. 각 초안의 「### 자기 점검표」 이후는 넣지 않는다.
const fs = require("fs");
const path = require("path");
const d = require("docx");
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, HeadingLevel, AlignmentType,
  WidthType, ShadingType, BorderStyle, Footer, PageNumber, LevelFormat, PageOrientation, FootnoteReferenceRun, LineRuleType } = d;
const AUTO = LineRuleType.AUTO;

const OUT = process.argv[2] || "drafts/report.docx";
const FILES = ["01_권고요약.md", "02_질문과범위.md", "03_선택과이유.md", "04_근거와재현조건.md",
  "05_오차분석과한계.md", "06_추가발견과다음할일.md", "07_부록.md"].map((f) => path.join("drafts", f));

// 영문은 Malgun Gothic, 한글은 맑은 고딕 이름으로 지정 (Windows Word에서 두 이름 모두 같은 글꼴로 찾음)
const FONT = { ascii: "Malgun Gothic", hAnsi: "Malgun Gothic", eastAsia: "맑은 고딕", cs: "Malgun Gothic" };
const MONO = { ascii: "Consolas", hAnsi: "Consolas", eastAsia: "맑은 고딕", cs: "Consolas" };  // 코드 글꼴(한글 파일명은 맑은 고딕)
const NAVY = "1F3864", BLUE = "2A78D6", QBOX = "E8F0FB";
const MARGIN = 1020;                 // 18mm
const A4W = 11906, A4H = 16838;
const WP = A4W - 2 * MARGIN;         // 세로 본문 폭 9,866 DXA
const WL = A4H - 2 * MARGIN;         // 가로 본문 폭 14,798 DXA
const BODY = 20;                     // 10pt
const LINE = 312;                    // 1.3줄 (2026-10-16 사용자 요청: 1.5줄에서 좁힘)

// ---------- 각주 ----------
const footnotes = {};
let fnNext = 1;
const usedFn = new Set();
const fnByKey = {};
const TABLE_LOG = [];
// 표지 아래 정보 (빈칸은 [팀원 결과 대기…] 형식이라 노란 형광펜으로 표시됨)
const TITLE_META = ["데이터 분석 부트캠프 프로젝트 3", "C2 팀 · 최의환, 최주영, 정호성", "2026년 10월 19일"];

// ---------- 인라인: **굵게**, `코드`, [^n] 각주, [팀원 결과 대기…] 형광펜 ----------
function runs(text, base = {}, fnMap = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\[\^\d+\]|\[팀원 결과 대기[^\]]*\])/g;
  let last = 0, m;
  const push = (t, extra = {}) => t && out.push(new TextRun({ text: t, font: FONT, ...base, ...extra }));
  while ((m = re.exec(text))) {
    push(text.slice(last, m.index));
    const t = m[0];
    if (t.startsWith("**")) {
      // 굵은 구간 안의 `코드` 도 처리
      const inner = t.slice(2, -2);
      inner.split(/(`[^`]+`)/).forEach((s) => {
        if (s.startsWith("`")) push(s.slice(1, -1), { bold: true, font: MONO });
        else push(s, { bold: true });
      });
    } else if (t.startsWith("`")) push(t.slice(1, -1), { font: MONO, size: (base.size || BODY) - 2 });
    else if (t.startsWith("[^")) {
      const id = fnMap[t.slice(2, -1)];
      if (id && !usedFn.has(id)) { usedFn.add(id); out.push(new FootnoteReferenceRun(id)); }
      else if (id) out.push(new TextRun({ text: String(id), superScript: true, font: FONT, size: base.size || BODY }));
    } else push(t, { highlight: "yellow", highlightComplexScript: false });
    last = m.index + t.length;
  }
  push(text.slice(last));
  return out;
}

const para = (text, fnMap, opt = {}) => new Paragraph({
  spacing: { after: 100, line: LINE, lineRule: AUTO }, ...opt, children: runs(text, opt.run || {}, fnMap) });

function qaBox(lines, fnMap) {
  const box = { shading: { type: ShadingType.CLEAR, fill: QBOX, color: "auto" },
    border: { left: { style: BorderStyle.SINGLE, size: 24, color: BLUE, space: 8 } }, indent: { left: 160, right: 160 } };
  return lines.map((l, i) => {
    const mm = l.match(/^\*\*(질문|답)\*\*\s*(.*)$/);
    const label = mm ? mm[1] : "", body = mm ? mm[2] : l;
    return new Paragraph({ ...box, keepNext: i < lines.length - 1,
      spacing: { before: i === 0 ? 80 : 0, after: i === lines.length - 1 ? 240 : 0, line: LINE, lineRule: AUTO },
      children: [new TextRun({ text: label + "  ", bold: true, color: BLUE, font: FONT }), ...runs(body, label === "답" ? { bold: true } : {}, fnMap)] });
  });
}

// ---------- 표 ----------
function textLen(s) { // 글자 폭(단위 = 0.5em). 맑은 고딕 굵게 실측 기준
  s = s.replace(/\*\*|`/g, "");
  let n = 0;
  for (const ch of s) {
    if (/[\u1100-\uFFDC]/.test(ch)) n += 2;          // 한글·전각 1em
    else if (/[WM%]/.test(ch)) n += 2;                 // 넓은 글자
    else if (/[A-Z]/.test(ch)) n += 1.4;               // 대문자 약 0.7em
    else if (/[0-9]/.test(ch)) n += 1.17;              // 숫자 약 0.58em
    else if (/[ .,:;'|il()\[\]]/.test(ch)) n += 0.7; // 좁은 글자
    else n += 1.1;
  }
  return n;
}
function table(lines, fnMap, width) {
  const split = (l) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
  const head = split(lines[0]);
  const align = split(lines[1]).map((a) => a.endsWith(":"));
  const rows = lines.slice(2).map(split);
  const n = head.length;
  const big = n >= 20;                       // 31일 표
  const size = big ? 13 : n >= 9 ? 14 : 16;  // 6.5pt / 7pt / 8pt
  // 열 폭 (2026-10-16 피드백: 머리글 행은 가능한 한 한 줄로)
  //  1) 머리글 전체 길이와 숫자 열의 가장 긴 값이 줄바꿈 없이 들어가는 폭을 최소 폭으로 잡는다
  //  2) 안 들어가면 머리글 글자를 1pt씩(최대 1.5pt) 줄여 다시 시도한다
  //  3) 그래도 안 되면 글자 열의 본문만 줄바꿈되도록 줄이고, 머리글은 낱말 단위로 줄바꿈한다
  const unit = size * 5.0;                    // textLen 1단위 폭(DXA): 맑은 고딕 실측 약 4.8 x 글자 크기
  const pad = big ? 80 : 170;
  const maxWord = (s) => Math.max(...s.replace(/\*\*|`/g, "").split(/\s+/).map(textLen), 1);
  const bodyMin = head.map((h, i) => {
    const cells = rows.map((r) => r[i] || "");
    return Math.max(...cells.map(align[i] ? textLen : maxWord), 1) * unit + pad;
  });
  const want = head.map((h, i) => Math.max(...[h, ...rows.map((r) => r[i] || "")].map(textLen)) * unit + pad);
  let hsize = size, need = null;
  for (const hs of [size, size - 1, size - 2, size - 3]) {
    const hdr = head.map((h) => textLen(h) * hs * 5.4 + pad);   // 굵은 글씨 실측 약 5.1
    const mins = head.map((h, i) => Math.max(hdr[i], bodyMin[i]));
    if (mins.reduce((a, b) => a + b, 0) <= width) { hsize = hs; need = mins; break; }
  }
  let widths;
  if (need) {
    const sumMin = need.reduce((a, b) => a + b, 0);
    const flex = need.map((m, i) => Math.max(want[i] - m, 0)), fsum = flex.reduce((a, b) => a + b, 0);
    widths = fsum > 0 ? need.map((m, i) => m + Math.min(1, (width - sumMin) / fsum) * flex[i]) : need.slice();
    const used = widths.reduce((a, b) => a + b, 0);
    if (used < width) widths = widths.map((w) => w * width / used);
  } else {
    hsize = size - 2;
    TABLE_LOG.push("머리글 줄바꿈 남음: " + head.join(" | "));
    const mins = head.map((h, i) => Math.max(maxWord(h) * unit + pad, bodyMin[i]));
    const numSum = mins.filter((m, i) => align[i]).reduce((a, b) => a + b, 0);
    const txtSum = mins.filter((m, i) => !align[i]).reduce((a, b) => a + b, 0) || 1;
    const k = Math.max(width - numSum, 0) / txtSum;
    widths = mins.map((m, i) => (align[i] && numSum < width ? m : m * (numSum < width ? k : width / (numSum + txtSum))));
  }
  if (hsize !== size && need) TABLE_LOG.push(`머리글 ${hsize / 2}pt로 줄임: ` + head.join(" | "));
  widths = widths.map(Math.floor);
  widths[n - 1] = width - widths.slice(0, -1).reduce((a, b) => a + b, 0);
  const line = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
  const none = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const cell = (t, i, isHead, isTotal) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA },
    margins: { top: 40, bottom: 40, left: big ? 30 : 70, right: big ? 30 : 70 },
    shading: isHead ? { type: ShadingType.CLEAR, fill: NAVY, color: "auto" } : isTotal ? { type: ShadingType.CLEAR, fill: "EEF2F7", color: "auto" } : undefined,
    borders: { top: none, left: none, right: none, bottom: line },
    verticalAlign: d.VerticalAlign.CENTER,
    children: [new Paragraph({ alignment: align[i] ? AlignmentType.RIGHT : AlignmentType.LEFT, spacing: { line: 240, lineRule: AUTO },
      children: runs(t, isHead ? { color: "FFFFFF", bold: true, size: hsize } : { size }, fnMap) })],
  });
  const trs = [new TableRow({ tableHeader: true, cantSplit: true, children: head.map((h, i) => cell(h, i, true)) })];
  rows.forEach((r) => {
    const tot = /^\*\*(합계|전체 절감)/.test(r[0] || "");
    while (r.length < n) r.push("");
    trs.push(new TableRow({ cantSplit: true, children: r.slice(0, n).map((t, i) => cell(t, i, false, tot)) }));
  });
  return [new Table({ width: { size: width, type: WidthType.DXA }, columnWidths: widths, rows: trs }),
    new Paragraph({ spacing: { after: 80 }, children: [] })];
}

// ---------- 그림 ----------
function image(rel, mdDir, width) {
  const p = path.join(mdDir, rel);
  const buf = fs.readFileSync(p);
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  const px = Math.floor((width / 1440) * 96);  // 본문 폭(px, 96dpi)
  return new Paragraph({ alignment: AlignmentType.CENTER, keepNext: false, spacing: { before: 120, after: 200, line: 240, lineRule: AUTO },
    children: [new ImageRun({ type: "png", data: buf, transformation: { width: px, height: Math.round((px * h) / w) } })] });
}

// ---------- md → 블록 ----------
const sections = [];   // { landscape, children }
let cur = { landscape: false, children: [] };
sections.push(cur);
const newSection = (landscape) => { cur = { landscape, children: [] }; sections.push(cur); };

let firstH1 = true;
FILES.forEach((file, fi) => {
  let md = fs.readFileSync(file, "utf8").replace(/\r/g, "");
  md = md.split(/\n### 자기 점검표/)[0];
  // 각주 정의 수집
  const fnMap = {};
  md = md.replace(/^\[\^(\d+)\]:\s*(.+)$/gm, (_, k, body) => {
    // 같은 출처(같은 주소)의 각주는 하나로 합치고 번호를 다시 씀 (2026-10-16 피드백)
    const key = (body.match(/https?:\/\/\S+/) || [body])[0];
    if (fnByKey[key]) { fnMap[k] = fnByKey[key]; return ""; }
    const id = fnNext++; fnMap[k] = id; fnByKey[key] = id;
    footnotes[id] = { children: [new Paragraph({ children: runs(body, { size: 15 }) })] };
    return "";
  });
  const lines = md.split("\n");
  const W = () => (cur.landscape ? WL : WP);
  let i = 0, hrCount = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (!l.trim()) { i++; continue; }
    let m;
    if ((m = l.match(/^# (.+)$/))) {
      const t = m[1];
      if (fi === 0 && i === lines.findIndex((x) => x.startsWith("# "))) {
        // 표지 (2026-10-16 피드백: 제목은 첫 쪽에 따로). 「제목: 부제」를 나눠 가운데 정렬
        const [a, b] = t.split(/:\s*/);
        cur.isTitle = true;
        cur.children.push(new Paragraph({ heading: HeadingLevel.TITLE, alignment: AlignmentType.CENTER, spacing: { after: 240 },
          children: [new TextRun({ text: a, font: FONT, size: 48 })] }));
        if (b) cur.children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: NAVY, space: 12 } },
          children: [new TextRun({ text: b, font: FONT, size: 28, color: BLUE, bold: true })] }));
        TITLE_META.forEach((m, k) => cur.children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: k ? 60 : 240, after: 60 },
          children: runs(m, { size: 22, color: "444444" }) })));
        newSection(false); cur.numberStart = true;
      } else {
        // v9 (2026-10-19): 본문 쪽수를 줄이려고 절마다 새 쪽을 열지 않고 이어 쓴다. 부록만 새 쪽에서 시작.
        const brk = !firstH1 && /^부록/.test(t);
        cur.children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: brk, keepNext: true,
          spacing: !firstH1 && !brk ? { before: 480 } : undefined,
          children: [new TextRun({ text: t, font: FONT })] }));
        firstH1 = false;
      }
      i++; continue;
    }
    if ((m = l.match(/^(#{2,3}) (.+)$/))) {
      const t = m[2];
      if (t.startsWith("표 B-2")) newSection(true);            // 31일 표는 가로 쪽
      if (t.startsWith("부록 C")) newSection(false);
      cur.children.push(new Paragraph({ heading: m[1] === "##" ? HeadingLevel.HEADING_2 : HeadingLevel.HEADING_3,
        keepNext: true, children: runs(t, {}, fnMap) }));
      i++; continue;
    }
    if (l.startsWith(">")) {
      const block = [];
      while (i < lines.length && lines[i].startsWith(">")) { block.push(lines[i].replace(/^>\s?/, "")); i++; }
      if (block[0].startsWith("**질문**")) cur.children.push(...qaBox(block, fnMap));
      else block.forEach((b) => cur.children.push(new Paragraph({
        shading: { type: ShadingType.CLEAR, fill: "F4F6F9", color: "auto" }, indent: { left: 160, right: 160 },
        spacing: { before: 60, after: 120, line: 300, lineRule: AUTO }, children: runs(b, { size: 17 }, fnMap) })));
      continue;
    }
    if (l.startsWith("|")) {
      const block = [];
      while (i < lines.length && lines[i].startsWith("|")) { block.push(lines[i]); i++; }
      cur.children.push(...table(block, fnMap, W()));
      continue;
    }
    if ((m = l.match(/^!\[[^\]]*\]\(([^)]+)\)/))) { cur.children.push(image(m[1], path.dirname(file), W())); i++; continue; }
    if (/^---+$/.test(l.trim())) {
      // ①: 첫 구분선 뒤(도표 1·권고표 안내)는 다음 쪽으로 → ① 본문을 한 쪽에 둠
      hrCount++;
      if (fi === 0 && hrCount === 1) cur.children.push(new Paragraph({ pageBreakBefore: true, children: [] }));
      i++; continue;
    }
    if ((m = l.match(/^- (.+)$/))) {
      cur.children.push(new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 60, line: LINE, lineRule: AUTO }, children: runs(m[1], {}, fnMap) }));
      i++; continue;
    }
    if ((m = l.match(/^(\d+)\. (.+)$/))) {
      cur.children.push(new Paragraph({ indent: { left: 360, hanging: 300 }, spacing: { after: 60, line: LINE, lineRule: AUTO },
        children: [new TextRun({ text: m[1] + ".  ", font: FONT, bold: true }), ...runs(m[2], {}, fnMap)] }));
      i++; continue;
    }
    cur.children.push(para(l, fnMap));
    i++;
  }
});

const footer = () => new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: "666666" })] })] });

const doc = new Document({
  creator: "궁·능 인력 배치 팀", title: "궁·능 인력 배치 2026",
  styles: {
    default: { document: { run: { font: FONT, size: BODY }, paragraph: { spacing: { line: LINE, lineRule: AUTO } } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 34, bold: true, color: NAVY }, paragraph: { spacing: { after: 60 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 30, bold: true, color: NAVY },
        paragraph: { spacing: { before: 0, after: 200 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: NAVY, space: 4 } } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 24, bold: true, color: NAVY }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 21, bold: true, color: "333333" }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 360, hanging: 240 } } } }] }] },
  footnotes,
  sections: sections.filter((s) => s.children.length).map((s) => ({
    properties: { page: { size: { width: A4W, height: A4H, orientation: s.landscape ? PageOrientation.LANDSCAPE : PageOrientation.PORTRAIT },
      margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN }, ...(s.numberStart ? { pageNumbers: { start: 1 } } : {}) }, ...(s.isTitle ? { verticalAlign: d.VerticalAlign.CENTER } : {}) },
    footers: s.isTitle ? {} : { default: footer() },
    children: s.children,
  })),
});

Packer.toBuffer(doc).then((b) => { fs.writeFileSync(OUT, b); console.log("wrote", OUT, b.length, "bytes"); TABLE_LOG.forEach((l) => console.log(l)); });
