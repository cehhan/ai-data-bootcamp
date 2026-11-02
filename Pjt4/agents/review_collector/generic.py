"""범용 어댑터 — 사이트를 몰라도 리뷰 API를 자동 탐지해 수집

1. 실제 Chrome으로 상품 페이지를 열고, 스크롤 + '리뷰/후기/상품평' 탭 클릭
2. 그동안 오간 JSON 응답 중 '리뷰 목록처럼 생긴 배열'(본문 텍스트 + 별점 필드)을 점수화해 고름
3. 그 요청의 페이지 파라미터(page/pageNo/offset...)를 찾아 증가시키며 같은 탭에서 재요청
4. 필드명은 휴리스틱으로 매핑(본문/별점/제목/날짜/옵션/ID). 작성자 등 개인정보 필드는 저장하지 않음
"""
import hashlib, json, random, re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from nodriver import cdp
from common import start_browser, page_fetch, Store, BLOCK_STATUSES, EXIT_BLOCKED, EXIT_UNSUPPORTED

KST = timezone(timedelta(hours=9))
FIELDS = ["site", "product_key", "review_id", "rating", "title", "content", "option",
          "helpful_count", "review_date"]

RATING_K = re.compile(r"(rating|score|star|grade|point|rate|평점|별점)", re.I)
TEXT_K = re.compile(r"(content|review|text|body|comment|message|desc|내용)", re.I)
TITLE_K = re.compile(r"(title|subject|headline|제목)", re.I)
DATE_K = re.compile(r"(date|created|regist|reg_?dt|written|time|_at$|At$|dt$|ymd)", re.I)
ID_K = re.compile(r"(review_?id|review_?no|review_?seq|^id$|\.id$|_id$|Id$|^no$|seq$)", re.I)
OPTION_K = re.compile(r"(option|item_?name|variant|sku|옵션)", re.I)
HELPFUL_K = re.compile(r"(helpful|like|recommend|useful|good_?c(ou)?nt)", re.I)
PII_K = re.compile(r"(nick|writer|author|user|member|email|phone|profile|^name$|\.name$|ip$)", re.I)
PAGE_KEYS = ["page", "pageNo", "pageNum", "page_no", "pageNumber", "currentPage", "pageIndex", "p", "pg"]
OFFSET_KEYS = ["offset", "start", "from", "skip"]
SKIP_HEADERS = {"cookie", "user-agent", "referer", "origin", "host", "content-length",
                "accept-encoding", "connection"}

CLICK_REVIEW_TAB = r"""
(() => {
  const re = /^\s*(리뷰|상품평|상품리뷰|구매후기|후기|상품후기|고객리뷰|reviews?)(?![가-힣A-Za-z])/i;
  const els = [...document.querySelectorAll('a, button, li, [role=tab], span')]
    .filter(e => e.offsetParent && (e.innerText || '').trim().length <= 20 && re.test(e.innerText || ''));
  if (!els.length) return '';
  els[0].scrollIntoView({block: 'center'}); els[0].click();
  return els[0].innerText.trim();
})()
"""


# ---------- 리뷰 목록 탐지 ----------

def flat(d, prefix="", depth=0):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict) and depth < 2:
            out.update(flat(v, key + ".", depth + 1))
        elif not isinstance(v, (dict, list)):
            out[key] = v
    return out


def lists_in(o, path=()):
    if isinstance(o, list) and len(o) >= 1 and all(isinstance(x, dict) for x in o[:5]):
        yield path, o
    if isinstance(o, dict):
        for k, v in o.items():
            yield from lists_in(v, path + (k,))


