"""SKA — Sıkışma Kırılım Arızası (Galen Woods, Congestion Breakout Failure) — kripto, 4 saatlik grafik.

Eğilim (4S): EMA(21) > EMA(50) ve kapanış EMA21 üstünde -> yalnız long (yalnız kapanmış 4S mumları).
Kurulum (4S, Galen 2.2.4):
  1. Tıkanıklık: en az 4 ardışık mum, her biri bir önceki mumun aralığı içinde kapanır.
  2. Düşüş kırılım mumu: tıkanıklıktan sonraki mum, önceki mumun dibinin altında kapanır (sahte kırılım).
  3. Kurulum mumu: hemen ardından gelen yükseliş mumu (kapanış > açılış).
Giriş: kurulum mumunun tepesi + 0.02 ATR'ye bekleyen alış emri, yalnız bir sonraki 4S mumunda geçerli.
Stop: kurulum mumunun dibi - 0.02 ATR; mesafe en az 1 x ATR(14, 4S).
Yönetim: +1R'de pozisyonun 1/4'ü kapatılır, stop başabaşa çekilir. Çıkış: 4S eğilim aşağı dönünce sonraki açılışta.
Portföy: o ayın hacim sıralamasında ilk 20 coin, en fazla 5 eşzamanlı pozisyon, işlem başına %1 risk, kaldıraçsız;
masraf %0.07/taraf + fonlama.

Kullanım:
  python3 -m backtest.pa_final            # rapor + dosyalar (sonuclar/pa/)
  python3 -m backtest.pa_final rastgele   # rastgele giriş kıyası
  python3 -m backtest.pa_final montecarlo
  python3 -m backtest.pa_final komsu      # komşu parametre / maliyet testi
"""
import itertools
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from . import kripto_strateji as ks, pa_arastirma as P
from .kripto_motor import portfoy, metrik

SONUC = Path(__file__).resolve().parent.parent / "sonuclar" / "pa"
KES = P.KES
SKA = dict(kurulumlar=("CBF",), cbf_n=4, egilim="h4", yon=1, evren_n=20, stop_min_atr=1.0,
           cikis="h4", tp1_r=1.0, tp1_pay=0.25, hedef_r=0.0)


def hazirla(cbf_ler=(4,)):
    V = P.yeniden_ornekle(ks.yukle(), "4h")
    F = ks.ozellikler(V, P.TREND)
    L = {n: {("CBF", y): P.kurulum_listesi(V, F, "CBF", y, cbf_n=n) for y in (1, -1)} for n in cbf_ler}
    return V, F, L


def calistir(V, F, L, p=SKA, maliyet=None):
    if maliyet is not None:
        P.PORTFOY["maliyet"] = maliyet
    try:
        o, e, t = P.degerlendir(V, F, L[p["cbf_n"]], p, egri=True)
    finally:
        P.PORTFOY["maliyet"] = 0.0007
    return o, e, t


def rapor():
    SONUC.mkdir(parents=True, exist_ok=True)
    V, F, L = hazirla()
    o, e, t = calistir(V, F, L)
    j = V["semboller"].index("BTCUSDT")
    b = pd.Series(V["C"][:, j], index=V["zaman"]).dropna(); b = b / b.iloc[0]
    oz = pd.DataFrame({"SKA TÜM": o["TUM"], "SKA IS 2020-2023": o["IS"], "SKA OOS 2024-2026/09": o["OOS"],
                       "BTC al-tut TÜM": metrik(b, pd.DataFrame({"R": []})),
                       "BTC al-tut OOS": metrik(b[b.index >= KES] / b[b.index >= KES].iloc[0], pd.DataFrame({"R": []}))}).T
    oz.to_csv(SONUC / "ozet.csv", float_format="%.3f")
    ey = e.resample("YE").last(); by = b.resample("YE").last()
    tt = t.copy(); tt["yil"] = tt.giris_zaman.dt.year
    yil = pd.DataFrame({"SKA_getiri": 100 * (ey / ey.shift(1).fillna(1) - 1), "BTC_al_tut": 100 * (by / by.shift(1).fillna(1) - 1)})
    yil.index = yil.index.year
    yil["islem"] = tt.groupby("yil").size()
    yil["kazanma"] = tt.groupby("yil").R.apply(lambda x: 100 * (x > 0).mean())
    yil["pf"] = tt.groupby("yil").R.apply(lambda x: x[x > 0].sum() / -x[x <= 0].sum() if (x <= 0).any() else np.nan)
    yil.to_csv(SONUC / "yillik.csv", float_format="%.2f")
    coin = t.groupby("sembol").agg(islem=("R", "size"), kazanma=("R", lambda x: 100 * (x > 0).mean()),
                                   toplamR=("R", "sum")).sort_values("toplamR", ascending=False)
    coin.to_csv(SONUC / "coin.csv", float_format="%.3f")
    t.drop(columns=["gi", "ci", "j"]).to_csv(SONUC / "islemler_SKA.csv", index=False, float_format="%.6g")
    # kazanç yoğunlaşması
    R = t.R.sort_values(ascending=False)
    yog = {f"en iyi {k} işlemin toplam R payı %": 100 * R.iloc[:k].sum() / R.sum() for k in (5, 10, 20)}
    sure = (t.cikis_zaman - t.giris_zaman).dt.total_seconds() / 86400
    with pd.option_context("display.width", 250, "display.float_format", "{:.2f}".format):
        print(oz.to_string()); print(yil.to_string()); print(coin.head(10).to_string()); print(coin.tail(5).to_string())
    print({k: round(v, 1) for k, v in yog.items()}, "toplam R", round(R.sum(), 1))
    print(f"işlem/yıl {len(t) / ((e.index[-1] - e.index[0]).days / 365.25):.0f}, ort. tutma {sure.mean():.1f} gün "
          f"(medyan {sure.median():.1f}), çıkış {t.sebep.value_counts().to_dict()}, stop% medyan {(100 * t.risk / t.giris).median():.2f}")
    grafik(e, b)


