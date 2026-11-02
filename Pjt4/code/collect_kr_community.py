"""Collect iPhone Duo posts + comments from Korean communities.

Usage (from Pjt4/):
    python code/collect_kr_community.py list    # search result lists -> data/community_kr/raw/kr_list.jsonl
    python code/collect_kr_community.py posts   # post bodies + comments -> data/community_kr/raw/kr_posts.jsonl
    python code/collect_kr_community.py export  # -> data/community_kr/kr_list.json, kr_posts.json, posts_by_site/*.json
Crawling appends to JSONL so it can resume; `export` writes the final JSON files.
Plain HTTP requests only, ~1 req/sec.
"""
import json, random, re, sys, time, datetime as dt
from pathlib import Path
from urllib.parse import quote, urljoin
import requests
from bs4 import BeautifulSoup

START = dt.datetime(2026, 9, 9)
FLOOR = START  # list crawl stops below this date; daily mode raises it to (last run - 2 days)
KEYWORDS = ['아이폰 듀오', '아이폰듀오']
MAX_PAGES = 100
OUT = Path(__file__).resolve().parent.parent / 'data' / 'community_kr'
DATA = OUT / 'raw'
DATA.mkdir(parents=True, exist_ok=True)
LIST_F, POST_F = DATA / 'kr_list.jsonl', DATA / 'kr_posts.jsonl'

S = requests.Session()
S.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/130.0 Safari/537.36', 'Accept-Language': 'ko-KR,ko;q=0.9'})


SLOW = {'fmkorea.com': (10.0, 15.0), 'ppomppu.co.kr': (8.0, 12.0), 'meeco.kr': (6.0, 10.0)}  # per-domain delay range; these rate-limit at ~1 req/s


def get(url, enc='utf-8', **kw):
    lo, hi = next((v for k, v in SLOW.items() if k in url), (1.0, 1.0))
    delay = random.uniform(lo, hi)
    for i in range(3):
        try:
            r = S.get(url, timeout=20, **kw)
            time.sleep(delay)
            if r.status_code == 200:
                return BeautifulSoup(r.content.decode(enc, 'replace'), 'html.parser')
            print('  HTTP', r.status_code, url)
            if r.status_code in (429, 430):  # rate limited: back off hard
                time.sleep(120 * (i + 1))
                continue
        except requests.RequestException as e:  # dropped connection = throttling: back off like a 429
            print('  ERR', e)
            time.sleep(120 * (i + 1))
            continue
        time.sleep(3 * (i + 1))
    return None


def parse_date(s):
    s = s.strip()
    now = dt.datetime(2026, 10, 30, 15, 0)
    if '전' in s:  # "17 시간 전", "5 분 전"
        return now
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y.%m.%d %H:%M:%S', '%Y.%m.%d %H:%M',
                '%Y.%m.%d', '%Y.%m.%d. %H:%M', '%y.%m.%d %H:%M', '%Y-%m-%d', '%y/%m/%d %H:%M'):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            pass
    m = re.search(r'(\d{2,4})[.\-/](\d{1,2})[.\-/](\d{1,2})', s)
    if m:
        y = int(m[1]); y = y + 2000 if y < 100 else y
        return dt.datetime(y, int(m[2]), int(m[3]))
    m = re.fullmatch(r'(\d{1,2})\.(\d{1,2})', s)  # "MM.DD" without year (fmkorea lists); re-checked from post date
    if m:
        return dt.datetime(2026, int(m[1]), int(m[2]))
    if re.fullmatch(r'\d{1,2}:\d{2}(:\d{2})?', s):  # today
        return now
    return None


def txt(el):
    return el.get_text(' ', strip=True) if el else ''


# ---------------- list collectors: yield (rows, oldest_date) per page ----------------

def list_clien(kw, p):
    s = get(f'https://www.clien.net/service/search?q={quote(kw)}&sort=recency&p={p}&boardCd=&isBoard=false')
    rows = []
    for it in (s.select('.list_item[data-board-sn]') if s else []):
        a = it.select_one('a.subject_fixed')
        rows.append(dict(url=urljoin('https://www.clien.net', a['href'].split('?')[0]), title=a.get('title', txt(a)),
                         board=it.select_one('.shortname').get_text(strip=True) if it.select_one('.shortname') else '',
                         date=txt(it.select_one('.timestamp')), n_comments=it.get('data-comment-count')))
    return rows


