"""Dış adayların yayınlanmış kurallarını olduğu gibi test eder (parametre seçimi yok).
Veri kilit tarihine kadar: 2025-10-31 (2025-11-01 sonrası kasada, karar 20)."""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "/home/user/1L3A-Proje")
from motor.veri.depo import mum_oku

BITIS = pd.Timestamp("2025-10-31 23:59:59", tz="UTC")
FEE = 0.001          # %0.1 işlem başı (her iki yön dahil edilir)
SLIP = 0.0002        # %0.02 kayma

def oku(sym, tf):
    return mum_oku(sym, tf, bitis=BITIS)

def metrikler(eq, yil_bar, islem_sayisi, ret_list):
    eq = pd.Series(eq)
    r = eq.pct_change().dropna()
    toplam = eq.iloc[-1] / eq.iloc[0] - 1
    yil = len(r) / yil_bar
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yil) - 1 if yil > 0 else np.nan
    dd = (eq / eq.cummax() - 1).min()
    sh = r.mean() / r.std() * np.sqrt(yil_bar) if r.std() > 0 else np.nan
    w = [x for x in ret_list if x > 0]; l = [x for x in ret_list if x < 0]
    pf = (sum(w) / -sum(l)) if l and sum(l) != 0 else np.nan
    return dict(toplam=round(toplam, 4), cagr=round(cagr, 4), maks_dusus=round(dd, 4),
                sharpe=round(sh, 2), islem=islem_sayisi,
                kazanma=round(len(w) / len(ret_list), 3) if ret_list else np.nan,
                pf=round(pf, 2) if pf == pf else np.nan)

def al_tut(close):
    return close / close.iloc[0]

def gunluk_sinyal_testi(close, sinyal, yil_bar=365):
    """Sinyal kapanışta okunur, bir sonraki barın getirisine uygulanır; işlem maliyeti pozisyon değişince."""
    poz = sinyal.shift(1).fillna(0)           # t barı kapanışı -> t+1 pozisyonu
    getiri = close.pct_change().fillna(0)
    maliyet = poz.diff().abs().fillna(0) * (FEE + SLIP)
    net = poz * getiri - maliyet
    eq = (1 + net).cumprod()
    eq = pd.concat([pd.Series([1.0]), eq.reset_index(drop=True)], ignore_index=True)
    islem_adim = poz.diff().abs().fillna(0)
    islem = int((islem_adim > 0).sum() // 2 + (islem_adim.iloc[0] > 0))
    # işlem başına getiri (basit): pozisyon açık kaldığı süreçler
    rl = []
    giris = None
    for t in range(1, len(poz)):
        if poz.iloc[t] == 1 and poz.iloc[t - 1] == 0:
            giris = close.iloc[t]
        if poz.iloc[t] == 0 and poz.iloc[t - 1] == 1 and giris:
            rl.append(close.iloc[t] / giris - 1 - 2 * (FEE + SLIP)); giris = None
    return metrikler(eq.values, yil_bar, islem, rl), eq

def donem_dilimleri(close, sinyal, yil_bar=365):
    out = {}
    for ad, a, b in [("2019-2021", "2019-01-01", "2021-12-31"), ("2022-2023", "2022-01-01", "2023-12-31"),
                     ("2024-2025(kilit_oncesi)", "2024-01-01", "2025-10-31")]:
        c = close.loc[a:b]; s = sinyal.loc[a:b]
        m, _ = gunluk_sinyal_testi(c, s, yil_bar)
        out[ad] = {"strat": m["toplam"], "al_tut": round(c.iloc[-1] / c.iloc[0] - 1, 4), "dd": m["maks_dusus"], "islem": m["islem"]}
    return out

def run_gunluk(sym, ad, sinyal_fn):
    d = oku(sym, "1d")
    c = d["kapanis"]
    s = sinyal_fn(d)
    m, eq = gunluk_sinyal_testi(c, s, 365)
    m["al_tut"] = round(c.iloc[-1] / c.iloc[0] - 1, 4)
    m["donemler"] = donem_dilimleri(c, s, 365)
    return {"aday": ad, "sembol": sym, "tf": "1d", "baslangic": str(c.index[0].date()), "bitis": str(c.index[-1].date()), **m}

# ---- Aday A: TrendRider özü: günlük kapanış > SMA50 ise tut, değilse nakit
def trendrider(d):
    sma = d["kapanis"].rolling(50).mean()
    return (d["kapanis"] > sma).astype(float).fillna(0)

# ---- Aday B: Leah E015: günlük EMA30 > EMA90 ise tut
def e015(d):
    e30 = d["kapanis"].ewm(span=30, adjust=False).mean()
    e90 = d["kapanis"].ewm(span=90, adjust=False).mean()
    return (e30 > e90).astype(float)

# ---- Aday C: ETH 4s kırılım (delta-paper-bot), yalnız long+short, sinyal kapanışta, giriş bir sonraki açılışta
def ind_adx(h, l, c, n=14):
    up = h.diff(); dn = -l.diff()
    pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / n, adjust=False).mean()
    pdi = 100 * pd.Series(pdm, index=h.index).ewm(alpha=1 / n, adjust=False).mean() / atr
    mdi = 100 * pd.Series(mdm, index=h.index).ewm(alpha=1 / n, adjust=False).mean() / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
    return dx.ewm(alpha=1 / n, adjust=False).mean(), atr

