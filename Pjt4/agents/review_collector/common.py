"""공통: 브라우저 세션, 페이지 내 fetch, CSV/상태 저장"""
import csv, json, os
import nodriver as uc

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
PROFILE = os.path.join(ROOT, "chrome_profile")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

EXIT_BLOCKED = 2      # 403/429 등 차단 신호 → 즉시 중단
EXIT_UNSUPPORTED = 3  # 리뷰 API를 찾지 못함 등
BLOCK_STATUSES = {401, 403, 429}

os.makedirs(DATA, exist_ok=True)


async def start_browser():
    return await uc.start(headless=False, browser_executable_path=CHROME, user_data_dir=PROFILE)


async def page_fetch(tab, url, method="GET", body=None, headers=None):
    """현재 탭(로그인·쿠키 세션 그대로)에서 fetch. (status, text) 반환, 네트워크 오류는 status 0."""
    opts = {"method": method, "credentials": "include"}
    if headers:
        opts["headers"] = headers
    if body is not None:
        opts["body"] = body
    js = (f"fetch({json.dumps(url)}, {json.dumps(opts)})"
          ".then(async r => r.status + '\\n' + await r.text()).catch(e => '0\\n' + e)")
    txt = await tab.evaluate(js, await_promise=True)
    status, text = str(txt).split("\n", 1)
    return (int(status) if status.isdigit() else 0), text


class Store:
    """리뷰 CSV(append, review_id 중복 제거) + 진행 상태(json)"""

    def __init__(self, name, fields):
        self.csv_path = os.path.join(DATA, f"{name}.csv")
        self.state_path = os.path.join(DATA, f".state_{name}.json")
        self.fields = fields
        self.state = json.load(open(self.state_path, encoding="utf-8")) if os.path.exists(self.state_path) else {}
        self.seen = set()
        if os.path.exists(self.csv_path):
            with open(self.csv_path, encoding="utf-8-sig") as f:
                self.seen = {r["review_id"] for r in csv.DictReader(f)}
        new = not os.path.exists(self.csv_path)
        self._f = open(self.csv_path, "a", newline="", encoding="utf-8-sig")
        self._w = csv.DictWriter(self._f, fieldnames=fields, extrasaction="ignore")
        if new:
            self._w.writeheader()

    def add(self, rows):
        added = 0
        for r in rows:
            rid = str(r["review_id"])
            if rid in self.seen:
                continue
            self.seen.add(rid)
            self._w.writerow(r)
            added += 1
        self._f.flush()
        return added

    def save(self):
        json.dump(self.state, open(self.state_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    def close(self):
        self._f.close()
        self.save()
