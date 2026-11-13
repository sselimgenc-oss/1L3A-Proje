"""Asli kaynak dosyalarinin satir kayipsiz cikarildigini denetler. Strateji testi degildir."""
import csv,json
from collections import Counter,defaultdict
from envanter import ROOT,OUT,write

def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    roles=read(OUT/'ara/P1_kaynak_rolleri.csv');checks=read(OUT/'ara/P4_P7_sayi_kontrolu.csv');byfile={r['dosya']:r for r in checks};out=[]
    for r in roles:
        if r['ana_ham_sayima_dahil']!='evet':continue
        check=byfile.get(r['dosya'])
        if check is None:raise ValueError('Asli kaynak cikarilmadi: '+r['dosya'])
        assert check['fark']=='0',check
        out.append(dict(kaynak_id=r['kaynak_id'],dosya=r['dosya'],rol=r['rol'],kaynak_kayit=int(check['kaynak_kayit']),ham_kayit=int(check['ham_kayit']),fark=0,birim=check['birim']))
    write('ara/P1_P7_asli_kaynak_kapsami.csv',out,list(out[0]))
    raw=[r for part in ('P4','P5','P6','P7') for r in read(OUT/'ara'/f'{part}_ham.csv')]
    primary={r['dosya'] for r in out};primary_rows=[r for r in raw if r['dosya'] in primary];assert len(primary_rows)==sum(r['ham_kayit'] for r in out)
    write('ara/asli_ham_satirlar.csv',primary_rows,list(primary_rows[0]))
    # TV arsiv sonuclarinin kaynak Pine id'lerinin tamami dis_envanterde var mi?
    old=read(OUT/'ara/P3_arsiv_tv_sonuclari.csv');src=read(ROOT/'stratejiler/dis_envanter.csv')
    stems={r['dosya'].rsplit('/',1)[-1].removesuffix('.pine') for r in src if r['dosya'].endswith('.pine')}
    missing=[r['pine_id'] for r in old if r['pine_id'] not in stems];assert not missing,missing
    summary=dict(asli_kaynak_dosya=len(out),asli_ham_kayit=len(primary_rows),dosya_bazinda_sayim_farki=0,arsiv_tv_sonuc=135,dis_envanterde_pine_id_karsiligi=135,not_='Eski 417/547/707 turlari ve surec/karar tablolari yeni ham strateji sayilmadi; tam ara tablolarda korunuyor')
    (OUT/'ara/asli_kaynak_sayim.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(summary)
if __name__=='__main__':main()
