#!/usr/bin/env python3
"""G3_REPO hesap defteri betiği: repo_kodlari / repo_raporlari / ek77 / xlsx / md listeleri -> ara/G3_REPO_ham.csv.
Yalnız okur; yalnız ara/G3_REPO_* dosyalarını yazar. Elle kararlar: ara/G3_REPO_elle_kararlar.csv (bu betik üretir)."""
import ast, csv, glob, re, sys, json, difflib, collections
from pathlib import Path
import openpyxl

K = Path('/home/user/1L3A-Proje')
ARA = K / 'sonuclar/hesap_defteri/ara'
EK = K / 'stratejiler/ek_kaynaklar'
ST = K / 'stratejiler'
RK, RR, E77, KQ = 'stratejiler/ek_kaynaklar/repo_kodlari.csv', 'stratejiler/ek_kaynaklar/repo_raporlari.csv', 'stratejiler/ek_kaynaklar/ek_77_strateji.md', 'stratejiler/ek_kaynaklar/kodlama_kuyrugu_2026-11-07.csv'
SUTUN = ['ham_id', 'kaynak_id', 'kaynak_satir_no', 'kaynaktaki_ad', 'kisa_mantik', 'aile', 'eslesme', 'hedef', 'ayar_id',
         'ayar_dosyasi', 'fark', 'on_durum', 'neden_kodu', 'neden_metni', 'kanit', 'not']


def oku(p):
    return list(csv.DictReader(open(p, encoding='utf-8')))


def norm(s):
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


# ---------------------------------------------------------------- yüklemeler
rk = oku(K / RK)
rr = oku(K / RR)
de = oku(ST / 'dis_envanter.csv')
kq = oku(K / KQ)
kod = {x['ad']: x for x in oku(ARA / 'kod_kaydi.csv')}
zincir = {}
ZF = {}
for f in sorted(glob.glob(str(ST / 'kodlama_2026-11-07_d1*.csv'))):
    for x in oku(f):
        zincir[x['yeni_aile']] = x
        ZF[x['yeni_aile']] = 'stratejiler/' + Path(f).name
b_csv = oku(ST / 'kodlama_2026-11-07_b.csv')
pf_csv = oku(ST / 'kodlama_2026-11-07_pf.csv')
pa = oku(ST / 'portfoy_adaylari.csv')

_doc = {}


def sinif_doc(ad):
    if ad not in kod:
        return ''
    if ad in _doc:
        return _doc[ad]
    x = kod[ad]
    try:
        t = ast.parse(open(K / x['dosya'], encoding='utf-8').read())
        d = ''
        for n in ast.walk(t):
            if isinstance(n, ast.ClassDef) and n.name == x['sinif']:
                d = ast.get_docstring(n) or ''
                break
        if not d:
            md = ast.get_docstring(t) or ''
            k = md.find(ad)
            d = md[k:k + 420] if k >= 0 else ''
    except Exception:
        d = ''
    _doc[ad] = re.sub(r'\s+', ' ', d)
    return _doc[ad]


def kanit_sinif(ad):
    x = kod.get(ad)
    return f"{x['dosya']}:{x['satir']}" if x else ''


# dis_envanter indeksleri (1 tabanlı veri satırı)
de_ad = collections.defaultdict(list)
de_id = collections.defaultdict(list)
for i, x in enumerate(de, 1):
    de_ad[norm(x['ad'])].append(i)
    m = re.search(r'/([A-Za-z0-9]+)\.pine$', x['dosya'])
    if m:
        de_id[m.group(1)].append(i)

# kuyruk referansları
kq_ref = []
for x in kq:
    for t in x['kaynak_kartlar'].split(';'):
        if t.startswith('repo'):
            k, n = t.split(':', 1)
            kq_ref.append((k, norm(n), x['yeni_aile'], x))


def kuyruk_bul(tur, ad):
    n = norm(ad)
    return [(a, x) for k, r, a, x in kq_ref if k == tur and r and (n.startswith(r) or r.startswith(n))]


AILE_MAP = {'ortalamaya_donus': 'MR', 'trend_takip': 'trend', 'kirilim': 'trend', 'momentum': 'trend'}


def aile_of(kat, metin=''):
    if kat in AILE_MAP:
        return AILE_MAP[kat]
    return 'diger'


def aile_metin(s):
    s = s.lower()
    if re.search(r'ortalamaya dön|reversal|rsi\(?2|mean rev|dip', s):
        return 'MR'
    if re.search(r'trend|momentum|kırılım|breakout|ma ç|cross', s):
        return 'trend'
    return 'diger'


def tv_id(url):
    m = re.search(r'tradingview\.com/script/([A-Za-z0-9]+)', url or '')
    return m.group(1) if m else ''


def bos(**kw):
    d = {c: '' for c in SUTUN}
    d.update(kw)
    return d


