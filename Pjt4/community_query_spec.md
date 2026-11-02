# iPhone Duo community reaction collection spec (KR + EN queries)

- Period: 2026-09-09 (announcement) ~ ongoing (daily incremental from 2026-10-31)
- Sub-periods for comparison: pre-order 09-09~10-15 / pre-order~launch 10-16~10-22 / post-launch 10-23~

## Step 1. Communities

| Tier | Community | Board(s) | Why |
|---|---|---|---|
| 1 | 클리앙 | 사용기(use), 모두의공원(park), 아이포니앙(소모임) | IT-heavy, buyer 사용기 board (already 1 hit) |
| 1 | 뽐뿌 | 아이폰포럼, 휴대폰포럼, 자유게시판 | purchase/price/carrier talk |
| 1 | 디시인사이드 | 아이폰 갤러리, 폴더블폰 갤러리 | high volume, unfiltered |
| 1 | 미코(meeco) | 자유, 애플 | Apple enthusiasts |
| 2 | 더쿠 | 스퀘어/일반 | general public (20-30s women) |
| 2 | 에펨코리아 | 포텐/자유, 휴대폰 | general public (20-30s men) |
| 2 | 루리웹 | 모바일/IT 게시판 | |
| 2 | 네이버 카페 아사모 | 구매/사용 후기 | largest iPhone user cafe; login may limit |
| 3 | 모요 커뮤니티 Q&A | 질문 | purchase-intent questions |
| 3 | 블라인드, 인스티즈, 네이트판 | | supplementary only |

### Actually collected (2026-10-30)

| Community | Source used | Note |
|---|---|---|
| 클리앙 | site search (all boards) | |
| 뽐뿌 | site search (all boards) | |
| 디시인사이드 | site-wide search (~last 4 days only) + gallery search: 아이폰, 스마트폰, 갤럭시, 아이패드 | |
| 미코 | site search (documents) | |
| 에펨코리아 | 포텐(best) search + 디지털 board search (`fmkorea.com/digital`) | rate-limited, see rules |
| 루리웹 | 유머 board (300143) search | |
| 더쿠 | excluded | search does not work without login |
| 아사모 (Naver cafe) | excluded | login required |

## Collection rules

