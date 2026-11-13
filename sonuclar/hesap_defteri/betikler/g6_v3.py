#!/usr/bin/env python3
"""G6_V3 hesap defteri: v3 aday araştırması ham kataloglarının her satırı için ham satır üretir.

Girdi (salt okunur): stratejiler/v3_adaylar/*, sonuclar/hesap_defteri/{kaynaklar.csv,ara/kod_kaydi.csv},
stratejiler/dis_envanter.csv, sonuclar/v3/eleme.csv, DURUM.md.
Çıktı: sonuclar/hesap_defteri/ara/G6_V3_ham.csv (+ G6_V3_ozet.json, NOTLAR'ı elle yazılır).
Elle kararlar: sonuclar/hesap_defteri/ara/G6_V3_elle_kararlar.csv (ham_id -> alan üzerine yazma).
Çalıştırma: python3 sonuclar/hesap_defteri/betikler/g6_v3.py
"""
import csv, json, os, re, sys, collections, ast

KOK = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SD = os.path.join(KOK, 'stratejiler', 'v3_adaylar')
ARA = os.path.join(KOK, 'sonuclar', 'hesap_defteri', 'ara')
REL_SD = 'stratejiler/v3_adaylar/'

# dal ek katalogları (birleşmemiş dalın salt okunur kopyası)
DAL_KOK = '/tmp/claude-0/-home-user-1L3A-Proje/bee1199a-0b5d-5964-8f7d-e654dea778f9/scratchpad/ref_haiku_arastirma/stratejiler/ek_kaynaklar/'
DAL_ON = 'dal:claude/haiku-strateji-arastirma:stratejiler/ek_kaynaklar/'
DAL_DOSYALAR = [('V901', 'bolgesel_son3yil_2026-11.csv'), ('V902', 'cjk_son3yil_2026-11.csv'), ('V903', 'uzakdogu_son3yil_2026-11.csv')]

SUTUNLAR = ['ham_id', 'kaynak_id', 'kaynak_satir_no', 'kaynaktaki_ad', 'kisa_mantik', 'aile', 'eslesme', 'hedef', 'ayar_id',
            'ayar_dosyasi', 'fark', 'on_durum', 'neden_kodu', 'neden_metni', 'kanit', 'not']


