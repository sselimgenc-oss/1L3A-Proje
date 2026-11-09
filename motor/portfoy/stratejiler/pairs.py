"""Çift işlemi (pairs / istatistiksel arbitraj) ailesi: tek sınıf, `yontem` parametresiyle.

Yöntemler: "eg" (Engle-Granger), "johansen", "kalman", "mesafe" (normalize fiyat mesafesi), "oran_sma" (oran / SMA).

LOOK-AHEAD DÜZELTMELERİ (kaynaklardaki hatalar)
  - Engle-Granger kaynağı (je-suis-tm "Pair trading backtest.py"): pozisyon büyüklüğü `capital0 // max(fiyat)` ile TÜM
    dönemin en yüksek fiyatından hesaplanıyordu (ileri bakış). Burada bacak ağırlıkları yalnız GİRİŞ anındaki hedge
    oranından (geçmiş pencereden) ve sabit `brut_cift` payından gelir; hiçbir tam-örneklem istatistiği yok.
  - Aynı kaynakta z bandı kointegrasyon başladığı günün z değeri +- artık std olarak tutarsız birimle sabitleniyordu;
    burada z = (spread - pencere ortalaması) / pencere std'si, yalnız t'ye kadar olan pencereden.
  - Kalman: gözlem gürültüsü yenilik karelerinin üstel ortalamasıyla uyarlanır (kaynağın sabit Ve'si fiyat düzeyi içindir).
  - Hedge oranı (OLS beta / Johansen vektörü / Kalman durumu) ve ortalama/std yalnız t'de biten kayan pencereden;
    kointegrasyon testi de yalnız o pencereden (test_aralik günde bir yenilenir; ADF kritik değeri Engle-Granger
    (MacKinnon) değeridir, standart ADF -2.86 DEĞİL: artık tahmin edildiği için standart ADF anti-muhafazakârdır).

Spread ve bacaklar
  spread = ln(A) - beta*ln(B). pos=+1: A long, B short. Bacak ağırlıkları (giriş anında sabitlenir, pozisyon boyunca
  değişmez -> boşuna işlem ve zararda büyütme yok): w_A = pos*brut_cift/(1+|beta|), w_B = -pos*brut_cift*beta/(1+|beta|)
  (|w_A|+|w_B| = brut_cift; dolar-nötre yakın). Birden çok çift aynı sembolü paylaşırsa ağırlıklar toplanır ve +-1'e kırpılır.
  Giriş |z| >= giris_z (ve < stop_z), çıkış |z| <= cikis_z (ortalamaya dönüş) ya da max_tutma gün; "z-skor stopu":
  |z| >= stop_z -> iki bacak da kapanır ve |z| giris_z altına inene kadar yeniden girilmez. Kointegrasyon (eg/johansen)
  kaybolursa pozisyon kapanır. Motorun zorunlu stopu: HER BACAĞA ATR felaket stopu (atr_k * ATR; PfTemel.stoplar);
  spread stopu bacak stoplarına çevrilmez (iki bacağın fiyat stopu spread stopuyla örtüşmez), bunun yerine z-skor stopu
  hedefleri sıfırlar, bacak felaket stopları ise z stopuna ulaşılamayan ani şoklar içindir.

Pencereler "çift günü" cinsindendir: çiftin en az bir bacağının mumu olan günler (hisse çiftlerinde işlem günleri,
kriptoda her gün).
"""
from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd

from motor.portfoy.stratejiler.ortak import HEPSI, ORTAK_PARAMETRELER, PfTemel, degisim_satirlari

DEFAULT_CIFTLER = (
    # Kripto: aynı varlık sınıfı, yüksek korelasyon (iktisadi yakınlık).
    ("BTCUSDT", "ETHUSDT"), ("ETHUSDT", "SOLUSDT"), ("BTCUSDT", "SOLUSDT"),
    # Hisse: aynı sektör / benzer iş modeli (büyük teknoloji).
    ("DK_GOOGL", "DK_MSFT"), ("DK_AAPL", "DK_MSFT"), ("DK_GOOGL", "DK_META"), ("DK_AMZN", "DK_MSFT"),
    # Emtia: döngüsel emtialar / altın-bakır (talimat: XAU/COPPER); WTI-bakır döngüsel çift.
    ("DK_XAU", "DK_COPPER"), ("DK_WTI", "DK_COPPER"),
)
EG_KRITIK = -3.34           # Engle-Granger 2 değişken, sabitli, %5 (MacKinnon asimptotik)
JOHANSEN_KRITIK = 15.4943   # iz istatistiği r=0, 2 değişken, %5 (sabit, gecikme farkı 1)


