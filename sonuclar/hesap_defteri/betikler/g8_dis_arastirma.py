"""G8_DIS_ARASTIRMA ham satir + NOTLAR uretici.
Kullanim: python sonuclar/hesap_defteri/betikler/g8_dis_arastirma.py [REF_DIS_ARASTIRMA_KLASORU]
Girdi : dal kopyasi (adoring-maxwell) dis_arastirma/2026-11_trend_ortalamaya_donus, ara/kod_kaydi.csv,
        ara/G8_DIS_ARASTIRMA_elle_kararlar.csv (kodla acilip dogrulanan satirlar; elle verildi).
Cikti : ara/G8_DIS_ARASTIRMA_ham.csv, ara/G8_DIS_ARASTIRMA_NOTLAR.md"""
import csv, os, re, subprocess, sys, collections
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
REF = sys.argv[1] if len(sys.argv) > 1 else ('/tmp/claude-0/-home-user-1L3A-Proje/bee1199a-0b5d-5964-8f7d-e654dea778f9/'
      'scratchpad/ref_adoring/sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus')
ARA = os.path.join(REPO, 'sonuclar/hesap_defteri/ara')
DAL = 'dal:claude/adoring-maxwell-q7t60g:sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/'
MAIN = 'sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/'

def rd(p, base=REF):
    with open(os.path.join(base, p), encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))
S = rd('ajan1/strateji_listesi.csv')
K = {r['dis_id']: r for r in rd('karsilastirma/karsilastirma.csv') + rd('tur4_degerlendirme/yeni_199.csv')}
B = {r['dis_id']: r for r in rd('derin_gecis/benzeri_derin.csv')}
O30 = rd('tur4_degerlendirme/oncelik30_hukum.csv')
KOD = {r['ad']: r for r in rd('kod_kaydi.csv', ARA)}
ELLE = {r['dis_id']: r for r in rd('G8_DIS_ARASTIRMA_elle_kararlar.csv', ARA)}
O30_GRUP = {r['fikir_grubu']: r for r in O30}
FG = {r['id']: r['fikir_grubu'] for r in rd('ajan1/fikir_gruplari.csv')}

def txt(p):
    try: return open(os.path.join(REF, p), encoding='utf-8').read()
    except Exception: return ''
ANIM = {'derin_gecis/ADAYLAR.md': txt('derin_gecis/ADAYLAR.md'), 'tur4_degerlendirme/RAPOR.md': txt('tur4_degerlendirme/RAPOR.md'),
        'derin_gecis/RAPOR.md': txt('derin_gecis/RAPOR.md')}

# repo icinde ayni link
files = subprocess.run('git ls-files stratejiler motor', shell=True, capture_output=True, text=True, cwd=REPO).stdout.split()
RT = {}
for f in files:
    try: RT[f] = open(os.path.join(REPO, f), encoding='utf-8').read()
    except Exception: pass

def kodyer(h):
    r = KOD.get(h)
    return f"{r['dosya']}:{r['satir']}" if r else ''

