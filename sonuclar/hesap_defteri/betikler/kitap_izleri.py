"""810 kitap kartinin yapisal yonlendirme ve ayar kosu kanitlari; mantik esdegerligi iddia etmez."""
import csv,json,hashlib
from collections import Counter,defaultdict
from envanter import ROOT,OUT,write

def main():
    books=[]
    for p in sorted((ROOT/'veri/kartlar_ham').rglob('*.json')):
        for i,r in enumerate(json.loads(p.read_text()),1):books.append((r,p.relative_to(ROOT).as_posix(),i))
    ids=[r['kart_id'] for r,_,_ in books]; assert len(ids)==len(set(ids))
    maps=defaultdict(list)
    for rel,field,typ in [('stratejiler/aileler.json','aile_id','giris_ailesi'),('stratejiler/cikis_risk_modulleri.json','modul_id','cikis_risk_modulu')]:
        for i,r in enumerate(json.loads((ROOT/rel).read_text()),1):
            for kid in r['kaynak_kartlar']:maps[kid].append((typ,r[field],f'{rel}:kayit={i}'))
    for i,r in enumerate(json.loads((ROOT/'stratejiler/elenenler.json').read_text()),1):maps[r['kart_id']].append(('ret_kaydi',r['neden'],f'stratejiler/elenenler.json:kayit={i}'))
    with (ROOT/'stratejiler/ek_kaynaklar/kitap_kartlari_eslesme.csv').open() as f:
        for i,r in enumerate(csv.DictReader(f),1):maps[r['kart_id']].append(('yeni_kitap_eslesmesi',json.dumps({k:r[k] for k in ('durum','yeni_aile','gerekce')},ensure_ascii=False),f'stratejiler/ek_kaynaklar/kitap_kartlari_eslesme.csv:kayit={i}'))
    settings=defaultdict(list)
    for p in sorted((ROOT/'stratejiler/kart_ayarlari').glob('*.json')):
        for i,r in enumerate(json.loads(p.read_text()),1):settings[r['kart_id']].append(dict(strateji=p.stem,kanit=f'{p.relative_to(ROOT)}:kayit={i}',parametre_hash=hashlib.sha256(json.dumps(r,sort_keys=True,ensure_ascii=False).encode()).hexdigest()))
    runs=defaultdict(list)
    with (OUT/'ara/P3_test_sonuclari.csv').open() as f:
        for r in csv.DictReader(f):
            if r.get('ayar_kaynagi','').startswith('kart:') and not r['hata']:
                runs[r['ayar_kaynagi'][5:]].append(dict(strateji=r['strateji'],tf=r['tf'],evren=r['evren'] or r['sembol'],islem=r['islem_sayisi'],kanit=f"{r['dosya']}:kayit={r['kayit_no']}"))
    out=[]
    for r,p,i in books:
        kid=r['kart_id'];route=maps[kid]
        out.append(dict(kart_id=kid,ad=r['ad'],kaynak=f'{p}:json=/{i-1}',yonlendirme_turu=';'.join(x[0] for x in route),yonlendirme=json.dumps(route,ensure_ascii=False),ayar_kayit_sayisi=len(settings[kid]),ayar_kaniti=json.dumps(settings[kid],ensure_ascii=False),kosu_kayit_sayisi=len(runs[kid]),kosu_kaniti=json.dumps(runs[kid],ensure_ascii=False),mantik_esdegerligi='denetlenmedi; yonlendirme kopya veya test kaniti degildir'))
    assert all(maps[x] for x in ids),'Yonlendirilmemis kitap karti'
    write('ara/P4_kitap_izleri.csv',out,list(out[0]))
    summary={'kart':len(ids),'tekil_kart_id':len(set(ids)),'yonlendirme_turu':dict(Counter(x['yonlendirme_turu'] for x in out)),'ayari_olan_kart':sum(bool(settings[x]) for x in ids),'kayitli_ayar_kosusu_olan_kart':sum(bool(runs[x]) for x in ids),'yonlendirme_kaydi_yok':sum(not maps[x] for x in ids),'index_kaydi':sum(1 for _ in csv.DictReader((ROOT/'veri/kart_dizini.csv').open()))}
    (OUT/'ara/P4_kitap_sayim.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(summary)
if __name__=='__main__':main()