# ---------------------------------------------------------------- ortak karar
def zincir_karar(aile_adi, kaynak_ad, tur):
    """kuyruk ailesi -> kodlama zinciri sonucu: (eslesme, hedef, on_durum, neden_kodu, neden_metni, kanit, fark)"""
    z = zincir.get(aile_adi)
    qk = KQ
    if z is None:
        # kuyrukta var, kodlama dosyasında yok -> kodlanmadı; neden kuyruk satırından
        qrow = next((x for k, r, a, x in kq_ref if a == aile_adi), None)
        nt = (qrow['not'] if qrow else '').strip()
        ozet = (qrow['mekanik_ozet'] if qrow else '')
        kb = qrow['kodlanabilirlik'] if qrow else ''
        if 'kapali kaynak' in ozet.lower() or 'kodlanamaz' in ozet.lower():
            return ('YOK', '', 'D_KODLANMADI_NEDENLI', 'kural_belirsiz',
                    'kuyrukta "kapalı kaynak / kural metni erişilemez, kodlanamaz sayılır" yazıyor', f'{qk}#{aile_adi}', '')
        if 'regresyon' in nt and 'ortus' in nt:
            return ('BENZER', 'swing__trend-cizgisi-kanal', 'D_KODLANMADI_NEDENLI', 'benzer_var',
                    'kuyruk notu: swing__trend-cizgisi-kanal (regresyon) ile örtüşüyor olabilir; kodlanmadı', f'{qk}#{aile_adi}',
                    'doğrulanmadı: kuyruk "olabilir" diyor; Zorro regresyon kanalı bölgeleri kuralı sınıfla karşılaştırılmadı')
        if 'karar 18' in nt:
            return ('BENZER', 'dis__ifr2', 'D_KODLANMADI_NEDENLI', 'benzer_var',
                    'karar 18: S3 alınmadı; RSI2 dip fikri dis__ifr2 ile yakın', f'{qk}#{aile_adi}',
                    'S3: S1 yönü + SMA200 + RSI2<10 + ertesi gün limit emir (kapanış-0,5 ATR) + SMA10/RSI2>70/10 gün çıkış; dis__ifr2 = RSI2<esik + Ichimoku bulutu üstü + önceki 2 mum zirvesi çıkışı (limit emir/haftalık yön yok)')
        if 'tanimi yok' in nt or 'tanım' in nt:
            return ('YOK', '', 'D_KODLANMADI_NEDENLI', 'kural_belirsiz', f'kuyruk notu: {nt}', f'{qk}#{aile_adi}', '')
        if nt:
            return ('YOK', '', 'D_KODLANMADI_NEDENLI', 'kural_belirsiz', f'kuyruk notu: {nt}'[:200], f'{qk}#{aile_adi}', '')
        return ('YOK', '', 'D_KODLANMADI_NEDENLI', 'kural_belirsiz',
                f'kuyruğa C önceliğiyle girmiş (kodlanabilirlik={kb or "?"}); kodlama dosyalarında kaydı yok; kural metni kaynakta yok (kaynak durum: kural_metni_yok)',
                f'{qk}#{aile_adi}', '')
    d, ad = z['durum'], z['yeni_strateji_adi']
    kan = f'{ZF[aile_adi]}#{aile_adi}'
    if d == 'kodlandi':
        if ad in kod:
            return ('KOD', ad, 'KOD', '', '', kan + ' ; ' + kanit_sinif(ad), '')
        return ('YOK', ad, 'BELIRSIZ', 'kod_yok', f'kodlama dosyası kodlandi diyor ama {ad} kod_kaydi.csv\'de yok', kan, '')
    if d == 'kurala_dokulemez':
        return ('YOK', '', 'D_KODLANMADI_NEDENLI', 'kural_belirsiz', z['gerekce'][:200], kan, '')
    if d == 'veri_yok':
        return ('YOK', '', 'D_KODLANMADI_NEDENLI', 'veri_yok', z['gerekce'][:200], kan, '')
    if d.startswith('mevcut:'):
        h = d.split(':', 1)[1]
        return ('BENZER', h, 'D_KODLANMADI_NEDENLI', 'benzer_var', f'kodlama dosyası "{d}" diyor: ' + z['gerekce'][:150], kan,
                'kaynak kuralı hedef sınıfla birebir karşılaştırılamadı (kaynakta ayrı kural/kod yok ya da kitap tablosu ayrı); kodlama dosyasının iddiası: ' + z['gerekce'][:200])
    return ('YOK', '', 'BELIRSIZ', '', f'beklenmeyen durum {d}', kan, '')


def uygula(satir, k):
    satir.update(dict(zip(['eslesme', 'hedef', 'on_durum', 'neden_kodu', 'neden_metni', 'kanit', 'fark'], k)))


# ---------------------------------------------------------------- elle kararlar (belirli satırlar için)
ELLE = []  # (ham_id, alan_ozeti, karar, neden)


def elle(ham_id, karar, neden):
    ELLE.append((ham_id, karar, neden))


# ---------------------------------------------------------------- P001: repo_kodlari
def liste_id(x):
    m = re.search(r'liste_id=([A-Z]\d-\d+)', x['ayar_durumu'])
    return m.group(1) if m else ''


def url_of(x):
    m = re.search(r'url=(\S+?)(?:;|$)', x['ayar_durumu'])
    return m.group(1) if m else ''


def ayar_hedef(durum):
    return durum.split(':', 1)[1] if ':' in durum else ''


ham = []
P001 = {}
for i, x in enumerate(rk, 1):
    hid = f'P001:{i}'
    s = bos(ham_id=hid, kaynak_id='P001', kaynak_satir_no=str(i), kaynaktaki_ad=x['ad'][:120],
            kisa_mantik=x['mekanik_ozet'][:160], aile=aile_of(x['kategori']))
    s['not'] = f"kaynak={x['kaynak']}; kaynak_durum={x['durum'].split(':')[0]}"
    d = x['durum']
    dk = d.split(':', 1)[0]
    P001[i] = s
    # 0) TradingView betiği dis_envanter'de aynı id ile var mı
    tid = tv_id(url_of(x))
    if not tid:
        m = re.search(r'\(([A-Za-z0-9]{8})\)\s*$', x['ad'])
        if m and m.group(1) in de_id:
            tid = m.group(1)
    if tid and tid in de_id:
        j = de_id[tid][0]
        s.update(eslesme='TEKRAR', hedef=f'D001:{j}', on_durum='TEKRAR', neden_kodu='kopya',
                 neden_metni=f'aynı TradingView betiği ({tid}) dis_envanter satır {j}',
                 kanit=f"stratejiler/dis_envanter.csv:{j} ({de[j-1]['dosya']})")
        P001[i]['not'] += f'; tv_id={tid}'
        ham.append(s)
        continue
    kmd = x['kaynak']
    if dk == 'yeni':
        refs = kuyruk_bul('repo_kodlari', x['ad'])
        if refs:
            a = refs[0][0]
            uygula(s, zincir_karar(a, x['ad'], 'repo_kodlari'))
            s['not'] += f'; yeni_aile={a}'
        else:
            s.update(eslesme='YOK', on_durum='E_KODLANMADI_NEDENSIZ', neden_metni='kuyrukta ve kodlama dosyalarında akıbeti yok')
    elif dk == 'yasak':
        s.update(eslesme='YOK', on_durum='F_YASAK_TIP', neden_kodu='dca', neden_metni=(x['ayar_durumu'] or 'DCA/grid/martingale')[:140],
                 kanit=f'{RK}:{i}')
    elif dk == 'ml':
        s.update(eslesme='YOK', on_durum='G_ML', neden_kodu='ml', neden_metni='makine öğrenmesi/yapay zeka stratejisi', kanit=f'{RK}:{i}')
    elif dk == 'veri_yok':
        s.update(eslesme='YOK', on_durum='H_BIZIM_EVRENDE_UYGULANAMAZ', neden_kodu='opsiyon',
                 neden_metni=x['ayar_durumu'][:120] or 'veri/enstrüman evrende yok', kanit=f'{RK}:{i}')
    elif dk == 'kural_yok':
        s.update(eslesme='YOK', on_durum='D_KODLANMADI_NEDENLI', neden_kodu='kural_belirsiz',
                 neden_metni='kural/kod erişilemez ya da belirtilmemiş (kaynak durum kural_yok)', kanit=f'{RK}:{i}')
    elif dk in ('ayar', 'mevcut'):
        h = ayar_hedef(d)
        ex = h in kod
        doc = sinif_doc(h)[:150]
        heur = 'heuristik' in x['ayar_durumu']
        s.update(eslesme='BENZER', hedef=h if ex else '', on_durum='D_KODLANMADI_NEDENLI', neden_kodu='benzer_var',
                 neden_metni='kaynak "ayar/mevcut" diyor; ayar dosyalarında bu satıra ait kayıt yok' if dk == 'ayar' else 'kaynak "mevcut" diyor; kural karşılaştırması aşağıda',
                 kanit=f'{RK}:{i} ; {kanit_sinif(h)}')
        s['fark'] = (('anahtar kelime eşlemesi (doğrulanmadı); ' if heur else '') + f"kaynak: {x['mekanik_ozet'][:110]} | sınıf {h}: {doc}")
        if not ex:
            s.update(hedef='', eslesme='YOK', on_durum='BELIRSIZ', neden_metni=f'hedef sınıf {h} kod_kaydi.csv\'de yok')
    ham.append(s)