def list_ppomppu(kw, p):
    s = get(f'https://www.ppomppu.co.kr/search_bbs.php?keyword={quote(kw.encode("euc-kr"))}'
            f'&search_type=sub_memo&order_type=date&page_no={p + 1}', enc='euc-kr')
    rows = []
    for c in (s.select('.results_board .content') if s else []):
        a = c.select_one('.title a')
        desc = [x.get_text(strip=True) for x in c.select('.desc span')]
        rows.append(dict(url=urljoin('https://www.ppomppu.co.kr', a['href']).split('&keyword')[0],
                         title=txt(a), board=desc[0] if desc else '', date=desc[2] if len(desc) > 2 else ''))
    return rows


def dc_q(kw):
    return ''.join('.%02X' % b if not (chr(b).isalnum() and b < 128) else chr(b) for b in kw.encode('utf-8'))


def list_dc(kw, p):
    s = get(f'https://search.dcinside.com/post/p/{p + 1}/sort/latest/q/{dc_q(kw)}')
    rows = []
    for li in (s.select('ul.sch_result_list li') if s else []):
        a = li.select_one('a.tit_txt')
        if not a:
            continue
        rows.append(dict(url=a['href'], title=txt(a), board=txt(li.select_one('.sub_txt')),
                         date=txt(li.select_one('.date_time'))))
    return rows


DC_GALLERIES = [('iphone', False), ('smartphone', False), ('galaxy', True), ('ipad1', True)]


def list_dc_gallery(kw):
    """Gallery-level search walks back through search_pos blocks (site-wide search stops at ~1 week)."""
    rows = []
    for gid, mg in DC_GALLERIES:
        base = (f'https://gall.dcinside.com/{"mgallery/" if mg else ""}board/lists/?id={gid}'
                f'&s_type=search_subject_memo&s_keyword={quote(kw)}')
        pos, blocks = '', 0
        while blocks < 60:
            newest_block, next_pos = None, None
            for page in range(1, 100):
                s = get(f'{base}{pos}&page={page}')
                trs = s.select('tr.ub-content.us-post') if s else []
                if s and page == 1:
                    nxt = s.select_one('a.search_next[href*="search_pos"]')
                    m = re.search(r'search_pos=(-?\d+)', nxt['href']) if nxt else None
                    next_pos = m[1] if m else None
                got = []
                for tr in trs:
                    a = tr.select_one('.gall_tit a[href*="no="]')
                    d = tr.select_one('.gall_date')
                    if not a or not d or tr.get('data-type') == 'icon_notice':
                        continue
                    got.append(dict(url=urljoin('https://gall.dcinside.com', a['href']).split('&s_type')[0].split('&page')[0],
                                    title=txt(a), board=gid, date=d.get('title', txt(d))))
                if not got or (rows and got[0]['url'] in {x['url'] for x in rows[-len(got):]}):
                    break  # past the last page DC repeats the final page instead of returning empty
                rows += got
                dates = [parse_date(g['date']) for g in got]
                newest_block = max([newest_block] + dates if newest_block else dates)
            print(f'dc_gallery {gid} [{kw}] block {blocks}: total rows {len(rows)}, newest in block={newest_block}')
            blocks += 1
            if (newest_block and newest_block < FLOOR) or not next_pos or pos == f'&search_pos={next_pos}':
                break
            pos = f'&search_pos={next_pos}'
    return rows


def list_meeco(kw, p):
    s = get(f'https://meeco.kr/index.php?act=IS&is_keyword={quote(kw)}&where=document&page={p + 1}&mid=index')
    rows = []
    for li in (s.select('main.misolSearch li') if s else []):
        a = li.select_one('a.cont_a')
        if not a:
            continue
        rows.append(dict(url=urljoin('https://meeco.kr', a['href']), title=txt(li.select_one('h1')), board='',
                         date=txt(li.select_one('.time'))))
    return rows


def list_fmkorea(kw, p):
    s = get(f'https://www.fmkorea.com/index.php?mid=best&search_keyword={quote(kw)}'
            f'&search_target=title_content&page={p + 1}')
    rows = []
    for li in (s.select('li.li') if s else []):
        a = li.select_one('h3.title a')
        if not a:
            continue
        srl = re.search(r'(\d{8,})', a['href'])
        rows.append(dict(url=f'https://www.fmkorea.com/{srl[1]}',
                         title=txt(li.select_one('.ellipsis-target')), board=txt(li.select_one('.category')),
                         date=txt(li.select_one('.regdate'))))
    return rows


