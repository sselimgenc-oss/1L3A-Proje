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

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'dene':
    for nm, P in (('P001', P001), ('P002', P002)):
        c = collections.Counter((s['on_durum'], s['eslesme']) for s in P.values())
        print(nm, sum(c.values()))
        for k, v in sorted(c.items()): print('  ', k, v)
