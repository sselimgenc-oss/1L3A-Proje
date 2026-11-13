"""P7 yapisal kapsam denetimi. Onceki eslesme/tekillik hukumlerini dogru saymaz."""
import csv,json
from collections import Counter,defaultdict
from envanter import ROOT,OUT,write

def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    b=ROOT/'sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus'; latest=read(b/'ajan1/strateji_listesi.csv'); byid={r['id']:r for r in latest};assert len(latest)==len(byid)==906
    checks=[];versions=[];diffs=[]
    for tour,n in [('tur1',417),('tur2',547),('tur3',707)]:
        rel='sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/ajan1/'+tour+'/strateji_listesi.csv';old=read(ROOT/rel); assert len(old)==n
        missing=set(r['id'] for r in old)-set(byid);assert not missing,(tour,missing)
        linkdiff=[r['id'] for r in old if r['kaynak_link']!=byid[r['id']]['kaynak_link']]
        for r in old:
            newer=byid[r['id']]
            changed=[k for k in ('strateji_adi','giris_kurali','cikis_kurali','stop_kurali','parametreler','kaynak_link') if r.get(k)!=newer.get(k)]
            if changed:diffs.append(dict(surum=tour,id=r['id'],degisen_alanlar=';'.join(changed),kanit=rel+'#'+r['id'],not_='Surum farki; eski tur yeni ham strateji sayilmaz, mantik degisikligi kayda alindi'))
        versions.append(dict(dosya=rel,satir=len(old),guncelde_eksik_id=len(missing),degisen_link=len(linkdiff),ana_ham_sayima_dahil='hayir',gerekce='Kullanici talimati: yalniz 906 son liste sayilir'))
    cmp=read(b/'karsilastirma/karsilastirma.csv');new=read(b/'tur4_degerlendirme/yeni_199.csv');ids1={r['dis_id'] for r in cmp};ids2={r['dis_id'] for r in new}
    assert len(cmp)==len(ids1)==707 and len(new)==len(ids2)==199 and not(ids1&ids2) and ids1|ids2==set(byid)
    rb=ROOT/'sonuclar/dis_arastirma/2026-11_freqtrade_robotic';files=read(rb/'dosya_listesi.csv');clusters=read(rb/'kume_listesi.csv');assert len(files)==909 and len(clusters)==540
    assert len({r['dosya'] for r in files})==909
    members=Counter(r['kume_id'] for r in files);lookup={r['kume_id']:r for r in clusters};assert len(lookup)==540;assert set(members)==set(lookup)
    memberrows=[]
    for key,r in lookup.items():
        expected=int(r['dosya_sayisi']);actual=members[key]
        memberrows.append(dict(kume_id=key,beyan_dosya=expected,listede_dosya=actual,fark=actual-expected,kanit='sonuclar/dis_arastirma/2026-11_freqtrade_robotic/kume_listesi.csv#'+key))
        assert expected==actual,(key,expected,actual)
    checks=[dict(kontrol='906 son liste',kaynak=906,cikti=len(latest),fark=len(latest)-906),dict(kontrol='707 + 199 ayri id birlesimi',kaynak=906,cikti=len(ids1|ids2),fark=0),dict(kontrol='909 dosya',kaynak=909,cikti=len(files),fark=0),dict(kontrol='540 kume uyelik toplami',kaynak=909,cikti=sum(members.values()),fark=0)]
    write('ara/P7_surum_kapsami.csv',versions,list(versions[0]));write('ara/P7_surum_mantik_farklari.csv',diffs,list(diffs[0]));write('ara/P7_robotic_kume_uyelik.csv',memberrows,list(memberrows[0]));write('ara/P7_sayi_kontrolu.csv',checks,list(checks[0]))
    summary=dict(son_liste=906,eski_turlar_sayima_dahil=False,surum_mantik_ve_link_fark_kaydi=len(diffs),dosya=909,kume=540,robotic_dosya_sinif_beyani=dict(Counter(r['dosya_sinif'] for r in files)),robotic_kume_sinif_beyani=dict(Counter(r['sinif'] for r in clusters)),not_='Kume uyeligi dogrulandi; kopya/benzer mantik iddialari dogrulanmadi. Ajan2 26 tekil satir CSVsi mevcut degil.')
    (OUT/'ara/P7_sayim.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(summary)
if __name__=='__main__':main()
