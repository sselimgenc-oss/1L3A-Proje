"""paperswithbacktest/awesome-systematic-trading — fiyat verisiyle uygulanabilen stratejiler, kripto evrenine taşınmış.

Eşleme: işlem günü pencereleri takvim gününe çevrildi (21->30, 63->90, 126->182, 252->365, 5->7); hisse/vadeli
evreni -> 25 coin; ondalık/beşlik dilimler 25 coine göre (beşlik = 5 coin). Orijinal koddaki hatalar (ör. 12 aylık döngüde
iki bacağın da long olması) düzeltilmiş, amaçlanan kural test edilmiştir; rapor tablosunda not edilir.
"""
import numpy as np, pandas as pd
from scipy.stats import skew
from . import ortak as O
from .kurallar import topn_agr, kw, atr, sma


def _aybasi(idx):
    return idx.is_month_start


def ls_agr(score, n_long, n_short, freq="M", long_only=False):
    """Skora göre en yüksek n_long long, en düşük n_short short; bacak başına brüt 0.5 (toplam brüt 1)."""
    W = pd.DataFrame(np.nan, index=score.index, columns=score.columns)
    rb = _aybasi(score.index) if freq == "M" else (score.index.dayofweek == 0 if freq == "W" else np.ones(len(score), bool))
    for i in np.where(rb)[0]:
        s = score.iloc[i].dropna()
        w = pd.Series(0.0, index=score.columns)
        if len(s) >= n_long + (0 if long_only else n_short):
            srt = s.sort_values()
            lg = srt.index[-n_long:]
            if long_only:
                w[lg] = 1.0 / n_long
            else:
                sh = srt.index[:n_short]
                w[lg] = 0.5 / n_long; w[sh] = -0.5 / n_short
        W.iloc[i] = w.values
    return W.ffill().fillna(0.0)


def katmanli(W, k):
    """k örtüşen aylık tutuş dilimi: son k yeniden dengeleme ağırlığının ortalaması."""
    rb = _aybasi(W.index)
    snaps = W[rb]
    avg = snaps.rolling(k, min_periods=1).mean()
    return avg.reindex(W.index).ffill().fillna(0.0)


# --- 1. 12 aylık döngü: 365-335 gün önceki 30 günlük getiri; top 5 long / bottom 5 short, aylık
def ay12_dongu(C):
    sc = C.shift(335) / C.shift(365) - 1
    return ls_agr(sc, 5, 5)


# --- 2. 52 hafta zirvesi: kapanış / 365g en yüksek; top 5 long, bottom 5 short, 3 örtüşen dilim
def zirve52(C):
    return katmanli(ls_agr(C / C.rolling(365).max(), 5, 5), 3)


# --- 4/45. Varlık sınıfı / sektör momentum rotasyonu: 365g ROC top 5 long, aylık
def mom_rotasyon(C):
    return ls_agr(C.pct_change(365), 5, 0, long_only=True)


