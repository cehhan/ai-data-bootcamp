"""Fetch a random sample of DC posts from the collected list -> CSV (preview of DC content)."""
import csv, json, random, sys, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import collect_kr_community as c

N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
rows = [json.loads(l) for l in open(Path(__file__).parent.parent / 'data' / 'kr_list.jsonl', encoding='utf-8')]
rows = [r for r in rows if r['site'].startswith('dcinside')]
random.seed(42)
sample = random.sample(rows, N)
out = c.OUT / 'samples' / f'dc_sample{N}.csv'
with out.open('w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['doc_type', 'timestamp', 'gallery', 'title', 'text', 'n_comments', 'first_comments', 'post_url'])
    for i, r in enumerate(sample):
        p = c.post_dc(r['url'])
        if not p:
            continue
        ts = c.norm_ts(p['date'], dt.datetime.now()) or r['list_date']
        w.writerow(['post', ts, r['board'], p['title'] or r['title'], p['body'][:2000], len(p['comments']),
                    ' || '.join(x['text'] for x in p['comments'][:3])[:500], r['url']])
        f.flush()
        if i % 20 == 0:
            print(i, ts, p['title'][:30])
print('saved', out)
