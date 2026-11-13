"""Mevcut sonuc tablolarini okur; arastirma veya test CALISTIRMAZ."""
import csv,gzip,io,json
from collections import Counter
from pathlib import Path
from envanter import ROOT,OUT,write

FIELDS=('strateji','tf','evren','sembol','stil','stil_v2','ayar','ayar_kaynagi','gecti','durum','test_durum','eleme_durum','kesif','nedenler','hata','e1','e2','e3','e4','e5','v1','v2','v3','v4','v5','p1','p2','p3','p4','p5','p6','net_x1','net_x2','pf_x1','n_islem_x1','kill_x1','sharpe_x1','max_dusus_x1','net_getiri','profit_factor','islem_sayisi','n_islem','p','p_rastgele','islem','net','n_aday','n_kosu','n_farkli_ayar','en_sik_ayar','n_disarida','n_hatali','atlandi','etiket','s','kart','n_enstruman_evren','n_enstruman','n_enstruman_islemli','sinif_net','disarida','oos_bas','oos_bit')

def main():
    schemas=json.loads((OUT/'ara/P1_csv_semalari.json').read_text())
    results=[]; counts=[]
    for item in schemas:
        rel=item['dosya']; keys=item['alanlar'] or []
        if not rel.startswith('sonuclar/') or rel.startswith(('sonuclar/hesap_defteri/','sonuclar/dis_arastirma/')) or 'strateji' not in keys: continue
        if '/atlanan_teshis.csv' in rel or '/korelasyon.csv' in rel: continue
        p=ROOT/rel; text=gzip.decompress(p.read_bytes()).decode('utf-8-sig') if p.suffix=='.gz' else p.read_text(encoding='utf-8-sig')
        reader=csv.DictReader(io.StringIO(text)); n=0
        for idx,row in enumerate(reader,1):
            n+=1
            if not row.get('strateji'): raise ValueError(f'Bos strateji: {rel}:{idx}')
            results.append(dict(dosya=rel,kayit_no=idx,fiziksel_bitis_satiri=reader.line_num,**{k:row.get(k,'') for k in FIELDS}))
        assert n==item['n'],(rel,n,item['n'])
        counts.append(dict(dosya=rel,kaynak_kayit=n,cikti_kayit=n,fark=0))
    write('ara/P3_test_sonuclari.csv',results,list(results[0]))
    write('ara/P3_sayi_kontrolu.csv',counts,list(counts[0]))
    e=list(csv.DictReader((ROOT/'sonuclar/evren/v2/eleme.csv').open()))
    structural=[r for r in e if r['e1']=='True' and r['e3']=='True' and r['gecti']=='False' and any(r[k]=='False' for k in ('e2','e4','e5'))]
    write('ara/P3_v2_yapisal_kapi.csv',[{k:r.get(k,'') for k in ('strateji','tf','evren','ayar','e1','e2','e3','e4','e5','nedenler','net_x1','net_x2','pf_x1','n_islem_x1','kill_x1')} for r in structural],['strateji','tf','evren','ayar','e1','e2','e3','e4','e5','nedenler','net_x1','net_x2','pf_x1','n_islem_x1','kill_x1'])
    classes=list(csv.DictReader((OUT/'ara/P2_kod_siniflari.csv').open()))
    seen={r['strateji'] for r in results if not r['hata'] and (r['islem_sayisi'] or r['n_islem_x1'] or r['n_islem'] or r['net_x1'] or r['net_getiri'] or r['profit_factor'])}
    notseen=[dict(**r,not_='Incelenen sonuc CSVlerinde basarili kosu kaniti bulunamadi; JSON/arsiv ve temsilci kapsam incelemesi bitmeden C kesin degil.') for r in classes if r['strateji_id'] not in seen]
    write('ara/P3_kosu_kaniti_bulunamayan.csv',notseen,list(notseen[0]))
    summary=dict(kaynak_dosya=len(counts),sonuc_kaydi=len(results),sonuc_id=len({r['strateji'] for r in results}),basarili_kosu_id=len(seen),v2_satir=len(e),v2_eleme_gecti=sum(r['gecti']=='True' for r in e),v2_yapisal=len(structural),v3_satir=sum(r['dosya']=='sonuclar/v3/eleme.csv' for r in results),kosu_kaniti_bulunamayan=len(notseen))
    (OUT/'ara/P3_sayim.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)); print(summary)
if __name__=='__main__': main()