def oku(yol):
    with open(yol, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def oku_satir_no(yol):
    """DictReader satırları + her satırın fiziksel başlangıç satır numarası."""
    out = []
    with open(yol, encoding='utf-8', newline='') as f:
        rd = csv.reader(f)
        baslik = next(rd)
        for rec in rd:
            ln = rd.line_num
            # line_num kaydın SON satırıdır; çok satırlı alan için başlangıcı bulmak üzere satır sayısı çıkarılır
            n_nl = sum(c.count('\n') for c in rec)
            d = dict(zip(baslik, rec))
            out.append((d, ln - n_nl))
    return out


def kisalt(s, n):
    s = re.sub(r'\s+', ' ', (s or '').strip())
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


_TR = str.maketrans('ğıİşöüçâî', 'giisoucai')


def nrm(s):
    return re.sub(r'\W+', '', (s or '').lower().translate(_TR))


def taban_ad(s):
    """parantez / iki nokta öncesi ad gövdesi (normalize)"""
    s = re.split(r'\s\(|:', s or '')[0]
    return nrm(s)


# --------------------------------------------------------------------------------------
# kaynak id'leri
# --------------------------------------------------------------------------------------
kaynaklar = oku(os.path.join(KOK, 'sonuclar/hesap_defteri/kaynaklar.csv'))
KID = {}
for r in kaynaklar:
    if r['grup'] == 'G6_V3' and r['tur'] == 'birincil:v3_ham_katalog':
        KID[os.path.basename(r['yol'])] = r['kaynak_id']

AD_SUTUN = {  # katalogdaki kimlik sütunu (kaynaktaki_ad)
    'MASTER_katalog_2026-11.csv': 'ad',
    'asya-siteleri-katalog__b_duzeyi.csv': 'strateji', 'asya-siteleri-katalog__tumu.csv': 'strateji',
    'bolgesel-katalog__b_duzeyi.csv': 'strateji', 'bolgesel-katalog__tumu.csv': 'strateji',
    'chatgpt_dr_tur1_gunici_kripto.csv': 'ad', 'chatgpt_dr_tur2_funding.csv': 'ad', 'chatgpt_dr_tur3_akademik_kismi.csv': 'ad',
    'diger-siteler-derin-21.csv': None,
    'gemini_dr_6bolge.csv': 'ad', 'gemini_dr_afrika.csv': 'ad',
    'github-backtest-katalog-denetimli__dogrulanan_48.csv': 'repo', 'github-backtest-katalog-denetimli__gercek_ek.csv': 'repo',
    'github-backtest-katalog-denetimli__tumu.csv': 'repo',
    'github-backtest-katalog-v4__diger_siteler.csv': 'strateji', 'github-backtest-katalog-v4__reddit.csv': 'strateji',
    'github-backtest-katalog-v4__sayfa_dogrulamasi.csv': 'repo',
}
URL_SUTUN = {
    'MASTER_katalog_2026-11.csv': None, 'asya-siteleri-katalog__b_duzeyi.csv': 'URL', 'asya-siteleri-katalog__tumu.csv': 'URL',
    'bolgesel-katalog__b_duzeyi.csv': 'URL', 'bolgesel-katalog__tumu.csv': 'URL',
    'chatgpt_dr_tur1_gunici_kripto.csv': 'kaynak_url', 'chatgpt_dr_tur2_funding.csv': 'kaynak_url',
    'chatgpt_dr_tur3_akademik_kismi.csv': 'kaynak_url', 'diger-siteler-derin-21.csv': 'URL',
    'gemini_dr_6bolge.csv': 'kod_linki', 'gemini_dr_afrika.csv': 'kod_linki',
    'github-backtest-katalog-denetimli__dogrulanan_48.csv': 'url', 'github-backtest-katalog-denetimli__gercek_ek.csv': 'url',
    'github-backtest-katalog-denetimli__tumu.csv': 'url', 'github-backtest-katalog-v4__diger_siteler.csv': 'URL',
    'github-backtest-katalog-v4__reddit.csv': 'URL', 'github-backtest-katalog-v4__sayfa_dogrulamasi.csv': 'url',
}


def mantik_kolonlari(dosya, row):
    if dosya.startswith('MASTER'):
        return row.get('kural_ozeti') or row.get('sonuc_ozeti') or row.get('durum') or ''
    if dosya.startswith(('asya', 'bolgesel')):
        return f"{row.get('strateji','')} | {row.get('piyasa','')}"
    if dosya.startswith('chatgpt'):
        return f"long: {row.get('long_giris','')} | short: {row.get('short_giris','')}"
    if dosya.startswith('gemini'):
        return f"{row.get('giris_kurali_kisa','')} | çıkış: {row.get('cikis_ve_stop_kisa','')}"
    if dosya.startswith('diger-siteler'):
        return row.get('kurallar', '')
    if dosya.endswith('reddit.csv') or dosya.endswith('diger_siteler.csv'):
        return f"{row.get('strateji','')} | {row.get('piyasa','')}"
    return f"{row.get('strateji','')} | {row.get('piyasa','')}"


# --------------------------------------------------------------------------------------
# karar zinciri dosyaları
# --------------------------------------------------------------------------------------
oe_rows = oku_satir_no(os.path.join(SD, 'on_eleme.csv'))
T2 = {(d['kaynak_dosya'], d['satir_no']): (d, ln) for d, ln in oku_satir_no(os.path.join(SD, 'on_eleme_tur2_kod_yok.csv'))}
T3 = {(d['kaynak_dosya'], d['satir_no']): (d, ln) for d, ln in oku_satir_no(os.path.join(SD, 'on_eleme_tur3.csv'))}
G2 = {(d['kaynak_dosya'], d['satir_no']): (d, ln) for d, ln in oku_satir_no(os.path.join(SD, 'on_eleme_tur3_gorev2.csv'))}
V6 = {(d['kaynak_dosya'], d['satir_no_veya_kart_id']): (d, ln) for d, ln in oku_satir_no(os.path.join(SD, 'veri_yok_etiket_tur6.csv'))}
ADAY = {d['kart_id']: (d, ln) for d, ln in oku_satir_no(os.path.join(SD, 'adaylar.csv'))}
AILE = {d['kart_id']: (d, ln) for d, ln in oku_satir_no(os.path.join(SD, 'aileler_v3.csv'))}
FABLE = {d['kart_id']: (d, ln) for d, ln in oku_satir_no(os.path.join(SD, 'fable_hakem.csv'))}
KODLAMA = {d['kart_id']: (d, ln) for d, ln in oku_satir_no(os.path.join(SD, 'kodlama_v3.csv'))}
TUR8 = collections.defaultdict(list)
for d, ln in oku_satir_no(os.path.join(SD, 'kod_kontrol_tur8.csv')):
    TUR8[d['kart_id']].append((d, ln))
ELEME = {r['kart']: r for r in oku(os.path.join(KOK, 'sonuclar/v3/eleme.csv'))}  # kart (kısa id) -> koşu
KOD = {r['ad']: r for r in oku(os.path.join(ARA, 'kod_kaydi.csv'))}
DIS_ENV = oku(os.path.join(KOK, 'stratejiler/dis_envanter.csv'))

# kart JSON'ları
KART = {}
for fn in os.listdir(os.path.join(SD, 'kartlar')):
    if fn.endswith('.json'):
        with open(os.path.join(SD, 'kartlar', fn), encoding='utf-8') as f:
            KART[fn[:-5]] = json.load(f)

# reddedilenler
RED = []  # (dosya, satir_no, ad, url, neden)
for fn in ['REDDEDILENLER.txt', 'REDDEDILENLER_tur2.txt', 'REDDEDILENLER_tur3.txt']:
    with open(os.path.join(SD, fn), encoding='utf-8') as f:
        for i, ln in enumerate(f, 1):
            ln = ln.rstrip('\n')
            if '|' not in ln:
                continue
            p = [x.strip() for x in ln.split('|')]
            if len(p) >= 3:
                RED.append((fn, i, p[0], p[1], ' | '.join(p[2:])))
            else:
                RED.append((fn, i, p[0], '', p[1]))


def nurl(u):
    u = (u or '').strip().lower()
    u = re.sub(r'^https?://(www\.)?', '', u)
    u = re.sub(r'\.git$', '', u).rstrip('/')
    return u


def repo_of(u):
    m = re.match(r'github\.com/([^/]+/[^/#?]+)', nurl(u))
    return m.group(1) if m else None


# --------------------------------------------------------------------------------------
# elle kararlar
# --------------------------------------------------------------------------------------
ELLE = {}
elle_yol = os.path.join(ARA, 'G6_V3_elle_kararlar.csv')
if os.path.exists(elle_yol):
    for r in oku(elle_yol):
        ELLE[r['ham_id']] = r

# --------------------------------------------------------------------------------------
# 1) taban satırlar (on_eleme sırası) + katalog hizası
# --------------------------------------------------------------------------------------
katalog = {}
for fn in KID:
    with open(os.path.join(SD, 'ham', fn), encoding='utf-8', newline='') as f:
        katalog[fn] = list(csv.DictReader(f))

taban = []   # dict listesi
uyari_hiza = []
for d, ln in oe_rows:
    fn = d['kaynak_dosya']
    s = int(d['satir_no'])
    veri_no = s if fn.startswith('gemini') else s - 1   # gemini: 1'den başlayan veri sırası; diğerleri başlık dahil satır no
    d2 = dict(d)
    d2['_oe_ln'] = ln
    d2['_veri_no'] = veri_no
    d2['_hiza'] = 'dogrudan'
    taban.append(d2)

# reddit kayması: oe satırının URL'si katalog satırıyla uyuşmuyorsa URL'ye göre yeniden hizala
for d in taban:
    fn = d['kaynak_dosya']
    uc = URL_SUTUN.get(fn)
    if not uc:
        continue
    kat = katalog[fn]
    row = kat[d['_veri_no'] - 1]
    cu, ou = nurl(row[uc]), nurl(d['url'])
    if not ou or cu == ou or cu.startswith(ou[:40]) or ou.startswith(cu[:40]):
        continue
    adaylar_ = [i for i, r in enumerate(kat, 1) if nurl(r[uc]) == ou]
    if len(adaylar_) == 1:
        uyari_hiza.append((fn, d['satir_no'], d['_veri_no'], adaylar_[0]))
        d['_veri_no'] = adaylar_[0]
        d['_hiza'] = 'url_ile_duzeltildi'

# --------------------------------------------------------------------------------------
# 2) zincir: oe -> tur2 -> tur3 -> gorev2
# --------------------------------------------------------------------------------------
for d in taban:
    k = (d['kaynak_dosya'], d['satir_no'])
    zincir = [('oe', d['karar'], d['_oe_ln'], d)]
    son = d
    for ad_, T in (('t2', T2), ('t3', T3), ('g2', G2)):
        if k in T:
            row, ln = T[k]
            zincir.append((ad_, row['karar'], ln, row))
            son = row
    d['_zincir'] = zincir
    d['_son'] = son
    d['_karar'] = son['karar']
    d['_neden'] = son['neden']
    d['_benzer'] = son.get('benzer_mevcut', '')

# --------------------------------------------------------------------------------------
# 3) kart eşleme (URL + ad), reddedilenler
# --------------------------------------------------------------------------------------
URL_KART = collections.defaultdict(list)
for kid, (a, ln) in ADAY.items():
    URL_KART[nurl(a['kaynak_url'])].append(kid)

KOD_ALIAS = {}   # kart_id -> strateji_ad (kodlama_v3 + eleme.csv)
for kid, (r, ln) in KODLAMA.items():
    KOD_ALIAS[kid] = r['strateji_ad']


def kart_secim(d, adaylar_):
    if len(adaylar_) == 1:
        return adaylar_[0]
    a = nrm(d['ad'])
    best, bs = None, -1
    for kid in adaylar_:
        sc = len(set(re.findall(r'[a-z0-9]{4,}', (KART[kid].get('ad', '') + ' ' + kid).lower())) &
                 set(re.findall(r'[a-z0-9]{4,}', (d['ad'] + ' ' + d['url']).lower())))
        if sc > bs:
            best, bs = kid, sc
    return best


# MASTER (URL'siz) satırlar için elle eşleme (ad karşılaştırması, kart json'larına bakıldı)
MASTER_KART_ELLE = {
    '2': 'swing__12ay-dongu-kesit__heston',
    '9': 'swing__bab-ulke-endeks__frazzini',
    '14': 'swing__petrol-hisse-zamanlama__driesprong',
    '27': 'swing__fomc-oncesi-gun__tori',
    '34': 'swing__dusuk-volatilite-desil__blitz',
    '49': 'swing__opsiyon-vade-haftasi__stivers',
    '50': 'swing__eslesmis-gecis-hisse-tahvil__maewal',
    '53': 'swing__payday-ayin-16si__ma-pratt',
    '55': 'swing__tatil-oncesi-gun__hansen',
    '56': 'swing__ramazan-mevsimsel__bialkowski',
    '68': 'swing__kisa-vade-tersine-donus__groot',
    '70': 'swing__carpiklik-emtia__dujava',
    '84': 'swing__stocks-on-the-move__clenow',
    '136': 'swing__pre-fomc-surunme__delphic',
}

for d in taban:
    d['_kart'] = None
    d['_kart_yontem'] = ''
    d['_red'] = None
    if d['_karar'] != 'kart':
        continue
    fn = d['kaynak_dosya']
    if fn.startswith('MASTER') and d['satir_no'] in MASTER_KART_ELLE:
        d['_kart'] = MASTER_KART_ELLE[d['satir_no']]
        d['_kart_yontem'] = 'ad (MASTER, URL yok)'
        continue
    u = nurl(d['url'])
    if u and u in URL_KART:
        d['_kart'] = kart_secim(d, URL_KART[u])
        d['_kart_yontem'] = 'url'
        continue
    # repo düzeyi
    r_ = repo_of(d['url'])
    if r_:
        cand = [kid for kid, (a, ln) in ADAY.items() if repo_of(a['kaynak_url']) == r_]
        if cand:
            d['_kart'] = kart_secim(d, cand)
            d['_kart_yontem'] = 'repo'
            continue
    # reddedilenler
    for (fn_, i, rad, rurl, rneden) in RED:
        a1, b1 = taban_ad(rad), taban_ad(d['ad'])
        if (u and nurl(rurl) == u) or (len(a1) >= 8 and len(b1) >= 8 and (a1 == b1 or a1.startswith(b1) or b1.startswith(a1))):
            d['_red'] = (fn_, i, rad, rneden)
            break

# birincil ham satır (kart başına ilk satır)
KART_BIRINCIL = {}
for d in taban:
    if d['_kart'] and d['_kart'] not in KART_BIRINCIL:
        KART_BIRINCIL[d['_kart']] = (d['kaynak_dosya'], d['satir_no'])


def ham_id_of(fn, satir_no):
    for d in taban:
        if d['kaynak_dosya'] == fn and d['satir_no'] == satir_no:
            return hid(d)
    return None


def hid(d):
    return f"{KID[d['kaynak_dosya']]}:{d['_veri_no']}"


HID_BY_KEY = {(d['kaynak_dosya'], d['satir_no']): hid(d) for d in taban}

# --------------------------------------------------------------------------------------
# 4) sınıf bilgisi (hedef sınıfı açma)
# --------------------------------------------------------------------------------------
_SINIF_CACHE = {}


def sinif_ozet(ad):
    """kod_kaydi satırından sınıfın dosya:satır + docstring ilk cümlesi (kodu açıp okur)."""
    if ad in _SINIF_CACHE:
        return _SINIF_CACHE[ad]
    r = KOD.get(ad)
    if not r:
        _SINIF_CACHE[ad] = ''
        return ''
    yol = os.path.join(KOK, r['dosya'])
    doc = ''
    try:
        with open(yol, encoding='utf-8') as f:
            src = f.read()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == r['sinif']:
                doc = ast.get_docstring(node) or ''
                break
    except Exception as e:  # noqa
        doc = ''
    doc = re.sub(r'\s+', ' ', doc).strip()
    s = f"{r['dosya']}:{r['satir']} sınıf {r['sinif']}"
    if doc:
        s += ' docstring: ' + kisalt(doc, 150)
    _SINIF_CACHE[ad] = s
    return s


PREFIXES = ['', 'swing__', 'daytrade__', 'scalp__', 'dis__', 'pf__', 'v2__']
DIS_ENV_BY_AD = collections.defaultdict(list)
for r in DIS_ENV:
    DIS_ENV_BY_AD[r['ad'].strip().lower()].append(r)


def temiz_token(t):
    t = t.strip()
    t = re.sub(r'\s*\((?:kartlar|havuz_v2|dis_envanter[^)]*|havuz_v2\))\s*$', '', t)
    t = re.sub(r'^(dis_envanter(\.csv)?:?\s*|havuz:\s*|tv:?\s*|kural:\s*|dis_e\s+)', '', t, flags=re.I)
    t = re.sub(r'\.json$', '', t)
    t = re.sub(r'\s*\(.*?\)\s*$', '', t) if t not in KOD else t
    return t.strip()


def coz_token(tok):
    """token -> ('kod', ad) | ('kart', kid) | ('satir', n) | None"""
    ham = tok.strip()
    if not ham or ham.lower() == 'yok':
        return None
    m = re.match(r"^(?:.*?\.csv\s+)?satir\s+'?(\d+)'?", ham, re.I)
    if m and ham.lower().startswith('satir'):
        return ('satir', m.group(1))
    if ham in KOD:
        return ('kod', ham)
    for kid in KART:
        if ham == kid or ham == kid + '.json' or ham.startswith(kid):
            return ('kart', kid)
    t = temiz_token(ham)
    if t in KART:
        return ('kart', t)
    if t in KOD:
        return ('kod', t)
    for p in PREFIXES:
        if p + t in KOD:
            return ('kod', p + t)
    # prefix eşleşmesi (swing__ma-kes -> swing__ma-kesisim) yalnız tek aday varsa
    cand = [k for k in KOD if k.endswith('__' + t) or k.startswith(t) or any(k.startswith(p + t) for p in PREFIXES[1:])]
    if len(cand) == 1:
        return ('kod', cand[0])
    # dis_envanter ad araması
    tl = t.lower()
    hits = DIS_ENV_BY_AD.get(tl) or [r for ad_, rs in DIS_ENV_BY_AD.items() if len(tl) > 6 and (tl in ad_ or ad_ in tl) for r in rs]
    if hits:
        for h in hits:
            a = h['benzer_1l3a_aile'].strip()
            if a in KOD:
                return ('kod', a)
            for p in PREFIXES[1:]:
                if p + a in KOD:
                    return ('kod', p + a)
    return None


def kart_kodu(kid):
    """kart_id -> (strateji_ad | None, durum)"""
    if kid in KODLAMA:
        r, ln = KODLAMA[kid]
        return r['strateji_ad'], r['durum']
    return None, 'kodlama_yok'


# --------------------------------------------------------------------------------------
# 5) sınıflandırma
# --------------------------------------------------------------------------------------
ML_RE = re.compile(r"\bML\b|makine öğren|machine learn|LSTM|XGBoost|xlstm|random forest|rastgele orman|neural|sinir ağ|derin öğren|deep learn|reinforcement|pekiştirmeli|\bRL\b|\bPPO\b|\bLLM\b|\bGPT|yapay zek|\bAI\b|Q-learning|transformer|\bSVM\b|LightGBM|gradient boost|k-means|kümeleme|model tahmin|tahmin model|meta-etiket|ajan.*LLM|\bGARCH-ML", re.I)
KAL_RE = [(re.compile(r'martingale', re.I), 'martingale'), (re.compile(r'\bDCA\b|dolar maliyet', re.I), 'dca'),
          (re.compile(r'ortalama düşür|ortalama dusur|kademeli alım|averaging down|zararda ekle', re.I), 'ortalama_dusurme'),
          (re.compile(r'grid|ızgara|izgara', re.I), 'stopsuz_grid'),
          (re.compile(r'lookahead|look-ahead|geleceğe bak|gelecegi gor|geleceği gör|repaint|yeniden çiz|shift\(-', re.I), 'lookahead')]


def yasak_tur(neden, ad):
    metin = neden + ' ' + ad
    if ML_RE.search(metin):
        return 'G', 'ml'
    for rx, kod in KAL_RE:
        if rx.search(metin):
            return 'F', kod
    return 'F', 'yasak_diger'


AILE_TREND = re.compile(r'trend|kırılım|kirilim|breakout|momentum|donchian|supertrend|ma kesişim|ma kesisim|crossover|kesişim|kesisim|turtle|orb|opening range|açılış aralığı|rotasyon|rotation|golden|macd|adx|ichimoku|killzone|izleyen|hareketli ortalama|ema\b|sma\b|动量|趋势|突破|均线', re.I)
AILE_MR = re.compile(r'mean.?reversion|ortalamaya dön|ortalama dön|reversal|ters dön|tersine|aşırı (alım|satım)|asiri (alim|satim)|bollinger|rsi|z-?skor|z-?score|pairs|çift|cift|stat.?arb|spread|oversold|dip|fade|geri çekil|pullback|均值回归|回归|reversion|stokastik|stochastic|kontrarian|contrarian', re.I)


def aile_belirle(d, mantik):
    if d['_kart'] and d['_kart'] in KART:
        k = KART[d['_kart']].get('kategori', '') or ''
        if 'ortalamaya' in k or 'donus' in k:
            return 'MR'
        if k in ('trend', 'kirilim', 'momentum', 'rejim') or 'trend' in k or 'kirilim' in k or 'momentum' in k:
            return 'trend'
        return 'diger'
    metin = d['ad'] + ' ' + mantik
    mr, tr = bool(AILE_MR.search(metin)), bool(AILE_TREND.search(metin))
    if mr and not tr:
        return 'MR'
    if tr and not mr:
        return 'trend'
    if mr and tr:
        return 'MR' if AILE_MR.search(d['ad']) else 'trend'
    return 'diger'


KURAL_ACIK_POS = re.compile(r"(kural(lar)?(ı|ları)?\s*(\([^)]*\))?\s*(net|açık|acik|ayrıntılı|ayrintili|ölçülebilir|olculebilir|okunabilir|yazıyla|yaziyla|README'de|var\b|mevcut|tanımlı|belirli))|(giriş[^.;]{0,40}(koşul|kural|eşik)[^.;]{0,30}\bvar\b)|(kuralı?\s*(okundu|çıkarıldı|yazılı))|(ama kod yok)|(kod yok[,;]? ?ama)|(kural[^.;]{0,20}(var|net)[^.;]{0,20}kod[^.;]{0,15}(yok|ekran|bulunamad))", re.I)
KURAL_ACIK_NEG = re.compile(r"kural(ı|lar|ları)?\s*(yok|belirsiz|tanımsız|yayınlanmamış|gizli|eksik|okunamad|görünmüyor|açık değil|net değil)|(giriş|çıkış|sinyal)[^.;]{0,25}(yok|tanımsız|belirsiz)|kural ve kod yok|kural yok|kuralı yok|tescilli", re.I)


def kural_acik_mi(neden):
    if KURAL_ACIK_NEG.search(neden):
        return False
    return bool(KURAL_ACIK_POS.search(neden))


EVREN_NEDEN = [(re.compile(r'opsiyon|option', re.I), 'opsiyon'), (re.compile(r'order ?book|emir defteri|orderbook|tick|HFT|L2', re.I), 'orderbook'),
               (re.compile(r'pairs|çift|cift|kointegrasyon|stat.?arb', re.I), 'pairs'),
               (re.compile(r'hisse|stock|ETF|endeks|index', re.I), 'hisse_kesitsel'),
               (re.compile(r'DeFi|LP |likidite havuzu|AMM', re.I), 'defi')]

GEREKEN_NEDEN = {'opsiyon': 'opsiyon', 'emir_defteri': 'orderbook', 'hisse_fiyat': 'hisse_kesitsel', 'hisse_temel': 'hisse_kesitsel',
                 'endeks': 'hisse_kesitsel', 'haber_duygu': 'haber_duygu', 'alt_1dk': 'alt_1dk', 'forex': 'forex_veri',
                 'vadeli_emtia': 'vadeli_emtia', 'onchain': 'onchain', 'makro_takvim': 'makro_takvim', 'diger': 'veri_diger'}

SATIR_REF = re.compile(r"satir\s+'?(\d+)'?", re.I)


def src_kanit(d, adimlar=None):
    """zincir adımlarının dosya:satır kanıtları"""
    ad_dosya = {'oe': 'on_eleme.csv', 't2': 'on_eleme_tur2_kod_yok.csv', 't3': 'on_eleme_tur3.csv', 'g2': 'on_eleme_tur3_gorev2.csv'}
    out = []
    for ad_, karar, ln, row in d['_zincir']:
        out.append(f"{REL_SD}{ad_dosya[ad_]}:{ln}")
    return ' ; '.join(out)


def sonuc(d, **kw):
    return kw


DURUM_KANIT = 'DURUM.md:433'   # "Test bütçesi: yalnız 10 aile temsilcisi" (2026-11-11 v3 araştırma kararları)
DURUM_VERI = 'DURUM.md:434'    # "Tur 6: veri_yok 514 ..."

# DURUM.md satır numaralarını doğrula
with open(os.path.join(KOK, 'DURUM.md'), encoding='utf-8') as f:
    _dm = f.read().split('\n')
assert 'Test bütçesi: yalnız 10 aile temsilcisi' in _dm[432], 'DURUM.md satırı kaymış'
assert 'Tur 6: veri_yok 514' in _dm[433], 'DURUM.md satırı kaymış'

TEKRAR_AYNI = re.compile(r'birebir|aynı repo|aynı kaynak|aynı kural|aynı yazı|aynı strateji|aynı kod|kopya|fork|aynı harness|aynı depo|aynı aday', re.I)


def tekrar_coz(d):
    """final karar tekrar -> (eslesme, hedef, fark, not, neden_kodu, ek_kanit, hedef_kart)"""
    benzer = d['_benzer']
    nd = d['_neden']
    parts = [p.strip() for p in benzer.split(';') if p.strip()]
    cozulen = []
    for p in parts:
        c = coz_token(p)
        if c:
            cozulen.append((p, c))
    # satir referansı
    for p, c in cozulen:
        if c[0] == 'satir':
            hedef_key = (d['kaynak_dosya'], str(int(c[1])))
            hh = HID_BY_KEY.get(hedef_key)
            if hh:
                return ('TEKRAR', hh, '', f"benzer_mevcut='{benzer}' (aynı katalogda satir {c[1]} = oe satır no)", 'kopya', '', None)
    # kod sınıfı
    for p, c in cozulen:
        if c[0] == 'kod':
            return ('BENZER', c[1], kisalt(nd, 200), f"benzer_mevcut='{kisalt(benzer, 90)}'", 'benzer_var', '', None)
    for p, c in cozulen:
        if c[0] == 'kart':
            kid = c[1]
            sa, du = kart_kodu(kid)
            if sa and sa in KOD:
                return ('BENZER', sa, kisalt(nd, 200), f"benzer_mevcut kart={kid} (kodlama_v3 durum={du})", 'benzer_var', f"{REL_SD}kodlama_v3.csv:{KODLAMA[kid][1]}", kid)
            return ('KARTBENZER', kid, kisalt(nd, 200), f"benzer_mevcut kart={kid} (kodlanmamış kart)", 'benzer_var', '', kid)
    return (None, '', '', f"benzer_mevcut çözülemedi: '{kisalt(benzer, 100)}'", '', '', None)


cikti = []
istat = collections.Counter()
kural_acik_liste = []
kart_isleme = collections.Counter()

for d in taban:
    fn = d['kaynak_dosya']
    kid_ = KID[fn]
    hid_ = hid(d)
    kat = katalog[fn][d['_veri_no'] - 1]
    ad_col = AD_SUTUN[fn]
    kaynaktaki_ad = kat[ad_col] if ad_col else d['ad']
    mantik = mantik_kolonlari(fn, kat)
    if not mantik.strip():
        mantik = d['ad']
    row = {c: '' for c in SUTUNLAR}
    row.update({'ham_id': hid_, 'kaynak_id': kid_, 'kaynak_satir_no': str(d['_veri_no']),
                'kaynaktaki_ad': kisalt(kaynaktaki_ad, 120), 'kisa_mantik': kisalt(mantik, 160)})
    row['aile'] = aile_belirle(d, mantik)
    kn = d['_karar']
    not_ = []
    if d['_hiza'] != 'dogrudan':
        not_.append(f"hiza düzeltildi: on_eleme satir_no={d['satir_no']} ama URL katalog satırı {d['_veri_no']}'ye ait")
    # ad uyumsuzluğu bayrağı (çeviri/kısaltma dışı)
    a_, b_ = nrm(d['ad']), nrm(kaynaktaki_ad)
    if ad_col and not (a_ == b_ or a_[:20] == b_[:20] or a_ in b_ or b_ in a_) and d['_hiza'] == 'dogrudan':
        not_.append(f"on_eleme adı '{kisalt(d['ad'], 50)}' katalog adından farklı (URL tutuyor)")
    zincir_kodu = '>'.join(f"{a}:{k}" for a, k, ln, r in d['_zincir'])
    not_.append('zincir ' + zincir_kodu)
    kanit = src_kanit(d)

    if kn == 'kart':
        kid = d['_kart']
        if kid:
            birincil = KART_BIRINCIL[kid]
            if (fn, d['satir_no']) != birincil:
                hh = HID_BY_KEY[birincil]
                row.update({'eslesme': 'TEKRAR', 'hedef': hh, 'on_durum': 'TEKRAR',
                            'neden_kodu': 'kopya',
                            'neden_metni': f"aynı kaynak/kart ({kid}); ilk ham satır {hh}",
                            'kanit': kanit + f" ; {REL_SD}adaylar.csv:{ADAY[kid][1]}"})
                not_.append(f"kart eşleme yöntemi: {d['_kart_yontem']}")
            else:
                sa, du = kart_kodu(kid)
                kanit_k = kanit + f" ; {REL_SD}adaylar.csv:{ADAY[kid][1]}"
                if kid in KODLAMA:
                    kanit_k += f" ; {REL_SD}kodlama_v3.csv:{KODLAMA[kid][1]}"
                row['not'] = ''
                if sa and du == 'kodlandi' and sa in KOD:
                    ek = ''
                    if kid.split('__', 1)[-1] in ELEME or any(k_ in ELEME for k_ in [kid.split('__', 1)[-1]]):
                        ek = f" ; sonuclar/v3/eleme.csv#{kid.split('__',1)[-1]}"
                    row.update({'eslesme': 'KOD', 'hedef': sa, 'on_durum': 'KOD', 'kanit': kanit_k + f" ; sonuclar/hesap_defteri/ara/kod_kaydi.csv#{sa}" + ek,
                                'neden_metni': f"kart {kid} kodlandı: {sa}"})
                    kart_isleme['KOD'] += 1
                elif sa and du == 'tekrar':
                    row.update({'eslesme': 'BENZER', 'hedef': sa if sa in KOD else '', 'on_durum': 'D_KODLANMADI_NEDENLI', 'neden_kodu': 'benzer_var',
                                'fark': kisalt((KODLAMA[kid][0]['not'] or '') + ' | varsayımlar: ' + (KODLAMA[kid][0]['varsayimlar'] or ''), 200) + (' | ' + sinif_ozet(sa) if sa in KOD else ''),
                                'neden_metni': f"kart {kid}: kodlama_v3 durum=tekrar (mevcut sınıf çekirdeği karşılıyor denmiş; fark satırı yazılı)",
                                'kanit': kanit_k})
                    kart_isleme['kodlama_tekrar'] += 1
                elif du in ('veri_yok', 'belirsiz', 'altyapi_yok'):
                    nk = {'veri_yok': 'veri_yok', 'belirsiz': 'kural_belirsiz', 'altyapi_yok': 'altyapi_yok'}[du]
                    row.update({'eslesme': 'YOK', 'on_durum': 'D_KODLANMADI_NEDENLI', 'neden_kodu': nk,
                                'neden_metni': kisalt(f"kart {kid}, kodlama_v3 durum={du}: {KODLAMA[kid][0]['not']}", 200), 'kanit': kanit_k})
                    kart_isleme['kodlama_' + du] += 1
                else:
                    a_r = AILE.get(kid)
                    fb = FABLE.get(kid)
                    if a_r and a_r[0]['aile_temsilcisi_mi'] == 'hayir':
                        row.update({'eslesme': 'YOK', 'on_durum': 'D_KODLANMADI_NEDENLI', 'neden_kodu': 'oncelik_disi',
                                    'neden_metni': f"aile temsilcisi değil, test bütçesi (aile={a_r[0]['aile']}; Fable puan {fb[0]['puan_0_10'] if fb else '?'}); kart {kid}",
                                    'kanit': kanit_k + f" ; {REL_SD}aileler_v3.csv:{a_r[1]}" + (f" ; {REL_SD}fable_hakem.csv:{fb[1]}" if fb else '') + f" ; {DURUM_KANIT}"})
                        kart_isleme['temsilci_degil'] += 1
                    else:
                        row.update({'eslesme': 'YOK', 'on_durum': 'E_KODLANMADI_NEDENSIZ', 'neden_kodu': '',
                                    'neden_metni': f"kart {kid} yazıldı; kodlama_v3'te yok ve aile temsilcisi kaydı yok/evet",
                                    'kanit': kanit_k})
                        kart_isleme['E'] += 1
                not_.append(f"kart={kid}; eşleme yöntemi: {d['_kart_yontem']}")
                if kid in KART:
                    vu = KART[kid].get('veri_uygun')
                    if isinstance(vu, list) and vu and vu[0] is False:
                        not_.append('kart veri_uygun=false')
        elif d['_red']:
            fn_, i, rad, rneden = d['_red']
            nk, ond = 'kart_reddedildi', 'D_KODLANMADI_NEDENLI'
            if ML_RE.search(rneden):
                nk, ond = 'ml', 'G_ML'
            elif re.search(r'okunamad|403|503|404|açılamad|acilamad|erişil', rneden, re.I):
                nk = 'kaynak_okunamadi'
            elif re.search(r'tekrar|aynı|benzer', rneden, re.I):
                nk = 'tekrar_kart_yok'
            row.update({'eslesme': 'YOK', 'on_durum': ond, 'neden_kodu': nk,
                        'neden_metni': kisalt(f"karar=kart ama kart yazılmadı: {rneden}", 200),
                        'kanit': kanit + f" ; {REL_SD}{fn_}:{i}"})
            kart_isleme['reddedildi'] += 1
        else:
            row.update({'eslesme': 'YOK', 'on_durum': 'E_KODLANMADI_NEDENSIZ',
                        'neden_metni': 'son karar=kart; ne kart (adaylar/kartlar) ne REDDEDILENLER kaydı bulundu (birleştirilmiş/atlanmış olabilir)',
                        'kanit': kanit})
            kart_isleme['E_kart_kaydi_yok'] += 1

    elif kn == 'kod_yok':
        ka = kural_acik_mi(d['_neden'])
        row.update({'eslesme': 'YOK', 'on_durum': 'D_KODLANMADI_NEDENLI', 'neden_kodu': 'kod_yok',
                    'neden_metni': kisalt('kaynakta açık kod yok: ' + d['_neden'], 220), 'kanit': kanit})
        if ka:
            not_.append('KURAL_ACIK_ADAY')
            kural_acik_liste.append(hid_)

    elif kn == 'veri_yok':
        v6 = V6.get((fn, d['satir_no']))
        if v6:
            vd, vln = v6
            gv = vd['gereken_veri']
            kn_ = GEREKEN_NEDEN.get(gv, 'veri_diger')
            if vd['bizde_islenebilir'] == 'hayir':
                row.update({'eslesme': 'YOK', 'on_durum': 'H_BIZIM_EVRENDE_UYGULANAMAZ', 'neden_kodu': kn_,
                            'neden_metni': kisalt(f"gereken veri={gv} ({vd['veri_ayrinti']}); bizde işlenebilir=hayir: {vd['not']}", 220),
                            'kanit': kanit + f" ; {REL_SD}veri_yok_etiket_tur6.csv:{vln} ; {DURUM_VERI}"})
            else:
                row.update({'eslesme': 'YOK', 'on_durum': 'D_KODLANMADI_NEDENLI', 'neden_kodu': 'veri_yok',
                            'neden_metni': kisalt(f"gereken veri={gv} ({vd['veri_ayrinti']}); bizde işlenebilir={vd['bizde_islenebilir']}: {vd['not']}", 220),
                            'kanit': kanit + f" ; {REL_SD}veri_yok_etiket_tur6.csv:{vln} ; {DURUM_VERI}"})
            not_.append(f"tur6 etiketi: {gv}/{vd['bizde_islenebilir']}/ucretsiz={vd['ucretsiz_kaynak']}")
        else:
            row.update({'eslesme': 'YOK', 'on_durum': 'D_KODLANMADI_NEDENLI', 'neden_kodu': 'veri_yok',
                        'neden_metni': kisalt('veri yok (tur6 etiketinde satır yok): ' + d['_neden'], 220), 'kanit': kanit})
            not_.append('tur6 etiketinde yok')

    elif kn == 'yasak':
        grp, nk = yasak_tur(d['_neden'], d['ad'])
        row.update({'eslesme': 'YOK', 'on_durum': 'G_ML' if grp == 'G' else 'F_YASAK_TIP', 'neden_kodu': nk,
                    'neden_metni': kisalt(d['_neden'], 220), 'kanit': kanit})
        if grp == 'F' and nk == 'yasak_diger':
            not_.append('yasak alt türü metinden otomatik çıkarılamadı')

    elif kn == 'arac':
        row.update({'eslesme': 'YOK', 'on_durum': 'D_KODLANMADI_NEDENLI', 'neden_kodu': 'arac_sablon',
                    'neden_metni': kisalt(d['_neden'], 220), 'kanit': kanit})

    elif kn == 'tekrar':
        esl, hedef, fark, nt, nk, ekk, hk = tekrar_coz(d)
        if esl == 'TEKRAR':
            row.update({'eslesme': 'TEKRAR', 'hedef': hedef, 'on_durum': 'TEKRAR', 'neden_kodu': 'kopya',
                        'neden_metni': kisalt(d['_neden'], 200), 'kanit': kanit})
            not_.append(nt)
        elif esl == 'BENZER':
            row.update({'eslesme': 'BENZER', 'hedef': hedef, 'on_durum': 'D_KODLANMADI_NEDENLI', 'neden_kodu': 'benzer_var',
                        'fark': kisalt(fark + ' | ' + sinif_ozet(hedef), 360),
                        'neden_metni': kisalt('benzer/tekrar denmiş, mantık farkı fark sütununda: ' + d['_neden'], 200),
                        'kanit': kanit + (' ; ' + ekk if ekk else '') + f" ; sonuclar/hesap_defteri/ara/kod_kaydi.csv#{hedef}"})
            not_.append(nt)
        elif esl == 'KARTBENZER':
            kid = hedef
            row.update({'eslesme': 'BENZER', 'hedef': kid, 'on_durum': 'D_KODLANMADI_NEDENLI', 'neden_kodu': 'benzer_var',
                        'fark': kisalt(fark, 300),
                        'neden_metni': kisalt('benzer/tekrar denmiş (hedef kodlanmamış kart; hedef=kart_id): ' + d['_neden'], 200),
                        'kanit': kanit + f" ; {REL_SD}adaylar.csv:{ADAY[kid][1]}"})
            not_.append(nt)
            if TEKRAR_AYNI.search(d['_neden']) and kid in KART_BIRINCIL:
                hh = HID_BY_KEY[KART_BIRINCIL[kid]]
                row.update({'eslesme': 'TEKRAR', 'hedef': hh, 'on_durum': 'TEKRAR', 'neden_kodu': 'kopya', 'fark': '',
                            'neden_metni': kisalt(d['_neden'], 200)})
                not_.append(f"aynı kaynak olduğu metinde yazıyor; hedef kartın birincil ham satırı {hh}")
        else:
            row.update({'eslesme': 'YOK', 'on_durum': 'BELIRSIZ', 'neden_kodu': 'benzer_var',
                        'neden_metni': kisalt('tekrar denmiş ama hedef çözülemedi: ' + d['_neden'], 200), 'kanit': kanit})
            not_.append(nt)

    elif kn == 'belirsiz':
        row.update({'eslesme': 'YOK', 'on_durum': 'BELIRSIZ', 'neden_kodu': 'kaynak_okunamadi',
                    'neden_metni': kisalt('tur3 sonunda da belirsiz: ' + d['_neden'], 200), 'kanit': kanit})
    else:
        row.update({'eslesme': 'YOK', 'on_durum': 'BELIRSIZ', 'neden_metni': 'tanınmayan karar ' + kn, 'kanit': kanit})

    row['not'] = ' ; '.join(x for x in ([row['not']] if row['not'] else []) + not_)
    if not row['kanit']:
        row['kanit'] = kanit
    cikti.append(row)

# --------------------------------------------------------------------------------------
# 6) dal ek katalogları (V901-V903)
# --------------------------------------------------------------------------------------
dal_rapor = []
ham_ad_set = set()
ham_url_set = set()
for fn, kat in katalog.items():
    uc = URL_SUTUN.get(fn)
    for r in kat:
        if uc and r.get(uc):
            ham_url_set.add(nurl(r[uc]))
        ham_ad_set.add(nrm(r.get(AD_SUTUN[fn] or 'kurallar', '')))

for vid, dfn in DAL_DOSYALAR:
    yol = DAL_KOK + dfn
    if not os.path.exists(yol):
        dal_rapor.append((vid, dfn, 'DOSYA YOK', 0, 0))
        continue
    rows_ = oku(yol)
    kap = 0
    ek = []
    for i, r in enumerate(rows_, 1):
        sutunlar = list(r.keys())
        ad_ = r.get('strateji') or r.get('ad') or r.get(sutunlar[1] if len(sutunlar) > 1 else sutunlar[0]) or ''
        url_ = r.get('URL') or r.get('url') or r.get('kod_linki') or r.get('kaynak_url') or ''
        ek.append((i, r, ad_, url_))
    dal_rapor.append((vid, dfn, 'okundu', len(rows_), sutunlar))
    globals().setdefault('DAL_SATIRLARI', {})[vid] = (dfn, ek)

DAL_OZET = {}
for vid, (dfn, ek) in globals().get('DAL_SATIRLARI', {}).items():
    kapsanan = 0
    for i, r, ad_, url_ in ek:
        if (nurl(url_) and nurl(url_) in ham_url_set) or (nrm(ad_) and nrm(ad_) in ham_ad_set):
            kapsanan += 1
    DAL_OZET[vid] = (dfn, len(ek), kapsanan)

# dal satırları: URL/repo'su MASTER_katalog (V001) içinde bulunanlar "kapsanıyor"; bulunamayanlar (strateji olmayan
# "proje bulunamadı / araç / okunmadı" satırları) ham satır olarak eklenir.
_master_blob = [' '.join(r.values()).lower() for r in katalog['MASTER_katalog_2026-11.csv']]
DAL_KAPSANAN = collections.Counter()
for vid, (dfn, ek) in globals().get('DAL_SATIRLARI', {}).items():
    for i, r, ad_, url_ in ek:
        keys = []
        u = re.sub(r'^https?://(www\.)?', '', (url_ or '').lower()).rstrip('/')
        if len(u) > 5 and u != '-':
            keys.append(u)
        m = re.match(r'([^ ]+)', (ad_ or '').lower())
        if m and '/' in m.group(1):
            keys.append(m.group(1))
        if keys and any(any(k in b for k in keys) for b in _master_blob):
            DAL_KAPSANAN[vid] += 1
            continue
        durum = (r.get('durum') or '')
        ad_g = ad_ if ad_ and ad_ != '-' else (r.get('bolge') or r.get('ulke') or '-')
        notm = r.get('not') or r.get('sonuc_ozeti') or ''
        nk, ond = 'kapsam_disi', 'D_KODLANMADI_NEDENLI'
        if r.get('tur') == 'ML' or durum == 'elendi' and 'ML' in notm:
            nk, ond = 'ml', 'G_ML'
        row = {c: '' for c in SUTUNLAR}
        row.update({'ham_id': f'{vid}:{i}', 'kaynak_id': vid, 'kaynak_satir_no': str(i), 'kaynaktaki_ad': kisalt(ad_g, 120),
                    'kisa_mantik': kisalt(f"{r.get('sonuc_ozeti','')} | {notm}", 160), 'aile': 'diger', 'eslesme': 'YOK',
                    'on_durum': ond, 'neden_kodu': nk,
                    'neden_metni': kisalt(f"strateji satırı değil (durum={durum}): {notm}; {r.get('sonuc_ozeti','')}", 200),
                    'kanit': f"{DAL_ON}{dfn}:{i}",
                    'not': f"dal ek kataloğu; MASTER_katalog (V001) içinde karşılığı yok; kaynak_id {vid} geçici (kaynaklar.csv'de yok)"})
        cikti.append(row)

# --------------------------------------------------------------------------------------
# 7) elle kararlar
# --------------------------------------------------------------------------------------
by_id = {r['ham_id']: r for r in cikti}
for hid_, e in ELLE.items():
    if hid_ not in by_id:
        print('UYARI: elle karar ham_id yok:', hid_, file=sys.stderr)
        continue
    r = by_id[hid_]
    for k, v in e.items():
        if k == 'ham_id' or v == '':
            continue
        if k == 'not':
            r['not'] = (r['not'] + ' ; ' if r['not'] else '') + 'ELLE: ' + v
        elif k in SUTUNLAR:
            r[k] = v

# --------------------------------------------------------------------------------------
# 8) yaz
# --------------------------------------------------------------------------------------
os.makedirs(ARA, exist_ok=True)
with open(os.path.join(ARA, 'G6_V3_ham.csv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=SUTUNLAR)
    w.writeheader()
    for r in cikti:
        w.writerow({k: r.get(k, '') for k in SUTUNLAR})

# özet
ozet = {
    'satir_sayisi': len(cikti),
    'kaynak_basina': collections.Counter(r['kaynak_id'] for r in cikti),
    'on_durum': collections.Counter(r['on_durum'] for r in cikti),
    'eslesme': collections.Counter(r['eslesme'] for r in cikti),
    'neden_kodu': collections.Counter(r['neden_kodu'] for r in cikti),
    'final_karar': collections.Counter(d['_karar'] for d in taban),
    'oe_karar': collections.Counter(d['karar'] for d in taban),
    'zincir': collections.Counter('>'.join(f"{a}:{k}" for a, k, ln, r in d['_zincir']) for d in taban),
    'kart_isleme': kart_isleme,
    'hiza_duzeltme': uyari_hiza,
    'kural_acik_aday': kural_acik_liste,
    'dal_ozet': DAL_OZET,
    'kart_ham_satirsiz': sorted(k for k in KART if k not in KART_BIRINCIL),
}
with open(os.path.join(ARA, 'G6_V3_ozet.json'), 'w', encoding='utf-8') as f:
    json.dump(ozet, f, ensure_ascii=False, indent=1, default=lambda o: dict(o) if isinstance(o, collections.Counter) else list(o))
print(json.dumps(ozet, ensure_ascii=False, indent=1, default=lambda o: dict(o) if isinstance(o, collections.Counter) else list(o))[:6000])