def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def map_fields(items):
    rows = [flat(x) for x in items[:20]]
    keys = {k for r in rows for k in r}
    col = {k: [r.get(k) for r in rows if r.get(k) not in (None, "")] for k in keys}

    def avg_len(k):
        vs = [v for v in col[k] if isinstance(v, str)]
        return sum(map(len, vs)) / len(vs) if vs and len(vs) >= len(rows) * 0.3 else 0

    str_keys = [k for k in keys if avg_len(k) > 0 and not PII_K.search(k)
                and not any(str(v).startswith(("http", "//")) for v in col[k][:3])]
    text = max((k for k in str_keys if TEXT_K.search(k)), key=avg_len, default=None)
    if text is None or avg_len(text) < 10:
        text = max(str_keys, key=avg_len, default=None)
    if text is None or avg_len(text) < 10:
        return None

    def pick(rx, pred):
        cands = [k for k in keys if rx.search(k) and not PII_K.search(k)
                 and col[k] and pred(col[k]) and k != text]
        return min(cands, key=len, default=None)

    rating = pick(RATING_K, lambda vs: all(is_num(v) or str(v).replace(".", "", 1).isdigit() for v in vs)
                  and all(0 <= float(v) <= 100 for v in vs))
    rid = pick(ID_K, lambda vs: len(set(map(str, vs))) == len(vs))
    return {
        "text": text, "rating": rating, "id": rid,
        "title": pick(TITLE_K, lambda vs: all(isinstance(v, str) for v in vs)),
        "date": pick(DATE_K, lambda vs: True),
        "option": pick(OPTION_K, lambda vs: all(isinstance(v, str) for v in vs)),
        "helpful": pick(HELPFUL_K, lambda vs: all(is_num(v) for v in vs)),
    }


def score(url, path, items, m):
    s = len(items) + (20 if m["rating"] else 0) + (5 if m["date"] else 0)
    s += 30 if re.search(r"review|comment|후기|평", url + "/".join(map(str, path)), re.I) else 0
    return s


def get_path(o, path):
    for k in path:
        o = o[k] if isinstance(o, dict) else None
        if o is None:
            return None
    return o


# ---------- 페이지 파라미터 ----------

def find_paging(url, post):
    q = dict(parse_qsl(urlparse(url).query, keep_blank_values=True))
    body = None
    if post:
        try:
            body = json.loads(post)
        except ValueError:
            body = None
    for where, src in (("query", q), ("json", body if isinstance(body, dict) else {})):
        for k in PAGE_KEYS:
            if k in src and str(src[k]).isdigit():
                return {"where": where, "key": k, "kind": "page", "start": int(src[k])}
        for k in OFFSET_KEYS:
            if k in src and str(src[k]).isdigit():
                return {"where": where, "key": k, "kind": "offset", "start": int(src[k])}
    return None


def build_request(spec, value):
    url, post = spec["url"], spec.get("post")
    p = spec["paging"]
    if p["where"] == "query":
        u = urlparse(url)
        q = parse_qsl(u.query, keep_blank_values=True)
        q = [(k, str(value) if k == p["key"] else v) for k, v in q]
        url = urlunparse(u._replace(query=urlencode(q)))
    else:
        b = json.loads(post)
        b[p["key"]] = value if isinstance(b[p["key"]], int) else str(value)
        post = json.dumps(b)
    return url, post


# ---------- 변환 ----------

def fmt_date(v):
    if is_num(v) or (isinstance(v, str) and v.isdigit() and len(v) >= 10):
        t = float(v)
        if t > 1e11:
            t /= 1000
        try:
            return datetime.fromtimestamp(t, KST).strftime("%Y-%m-%d %H:%M")
        except (OverflowError, OSError, ValueError):
            return str(v)
    return str(v or "")


def to_row(site, pkey, item, m):
    f = flat(item)
    text = str(f.get(m["text"]) or "").strip()
    rid = f.get(m["id"]) if m["id"] else None
    if rid in (None, ""):
        rid = "h" + hashlib.md5(f"{text}|{f.get(m['date'])}".encode()).hexdigest()[:16]
    g = lambda k: f.get(m[k], "") if m[k] else ""
    return {"site": site, "product_key": pkey, "review_id": rid, "rating": g("rating"),
            "title": str(g("title")).strip(), "content": text, "option": g("option"),
            "helpful_count": g("helpful"), "review_date": fmt_date(g("date"))}


def product_key(url):
    u = urlparse(url)
    q = {k.lower(): v for k, v in parse_qsl(u.query)}
    for k in ("productno", "goodsno", "goodscode", "itemid", "item_id", "prdno", "productid", "pid", "no"):
        if q.get(k, "").isdigit():
            return q[k]
    nums = re.findall(r"\d{4,}", u.path)
    return nums[-1] if nums else hashlib.md5(url.encode()).hexdigest()[:10]


# ---------- 탐지 실행 ----------