# ------------------------------------------------------------------ istatistik yardımcıları
def ols_cizgi(x: np.ndarray, y: np.ndarray) -> tuple:
    """y = a + b x -> (a, b, artik)."""
    xm, ym = x.mean(), y.mean()
    vx = ((x - xm) ** 2).sum()
    b = ((x - xm) * (y - ym)).sum() / vx if vx > 0 else np.nan
    a = ym - b * xm
    return a, b, y - a - b * x


def adf_t(e: np.ndarray, lag: int = 1) -> float:
    """Artığın birim kök t istatistiği: de_t = c + g e_{t-1} + sum phi de_{t-j} (g'nin t'si). Sabit seri -> nan."""
    e = np.asarray(e, dtype=float)
    if len(e) < lag + 10 or np.ptp(e) == 0:
        return math.nan
    de = np.diff(e)
    y = de[lag:]
    cols = [np.ones(len(y)), e[lag:-1]]
    for j in range(1, lag + 1):
        cols.append(de[lag - j:len(de) - j])
    X = np.column_stack(cols)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    dof = len(y) - X.shape[1]
    if dof <= 0:
        return math.nan
    s2 = (res ** 2).sum() / dof
    try:
        cov = s2 * np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        return math.nan
    se = math.sqrt(cov[1, 1]) if cov[1, 1] > 0 else math.nan
    return float(beta[1] / se) if se and se > 0 else math.nan


def johansen_iki(y: np.ndarray) -> tuple:
    """2 değişkenli Johansen (VECM, 1 gecikme farkı, sabitli). y: (T,2). -> (iz_istatistigi r=0, hedge_beta).
    Spread = y0 - beta*y1 (beta = -v1/v0, ilk özvektör)."""
    y = np.asarray(y, dtype=float)
    dy = np.diff(y, axis=0)
    Y0, Y1 = dy[1:], y[1:-1]
    Z = np.column_stack([dy[:-1], np.ones(len(Y0))])

    def artik(Y):
        b, *_ = np.linalg.lstsq(Z, Y, rcond=None)
        return Y - Z @ b

    R0, R1 = artik(Y0), artik(Y1)
    T = len(R0)
    S00, S11, S01 = R0.T @ R0 / T, R1.T @ R1 / T, R0.T @ R1 / T
    try:
        M = np.linalg.inv(S11) @ S01.T @ np.linalg.inv(S00) @ S01
        w, v = np.linalg.eig(M)
    except np.linalg.LinAlgError:
        return math.nan, math.nan
    w, v = np.real(w), np.real(v)
    sira = np.argsort(-w)
    w, v = w[sira], v[:, sira]
    lam = np.clip(w, 0.0, 1.0 - 1e-12)
    iz = float(-T * np.log(1.0 - lam).sum())
    beta = float(-v[1, 0] / v[0, 0]) if v[0, 0] != 0 else math.nan
    return iz, beta


