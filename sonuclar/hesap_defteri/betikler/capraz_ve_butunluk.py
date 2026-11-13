"""Satir ve kimlik butunlugu, kaynak hashleri, belge sayilarinin baglamli karsilastirmasi."""
import ast,csv,hashlib,json,subprocess
from collections import Counter,defaultdict
from pathlib import Path
from envanter import ROOT,OUT,write

def load(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    inv=load(OUT/'kaynaklar.csv');raw=load(OUT/'ham_satirlar.csv');nodes=load(OUT/'tekil_stratejiler.csv');primary=load(OUT/'ara/asli_ham_satirlar.csv')
    source_ids={r['kaynak_id'] for r in inv};ids={r['tekil_id'] for r in nodes};byid={r['tekil_id']:r for r in nodes};counts=Counter(r['tekil_id'] for r in raw)
    assert len(ids)==len(nodes) and len({r['ham_id'] for r in raw})==len(raw)
    assert set(counts)==ids and all(r['kaynak_id'] in source_ids for r in raw)
    assert all(int(r['ham_kayit_sayisi'])==counts[r['tekil_id']] for r in nodes)
    assert len(primary)+521==len(raw)
    assert not any('/ajan1/tur'+str(t)+'/' in r['dosya'] for r in raw for t in (1,2,3))
    assert sum(r['dosya'].endswith('/ajan1/strateji_listesi.csv') for r in raw)==906
    assert sum(r['dosya'].endswith('2026-11_freqtrade_robotic/dosya_listesi.csv') for r in raw)==909
    for p in ('P3_sayi_kontrolu.csv','P4_P7_sayi_kontrolu.csv','P1_P7_asli_kaynak_kapsami.csv'):
        rows=load(OUT/'ara'/p)
        for r in rows:
            assert int(r['fark'])==0,(p,r)
    changed=[]
    for r in inv:
        p=ROOT/r['dosya']
        if r['sha256'] and hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:changed.append(r['dosya'])
    assert not changed,changed
    # Gerçek ilk ekleme tarihleri; geliş tarihi diye tahmin edilmez.
    if any(not r['gelis_tarihi'] for r in inv):
        missing=[r for r in inv if not r['gelis_tarihi']]
        for r in missing:
            d=subprocess.check_output(['git','log','--reverse','--diff-filter=A','--format=%aI','--',r['dosya']],cwd=ROOT,text=True).splitlines()
            r['gelis_tarihi']=d[0] if d else 'BELIRSIZ'
        write('kaynaklar.csv',inv,list(inv[0]))
    # Tarihsel kod sayısı, aynı tarihli Git nesnelerinden salt okunur AST ile.
    historical=[]
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only','c10e79d','motor/strateji','motor/portfoy'],cwd=ROOT,text=True).splitlines()
    for rel in paths:
        if not rel.endswith('.py'):continue
        tree=ast.parse(subprocess.check_output(['git','show','c10e79d:'+rel],cwd=ROOT,text=True))
        for node in ast.walk(tree):
            if not isinstance(node,ast.ClassDef):continue
            for n in node.body:
                if not isinstance(n,ast.Assign):continue
                for target in n.targets:
                    names=[target.id] if isinstance(target,ast.Name) else [a.id if isinstance(a,ast.Name) else '' for a in target.elts] if isinstance(target,(ast.Tuple,ast.List)) else []
                    if 'ad' not in names:continue
                    value=n.value
                    if isinstance(value,(ast.Tuple,ast.List)):value=value.elts[names.index('ad')]
                    if isinstance(value,ast.Constant) and isinstance(value.value,str) and value.value:historical.append((value.value,rel))
    oldsg=[x for x in historical if x[1].startswith('motor/strateji/')];oldpf=[x for x in historical if x[1].startswith('motor/portfoy/') and not x[0].startswith('ornek__')]
    assert len(oldsg)==460 and len(oldpf)==19,(len(oldsg),len(oldpf))
    configs=load(OUT/'ara/P5_ayar_kosu_izleri.csv')
    comparisons=[
      dict(konu='460 tek grafik +19 portföy',beyan='DURUM.md:407, 2026-11-08',olcum=f'c10e79d: {len(oldsg)} + {len(oldpf)}; güncel:492 +29=521',hukum='Tarihsel sayı doğru; bugünkü tüm kaynak veya test adedi değil',kanit='Git c10e79d; ara/P2_kod_denetimli.csv'),
      dict(konu='~120 ek ayar/mod',beyan='DURUM.md:407',olcum='177 dis_ayarlari +11 d11j +7 d12b=195 yazılı ayar; kitap226 ile421. 336 ayar için özgül kaynak kimlikli koşu kaydı,85 için yok.',hukum='Yaklaşık sayının birimi açık değil;195 yazılı kayıtla birebir eşit değil. Kod ailesinin testi her ayarın testi değil.',kanit='ara/P5_ayar_kosu_izleri.csv; c10e79d aynı ayar dosyaları'),
      dict(konu='Kart dizini',beyan='veri/kart_dizini.csv:438',olcum='810 güncel kitap kartı; v3 kartları154 ayrı',hukum='Dizin kitap kartlarının tamamını kapsamıyor',kanit='ara/P4_kitap_sayim.json; ara/P4_kitap_izleri.csv'),
      dict(konu='v3 kod ve koşu',beyan='35 kod tanımı / eleme9',olcum='35=9 sonuç+26 koşu kanıtsız',hukum='Doğrulandı; C gerçek kod listesi26, kaynak profilleriyle53 görünmesi53 ayrı kod değil',kanit='ara/P8_v3_kosulmayan_26.csv; sonuclar/v3/eleme.csv'),
      dict(konu='v2 yapısal eleme',beyan='222 havuz;73 E1/E3 geçtiği halde elendi',olcum='222,73; ayrıca6 hata',hukum='Doğrulandı; hata performans elemesi değil',kanit='ara/P3_v2_yapisal_kapi.csv; ara/P3_v2_hata_satirlari.csv'),
      dict(konu='GitHub g1..g7',beyan='DURUM.md:1198',olcum=str(sum(len(load(ROOT/'stratejiler/ek_kaynaklar'/p)) for p in ('github_g1_freqtrade.csv','github_g2_kripto_bot.csv','github_g3_cerceve.csv','github_g4_platform.csv','github_g5_mt_pine.csv','github_g6_liste_notebook.csv','github_g7_kutuphane.csv'))),hukum='Satır sayısı; bağımsız strateji/test sayısı değil',kanit='ara/P4_P7_sayi_kontrolu.csv'),
      dict(konu='Kakushadze 151',beyan='Kitap/katalog adı151',olcum='CSV173',hukum='Kitap başlığı ile envanter alt strateji satırı farklı birim',kanit='stratejiler/ek_kaynaklar/kakushadze_151.csv'),
      dict(konu='Repo raporları',beyan='DURUM.md eski314',olcum='Güncel CSV331',hukum='Farklı sürüm;314 bugünkü kapsam sayısı değil',kanit='stratejiler/ek_kaynaklar/repo_raporlari.csv'),
      dict(konu='Dış liste turları',beyan='417/547/707/906',olcum='906 son liste;707+199=906',hukum='Üst kümeler; eski turlar ham sayımda yok.18 kural/parametre sürüm farkı korundu',kanit='ara/P7_sayim.json; ara/P7_surum_mantik_farklari.csv'),
      dict(konu='Robotic909/540',beyan='909 dosya/540küme',olcum='909 dosya,540 üyelik kümesi; toplamsal üyelik909',hukum='Üyelik doğrulandı;540 mantıksal tekil strateji olduğu ispatlanmadı',kanit='ara/P7_robotic_kume_uyelik.csv'),
      dict(konu='ChatGPT26',beyan='Ajan2 raporu26',olcum='Tekil CSV yok;1 eksik-liste toplu kaydı',hukum='26 adı/kuralı uydurulmadı; satır kapsamı doğrulanamaz',kanit='sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/ajan2/derin_arastirma_26_kayit_raporu.md')]
    write('ara/P9_belge_sayi_karsilastirma.csv',comparisons,list(comparisons[0]))
    # Karşılıklı aynı içerik kopyaları; birleşim gerekçesindeki alanlar yeniden karşılaştırılır.
    groups=defaultdict(list)
    for r in raw:
        if r['kayit_turu']!='operasyonel_kod':groups[r['tekil_id']].append(json.loads(r['veri_json']))
    for sid,rs in groups.items():
        if len(rs)<2:continue
        if sid.startswith(('TAMKAYIT:','EXCELKURAL:')):assert all(d==rs[0] for d in rs)
        elif sid.startswith('KURAL:'):
            for d in rs:assert all(d.get(k)==rs[0].get(k) for k in ('dosya','mekanik_ozet','gostergeler','zaman_dilimi','veri_ihtiyaci'))
    summary=dict(ham=len(raw),dugum=len(nodes),kaynak_hash_kontrolu=len(inv),kaynak_hash_farki=0,ham_tekil_orphan=0,duplicate_ham_id=0,sayi_farki=0,harici_orijinal_kod_esdegerligi='İddia edilmedi; BELIRSIZ ve zayıf temsilci korunur',kod_historical_460_19_dogrulandi=True,ayar_kaydi=len(configs),ayar_kosu_kaniti_yok=sum(int(r['kosu_kaydi'])==0 for r in configs))
    (OUT/'ara/P9_butunluk.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(summary)
if __name__=='__main__':main()