async def discover(tab, url):
    reqs, resp_ids = {}, []
    tab.add_handler(cdp.network.RequestWillBeSent, lambda e: reqs.__setitem__(e.request_id, e.request))
    tab.add_handler(cdp.network.ResponseReceived, lambda e: resp_ids.append(e.request_id)
                    if e.type_ in (cdp.network.ResourceType.XHR, cdp.network.ResourceType.FETCH)
                    or "json" in (e.response.mime_type or "") else None)
    await tab.send(cdp.network.enable())
    await tab.get(url)
    await tab.sleep(random.uniform(6, 9))
    for _ in range(4):
        await tab.scroll_down(1200)
        await tab.sleep(random.uniform(1, 2))
    clicked = await tab.evaluate(CLICK_REVIEW_TAB)
    print(f"   review tab click: {clicked or '(없음)'}")
    await tab.sleep(random.uniform(3, 5))
    for _ in range(4):
        await tab.scroll_down(1200)
        await tab.sleep(random.uniform(1, 2))

    best = None
    for rid in resp_ids:
        req = reqs.get(rid)
        if req is None:
            continue
        try:
            body, b64 = await tab.send(cdp.network.get_response_body(rid))
            data = json.loads(body)
        except Exception:
            continue
        for path, items in lists_in(data):
            m = map_fields(items)
            if not m:
                continue
            s = score(req.url, path, items, m)
            if best is None or s > best[0]:
                best = (s, {"url": req.url, "method": req.method,
                            "post": getattr(req, "post_data", None),
                            "headers": {k: v for k, v in (req.headers or {}).items()
                                        if k.lower() not in SKIP_HEADERS and not k.startswith(":")},
                            "path": list(path), "map": m}, items)
    if not best:
        return None, None
    spec, items = best[1], best[2]
    spec["paging"] = find_paging(spec["url"], spec["post"])
    return spec, items


async def run(a):
    site = (urlparse(a.url).hostname or "").removeprefix("www.")
    pkey = product_key(a.url)
    name = f"reviews_{site.replace('.', '_')}_{pkey}"
    store = Store(name, FIELDS)
    st = store.state

    if st.get("done"):
        print(f"[{site}:{pkey}] 이미 수집 완료 ({len(store.seen)}건)")
        store.close()
        return 0

    browser = await start_browser()
    tab = await browser.get("about:blank")
    added, status = 0, 200
    try:
        spec, first = await discover(tab, a.url)
        if spec is None:
            print(f"[{site}:{pkey}] 리뷰 JSON API를 찾지 못했습니다(서버 렌더링 HTML이거나 로그인 필요 가능성).")
            return EXIT_UNSUPPORTED
        m = spec["map"]
        print(f"[{site}:{pkey}] API={spec['method']} {spec['url'][:150]}")
        print(f"[{site}:{pkey}] 필드매핑={m} paging={spec['paging']}")
        st["spec"] = {k: spec[k] for k in ("url", "method", "path", "map", "paging")}

        if not spec["paging"]:
            added += store.add(to_row(site, pkey, x, m) for x in first)
            st["done"] = True
            print(f"[{site}:{pkey}] 페이지 파라미터를 찾지 못해 첫 응답({len(first)}건)만 저장")
            return 0

        p = spec["paging"]
        value = st.get("next", p["start"])
        step = 1 if p["kind"] == "page" else len(first)
        for _ in range(a.max_pages):
            url, post = build_request(spec, value)
            status, text = await page_fetch(tab, url, spec["method"], post, spec["headers"])
            if status != 200:
                break
            items = get_path(json.loads(text), spec["path"]) or []
            if not items:
                st["done"] = True
                break
            n = store.add(to_row(site, pkey, x, m) for x in items)
            added += n
            value += step
            st["next"] = value
            store.save()
            if n == 0:  # 새 리뷰가 하나도 없으면 페이지 파라미터가 무시되는 것 → 종료
                st["done"] = True
                break
            await tab.sleep(random.uniform(a.delay, a.delay * 2))
    finally:
        store.close()
        browser.stop()

    print(f"[{site}:{pkey}] 이번 실행 +{added}건, 누적 {len(store.seen)}건, next={st.get('next')}, done={bool(st.get('done'))}")
    print(f"[{site}:{pkey}] file={store.csv_path}")
    if status in BLOCK_STATUSES:
        print(f"[{site}:{pkey}] 응답 {status} — 차단 신호로 보고 중단. 몇 시간 뒤 다시 실행하세요.")
        return EXIT_BLOCKED
    if status != 200:
        print(f"[{site}:{pkey}] 응답 {status} — 재요청 실패(교차 출처 API·토큰 만료 등). 첫 페이지 탐지는 성공했을 수 있음.")
        return EXIT_UNSUPPORTED
    return 0
