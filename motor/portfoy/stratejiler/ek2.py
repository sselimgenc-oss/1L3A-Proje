"""portfoy_adaylari.csv'de pf_sinif'i boş kalan satırlardan kodlanabilenler (2026-11-07, karar 23c + karar 27 evreni).

pf__pca_statarb  — ek77 #55 ArbitrageLab PCA stat-arb (Avellaneda-Lee 2010). Kural özü (kendi kodumuz, kopya yok):
  korelasyon matrisinin ilk `n_faktor` özvektöründen özportföyler (Q_j,i = v_j,i / sigma_i), son `regres_gun` günde hisse
  getirisinin faktör getirilerine OLS'u (beta), kalıntıların toplamı X'in AR(1)'i -> OU: kappa = -ln(b)*252,
  s = (X_son - m) / sigma_eq. s < -giris_long -> long, s > giris_short -> short; long'u s > -cik_long, short'u
  s < cik_short olunca kapat; kappa < kappa_min olan hisse giriş almaz (hızlı ortalamaya dönüş şartı). Bir pozisyon
  = hisse eksi onun faktör betalarıyla özportföy hedge'i (faktör-nötr). Sapmalar (belgeli): kaynak ~15 özportföy
  / ~170+ hisse; evren 18 hisse olduğu için n_faktor=3 (ızgarada 2/3/4); "m düzeltmesi" (sürüklenme terimi) yok;
  hacim-zamanı yok; günlük kapanış; pencereler İŞLEM GÜNÜ (satır) cinsindendir (hisse eksenine karşılık gelir).
  Ağırlık: bacak başı 1/max_poz birim, toplam brüt <= `brut` (varsayılan 1.0). Hedge her `takvim` döneminde ya da
  pozisyon kümesi değişince yenilenir.

pf__gumus_makro  — tv: Silver Always Long + Macro Exit + Flush Protection v2 (CuriousMacroX). Kural özü: gümüşte hep
  long; çıkış: kapanış < EMA(150), ya da makro stres `makro_bar` bar üst üste, ya da "flush" (1 gün <= -%4,5, 2 gün
  <= -%8 ya da menzil > 1,8 x ATR% ve kapanış < açılış). Yeniden giriş: EMA150 üstü + makro sakin + flush sonrası
  toparlanma (flush'tan en geç 3 bar içindeyse: kapanış > EMA(75) ve 2 bar volatilite sakin). Makro VEKİL: kaynakta ABD
  10Y getiri (TVC:US10Y) ve DXY var; evrende yalnız DK_UST (ABD T-Bond CFD FİYATI) var: getiri yükselişi = fiyat düşüşü
  -> stres = UST kapanışı EMA(50)'nin `ust_esik_yuzde` (varsayılan %0,9; getiride kaynaktaki %1,35'in ~17 vadeli
  tahvil fiyat karşılığı, TAHMİN) altında VE önceki 20 günün en düşüğünün altında. DXY yok (kaynakta varsayılan kapalı).
  Evren (karar 27 emtia): DK_XAG. Kaynak yalnız long (hiç short yok).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.portfoy.stratejiler.ortak import ORTAK_PARAMETRELER, PfTemel, ema_gun, tetik_satirlari
from motor.strateji import gostergeler as gst

HISSE18 = ("DK_AAPL", "DK_NVDA", "DK_MSFT", "DK_GOOGL", "DK_AMZN", "DK_META", "DK_TSLA", "DK_AVGO", "DK_LLY",
           "DK_WMT", "DK_JPM", "DK_V", "DK_MU", "DK_AMD", "DK_XOM", "DK_JNJ", "DK_MA", "DK_ABBV")


# ------------------------------------------------------------------ PCA stat-arb
def _ou_s_skorlari(R: np.ndarray, n_faktor: int, regres_gun: int):
    """R: (T, N) tam dolu getiri penceresi (son satır = bugün). -> (s, kappa, beta (nf, N), Q (nf, N))."""
    T, N = R.shape
    sd = R.std(axis=0, ddof=1)
    sd = np.where(sd > 1e-12, sd, np.nan)
    if np.isnan(sd).any():
        return None
    Y = (R - R.mean(axis=0)) / sd
    C = np.corrcoef(Y, rowvar=False)
    w, v = np.linalg.eigh(C)
    v = v[:, np.argsort(w)[::-1][:n_faktor]]                       # (N, nf) en büyük özdeğerler
    Q = (v / sd[:, None]).T                                        # (nf, N): özportföy ağırlıkları
    Rw = R[-regres_gun:]
    F = Rw @ Q.T                                                   # (regres_gun, nf) faktör getirileri
    X = np.column_stack([np.ones(len(Rw)), F])
    coef, *_ = np.linalg.lstsq(X, Rw, rcond=None)                  # (1+nf, N)
    eps = Rw - X @ coef
    beta = coef[1:]
    kum = np.cumsum(eps - eps.mean(axis=0), axis=0)                # ortalaması çıkarılmış kalıntı toplamı
    x0, x1 = kum[:-1], kum[1:]
    xm0, xm1 = x0.mean(axis=0), x1.mean(axis=0)
    var0 = ((x0 - xm0) ** 2).sum(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        b = ((x0 - xm0) * (x1 - xm1)).sum(axis=0) / var0
        a = xm1 - b * xm0
        zeta = x1 - (a + b * x0)
        sig2 = zeta.var(axis=0, ddof=1) / (1.0 - b ** 2)
        m = a / (1.0 - b)
        kappa = -np.log(b) * 252.0
        s = (kum[-1] - m) / np.sqrt(sig2)
    gecerli = (b > 0.0) & (b < 1.0) & np.isfinite(s)
    s = np.where(gecerli, s, np.nan)
    kappa = np.where(gecerli, kappa, np.nan)
    return s, kappa, beta, Q


class PcaStatArb(PfTemel):
    ad = "pf__pca_statarb"
    min_sembol = 6
    varsayilan_parametreler = {
        **ORTAK_PARAMETRELER, "semboller": HISSE18, "n_faktor": 3, "korel_gun": 252, "regres_gun": 60,
        "giris_long": 1.25, "giris_short": 1.25, "cik_long": 0.5, "cik_short": 0.75, "kappa_min": 8.4,
        "max_poz": 4, "brut": 1.0, "takvim": "W"}
    parametre_izgarasi = {"n_faktor": [2, 3, 4], "giris_long": [1.0, 1.25, 1.5], "regres_gun": [40, 60, 90]}

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        n = len(kolon)
        nf, L, M = int(p["n_faktor"]), int(p["korel_gun"]), int(p["regres_gun"])
        if nf < 1 or nf >= n - 1 or M <= nf + 5 or L < M:
            raise ValueError("pca_statarb: 1 <= n_faktor < semboller-1, regres_gun > n_faktor+5 ve korel_gun >= regres_gun olmalı")
        ax = tk.eksen
        kap = tk.eksene(tk.kap[kolon]).to_numpy(dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            R = kap[1:] / kap[:-1] - 1.0
        R = np.vstack([np.full((1, n), np.nan), R])
        hazir = np.zeros(len(ax), dtype=bool)
        hazir[L:] = True
        tetik = tetik_satirlari(ax, p["takvim"], hazir)
        h = np.full((len(ax), n), np.nan)
        elde = np.zeros(n)                                         # +1 long, -1 short, 0 yok
        for i in range(L, len(ax)):
            pencere = R[i - L + 1:i + 1]
            tam = ~np.isnan(pencere).any(axis=0)
            degisti = False
            if tam.sum() >= max(nf + 3, 6):
                idx = np.flatnonzero(tam)
                sonuc = _ou_s_skorlari(pencere[:, idx], nf, M)
            else:
                sonuc = None
            if sonuc is None:
                yeni = np.zeros(n)                                 # skor hesaplanamıyorsa mevcut pozisyonlar kapanır
                s = np.full(n, np.nan)
            else:
                s_k, kappa_k, beta_k, Q_k = sonuc
                s = np.full(n, np.nan)
                kappa = np.full(n, np.nan)
                s[idx], kappa[idx] = s_k, kappa_k
                yeni = elde.copy()
                for j in range(n):
                    if not np.isfinite(s[j]):
                        yeni[j] = 0.0
                    elif elde[j] > 0 and s[j] > -p["cik_long"]:
                        yeni[j] = 0.0
                    elif elde[j] < 0 and s[j] < p["cik_short"]:
                        yeni[j] = 0.0
                    elif elde[j] == 0 and kappa[j] >= p["kappa_min"]:
                        if s[j] < -p["giris_long"]:
                            yeni[j] = 1.0
                        elif s[j] > p["giris_short"]:
                            yeni[j] = -1.0
                aktif = np.flatnonzero(yeni != 0)
                if len(aktif) > int(p["max_poz"]):                 # en güçlü |s| ilk max_poz; mevcutlar öncelikli
                    oncelik = sorted(aktif, key=lambda j: (elde[j] == 0, -abs(s[j])))
                    for j in oncelik[int(p["max_poz"]):]:
                        yeni[j] = 0.0
            degisti = bool((yeni != elde).any())
            elde = yeni
            if not (degisti or tetik[i]):
                continue
            w = np.zeros(n)
            if sonuc is not None:
                for j in np.flatnonzero(elde != 0):
                    k = int(np.flatnonzero(idx == j)[0])
                    bacak = np.zeros(n)
                    bacak[idx] = -(beta_k[:, k] @ Q_k)             # özportföy hedge'i (faktör-nötr)
                    bacak[j] += 1.0
                    w += elde[j] * bacak
                brut = np.abs(w).sum()
                if brut > 0:
                    w = w / brut * min(p["brut"], len(np.flatnonzero(elde)) * p["brut"] / int(p["max_poz"]))
            h[i] = w
        return pd.DataFrame(h, index=ax, columns=kolon)


# ------------------------------------------------------------------ gümüş makro
def _kalici(kosul: np.ndarray, bar: int) -> np.ndarray:
    """Son `bar` barın hepsinde doğru (nedensel; ilk bar-1 satır yanlış)."""
    s = pd.Series(kosul.astype(float))
    return (s.rolling(bar, min_periods=bar).min() == 1.0).to_numpy()


class GumusMakro(PfTemel):
    ad = "pf__gumus_makro"
    min_sembol = 1
    varsayilan_parametreler = {
        **ORTAK_PARAMETRELER, "semboller": ("DK_XAG",), "makro_sembol": "DK_UST", "ema_yavas": 150, "ema_toparlanma": 75,
        "tampon_yuzde": 0.0, "makro_ema": 50, "makro_ust_yuzde": 0.9, "makro_kirilim_gun": 20, "makro_bar": 3,
        "yeniden_bar": 1, "flush_1g": 4.5, "flush_2g": 8.0, "atr_gun": 14, "atr_sok": 1.8, "flush_bekle": 3,
        "sakin_bar": 2, "takvim": "D"}
    parametre_izgarasi = {"ema_yavas": [100, 150, 200], "makro_ust_yuzde": [0.6, 0.9, 1.2], "flush_1g": [3.5, 4.5, 5.5]}

    def ek_semboller(self):
        return (self.parametreler["makro_sembol"],)

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        if len(kolon) != 1:
            raise ValueError("pf__gumus_makro tek enstrümanlıdır (semboller bir eleman)")
        s = kolon[0]
        ax = tk.eksen
        D = lambda x: np.asarray(tk.eksene(x), dtype=float)
        c = D(tk.kap[s])
        o, hi, lo = D(tk.panel("acilis")[s]), D(tk.panel("yuksek")[s]), D(tk.panel("dusuk")[s])
        yavas = D(ema_gun(tk.kap[[s]], int(p["ema_yavas"]))[s])
        toparlan = D(ema_gun(tk.kap[[s]], int(p["ema_toparlanma"]))[s])
        hazir = np.isfinite(c) & np.isfinite(yavas) & np.isfinite(toparlan)
        with np.errstate(invalid="ignore", divide="ignore"):
            trend_cik = c < yavas * (1.0 - p["tampon_yuzde"] / 100.0)
            gun1 = c / np.r_[np.nan, c[:-1]] - 1.0
            gun2 = c / np.r_[np.nan, np.nan, c[:-2]] - 1.0
        atr = gst.atr(tk.panel("yuksek")[s], tk.panel("dusuk")[s], tk.kap[s], int(p["atr_gun"]))
        atr_yuzde = D(atr) / c * 100.0
        with np.errstate(invalid="ignore", divide="ignore"):
            menzil = (hi - lo) / c * 100.0
            sok = (menzil > atr_yuzde * p["atr_sok"]) & (c < o)
            flush_simdi = (gun1 <= -p["flush_1g"] / 100.0) | (gun2 <= -p["flush_2g"] / 100.0) | sok
        flush_simdi = np.where(hazir, flush_simdi, False)
        if p["makro_sembol"]:
            m = p["makro_sembol"]
            mk = tk.kap[m]
            me = mk.ewm(span=int(p["makro_ema"]), adjust=False, min_periods=int(p["makro_ema"])).mean()
            alt_onceki = tk.panel("dusuk")[m].shift(1).rolling(int(p["makro_kirilim_gun"]),
                                                               min_periods=max(5, int(p["makro_kirilim_gun"] * 0.6))).min()
            stres = ((mk < me) & ((me - mk) / me * 100.0 > p["makro_ust_yuzde"]) & (mk < alt_onceki))
            makro_hazir = D(me.notna() & alt_onceki.notna()).astype(bool)
            stres = D(stres).astype(bool) & makro_hazir
            sakin = ~stres
        else:
            makro_hazir = np.ones(len(ax), dtype=bool)
            stres = np.zeros(len(ax), dtype=bool)
            sakin = np.ones(len(ax), dtype=bool)
        hazir = hazir & makro_hazir
        stres_kalici = _kalici(stres, int(p["makro_bar"]))
        sakin_kalici = _kalici(sakin, int(p["yeniden_bar"]))
        with np.errstate(invalid="ignore", divide="ignore"):
            vol_sakin = np.where(hazir, menzil <= atr_yuzde * p["atr_sok"], True)
        vol_kalici = _kalici(vol_sakin, int(p["sakin_bar"]))
        son_flush = np.full(len(ax), 10 ** 9)
        sayac = 10 ** 9
        for i in range(len(ax)):
            sayac = 0 if flush_simdi[i] else sayac + 1
            son_flush[i] = sayac
        yakin_flush = son_flush <= int(p["flush_bekle"])
        toparlandi = (~yakin_flush) | ((c > toparlan) & vol_kalici)
        h = np.full((len(ax), 1), np.nan)
        pozisyon = False
        ilk = True
        for i in np.flatnonzero(hazir):
            onceki = pozisyon
            if onceki and (trend_cik[i] or stres_kalici[i] or flush_simdi[i]):
                pozisyon = False
            elif (not onceki) and (not trend_cik[i]) and sakin_kalici[i] and toparlandi[i]:
                pozisyon = True
            if ilk or pozisyon != onceki:
                h[i, 0] = 1.0 if pozisyon else 0.0
                ilk = False
        return pd.DataFrame(h, index=ax, columns=kolon)


BAGLAMA_EK2 = [
    dict(satir=3, ad_basi="Clenow Stocks", sinif="pf__rotasyon",
         ayar=dict(semboller=HISSE18, skor="regresyon", lookback_gun=90, trend_sma=100, gap_filtre=0.15, k=4, takvim="W",
                   agirlik="ters_vol", mutlak=False, rejim_sembol="DK_SPX", rejim_sma=200),
         not_="S&P 500 -> karar 27 evreni 18 ABD hisse (bugünkü liste sabit; nokta zamanlı üyelik yok = hayatta kalma yanlılığı); "
              "üst %20 ~ k=4; endeks filtresi 'SMA10>SMA200' yerine DK_SPX kapanış > SMA200 (rejim tek SMA); ATR boyutu -> ters-vol; "
              "haftalık dengeleme (kaynakta iki haftalık boyut yenileme yok)."),
    dict(satir=9, ad_basi="ArbitrageLab P", sinif="pf__pca_statarb",
         ayar=dict(semboller=HISSE18, n_faktor=3, korel_gun=252, regres_gun=60, giris_long=1.25, giris_short=1.25,
                   cik_long=0.5, cik_short=0.75, kappa_min=8.4, max_poz=4, brut=1.0, takvim="W"),
         not_="Kaynak ~170 hisse / 15 özportföy; evren 18 hisse -> n_faktor=3 (uyarlama, tahmin); s-skoru eşikleri kaynaktan "
              "(-1,25/+1,25/-0,5/+0,75); sürüklenme (m) düzeltmesi yok; en çok 4 bacak, brüt 1x."),
    dict(satir=22, ad_basi="tv: Silver Alw", sinif="pf__gumus_makro",
         ayar=dict(semboller=("DK_XAG",), makro_sembol="DK_UST"),
         not_="Makro faiz tetiği için VEKİL: DK_UST (T-Bond CFD fiyatı; getiri artışı = fiyat düşüşü), eşik %0,9 TAHMİN (kaynak %1,35 getiri "
              "~ vade 17 ile); DXY kapalı (kaynakta da varsayılan kapalı). Gümüş DK_XAG (karar 27)."),
]
