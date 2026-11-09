"""Kaldıraç testi: KGT v3, KMN ve KGT %50 + KMN %50 (nihai parametreler, aynı işlemler).

Senaryolar (L = 1; 1,5; 2; 3; 5):
  (a) Aynı risk: pozisyon büyüklükleri değişmez, kaldıraç yalnız teminatı azaltır (izole teminat = notional / L).
      Tasfiye mesafesi = 1/L - %0,5 (bakım teminatı). KGT: stop bundan uzaksa ve fiyat (1S dip/tepe) stoptan önce
      tasfiye seviyesine değerse işlem tasfiye olur, kayıp = teminatın tamamı (notional / L), işlem kârlı kapanacak
      olsa bile. 1R kısmi kârdan sonra stop başabaşa çekildiği için tasfiye riski kalkar.
      KMN: her coin pozisyonu için dengelemeden sonraki tutma süresinde günlük en kötü fiyat (1S'lerden günlük dip/tepe)
      tasfiye seviyesine değerse o pozisyonun teminatı kaybedilir, pozisyon bir sonraki dengelemeye kadar kapalı kalır.
      Dengelemede pozisyonlar yeniden teminatlandırılır (tasfiye referansı = dengeleme fiyatı).
  (b) Büyütme: KGT işlem riski, tek pozisyon ve brüt sınırı x L; KMN brüt maruziyet x L; tasfiye kontrolü (a) ile aynı.
Fonlama: Binance USDT-M gerçek fonlama oranları (veri setindeki; OKX geçmişine bu ortamdan erişim yok).
Sonuçlar: sonuclar/kaldirac/ozet.csv, KALDIRAC.md.

Kullanım: python3 -m backtest.kaldirac
"""
from pathlib import Path
import numpy as np
import pandas as pd
from . import kripto_final as KF, kripto_strateji as ks, momentum as M
from .kripto_motor import metrik

KOK = Path(__file__).resolve().parent.parent
SONUC = KOK / "sonuclar" / "kaldirac"
LER = (1.0, 1.5, 2.0, 3.0, 5.0)
BAKIM = 0.005
KMN = dict(mod="notr", N=30, L=14, S=0, K=5, H=14, agirlik="ters_oyn", skor="risk", gecmis_gun=90, kayma=True)


def tasfiye_d(L):
    return 1.0 / L - BAKIM


# ---------------- KGT ----------------
def kgt(V, F, sinyaller, L, senaryo):
    """6 gün başlangıçlı topluluk; günlük getiri serisi ve işlemler."""
    rs, ts = [], []
    for gb in KF.GUN_BASLARI:
        SIG, STOP = sinyaller[gb]
        be = KF.be_dizisi(V, gb)
        q = dict(KF.KGT) if be is None else dict(KF.KGT, ici_sira=3, BEZ=be)
        if L > 1:
            q.update(tasfiye_d=tasfiye_d(L), kaldirac=L)
            if senaryo == "b":
                q.update(risk=q["risk"] * L, max_pay=q["max_pay"] * L, max_brut=q["max_brut"] * L)
        e, t = KF.calistir(V, q, SIG=SIG, STOP=STOP, F=F)
        rs.append(e.resample("1D").last().pct_change().fillna(0)); t["gun_bas"] = gb; ts.append(t)
    return pd.concat(rs, axis=1).fillna(0).mean(axis=1), pd.concat(ts)