def list_fmkorea_digital(kw, p):
    s = get(f'https://www.fmkorea.com/index.php?mid=digital&search_keyword={quote(kw)}'
            f'&search_target=title_content&page={p + 1}')
    rows = []
    for tr in (s.select('table.bd_lst tbody tr') if s else []):
        a = tr.select_one('td.title a[href*="document_srl"]')
        if not a or 'notice' in (tr.get('class') or []):
            continue
        srl = re.search(r'document_srl=(\d+)', a['href'])
        rows.append(dict(url=f'https://www.fmkorea.com/{srl[1]}', title=txt(a), board='디지털/' + txt(tr.select_one('td.cate')),
                         date=txt(tr.select_one('td.time'))))
    return rows


def list_ruliweb(kw, p):
    s = get(f'https://bbs.ruliweb.com/community/board/300143?search_type=subject_content'
            f'&search_key={quote(kw)}&page={p + 1}')
    rows = []
    for tr in (s.select('tr.table_body.blocktarget') if s else []):
        a = tr.select_one('a.subject_link, a.deco')
        if not a or '/300143/read/' not in a.get('href', '') or 'notice' in ' '.join(tr.get('class', [])):
            continue
        rows.append(dict(url=a['href'].split('?')[0], title=txt(a), board='유머',
                         date=txt(tr.select_one('td.time'))))
    return rows


LISTERS = dict(clien=list_clien, ppomppu=list_ppomppu, dcinside=list_dc, meeco=list_meeco,
               fmkorea=list_fmkorea, fmkorea_digital=list_fmkorea_digital, ruliweb=list_ruliweb)


def run_list(sites):
    seen = set()
    if LIST_F.exists():
        seen = {json.loads(l)['url'] for l in LIST_F.open(encoding='utf-8')}
    with LIST_F.open('a', encoding='utf-8') as f:
        for site in sites:
            for kw in KEYWORDS:
                if site == 'dcinside_gallery':
                    new = 0
                    for r in list_dc_gallery(kw):
                        d = parse_date(r['date'])
                        if (d and d < START) or r['url'] in seen:
                            continue
                        seen.add(r['url']); new += 1
                        f.write(json.dumps(dict(site=site, keyword=kw, list_date=d.isoformat() if d else None,
                                                **r), ensure_ascii=False) + '\n')
                    f.flush()
                    print(f'dcinside_gallery [{kw}] {new} new')
                    continue
                stale = 0
                for p in range(MAX_PAGES):
                    rows = LISTERS[site](kw, p)
                    if not rows:
                        break
                    dates = [d for d in (parse_date(r['date']) for r in rows) if d]
                    new = 0
                    for r in rows:
                        d = parse_date(r['date'])
                        if d and d < START:
                            continue
                        if r['url'] in seen:
                            continue
                        seen.add(r['url']); new += 1
                        f.write(json.dumps(dict(site=site, keyword=kw, list_date=d.isoformat() if d else None,
                                                **r), ensure_ascii=False) + '\n')
                    f.flush()
                    newest = max(dates) if dates else None
                    print(f'{site} [{kw}] p{p}: {len(rows)} rows, {new} new, newest={newest}')
                    if newest and newest < FLOOR:  # whole page is older (results can be mixed-order)
                        break
                    stale = stale + 1 if new == 0 else 0
                    if stale >= 3:  # search capped / repeating pages
                        break


# ---------------- post parsers ----------------

def post_clien(u):
    s = get(u)
    if not s: return None
    cm = [dict(text=txt(r.select_one('.comment_view')), date=txt(r.select_one('.timestamp')))
          for r in s.select('.comment_row') if r.select_one('.comment_view')]
    return dict(title=txt(s.select_one('.post_subject')), date=txt(s.select_one('.post_author .view_count.date')),
                body=txt(s.select_one('.post_article')), comments=cm)