def delta_kirilim(d):
    h, l, c, o = d["yuksek"], d["dusuk"], d["kapanis"], d["acilis"]
    adx, atr = ind_adx(h, l, c, 14)
    ema200 = c.ewm(span=200, adjust=False).mean()
    don_h = h.shift(1).rolling(40).max(); don_l = l.shift(1).rolling(40).min()
    low20 = l.rolling(20).min().shift(1); high20 = h.rolling(20).max().shift(1)
    n = len(c)
    pos = np.zeros(n); entry = np.full(n, np.nan); stop = np.full(n, np.nan); best = np.nan
    ret = []; eq = [1.0]; equity = 1.0; cur = 0; ep = np.nan; sl = np.nan; best = np.nan; qty_frac = 0
    trades_r = []
    for t in range(1, n):
        # açık pozisyonu yönet (bu bar içinde high/low ile stop kontrolü, kapanışta izleyen stop güncelle)
        if cur != 0:
            if cur == 1:
                hit = l.iloc[t] <= sl
                best = max(best, h.iloc[t])
                trail = min(low20.iloc[t] if low20.iloc[t] == low20.iloc[t] else 1e18, best - 3 * atr.iloc[t])
                new_sl = max(sl, trail)
                if hit:
                    r = sl / ep - 1 - 2 * (FEE + SLIP); cur = 0
                else:
                    sl = new_sl; r = None
            else:
                hit = h.iloc[t] >= sl
                best = min(best, l.iloc[t])
                trail = max(high20.iloc[t] if high20.iloc[t] == high20.iloc[t] else -1e18, best + 3 * atr.iloc[t])
                new_sl = min(sl, trail)
                if hit:
                    r = 1 - sl / ep - 2 * (FEE + SLIP); cur = 0
                else:
                    sl = new_sl; r = None
            if cur == 0:
                trades_r.append(r)
                equity *= 1 + qty_frac * r
        # yeni giriş: önceki bar kapanışında sinyal, bu barın açılışında
        if cur == 0 and t >= 201 and adx.iloc[t - 1] == adx.iloc[t - 1] and atr.iloc[t - 1] == atr.iloc[t - 1]:
            up = c.iloc[t - 1] > don_h.iloc[t - 1] and c.iloc[t - 1] > ema200.iloc[t - 1] and adx.iloc[t - 1] >= 20
            dn = c.iloc[t - 1] < don_l.iloc[t - 1] and c.iloc[t - 1] < ema200.iloc[t - 1] and adx.iloc[t - 1] >= 20
            if up or dn:
                ep = o.iloc[t]; a = atr.iloc[t - 1]
                dist = 2.5 * a
                cur = 1 if up else -1
                sl = ep - dist if up else ep + dist
                best = h.iloc[t] if up else l.iloc[t]
                risk_pct = dist / ep
                qty_frac = min(0.015 / risk_pct, 10.0) * 0.01 * 0 + min(0.015 / risk_pct, 10.0)
                qty_frac = min(qty_frac, 10.0)  # kaldıraç tavanı 10x (notional/equity)
        pos[t] = cur
        eq.append(equity)
    # eq: işlem kapanışlarında oluşan özsermaye
    eqs = pd.Series(eq)
    m = metrikler(eqs.values, 365 * 6, len(trades_r), [x for x in trades_r if x is not None])
    return m, trades_r

def run_4h_delta(sym="ETHUSDT"):
    d = oku(sym, "4h")
    m, trades = delta_kirilim(d)
    m["aday"] = "ETH 4s kırılım (delta-paper-bot)"; m["sembol"] = sym; m["tf"] = "4h"
    m["baslangic"] = str(d.index[0].date()); m["bitis"] = str(d.index[-1].date())
    return m

if __name__ == "__main__":
    sonuc = []
    sonuc.append(run_gunluk("BTCUSDT", "TrendRider özü (SMA50)", trendrider))
    sonuc.append(run_gunluk("ETHUSDT", "TrendRider özü (SMA50)", trendrider))
    sonuc.append(run_gunluk("BTCUSDT", "Leah E015 (EMA30/90)", e015))
    sonuc.append(run_gunluk("ETHUSDT", "Leah E015 (EMA30/90)", e015))
    try:
        sonuc.append(run_4h_delta("ETHUSDT"))
    except FileNotFoundError as e:
        sonuc.append({"aday": "ETH 4s kırılım", "hata": str(e)})
    print(json.dumps(sonuc, ensure_ascii=False, indent=1, default=str))
