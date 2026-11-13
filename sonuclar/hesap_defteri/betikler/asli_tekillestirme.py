"""Asli kaynak kayitlarinda muhafazakar tekillestirme.
Isim/benzerlik skoruyla birlestirme yok. Ayni kaynak ve ayni kural icerigi gerekir.
Bos/tanimsiz mekanik bilgi kopya kaniti kabul edilmez.
"""
import csv,hashlib,json,re
from collections import defaultdict,Counter
from envanter import ROOT,OUT,write

def load(rel):
    with (OUT/rel).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:20]
def main():
    raw=load('ara/asli_ham_satirlar.csv');buckets=defaultdict(list);criteria={}
    for r in raw:
        d=json.loads(r['veri_json']);rel=r['dosya'];key='KAYIT:'+r['ham_id'];reason='Kural esdegerligi kaniti yok; ayri korundu'
        if rel.startswith(('veri/kartlar_ham/','stratejiler/v3_adaylar/kartlar/')):
            kid=d['kart_id'];key='KART:'+kid;reason='Ayni asli kart_id; kart icerigi korunur'
        elif d.get('mekanik_ozet') and d.get('dosya'):
            fields=('dosya','mekanik_ozet','gostergeler','zaman_dilimi','veri_ihtiyaci')
            if all(f in d for f in fields):
                content={f:d[f] for f in fields}
                content['kaynak_sahibi']='yerel_arsiv_yolu' if str(d['dosya']).startswith('arsiv/') else d.get('repo') or d.get('kaynak') or rel
                key='KURAL:'+digest(content);reason='Ayni kaynak sahibi/dosyasi ve ayni mekanik ozet/gostergeler/TF/veri; ad kullanilmadi'
        elif rel.endswith('/ajan1/strateji_listesi.csv'):
            key='DIS906:'+d['id'];reason='906 son liste, sabit kaynak id; eski surumler kapsam disi'
        elif rel.endswith('2026-11_freqtrade_robotic/dosya_listesi.csv'):
            key='ROBOTIC:'+digest(d['dosya']);reason='Tam dosya yolu; kume kopya iddiasi dogrulanmadigi icin 909 dosya ayri'
        elif '/v3_adaylar/ham/' in rel:
            # Katalog alt kume CSVlerinin ayni kaynakta ayni kurali anlatan birebir kayit kopyalari.
            mechanism=d.get('kural_ozeti') or d.get('giris_kurali_kisa') or d.get('giris_kurali') or d.get('kurallar')
            origin=d.get('url') or d.get('URL') or d.get('kaynak_url') or d.get('kod_linki')
            if origin and any(d.get(k) for k in ('strateji','ad','giris_kurali','kurallar')):
                key='TAMKAYIT:'+digest(d);reason='Ayni asli kaynak adresi ve kaydin TUM alanlari birebir ayni; ayni kaynak kaydi kopyasi, benzer ada dayali denklesme degil'
        elif rel.endswith('.xlsx'):
            fields=('ID','URL','Strateji Adı','Özet','Giriş','Çıkış','Göstergeler','Zaman Dilimi','Tür')
            if all(f in d for f in fields) and d.get('URL') and any(d.get(f,'').strip().casefold() not in ('','belirtilmemiş','belirtilmemis','?') for f in ('Giriş','Çıkış')):
                key='EXCELKURAL:'+digest(d);reason='Ayni kaynak ID/URL ve kaydin tum alanlari birebir ayni; eksik/kucuk kural farki birlestirilmedi'
        r['tekil_id']=key;buckets[key].append(r);criteria[key]=reason
    # Bir mekanik kayit eksik bilgi yuzunden farkli kaldiginda "tekil strateji kesin sayisi" iddia edilmez.
    links=[];nodes=[]
    for sid,rs in sorted(buckets.items()):
        for r in rs:links.append(dict(ham_id=r['ham_id'],tekil_id=sid,dayanak=criteria[sid]))
        nodes.append(dict(tekil_id=sid,ad=rs[0]['kaynaktaki_ad'],ham_kayit=len(rs),kaynak_sayisi=len({r['kaynak_id'] for r in rs}),tekillestirme_dayanagi=criteria[sid],kanit=';'.join(r['dosya']+'#'+r['kaynak_satir_no'] for r in rs),mantik_hukmu='ayri_kayit' if len(rs)==1 else 'ayni_kaynak_kaydi_icerigi_ayni',not_='Asil ucuncu taraf kodu veya tam kural olmayan kaynaklarda anlamca kopya karari verilmedi'))
    assert len(links)==len(raw) and len({r['ham_id'] for r in links})==len(raw)
    write('ara/P8_asli_ham_tekil_baglantisi.csv',links,list(links[0]));write('ara/P8_asli_kimlik_dugumleri.csv',nodes,list(nodes[0]));write('ara/P8_asli_ham_tekillestirilmis.csv',raw,list(raw[0]))
    summary=dict(ham=len(raw),muhafazakar_kayit_dugumu=len(nodes),icerigi_ayni_ek_kopya=len(raw)-len(nodes),cok_kayitli_dugum=sum(len(v)>1 for v in buckets.values()),not_='Bu asama kaynak-kod denklesmesini cozmuyor; isim veya benzer aileyle birlestirme yapilmadi')
    (OUT/'ara/P8_asli_tekillestirme_sayim.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(summary)
if __name__=='__main__':main()
