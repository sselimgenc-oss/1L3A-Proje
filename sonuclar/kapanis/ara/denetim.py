"""Lider denetimi: parti çıktısından tohumlu örnek + aday_listesi kuralı + eski kaynak satırı."""
import csv,random,sys
csv.field_size_limit(10**9)
from pathlib import Path
K=Path(__file__).resolve().parents[1]; R=K.parents[1]
p,n,t=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
a={r['strateji_id']:r for r in csv.DictReader(open(K/'aday_listesi.csv'))}
kay={r['kaynak_id']:r['yol'] for r in csv.DictReader(open(R/'sonuclar/hesap_defteri/kaynaklar.csv'))}
h={r['ham_id']:r for r in csv.DictReader(open(R/'sonuclar/hesap_defteri/ham_satirlar.csv'))}
rows=list(csv.DictReader(open(K/'ara'/f'{p}.csv'))); random.seed(t)
cache={}
for x in random.sample(rows,n):
    i=x['kaynak_id']; ad=a.get(i,{})
    hid=i[4:] if i.startswith('HAM:') else ''
    kid=hid.split(':')[0]; src=''
    y=kay.get(kid,'')
    if y.endswith('.csv') and not y.startswith('dal:') and hid.split(':')[-1].isdigit():
        if y not in cache: cache[y]=list(csv.reader(open(R/y,encoding='utf-8-sig')))
        try: src=' | '.join(c[:200] for c in cache[y][int(hid.split(':')[-1])][:9])
        except Exception as e: src=str(e)
    print(f"== {i} -> {x['karar']} | {x['neden'][:160]}")
    print(f"   KURAL(aday): {ad.get('kaynak_kurali','')[:300]}")
    if src: print(f"   SRC: {src[:600]}")
    print(f"   kural_tam={x['kural_tam'][:150]} sinif={x['sinif']} bagli={x['bagli_kimlik']} kanit={x['kanit'][:100]}")