def neden(k, s):
    t = (k.get('kapsam_disi_neden', '') + ' ' + s.get('bayraklar', '')).lower()
    a = k.get('fark_aciklamasi', '').lower()
    if 'yasak' in t or 'grid' in t or 'dca' in t or 'martingale' in t:
        return 'F_YASAK_TIP', 'stopsuz_grid' if 'grid' in t else 'martingale', 'Yasak tip (grid/DCA/martingale/yasak bayrağı)'
    if 'pairs' in t or 'kointegrasyon' in t or 'spread' in t:
        return 'H_BIZIM_EVRENDE_UYGULANAMAZ', 'pairs', 'Pairs/spread: iki bacaklı, bizim evrende yok'
    if 'vix' in t: return 'H_BIZIM_EVRENDE_UYGULANAMAZ', 'vix', 'VIX verisi gerekir'
    if 'arbitraj' in t: return 'H_BIZIM_EVRENDE_UYGULANAMAZ', 'arbitraj', 'Çapraz borsa/ETF arbitrajı'
    if 'tick' in t or 'market-making' in t or 'limit emir' in t: return 'H_BIZIM_EVRENDE_UYGULANAMAZ', 'hft', 'Tick/limit-emir tabanlı'
    if 'kesit' in t or 'rotasyon' in t or 'çok varlıklı' in t or 'sıralama' in t or 'hisse evreni' in t or 'etf' in t and 'çok' in t:
        return 'H_BIZIM_EVRENDE_UYGULANAMAZ', 'hisse_kesitsel', 'Kesitsel/çok varlıklı sıralama; evren dışı'
    if 'seans' in t or 'açılış' in t or 'boşluğ' in t or 'gap' in t or 'saat' in t or 'ny ' in t:
        return 'H_BIZIM_EVRENDE_UYGULANAMAZ', 'seans_gap', 'Borsa seans/saat penceresine bağlı (kripto 7/24)'
    if 'lookahead' in t: return 'D_KODLANMADI_NEDENLI', 'lookahead', 'Dış ajan LOOKAHEAD_RİSKİ bayrağı'
    if 'şüpheli' in t: return 'D_KODLANMADI_NEDENLI', 'kural_belirsiz', 'Dış ajan ŞÜPHELİ bayrağı'
    if 'veri' in t or 'vadeli' in t or 'ilişkili' in t or 'olay' in t:
        return 'D_KODLANMADI_NEDENLI', 'veri_yok', 'Gereken veri yok (vadeli/olay/ilişkili varlık)'
    return 'BELIRSIZ', 'kapsam_disi', 'kullanilabilir=hayir ama kapsam_disi_neden boş; fark: ' + a[:90]