def post_ppomppu(u):
    m = re.search(r'id=(\w+)&no=(\d+)', u)
    s = get(u, enc='euc-kr')
    if not s: return None
    cm, page, total = [], 1, 1
    while page <= min(total, 10):  # comments come from the site's own JSON endpoint
        try:
            js = S.get('https://www.ppomppu.co.kr/zboard/comment.php', timeout=20, params=dict(
                id=m[1], no=m[2], c_page=page, comment_mode='sort_asc', cmd='get_comment_json')).json()
            time.sleep(random.uniform(*SLOW['ppomppu.co.kr']))
        except Exception:
            break
        total = int(js.get('total_page') or 1)
        for top in js.get('comments') or []:
            for c in [top] + list(top.get('sub_cmt') or []):  # replies are nested under sub_cmt
                meta = c.get('meta') or {}
                d = (meta.get('time_detail') or meta.get('time_display') or '') if isinstance(meta, dict) else ''
                cm.append(dict(text=BeautifulSoup(c.get('memo', ''), 'html.parser').get_text(' ', strip=True),
                               date=d, depth=c.get('depth', 0)))
        page += 1
    title = [x.get_text(strip=True) for x in s.select('#topTitle h1')]
    dm = re.search(r'등록일\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})', txt(s.select_one('#topTitle')))
    return dict(title=title[0] if title else '', date=dm[1] if dm else '', body=txt(s.select_one('.han')), comments=cm)


def post_dc(u):
    s = get(u)
    if not s: return None
    q = dict(re.findall(r'[?&](id|no)=([\w]+)', u))
    cm = []
    esno = s.select_one('#e_s_n_o')
    gtype = 'M' if '/mgallery/' in u else ('MI' if '/mini/' in u else 'G')
    if esno and q.get('id'):
        for page in (1, 2, 3):
            try:
                r = S.post('https://gall.dcinside.com/board/comment/', data=dict(
                    id=q['id'], no=q['no'], cmt_id=q['id'], cmt_no=q['no'], e_s_n_o=esno['value'],
                    comment_page=page, sort='D', _GALLTYPE_=gtype),
                    headers={'X-Requested-With': 'XMLHttpRequest', 'Referer': u}, timeout=20)
                time.sleep(1.0)
                js = r.json()
            except Exception:
                break
            items = [c for c in (js.get('comments') or []) if c.get('nicktype') != 'COMMENT_BOY']
            cm += [dict(text=BeautifulSoup(c.get('memo', ''), 'html.parser').get_text(' ', strip=True),
                        date=c.get('reg_date', '')) for c in items]
            if int(js.get('total_cnt', 0) or 0) <= len(cm) or not items:
                break
    gd = s.select_one('.gallview_head .gall_date')
    return dict(title=txt(s.select_one('.title_subject')), date=gd.get('title', txt(gd)) if gd else '',
                body=txt(s.select_one('.write_div')), comments=cm)


def post_meeco(u):
    s = get(u)
    if not s: return None
    cm = [dict(text=txt(b.select_one('.xe_content')), date=txt(b.find_parent(class_='cmt-el').select_one('.date')))
          for b in s.select('.cmt-el-body') if b.select_one('.xe_content')]
    body = s.select_one('.atc-wrap .xe_content')
    return dict(title=txt(s.select_one('.atc-title')), date=txt(s.select_one('.bAtc .date')), body=txt(body), comments=cm)


def post_fmkorea(u):
    s = get(u)
    if not s: return None
    cm = [dict(text=txt(li.select_one('.xe_content')), date=txt(li.select_one('.date')))
          for li in s.select('.fdb_lst_ul li') if li.select_one('.xe_content')]
    return dict(title=txt(s.select_one('.np_18px')), date=txt(s.select_one('.top_area .date')),
                body=txt(s.select_one('.rd_body .xe_content')), comments=cm)


def post_ruliweb(u):
    s = get(u)
    if not s: return None
    cm = [dict(text=txt(c.select_one('.text_wrapper')), date=txt(c.select_one('.time')))
          for c in s.select('.comment_element') if c.select_one('.text_wrapper')]
    return dict(title=txt(s.select_one('.subject_text')), date=txt(s.select_one('.regdate')),
                body=txt(s.select_one('.view_content')), comments=cm)


PARSERS = dict(clien=post_clien, ppomppu=post_ppomppu, dcinside=post_dc, meeco=post_meeco,
               fmkorea=post_fmkorea, fmkorea_digital=post_fmkorea, ruliweb=post_ruliweb,
               dcinside_gallery=post_dc)


