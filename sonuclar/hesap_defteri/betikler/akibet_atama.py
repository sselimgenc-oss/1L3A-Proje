"""P8: kanit zinciri ve muhafazakar akibet tablosu (ara surum).
Benzerlik beyanindan test gecisi turetmez. Bos kanit BELIRSIZ kalir.
"""
import csv,json,re,unicodedata
from collections import Counter,defaultdict
from pathlib import Path
from envanter import ROOT,OUT,write

def load(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def norm_url(s):return str(s or '').strip().rstrip('/')
def definition_text(d):
    fields=('ad','strateji','strateji_adi','ozet','mekanik_ozet','giris_kurali','cikis_kurali','long_giris','short_giris','gostergeler','kategori','pozisyon_risk','not','notlar','kurallar','kural_ozeti','giris_kurali_kisa','Özet','Giriş','Göstergeler','kural_ozu','cekirdek_mantik')
    text=' '.join(json.dumps(d.get(k,''),ensure_ascii=False) for k in fields)
    return ''.join(c for c in unicodedata.normalize('NFKD',text.casefold().replace('ı','i')) if not unicodedata.combining(c))

def main():
    raw=load(OUT/'ara/P8_asli_ham_tekillestirilmis.csv');code=load(OUT/'ara/P8_kod_akibet_GECICI.csv');code={r['tekil_id']:r for r in code};bygroup=defaultdict(list)
    for r in raw:bygroup[r['tekil_id']].append(r)
    book={r['kart_id']:r for r in load(OUT/'ara/P4_kitap_izleri.csv')}
    rejected={r['kart_id']:dict(r,kanit='stratejiler/elenenler.json:kayit='+str(i)) for i,r in enumerate(json.loads((ROOT/'stratejiler/elenenler.json').read_text()),1)}
    coding={r['kart_id']:dict(r,kanit='stratejiler/v3_adaylar/kodlama_v3.csv:kayit='+str(i)) for i,r in enumerate(load(ROOT/'stratejiler/v3_adaylar/kodlama_v3.csv'),1)}
    archive=defaultdict(list)
    for ar in load(OUT/'ara/P3_arsiv_tv_sonuclari.csv'):archive[ar['pine_id']].append(ar)
    preliminary={}
    for r in load(OUT/'ara/P6_katalog_karar_izleri.csv'):preliminary[r['kaynak'],r['kaynak_kayit']]=r
    compare={r['dis_id']:dict(r,kanit='sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/'+rel+':kayit='+str(i)) for rel in ('karsilastirma/karsilastirma.csv','tur4_degerlendirme/yeni_199.csv') for i,r in enumerate(load(ROOT/'sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus'/rel),1)}
    p5_card=defaultdict(list);p5_ham=defaultdict(list)
    for tr in load(OUT/'ara/P5_kodlama_izleri.csv'):
        if tr['kaynak_tipi']=='kart_id':p5_card[tr['kaynak_kimligi']].append(tr)
        elif tr['kaynak_ham_id']:p5_ham[tr['kaynak_ham_id']].append(tr)
    manual={r['kaynak_kimligi']:r for r in load(OUT/'ara/P8_manuel_mantik_denetimi.csv')}
    attr=defaultdict(set)
    for r in load(OUT/'ara/P8_kod_kaynak_atiflari.csv'):
        if r['tip']=='URL':attr[norm_url(r['deger'])].add(r['strateji_id'])
    rows=[];decisions=[]
    for sid,rs in sorted(bygroup.items()):
        first=rs[0];d=json.loads(first['veri_json']);kid=d.get('kart_id','');rel=first['dosya'];external=d.get('id','');state='BELIRSIZ';phase='';fair='BELIRSIZ';gate='';struct='hayir';paths=[];note=[];targets=set();kind='kaynak_strateji_kaydi'
        proof=rel+'#'+first['kaynak_satir_no'];paths.append(proof)
        # Tum kaynaklarda yaziya dokulmus kural ozeti korunur; kaynak PDF metni eklenmez.
        summary=d.get('ozet') or d.get('mekanik_ozet') or d.get('giris_kurali') or d.get('kural_ozeti') or d.get('kural_ozu') or d.get('Özet') or d.get('cekirdek_mantik') or d.get('long_giris') or d.get('giris_kurali_kisa') or d.get('kurallar') or ''
        if not isinstance(summary,str):summary=json.dumps(summary,ensure_ascii=False)
        summary=summary[:650] if summary else 'Kaynak kaydında açık mekanik özet yok; adından kural türetilmedi.'
        family=d.get('aile') or d.get('kategori') or 'BELIRSIZ'
        if str(family).casefold() in ('trend','trend_takip','kirilim','momentum'):family='trend'
        elif str(family).casefold() in ('ortalamaya_donus','mean_reversion','mr'):family='MR'
        else:family='diger'
        tf=d.get('zaman_dilimi') or d.get('tf') or d.get('Zaman Dilimi') or d.get('Piyasa / zaman dilimi') or ''
        if isinstance(tf,dict):tf=json.dumps(tf,ensure_ascii=False)
        universe=d.get('piyasa') or d.get('orijinal_piyasa') or d.get('varlik_sinifi') or d.get('Piyasa') or ''
        if kid in book:
            b=book[kid];paths.append('sonuclar/hesap_defteri/ara/P4_kitap_izleri.csv#'+kid)
            if b['yonlendirme_turu']=='cikis_risk_modulu':
                state='D_KODLANMADI_NEDENLI';phase='giris stratejisi degil, cikis/risk modulu';kind='cikis_risk_modulu';gate='Bağımsız giriş kuralı değil; 13 çıkış/risk modülünde muhasebeleştirildi.';paths.extend(x[2] for x in json.loads(b['yonlendirme']))
            elif kid in rejected:
                reason=rejected[kid]['neden'];state='D_KODLANMADI_NEDENLI';phase='belgeli kaynak elemesi';gate=reason;paths.append(rejected[kid]['kanit'])
                if 'MARTINGALE' in reason:state='F_YASAK_TIP'
                elif re.search(r'\bML\b|makine ogren|Makine ogren',reason):state='G_ML'
                elif 'Opsiyon' in reason or 'opsiyon' in reason:state='H_BIZIM_EVRENDE_UYGULANAMAZ'
                note.append('Kararın yazılı olduğu kart/reddetme kaydı doğrulandı; tarihsel veri-yok gerekçesi yeni veri erişimi imkânsız demek değildir.')
            else:
                phase='kitap karti yonlendirmesi';gate='Aile/ayar atfı tek başına kaynak kuralının test edildiğini kanıtlamaz.'
                if int(b['kosu_kayit_sayisi']):
                    phase='k2 kart ayari taramasi';fair='zayif temsilci';gate='Karta bağlı ayar koşusu mevcut; bu tarama satırında geçme/kalma kapısı yok. Ailenin başka ayardaki sonraki elemesi karta aktarılmadı.'
                    paths.extend(x['kanit'] for x in json.loads(b['kosu_kaniti']))
                note.append('BELIRSIZ: özgül kaynağın bütün kuralları için kapı kararı gösterilemiyor; aile sonucu kopyalanmadı.')
        p5_traces=p5_card.get(kid,[])+[tr for rr in rs for tr in p5_ham.get(rr['ham_id'],[])]
        for tr in p5_traces:
            paths.append(tr['kanit']);linked=[t for t in tr['hedef_kod'].split(';') if t in code];targets.update(linked)
            if linked:
                phase=phase or 'belgeli kod uyarlamasi';fair='zayif temsilci'
                note.append('Açık kaynak/kart atıflı kod: '+tr['hedef_kod']+'. Varsayım/kapsam: '+tr['varsayim_kapsam'])
                note.append('Kod ailesinin koşması kaynak alt-modunun veya tam giriş/çıkışının ayrı test edildiğini göstermez; otomatik B/A aktarımı yapılmadı.')
                if all(code[t]['durum']=='C_KODLANDI_KOSULMADI' for t in linked):
                    state='C_KODLANDI_KOSULMADI';phase='belgeli fakat kosu kaydi olmayan uyarlama'
            elif tr['gunluk_durum'] and tr['gunluk_durum'] not in ('kodlandi','kodlandı'):
                phase='belgeli kodlama karari';gate=tr['varsayim_kapsam']
                if re.search(r'MEVCUT|KAPSANIYOR|kopya|tekrar|benzer',tr['varsayim_kapsam']):
                    state='BELIRSIZ';note.append('Kodlamama gerekçesi mevcut/benzer kural iddiası içeriyor; bu iddia mantık denetimi olmadan D diye kesinleştirilmedi.')
                else:state='D_KODLANMADI_NEDENLI'
        if kid in coding:
            c=coding[kid];paths.append(c['kanit']);target=c.get('strateji_ad','')
            if target in code:targets.add(target)
            if c['durum'] in ('veri_yok','belirsiz') and target not in code:
                state='D_KODLANMADI_NEDENLI';phase='v3 kodlama karar kaydi';gate=c['not'];note.append('Bu belgeli kodlamama kararıdır; gerekçenin bugün teknik olarak değişmez olduğu iddia edilmez.')
            elif c['durum']=='tekrar':
                state='BELIRSIZ';phase='tekrar iddiasi';gate=c['not'];note.append('Tekrar iddiası mantık eşitliği kanıtı yerine kullanılmadı.')
            elif target in code:
                cr=code[target];phase='acik kart atifli uyarlama: '+cr['asama'];gate=cr['kapi_ve_deger'];fair='zayif temsilci';state=cr['durum'];struct=cr['yapisal_kapi'];paths.append(cr['kanit_dosyasi'])
                note.append('Kart-id → gerçek kod ad tanımı → sonuç kaydı zinciri var. Sonuç TEST EDİLEN UYARLAMAYA aittir; kaynakla birebir mantık iddiası değildir. Varsayımlar: '+c['varsayimlar'])
        traces=[]
        for rr in rs:
            m=re.search(r'kayit:(\d+)',rr['kaynak_satir_no']);tr=preliminary.get((rr['dosya'],m[1] if m else ''))
            if tr:
                hist=json.loads(tr['sonraki_kararlar']);lastfile=hist[-1]['dosya'] if hist else ''
                rank=4 if 'gorev2' in lastfile else 3 if 'tur3' in lastfile else 2 if 'tur2' in lastfile else 1
                traces.append((rank,tr))
        top_rank=max((t[0] for t in traces),default=0)
        active_traces=[tr for rank,tr in traces if rank==top_rank]
        classifications=set()
        for tr in active_traces:
            hist=json.loads(tr['sonraki_kararlar']);classifications.add(hist[-1]['karar'] if hist else tr['ilk_karar'])
        for tr in active_traces[-1:]:
            paths.append(tr['ilk_karar_kaniti']);phase=phase or 'v3 kaynak on elemesi';last=tr['ilk_karar'];why=tr['ilk_neden']
            later=json.loads(tr['sonraki_kararlar'])
            if later:
                last=later[-1]['karar'];why=later[-1]['neden'];paths.extend(x['dosya']+':kayit='+str(x['kayit']) for x in later)
            if last in ('kod_yok','veri_yok'):
                state='D_KODLANMADI_NEDENLI';gate=why;note.append('Kaynak/eleme belgesi bu gerekçeyle kodlamamayı kaydediyor; bağımsız testte zarar sonucu değildir.')
            elif last=='arac':
                state='D_KODLANMADI_NEDENLI';gate=why;kind='arac_veya_yazi';note.append('Strateji olmayan araç/yazı kaydı sayımdan gizlenmedi.')
            elif last=='yasak':
                if re.search(r'\bML\b|FreqAI|LSTM|LightGBM|XGBoost|makine|[Rr]einforcement',why):state='G_ML'
                elif re.search(r'\bDCA\b|[Mm]artingale|[Oo]rtalama(?:yı|yi)? (?:düşür|dusur)|[Pp]ozisyon[^.;]{0,40}(?:büyüt|buyut)|[Ll]ot[^.;]{0,25}(?:katla|iki kat)|stopsuz [ıi]zgara',why):state='F_YASAK_TIP'
                else:state='D_KODLANMADI_NEDENLI'
                gate=why;note.append('Tür sınıflaması mekanik/tür açıklaması ve gerekçeye dayanır; backtest başarısızlığı değildir.')
            elif last=='tekrar':
                state='BELIRSIZ';gate=why;note.append('Benzer/tekrar hükmü kod/ayar eşdeğerliği kanıtı olmadan test sonucuna dönüştürülmedi.')
            else:gate=gate or why
        if external in compare and rel.endswith('/ajan1/strateji_listesi.csv'):
            cmp=compare[external];paths.append(cmp['kanit']);phase='dis kaynak karsilastirmasi';gate=cmp['sinif']+': '+cmp.get('fark_aciklamasi','');note.append('Önceki karşılaştırma hükmü kanıt olarak tek başına kabul edilmedi. Bir stratejinin benzeri için test bulunması bu kaynak kuralının koşulduğu anlamına gelmez.')
            if cmp['sinif']=='BIZDE_YOK':note.append('Akıbet/uygulama boşluğu adayı: kesin E için mantık eşleştirmesi eksik; BELIRSIZ bırakıldı.')
        # Dogrudan kaynak adresi kodda gorunuyorsa eski "kod yok" karari kesin son durum sayilamaz.
        srcurl=(d.get('kaynak') or {}).get('url','') if isinstance(d.get('kaynak'),dict) else d.get('kaynak_url') or d.get('kaynak_link') or d.get('url') or d.get('URL') or ''
        direct=attr[norm_url(srcurl)]
        if direct:
            targets.update(direct)
            if state=='D_KODLANMADI_NEDENLI' and kind not in ('cikis_risk_modulu','arac_veya_yazi'):
                state='BELIRSIZ';note.append('Kod sınıfında aynı kaynak URLsi var; eski kod-yok kaydı ile çelişki nedeniyle D kesinleştirilmedi.')
        if d.get('dosya_sinif') and rel.endswith('2026-11_freqtrade_robotic/dosya_listesi.csv'):
            phase='Robotic statik kaynak taramasi';gate=d['dosya_sinif']+': '+d['neden'];note.append('Asıl 909 üçüncü taraf dosya bu checkoutta yok. Küme ve yasak/ML bayrakları rapor beyanı olarak saklandı; bağımsız kod doğrulaması olmadan kesin test/aynılık hükmü verilmedi.')
        if d.get('belgeli_karar'):
            state='D_KODLANMADI_NEDENLI';phase='belgeli ek arastirma reddi';gate=d['belgeli_karar']+'; '+summary
            if d.get('toplu_kayit')=='evet':kind='toplu_katalog_kaydi'
        if first['kayit_turu']=='toplu_beyan':
            kind='toplu_beyan';phase='eksik tekil liste';gate='26 beyanı var, tekil CSV yok';note.append('26 satır veya ad uydurulmadı; 26 bağımsız tekil strateji toplamına eklenmedi.')
        mk=external if external in manual else 'ROBOTIC:'+str(d.get('kume_id',''))
        if mk in manual:
            mm=manual[mk];paths.extend((mm['kaynak_kaniti'],mm['kod_test_kaniti']));gate=mm['gerekce'];fair=mm['adil_test'];targets.add(mm['eslesen_kod_id']);note.append(mm['sinir'])
            if mm['eslesen_kod_id'] in code and mk!='ROBOTIC:K001':
                cr=code[mm['eslesen_kod_id']];state=cr['durum'];phase='mantigi farkli temsilcinin '+cr['asama'];struct=cr['yapisal_kapi'];note.append('Akıbet temsilci uygulamaya aittir; kaynak özgün kuralıyla tekilleştirilmedi.')
            else:state='BELIRSIZ'
        # Eski olcum, ayni Pine kaynak kimligiyle bulunuyorsa kaybolmaz; modern 1L3A sonucu diye sunulmaz.
        pine_ids=set(re.findall(r'(?:^|/)([A-Za-z0-9_-]+)\.pine',str(d.get('dosya',''))))
        old=[ar for pid in pine_ids for ar in archive.get(pid,[])]
        if len(pine_ids)==1 and old and state in ('BELIRSIZ','D_KODLANMADI_NEDENLI') and kind=='kaynak_strateji_kaydi':
            note.append('Daha yeni envanter/kodlama beyanı: '+gate if gate else 'Önceki envanter sonucu yalnız beyan olarak vardı; somut arşiv JSONu bulundu.')
            passed=any(str(ar['gecti']).casefold()=='true' for ar in old)
            state='A_TEST_EDILDI_GECTI' if passed else 'B_TEST_EDILDI_ELENDI';phase='onceki proje TV arsiv olcumu';fair='zayif temsilci'
            gate=json.dumps([{'gecti':ar['gecti'],'tf':ar['tf'],'olcut':json.loads(ar['olcut'])} for ar in old],ensure_ascii=False)
            paths.extend(ar['dosya'] for ar in old);note.append('Arşiv aşaması geçişi/elemesi; güncel 1L3A/WF/v2 geçişi veya kaynağın birebir kodlandığı iddiası değildir. Eski risk, veri ve seçim yanlılıkları geçerlidir.')
        core=definition_text(d)
        if state=='G_ML' and not re.search(r'\b(lstm|rnn|cnn|mlp|vae|svm|svr|ppo|dqn|freqai|xgboost|lightgbm|gbdt|gpt|bert|transformer|tensorflow|pytorch|sklearn|keras|hmm|gmm)\b|random.?forest|randomforest|k.?means|k.?nn|lorentzian|gradient.?boost|makine.?ogren|machine.?learning|sinir.?ag|reinforcement',core):
            state='BELIRSIZ';note.append('ML eleme notu mevcut, fakat asıl kaynak kaydı somut model türünü belirtmiyor; önceki raporun ML hükmü tek başına doğrulanmış sayılmadı.')
        if state=='F_YASAK_TIP' and not re.search(r'martingale|\bdca\b|ortalama(?:yi)? dusur|pozisyon[^.;]{0,40}buyut|lot[^.;]{0,25}(?:katla|iki kat)|stopsuz.{0,20}(?:grid|izgara)|(?:grid|izgara).{0,20}(?:stopsuz|stop yok)',core):
            state='BELIRSIZ';note.append('Yasak işlem türü önceki eleme notunda iddia ediliyor; asıl kayıtta o türü doğrulayacak açık risk/pozisyon kuralı yok.')
        # Asıl kaydın doğrudan tür tanımı, benzerlik/performans çıkarımı gerektirmez.
        if state in ('BELIRSIZ','D_KODLANMADI_NEDENLI') and kind=='kaynak_strateji_kaydi' and not targets:
            if re.search(r'\bllm tabanli|\blarge language model',core):
                state='G_ML';phase='kaynakta acik model turu';gate='Asıl mekanik özet LLM tabanlı sistem diyor; deterministik strateji kuralı yok. Test sonucu çıkarılmadı.'
            asset=str(d.get('varlik_sinifi','')).casefold()
            if asset.startswith('opsiyon') and 'opsiyon' in str(d.get('veri_ihtiyaci','')).casefold():
                state='H_BIZIM_EVRENDE_UYGULANAMAZ';phase='opsiyon verisi ve urun gereksinimi';gate='Kaynak opsiyon zinciri/strike/vade gerektiriyor; mevcut OHLCV/perpetual evrende aynı işlem kurulamaz. Hisse veya pairs olmasına bakarak H verilmedi.'
        claims={k:d[k] for k in ('durum','ayar_durumu','benzer_1l3a_aile','benzer_1l3a','benzer_mevcut','onceki_sonuc') if d.get(k)}
        if claims:
            claimtext=json.dumps(claims,ensure_ascii=False)
            mentioned=set(re.findall(r'(?:dis|pf|swing|daytrade|scalp|v2|v3|onceki)__[\w-]+',claimtext))&set(code)
            targets.update(mentioned)
            if not phase:phase='kaynak envanterindeki akibet beyani'
            if not gate:gate='Envanter beyanı: '+claimtext
            note.append('Kaynak envanterinin mevcut/benzer/eski sonuç beyanı korundu; bu beyanlardan birebir test geçişi türetilmedi.')
        if len(classifications)>1:
            state='BELIRSIZ';note.append('Birebir aynı kaynak kayıt kopyaları aynı inceleme turunda farklı akıbet sınıfları taşıyor: '+','.join(sorted(classifications))+'. Dosya sırasına göre bir hüküm seçilmedi.')
            paths.extend(tr['ilk_karar_kaniti'] for tr in active_traces)
        if (';' in first['kaynaktaki_ad'] and re.search(r';\s*(?:SMA|EMA|RSI|MACD)',first['kaynaktaki_ad'],re.I)) or re.search(r'\bvs\b.*DCA',first['kaynaktaki_ad'],re.I):
            state='BELIRSIZ';kind='toplu_katalog_kaydi';note.append('Satır birden fazla bağımsız kural/karşılaştırma bacağı içeriyor. Tek ML/DCA hükmü bütün bileşenlere aktarılmadı; üye adları ara/P8_grup_uyeleri.csv içinde.')
        if 'CEZLSMA' in str(d) and 'NWERSIASF' in str(d):
            kind='toplu_katalog_kaydi';state='BELIRSIZ';note.append('Kaynak dokuz ayrı script adı içeriyor; bir bağımsız strateji diye sayılmadı. Üye adları ara/P8_grup_uyeleri.csv içinde.')
        if not gate:gate='BELIRSIZ: kaynak kaydı mevcut; açık uygulama veya gerekçeli eleme zinciri bulunamadı. Sadece ad benzerliğiyle bağ kurulmadı.'
        paths=[p for p in dict.fromkeys(paths) if p]
        rows.append(dict(tekil_id=sid,ad=first['kaynaktaki_ad'],aile=family,kisa_mantik=summary,kaynak_sayisi=len({r['kaynak_id'] for r in rs}),durum=state,asama=phase or 'kaynak kaydi',tf_evren=str(tf)+' / '+str(universe),kapi_ve_deger=gate,yapisal_kapi=struct,adil_test=fair,kod_dosyasi=';'.join(code[t]['kod_dosyasi'] for t in sorted(targets) if t in code),kanit_dosyasi=';'.join(paths),not_=' '.join(note),birim_turu=kind,uygulama_idleri=';'.join(sorted(targets)),envanter_beyani=json.dumps(claims,ensure_ascii=False) if claims else ''))
    # Operasyonel tanimlar, dis kaynakla denk olduklari ispatlanmadikca ayri tutulur.
    for sid,c in sorted(code.items()):
        if sid.startswith('ornek__'):continue
        r=dict(c);r['tekil_id']='KOD:'+sid;r['kaynak_sayisi']=1;r['birim_turu']='operasyonel_kod';r['uygulama_idleri']=sid;r['envanter_beyani']='';r['not_']+=' Dış kaynaklarla otomatik birleştirilmedi; bu satır gerçek ad kimliğinin akıbetidir.';rows.append(r)
    assert len({r['tekil_id'] for r in rows})==len(rows)
    write('ara/P8_tekil_akibet_ARA.csv',rows,list(rows[0]))
    summary=dict(toplam_kayit_dugumu=len(rows),durum=dict(Counter(r['durum'] for r in rows)),birim_turu=dict(Counter(r['birim_turu'] for r in rows)),not_='ARA SURUM: kayit dugumleri matematiksel bagimsiz strateji sayisi degildir; prototip/temsilci ve asli kaynak ayridir. Son mantik ve oz denetim bitmedi.')
    (OUT/'ara/P8_akibet_sayim_ARA.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(summary)
if __name__=='__main__':main()