# elle düzeltmeler P001 (mevcut:X satırlarının incelenmesi) sonradan uygulanır: bkz. elle_p001()

# ---------------------------------------------------------------- P002: repo_raporlari
def yasak_tur(txt):
    t = txt.lower()
    if 'katlama' in t or 'martingale' in t:
        return 'martingale'
    if 'izgara' in t or 'grid' in t:
        return 'stopsuz_grid'
    return 'dca'


P002 = {}
for i, x in enumerate(rr, 1):
    hid = f'P002:{i}'
    s = bos(ham_id=hid, kaynak_id='P002', kaynak_satir_no=str(i), kaynaktaki_ad=x['ad'][:120],
            kisa_mantik=x['mekanik_ozet'][:160], aile=aile_of(x['kategori']))
    d = x['durum']
    dk = d.split(':', 1)[0]
    s['not'] = f"kaynak={x['kaynak']}; kaynak_durum={dk}"
    P002[i] = s
    cand = de_ad.get(norm(x['ad']), [])
    tekrar = None
    if x['kaynak'] == 'tv_listesi' and cand:
        if len(cand) == 1:
            tekrar = cand[0]
        else:
            ok = []
            for j in cand:
                key = f"durum={de[j-1]['durum']}; {de[j-1]['ayar_durumu']}"[:50]
                if key in x['ayar_durumu']:
                    ok.append(j)
            if len(ok) == 1:
                tekrar = ok[0]
            else:
                s['not'] += f'; dis_envanter aynı adlı satırlar={cand} (ayrıştırılamadı)'
    if tekrar:
        s.update(eslesme='TEKRAR', hedef=f'D001:{tekrar}', on_durum='TEKRAR', neden_kodu='kopya',
                 neden_metni=f'aynı ad (tv_listesi <-> dis_envanter satır {tekrar}); dis_envanter kararı: {de[tekrar-1]["durum"]}/{de[tekrar-1]["ayar_durumu"][:60]}',
                 kanit=f"{RR}:{i} ; stratejiler/dis_envanter.csv:{tekrar}")
        continue
    if dk == 'yasak':
        tur = yasak_tur(x['ayar_durumu'] + x['mekanik_ozet'])
        s.update(eslesme='YOK', on_durum='F_YASAK_TIP', neden_kodu=tur, neden_metni=x['ayar_durumu'][:140], kanit=f'{RR}:{i}')
    elif dk == 'arac_sablon':
        s.update(eslesme='YOK', on_durum='D_KODLANMADI_NEDENLI', neden_kodu='arac_sablon',
                 neden_metni='liste/dis_envanter "araç/şablon" diyor, strateji değil', kanit=f'{RR}:{i}')
    elif dk == 'kurala_dokulemez':
        s.update(eslesme='YOK', on_durum='D_KODLANMADI_NEDENLI', neden_kodu='kural_belirsiz',
                 neden_metni='dis_envanter/kodlama kararı: kurala dökülemez (çok girişli/kullanıcı seçimli)', kanit=f'{RR}:{i}')
    elif dk == 'ml_elendi':
        s.update(eslesme='YOK', on_durum='G_ML', neden_kodu='ml', neden_metni='ML (Lorentzian/XGBoost/HMM) — DURUM.md ML elemesi', kanit=f'{RR}:{i}')
    elif dk == 'veri_yok':
        s.update(eslesme='YOK', on_durum='H_BIZIM_EVRENDE_UYGULANAMAZ', neden_kodu='veri_yok',
                 neden_metni=x['ayar_durumu'][:140], kanit=f'{RR}:{i}')
    elif dk == 'yeni':
        refs = kuyruk_bul('repo_raporlari', x['ad'])
        if refs:
            a = refs[0][0]
            uygula(s, zincir_karar(a, x['ad'], 'repo_raporlari'))
            s['not'] += f'; yeni_aile={a}'
        else:
            s.update(eslesme='YOK', on_durum='E_KODLANMADI_NEDENSIZ', neden_metni='kuyrukta ve kodlama dosyalarında akıbeti yok')
    elif dk in ('ayar', 'mevcut'):
        h = ayar_hedef(d)
        ex = h in kod
        doc = sinif_doc(h)[:150]
        fuzzy = 'ad benzerliğiyle' in x['ayar_durumu']
        s.update(eslesme='BENZER', hedef=h if ex else '', on_durum='D_KODLANMADI_NEDENLI', neden_kodu='benzer_var',
                 neden_metni='kaynak "ayar/mevcut" diyor; ayar dosyalarında bu satıra ait kayıt yok', kanit=f'{RR}:{i} ; {kanit_sinif(h)}')
        s['fark'] = (('dis_envanter ile ad benzerliği eşlemesi (aynı betik doğrulanamadı); ' if fuzzy else '') +
                     f"kaynak: {x['ayar_durumu'][:120]} | sınıf {h}: {doc}")
        if not ex:
            s.update(hedef='', eslesme='YOK', on_durum='BELIRSIZ', neden_metni=f'hedef sınıf {h} kod_kaydi.csv\'de yok')

# ---------------------------------------------------------------- sınıf docstring'indeki TradingView id'leri ile TEKRAR
DOC_ID_REDDET = {('P001', 6), ('P001', 7), ('P001', 33), ('P001', 60), ('P002', 52)}


def doc_id_tekrar(nm, P, R):
    n_degisen = 0
    for k, s in P.items():
        if s['eslesme'] != 'BENZER' or not s['hedef'].startswith('dis__') or (nm, k) in DOC_ID_REDDET:
            continue
        ids = [t for t in re.findall(r'[A-Za-z0-9]{8}', sinif_doc(s['hedef'])) if t in de_id]
        if not ids:
            continue
        j = de_id[ids[0]][0]
        r = difflib.SequenceMatcher(None, norm(R[k - 1]['ad']), norm(de[j - 1]['ad'])).ratio()
        if r >= 0.45:
            ELLE.append((s['ham_id'], f'TEKRAR D001:{j}',
                         f'hedef sınıf {s["hedef"]} docstring\'i TradingView betiği {ids[0]}\'ı kaynak gösteriyor = dis_envanter satır {j} ("{de[j-1]["ad"][:50]}"); ad benzerliği {r:.2f}'))
            s.update(eslesme='TEKRAR', hedef=f'D001:{j}', on_durum='TEKRAR', neden_kodu='kopya', fark='', ayar_id='', ayar_dosyasi='',
                     neden_metni=f'aynı TradingView betiği ({ids[0]}) = dis_envanter satır {j}; sınıf {s["hedef"]} bu betikten kodlanmış',
                     kanit=f'{s["kanit"]} ; stratejiler/dis_envanter.csv:{j}')
            n_degisen += 1
    return n_degisen