# ---------------- KMN ----------------
def kmn_kayma(D, W, olcek, L, maliyet=M.MALIYET, fiyat="hl"):
    """momentum.getiri_kayma ile aynı muhasebe (dolar bazında), artı izole teminat tasfiyesi.
    Döndürür: günlük getiri, tasfiye sayısı, pozisyon başına tutma süresindeki en kötü ters hareket listesi."""
    C = D["C"]; Cn = C.to_numpy()
    Hn = D["H"].to_numpy(); Ln = D["L"].to_numpy()
    if fiyat == "kapanis":          # duyarlılık: tasfiye günlük kapanışla (işaret fiyatı iğneleri yumuşatır)
        Hn = Ln = Cn
    hedef = W.to_numpy() * olcek
    dg = np.r_[True, (np.abs(np.diff(hedef, axis=0)).sum(axis=1) > 0)]
    dg &= np.abs(hedef).sum(axis=1) > 0
    r1 = (C.shift(-1) / C - 1).fillna(0.0).to_numpy()
    F1 = D["F"].shift(-1).fillna(0).to_numpy()
    T, N = Cn.shape
    d = tasfiye_d(L) if L > 1 else np.inf
    deger = 1.0
    p = np.zeros(N)                 # pozisyon değeri (işaretli, defter birimi)
    giris = np.full(N, np.nan); teminat = np.zeros(N); en_kotu = np.zeros(N)
    net = np.zeros(T); n_tas = 0; mae = []
    for t in range(T):
        devir = 0.0
        if dg[t]:
            for j in np.flatnonzero(p != 0):
                mae.append(en_kotu[j])
            yeni = hedef[t] * deger
            devir = np.abs(yeni - p).sum()
            p = yeni.copy()
            giris = np.where(p != 0, Cn[t], np.nan); teminat = np.abs(p) / L; en_kotu = np.zeros(N)
        pnl = -devir * maliyet
        if t + 1 < T:
            ac = np.flatnonzero(p != 0)
            for j in ac:
                y = 1.0 if p[j] > 0 else -1.0
                h, l = Hn[t + 1, j], Ln[t + 1, j]
                if np.isnan(h) or np.isnan(l) or np.isnan(giris[j]):
                    ters = 0.0
                else:
                    ters = (giris[j] - l) / giris[j] if y > 0 else (h - giris[j]) / giris[j]
                en_kotu[j] = max(en_kotu[j], ters)
                if ters >= d:                              # tasfiye: teminatın tamamı kaybedilir
                    pnl -= teminat[j]; p[j] = 0.0; n_tas += 1
                    continue
                pnl += p[j] * r1[t, j] - p[j] * F1[t, j]
                p[j] *= (1 + r1[t, j])
        net[t] = pnl / deger if deger > 0 else 0.0
        deger += pnl
        if deger <= 0:
            net[t + 1:] = 0.0; break
    for j in np.flatnonzero(p != 0):
        mae.append(en_kotu[j])
    return pd.Series(net, index=C.index).shift(1).fillna(0.0), n_tas, mae


def kmn(D, L, senaryo, fiyat="hl"):
    rs, tas, mae = [], 0, []
    olcek = L if senaryo == "b" else 1.0
    for k in range(KMN["H"]):
        W = M.agirliklar(D, KMN, k)
        r, n, m = kmn_kayma(D, W, olcek, L, fiyat=fiyat)
        rs.append(r); tas += n; mae += m
    return pd.concat(rs, axis=1).mean(axis=1), tas / KMN["H"], np.array(mae)


# ---------------- özet ----------------
def olc(r, ek=None):
    bos = pd.DataFrame({"R": []})
    r = r[r.index >= "2020-01-01"]
    e = (1 + r).cumprod()
    m = metrik(e, bos)
    e24 = e[e.index >= "2024-01-01"]; m24 = metrik(e24 / e24.iloc[0], bos)
    y = e.resample("YE").last(); yil = y / y.shift(1).fillna(1) - 1
    out = dict(cagr=m["cagr"], dd=m["maxdd"], sharpe=m["sharpe"], y2022=100 * yil.get(pd.Timestamp("2022-12-31"), np.nan),
               cagr24=m24["cagr"], dd24=m24["maxdd"], sharpe24=m24["sharpe"], son_deger=e.iloc[-1])
    if ek:
        out.update(ek)
    return out


