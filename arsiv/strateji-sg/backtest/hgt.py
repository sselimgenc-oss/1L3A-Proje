"""HGT — Haftalık Yön, Günlük Tetik (kripto, çoklu zaman dilimi; 20 Trading Stratejisi Sistem #5'in uyarlaması).

Kaynak kural (20 Str. #5, "Çoklu Zaman Çerçevesi Sistemi", 15dk yön / 5dk işlem): üst zaman diliminde
  fiyat > EMA3(1 kaydırılmış), EMA3 > EMA5 > EMA15 > EMA45 (3 kaydırılmış) ve histogramlar yeşil -> yükseliş;
  fiyat üst zaman diliminde 5 EMA'ya geri çekilir (dokunur) -> alt zaman dilimine inilir;
  alt zaman diliminde fiyat tüm EMA'ların üzerinde kapanır, EMA15 > EMA45, histogramlar yeşil -> giriş kapanışta;
  stop son dibin altı, hedef 1:1.
Uyarlama (haftalık yön / günlük işlem):
  * Hafta pazartesi 00:00 UTC başlar; yalnız KAPANMIŞ haftalık mumlar kullanılır (ileriye bakma yok).
  * "Histogram" (GHL/QTI, kitapta tanımsız göstergeler) yerine MACD(12,26,9) histogramı > 0 kullanılır.
  * Geri çekilme: haftalık dizilim yukarıyken son `geri_n` günde günlük dip, haftalık kaydırılmış EMA5 seviyesine
    (son kapanmış haftanın değeri) değmiş olmalı.
  * Günlük tetik: kapanış > günlük EMA3(1k), EMA5(3k), EMA15(3k), EMA45(3k); EMA15(3k) > EMA45(3k); MACD hist > 0.
  * Giriş ertesi günün açılışında (motor). Stop: son `sw_n` günün dibi, 1-3 x ATR14(1G) aralığına sıkıştırılır.
  * Çıkış: '1R' (kitap: 1:1 hedef) ya da 'trend' (1R'de %15 kısmi + başabaş, haftalık dizilim bozulunca ya da
    günlük kapanış EMA15(3k) altına inince ertesi açılışta).
Portföy: o ayın hacim sıralamasında ilk `evren_n` coin, en fazla `max_poz` pozisyon, işlem başına `risk`,
  kaldıraçsız; masraf %0.07/taraf + fonlama (günlük toplam). Motor: kripto_motor.portfoy (günlük mumlarla).

Kullanım:
  python3 -m backtest.hgt izgara    # IS (2020-2023) ızgarası + OOS (2024-2026/09) -> sonuclar/hgt/izgara.csv
  python3 -m backtest.hgt nihai     # seçilen ayarın ayrıntılı testleri (sağlamlık, rastgele kıyas, KGT/KMN ile birleşim)
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from . import gostergeler as g
from .kripto_motor import portfoy, metrik

KOK = Path(__file__).resolve().parent.parent
SONUC = KOK / "sonuclar" / "hgt"
ONBELLEK = KOK / "data" / "kripto" / "gunluk_V.pkl"
KES = pd.Timestamp("2024-01-01")
PAZARTESI = pd.Timestamp("2019-12-30")        # hafta başlangıcı referansı (pazartesi)

TEMEL = dict(yon_mod="dok", hist=True, geri=True, geri_n=10, tetik="dok", sw_n=5, stop_min=1.0, stop_max=3.0,
             cikis="trend", evren_n=20, max_poz=6, max_yon=6, risk=0.01, max_pay=0.25, max_brut=1.0,
             maliyet=0.0007, tp1_r=1.0, tp1_pay=0.15, be_tp1=True, hedef_r=0.0, ici_sira=1, yon=1, min_hafta=20)


def gunluk_V():
    """1S dizilerinden (kripto_strateji.yukle) günlük T x N diziler (UTC günü), fonlama günlük toplam."""
    if ONBELLEK.exists():
        return pd.read_pickle(ONBELLEK)
    from . import kripto_strateji as ks
    V = ks.yukle()
    z = V["zaman"]; gun = z.floor("1D"); sem = V["semboller"]
    df = lambda k: pd.DataFrame(V[k], index=z, columns=sem)
    C = df("C")
    say = C.notna().groupby(gun).sum()
    Cd = C.groupby(gun).last().where(say >= 20)
    Od = df("O").groupby(gun).first().where(Cd.notna())
    Hd = df("H").groupby(gun).max().where(Cd.notna())
    Ld = df("L").groupby(gun).min().where(Cd.notna())
    F = df("FUND").groupby(gun).sum().reindex(Cd.index).fillna(0)
    U = pd.DataFrame(V["UYE"], index=z, columns=sem).groupby(gun).last().reindex(Cd.index).fillna(False)
    ONC = pd.DataFrame(V["ONC"], index=z, columns=sem).groupby(gun).last().reindex(Cd.index).fillna(999)
    D = dict(O=Od.to_numpy(), H=Hd.to_numpy(), L=Ld.to_numpy(), C=Cd.to_numpy(), FUND=F.to_numpy(),
             UYE=U.to_numpy().astype(bool), ONC=ONC.to_numpy(), zaman=Cd.index, semboller=sem)
    pd.to_pickle(D, ONBELLEK)
    return D


def _kay(x, n):
    """n mum ileri kaydırılmış dizi (grafikte EMA'yı sağa kaydırmak = bugünkü değer n mum önceki EMA)."""
    out = np.full(len(x), np.nan)
    if n < len(x):
        out[n:] = x[:len(x) - n] if n > 0 else x
    return out


def _dizilim(c, h=None):
    """20 Str. #5 dizilimi: +1 yukarı, -1 aşağı, 0 yok. Döndürür (yön, kaydırılmış EMA5)."""
    e3, e5, e15, e45 = _kay(g.ema(c, 3), 1), _kay(g.ema(c, 5), 3), _kay(g.ema(c, 15), 3), _kay(g.ema(c, 45), 3)
    hi = g.macd(c)[2]
    yuk = (c > e3) & (e3 > e5) & (e5 > e15) & (e15 > e45)
    dus = (c < e3) & (e3 < e5) & (e5 < e15) & (e15 < e45)
    if h:
        yuk &= hi > 0; dus &= hi < 0
    return np.where(yuk, 1.0, np.where(dus, -1.0, 0.0)), e5, e15, e45


def ozellikler(D, p):
    """Coin başına günlük sinyal (+1 long / -1 short), stop mesafesi, çıkış (+1/-1: o yöndeki pozisyondan çık)
    ve haftalık yön dizileri (T x N)."""
    T, N = D["C"].shape; z = D["zaman"]
    SIG = np.zeros((T, N)); STOP = np.full((T, N), np.nan); CIK = np.zeros((T, N)); WY = np.zeros((T, N))
    hafta = ((z - PAZARTESI).days // 7).to_numpy()
    for j in range(N):
        c = D["C"][:, j]; ok = ~np.isnan(c)
        if ok.sum() < 7 * p["min_hafta"]:
            continue
        i0, i1 = np.argmax(ok), len(c) - np.argmax(ok[::-1])
        d = pd.DataFrame({k: D[K][i0:i1, j] for k, K in (("open", "O"), ("high", "H"), ("low", "L"), ("close", "C"))},
                         index=z[i0:i1]).ffill()
        hf = hafta[i0:i1]
        # haftalık mumlar; hafta k'nin değeri, hafta k'nin son günü kapanınca (ertesi pazartesi 00:00) kullanılabilir
        w = d.groupby(hf).agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        wc = w.close.to_numpy()
        if p["yon_mod"] == "dok":
            wy, _, _, _ = _dizilim(wc, p["hist"])
        else:                                   # 'ema1020': haftalık EMA10 > EMA20 ve kapanış > EMA10
            ef, es = g.ema(wc, 10), g.ema(wc, 20)
            wy = np.where((ef > es) & (wc > ef), 1.0, np.where((ef < es) & (wc < ef), -1.0, 0.0))
        we5 = _kay(g.ema(wc, 5), p.get("geri_kay", 3))   # geri çekilme seviyesi: haftalık EMA5 (kitap: 3 kaydırılmış)
        wy[:p["min_hafta"]] = 0                 # EMA'ların oturması için asgari geçmiş
        son_gun = d.groupby(hf).apply(lambda x: x.index[-1])
        s_wy = pd.Series(wy, index=son_gun.to_numpy()).reindex(d.index).ffill().fillna(0).to_numpy()
        s_we5 = pd.Series(we5, index=son_gun.to_numpy()).reindex(d.index).ffill().to_numpy()
        o, h, l, cc = (d[k].to_numpy() for k in ("open", "high", "low", "close"))
        _, de5, de15, de45 = _dizilim(cc, p["hist"])
        e3 = _kay(g.ema(cc, 3), 1); hi = g.macd(cc)[2]
        a = g.atr(h, l, cc, 14)
        sl = slice(i0, i1)
        WY[sl, j] = s_wy
        for y in ((1, -1) if p["yon"] == 0 else (p["yon"],)):
            yon_ok = s_wy == y
            if p["geri"]:                       # son geri_n günde fiyat haftalık EMA5 seviyesine geri çekildi
                deg = (l <= s_we5) if y > 0 else (h >= s_we5)
                deg = pd.Series(deg & yon_ok).rolling(p["geri_n"], min_periods=1).max().to_numpy() > 0
                yon_ok = yon_ok & deg
            if p["tetik"] == "dok":
                if y > 0:
                    tet = (cc > np.fmax.reduce([e3, de5, de15, de45])) & (de15 > de45)
                else:
                    tet = (cc < np.fmin.reduce([e3, de5, de15, de45])) & (de15 < de45)
                if p["hist"]:
                    tet &= (y * hi) > 0
            else:                               # 'kir': son 5 günün tepesinin (dibinin) kapanışla kırılması
                if y > 0:
                    tet = cc > np.roll(pd.Series(h).rolling(5).max().to_numpy(), 1)
                else:
                    tet = cc < np.roll(pd.Series(l).rolling(5).min().to_numpy(), 1)
            sig = yon_ok & tet
            sw = (pd.Series(l).rolling(p["sw_n"]).min() if y > 0 else pd.Series(h).rolling(p["sw_n"]).max()).to_numpy()
            sd = np.clip(y * (cc - sw), p["stop_min"] * a, p["stop_max"] * a)
            if p["cikis"] == "trend":
                cik = (s_wy != y) | (y * (cc - de15) < 0)
            elif p["cikis"] == "haftalik":
                cik = s_wy != y
            else:
                cik = np.zeros(len(cc), bool)
            SIG[sl, j] = np.where(sig, y, SIG[sl, j]); STOP[sl, j] = np.where(sig, sd, STOP[sl, j])
            # motor: CIKIS == -yön -> çık; long çıkışı -1, short çıkışı +1; ikisi birden 2
            ck = np.where(cik, -y, 0.0)
            CIK[sl, j] = np.where((CIK[sl, j] != 0) & (ck != 0), 2.0, CIK[sl, j] + ck)
    return SIG, STOP, CIK, WY


def calistir(D, p, F=None):
    SIG, STOP, CIK, WY = F if F is not None else ozellikler(D, p)
    S = SIG.copy(); S[D["ONC"] >= p["evren_n"]] = 0
    if p.get("btc_filtre"):                     # piyasa rejimi: işlem yönü BTC'nin haftalık yönüyle aynı olmalı
        jb = D["semboller"].index("BTCUSDT")
        S[S != WY[:, jb:jb + 1]] = 0
    q = dict(p)
    if p["cikis"] == "1R":
        q.update(tp1_r=0.0, hedef_r=1.0)
    elif p["cikis"] == "2R":
        q.update(tp1_r=0.0, hedef_r=2.0)
    return portfoy(D, S, STOP, np.zeros(S.shape), CIK, D["ONC"], q)


def ozetle(e, t):
    out = {}
    for ad, m in (("TÜM", None), ("IS 2020-2023", e.index < KES), ("OOS 2024-2026/09", e.index >= KES)):
        ee = e if m is None else e[m]
        tt = t if m is None else t[(t.giris_zaman < KES) if "IS" in ad else (t.giris_zaman >= KES)]
        out[ad] = metrik(ee, tt)
    return pd.DataFrame(out).T


def izgara():
    import itertools
    SONUC.mkdir(parents=True, exist_ok=True)
    D = gunluk_V()
    satir = []
    for ym, hi, ge, ck in itertools.product(("dok", "ema1020"), (True, False), (True, False), ("1R", "trend", "haftalik")):
        p = dict(TEMEL, yon_mod=ym, hist=hi, geri=ge, cikis=ck)
        e, t = calistir(D, p)
        o = ozetle(e, t)
        r = dict(yon=ym, hist=hi, geri=ge, cikis=ck)
        for per, k in (("IS 2020-2023", "is"), ("OOS 2024-2026/09", "oos")):
            for m in ("cagr", "maxdd", "sharpe", "islem", "kazanma", "ortR"):
                r[f"{k}_{m}"] = o.loc[per, m]
        satir.append(r); print(r, flush=True)
    d = pd.DataFrame(satir)
    d.to_csv(SONUC / "izgara.csv", index=False)
    pd.set_option("display.width", 250)
    print(d.round(2).to_string(index=False))


def _satir(D, ad, p):
    e, t = calistir(D, p)
    o = ozetle(e, t)
    r = dict(varyant=ad)
    for per, k in (("IS 2020-2023", "is"), ("OOS 2024-2026/09", "oos")):
        for m in ("cagr", "maxdd", "sharpe", "islem", "kazanma", "ortR"):
            r[f"{k}_{m}"] = o.loc[per, m]
    return r, e, t


def izgara2():
    """2. tur: evren genişliği, BTC rejim filtresi, long/short, geri çekilme seviyesi (kaydırmasız)."""
    D = gunluk_V()
    B = dict(TEMEL, hist=False, geri=False)
    V = {}
    for ck in ("haftalik", "trend"):
        for ym in ("dok", "ema1020"):
            b = dict(B, yon_mod=ym, cikis=ck)
            V[f"{ym}/{ck}"] = b
            V[f"{ym}/{ck} BTC filtresi"] = dict(b, btc_filtre=True)
            V[f"{ym}/{ck} evren 5"] = dict(b, evren_n=5, max_poz=3, max_yon=3)
            V[f"{ym}/{ck} evren 10"] = dict(b, evren_n=10, max_poz=4, max_yon=4)
            V[f"{ym}/{ck} long+short"] = dict(b, yon=0)
            V[f"{ym}/{ck} long+short BTC f."] = dict(b, yon=0, btc_filtre=True)
            V[f"{ym}/{ck} geri EMA5 kaydırmasız"] = dict(b, geri=True, geri_kay=0, geri_n=5)
    satir = []
    for ad, p in V.items():
        r, _, _ = _satir(D, ad, p); satir.append(r); print(r["varyant"], round(r["is_sharpe"], 2), round(r["oos_sharpe"], 2), flush=True)
    d = pd.DataFrame(satir); d.to_csv(SONUC / "izgara2.csv", index=False)
    pd.set_option("display.width", 250)
    print(d.round(2).to_string(index=False))


if __name__ == "__main__":
    {"izgara": izgara, "izgara2": izgara2}[sys.argv[1]]()