doc_id_tekrar('P001', P001, rk)
doc_id_tekrar('P002', P002, rr)

# ---------------------------------------------------------------- P001 / P002 elle düzeltmeler
def set_(P, k, nm, **kw):
    s = P[k]
    for a in ('ayar_id', 'ayar_dosyasi', 'fark'):
        s[a] = ''
    s.update(kw)
    return s


def elle_p(P, k, nm, neden, **kw):
    set_(P, k, nm, **kw)
    ELLE.append((P[k]['ham_id'], ' '.join(f'{a}={b}' for a, b in kw.items() if a in ('eslesme', 'hedef', 'on_durum', 'neden_kodu'))[:200], neden))


H = 'H_BIZIM_EVRENDE_UYGULANAMAZ'
D = 'D_KODLANMADI_NEDENLI'
F = 'F_YASAK_TIP'
# veri_yok / yasak alt türleri (kaynak durum metni okunarak)
elle_p(P001, 38, 'P001', 'kaynak "DCA/Grid/Martingale ailesi" tek satır; alt tür birleşik', on_durum=F, neden_kodu='dca', neden_metni='DCA / grid / martingale ailesi (kaynakta alt türler ayrılmamış)')
elle_p(P001, 45, 'P001', 'kaynak: 10 sn verisi (min TF 5dk)', on_durum=D, neden_kodu='veri_yok', neden_metni='10 saniyelik veri evrende yok (en küçük TF 5dk)')
elle_p(P001, 91, 'P001', 'tick grafiği + ücretli ürün', on_durum=D, neden_kodu='veri_yok', neden_metni='tick verisi gerektiriyor, ücretli kapalı ürün; kaynak durum veri_yok')
elle_p(P001, 115, 'P001', 'SPX opsiyon gün stratejisi (ThinkorSwim)', on_durum=H, neden_kodu='opsiyon', neden_metni='SPX opsiyon gün stratejisi')
elle_p(P001, 149, 'P001', 'VIX MA + Brain sentiment verisi', on_durum=H, neden_kodu='vix', neden_metni='VIX + alternatif duygu verisi (Brain Market Sentiment) gerektirir')
elle_p(P001, 261, 'P001', 'bilanço/olay verisi', on_durum=D, neden_kodu='veri_yok', neden_metni='bilanço açıklama tarihleri verisi evrende yok')
elle_p(P001, 267, 'P001', 'TRF perakende emir akışı', on_durum=H, neden_kodu='orderbook', neden_metni='perakende emir akışı (TRF) verisi gerektirir')
elle_p(P001, 268, 'P001', 'OFI emir akışı', on_durum=H, neden_kodu='orderbook', neden_metni='sabah emir akışı dengesizliği (OFI) verisi gerektirir')
elle_p(P001, 348, 'P001', 'opsiyon spread', on_durum=H, neden_kodu='opsiyon', neden_metni='0DTE opsiyon spread')
elle_p(P001, 356, 'P001', 'opsiyon spread', on_durum=H, neden_kodu='opsiyon', neden_metni='put credit spread (opsiyon)')
elle_p(P001, 368, 'P001', 'geometrik grid', on_durum=F, neden_kodu='stopsuz_grid', neden_metni='geometrik grid botu: her seviye bağımsız alış, stop yok')
elle_p(P001, 370, 'P001', 'kademeli alım', on_durum=F, neden_kodu='ortalama_dusurme', neden_metni='RSI<31 sonrası kademeli alım (ortalama düşürme)')
# kuyruk/kodlama dosyası: bu kaynaklar kodlanmadı (gerekçede açıkça yazıyor)
for k in (107, 212, 222):
    elle_p(P001, k, 'P001', 'kodlama d10a gerekçesi: Blue Monday DAX ve Monday/Tuesday-Monday reversal repo satırlarının kuralları üyelere özel, kodlanmadı',
           eslesme='YOK', hedef='', on_durum=D, neden_kodu='kural_belirsiz', neden_metni='kuralları üyelere özel/erişilemez; dis__hafta-ici-takvim bu satırdan kodlanmadı (yalnız cuma_pzt/pzt_sali/sali_persembe modları)',
           kanit='stratejiler/kodlama_2026-11-07_d10a.csv#yeni__hafta-ici-takvim')
elle_p(P001, 253, 'P001', 'kuyruk notu: çift sınıflı hisse long-short, pf__pairs ailesi', eslesme='YOK', hedef='', on_durum=H, neden_kodu='pairs',
       neden_metni='ABD çift sınıflı hisse çiftleri long-short (hisse kesitsel/pairs); evrende çift sınıflı hisse yok',
       kanit=f'{KQ}#yeni__kapali-kaynak-sistemler')
for k, h in ((137, 'DevZenPro'), (138, 'pandianmn')):
    elle_p(P001, k, 'P001', 'kuyruk notu: Strategy002-004 dis__ft-strategy002/003/004 olarak kodlu; 001/005 kodlanmadı',
           eslesme='BENZER', hedef='dis__ft-strategy002', on_durum=D, neden_kodu='benzer_var',
           neden_metni='freqtrade fork deposu; Strategy002-004 zaten kodlu (dis__ft-strategy002/003/004), 001/005 kodlanmadı',
           fark='depo=Strategy001-004/005 fork; sınıflar yalnız 002/003/004 kuralını taşır (RSI+stok+BB+çekiç / Fisher RSI+MFI / ADX+CCI); 001 ve 005 kodlanmadı; fork içeriği dosya düzeyinde karşılaştırılmadı',
           kanit=f'{KQ}#yeni__kapali-kaynak-sistemler ; {kanit_sinif("dis__ft-strategy002")}')
# xlsx 'yeni' olup 'Quantified Strategies beşli portföy': md satırları ayrı kurallar veriyor -> NOTLAR'da tutarsızlık
# P002 elle
for k, why in ((28, 'KISS 5dk saat çıkışlı'), (51, 'RSI+MA yığını')):
    elle_p(P002, k, 'P002', f'kodlama d10a gerekçesi: "KISS 5dk saat çıkışlı ve RSI+MA yığını repo satırları kodlanmadı" ({why})',
           eslesme='YOK', hedef='', on_durum=D, neden_kodu='kural_belirsiz', neden_metni='dis__ma-mukemmel-siralama yalnız Lien kuralından kodlandı; bu repo satırı kodlanmadı',
           kanit='stratejiler/kodlama_2026-11-07_d10a.csv#yeni__ma-mukemmel-siralama')
for k, why in ((45, 'pzt_sali'), (46, 'sali_persembe')):
    P002[k]['not'] += f'; mod={why}'
