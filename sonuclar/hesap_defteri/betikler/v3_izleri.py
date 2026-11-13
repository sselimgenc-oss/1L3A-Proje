"""P6: katalog satiri -> on eleme karari, yalniz acik kaynak/satir baglantisi."""
import csv,json
from collections import defaultdict,Counter
from pathlib import Path
from envanter import ROOT,OUT,write

def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def norm(x):return ' '.join(str(x).split()).casefold()
def main():
    base=ROOT/'stratejiler/v3_adaylar';dec=read(base/'on_eleme.csv');m=defaultdict(list)
    for i,d in enumerate(dec,1):m[d['kaynak_dosya']].append((i,d))
    later=defaultdict(list)
    for name in ('on_eleme_tur2_kod_yok.csv','on_eleme_tur3.csv','on_eleme_tur3_gorev2.csv'):
        for i,r in enumerate(read(base/name),1):later[r['kaynak_dosya'],r['satir_no']].append(dict(dosya='stratejiler/v3_adaylar/'+name,kayit=i,karar=r['karar'],neden=r['neden'],benzer_mevcut=r.get('benzer_mevcut','')))
    out=[];counts=[];unmatched=[]
    for name,ds in sorted(m.items()):
        p=base/'ham'/name;raw=read(p);offset=1 if name.startswith('gemini_') else 2
        assert sorted(int(d['satir_no']) for _,d in ds)==list(range(offset,len(raw)+offset)),name
        counts.append(dict(dosya=p.relative_to(ROOT).as_posix(),kaynak_kayit=len(raw),karar_kayit=len(ds),fark=len(ds)-len(raw),satir_no_kurali=f'kayit_no + {offset-1}; kaynakta dosyaya gore farkli'))
        byno={int(d['satir_no']):(i,d) for i,d in ds}
        for n,r in enumerate(raw,1):
            i,d=byno[n+offset-1];values=[norm(v) for v in r.values() if isinstance(v,str) and v.strip()]
            nameok=norm(d['ad']) in values;urlok=bool(d['url']) and norm(d['url']) in values
            validation='ad_ayni' if nameok else 'URL_ayni' if urlok else 'yalniz_acik_satir_atfi_isim_URL_dogrulamasi_bekliyor'
            rec=dict(kaynak=p.relative_to(ROOT).as_posix(),kaynak_kayit=n,karar_satir_no=d['satir_no'],kaynak_ad=r.get('ad') or r.get('strateji') or r.get('repo') or r.get('URL') or '(ad yok)',karardaki_ad=d['ad'],baglanti_denetimi=validation,ilk_karar=d['karar'],ilk_neden=d['neden'],ilk_karar_kaniti=f'stratejiler/v3_adaylar/on_eleme.csv:kayit={i}',sonraki_kararlar=json.dumps(later[name,d['satir_no']],ensure_ascii=False),mantik_esdegerligi='tekrar/benzer iddiasi burada dogrulanmadi')
            out.append(rec)
            if not nameok and not urlok:unmatched.append(rec)
    assert len(out)==len(dec)==2592
    write('ara/P6_katalog_karar_izleri.csv',out,list(out[0]));write('ara/P6_sayi_kontrolu.csv',counts,list(counts[0]))
    if unmatched:write('ara/P6_atif_dogrulama_kuyrugu.csv',unmatched,list(unmatched[0]))
    summary=dict(katalog_dosya=len(counts),katalog_kayit=len(out),ilk_karar_kayit=len(dec),baglanti_denetimi=dict(Counter(r['baglanti_denetimi'] for r in out)),ilk_karar_dagilimi=dict(Counter(r['ilk_karar'] for r in out)))
    (OUT/'ara/P6_iz_sayim.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(summary)
if __name__=='__main__':main()