def grafik(e, b):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(2, 1, figsize=(10, 7), dpi=120, sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
    fig.patch.set_facecolor("#fcfcfb")
    for ax in axs:
        ax.set_facecolor("#fcfcfb")
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)
        ax.spines["left"].set_color("#c3c2b7"); ax.spines["bottom"].set_color("#c3c2b7")
        ax.tick_params(colors="#52514e", labelsize=9); ax.grid(axis="y", color="#e5e4df", lw=0.6)
    for ad, s_, r in (("SKA", e, "#2a78d6"), ("BTC al-tut", b, "#eb6834")):
        s_ = s_.resample("1D").last().dropna()
        axs[0].plot(s_.index, s_.values, color=r, lw=2, label=ad)
        axs[0].annotate(f"{ad} ×{s_.values[-1]:.1f}", (s_.index[-1], s_.values[-1]), xytext=(4, 0),
                        textcoords="offset points", fontsize=9, color="#0b0b0b", va="center")
        axs[1].plot(s_.index, 100 * (s_ / s_.cummax() - 1), color=r, lw=1.5)
    axs[0].set_yscale("log"); axs[0].axvline(KES, color="#52514e", lw=0.8, ls="--")
    axs[0].text(KES, axs[0].get_ylim()[1], " test dönemi →", fontsize=9, color="#52514e", va="top")
    axs[0].set_ylabel("Özsermaye (log, başlangıç = 1)", color="#52514e"); axs[1].set_ylabel("Düşüş %", color="#52514e")
    axs[0].set_title("SKA — Sıkışma Kırılım Arızası (4S), masraf ve fonlama dahil", loc="left", fontsize=12, color="#0b0b0b")
    axs[0].legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout(); fig.savefig(SONUC / "egri_SKA.png"); plt.close(fig)


def komsu():
    V, F, L = hazirla((3, 4, 5))
    satir = []
    degis = [dict()] + [dict(cbf_n=n) for n in (3, 5)] + [dict(evren_n=n) for n in (10, 15, 30)] + \
            [dict(stop_min_atr=s) for s in (0.5, 0.75, 1.5)] + [dict(tp1_pay=x) for x in (1 / 3, 0.5)] + \
            [dict(tp1_r=x) for x in (0.75, 1.5)] + [dict(tp1_r=0.0)] + [dict(egilim="h4d"), dict(egilim="d")] + \
            [dict(yon=0)] + [dict(cikis="d")]
    for d in degis:
        o, e, t = calistir(V, F, L, dict(SKA, **d))
        satir.append(dict(degisiklik=str(d) if d else "varsayılan", IS_pf=o["IS"]["pf"], OOS_pf=o["OOS"]["pf"],
                          IS_wr=o["IS"]["kazanma"], OOS_wr=o["OOS"]["kazanma"], IS_cagr=o["IS"]["cagr"],
                          OOS_cagr=o["OOS"]["cagr"], IS_dd=o["IS"]["maxdd"], OOS_dd=o["OOS"]["maxdd"], n=o["TUM"]["islem"]))
    for mk in (1.5, 2.0):
        o, e, t = calistir(V, F, L, SKA, maliyet=0.0007 * mk)
        satir.append(dict(degisiklik=f"maliyet x{mk}", IS_pf=o["IS"]["pf"], OOS_pf=o["OOS"]["pf"], IS_wr=o["IS"]["kazanma"],
                          OOS_wr=o["OOS"]["kazanma"], IS_cagr=o["IS"]["cagr"], OOS_cagr=o["OOS"]["cagr"],
                          IS_dd=o["IS"]["maxdd"], OOS_dd=o["OOS"]["maxdd"], n=o["TUM"]["islem"]))
    r = pd.DataFrame(satir)
    r.to_csv(SONUC / "komsu.csv", index=False, float_format="%.3f")
    with pd.option_context("display.width", 250):
        print(r.round(2).to_string(index=False))


