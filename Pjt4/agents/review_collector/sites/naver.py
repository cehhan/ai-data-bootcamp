"""네이버 브랜드스토어/스마트스토어 전용 어댑터

상품 페이지를 열고 '리뷰 N' 탭을 눌러 페이지가 스스로 보내는 리뷰 요청(.../contents/reviews/query-pages)을
잡은 뒤, 같은 요청의 page 값만 올려 가며 탭 안에서 다시 보낸다. 작성자 등 개인정보 필드는 저장하지 않는다.
"""
import json, random, re
from datetime import datetime, timezone, timedelta
from nodriver import cdp
from common import start_browser, page_fetch, Store, BLOCK_STATUSES, EXIT_BLOCKED, EXIT_UNSUPPORTED

KST = timezone(timedelta(hours=9))
FIELDS = ["store", "product_no", "review_id", "rating", "content", "option", "review_type",
          "helpful_count", "photo_count", "review_date"]
REVIEW_API = re.compile(r"/contents/reviews/query-pages")
SKIP_HEADERS = {"cookie", "user-agent", "referer", "origin", "host", "content-length",
                "accept-encoding", "connection"}

CLICK_REVIEW_TAB = r"""
(() => {
  const re = /^\s*(리뷰|구매평|상품리뷰)(?![가-힣A-Za-z])/;
  const els = [...document.querySelectorAll('a, button, li, [role=tab]')]
    .filter(e => e.offsetParent && (e.innerText || '').trim().length <= 20 && re.test(e.innerText || ''));
  if (!els.length) return '';
  els[0].scrollIntoView({block: 'center'}); els[0].click();
  return els[0].innerText.trim().replace(/\s+/g, ' ');
})()
"""


def fmt_date(v):
    """Naver createDate is ISO (UTC 'Z' or with offset) -> KST 'YYYY-MM-DD HH:MM'."""
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return str(v or "")
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(KST).strftime("%Y-%m-%d %H:%M")


def row(store_id, pno, c):
    return {
        "store": store_id,
        "product_no": pno,
        "review_id": c.get("id"),
        "rating": c.get("reviewScore"),
        "content": (c.get("reviewContent") or "").strip(),
        "option": (c.get("productOptionContent") or "").strip(),
        "review_type": c.get("reviewType", ""),
        "helpful_count": c.get("helpCount", 0),
        "photo_count": len(c.get("reviewAttaches") or []),
        "review_date": fmt_date(c.get("createDate")),
    }


async def run(a):
    m = re.search(r"naver\.com/([^/]+)/products/(\d+)", a.url)
    if not m:
        print(f"[naver] 상품 URL이 아닙니다: {a.url}")
        return EXIT_UNSUPPORTED
    store_id, pno = m.group(1), m.group(2)
    store = Store(f"naver_reviews_{store_id}_{pno}", FIELDS)
    st = store.state
    if st.get("done"):
        print(f"[naver:{store_id}:{pno}] 이미 수집 완료 ({len(store.seen)}건)")
        store.close()
        return 0

    browser = await start_browser()
    tab = await browser.get("about:blank")
    # 리뷰 요청은 페이지 로드 중에 이미 나가고 응답 본문은 나중에 못 읽으므로, 요청(본문 포함)만 잡아 직접 다시 보낸다.
    # 이 요청에는 URL과 다른 내부 상품번호(originProductNo)와 판매자번호가 들어 있다.
    hits = []
    tab.add_handler(cdp.network.RequestWillBeSent,
                    lambda e: hits.append(e.request) if REVIEW_API.search(e.request.url) and e.request.post_data else None)
    added, status = 0, 200
    try:
        await tab.send(cdp.network.enable())
        await tab.get(a.url.split("?")[0])
        await tab.sleep(random.uniform(6, 9))
        for _ in range(3):
            await tab.scroll_down(1000)
            await tab.sleep(random.uniform(1, 2))
        clicked = await tab.evaluate(CLICK_REVIEW_TAB)
        print(f"   review tab click: {clicked or '(없음)'}")
        await tab.sleep(random.uniform(4, 6))

        if not hits:
            title = await tab.evaluate("document.title")
            print(f"[naver:{store_id}:{pno}] 리뷰 요청을 잡지 못했습니다. 페이지 제목={title!r} "
                  "(보안 확인/캡차 화면이면 차단 신호로 보고 중단)")
            return EXIT_UNSUPPORTED
        req = hits[0]
        body = json.loads(req.post_data)
        headers = {k: v for k, v in (req.headers or {}).items()
                   if k.lower() not in SKIP_HEADERS and not k.startswith(":")}
        body["reviewSearchSortType"] = "REVIEW_CREATE_DATE_DESC"  # 최신순
        print(f"[naver:{store_id}:{pno}] API=POST {req.url[:120]} 요청본문 키={sorted(body)} "
              f"originProductNo={body.get('originProductNo')}")
        total = None
        page = st.get("next", 1)
        for _ in range(a.max_pages):
            if total is not None and len(store.seen) >= total:
                break
            body["page"] = page
            status, text = await page_fetch(tab, req.url, "POST", json.dumps(body), headers)
            if status != 200:
                break
            data = json.loads(text)
            total = data.get("totalElements", total)
            contents = data.get("contents") or []
            if not contents:
                break
            n = store.add(row(store_id, pno, c) for c in contents)
            added += n
            page += 1
            st["next"] = page
            store.save()
            if n == 0:
                break
            await tab.sleep(random.uniform(a.delay, a.delay * 2))
        if status == 200 and (total is None or len(store.seen) >= total):
            st["done"] = True
    finally:
        store.close()
        browser.stop()

    print(f"[naver:{store_id}:{pno}] 이번 실행 +{added}건, 누적 {len(store.seen)}건, done={bool(st.get('done'))}")
    print(f"[naver:{store_id}:{pno}] file={store.csv_path}")
    if status in BLOCK_STATUSES:
        print(f"[naver:{store_id}:{pno}] 응답 {status} — 차단 신호로 보고 중단. 몇 시간 뒤 다시 실행하세요.")
        return EXIT_BLOCKED
    if status != 200:
        print(f"[naver:{store_id}:{pno}] 응답 {status} — 재요청 실패")
        return EXIT_UNSUPPORTED
    return 0