# onceki__ sınıf docstring'leri bu satırların portu olduğunu açıkça yazıyor -> KOD
ONCEKI = {63: ('onceki__s1-geri-cekilme', 's1_geri_cekilme.py', 'swing-sg S1'), 64: ('onceki__4s-kirilim', 'kirilim_4s.py', 'swing-sg S2'),
          71: ('onceki__4s-kirilim', 'kirilim_4s.py', 'algo-sg A1'), 73: ('onceki__kapitulasyon', 'kapitulasyon.py', 'algo-sg B'),
          69: ('onceki__kgt', 'kgt.py', 'strateji-sg KGT v3')}
for k, (h, f, kay) in ONCEKI.items():
    elle_p(P002, k, 'P002', f'motor/strateji/onceki/{f} modül docstring\'i "{kay}" kaynağından yeniden yazıldığını yazıyor; DURUM.md karar 18/21',
           eslesme='KOD', hedef=h, on_durum='KOD', neden_kodu='', neden_metni='',
           kanit=f'{RR}:{k} ; motor/strateji/onceki/{f}:1 ; {kanit_sinif(h)}')
elle_p(P002, 70, 'P002', 'pf__kesit_ls docstring\'i KMN kaynağını (arsiv/strateji-sg/backtest/momentum.py) açıkça yazıyor; baglama.py satir=16 KMN ayarı',
       eslesme='KOD', hedef='pf__kesit_ls', on_durum='KOD', neden_kodu='', neden_metni='',
       ayar_id='baglama:satir16', ayar_dosyasi='motor/portfoy/stratejiler/baglama.py (BAGLAMA satir=16; stratejiler/portfoy_adaylari.csv pf_ayar)',
       kanit=f'{RR}:70 ; motor/portfoy/stratejiler/kesit.py ; stratejiler/portfoy_adaylari.csv:17')
# freqtrade: aynı dosya
for k, j, h in ((34, 294, 'dis__ft-reinforced-smoothscalp'), (60, 248, 'dis__ft-adx-momentum')):
    elle_p(P002, k, 'P002', f'dis_envanter satır {j} = {de[j-1]["ad"]} ({de[j-1]["dosya"]}); sınıf {h} docstring\'i aynı dosyayı kaynak gösteriyor',
           eslesme='TEKRAR', hedef=f'D001:{j}', on_durum='TEKRAR', neden_kodu='kopya', neden_metni=f'aynı freqtrade stratejisi dis_envanter satır {j}',
           kanit=f'{RR}:{k} ; stratejiler/dis_envanter.csv:{j} ; {kanit_sinif(h)}')
# KGT v3 ve S3 notları
P002[65]['not'] += '; karar 18: S3 alınmadı (DURUM.md)'

# ---------------------------------------------------------------- P003: ek_77_strateji.md
e77 = {}
for l in open(K / E77, encoding='utf-8'):
    m = re.match(r'### (\d+)\. (.*)', l)
    if m:
        e77[int(m.group(1))] = re.sub(r'\s*★+\s*$', '', m.group(2))
e77_ozet = {}
for l in open(K / E77, encoding='utf-8'):
    m = re.match(r'\| (\d+) \| (.*?) \| (.*?) \| (.*?) \|', l)
    if m:
        e77_ozet[int(m.group(1))] = (m.group(3)[:150])
mant = {}
cur = None
for l in open(K / E77, encoding='utf-8'):
    m = re.match(r'### (\d+)\.', l)
    if m:
        cur = int(m.group(1))
    if cur and l.startswith('**Mantık:**') and cur not in mant:
        mant[cur] = re.sub(r'\s+', ' ', l[len('**Mantık:**'):]).strip()

bmap = {int(x['satir_indeksi_veya_madde_no']): x for x in b_csv if x['kaynak_dosya'] == 'ek77'}
pf_by_ad = {norm(x['ad'])[:20]: x for x in pf_csv}
BAGLAMA_SATIR = {1: 0, 22: 1, 23: 2, 25: 3, 26: 4, 27: 5, 39: 8, 55: 9, 56: 10, 64: 11, 65: 12, 66: 13}  # ek77 no -> portfoy_adaylari 0-tabanlı satır
BAG_SINIF = {1: 'pf__rotasyon', 22: 'pf__gem', 23: 'pf__kanarya', 25: 'pf__rotasyon', 26: 'pf__trend_sepet', 27: 'pf__rotasyon', 39: 'pf__pairs',
             55: 'pf__pca_statarb', 56: 'pf__pairs', 64: 'pf__gem', 65: 'pf__wq_alfa', 66: 'pf__rotasyon'}
BAG_AYAR_ID = {1: 'clenow-yok:momentumregime', }
D5_KOD = {16: 'dis__e0v1en', 18: 'dis__ifr2', 20: 'dis__ott-bantlari', 21: 'dis__sparta-whb', 24: 'dis__connors-etf', 28: 'dis__tsmom',
          33: 'dis__ibs-donus', 36: 'dis__dual-thrust', 37: 'dis__r-breaker', 61: 'dis__gun-ici-donus', 71: 'dis__ema50-200-geri', 2: 'dis__funding-carry'}
D5_KANIT = {2: 'motor/strateji/dis/d6_funding.py:21', 71: 'motor/strateji/dis/d5_ek.py:1'}
AYAR77 = {19: ('swing__donchian-kirilim', 'ek77:19', 'stratejiler/dis_ayarlari/swing__donchian-kirilim.json'),
          60: ('daytrade__orb', 'ek77:60', 'stratejiler/dis_ayarlari/daytrade__orb.json'),
          62: ('dis__dual-thrust', 'ek77:62', 'stratejiler/dis_ayarlari/dis__dual-thrust.json'),
          67: ('dis__dual-thrust', 'ek77:62', 'stratejiler/dis_ayarlari/dis__dual-thrust.json')}
for n, (h, aid, f) in AYAR77.items():  # ayar gerçekten dosyada mı?
    j = json.load(open(K / f, encoding='utf-8'))
    assert any(r.get('dis_id') == aid for r in j), (n, aid, f)

