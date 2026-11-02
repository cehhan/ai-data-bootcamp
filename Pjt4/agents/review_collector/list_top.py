"""쿠팡 카테고리/검색 목록에서 리뷰 수 상위 상품 추출 (쿠팡 전용)

usage:
  python list_top.py <카테고리 또는 검색 URL> [--top 3] [--pages 5]

- 목록 페이지(listSize=120)를 pages 장 넘기며 상품별 리뷰 수를 모은다.
- 결과: category_<key>_products.json 저장, 상위 N개를 JSON 한 줄로 stdout 출력
  (마지막 줄이 "TOP " 으로 시작)
"""
import argparse, json, os, random, re, sys
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import nodriver as uc
from common import DATA, start_browser

JS = r"""
(() => {
  const out = [];
  document.querySelectorAll('a[href*="/vp/products/"]').forEach(a => {
    const m = a.href.match(/\/vp\/products\/(\d+)/);
    if (!m) return;
    const li = a.closest('li') || a;
    const t = li.innerText || '';
    const rc = t.match(/\(([\d,]+)\)/);
    const img = li.querySelector('img[alt]');
    const name = (img && img.alt.trim()) || t.split('\n').find(s => s.trim().length > 8) || '';
    out.push({id: m[1], name, reviews: rc ? +rc[1].replace(/,/g, '') : null, ad: /광고/.test(t)});
  });
  return JSON.stringify(out);
})()
"""


def page_url(url, page):
    u = urlparse(url)
    q = {k: v[0] for k, v in parse_qs(u.query).items()}
    q.update({"page": str(page), "listSize": "120"})
    return urlunparse(u._replace(query=urlencode(q)))


def key_of(url):
    m = re.search(r"/np/categories/(\d+)", url)
    if m:
        return m.group(1)
    q = parse_qs(urlparse(url).query).get("q", ["search"])[0]
    return "search_" + re.sub(r"\W+", "_", q)


async def main(a):
    browser = await start_browser()
    tab = await browser.get("https://www.coupang.com/")
    await tab.sleep(random.uniform(3, 5))
    allp = {}
    for p in range(1, a.pages + 1):
        tab = await browser.get(page_url(a.url, p))
        await tab.sleep(random.uniform(5, 8))
        for _ in range(6):
            await tab.scroll_down(1500)
            await tab.sleep(random.uniform(0.7, 1.5))
        items = json.loads(await tab.evaluate(JS))
        print(f"page {p}: {len(items)} items", file=sys.stderr)
        if not items:
            break
        for it in items:
            cur = allp.get(it["id"])
            if cur is None or (it["reviews"] or 0) > (cur["reviews"] or 0):
                allp[it["id"]] = it
    browser.stop()

    ranked = sorted(allp.values(), key=lambda x: x["reviews"] or 0, reverse=True)
    out = os.path.join(DATA, f"category_{key_of(a.url)}_products.json")
    json.dump(ranked, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"saved {len(ranked)} products -> {out}", file=sys.stderr)
    print("TOP " + json.dumps(ranked[:a.top], ensure_ascii=False))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("--top", type=int, default=3)
    p.add_argument("--pages", type=int, default=5)
    uc.loop().run_until_complete(main(p.parse_args()))
