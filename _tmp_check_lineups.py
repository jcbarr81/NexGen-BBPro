import csv, glob, os
errs=[]
for path in glob.glob('data/lineups/*_vs_*.csv'):
    with open(path, newline='') as fh:
        rows=list(csv.DictReader(fh))
    ids=[r.get('player_id') for r in rows]
    if len(rows)!=9 or len(set(ids))!=len(ids):
        errs.append((os.path.basename(path), len(rows), len(ids)-len(set(ids))))
if errs:
    for e in errs:
        print(f"{e[0]} rows={e[1]} dup_count={e[2]}")
else:
    print('All lineups have 9 unique players')