H = 'H_BIZIM_EVRENDE_UYGULANAMAZ'
P003 = {}
for n in range(1, 78):
    ad = e77[n]
    s = bos(ham_id=f'P003:{n}', kaynak_id='P003', kaynak_satir_no=str(n), kaynaktaki_ad=ad[:120], kisa_mantik=mant.get(n, '')[:160],
            aile=aile_metin(mant.get(n, '') + ' ' + ad))
    P003[n] = s
    s['not'] = ''
    b = bmap.get(n)
    kan_b = f'stratejiler/kodlama_2026-11-07_b.csv#ek77:{n}'

    def kodla(h, kan, extra=''):
        s.update(eslesme='KOD', hedef=h, on_durum='KOD', kanit=kan + ' ; ' + kanit_sinif(h))
        if h not in kod:
            s.update(on_durum='BELIRSIZ', eslesme='YOK', neden_metni=f'{h} kod_kaydi.csv\'de yok')
        if extra:
            s['not'] = extra

    if n in D5_KOD:
        h = D5_KOD[n]
        kodla(h, D5_KANIT.get(n, 'motor/strateji/dis/d5_ek.py:1') + f' (docstring "belge #{n}")')
        if n == 36:
            s['not'] = 'dis__dual-thrust #36/#62/#67 birleşik; ayrıca dis_ayarlari ek77:36 kaydı var'
            s['ayar_id'], s['ayar_dosyasi'] = 'ek77:36', 'stratejiler/dis_ayarlari/dis__dual-thrust.json'
        continue
    if n in AYAR77:
        h, aid, f = AYAR77[n]
        s.update(eslesme='AYAR', hedef=h, ayar_id=aid, ayar_dosyasi=f, on_durum='KOD', kanit=f'{f}#{aid} ; {kanit_sinif(h)}')
        if n == 67:
            s['not'] = 'ek77:62 ayar kaydının kaynak_dosya alanı "#62 ve #67 (TqSdk Dual Thrust)" diyor'
        continue
    if n in BAGLAMA_SATIR and n not in (34, 35):
        h = BAG_SINIF[n]
        sat = BAGLAMA_SATIR[n]
        if n == 55:
            kodla(h, f'stratejiler/kodlama_2026-11-07_pf.csv#ArbitrageLab PCA ; motor/portfoy/stratejiler/ek2.py:3 ; stratejiler/portfoy_adaylari.csv:{sat+2}')
            s['ayar_id'], s['ayar_dosyasi'] = f'baglama_ek2:satir{sat}', 'motor/portfoy/stratejiler/ek2.py (BAGLAMA_EK2)'
        elif n == 65:
            kodla(h, f'motor/portfoy/stratejiler/baglama.py (satir={sat}) ; stratejiler/portfoy_adaylari.csv:{sat+2}')
            s['ayar_id'], s['ayar_dosyasi'] = f'baglama:satir{sat}', 'motor/portfoy/stratejiler/baglama.py'
            s['not'] = 'pf__wq_alfa sınıfı bu satır için yazılmış (WqAlfa); alfa=101 ayarı bağlama kaydında'
        else:
            ek2 = n == 25
            dosya = 'motor/portfoy/stratejiler/ek2.py (BAGLAMA_EK2)' if ek2 else 'motor/portfoy/stratejiler/baglama.py'
            s.update(eslesme='AYAR', hedef=h, ayar_id=f'baglama{"_ek2" if ek2 else ""}:satir{sat}', ayar_dosyasi=dosya, on_durum='KOD',
                     kanit=f'{dosya.split(" ")[0]} (satir={sat}) ; stratejiler/portfoy_adaylari.csv:{sat+2} ; {kanit_sinif(h)}')
            if n == 25:
                s['kanit'] += ' ; stratejiler/kodlama_2026-11-07_pf.csv#clenow_18hisse (kodlandi)'
                s['not'] = 'portfoy_adaylari.csv\'de pf_sinif sütunu boş kalmış; bağlama ek2.BAGLAMA_EK2 + pf.csv kodlandi kaydıyla var'
            if n == 26:
                s['not'] = 'bağlama iki kayıt: pf__trend_sepet (Faber/Ivy) + pf__kanarya (VAA); KDA kodlanmadı'
        continue
    if n == 34 or n == 35:
        s.update(eslesme='YOK', on_durum='D_KODLANMADI_NEDENLI', neden_kodu='veri_yok',
                 neden_metni='temel veri (EV/EBITDA, ROA) ya da 3x ETN fiyat/ürün verisi evrende yok, vekil kurulmadı' if n == 34 else 'UGLD/DGLD 3x ETN çifti evrende yok',
                 kanit='stratejiler/kodlama_2026-11-07_pf.csv#' + ('Greenblatt' if n == 34 else 'UGLD/DGLD'))
        continue
    if n == 17:
        s.update(eslesme='BENZER', hedef='swing__ma-kesisim', on_durum='D_KODLANMADI_NEDENLI', neden_kodu='benzer_var',
                 neden_metni='d5_ek.py docstring "mevcut ayarlarla aynı" diyor; sınıfla karşılaştırıldı, tam aynı değil',
                 fark='kaynak: EMA9/21 yukarı kesişimi + MUM DİBİ > EMA200, çıkış ters kesişim ya da dip<EMA200, sabit stop -%20; sınıf swing__ma-kesisim (hızlı 9/yavaş 21 varsayılan, ma_tipi=ema) trend_ma filtresini KAPANIŞ ile uygular, EMA200 altı çıkış yok, ATR stop',
                 kanit='motor/strateji/dis/d5_ek.py:99 ; ' + kanit_sinif('swing__ma-kesisim'))
        ELLE.append(('P003:17', 'BENZER swing__ma-kesisim', 'd5_ek.py "mevcut ayarlarla aynı" iddiası sınıf kodu açılarak denendi: filtre/çıkış/stop farkı var'))
        continue
    if n == 69:
        s.update(eslesme='BENZER', hedef='swing__supertrend-psar', on_durum='D_KODLANMADI_NEDENLI', neden_kodu='benzer_var',
                 neden_metni='d5_ek.py docstring "mevcut ayarlarla aynı" diyor; sınıfla karşılaştırıldı, ek giriş kolu yok',
                 fark='kaynak: Supertrend(10,3) yön değişimi giriş/ters değişimde çıkış + trend yönünde EMA(20) geri kazanımında EK giriş (daha iyi fiyatta) + isteğe bağlı %1,5 kâr al; sınıf: yön değişimi girişi/çıkışı var (atr 10, çarpan 3), ek giriş ve %1,5 hedef yok',
                 kanit='motor/strateji/dis/d5_ek.py:99 ; ' + kanit_sinif('swing__supertrend-psar'))
        ELLE.append(('P003:69', 'BENZER swing__supertrend-psar', 'd5_ek.py "mevcut ayarlarla aynı" iddiası sınıf kodu açılarak denendi: ek EMA20 giriş kolu sınıfta yok'))
        continue
    if b is None:
        # ek77 #54: hiçbir dosyada yok
        s.update(eslesme='YOK', on_durum='G_ML', neden_kodu='ml',
                 neden_metni='kaynak metni: vade yapısı/momentum özelliklerinden ML modelleriyle getiri tahmini (CME vadeli, 30 kontrat)',
                 kanit=f'{E77}#54')
        s['not'] = 'HİÇBİR kodlama/eşleme dosyasında akıbeti yok (b.csv, pf.csv, portfoy_adaylari, d5_ek docstring taranmadı-bulunamadı); G sınıfı kaynak metnine dayanıyor, lider teyit etmeli'
        ELLE.append(('P003:54', 'G_ML (akıbet kaydı yok)', 'hiçbir dosyada akıbeti yok; ML model tahmini olduğu için G'))
        continue
    d = b['durum']
    g = b['gerekce']
    if d == 'kodlandi':
        kodla(b['yeni_strateji_adi'], kan_b)
        if n == 72:
            s['not'] = 'SmaCross kolu: swing__ma-kesisim ayarıyla aynı (b.csv gerekçesi; doğrulanmadı)'
        if n == 59:
            s['not'] = 'yalnız saf giriş kuralı kodlandı; Grid/martingale benzeri commit ayarı yasak olduğu için alınmadı'
        continue
    # kodlanmayanlar
    s['kanit'] = kan_b
    if n == 29:
        s.update(eslesme='ESDEGER', hedef='dis__ay-donumu', on_durum='KOD', fark='yok',
                 kanit=kan_b + ' ; ' + kanit_sinif('dis__ay-donumu'),
                 neden_metni='sınıf kodu açıldı: ayın son gününe giris_kalan kala giriş, ayın 3. günü çıkış; kaynak son gün açılışı~sondan ikinci gün kapanışı; parametreler (giris_kalan 1-3, cikis_gun 2/3/5) ızgara içinde')
        ELLE.append(('P003:29', 'ESDEGER dis__ay-donumu', 'sınıf docstring+ızgara açılarak doğrulandı (kaynak: ay sonu işlem günü al, ~3. gün çık, stop yok)'))
        continue
    if n == 68:
        s.update(eslesme='ESDEGER', hedef='swing__donchian-kirilim', on_durum='KOD', fark='yok',
                 kanit=kan_b + ' ; ' + kanit_sinif('swing__donchian-kirilim'),
                 neden_metni='sınıf kodu açıldı: giris_n=20/cikis_n=10 varsayılan, kanal mevcut mum hariç; kaynak 20 gün yüksek/düşük girişi + 10 gün ters kanal çıkışı')
        ELLE.append(('P003:68', 'ESDEGER swing__donchian-kirilim', 'sınıf kodu açılarak doğrulandı (20/10 Turtle kanalı)'))
        continue
    if n == 57:
        s.update(eslesme='BENZER', hedef='dis__ewmac-carver', on_durum='D_KODLANMADI_NEDENLI', neden_kodu='benzer_var',
                 neden_metni='b.csv "MEVCUT: dis__ewmac-carver ve dis__ewmac-carry zaten kodluyor" diyor; sınıf açıldı: EWMAC kısmı aynı, carry kısmı farklı',
                 fark='EWMAC: aynı (16/64, 32/128... sabit ölçek, ±20 kırpma) ama sınıf sürekli forecast pozisyonu yerine ayrık işlem+ATR felaket stopu; Carry: kaynak vadeli kontrat farkı (nerpu), dis__ewmac-carry funding oranını vekil kullanıyor, kontrat vade farkı verisi yok',
                 kanit=kan_b + ' ; ' + kanit_sinif('dis__ewmac-carver') + ' ; ' + kanit_sinif('dis__ewmac-carry'))
        ELLE.append(('P003:57', 'BENZER dis__ewmac-carver', 'b.csv "zaten kodluyor" iddiası: carry bileşeni vadeli kontrat farkı, bizde funding vekili -> tam aynı değil'))
        continue
    gl = g.lower()
    if d == 'yasak':
        tur = 'martingale' if ('martingale' in gl) else ('stopsuz_grid' if 'ızgara' in gl else 'dca')
        s.update(eslesme='YOK', on_durum='F_YASAK_TIP', neden_kodu=tur, neden_metni=g[:160])
    elif d == 'kurala_dokulemez':
        s.update(eslesme='YOK', on_durum='D_KODLANMADI_NEDENLI', neden_kodu='kural_belirsiz', neden_metni=g[:160])
    elif d == 'veri_yok':
        if 'emir defteri' in gl or 'l2' in gl:
            kd = 'orderbook'
        elif 'dex' in gl or 'zincir' in gl:
            kd = 'defi'
        elif 'arbitraj' in gl or 'çok borsalı' in gl:
            kd = 'arbitraj'
        else:
            kd = 'veri_yok'
        if kd == 'veri_yok':
            s.update(eslesme='YOK', on_durum='D_KODLANMADI_NEDENLI', neden_kodu=kd, neden_metni=g[:160])
        else:
            s.update(eslesme='YOK', on_durum=H, neden_kodu=kd, neden_metni=g[:160])
    elif d == 'kapsam_disi':
        if 'opsiyon' in gl:
            s.update(eslesme='YOK', on_durum=H, neden_kodu='opsiyon', neden_metni=g[:160])
        elif 'makine' in gl or 'pekiştirmeli' in gl or 'öğrenme' in gl:
            s.update(eslesme='YOK', on_durum='G_ML', neden_kodu='ml', neden_metni=g[:160])
        elif 'market making' in gl or 'l2' in gl:
            s.update(eslesme='YOK', on_durum=H, neden_kodu='hft', neden_metni=g[:160])
        else:
            s.update(eslesme='YOK', on_durum='D_KODLANMADI_NEDENLI', neden_kodu='kapsam_disi', neden_metni=g[:160])
    else:
        s.update(eslesme='YOK', on_durum='BELIRSIZ', neden_metni=f'beklenmeyen durum {d}')