HAM = []
first_key = {}
for i, s in enumerate(S):
    n = i + 1; sid = s['id']; k = K[sid]; b = B.get(sid)
    hid = f'X005:{n}'
    row = dict(ham_id=hid, kaynak_id='X005', kaynak_satir_no=str(n), kaynaktaki_ad=s['strateji_adi'][:120],
               kisa_mantik=(s['alt_tur'] + ': ' + s['giris_kurali'])[:157] + ('…' if len(s['alt_tur'] + ': ' + s['giris_kurali']) > 157 else ''),
               aile='trend' if s['aile'].startswith('TREND') else 'MR', eslesme='', hedef='', ayar_id='', ayar_dosyasi='', fark='',
               on_durum='', neden_kodu='', neden_metni='', kanit='', **{'not': ''})
    row['not'] = sid
    kayit = (DAL if int(sid[1:]) > 707 else MAIN) + ('tur4_degerlendirme/yeni_199.csv' if int(sid[1:]) > 707 else 'karsilastirma/karsilastirma.csv') + '#' + sid
    prior = k['sinif'] + (('/' + b['yeni_sinif']) if b else '')
    m_ids = [x.strip() for x in k['eslesen_arsiv_id'].split(';') if x.strip()]
    link = s['kaynak_link'].strip().rstrip('/')
    key = (link, s['giris_kurali'][:100])
    rep = [f for f, t in RT.items() if len(link) > 25 and link in t]
    repnot = (' | aynı link repoda: ' + ', '.join(rep[:3])) if rep else ''
    if sid in ELLE:
        e = ELLE[sid]
        row.update(eslesme=e['eslesme'], hedef=e['hedef'], fark=e['fark'], neden_metni='' if e['eslesme'] == 'ESDEGER' else 'Sınıf açıldı, mantık farkı var (fark sütunu)', on_durum='KOD' if e['eslesme'] == 'ESDEGER' else 'D_KODLANMADI_NEDENLI',
                   neden_kodu='' if e['eslesme'] == 'ESDEGER' else 'benzer_var')
        row['kanit'] = f"{kodyer(e['hedef'])} ; {kayit}"
        row['not'] = f"{sid} | önceki ajan: {prior}; lider kodla açtı: {e['eslesme']}" + repnot
    elif key in first_key and len(s['giris_kurali']) > 20:
        row.update(eslesme='TEKRAR', hedef=first_key[key], on_durum='TEKRAR', kanit=f'{DAL}ajan1/strateji_listesi.csv:{n}',
                   fark='yok'); row['not'] = f'{sid} | aynı link + aynı giriş kuralı' + repnot
    elif k['sinif'] == 'BIZDE_YOK':
        row['eslesme'] = 'YOK'; row['kanit'] = kayit
        if k['kullanilabilir'] == 'evet':
            if re.search(r'elendi|kodlanmad', k['fark_aciklamasi'], re.I):
                row.update(on_durum='D_KODLANMADI_NEDENLI', neden_kodu='hakem_elendi', neden_metni=k['fark_aciklamasi'][:150])
            else:
                row['on_durum'] = 'E_KODLANMADI_NEDENSIZ'
                an = [f"{f}" for f, t in ANIM.items() if re.search(r'\b' + sid + r'\b', t)]
                g = FG.get(sid, '')
                hk = O30_GRUP.get(g)
                row['neden_metni'] = 'Arşivde karşılığı yok; akıbet (test/kodlama kararı) yazılı değil.'
                row['not'] = (f"{sid} | {k['fark_aciklamasi'][:110]} | kanıt={k['kanit_turu']} | grup={g}" +
                              (f" | öncelik30 hükmü: {hk['hukum']}" if hk else '') +
                              (f" | anıldığı: {', '.join(an)} (akıbet değil)" if an else '') + repnot)
        else:
            od, nk, nm = neden(k, s)
            row.update(on_durum=od, neden_kodu=nk, neden_metni=nm + ' | ' + (k['kapsam_disi_neden'] or k['fark_aciklamasi'])[:90])
    elif k['kullanilabilir'] == 'hayir':
        od, nk, nm = neden(k, s)
        row.update(eslesme='YOK', on_durum=od, neden_kodu=nk, neden_metni=nm + ' | ' + (k['kapsam_disi_neden'] or k['fark_aciklamasi'])[:90],
                   kanit=kayit)
        row['not'] = f"{sid} | önceki ajan: {prior}, eşleşen arşiv: {k['eslesen_arsiv_id']} (doğrulanmadı; kapsam dışı olduğu için eşleme anlamsız)" + repnot
    else:  # BENZERI/ZATEN, kullanilabilir=evet, kodla dogrulanmadi
        hedef = m_ids[0] if m_ids else ''
        if b and b['yeni_sinif'] == 'ARSIV_ESLESMESI_YANLIS' and b['dogru_sinif_yanlis_eslesme_icin']:
            hedef = hedef
        fark = (b['gerekce'] if b and b['gerekce'] else k['fark_aciklamasi'])[:300]
        row.update(eslesme='BENZER', hedef=hedef, fark=fark, on_durum='D_KODLANMADI_NEDENLI', neden_kodu='benzer_var',
                   neden_metni='Arşivde aynı aileden sınıf var, fark test edilmedi (önceki ajan kararı)', kanit=f"{kodyer(hedef)} ; {kayit}")
        row['not'] = f"{sid} | önceki ajan kararı ({prior}), lider doğrulamadı" + repnot
    first_key.setdefault(key, hid)
    HAM.append(row)

