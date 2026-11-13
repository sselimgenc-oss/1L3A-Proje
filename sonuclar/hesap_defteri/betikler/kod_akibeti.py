"""P8 ara adim: operasyonel ad kimliklerinin sonuc zinciri. Kaynak-kod denklesmesi DEGILDIR."""
import ast,csv,json,re
from collections import defaultdict,Counter
from envanter import ROOT,OUT,write

def read(rel):
    with (ROOT/rel).open(encoding='utf-8-sig',newline='') as f:
        rd=csv.DictReader(f)
        return [dict(r,_kanit=f'{rel}:kayit={i}') for i,r in enumerate(rd,1)]

def main():
    classes=list(csv.DictReader((OUT/'ara/P2_kod_denetimli.csv').open()))
    history=defaultdict(list)
    with (OUT/'ara/P3_test_sonuclari.csv').open() as f:
        for r in csv.DictReader(f): history[r['strateji']].append(r)
    stages={}
    for path in ('sonuclar/evren/v2/eleme.csv','sonuclar/evren/v2/test.csv','sonuclar/evren/v2/saglamlik.csv','sonuclar/evren/v2/set.csv','sonuclar/v3/eleme.csv','sonuclar/evren/2017_gelistirme/wf_evren.csv','sonuclar/evren/2017_gelistirme/saglamlik.csv'):
        m=defaultdict(list)
        for r in read(path):m[r['strateji']].append(r)
        stages[path]=m
    paper=json.loads((ROOT/'stratejiler/paper_v2_seti.json').read_text())
    paper_ids={r['strateji']:r for r in paper['stratejiler']}
    hold_ids={r['strateji'] for r in json.loads((ROOT/'sonuclar/evren/v2/holdout/paper_girdisi.json').read_text())['set']}
    rows=[]; timelines=[];trees={}
    def describe(c):
        if c['dosya'] not in trees:trees[c['dosya']]=ast.parse((ROOT/c['dosya']).read_text())
        node=next(n for n in ast.walk(trees[c['dosya']]) if isinstance(n,ast.ClassDef) and n.name==c['sinif'])
        doc=ast.get_docstring(node) or ''
        methods=[n for n in node.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in ('sinyaller','_sinyal','_hedef','hedefler')]
        mechanics=' | '.join(ast.unparse(n) for n in methods)
        return (doc[:750] if doc else 'Sınıf açıklaması yok; gerçek giriş/hedef gövdesi: '+mechanics[:750] if mechanics else 'Sınıf açıklaması yok; miras alınan mantık. Temel sınıflar: '+c['temel_siniflar'])

    for c in classes:
        sid=c['strateji_id']; h=history[sid];state='BELIRSIZ';phase='';gate='';evidence='';structural='hayir';fair='BELIRSIZ';note='Kaynak stratejilerle mantik denkligi bu tabloda kurulmaz.'
        selected=[]
        if c['kayit_durumu']=='kayit_disinda_ornek':note+=' Kayit disinda ornek; uretim stratejisi sayisina katilmaz.'
        elif sid in stages['sonuclar/v3/eleme.csv']:
            selected=stages['sonuclar/v3/eleme.csv'][sid];phase='v3 eleme';state='B_TEST_EDILDI_ELENDI';gate='; '.join(r['nedenler'] for r in selected)
        elif sid in hold_ids:
            phase='v2 resmi holdout SET kapisi';state='A_TEST_EDILDI_GECTI';gate='SET kapisi gecti; bireysel karli olma/gelecek avantaj kaniti degil';evidence='sonuclar/evren/v2/holdout/paper_girdisi.json;sonuclar/evren/v2/holdout/holdout_raporu.md'
        elif sid in stages['sonuclar/evren/v2/eleme.csv']:
            selected=stages['sonuclar/evren/v2/eleme.csv'][sid];phase='v2 eleme'
            if any(r.get('hata') for r in selected):
                state='BELIRSIZ';gate='; '.join(r['hata'] for r in selected);note+=' Son v2 kosusunda altyapi/uygunluk hatasi var; olculmus basarisizlik diye siniflandirilmadi.'
            elif any(r['gecti']=='False' for r in selected):
                state='B_TEST_EDILDI_ELENDI';gate='; '.join(r['nedenler'] for r in selected)
                structural='evet' if any(r['e1']=='True' and r['e3']=='True' and r['gecti']=='False' for r in selected) else 'hayir'
            else:
                t=stages['sonuclar/evren/v2/test.csv'].get(sid,[])
                if t and all(r['kesif']=='False' for r in t):
                    selected=t;phase='v2 resmi test/BH';state='B_TEST_EDILDI_ELENDI';gate='; '.join('kesif='+r['kesif']+';p='+r['p']+';bh_esik='+r['bh_esik'] for r in t)
                else:
                    ss=stages['sonuclar/evren/v2/saglamlik.csv'].get(sid,[])
                    if ss and any(r['saglam']=='False' for r in ss):
                        selected=ss;phase='v2 saglamlik';state='B_TEST_EDILDI_ELENDI';gate='; '.join('liste='+r['liste']+';S1='+r['s1']+';S2='+r['s2']+';S3='+r['s3']+';S4='+r['s4'] for r in ss)
                    else:
                        selected=ss;phase='v2 saglamlik gecti, resmi sete alinmadi';state='A_TEST_EDILDI_GECTI';gate='Saglamlik gecti; resmi son sette yok. A yalniz bu asamanin gecisidir, holdout/set/canli kabulu degil';note+=' Seçim dışı kalma, performans testinde başarısızlık diye sunulmadı.'
            fair='yapisal_kapi' if structural=='evet' else 'yalniz varsayilan ayar (v2 asamasi; tarihsel WF ayri)'
        elif sid in stages['sonuclar/evren/2017_gelistirme/saglamlik.csv']:
            selected=stages['sonuclar/evren/2017_gelistirme/saglamlik.csv'][sid];phase='v1 evren saglamlik';state='B_TEST_EDILDI_ELENDI' if all(r['saglam_mi']=='False' for r in selected) else 'A_TEST_EDILDI_GECTI';gate='; '.join(r['kapi_basarisiz'] for r in selected)
        elif sid in stages['sonuclar/evren/2017_gelistirme/wf_evren.csv']:
            selected=stages['sonuclar/evren/2017_gelistirme/wf_evren.csv'][sid];phase='v1 evren WF'
            if any(r.get('hata') for r in selected):state='BELIRSIZ';gate='Kosuda hata var; testte elenmis sayilmadi'
            else:state='A_TEST_EDILDI_GECTI' if any(r['gecti']=='True' for r in selected) else 'B_TEST_EDILDI_ELENDI';gate='; '.join(r.get('nedenler','') for r in selected)
        elif not h and c['kayit_durumu']!='kayit_disinda_ornek':
            state='C_KODLANDI_KOSULMADI';phase='mevcut sonuc tablolari kapsaminda';evidence='sonuclar/hesap_defteri/ara/P3_sayi_kontrolu.csv';note+=' 57 sonuç tablosu ve 135 arşiv JSONu kapsamı denetlendi; burada kayıtlı kod için araştırma koşusu kanıtı bulunmadı. Birim test ayrı birimdir.'
        else:phase='tarihsel tarama/WF';note+=' Tarihsel kayıt var; başarı/başarısızlık kapısı kesinleştirilemedi.'
        if not evidence:evidence=';'.join(r['_kanit'] for r in selected)
        breadth=sorted({f"{r['tf']}:{r['evren'] or r['sembol'] or ('evren '+r['n_enstruman_evren']+', kullanılan '+r['n_enstruman']) if r['n_enstruman_evren'] else r['evren'] or r['sembol'] or '(evren etiketi yok; özgün sonuç satırına bak)'}" for r in h if r['tf']})
        if fair=='BELIRSIZ' and selected:
            fair='yalniz tek TF' if len({r.get('tf','') for r in selected})==1 else 'BELIRSIZ'
        if sid in paper_ids:note+=' Paper v2 etiketi='+paper_ids[sid]['etiket']+'; paper uyeligi testteki elemeyi silmez.'
        rows.append(dict(tekil_id=sid,ad=sid,aile='BELIRSIZ',kisa_mantik=describe(c),kaynak_sayisi='',durum=state,asama=phase,tf_evren=';'.join(breadth),kapi_ve_deger=gate,yapisal_kapi=structural,adil_test=fair,kod_dosyasi=f"{c['dosya']}:{c['satir']}:{c['sinif']}",kanit_dosyasi=evidence,not_=note))
        for r in h:
            timelines.append({k:r[k] for k in ('strateji','dosya','kayit_no','tf','evren','sembol','ayar','ayar_kaynagi','islem_sayisi','n_islem_x1','n_islem','gecti','durum','hata')})
    write('ara/P8_kod_akibet_GECICI.csv',rows,list(rows[0]));write('ara/P8_kod_tarihce.csv',timelines,list(timelines[0]));print(dict(Counter(r['durum'] for r in rows)))
if __name__=='__main__':main()