# ---------------------------------------------------------------- xlsx satırları (P006 = strateji_listesi.xlsx, P007 = strateji_listesi (2).xlsx)
lid2p001 = {}
for i, x in enumerate(rk, 1):
    t = liste_id(x)
    if t:
        lid2p001[t] = i


def xlsx_satirlari(yol, kid):
    wb = openpyxl.load_workbook(K / yol, read_only=True)
    ws = wb['Strateji Listesi']
    out = []
    for r, row in enumerate(ws.iter_rows(values_only=True), 1):
        if r == 1 or not row[0]:
            continue
        out.append((r, row))
    return out


XLSX = {}
for kid, yol in (('P006', 'arsiv/sg-arge-/strateji_listesi.xlsx'), ('P007', 'arsiv/sg-arge-/strateji_listesi (2).xlsx')):
    XLSX[kid] = xlsx_satirlari(yol, kid)
xlsx_ham = []
xlsx_eslesmeyen = []
for kid, rows_ in XLSX.items():
    for r, row in rows_:
        lid = row[0]
        p = lid2p001.get(lid)
        s = bos(ham_id=f'{kid}:Strateji Listesi!{r}', kaynak_id=kid, kaynak_satir_no=f'Strateji Listesi!{r}', kaynaktaki_ad=str(row[1])[:120])
        if p is None:
            xlsx_eslesmeyen.append((kid, r, lid))
            s.update(eslesme='YOK', on_durum='BELIRSIZ', neden_metni=f'liste_id {lid} repo_kodlari.csv\'de yok', not_='')
            s['not'] = f'liste_id={lid}'
            xlsx_ham.append(s)
            continue
        ps = P001[p]
        s.update(kisa_mantik=ps['kisa_mantik'], aile=ps['aile'], eslesme='TEKRAR', hedef=f'P001:{p}', on_durum='TEKRAR', neden_kodu='kopya',
                 neden_metni=f'aynı liste kaydı ({lid}); repo_kodlari.csv liste_xlsx satırı P001:{p}',
                 kanit=f'{RK}:{p} (liste_id={lid})')
        s['not'] = f'liste_id={lid}; ad_eslesti={norm(str(row[1])) == norm(rk[p-1]["ad"])}'
        xlsx_ham.append(s)