# --- 5. Varlık sınıfı trend takibi: kapanış > 300g SMA olanlar eşit ağırlık, aylık
def trend_takip(C):
    ok = C > C.rolling(300).mean()
    W = ok.astype(float).div(ok.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    W[~_aybasi(C.index)] = np.nan
    return W.ffill().fillna(0.0)


# --- 7/8. Düşük beta (BAB): BTC'ye göre 365g beta; düşük üçte bir long, yüksek üçte bir short, bacaklar 1/ort.beta (en çok 2)
def bab(C):
    R = C.pct_change()
    m = R["BTCUSDT"] if "BTCUSDT" in R else R.mean(axis=1)  # BTC yoksa eşit ağırlıklı evren piyasa vekili
    beta = R.rolling(365, min_periods=200).cov(m).div(m.rolling(365, min_periods=200).var(), axis=0)
    W = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    for i in np.where(_aybasi(C.index))[0]:
        b = beta.iloc[i].drop("BTCUSDT", errors="ignore").dropna()
        w = pd.Series(0.0, index=C.columns)
        if len(b) >= 9:
            k = len(b) // 3; srt = b.sort_values(); lo, hi = srt.index[:k], srt.index[-k:]
            ml = min(2.0, 1 / b[lo].mean()) if b[lo].mean() > 0 else 2.0
            mh = min(2.0, 1 / b[hi].mean()) if b[hi].mean() > 0 else 2.0
            w[lo] = 0.5 / k * ml; w[hi] = -0.5 / k * mh
        W.iloc[i] = w.values
    return W.ffill().fillna(0.0)


# --- 11. Tutarlı momentum: (212->30 gün) ve (182->0 gün) getirilerinin ikisinde de üst üçte bir long, alt üçte bir short; 6 ay tut
def tutarli_mom(C):
    r1 = C.shift(30) / C.shift(212) - 1; r2 = C / C.shift(182) - 1
    W = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    ms = np.where(_aybasi(C.index) & (C.index.month % 6 == 1))[0]
    for i in ms:
        a, b_ = r1.iloc[i].dropna(), r2.iloc[i].dropna(); ix = a.index.intersection(b_.index)
        w = pd.Series(0.0, index=C.columns)
        if len(ix) >= 9:
            a, b_ = a[ix], b_[ix]
            q = len(ix) // 3
            lg = set(a.nlargest(q).index) & set(b_.nlargest(q).index); sh = set(a.nsmallest(q).index) & set(b_.nsmallest(q).index)
            if lg: w[list(lg)] = 0.5 / len(lg)
            if sh: w[list(sh)] = -0.5 / len(sh)
        W.iloc[i] = w.values
    return W.ffill().fillna(0.0)


# --- 13. Döviz momentum faktörü: 365g ROC top 3 long / bottom 3 short, aylık
def mom_3_3(C):
    return ls_agr(C.pct_change(365), 3, 3)


# --- 29/32. Momentum faktörü: 365g ROC beşlik (5/5), aylık
def mom_5_5(C):
    return ls_agr(C.pct_change(365), 5, 5)


# --- 30. Stil rotasyonu: 365g getiri en iyi 1 long / en kötü 1 short (orijinal dolar farkı -> yüzde)
def mom_1_1(C):
    return ls_agr(C.pct_change(365), 1, 1)


# --- 33. Fon momentumu: 182g getiri top %10 (3 coin) long, çeyreklik
def fon_mom(C):
    W = ls_agr(C.pct_change(182), 3, 0, long_only=True)
    q = _aybasi(C.index) & np.isin(C.index.month, [3, 6, 9, 12])
    W[~q] = np.nan
    return W.ffill().fillna(0.0)


# --- 26. Düşük volatilite: 365g haftalık getiri std; en düşük çeyrek (6) long, aylık
def dusuk_vol(C):
    wk = C.pct_change(7)
    v = wk.rolling(365).apply(lambda x: np.nanstd(x[::7]), raw=True)
    return ls_agr(-v, 6, 0, long_only=True)


# --- 28. Momentum + volatilite: 182g getiri (son 7 gün hariç); yüksek vol yarısında top 3 long / bottom 3 short; 6 örtüşen dilim
def mom_vol(C):
    r = C.shift(7) / C.shift(182) - 1
    v = C.pct_change().rolling(175).std().shift(7)
    W = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    for i in np.where(_aybasi(C.index))[0]:
        rr, vv = r.iloc[i].dropna(), v.iloc[i].dropna(); ix = rr.index.intersection(vv.index)
        w = pd.Series(0.0, index=C.columns)
        if len(ix) >= 10:
            hv = vv[ix].nlargest(len(ix) // 2).index; x = rr[hv].sort_values()
            w[x.index[-3:]] = 0.5 / 3; w[x.index[:3]] = -0.5 / 3
        W.iloc[i] = w.values
    return katmanli(W.ffill().fillna(0.0), 6)


# --- 35. Eşli geçiş: BTC ile ETH'den son 90 günde iyi olana %100, çeyreklik
def esli_gecis(C):
    a, b_ = "BTCUSDT", "ETHUSDT"
    W = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    q = _aybasi(C.index) & np.isin(C.index.month, [3, 6, 9, 12])
    for i in np.where(q)[0]:
        if i < 90: continue
        ra, rb = C[a].iloc[i] / C[a].iloc[i - 90] - 1, C[b_].iloc[i] / C[b_].iloc[i - 90] - 1
        w = pd.Series(0.0, index=C.columns); w[a if ra >= rb else b_] = 1.0; W.iloc[i] = w.values
    return W.ffill().fillna(0.0)


# --- 36/37. Mesafe yöntemiyle çift işlemi
def cift_mesafe(C, form=120, period=20, npairs=5, k=0.5, stocks=False):
    """36 (ülke ETF): her 20 günde 120g normalize fiyat mesafesine göre en yakın 5 çift; yayılım ±0.5 sd dışına çıkınca
    düşük olan long / yüksek olan short; bant içine dönünce veya dönem sonunda çık.
    37 (hisse): 365g pencere, en yakın 20 çift, ±2 sd giriş, bant içine dönünce çık, en çok 5 açık çift."""
    cols = list(C.columns); W = pd.DataFrame(0.0, index=C.index, columns=cols)
    idx = C.index; i = form; open_pairs = {}
    pairs = []
    while i < len(idx):
        if (i - form) % period == 0 or (stocks and not pairs):
            X = C.iloc[i - form:i].dropna(axis=1)
            if X.shape[1] >= 4:
                N = X / X.iloc[0]
                cs = list(N.columns); d = []
                for a_ in range(len(cs)):
                    for b_ in range(a_ + 1, len(cs)):
                        d.append((((N[cs[a_]] - N[cs[b_]]) ** 2).sum(), cs[a_], cs[b_]))
                pairs = [(x, y) for _, x, y in sorted(d)[:npairs]]
            if not stocks:
                open_pairs = {}
        w = pd.Series(0.0, index=cols)
        for x, y in pairs:
            win = C[[x, y]].iloc[max(0, i - form):i + 1].dropna()
            if len(win) < form // 2: continue
            N = win / win.iloc[0]; sp = N[x] - N[y]; mu, sd = sp.iloc[:-1].mean(), sp.iloc[:-1].std(); s = sp.iloc[-1]
            key = (x, y)
            if key in open_pairs:
                if abs(s - mu) <= k * sd:
                    del open_pairs[key]
            elif abs(s - mu) > k * sd and (not stocks or len(open_pairs) < 5):
                open_pairs[key] = 1 if s > mu else -1
            if key in open_pairs:
                sg = open_pairs[key]; lim = npairs if not stocks else 5
                w[x] += -sg * 0.5 / lim; w[y] += sg * 0.5 / lim
        W.iloc[i] = w.values
        i += 1
    return W


# --- 40. Yeniden dengeleme primi: günlük dengelenen eşit ağırlık long - 0.7 x dengelenmeyen eşit ağırlık
def dengeleme_primi(C):
    ok = C.notna()
    start = ok.all(axis=1).idxmax() if ok.all(axis=1).any() else C.index[0]
    X = C[C.index >= start]
    n = X.shape[1]
    lw = pd.DataFrame(1.0 / n, index=X.index, columns=X.columns)
    bh = (X / X.iloc[0]) / n * 0.7
    sw = bh.div(1 + (lw * 0).sum(axis=1), axis=0)  # sabit adet short: ağırlık fiyatla kayar
    W = (lw - sw).reindex(C.index).fillna(0.0)
    return W / 1.7


# --- 42. Getiri asimetrisi: 365g günlük getiride (ort+2sd üstü sayısı - ort-2sd altı sayısı); en düşük 5 long, en yüksek 5 short
def asimetri(C):
    R = C.pct_change()
    def ie(x):
        x = x[~np.isnan(x)]
        if len(x) < 200: return np.nan
        m, s = x.mean(), x.std(); return ((x > m + 2 * s).sum() - (x < m - 2 * s).sum())
    sc = R.rolling(365).apply(ie, raw=True)
    return ls_agr(-sc, 5, 5)


# --- 47. Kısa vadeli dönüş: haftalık; 7 günün en kötü 5'i long, 30 günün en iyi 5'i short (longlar hariç)
def kisa_donus(C):
    r7, r30 = C.pct_change(7), C.pct_change(30)
    W = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    for i in np.where(C.index.dayofweek == 0)[0]:
        a, b_ = r7.iloc[i].dropna(), r30.iloc[i].dropna(); w = pd.Series(0.0, index=C.columns)
        if len(a) >= 10:
            lg = a.nsmallest(5).index; sh = b_.drop(lg, errors="ignore").nlargest(5).index
            w[lg] = 0.1; w[sh] = -0.1
        W.iloc[i] = w.values
    return W.ffill().fillna(0.0)


# --- 49. Çarpıklık: 365g günlük getiri çarpıklığı; en düşük 5 long, en yüksek 5 short
def carpiklik(C):
    sk = C.pct_change().rolling(365, min_periods=300).apply(lambda x: skew(x[~np.isnan(x)]), raw=True)
    return ls_agr(-sk, 5, 5)


# --- 54. Zaman serisi momentumu: 365g getiri işareti; ters vol ağırlık (90g), bacak başına %10 vol hedefi (en çok 4x)
def tsmom(C, target=0.10):
    R = C.pct_change(); sig = np.sign(C.pct_change(365))
    vol = R.rolling(90).std() * np.sqrt(365)
    W = pd.DataFrame(np.nan, index=C.index, columns=C.columns)
    for i in np.where(_aybasi(C.index))[0]:
        s, v = sig.iloc[i], vol.iloc[i]; w = pd.Series(0.0, index=C.columns)
        for sg in (1, -1):
            ix = s[s == sg].index.intersection(v.dropna().index)
            if len(ix) == 0: continue
            iv = 1 / v[ix]; wl = iv / iv.sum()
            cov = R[ix].iloc[max(0, i - 90):i].cov() * 365
            pv = float(np.sqrt(wl.values @ cov.values @ wl.values)) if len(ix) > 1 else float(v[ix].iloc[0])
            lev = min(4.0, target / pv) if pv > 0 else 0
            w[ix] = sg * wl * lev
        W.iloc[i] = w.values
    return W.ffill().fillna(0.0)


# --- 50*. Küçük ölçek (piyasa değeri yok -> 30g dolar hacmi): en küçük 5 long / en büyük 5 short, aylık
def kucuk_olcek(C, QV):
    return ls_agr(-QV.rolling(30).mean(), 5, 5)


# --- 55*. WTI-Brent yayılımı -> log(ETH/BTC) 20g SMA: üstündeyse ETH short / BTC long, altındaysa tersi (günlük)
def eth_btc_yayilim(C):
    sp = np.log(C["ETHUSDT"] / C["BTCUSDT"]); m = sp.rolling(20).mean()
    W = pd.DataFrame(0.0, index=C.index, columns=C.columns)
    s = np.where(sp > m, -1.0, np.where(sp < m, 1.0, 0.0))
    W["ETHUSDT"] = 0.5 * s; W["BTCUSDT"] = -0.5 * s
    return W


# --- 41*. Kalıntı momentum: aylık; son 36 ayın aylık getirisi BTC'ye regresyon; son 12 ay kalıntısı toplam/std; beşlik L/S
def kalinti_mom(C):
    M = C.resample("MS").first()
    Rm = M.pct_change()
    sc = pd.DataFrame(np.nan, index=M.index, columns=M.columns)
    mkt = Rm["BTCUSDT"] if "BTCUSDT" in Rm else Rm.mean(axis=1)
    for t in range(36, len(M)):
        win = Rm.iloc[t - 36:t]; mk = mkt.iloc[t - 36:t]
        for s in M.columns:
            y = win[s]; ok = y.notna() & mk.notna()
            if ok.sum() < 24 or s == "BTCUSDT": continue
            X = np.column_stack([np.ones(ok.sum()), mk[ok].values]); beta = np.linalg.lstsq(X, y[ok].values, rcond=None)[0]
            res = y[ok].values - X @ beta; r12 = res[-12:]
            sc.iloc[t, sc.columns.get_loc(s)] = r12.sum() / r12.std() if r12.std() > 0 else np.nan
    S = sc.reindex(C.index, method="ffill")
    return ls_agr(S, 5, 5)


# --- takvim (BTC ve sepet; "pos")
def ay_donumu(b):
    d = b.index; nxt = d + pd.Timedelta(days=2)
    # ayın sondan ikinci günü kapanışında al, yeni ayın 3. günü kapanışında sat
    return pd.Series(((nxt.month != d.month) | (d.day < 3)).astype(float), index=d)


def maas_gunu(b):
    return pd.Series((b.index.day == 15).astype(float), index=b.index)


def ocak_barometre(b):
    c = b["close"]; pos = pd.Series(0.0, index=c.index)
    for y in sorted(set(c.index.year)):
        jan = c[(c.index.year == y) & (c.index.month == 1)]
        if len(jan) < 20: continue
        pos[(c.index.year == y) & (c.index.month == 1)] = 1.0
        if jan.iloc[-1] > jan.iloc[0]:
            pos[(c.index.year == y) & (c.index.month > 1)] = 1.0
    return pos.shift(-1).fillna(0.0)  # Ocak'ın ilk kapanışında al (pozisyon ertesi mumdan)


def vade_haftasi(b):
    """Opsiyon vade haftası (kripto uyarlaması: ayın son Cuma'sı Deribit vadesi): o haftanın Pazartesi'sinden Cuma'ya long."""
    d = b.index
    last_fri = pd.Series(d).apply(lambda x: (x + pd.offsets.MonthEnd(0)) - pd.Timedelta(days=((x + pd.offsets.MonthEnd(0)).dayofweek - 4) % 7))
    days_to = (pd.DatetimeIndex(last_fri.values).tz_localize(None) - d.tz_localize(None)).days
    return pd.Series(((days_to >= 2) & (days_to <= 5)).astype(float), index=d)  # tutulan gün = Pzt..Per


def gece_seans_btc(b1h):
    """Bitcoin gün içi mevsimsellik: 22:00'de long, 00:00'da kapat (pozisyon 22 ve 23 mumlarında)."""
    return pd.Series(np.isin(b1h.index.hour, [21, 22]).astype(float), index=b1h.index)  # 21 kapanışında karar -> 22,23 tutulur


def ath_trend(b):
    """Tüm zamanların en yüksek kapanışı (veri başından) -> long; 1 x ATR(10) iz süren stop."""
    c = b["close"]; a = atr(b, 10)
    return kw(b, c >= c.cummax().shift(1), sl_abs=a, trail=a, trail_k=1.0)


# --- literatürden (README'deki kripto makaleleri; site erişilemedi, kurallar yayımlanmış tanımlardan)
def btc_max10(b):
    """Padysak & Vojtko (2022) MAX: kapanış 10 günün en yüksek kapanışıysa ertesi gün long."""
    c = b["close"]; return (c >= c.rolling(10).max()).astype(float)


def btc_min10(b):
    """Padysak & Vojtko (2022) MIN: kapanış 10 günün en düşüğüyse ertesi gün long."""
    c = b["close"]; return (c <= c.rolling(10).min()).astype(float)


def asiri_tepki(b, k=2.0, n=30):
    """Caporale & Plastun (2019) aşırı tepki: günlük getiri ort ± k sd dışındaysa ertesi gün aynı yönde pozisyon."""
    r = b["close"].pct_change(); m, s = r.rolling(n).mean().shift(1), r.rolling(n).std().shift(1)
    return pd.Series(np.where(r > m + k * s, 1.0, np.where(r < m - k * s, -1.0, 0.0)), index=b.index)
