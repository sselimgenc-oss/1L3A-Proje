import json,re,pathlib
K=pathlib.Path(__file__).parent
m=json.load(open(K/'ham/meta.json'))
for x in m:
    p=K/'pine'/f"{x['id']}.pine"
    if not p.exists(): print(x['id'],'KAPALI',x['ad'][:50]); continue
    s=p.read_text()
    v=re.search(r'@version\s*=\s*(\d+)',s); 
    feats=[]
    for k,pat in [('LA_ON','lookahead_on|lookahead\s*=\s*true'),('SEC','request\.security|security\('),('TICK','calc_on_every_tick\s*=\s*true'),('POC','process_orders_on_close\s*=\s*true'),('PYR','pyramiding\s*=\s*[1-9]'),('pivot','pivothigh|pivotlow|ta\.pivot'),('zz','zigzag|ZigZag'),('inputs','input'),('SHORT','strategy\.short|direction\.short|strategy\.short'),('exit','strategy\.exit'),('ML','knn|lorentz|neural|kmeans'),('alert','alertcondition|alert\(')]:
        c=len(re.findall(pat,s))
        if c: feats.append(f"{k}{c}")
    print(x['id'],f"v{v.group(1) if v else '?'}",len(s.splitlines()),'|',x['ad'][:55],'|',x['yazar'],'|',' '.join(feats))