def post_file(site):
    return DATA / f'posts_{site}.jsonl'


def load_jsonl(p):
    return [json.loads(l) for l in p.open(encoding='utf-8')] if p.exists() else []


def fetch_post(r):
    try:
        p = PARSERS[r['site']](r['url'])
    except Exception as e:
        print('  parse fail', r['url'], e)
        return None
    if p is None:
        return None
    return dict(site=r['site'], board=r['board'], url=r['url'], list_title=r['title'], list_date=r['list_date'],
                fetched_at=dt.datetime.now().isoformat(timespec='seconds'), **p)


def run_posts(sites, limit=None, refresh_urls=()):
    """Fetch posts not yet fetched (+ re-fetch `refresh_urls` to pick up new comments).
    Each site writes its own raw/posts_<site>.jsonl, so site groups can run as parallel processes."""
    lock = DATA / f'.lock_{"_".join(sorted(sites))}'
    lock.write_text(str(dt.datetime.now()))
    try:
        rows = load_jsonl(LIST_F)
        for site in sites:
            done = {x['url'] for x in load_jsonl(post_file(site))}
            todo = [r for r in rows if r['site'] == site and (r['url'] not in done or r['url'] in refresh_urls)][:limit]
            print(f'{site}: {len(todo)} posts to fetch')
            fails = 0
            with post_file(site).open('a', encoding='utf-8') as f:
                for i, r in enumerate(todo):
                    rec = fetch_post(r)
                    if rec is None:
                        fails += 1
                        if fails >= 5:  # site keeps refusing: stop this site, unfetched posts stay for a later run
                            print(f'{site}: 5 consecutive failures - stopping this site for now ({i + 1}/{len(todo)})')
                            break
                        continue
                    fails = 0
                    f.write(json.dumps(rec, ensure_ascii=False) + '\n')
                    f.flush()
                    if i % 25 == 0:
                        print(f'  {site} {i}/{len(todo)} comments={len(rec["comments"])} {rec["title"][:30]}')
    finally:
        lock.unlink(missing_ok=True)


def norm_ts(s, ref):
    """Normalize site-specific date strings to 'YYYY-MM-DD HH:MM'. ref = fetch time (for relative/time-only)."""
    s = (s or '').strip().replace('(', '').replace(')', '')
    if not s:
        return None
    m = re.match(r'(\d+)\s*(초|분|시간|일)\s*전', s)
    if m:
        unit = dict(초='seconds', 분='minutes', 시간='hours', 일='days')[m[2]]
        return (ref - dt.timedelta(**{unit: int(m[1])})).strftime('%Y-%m-%d %H:%M')
    m = re.fullmatch(r'(\d{1,2}):(\d{2})(:\d{2})?', s)  # time only = same day as fetch
    if m:
        return ref.strftime('%Y-%m-%d ') + f'{int(m[1]):02d}:{m[2]}'
    m2 = re.match(r'^(\d{1,2})[.\-/](\d{1,2})\s+(\d{1,2}):(\d{2})', s)  # "MM.DD HH:MM" without year
    if m2:
        return f'2026-{int(m2[1]):02d}-{int(m2[2]):02d} {int(m2[3]):02d}:{m2[4]}'
    m3 = re.match(r'^(\d{2,4})[.\-/](\d{1,2})[.\-/](\d{1,2})\.?(?:\s+(\d{1,2}):(\d{2}))?', s)
    if m3:
        y = int(m3[1]); y = y + 2000 if y < 100 else y
        hhmm = f'{int(m3[4]):02d}:{m3[5]}' if m3[4] else '00:00'
        return f'{y}-{int(m3[2]):02d}-{int(m3[3]):02d} {hhmm}'
    return None


