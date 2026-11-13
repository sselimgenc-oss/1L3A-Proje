"""Denetlenebilir son CSVleri hazirlar; orneklem/rapor ayrica uretilir."""
import csv,json,hashlib,re
from collections import Counter,defaultdict
from envanter import ROOT,OUT,write

def load(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    rows=load(OUT/'ara/P8_tekil_akibet_ARA.csv');raw=load(OUT/'ara/P8_asli_ham_tekillestirilmis.csv');classes=load(OUT/'ara/P2_kod_denetimli.csv');sources=load(OUT/'kaynaklar.csv');source_by_path={r['dosya']:r for r in sources};codes={r['strateji_id']:r for r in classes}
    results=load(OUT/'ara/P3_test_sonuclari.csv');history=defaultdict(list)
    for r in results:history[r['strateji']].append(r)
    for c in classes:
        if c['kayit_durumu']=='kayit_disinda_ornek':continue
        rel=c['dosya'];raw.append(dict(ham_id='HKOD'+hashlib.sha256((rel+':'+c['sinif']).encode()).hexdigest()[:16],kaynak_id=source_by_path[rel]['kaynak_id'],kaynaktaki_ad=c['strateji_id'],kaynak_satir_no='AST:sinif:'+c['sinif']+';satir:'+c['satir'],tekil_id='KOD:'+c['strateji_id'],dosya=rel,kayit_turu='operasyonel_kod',kaynak_kimligi=c['strateji_id'],veri_json=json.dumps(c,ensure_ascii=False)))
    counts=Counter(r['tekil_id'] for r in raw);src_counts=defaultdict(set)
    for r in raw:src_counts[r['tekil_id']].add(r['kaynak_id'])
    for r in rows:
        r['kaynak_sayisi']=len(src_counts[r['tekil_id']]);r['ham_kayit_sayisi']=counts[r['tekil_id']]
        r['not']=r.pop('not_');r['aile']=r['aile'] if r['aile'] in ('trend','MR') else 'diğer'
        r['ayar_kapsami']='BELIRSIZ; kaynak kuralı/ayarının tam koşusu kanıtlanamadı';r['islem_kaniti']='BELIRSIZ; işlem sayısı kaynağından doğrulanmalı'
        targets=r['uygulama_idleri'].split(';') if r['uygulama_idleri'] else []
        evidence=[];settings=set()
        for target in targets:
            h=history[target]
            settings.update(x['ayar_kaynagi'].split(':',1)[0] for x in h if x['ayar_kaynagi'])
            selected=[x for x in h if x['dosya']+':kayit='+x['kayit_no'] in r['kanit_dosyasi']]
            if not selected:
                stage='sonuclar/evren/v2/eleme.csv' if 'v2' in r['asama'] else 'sonuclar/v3/eleme.csv' if 'v3' in r['asama'] else None
                selected=[x for x in h if x['dosya']==stage]
            for x in selected:
                metrics={k:x[k] for k in ('tf','evren','sembol','ayar','ayar_kaynagi','islem_sayisi','n_islem_x1','n_islem','islem','net_x1','net_x2','kill_x1','pf_x1','p','e1','e2','e3','e4','e5','n_enstruman_evren','n_enstruman','n_enstruman_islemli','sinif_net','disarida','oos_bas','oos_bit') if x[k]}
                evidence.append(dict(uygulama=target,kanit=x['dosya']+':kayit='+x['kayit_no'],**metrics))
        if evidence:r['islem_kaniti']=json.dumps(evidence,ensure_ascii=False)
        if targets:r['ayar_kapsami']='Uygulama tarihçesinde: '+(','.join(sorted(settings)) or 'ayar etiketi yok')+'; özgün kaynakla eşdeğerlik iddiası değildir. Tüm TF/evren/ayar/işlem satırları ara/P8_kod_tarihce.csv içinde; dönemler toplanmadı.'
        if r['durum']=='C_KODLANDI_KOSULMADI':r['islem_kaniti']='Araştırma koşusu kanıtı yok; işlem sayısı üretilmedi.'
        if r['asama']=='onceki proje TV arsiv olcumu':r['islem_kaniti']='Eski JSONlardaki metrikler kapi_ve_deger alanında; ara/P3_arsiv_tv_sonuclari.csv. Güncel test değildir.';r['ayar_kapsami']='Eski TV arşiv ayarı; özgün kaynak/kod eşdeğerliği doğrulanmadı.'
    assert len(raw)==len({r['ham_id'] for r in raw})
    assert set(counts)=={r['tekil_id'] for r in rows}
    assert all(r['kanit_dosyasi'] and r['durum'] for r in rows)
    write('ham_satirlar.csv',raw,list(raw[0]))
    write('tekil_stratejiler.csv',rows,list(rows[0]))
    # Kesin E yoksa da uygulanma/karar izi eksik olanlar görünür kalir.
    gaps=[dict(r) for r in rows if r['durum']=='BELIRSIZ' and r['birim_turu']=='kaynak_strateji_kaydi' and not r['uygulama_idleri'] and ('açık uygulama veya gerekçeli eleme zinciri bulunamadı' in r['kapi_ve_deger'] or 'boşluğu adayı' in r['not'])]
    for r in gaps:r['E_kesinlestirmeme_nedeni']='İz eksikliği adayı; aynı mantığın adsız/farklı adlı kodu olmadığını veya karar kaydının bulunmadığını kesinleştirecek tam özgün kural yok. Kanıtsız E hükmü verilmedi.'
    if gaps:write('ara/P8_iz_eksigi_E_adaylari.csv',gaps,list(gaps[0]))
    for code in ('A','B','C','D','E','F','G','H','BELIRSIZ'):
        group=[r for r in rows if r['durum'].split('_')[0]==code]
        write('ara/AKIBET_'+code+'.csv',group,list(rows[0]))
    source_count=len({r['kaynak_id'] for r in raw});current_codes=[r for r in rows if r['birim_turu']=='operasyonel_kod']
    summary=dict(envanter_dosyasi=len(sources),ham_kaynak_dosyasi=source_count,ham=len(raw),tekil_kayit_profili=len(rows),durum=dict(Counter(r['durum'] for r in rows)),birim_turu=dict(Counter(r['birim_turu'] for r in rows)),operasyonel_kod=len(current_codes),kod_durum=dict(Counter(r['durum'] for r in current_codes)),E_iz_eksigi_adayi=len(gaps),tekil_tablo_sha256=hashlib.sha256((OUT/'tekil_stratejiler.csv').read_bytes()).hexdigest())
    (OUT/'ara/nihai_sayim.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(summary)
if __name__=='__main__':main()
