"""Ayar/kosu baglari, v3 farki, belge kapsam izleri ve grup uyeleri. Strateji calistirmaz."""
import csv,json,re
from collections import defaultdict,Counter
from envanter import ROOT,OUT,write

def load(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    results=load(OUT/'ara/P3_test_sonuclari.csv');index=defaultdict(list)
    for r in results:index[(r['strateji'],r['ayar_kaynagi'])].append(r)
    configs=[]
    for folder in ('dis_ayarlari','kart_ayarlari'):
        prefix='dis:' if folder=='dis_ayarlari' else 'kart:'
        for p in sorted((ROOT/'stratejiler'/folder).glob('*.json')):
            obj=json.loads(p.read_text());obj=obj if isinstance(obj,list) else [obj]
            for i,d in enumerate(obj):
                key=d.get('dis_id') or d.get('kart_id') or '';sid=p.stem;matches=index[sid,prefix+key]
                configs.append(dict(dosya=str(p.relative_to(ROOT)),json_isaretci='/'+str(i),strateji=sid,kaynak_kimligi=key,parametre=json.dumps(d.get('parametreler',{}),ensure_ascii=False),cikis=json.dumps(d.get('cikis_ayarlari'),ensure_ascii=False),varsayim=d.get('not',''),kosu_kaydi=len(matches),kosu_kaniti=';'.join(r['dosya']+':kayit='+r['kayit_no'] for r in matches),sinir='Ayar koşusu kaynak kuralının bütün filtrelerini temsil etmeyebilir; kapısız tarama geçiş/eleme değildir.'))
    for rel in ('stratejiler/ayarlar_d11j_ek.json','stratejiler/ayarlar_d12b_ek.json'):
        for i,d in enumerate(json.loads((ROOT/rel).read_text())):
            sid=d.get('hedef','');key=d.get('ayar_id','');matches=[r for r in results if r['strateji']==sid and (r['ayar']==key or r['ayar_kaynagi']==key)]
            configs.append(dict(dosya=rel,json_isaretci='/'+str(i),strateji=sid,kaynak_kimligi=key,parametre=json.dumps(d.get('parametreler',{}),ensure_ascii=False),cikis=json.dumps(d.get('cikis_ayarlari'),ensure_ascii=False),varsayim=d.get('not',''),kosu_kaydi=len(matches),kosu_kaniti=';'.join(r['dosya']+':kayit='+r['kayit_no'] for r in matches),sinir='Özgül ayar kimliğiyle sonuç eşlemesi; genel aile koşusu bu ayarın koştuğu anlamına gelmez.'))
    write('ara/P5_ayar_kosu_izleri.csv',configs,list(configs[0]))
    missing=[r for r in load(OUT/'ara/P8_kod_akibet_GECICI.csv') if r['durum']=='C_KODLANDI_KOSULMADI' and 'v3' in r['tekil_id']]
    assert len(missing)==26
    write('ara/P8_v3_kosulmayan_26.csv',missing,list(missing[0]))
    errors=[r for r in results if r['dosya']=='sonuclar/evren/v2/eleme.csv' and r['hata']];assert len(errors)==6
    write('ara/P3_v2_hata_satirlari.csv',errors,list(errors[0]))
    paper=[]
    for p in sorted((ROOT/'sonuclar/paper_v2/uyum').glob('*.json')):
        d=json.loads(p.read_text());ref=d.get('referans',{});repeat=d.get('paper',{})
        paper.append(dict(strateji=d.get('strateji',''),dosya=str(p.relative_to(ROOT)),tf=d.get('tf',''),etiket=d.get('etiket',''),referans_net=ref.get('net',''),paper_tekrar_net=repeat.get('net',''),referans_n=ref.get('n_islem',''),paper_tekrar_n=repeat.get('n_islem',''),asama='geçmiş paper tekrar uyum raporu; ileri paper performansı DEĞİL'))
    if paper:write('ara/P3_paper_tekrar_uyum.csv',paper,list(paper[0]))
    # Karar zincirleri farki: onceki etiket mutlaka ayni kapsami ifade etmeyebilir.
    traces=load(OUT/'ara/P6_katalog_karar_izleri.csv');amb=[]
    for r in traces:
        hist=json.loads(r['sonraki_kararlar'])
        for h in hist:
            if 'gorev2' in h['dosya']:
                amb.append(dict(kaynak=r['kaynak'],kayit=r['kaynak_kayit'],onceki_zincir=json.dumps(hist,ensure_ascii=False),not_='gorev2 atfı önceki tablo/kart kapsamını farklı kullanabilir; son etiket kural/test eşitliği kanıtı değildir.'))
    if amb:write('ara/P6_gorev2_kapsam_notlari.csv',amb,list(amb[0]))
    primary=load(OUT/'ara/P8_asli_ham_tekillestirilmis.csv');groups=[]
    for r in primary:
        d=json.loads(r['veri_json']);name=r['kaynaktaki_ad'];members=[]
        if name.startswith('Mikro-cap kripto RSI'):members=[('Mikro-cap kripto RSI','BELIRSIZ'),('SMA kesişimi','BELIRSIZ'),('XGBoost bot','G_ML')]
        elif 'HMM sektör rotasyonu vs' in name:members=[('HMM sektör rotasyonu','G_ML'),('aylık DCA','F_YASAK_TIP')]
        elif 'CEZLSMA' in str(d) and 'NWERSIASF' in str(d):members=[(x,'BELIRSIZ') for x in ('CEZLSMA','3MAF','CP1','BBRSI','ABSAR','DHLAOS','MLCEL_MACD','NWERSIASF','LRCUTB')]
        for member,state in members:groups.append(dict(ham_id=r['ham_id'],ust_tekil_id=r['tekil_id'],uye_ad=member,uye_tur_beyani=state,kanit=r['dosya']+'#'+r['kaynak_satir_no'],sinir='Kaynakta adı verilen bileşen; tam giriş/çıkış yok. Üst ham satır sayısını artırmaz; adlardan kural uydurulmadı.'))
    if groups:write('ara/P8_grup_uyeleri.csv',groups,list(groups[0]))
    queue=load(OUT/'ara/P4_P7_belge_inceleme_kuyrugu.csv');doc=[]
    known=load(OUT/'ara/belge_atiflari.csv');keys=known[0].keys();filekey='dosya' if 'dosya' in keys else next(iter(keys))
    for r in queue:
        rel=r['dosya'];text=(ROOT/rel).read_text();refs=re.findall(r'[\w./-]+\.(?:csv|json|xlsx)',text)
        if 'tam_okuma_' in rel:why='Kitap kartı/güncelleme raporu; kart JSONları ve tam_okuma_guncelleme_ozet.csv ham/karar katmanında.'
        elif rel.endswith('kiyas_ayar.json'):why='Karşılaştırma çalışma ayarı; bağımsız giriş stratejisi değil.'
        elif any(x in rel for x in ('KART_SEMASI','CODEX_KODLAMA','TALIMAT','README','BENIOKU')):why='Şema/talimat/erişim belgesi; yeni strateji listesi değil.'
        elif 'profesyonel_' in rel:why='Yayın kanalları/erişim haritası; strateji tanımları katalogda, platform adları strateji sayılmadı.'
        elif 'VOL_YONETIMLI' in rel:why='Mevcut kart/kod uygulama gerekçesi; pf__v3-vol-yonetimli-long prototipi ayrı kod satırında.'
        else:why='Yapılandırılmış katalog/karar tablolarının anlatımı ve kaynak id atıfları; yeni bağımsız strateji sayısına eklenmedi. Ayrıntılı kuralların eşdeğerliği ispatlanmış sayılmaz.'
        doc.append(dict(dosya=rel,satir=len(text.splitlines()),islem=why,belgedeki_tablo_atiflari=';'.join(dict.fromkeys(refs)),sinir='Otomatik belge atıf indeksi ve dosya kapsamı; üçüncü taraf kodun eksiksiz doğrulanması iddia edilmez.'))
    write('ara/P5_P7_belge_kapsam_kararlari.csv',doc,list(doc[0]))
    summary=dict(ayar_sayisi=len(configs),kosu_kanitli_ayar=sum(int(r['kosu_kaydi'])>0 for r in configs),v3_kosulmayan=len(missing),v2_hata=len(errors),belge_kapsami=len(doc),grup_uye_atfi=len(groups))
    (OUT/'ara/ek_iz_sayim.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(summary)
if __name__=='__main__':main()