def kalman_hata(la: np.ndarray, lb: np.ndarray, delta: float, ve: float, ewma_pencere: int = 0) -> tuple:
    """Chan Kalman: ln A = beta ln B + alfa. Durum [beta, alfa], rastgele yürüyüş (Vw = delta/(1-delta) I).
    Her t için (e_t, sqrt(Q_t), beta_tahmin) : tahmin t-1'e kadar olan bilgiyle yapılır (nedensel), sonra güncellenir.
    ewma_pencere > 0: gözlem gürültüsü Ve, geçmiş yenilik karelerinin (e_{t-1}^2) üstel ortalamasıyla uyarlanır
    (alfa = 2/(pencere+1); başlangıç `ve`). Kaynaktaki sabit Ve=1e-3 FİYAT DÜZEYİ içindir; log fiyatlarda spread
    ölçeği çiftten çifte çok değiştiğinden sabit Ve beta'yı spread'e kilitleyip z'yi bozar."""
    n = len(la)
    theta = np.zeros(2)
    P = np.zeros((2, 2))
    vw = delta / (1.0 - delta) * np.eye(2)
    e = np.full(n, np.nan)
    sq = np.full(n, np.nan)
    bt = np.full(n, np.nan)
    ilk = True
    ve_t = ve
    lam = 2.0 / (ewma_pencere + 1.0) if ewma_pencere > 0 else 0.0
    for t in range(n):
        if not (np.isfinite(la[t]) and np.isfinite(lb[t])):
            continue
        if ilk:
            theta[:] = [1.0, la[t] - lb[t]]
            P = np.eye(2) * 1.0
            ilk = False
        x = np.array([lb[t], 1.0])
        R = P + vw
        yhat = float(x @ theta)
        Q = float(x @ R @ x) + ve_t
        et = la[t] - yhat
        e[t], sq[t], bt[t] = et, math.sqrt(Q), theta[0]
        if lam > 0:
            ve_t = (1.0 - lam) * ve_t + lam * et * et
        K = R @ x / Q
        theta = theta + K * et
        P = R - np.outer(K, x) @ R
    return e, sq, bt


