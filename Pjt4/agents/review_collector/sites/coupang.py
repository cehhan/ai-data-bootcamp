"""쿠팡 전용 어댑터 — /next-api/review 사용"""
import json, random, re, sys
from datetime import datetime, timezone, timedelta
from common import start_browser, page_fetch, Store, EXIT_BLOCKED, EXIT_UNSUPPORTED

SIZE = 30
KST = timezone(timedelta(hours=9))
FIELDS = ["product_id", "review_id", "item_name", "rating", "title", "content", "survey",
          "helpful_count", "photo_count", "vendor", "review_date"]


def row(c):
    survey = "; ".join(f"{a.get('question', '')}: {a.get('answer', '')}" for a in (c.get("reviewSurveyAnswers") or []))
    return {
        "product_id": c["productId"],
        "review_id": c["reviewId"],
        "item_name": c.get("itemName", ""),
        "rating": c.get("rating"),
        "title": (c.get("title") or "").strip(),
        "content": (c.get("content") or "").strip(),
        "survey": survey,
        "helpful_count": c.get("helpfulTrueCount", 0),
        "photo_count": len(c.get("attachments") or []),
        "vendor": (c.get("vendorName") or "").replace("판매자: ", ""),
        "review_date": datetime.fromtimestamp(c["createdAt"] / 1000, KST).strftime("%Y-%m-%d %H:%M"),
    }


async def run(a):
    m = re.search(r"/vp/products/(\d+)", a.url)
    if not m:
        print(f"[coupang] 상품 URL이 아닙니다: {a.url}")
        return EXIT_UNSUPPORTED
    pid = m.group(1)
    store = Store(f"coupang_reviews_{pid}", FIELDS)
    state = store.state.setdefault("next_page", {}), store.state.setdefault("done", [])
    next_page, done = state
    rating_keys = [""] if a.ratings == "all" else a.ratings.split(",")

    # 진행 상태 키: 최신순은 "all"/"1".. , 다른 정렬은 접두어로 구분
    def skey(r):
        k = r or "all"
        return k if a.sort == "DATE_DESC" else f"{a.sort}:{k}"

    todo = [r for r in rating_keys if skey(r) not in done]
    if not todo:
        print(f"[coupang:{pid}] 이미 모든 필터 수집 완료 ({len(store.seen)}건)")
        store.close()
        return 0

    browser = await start_browser()
    tab = await browser.get(a.url)
    await tab.sleep(random.uniform(6, 9))
    await tab.scroll_down(1500)
    await tab.sleep(random.uniform(2, 4))

    pages_left, added, blocked = a.max_pages, 0, None
    try:
        for r in todo:
            page = next_page.get(skey(r), 1)
            while pages_left > 0:
                url = (f"/next-api/review?productId={pid}&page={page}&size={SIZE}"
                       f"&sortBy={a.sort}&ratingSummary=true&ratings={r}&market=")
                status, body = await page_fetch(tab, url)
                if status != 200:
                    blocked = status
                    break
                contents = ((json.loads(body).get("rData") or {}).get("paging") or {}).get("contents") or []
                if not contents:
                    done.append(skey(r))
                    break
                added += store.add(row(c) for c in contents)
                page += 1
                pages_left -= 1
                next_page[skey(r)] = page
                store.save()
                await tab.sleep(random.uniform(a.delay, a.delay * 2))
            if blocked or pages_left <= 0:
                break
    finally:
        store.close()
        browser.stop()

    print(f"[coupang:{pid}] 이번 실행 +{added}건, 누적 {len(store.seen)}건, 진행={next_page}, 완료 필터={done}")
    print(f"[coupang:{pid}] file={store.csv_path}")
    if blocked is not None:
        print(f"[coupang:{pid}] 응답 {blocked} — 차단 신호로 보고 중단. 몇 시간 이상 지난 뒤 다시 실행하세요.")
        return EXIT_BLOCKED
    return 0