def rastgele(n_sim=40, tohum=5):
    """Aynı coin/yıl başına aynı sayıda giriş; 4S eğilimi yukarı ve evrende olan rastgele mumlarda, aynı stop
    yüzdesi dağılımıyla bekleyen emir yerine piyasa emriyle; aynı çıkış ve yönetim."""
    V, F, L = hazirla()
    o0, e0, t0 = calistir(V, F, L)
    SIG, STOP, GSEV, CIK = P.diziler(V, F, L[4], SKA)
    uygun = (F["h4_yon"] > 0) & (V["ONC"] < SKA["evren_n"]) & ~np.isnan(V["C"])
    yil = V["zaman"].year.to_numpy()
    gercek = np.argwhere(SIG > 0)
    stop_pct = STOP[SIG > 0] / GSEV[SIG > 0]
    rng = np.random.default_rng(tohum)
    q = dict(P.PORTFOY, tp1_r=SKA["tp1_r"], tp1_pay=SKA["tp1_pay"], be_tp1=True)
    sonuc = []
    for k in range(n_sim):
        RS = np.zeros_like(SIG); RST = np.full_like(STOP, np.nan)
        for (ti, j), sp in zip(gercek, rng.permutation(stop_pct)):
            aday = np.flatnonzero(uygun[:, j] & (yil == yil[ti]))
            if len(aday):
                tt = rng.choice(aday); RS[tt, j] = 1; RST[tt, j] = sp * V["C"][tt, j]
        e, t = portfoy(V, RS, RST, np.zeros_like(RST), CIK, V["ONC"], q)
        m = metrik(e, t); mo = metrik(e[e.index >= KES], t[t.giris_zaman >= KES])
        sonuc.append(dict(pf=m["pf"], cagr=m["cagr"], maxdd=m["maxdd"], kazanma=m["kazanma"], oos_pf=mo["pf"], oos_cagr=mo["cagr"]))
    r = pd.DataFrame(sonuc)
    print("GERÇEK:", {k: round(v, 2) for k, v in dict(pf=o0["TUM"]["pf"], cagr=o0["TUM"]["cagr"], maxdd=o0["TUM"]["maxdd"],
                                                      oos_pf=o0["OOS"]["pf"], oos_cagr=o0["OOS"]["cagr"]).items()})
    print(r.describe(percentiles=[0.05, 0.5, 0.95]).round(2).to_string())
    print("gerçekten iyi rastgele oranı: PF %.2f, CAGR %.2f, OOS PF %.2f" % ((r.pf >= o0["TUM"]["pf"]).mean(),
          (r.cagr >= o0["TUM"]["cagr"]).mean(), (r.oos_pf >= o0["OOS"]["pf"]).mean()))
    r.to_csv(SONUC / "rastgele_kiyas.csv", index=False, float_format="%.3f")


def montecarlo(n=5000, blok=20, tohum=11):
    V, F, L = hazirla()
    o, e, t = calistir(V, F, L)
    r = e.resample("1D").last().pct_change().dropna().to_numpy()
    rng = np.random.default_rng(tohum)
    def yol(u):
        idx = []
        while len(idx) < u:
            s0 = rng.integers(0, len(r) - blok); idx.extend(range(s0, s0 + blok))
        x = np.cumprod(1 + r[idx[:u]]); return x[-1] - 1, (1 - x / np.maximum.accumulate(x)).max()
    satir = []
    for ad, u in (("1 yıl", 365), ("3 yıl", 3 * 365)):
        s_ = np.array([yol(u) for _ in range(n)])
        satir.append(dict(ufuk=ad, getiri_p5=100 * np.percentile(s_[:, 0], 5), getiri_medyan=100 * np.median(s_[:, 0]),
                          getiri_p95=100 * np.percentile(s_[:, 0], 95), zarar_olasiligi=100 * (s_[:, 0] < 0).mean(),
                          maxdd_medyan=100 * np.median(s_[:, 1]), maxdd_p95=100 * np.percentile(s_[:, 1], 95),
                          maxdd_p99=100 * np.percentile(s_[:, 1], 99)))
    d = pd.DataFrame(satir); print(d.round(1).to_string(index=False))
    d.to_csv(SONUC / "montecarlo.csv", index=False, float_format="%.2f")


if __name__ == "__main__":
    {"rapor": rapor, "rastgele": rastgele, "montecarlo": montecarlo, "komsu": komsu}[sys.argv[1] if len(sys.argv) > 1 else "rapor"]()