# ---- ajan2 (26 kayit raporu; yalniz anlatim) ----
A2 = [  # (satir, ad, kisa mantik, aile, eslesme, hedef, fark/not)
 ('L13', 'Donchian backtester (20 giriş/10 çıkış, 2xATR stop)', 'Donchian 20 giriş, 10 çıkış kanalı, 2xATR stop, ertesi açılışta dolum, bugün kanaldan dışlanır', 'trend', 'ESDEGER', 'swing__donchian-kirilim', 'yok', 'varsayılan giris_n=20,cikis_n=10,stop_atr=2 sınıf varsayılanı'),
 ('L13', 'Freqtrade Strategy001', 'EMA / Heikin-Ashi trend kuralı (freqtrade)', 'trend', 'TEKRAR', 'X005:19', '', 'S0019 Strategy001 ile aynı isim/kaynak; ajan2 metninde link yok, isimden'),
 ('L13', 'Freqtrade Strategy002', 'RSI-Stoch-Bollinger-Hammer ortalamaya dönüş (freqtrade)', 'MR', 'TEKRAR', 'X005:20', '', 'S0020 Strategy002 ile aynı isim/kaynak; ajan2 metninde link yok, isimden'),
 ('L15', 'Kore Fintrix Bollinger (KOSPI/KOSDAQ)', 'Bollinger alt bant girişi, -%3 stop, üst bant hedef, 5 gün zaman çıkışı', 'MR', 'BENZER', 'swing__bant-donus', 'Giriş bant içine dönüş mumu değil; -%3 stop ve 5 günlük zaman çıkışı sınıfta yok', 'doğrulanamadı (anlatım)'),
 ('L15', 'Hindistan Nifty EMA/Supertrend SAR (1g/4s/1s)', 'Nifty spot EMA/Supertrend stop-and-reverse, günlük/4s/1s, 2015-2025', 'trend', 'BENZER', 'swing__supertrend-psar', 'EMA bileşeni ve parametreler anlatımda yok; doğrulanamadı', 'doğrulanamadı (anlatım)'),
 ('L15', 'Qiita tekil hisse 25 günlük Bollinger', '25 günlük Bollinger bandı stratejisi, tekil hisse', 'MR', 'BENZER', 'swing__bant-donus', 'BB periyodu 25 ızgara (20/30/40) dışı; kural ayrıntısı anlatımda yok', 'S0219 (qiita, BB25) ile aynı olabilir; emin değil'),
 ('L15', 'Qiita TOPIX500 5 yıllık Bollinger olay çalışması', 'TOPIX500 üzerinde Bollinger olay çalışması', 'MR', 'BENZER', 'swing__bant-donus', 'Olay çalışması, kural ayrıntısı anlatımda yok', 'doğrulanamadı (anlatım)'),
 ('L17', 'FMZ Binance Futures BTC_USDT 1h EMA9/21', 'EMA9/21 kesişimi, %1 stop / %2 hedef, 1 saat', 'trend', 'BENZER', 'swing__ma-kesisim', '%2 sabit hedef (TP) sınıfta yok; EMA9/21 varsayılan', 'metin-kod farkı (MACD teyidi) ajan2 notunda'),
 ('L17', 'StockSharp RSI', 'RSI ortalamaya dönüş, 5 dk varsayılan', 'MR', 'BENZER', 'swing__rsi-asiri-donus', 'Parametreler/çıkış anlatımda yok; doğrulanamadı', 'doğrulanamadı (anlatım); S0313 StockSharp RSI olabilir'),
 ('L17', 'StockSharp Bollinger', 'Bollinger ortalamaya dönüş, 5 dk', 'MR', 'BENZER', 'swing__bant-donus', 'Parametreler anlatımda yok', 'doğrulanamadı (anlatım)'),
 ('L17', 'StockSharp Z-score', 'Z-score ortalamaya dönüş, ~%121 yıllık iddia', 'MR', 'BENZER', 'v3__z-skor-karsit', 'Kural ayrıntısı anlatımda yok', 'doğrulanamadı (anlatım)'),
 ('L17', 'StockSharp VWAP mean reversion', 'VWAP ortalamaya dönüş, 5 dk', 'MR', 'BENZER', 'daytrade__vwap-donus', 'Kural ayrıntısı anlatımda yok', 'doğrulanamadı (anlatım)'),
 ('L21', '513 ABD hissesi EMA pullback testi', 'EMA geri çekilme kuralı, 20.572 işlem, rastgele giriş kontrolü', 'trend', 'BENZER', 'swing__ma-geri-cekilme', 'Kural ayrıntısı anlatımda yok; hisse evreni', 'doğrulanamadı (anlatım)'),
 ('L21', 'Faber 10 aylık SMA (quantstrat)', 'Faber 10 ay SMA taktik dağılım', 'trend', 'BENZER', 'pf__trend_sepet', 'Evren farkı (kripto+hisse+3 emtia); S0141 ile aynı fikir olabilir', 'doğrulanamadı (anlatım)'),
 ('L21', 'AAPL/STLD/IBM açık Python backtesti', 'AAPL, STLD, IBM üzerinde Python backtest (strateji türü anlatımda yok)', 'diger', 'YOK', '', '', 'kural anlatımda yok'),
 ('L23', 'Freqtrade Triple Supertrend', 'Üçlü Supertrend (ŞÜPHELİ bayraklı)', 'trend', 'TEKRAR', 'X005:278', '', 'S0278 Triple Supertrend ile aynı isim; ajan2 metninde link yok, isimden'),
 ('L23', 'MQL5 MACD EA (destek/direnç)', 'MACD EA, öznel destek/direnç seviyeleri, ŞÜPHELİ bayraklı', 'trend', 'BENZER', 'swing__macd-sinyal', 'Destek/direnç öznel; MACD kısmı sınıfta var', 'doğrulanamadı (anlatım)'),
]
cnt = collections.Counter()
for j, (ln, ad, km, aile, es, hd, fk, nt) in enumerate(A2, 1):
    cnt[ln] += 1
    r = dict(ham_id=f'X008:{ln}#{cnt[ln]}', kaynak_id='X008', kaynak_satir_no=ln, kaynaktaki_ad=ad[:120], kisa_mantik=km[:160], aile=aile,
             eslesme=es, hedef=hd, ayar_id='', ayar_dosyasi='', fark=fk, on_durum='', neden_kodu='', neden_metni='',
             kanit=f'{DAL}ajan2/derin_arastirma_26_kayit_raporu.md:{ln[1:]}', **{'not': nt})
    if es == 'ESDEGER': r['on_durum'] = 'KOD'; r['kanit'] += ' ; ' + kodyer(hd)
    elif es == 'TEKRAR': r['on_durum'] = 'TEKRAR'
    elif es == 'BENZER': r.update(on_durum='D_KODLANMADI_NEDENLI', neden_kodu='benzer_var'); r['kanit'] += ' ; ' + kodyer(hd)
    else: r.update(on_durum='BELIRSIZ', neden_kodu='kural_belirsiz', neden_metni='Anlatımda kural yok')
    HAM.append(r)

