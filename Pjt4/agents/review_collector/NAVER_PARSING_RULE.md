# Naver review parsing rule (brand.naver.com / smartstore.naver.com)

Implemented in `sites/naver.py`; `collect.py` routes `brand.naver.com` and `smartstore.naver.com` URLs to it automatically.
Verified 2026-10-30 on `https://brand.naver.com/applestore/products/13771279742` (1 review: "더럽게 이뻐요 진짜", 5점, 2026-10-25 13:18 KST).

## Why the generic adapter fails on Naver

| Problem | Detail |
|---|---|
| Review tab not detected | Tab text is `리뷰 1`. A JS regex `리뷰\b` never matches before a space/number because Korean is not a `\w` character. Use `(?![가-힣A-Za-z])` instead of `\b`. |
| Review request already sent | `query-pages` is requested **while the page loads/scrolls**, before the tab click. |
| Response body not readable | Reading the captured response body later fails (`No resource with given identifier`). |
| Different product number | The API uses an internal `originProductNo` (e.g. `13710351502`) that differs from the number in the page URL (`13771279742`). |
| Few reviews | Products with 1 review were ignored by the "list of ≥ 2 items" heuristic. |

## Rule

1. **URL** — accept `https://{brand|smartstore}.naver.com/<store>/products/<productNo>`. Strip tracking query params (`nl-query`, `nl-au`, `NaPm`, `n_*` …) before opening.
2. **Open the page in the collector's real Chrome** (`start_browser()`), enable network events, wait 6–9 s, scroll 3× (≈1000 px, 1–2 s apart), then click the tab whose text starts with `리뷰` / `구매평` / `상품리뷰` (regex above). Wait 4–6 s.
3. **Capture the outgoing request** (not the response):
   - Event: `Network.requestWillBeSent`
   - URL contains `/n/v1/contents/reviews/query-pages`, method `POST`, has a JSON body.
   - Body keys: `checkoutMerchantNo`, `originProductNo`, `page`, `pageSize`, `reviewSearchSortType`.
   - Keep the request headers except cookie / user-agent / referer / origin / host / content-length / accept-encoding / connection.
4. **Re-send it from inside the page tab** (`page_fetch`, same session/cookies) with:
   - `reviewSearchSortType = "REVIEW_CREATE_DATE_DESC"` (newest first)
   - `page = 1, 2, 3 …` (keep `pageSize` from the captured request)
   - delay `delay ~ 2×delay` s between pages (default 3–6 s)
5. **Stop** when collected ≥ `totalElements`, or `contents` is empty, or a page adds no new review ID, or `--max-pages` (≤ 50) is reached.
6. **Parse** each item of `contents[]`:

   | CSV column | API field | Note |
   |---|---|---|
   | `store` | URL path | e.g. `applestore` |
   | `product_no` | URL path | number in the page URL |
   | `review_id` | `id` | de-duplication key |
   | `rating` | `reviewScore` | 1–5 |
   | `content` | `reviewContent` | stripped |
   | `option` | `productOptionContent` | may be empty |
   | `review_type` | `reviewType` | e.g. `NORMAL` |
   | `helpful_count` | `helpCount` | |
   | `photo_count` | `len(reviewAttaches)` | |
   | `review_date` | `createDate` | ISO in UTC → **convert to KST**, `YYYY-MM-DD HH:MM` |

7. **Never store** writer ID / nickname / profile fields (the page shows masked IDs like `qotj********`; they are not collected).
8. **Output** — `data/naver_reviews_<store>_<productNo>.csv` (UTF-8 with BOM) + resume state `data/.state_naver_reviews_<store>_<productNo>.json`.

## Failure handling

| Situation | Exit | Meaning |
|---|---|---|
| No `query-pages` request captured | 3 | Print the page title. If it is a security-check / captcha page, treat it as a **block** and stop; do not bypass. |
| Re-sent request returns 401 / 403 / 429 | 2 | Block signal — stop, retry hours later (resume state is kept). |
| Other non-200 | 3 | Report; the request format may have changed — re-verify with this rule's step 3. |
| `totalElements = 0` | 0 | No reviews yet (not an error). |

## Re-verifying when Naver changes

Open the product page in Chrome → DevTools → Network → filter `reviews` → click the review tab / page 2 → check that `query-pages` still exists with the same body keys and that `contents[]` still has `id`, `reviewScore`, `reviewContent`, `createDate`. Update `REVIEW_API`, the body keys or the field map in `sites/naver.py` and this file together.