# ---------------------------------------------------------------- md satırları (P008 day_trade..., P009 dpay_trade...)
p001_line = {}
p001_url = {}
for i, x in enumerate(rk, 1):
    m = re.search(r'liste_md=\S+?\.md:(\d+)', x['ayar_durumu'])
    if m:
        p001_line[int(m.group(1))] = i
    u = url_of(x)
    if u:
        p001_url.setdefault(u, []).append(i)


def md_satirlari(yol):
    out = []
    for n, l in enumerate(open(K / yol, encoding='utf-8'), 1):
        if not l.startswith('|'):
            continue
        cells = [c.strip() for c in l.strip().strip('|').split('|')]
        for c in cells[:2]:
            m = re.match(r'\[(.+?)\]\((https?://[^)]+)\)', c)
            if m:
                out.append((n, m.group(1), m.group(2), ' | '.join(cells[1:])))
                break
    return out


MD1 = md_satirlari('arsiv/sg-arge-/day_trade_swing_trade_strateji_listesi.md')
MD2 = md_satirlari('arsiv/sg-arge-/dpay_trade_swing_trade_strateji_listesi.md')
MD_OZEL = {
    82: dict(eslesme='BENZER', hedef=None, fark='Quadrant 2.0 = aynı sayfadaki Quadrant mantığı + HULL trend filtresi + 29 bar zaman çıkışı (topluluk varyantı); P001:362 heuristik (anahtar kelime) eşlemesi olan daytrade__donchian-kirilim ile kural karşılaştırması yapılmadı'),
    103: dict(eslesme='BENZER', hedef='dis__ibs-donus', fark='kaynak: 10 günlük zirve - 2,5x 25 günlük ort. aralık bandının altı VE IBS<0,3 -> al, önceki gün zirvesi üstü sat; dis__ibs-donus: IBS<alt(0,2) al / IBS>ust(0,8) çık, opsiyonel SMA filtresi, band koşulu yok (P002:21 R2 satırı da aynı aileyi gösteriyor)'),
    104: dict(eslesme='BENZER', hedef='dis__hafta-ici-takvim', fark='kaynak: Cuma VE pazartesi art arda düşüşte pazartesi kapanışı al, önceki gün zirvesi üstü çık; sınıf pzt_sali modu: pazartesi kapanışı<cuma kapanışı ve IBS<0,5 (ayrı çıkış kuralı, "Cuma da düştü" koşulu yok)'),
    105: dict(eslesme='BENZER', hedef='dis__min10-dip', fark='kaynak: kapanış önceki 5 günün en düşüğünün altında -> al, önceki gün zirvesi üstü çık; dis__min10-dip: kapanış <= son pencere(10) kapanışın en düşüğü -> al, 1 mum zaman çıkışı (çıkış kuralı farklı, pencere 5 vs 10)'),
}
md1_ham = {}
for n, ad, url, ozet in MD1:
    s = bos(ham_id=f'P008:L{n}', kaynak_id='P008', kaynak_satir_no=f'L{n}', kaynaktaki_ad=ad[:120], kisa_mantik=re.sub(r'\*\*', '', ozet)[:160],
            aile=aile_metin(ad + ' ' + ozet))
    s['not'] = f'md tablo satırı; url={url}'
    p = p001_line.get(n)
    if n in MD_OZEL:
        o = MD_OZEL[n]
        h = o['hedef'] or P001[p001_url[url][0]]['hedef']
        s.update(eslesme='BENZER', hedef=h, on_durum=D, neden_kodu='benzer_var', fark=o['fark'],
                 neden_metni='repo_kodlari.csv bu md satırını ayrı satır yapmamış (aynı URL\'li satıra katmış); ayrı kural olduğu için ayrıca değerlendirildi',
                 kanit=f'{kanit_sinif(h)}')
        ELLE.append((s['ham_id'], f'BENZER {h}', 'repo_kodlari bu md satırını ayrı satır yapmamış; kural özeti md\'den okunarak ilgili sınıfla kıyaslandı'))
        if h == '':
            s.update(eslesme='YOK', on_durum='BELIRSIZ')
    else:
        if p is None:
            c = p001_url.get(url, [])
            p = c[0] if c else None
            nt = 'repo_kodlari.csv bu md satırını ayrı satır yapmamış; aynı URL\'li satıra bağlandı'
        else:
            nt = 'repo_kodlari.csv liste_md satırı'
        if p is None:
            s.update(eslesme='YOK', on_durum='BELIRSIZ', neden_metni='repo_kodlari.csv\'de karşılığı bulunamadı')
        else:
            s.update(eslesme='TEKRAR', hedef=f'P001:{p}', on_durum='TEKRAR', neden_kodu='kopya',
                     neden_metni=nt, kanit=f'{RK}:{p}')
            if p001_line.get(n) is None:
                s['not'] += '; URL eşlemesi (ad farklı olabilir)'
                ELLE.append((s['ham_id'], f'TEKRAR P001:{p}', 'md satırı repo_kodlari\'da ayrı satır değil; aynı URL\'li P001 satırına bağlandı'))
    md1_ham[n] = s
md1_by_name = {norm(ad): n for n, ad, u, o in MD1}
md1_by_url = collections.defaultdict(list)
for n, ad, u, o in MD1:
    md1_by_url[u].append(n)
md2_ham = []
for n, ad, url, ozet in MD2:
    s = bos(ham_id=f'P009:L{n}', kaynak_id='P009', kaynak_satir_no=f'L{n}', kaynaktaki_ad=ad[:120], kisa_mantik=re.sub(r'\*\*', '', ozet)[:160],
            aile=aile_metin(ad + ' ' + ozet))
    s['not'] = f'md tablo satırı; url={url}'
    t = md1_by_name.get(norm(ad))
    if t is None and len(md1_by_url.get(url, [])) == 1:
        t = md1_by_url[url][0]
        s['not'] += '; URL eşlemesi (ad farklı)'
    if t is None:
        s.update(eslesme='YOK', on_durum='BELIRSIZ', neden_metni='day_trade md\'de karşılığı yok')
    else:
        s.update(eslesme='TEKRAR', hedef=f'P008:L{t}', on_durum='TEKRAR', neden_kodu='kopya',
                 neden_metni='aynı strateji aynı URL (day_trade_..._listesi.md satır %d)' % t, kanit=f'arsiv/sg-arge-/day_trade_swing_trade_strateji_listesi.md:{t}')
    md2_ham.append(s)