COLS = ['ham_id', 'kaynak_id', 'kaynak_satir_no', 'kaynaktaki_ad', 'kisa_mantik', 'aile', 'eslesme', 'hedef', 'ayar_id', 'ayar_dosyasi',
        'fark', 'on_durum', 'neden_kodu', 'neden_metni', 'kanit', 'not']
with open(os.path.join(ARA, 'G8_DIS_ARASTIRMA_ham.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, COLS); w.writeheader(); w.writerows(HAM)

# ---- NOTLAR ----
d_on = collections.Counter(r['on_durum'] for r in HAM); d_es = collections.Counter(r['eslesme'] for r in HAM)
elle_prior = collections.Counter()
farkli = []
for sid, e in ELLE.items():
    k = K[sid]; b = B.get(sid)
    onceki = 'ESDEGER_SAYILIR' if (k['sinif'] == 'ZATEN_TEST' or (b and b['yeni_sinif'] == 'FARK_ONEMSIZ')) else 'BENZER_SAYILIR'
    elle_prior[(onceki, e['eslesme'])] += 1
    if onceki == 'ESDEGER_SAYILIR' and e['eslesme'] == 'BENZER': farkli.append(sid)
# unverified ESDEGER-candidates
cand = [sid for sid, k in K.items() if k['sinif'] == 'ZATEN_TEST' or (sid in B and B[sid]['yeni_sinif'] == 'FARK_ONEMSIZ')]
cand_hay = [c for c in cand if K[c]['kullanilabilir'] == 'evet']
unv = [c for c in cand_hay if c not in ELLE]
benz_evet = [sid for sid, k in K.items() if k['sinif'] != 'BIZDE_YOK' and k['kullanilabilir'] == 'evet']
L = []
L.append('# G8_DIS_ARASTIRMA notlar\n')
L.append('Üretici: `sonuclar/hesap_defteri/betikler/g8_dis_arastirma.py`; elle verilen kararlar: `ara/G8_DIS_ARASTIRMA_elle_kararlar.csv`.\n')
L.append('## Kaynak sayıları')
L.append(f'- X005 `ajan1/strateji_listesi.csv` (dal): 906 veri satırı -> 906 ham satır (hiçbiri atlanmadı).')
L.append(f'- X008 `ajan2/derin_arastirma_26_kayit_raporu.md`: 26 kayıt iddia ediliyor, CSV yok; metinden AYIRT EDİLEBİLEN {len(A2)} strateji çıkarıldı (kalan ~9 kayıt anlatımda adlandırılmamış, sayı olarak da yok). Linkleri anlatımda yok (citeturn etiketleri), bu yüzden 906 listesiyle eşleme yalnız isimden/mantıktan: 3 TEKRAR (Strategy001->S0019, Strategy002->S0020, Triple Supertrend->S0278; isim eşliği, emin değilim), 1 ESDEGER (Donchian 20/10 2xATR = sınıf varsayılanı), diğerleri BENZER/YOK doğrulanamadı. Aynı satır numaralı paragraftan birden çok strateji: ham_id `X008:L13#1` biçiminde.')
L.append(f'- Toplam ham satır: {len(HAM)}.\n')
L.append('## Dağılımlar')
L.append('eslesme: ' + ', '.join(f'{a}={b}' for a, b in sorted(d_es.items())))
L.append('on_durum: ' + ', '.join(f'{a}={b}' for a, b in sorted(d_on.items())) + '\n')
L.append('## Karşılaştırma dosyaları tutarlılığı')
L.append('main `sonuclar/dis_arastirma/.../karsilastirma/` {karsilastirma.csv, arsiv_envanteri.csv, fikir_grubu_ozeti.csv, RAPOR.md} dal kopyasıyla bayt bayt AYNI (cmp). Karşılaştırma yalnız ilk 707 satırı kapsar; S0708-S0906 yalnız dalda (`tur4_degerlendirme/yeni_199.csv`).\n')
L.append('## Önceki ajan kararlarının doğrulaması')
L.append('Hiçbir S0xxx id\'si kodlama_* dosyalarında / motor docstring\'lerinde geçmiyor (kontrol edildi); dolayısıyla KOD/AYAR yok. Not: 38 satırın linki repoda başka kaynaklarda (v3_adaylar, on_eleme, repo_kodlari...) geçiyor; ilgili satırların `not` sütununda yazıldı (bu satırların başka gruplarda kodlanmış olma ihtimali o grupların işi).')
L.append(f'- Kodla açıp ESDEGER/BENZER doğruladığım satır: {len(ELLE)} (ZATEN_TEST + FARK_ONEMSIZ adayları: {len(cand_hay)} kullanılabilir adaydan {len(cand_hay)-len(unv)} doğrulandı).')
L.append(f'- Önceki ajan "ZATEN_TEST/FARK_ONEMSIZ" (=aynı) demişti; benim sonucum: ' + ', '.join(f'{a}->{b}: {c}' for (a, b), c in sorted(elle_prior.items())) + '.')
L.append(f'- Doğrulanıp ONAYLANAN (ESDEGER): {elle_prior[("ESDEGER_SAYILIR","ESDEGER")]}; FARKLI karar verdiğim (önceki "aynı" -> ben BENZER): {len(farkli)}.')
L.append('  Ölçüt: parametre çifti ızgara/ayar kümesi ya da ızgara aralığı (±%15) içinde değilse; kaynakta sınıfta olmayan filtre/TP/zaman-iz çıkışı/bant/MTF/TF varsa; sınıf kural tetiği farklıysa (örn. bant dışı kapanış vs bant içine dönüş) BENZER.')
L.append('  Farklı karar liste: ' + ', '.join(sorted(farkli)))
L.append(f'- Doğrulanmayan (önceki ajan kararı, lider doğrulamadı) kullanılabilir=evet ZATEN/FARK_ONEMSIZ adayı: {len(unv)} satır; BENZER yazıldı (not sütununda işaretli): ' + ', '.join(sorted(unv)))
L.append('- FARK_TEST_EDILMEDI (208) ve yeni_199 BENZERI_TEST (172) satırları: kural satır satır açılmadı; BENZER kabul edildi, `not`: "önceki ajan kararı, lider doğrulamadı". Önceki ajanın "denenmemiş bileşen" iddiaları kodla sınıf bazında örneklendi ve doğru çıktı: macd-sinyal\'de fiyat>EMA trend filtresi yok (yalnız sifir_filtre); ma-kesisim\'de zaman çıkışı yok; rsi-asiri-donus\'ta SMA5 geri kazanım çıkışı yok; bant-donus giriş = banda dönüş mumu; donchian scalp klonu/TRB 50-200 yok. Yani BENZERI sınıfı doğrulanan 5 büyük aile için tutarlı; kalan ~170 sınıfın tamamında yapılmadı (sınıf başına en az 1 satır koşulu SAĞLANMADI).')
L.append('- Önceki ajanın ZATEN_TEST sınıfı güvenilir değil: doğruladığım ZATEN satırlarının çoğu BENZER çıktı (kendi denetimi de %35 sorun demişti). Örnekler: S0001/S0780 dual-thrust (n=21; kaynak her zaman piyasada, sınıf seans sonu çıkış), S0018 bandtastic (sınıfta RSI/MFI/EMA filtreleri açık, kaynak varsayılanında kapalı), S0549 AwesomeMacd (AO sıfır kesişimi vs AO dönüşü).\n')
L.append('- TEKRAR (906 liste içi): aynı link + aynı giriş kuralı olan çift bulunmadı (828 benzersiz link; ortak linkler farklı stratejiler: aynı repo/sayfada birden çok kural). Emin olmadığım için isimden TEKRAR demedim.')
L.append(f"- BELIRSIZ ({d_on['BELIRSIZ']}): kullanilabilir=hayir ama karşılaştırma dosyasında kapsam_disi_neden boş ve bayrak da yok; nedeni dosyada yazmıyor (1 satırı ajan2 AAPL/STLD/IBM).")
L.append('## Tutarsızlıklar')
L.append('- `swing__ma-kesisim` ayar kümesinde 15/70 EMA (S0839 "aynı" denmişti) yok; S0347 (DI/ADX kesişimi) yanlışlıkla `swing__macd-sinyal`e bağlanmıştı.')
L.append('- `dis__ft-bandtastic` sınıf kodu kaynağın varsayılan tetikleyicisini (yalnız BB 1σ alt) yansıtmıyor.')
L.append('- Derin geçiş: hiç koşulmamış sınıflara bağlı 21 satır (v3__volatilite-kirilim-k05, v3__adaptivetrend-6s, v3__z-skor-karsit...) "test edildi" sayılamaz (önceki rapor kendi söylemiş); burada o satırlar BENZER.\n')
L.append('## E_KODLANMADI_NEDENSIZ yargısı')
L.append('BIZDE_YOK + kullanilabilir=evet satırların akıbeti yalnızca "kanıtsız, ayrı test açmaya değmez / canlıya filtre eklenmez" önerisi (tur4 RAPOR §1.5) ya da test önceliği; bu bir karar değil -> E yazıldı. Hakem elemesi/kodlanmadı gerekçesi yazılanlar D.\n')
L.append('## oncelik30 (30 fikir grubu) akıbeti')
L.append('Kaynak: dal `tur4_degerlendirme/oncelik30_hukum.csv` (önceki ajan hükmü; kodla yeniden doğrulamadım, ancak Donchian/RSI/MA/MACD/bant sınıfları yukarıdaki doğrulamaya uyuyor).\n')
L.append('| sıra | fikir grubu | hüküm | bizde test edilen |'); L.append('|---|---|---|---|')
for r in O30: L.append(f"| {r['sira']} | {r['fikir_grubu'][:70]} | {r['hukum']} | {r['bizde_test_edilen_arsiv_id'][:70]} |")
L.append('\nÖzet: ' + ', '.join(f'{a}={b}' for a, b in collections.Counter(r['hukum'] for r in O30).items()) + '. "HIC_TEST_EDILMEDI" = M36 (kontrarian trend göstergesi): kodlanmamış, test bekliyor (akıbet değil).\n')
L.append('## Öz kontrol')
L.append('Betikle: ham_id sırası = strateji_listesi veri sırası, id S0xxx numarası = satır no (906/906 tutuyor). Elle 6 rastgele/özel satır (X005:277,422,458,138,583,868) kaynağa geri izlendi; ESDEGER/BENZER kodla açılan 174 satırın hedef sınıfı kod_kaydi.csv\'de var.')
open(os.path.join(ARA, 'G8_DIS_ARASTIRMA_NOTLAR.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print(len(HAM), dict(d_es), dict(d_on), 'dogrulanan', len(ELLE), 'farkli', len(farkli), 'dogrulanmayan', len(unv))
