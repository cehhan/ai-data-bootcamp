"""이커머스 상품 리뷰 수집기 — 진입점

usage:
  python collect.py <상품 URL> [--max-pages 30] [--delay 3]
                    [--sort DATE_DESC|ORDER_SCORE_ASC] [--ratings all|1,2,3]   # 쿠팡 전용 옵션

- 전용 어댑터가 있는 사이트(sites/)는 그것을, 나머지는 generic(리뷰 API 자동 탐지)을 쓴다.
- 종료코드: 0 정상, 2 차단 신호(403/429 등)로 중단, 3 지원 불가/탐지 실패
"""
import argparse, sys
from urllib.parse import urlparse
import nodriver as uc
import generic
from sites import coupang, naver

ADAPTERS = {"coupang.com": coupang, "brand.naver.com": naver, "smartstore.naver.com": naver}


def pick_adapter(url):
    host = (urlparse(url).hostname or "").lower()
    for domain, mod in ADAPTERS.items():
        if host == domain or host.endswith("." + domain):
            return mod
    return generic


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("--max-pages", type=int, default=30, help="실행 1회당 최대 페이지 수")
    p.add_argument("--delay", type=float, default=3.0, help="요청 간 최소 대기(초), 실제는 delay~2*delay")
    p.add_argument("--sort", default="DATE_DESC", choices=["DATE_DESC", "ORDER_SCORE_ASC"], help="쿠팡 전용")
    p.add_argument("--ratings", default="all", help="쿠팡 전용: all 또는 1,2,3,4,5")
    p.add_argument("--generic", action="store_true", help="전용 어댑터 대신 범용 탐지 강제(테스트용)")
    a = p.parse_args()
    a.max_pages = min(a.max_pages, 50)
    adapter = generic if a.generic else pick_adapter(a.url)
    sys.exit(uc.loop().run_until_complete(adapter.run(a)) or 0)