def calistir():
    SONUC.mkdir(parents=True, exist_ok=True)
    V = ks.yukle(); F = ks.ozellikler(V, KF.TREND)
    sinyaller = {gb: KF.giris_sinyalleri(V, dict(KF.GIRIS, gun_bas=float(gb))) for gb in KF.GUN_BASLARI}
    D = M.gunluk_panel(V)
    satir, stop_dag = [], None
    for sen in ("a", "b"):
        for L in LER:
            if sen == "b" and L == 1.0:
                continue
            rk, tk = kgt(V, F, sinyaller, L, sen)
            if stop_dag is None:
                stop_dag = (tk.risk / tk.giris).to_numpy()
            rm, nm, mae = kmn(D, L, sen)
            if L == 1.0:
                kmn_mae = mae
            ad = "a: aynı risk" if sen == "a" else "b: büyütme"
            n_kgt = (tk.sebep == "tasfiye").sum() / len(KF.GUN_BASLARI)
            satir.append(dict(senaryo=ad, L=L, strateji="KGT", **olc(rk, dict(tasfiye=n_kgt, islem=len(tk) / 6))))
            satir.append(dict(senaryo=ad, L=L, strateji="KMN", **olc(rm, dict(tasfiye=nm))))
            rb = pd.concat([rk, rm], axis=1).fillna(0).mean(axis=1)
            satir.append(dict(senaryo=ad, L=L, strateji="KGT+KMN", **olc(rb, dict(tasfiye=n_kgt + nm))))
            print(satir[-3:], flush=True)
    d = pd.DataFrame(satir)
    if (d.senaryo == "a: aynı risk").any():          # L=1 satırlarını b senaryosuna da kopyala (karşılaştırma için)
        b1 = d[(d.senaryo == "a: aynı risk") & (d.L == 1.0)].assign(senaryo="b: büyütme")
        d = pd.concat([d, b1]).sort_values(["senaryo", "strateji", "L"])
    d.to_csv(SONUC / "ozet.csv", index=False, float_format="%.3f")
    dag = {}
    for ad, x in (("KGT stop mesafesi", stop_dag), ("KMN 14 günlük en kötü ters hareket", kmn_mae)):
        x = x[np.isfinite(x)]
        q = np.percentile(x, [50, 75, 95, 99])
        dag[ad] = dict(medyan=100 * q[0], p75=100 * q[1], p95=100 * q[2], p99=100 * q[3],
                       guvenli_L=1 / (q[2] + BAKIM), n=len(x))
    dg = pd.DataFrame(dag).T
    dg.to_csv(SONUC / "dagilim.csv", float_format="%.3f")
    with pd.option_context("display.width", 250, "display.float_format", "{:.2f}".format):
        print(d.to_string(index=False)); print(dg.to_string())
    return d, dg


def ek():
    """Ek: (1) yalnız KGT kaldıraçlı (b), KMN 1x, %50/%50; (2) KMN tasfiyesi günlük kapanışla (duyarlılık)."""
    V = ks.yukle(); F = ks.ozellikler(V, KF.TREND)
    sinyaller = {gb: KF.giris_sinyalleri(V, dict(KF.GIRIS, gun_bas=float(gb))) for gb in KF.GUN_BASLARI}
    D = M.gunluk_panel(V)
    rm1 = pd.read_pickle(KOK / "sonuclar" / "s2" / "getiri_KMN.pkl")
    satir = []
    for L in (1.5, 2.0, 3.0):
        rk, tk = kgt(V, F, sinyaller, L, "b")
        rb = pd.concat([rk, rm1], axis=1).fillna(0).mean(axis=1)
        satir.append(dict(varyant=f"KGT {L}x (b) + KMN 1x", L=L, **olc(rb, dict(tasfiye=(tk.sebep == "tasfiye").sum() / 6))))
        print(satir[-1], flush=True)
    for sen in ("a", "b"):
        for L in (1.5, 2.0, 3.0):
            rm, nm, _ = kmn(D, L, sen, fiyat="kapanis")
            satir.append(dict(varyant=f"KMN {sen} {L}x, tasfiye kapanışla", L=L, **olc(rm, dict(tasfiye=nm))))
            print(satir[-1], flush=True)
    d = pd.DataFrame(satir); d.to_csv(SONUC / "ek.csv", index=False, float_format="%.3f")
    with pd.option_context("display.width", 250, "display.float_format", "{:.2f}".format):
        print(d.to_string(index=False))


if __name__ == "__main__":
    import sys, warnings
    warnings.filterwarnings("ignore")
    ek() if sys.argv[1:] == ["ek"] else calistir()