class Pairs(PfTemel):
    """Çift işlemi (bkz. modül docstring'i). Ayrıntılar orada.

    Kaynaklar: ek77 Engle-Granger kointegrasyon çift işlemi (je-suis-tm), ArbitrageLab Kalman pairs (Chan), liste8
    Pairs pipeline (Chan/QuantRocket, Johansen), awesome: Çift işlemi mesafe (120g/5 çift/0,5sd ve 365g/20 çift/2sd),
    awesome: ETH/BTC yayılımı 20g SMA, jesuistm JT_Pair_trading (tüm çift kombinasyonları).

    ÇİFT SEÇİMİ (belgelenmiş, OOS görülmeden, iktisadi yakınlıkla): `DEFAULT_CIFTLER` (kripto 3 çift, büyük teknoloji
    hisseleri 4 çift, XAU/COPPER ve WTI/COPPER). `ciftler="otomatik"` evrendeki tüm kombinasyonları dener (kointegrasyon
    testi seçer; mesafe yönteminde SSD sırası ve max_cift). Yalnız iki bacağı da evrende olan çiftler kullanılır.

    d11j EK YÖNTEM (varsayılan "eg" değişmez; ızgarada yok, ayar kaydıyla denenir): yontem="dunku_getiri" -> long-only: her çiftte günün kapanışında iki
    bacağın GÜNLÜK getirisi (bugün/dün) karşılaştırılır, getirisi DÜŞÜK olan bacak ertesi gün tutulur (brut_cift payı; her gün yeniden seçilir;
    kısa bacak yok); koşul: iki bacağın son `kor_gun` (19) günlük getiri korelasyonu < `kor_esik` (0.9) ise işlem (kaynakta korelasyon < 0.9 giriş
    kapısıdır), değilse o çift o gün düz. Kaynağın "9 pencere boyunca" ifadesi
    tek pencereye indirildi (yaklaşık). KO/PEP evrende yok: kripto/hisse çiftleriyle denenir; sonuçlar kaynağın iddiasını doğrulamaz.
    """

    ad = "pf__pairs"
    min_sembol = 2
    varsayilan_parametreler = {
        **ORTAK_PARAMETRELER, "semboller": HEPSI, "ciftler": DEFAULT_CIFTLER, "yontem": "eg", "pencere": 250,
        "giris_z": 2.0, "cikis_z": 0.5, "stop_z": 4.0, "test_aralik": 5, "max_tutma": 90, "brut_cift": 0.5,
        "max_cift": 5, "beta_min": 0.2, "beta_max": 5.0, "adf_lag": 1, "kalman_delta": 1e-4, "kalman_ve": 1e-3,
        "yon_modu": "donus", "atr_k": 4.0, "kor_gun": 19, "kor_esik": 0.9}
    parametre_izgarasi = {"yontem": ["eg", "johansen", "kalman"], "giris_z": [1.0, 1.5, 2.0], "pencere": [120, 250, 365]}

    def cift_listesi(self, kolon) -> list:
        p = self.parametreler
        if p["ciftler"] == "otomatik":
            return list(itertools.combinations(kolon, 2))
        return [(a, b) for a, b in p["ciftler"] if a in kolon and b in kolon]

    def uygun_mu(self, mevcut) -> bool:
        ev = self.etkin_semboller(mevcut)
        return len(self.cift_listesi(ev)) >= 1

    # ---------------------------------------------------------------- tek çift
    def _seri(self, la, lb, gun_no):
        """Bir çift için günlük (z, beta, izin, ssd) dizileri; hepsi t'ye kadar bilgiyle."""
        p = self.parametreler
        n, W = len(la), int(p["pencere"])
        z = np.full(n, np.nan)
        beta = np.full(n, np.nan)
        izin = np.zeros(n, dtype=bool)
        ssd = np.full(n, np.nan)
        yontem = p["yontem"]
        if yontem == "kalman":
            e, sq, bt = kalman_hata(la, lb, p["kalman_delta"], p["kalman_ve"], int(p["pencere"]))
            z, beta = e / sq, bt
            izin[:] = np.isfinite(z)
            izin[:W] = False
            z[:W] = np.nan
            return z, beta, izin, ssd
        if yontem == "oran_sma":
            r = pd.Series(np.exp(la - lb))
            sm, sd = r.rolling(W, min_periods=W).mean(), r.rolling(W, min_periods=W).std()
            z = ((r - sm) / sd).to_numpy()
            beta[:] = 1.0
            izin = np.isfinite(z)
            return z, beta, izin, ssd
        flag, b_k, a_k = False, np.nan, np.nan
        for t in range(W - 1, n):
            ya, xb = la[t - W + 1:t + 1], lb[t - W + 1:t + 1]
            if not (np.isfinite(ya).all() and np.isfinite(xb).all()):
                continue
            if yontem == "mesafe":
                na, nb = np.exp(ya - ya[0]), np.exp(xb - xb[0])
                sp = na - nb
                sd = sp.std(ddof=1)
                ssd[t] = float((sp ** 2).sum())
                if sd > 0:
                    z[t] = (sp[-1] - sp.mean()) / sd
                beta[t] = 1.0
                izin[t] = np.isfinite(z[t])
                continue
            if t == W - 1 or gun_no[t] % int(p["test_aralik"]) == 0:        # test günü: yalnız pencereden
                if yontem == "eg":
                    a_k, b_k, res = ols_cizgi(xb, ya)
                    tt = adf_t(res, int(p["adf_lag"]))
                    flag = bool(np.isfinite(tt) and tt < EG_KRITIK and np.isfinite(b_k))
                elif yontem == "johansen":
                    iz, b_k = johansen_iki(np.column_stack([ya, xb]))
                    flag = bool(np.isfinite(iz) and iz > JOHANSEN_KRITIK and np.isfinite(b_k))
                else:
                    raise ValueError(f"bilinmeyen yontem: {yontem}")
            if flag:
                sp = ya - b_k * xb
                sd = sp.std(ddof=1)
                if sd > 0:
                    z[t] = (sp[-1] - sp.mean()) / sd
                    beta[t] = b_k
                    izin[t] = True
        return z, beta, izin, ssd

    def _durum(self, z, beta, izin, rank_ok):
        """z-skor durum makinesi -> (pos, beta_giris) dizileri (pos in {-1,0,1}: +1 A long/B short)."""
        p = self.parametreler
        n = len(z)
        pos = np.zeros(n)
        bgir = np.full(n, np.nan)
        cur, b0, tut, engel = 0, np.nan, 0, False
        trend = p["yon_modu"] == "trend"
        for t in range(n):
            zt = z[t]
            if cur != 0:
                tut += 1
                cik = False
                if not izin[t] or not np.isfinite(zt):
                    cik = True
                elif trend:
                    cik = (cur == 1 and zt <= p["cikis_z"]) or (cur == -1 and zt >= -p["cikis_z"])
                else:
                    cik = ((cur == -1 and zt <= p["cikis_z"]) or (cur == 1 and zt >= -p["cikis_z"])
                           or abs(zt) >= p["stop_z"])
                    if abs(zt) >= p["stop_z"]:
                        engel = True
                if tut >= p["max_tutma"]:
                    cik = True
                if cik:
                    cur, tut = 0, 0
            else:
                if engel and np.isfinite(zt) and abs(zt) < p["giris_z"]:
                    engel = False
                if (not engel and izin[t] and rank_ok[t] and np.isfinite(zt) and abs(zt) >= p["giris_z"]
                        and (trend or abs(zt) < p["stop_z"]) and p["beta_min"] <= beta[t] <= p["beta_max"]):
                    yon = 1 if zt > 0 else -1
                    cur = yon if trend else -yon
                    b0, tut = beta[t], 0
            pos[t] = cur
            if cur != 0:
                bgir[t] = b0
        # giriş anındaki beta pozisyon boyunca sabit: bgir zaten b0
        return pos, bgir

    def _dunku_getiri(self, kolon, ciftler, tk):
        p = self.parametreler
        r = tk.getiri()
        toplam = pd.DataFrame(0.0, index=tk.gun, columns=kolon)
        for a, b in ciftler:
            kor = r[a].rolling(int(p["kor_gun"]), min_periods=int(p["kor_gun"])).corr(r[b])
            ok = (kor < p["kor_esik"]) & r[a].notna() & r[b].notna()
            zayif_a = r[a] < r[b]
            toplam[a] += np.where(ok & zayif_a, p["brut_cift"], 0.0)
            toplam[b] += np.where(ok & ~zayif_a, p["brut_cift"], 0.0)
        return degisim_satirlari(tk.eksene(toplam.clip(0.0, 1.0)))

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        ciftler = self.cift_listesi(kolon)
        if not ciftler:
            raise ValueError("pf__pairs: evrende iki bacağı da bulunan çift yok")
        if p["yontem"] == "dunku_getiri":
            return self._dunku_getiri(kolon, ciftler, tk)
        logk = np.log(tk.kap[kolon])
        var = tk.panel("kapanis", False)[kolon].notna()
        gun_epoch = ((tk.gun - pd.Timestamp("1970-01-01", tz="UTC")).days).to_numpy().astype(np.int64)
        seriler = {}
        for a, b in ciftler:
            aktif = (var[a] | var[b]).to_numpy() & logk[a].notna().to_numpy() & logk[b].notna().to_numpy()
            idx = np.flatnonzero(aktif)
            if len(idx) < p["pencere"] + 10:
                continue
            la, lb = logk[a].to_numpy()[idx], logk[b].to_numpy()[idx]
            z, beta, izin, ssd = self._seri(la, lb, gun_epoch[idx])
            seriler[(a, b)] = (idx, z, beta, izin, ssd)
        # mesafe yöntemi: SSD sırası (günlük, çiftler arası) -> yalnız en yakın max_cift çift yeni giriş yapabilir
        rank_tablo = {}
        if p["yontem"] == "mesafe" and seriler:
            ssd_df = pd.DataFrame({k: pd.Series(v[4], index=tk.gun[v[0]]) for k, v in seriler.items()}).reindex(tk.gun)
            rk = ssd_df.rank(axis=1, method="first")
            rank_tablo = {k: (rk[k] <= p["max_cift"]).fillna(False).to_numpy() for k in seriler}
        toplam = pd.DataFrame(0.0, index=tk.gun, columns=kolon)
        for (a, b), (idx, z, beta, izin, ssd) in seriler.items():
            rok = rank_tablo[(a, b)][idx] if rank_tablo else np.ones(len(idx), dtype=bool)
            pos, bgir = self._durum(z, beta, izin, rok)
            wa = np.where(pos != 0, pos * p["brut_cift"] / (1.0 + np.abs(bgir)), 0.0)
            wb = np.where(pos != 0, -pos * p["brut_cift"] * bgir / (1.0 + np.abs(bgir)), 0.0)
            # çift günleri dışındaki günlerde durum bir önceki çift gününden taşınır (ileri doldurma)
            sa = pd.Series(wa, index=tk.gun[idx]).reindex(tk.gun).ffill().fillna(0.0)
            sb = pd.Series(wb, index=tk.gun[idx]).reindex(tk.gun).ffill().fillna(0.0)
            toplam[a] += sa
            toplam[b] += sb
        toplam = toplam.clip(-1.0, 1.0)
        return degisim_satirlari(tk.eksene(toplam))