1. **Search keywords**: `아이폰 듀오`, `아이폰듀오` (each community's own search, title+content). Boolean filters below are applied after collection.
2. **Period**: keep units with timestamp 2026-09-09 ~ 2026-10-30. Lists that show dates without a year are re-checked against the post page date.
3. **Unit of analysis — post vs comment**: every fetched item is stored as a separate record with `doc_type`:
   - `post`: title + body, `n_comments`
   - `comment`: comment text, `post_url` (parent), `comment_idx`, `depth` (0 = comment, 1+ = reply, where available)
   - Buyer / non-buyer tags are applied per unit (a buyer may comment under a non-buyer's post).
4. **Timestamps**: normalized to `YYYY-MM-DD HH:MM` (KST). Time-only or relative values ("12:17", "16 시간 전") are resolved against the fetch time (`fetched_at`); comments with no time fall back to the post timestamp.
5. **Request pacing**: plain HTTP only (no fingerprint spoofing / bot-check bypass), ~1 req/s per site; **에펨코리아 10–15 s, 뽐뿌 8–12 s, 미코 6–10 s per request** (all rate-limited at 1 req/s) with a 2–4 min back-off on HTTP 429/430 or dropped connections; after 5 consecutive failures a site is paused and its unfetched posts are left for a later run. Stop and report if a site keeps blocking.
6. **Privacy**: no author names / nicknames / IPs are stored.
7. **Output** (`data/community_kr/`): `kr_posts.json`, `kr_comments.json`, `kr_all_units.json` (both, with `doc_type`), `by_site/<site>.json`, `kr_list.json` (search results). Working files in `raw/*.jsonl` (`kr_list.jsonl`, `posts_<site>.jsonl`).
8. **Coverage**: full fetch — every search result in the period is fetched (no sampling), including 디시 posts from non-device galleries. Samples (e.g. `samples/dc_sample100.csv`) are for monitoring only.
9. **Daily cadence (incremental) — ON HOLD (not scheduled; start only on explicit request)** — `code/run_daily_kr.bat` → `python code/collect_kr_community.py daily`, scheduled every day 06:00 (Windows Task Scheduler, task `iPhoneDuo_KR_Community_Daily`):
   1. Re-run each community search, stopping at (last run − 2 days) so nothing between runs is missed.
   2. Fetch posts not fetched before.
   3. Re-fetch posts from the last **3 days** to capture comments added after the first fetch (comments are merged; existing ones are never duplicated).
   4. Write **only the units that are new since the previous run** (new posts + new comments, with `doc_type`) to `daily/YYYY-MM-DD_new_units.json`.
   5. Rebuild the cumulative files in rule 7. Run state: `raw/daily_state.json`; log: `logs/daily_YYYY-MM-DD.log`.
   - Skips the day if another collection is still running (`raw/.lock_*`).
   - Requires the PC to be on at run time; a missed day is caught up by the next run (step 1 looks back to the last run).

## US scope (decided 2026-10-30)

### US e-commerce (buyer reviews)

| Site | Status | Note |
|---|---|---|
| AT&T | in scope | 6 reviews / 3.66★ seen on 10/30 |
| Best Buy | in scope | carrier-locked listings only (Verizon/AT&T); one URL per storage × color × carrier listing |
| Verizon | in scope | |
| T-Mobile | in scope | |
| Walmart | in scope | shows a "Robot or human?" check to plain requests — if the agent's browser also gets it, treat as a block (no bypass) |
| Amazon | in scope | review pages beyond the top reviews require sign-in → collect only what is visible without login |

- Period: US launch 2026-10-23 ~.
- Collected with the review-collector agent (generic mode first; site adapter only when needed, like Naver).
- Extra fields vs KR: `verified_purchase`, `incentivized` (if the site marks it), `syndicated_from` (review-platform syndication, e.g. reviews copied from another retailer — de-duplicate by text + date + rating across sites), original timestamp + time zone.
- Waiting for: US product URL list (same format as `iphoneduo_ecom_urls.xlsx`).

### US community — Reddit

- **Only Apple / iPhone / smartphone-related subreddits** (proposed list — confirm):
  - Apple / iPhone: r/apple, r/iphone, r/ios, r/AppleHelp
  - Smartphone: r/smartphones, r/foldables, r/Android, r/GalaxyFold
- Period: 2026-09-09 ~ (same as KR).
- Query: English core terms (`"iPhone Duo"`, `"iPhoneDuo"`, `Duo AND (iPhone OR Apple OR foldable)` with the exclusions) via each subreddit's search, `restrict_sr=1`, `sort=new`.
- Access: Reddit's public **RSS** feeds (`/r/<sub>/search.rss`, per-post comment feeds `/comments/<id>/.rss`) with plain requests and a descriptive User-Agent. The `.json` endpoints return 403 without login and are not used. RSS has no score / vote counts.
- Units: `post` and `comment` records with `doc_type`, same schema as KR; buyer / non-buyer tagged with the EN keyword lists in Step 2.
- Pacing: ≥ 2 s per request, stop a subreddit after repeated 429s.

## Step 2. Boolean query

### Core (product)
```
("아이폰 듀오" OR "아이폰듀오" OR "iPhone Duo" OR "iPhoneDuo" OR "폰듀오"
 OR (("듀오") AND ("아이폰" OR "애플" OR "폴더블")))
```
Optional recall expansion (pre-announcement nicknames, low precision):
`"폴더블 아이폰" OR "접는 아이폰" OR "아이폰 폴드" OR "아폴드"`

### Exclusion (noise)
```
NOT ("결혼정보" OR "듀오 회원" OR "듀오링고" OR "Duolingo" OR "서피스 듀오" OR "Surface Duo"
     OR "맥세이프 듀오" OR "MagSafe Duo" OR "갤럭시 듀오스" OR "Galaxy Duos"
     OR "케이스 판매" OR "필름 판매" OR "최저가 링크" OR "파트너스 활동")
```

### Buyer classification (post OR comment level)
```
KR: ("개봉기" OR "언박싱" OR "수령" OR "받았" OR "도착했" OR "개통했" OR "개통 완료"
     OR "사용기" OR "써보니" OR "써보고" OR "실사용" OR "일주일 사용" OR "며칠 써"
     OR "반품했" OR "교환받" OR "내 듀오" OR "제 듀오")

EN: ("unboxing" OR "unboxed" OR "got my" OR "picked up my" OR "just arrived" OR "arrived today"
     OR "my Duo" OR "my iPhone Duo" OR "I bought" OR "I've been using" OR "after a week"
     OR "days in" OR "week with" OR "first impressions" OR "daily driver"
     OR "returned it" OR "returned my" OR "exchanged" OR "replacement unit")
```
-> matched = buyer candidate, then manual check (exclude "~받았다던데", "my friend got", 리뷰어 영상 요약 etc.)

### Non-buyer (everything else that matches Core), sub-tag purchase intent
```
Intent+ KR: ("살까" OR "사야" OR "예약했" OR "대기" OR "기다리" OR "지를")
Intent+ EN: ("should I buy" OR "should I get" OR "thinking about" OR "considering" OR "pre-ordered"
             OR "preordered" OR "waiting for" OR "ships in" OR "delivery date" OR "can't wait")

Intent- KR: ("안 산다" OR "안살" OR "패스" OR "거르" OR "비싸" OR "돈값" OR "다음 세대" OR "2세대")
Intent- EN: ("not buying" OR "won't buy" OR "pass on" OR "skip" OR "skipping" OR "overpriced"
             OR "too expensive" OR "not worth" OR "wait for gen 2" OR "second gen" OR "next gen"
             OR "cancelled my preorder" OR "canceled my pre-order")
```
Note: "예약했/대기", "pre-ordered/waiting for" = intent but not yet received -> non-buyer (pre-receipt).
Note: "cancelled my preorder" = Intent- (non-buyer), unlike "returned it" (buyer who returned).

### Aspect dictionary (for later tagging)
- 가격: 329만, 가격, 비싸, 돈값, 할부
- 내구성: 크랙, 크랙게이트, 균열, 힌지, 주름, 파손, 보험
- 디스플레이/앱: 여백, 레터박스, 최적화, 앱 대응, 화면비
- 성능: 발열, 배터리, 카메라
- 인증: 터치ID, Touch ID, 페이스ID
- 비교: 폴드8, 갤럭시 Z, 18 프로, 프로맥스
- 구매/공급: 품절, 배송, 1월, 웃돈, 리셀