def build_units():
    """One record per unit: doc_type = 'post' | 'comment'. A post fetched several times (daily refresh)
    is merged: latest body, union of comments (keyed by text + occurrence, first-seen timestamp kept)."""
    snaps = {}
    for f in sorted(DATA.glob('posts_*.jsonl')):
        for p in load_jsonl(f):
            snaps.setdefault(p['url'], []).append(p)
    units = []
    for url, ps in snaps.items():
        ps.sort(key=lambda p: p.get('fetched_at') or '')
        last = ps[-1]
        ref = dt.datetime.fromisoformat(ps[0].get('fetched_at') or '2026-10-30T15:00:00')
        post_ts = norm_ts(ps[0].get('date'), ref) or (last['list_date'] or '')[:16].replace('T', ' ') or None
        if post_ts and post_ts < START.strftime('%Y-%m-%d'):
            continue  # outside collection period (list dates without year can let these through)
        comments, seen = [], set()
        for p in ps:
            pref = dt.datetime.fromisoformat(p.get('fetched_at') or '2026-10-30T15:00:00')
            occ = {}
            for c in p['comments']:
                occ[c['text']] = occ.get(c['text'], 0) + 1
                key = (c['text'], occ[c['text']])
                if key in seen:
                    continue
                seen.add(key)
                comments.append(dict(c, ts=norm_ts(c.get('date'), pref) or post_ts, first_fetched=p.get('fetched_at')))
        title = last['title'] or last['list_title']
        units.append(dict(doc_type='post', site=last['site'], board=last['board'], post_url=url, title=title,
                          text=last['body'], timestamp=post_ts, n_comments=len(comments),
                          first_fetched=ps[0].get('fetched_at')))
        for i, c in enumerate(comments):
            units.append(dict(doc_type='comment', site=last['site'], board=last['board'], post_url=url,
                              comment_idx=i, depth=c.get('depth'), title=title, text=c['text'],
                              timestamp=c['ts'], first_fetched=c['first_fetched']))
    return units


def unit_key(u):
    return (u['doc_type'], u['post_url'], u.get('comment_idx'))  # comments are append-only per post


def dump(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')


def run_export(units=None):
    units = units if units is not None else build_units()
    dump(OUT / 'kr_list.json', load_jsonl(LIST_F))
    dump(OUT / 'kr_posts.json', [u for u in units if u['doc_type'] == 'post'])
    dump(OUT / 'kr_comments.json', [u for u in units if u['doc_type'] == 'comment'])
    dump(OUT / 'kr_all_units.json', units)
    for site in sorted({u['site'] for u in units}):
        dump(OUT / 'by_site' / f'{site}.json', [u for u in units if u['site'] == site])
    n_post = sum(u['doc_type'] == 'post' for u in units)
    print(f'exported {n_post} posts, {len(units) - n_post} comments -> {OUT}')


STATE_F = DATA / 'daily_state.json'
REFRESH_DAYS = 3  # re-fetch posts this recent to capture new comments


def run_daily():
    """Daily increment: new search results since last run -> fetch new posts -> refresh recent posts' comments
    -> write only the new units to daily/<date>_new_units.json, then refresh the cumulative export."""
    global FLOOR
    if list(DATA.glob('.lock_*')):
        print('another collection is running (lock file present) - skip today')
        return
    state = json.loads(STATE_F.read_text(encoding='utf-8')) if STATE_F.exists() else {}
    last = dt.datetime.fromisoformat(state.get('last_run', START.isoformat()))
    FLOOR = max(START, last - dt.timedelta(days=2))
    before = {unit_key(u) for u in build_units()}
    sites = list(LISTERS) + ['dcinside_gallery']
    run_list(sites)
    cutoff = (dt.datetime.now() - dt.timedelta(days=REFRESH_DAYS)).strftime('%Y-%m-%d')
    recent = {u['post_url'] for u in build_units() if u['doc_type'] == 'post' and (u['timestamp'] or '') >= cutoff}
    run_posts(sites, refresh_urls=recent)
    units = build_units()
    new = [u for u in units if unit_key(u) not in before]
    today = dt.date.today().isoformat()
    dump(OUT / 'daily' / f'{today}_new_units.json', new)
    run_export(units)
    STATE_F.write_text(json.dumps(dict(last_run=dt.datetime.now().isoformat(timespec='seconds'),
                                       last_new_posts=sum(u['doc_type'] == 'post' for u in new),
                                       last_new_comments=sum(u['doc_type'] == 'comment' for u in new))),
                       encoding='utf-8')
    print(f'daily {today}: {len(new)} new units -> daily/{today}_new_units.json')


if __name__ == '__main__':
    mode = sys.argv[1]
    sites = sys.argv[2].split(',') if len(sys.argv) > 2 else list(LISTERS) + ['dcinside_gallery']
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
    if mode == 'list':
        run_list(sites)
    elif mode == 'posts':
        run_posts(sites, limit)
    elif mode == 'daily':
        run_daily()
    else:
        run_export()
