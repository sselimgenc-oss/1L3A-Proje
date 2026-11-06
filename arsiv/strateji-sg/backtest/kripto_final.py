"""KGT — Kripto Günlük Pivot Kırılımı + Trend Takibi (nihai strateji, v3).

Yön (1G, UTC): günlük EMA(10) > EMA(20) ve son günlük kapanış > EMA(20) (v3, Brooks "always-in long").
Gün tanımı: gün başlangıcı gun_bas (UTC saat); pivot/CPR bir önceki "günden" hesaplanır.
Dar CPR: |TC-BC| <= 0.25 x günlük ATR14 (51 Strateji 2.7'nin "dar CPR = trend günü" kuralının sayısallaştırılması).
Giriş (1S): gün başından itibaren ilk 20 saat içinde 1S kapanışı önceki günün pivot R1 seviyesini yukarı keserse,
  bir sonraki 1S açılışında; günde tek işlem; yalnız long.
Stop: giriş - (R1 kırılım kapanışı - S1) mesafesi, 0.75-3 x ATR14(1S) aralığına sıkıştırılır. R1-S1 bir önceki
  günün aralığına eşit olduğundan mesafe pratikte hep üst sınıra takılır (~%96): fiilen stop = 3 x ATR14(1S)
  (Faz 9 denetimi; S1 stopu yalnız teorik).
Yönetim: 1R'de pozisyonun %15'i kapatılır, stop başabaşa çekilir.
Çıkış (4S): 4 saatlik EMA(21) < EMA(50) ve kapanış < EMA21 olunca (4S mumu kapanır kapanmaz) bir sonraki 1S açılışında.
Portföy: o ayın hacim sıralamasında ilk 15 coin, en fazla 5 eşzamanlı pozisyon, işlem başına %0.4 risk, kaldıraçsız
  (toplam brüt <= özsermaye, tek pozisyon <= %25). Masraf %0.07/taraf + fonlama.
Topluluk: 6 gün başlangıcı (0/4/.../20 UTC); günlük getirilerin ortalaması = sermaye 6'ya bölünüp her gün eşitlenir.

Kullanım:
  python3 -m backtest.kripto_final topluluk   # nihai backtest (6'lı topluluk) + rapor dosyaları (sonuclar/kripto/)
  python3 -m backtest.kripto_final rastgele   # rastgele giriş kıyası
  python3 -m backtest.kripto_final montecarlo # Monte Carlo düşüş/getiri dağılımı (topluluk getirileriyle)
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from . import kripto_strateji as ks, strateji as st, konfig as K, gostergeler as g
from .kripto_motor import portfoy, metrik

SONUC = Path(__file__).resolve().parent.parent / "sonuclar" / "kripto"
KES = pd.Timestamp("2024-01-01")

GIRIS = dict(K.GPK_ORTAK, **K.GPK_GUN["BTCUSDT"], htf_ust=1, yon=1)  # dar CPR + R1 kırılımı + günlük EMA10/20 + kapanış>EMA20 (v3)
# yon=1: yalnız long sinyal (Faz 9: short sinyaller "günün ilk sinyali" sayımında long'u engelleyebiliyordu)
GIRIS_V2 = dict(GIRIS, htf_ust=0)
TREND = dict(d_f=20, d_s=50, h4_f=21, h4_s=50, kir_n=48, sw_n=12)
# v2 (Faz 5, 2026-10-09): evren 10 -> 15, kısmi kâr 1/4 -> %15, risk %1 -> %0.5 (6 gün başı ortalaması ve
# yürüyen pencere testleriyle seçildi; bkz. RAPOR_KRIPTO.md "v2" bölümü)
# v3 (Faz 6): girişte günlük kapanış > EMA20 şartı (Brooks), risk %0.5 -> %0.4 (düşüşü azaltmak için; Sharpe değişmez)
KGT = dict(evren_n=15, yon=1, max_poz=5, max_yon=5, risk=0.004, max_pay=0.25, max_brut=1.0, maliyet=0.0007,
           tp1_r=1.0, tp1_pay=0.15, be_tp1=True, hedef_r=0.0, max_bar=0, iz_atr=0.0)
KGT_V2 = dict(KGT, risk=0.005)                                 # v2 risk (girişte GIRIS_V2 ile)
KGT_V1 = dict(KGT, evren_n=10, risk=0.01, tp1_pay=0.25)
VARYANT_A = dict(KGT, tp1_r=0.0)
# Topluluk: aynı strateji 6 farklı gün başlangıcıyla (pivot/CPR'nin hesaplandığı UTC günü 0,4,...,20 saat kaydırılır),
# sermaye 6'ya bölünür. Girişleri zamana yayar, tek bir zamanlamanın şans etkisini ortadan kaldırır.
GUN_BASLARI = (0, 4, 8, 12, 16, 20)                             # saf trend sürme (karşılaştırma)


def coin_df(V, j):
    c = V["C"][:, j]
    ok = ~np.isnan(c)
    if ok.sum() < 24 * 90:
        return None, None, None
    i0, i1 = np.argmax(ok), len(c) - np.argmax(ok[::-1])
    df = pd.DataFrame({"open": V["O"][i0:i1, j], "high": V["H"][i0:i1, j], "low": V["L"][i0:i1, j],
                       "close": c[i0:i1], "volume": 1.0}, index=V["zaman"][i0:i1]).ffill()
    return df, i0, i1


def giris_sinyalleri(V, p=GIRIS):
    T, N = V["C"].shape
    SIG = np.zeros((T, N)); STOP = np.full((T, N), np.nan)
    for j in range(N):
        df, i0, i1 = coin_df(V, j)
        if df is None:
            continue
        st._IND.clear()
        s, stp, _, _, _ = st.gunluk_kirilim(df, p)
        # veri boşluğu: ileri doldurulmuş (H==L) ya da eksik mumlar. Önceki günü boşluklu olan günde pivot/CPR bayat
        # fiyattan hesaplanır ve yapay sinyal üretir -> o gün ve boşluklu mumlarda sinyal yok (Faz 9 denetimi).
        bos = np.isnan(V["C"][i0:i1, j]) | (V["H"][i0:i1, j] == V["L"][i0:i1, j])
        _, _, gun, _ = st.gunluk_seviyeler(df, p["tz"], p.get("gun_bas", 0.0))
        gs = pd.Series(bos.astype(int), index=gun).groupby(level=0).sum()
        onceki = gs.shift(1).reindex(gun).fillna(0).to_numpy() >= 2
        s = np.where(bos | onceki, 0.0, s)
        SIG[i0:i1, j] = s
        STOP[i0:i1, j] = np.where(s != 0, stp, np.nan)
    return SIG, STOP


def diziler(V, q=KGT, SIG=None, STOP=None, F=None):
    if SIG is None:
        SIG, STOP = giris_sinyalleri(V)
    if F is None:
        F = ks.ozellikler(V, TREND)
    S = SIG.copy()
    S[V["ONC"] >= q["evren_n"]] = 0
    if q["yon"] == 1:
        S[S < 0] = 0
    CIK = np.where(F["h4_yon"] < 0, -1.0, np.where(F["h4_yon"] > 0, 1.0, 0.0))
    return S, STOP, np.nan_to_num(F["atr4"]), CIK


def calistir(V, q=KGT, **kw):
    S, STOP, IZ, CIK = diziler(V, q, **kw)
    return portfoy(V, S, STOP, IZ, CIK, V["ONC"], q)


def ozetle(e, t):
    out = {}
    for ad, m in (("TÜM", slice(None)), ("IS 2020-2023", e.index < KES), ("OOS 2024-2026/09", e.index >= KES)):
        ee = e if isinstance(m, slice) else e[m]
        tt = t if isinstance(m, slice) else t[(t.giris_zaman < KES) if "IS" in ad else (t.giris_zaman >= KES)]
        out[ad] = metrik(ee, tt)
    return pd.DataFrame(out).T


def btc_al_tut(V):
    j = V["semboller"].index("BTCUSDT")
    b = pd.Series(V["C"][:, j], index=V["zaman"]).dropna()
    return b / b.iloc[0]


def be_dizisi(V, gb):
    """Aynı saatlik mumda 1R kısmi kâr + başabaş stop belirsizliğinin 1 dakikalık Binance verisiyle çözümü
    (Faz 9; sonuclar/kripto/be_1dk.pkl: (gun_bas, t, j) -> 1 başabaş vuruldu / 0 vurulmadı). Yoksa None."""
    import pickle
    f = SONUC / "be_1dk.pkl"
    if not f.exists():
        return None
    B = np.zeros(V["C"].shape)
    for (g_, t_, j_), v in pickle.load(open(f, "rb")).items():
        if g_ == gb and v and t_ < B.shape[0]:
            B[t_, j_] = 1.0
    return B


def topluluk():
    """KGT v3 topluluğu: 6 gün başlangıcı, sermaye/6. Özet, yıllık, eğri -> sonuclar/kripto/*_v3*."""
    SONUC.mkdir(parents=True, exist_ok=True)
    V = ks.yukle(); F = ks.ozellikler(V, TREND)
    rs, ts = [], []
    for gb in GUN_BASLARI:
        SIG, STOP = giris_sinyalleri(V, dict(GIRIS, gun_bas=float(gb)))
        be = be_dizisi(V, gb)
        q = KGT if be is None else dict(KGT, ici_sira=3, BEZ=be)    # 1 dk çözümü yoksa OHLC yolu varsayımı (ici_sira=1)
        e, t = calistir(V, q, SIG=SIG, STOP=STOP, F=F)
        rs.append(e.resample("1D").last().pct_change().fillna(0)); t["gun_bas"] = gb; ts.append(t)
    r = pd.concat(rs, axis=1).fillna(0).mean(axis=1); e = (1 + r).cumprod(); T = pd.concat(ts)
    r.to_pickle(SONUC / "getiri_v3_topluluk.pkl")                 # montecarlo() bunu kullanır
    b = btc_al_tut(V).resample("1D").last()
    satir = {}
    for ad, m in (("TÜM", slice(None)), ("IS 2020-2023", e.index < KES), ("OOS 2024-2026/09", e.index >= KES)):
        ee = e if isinstance(m, slice) else e[m]
        tt = T if isinstance(m, slice) else T[(T.giris_zaman < KES) if "IS" in ad else (T.giris_zaman >= KES)]
        x = metrik(ee / ee.iloc[0], tt); x["islem"] = len(tt) / len(GUN_BASLARI); satir["KGT v3 topluluk " + ad] = x
    satir["BTC al-tut TÜM"] = metrik(b, pd.DataFrame({"R": []}))
    oz = pd.DataFrame(satir).T
    oz.to_csv(SONUC / "ozet_v3_topluluk.csv", float_format="%.3f")
    y = e.resample("YE").last(); by = b.resample("YE").last()
    yil = pd.DataFrame({"KGT_v3_topluluk": 100 * (y / y.shift(1).fillna(1) - 1), "BTC_al_tut": 100 * (by / by.shift(1).fillna(1) - 1)})
    yil.index = yil.index.year
    T["yil"] = T.giris_zaman.dt.year
    yil["kazanma"] = T.groupby("yil").R.apply(lambda x: 100 * (x > 0).mean())
    yil["pf"] = T.groupby("yil").R.apply(lambda x: x[x > 0].sum() / -x[x <= 0].sum())
    yil.to_csv(SONUC / "yillik_v3_topluluk.csv", float_format="%.2f")
    T.drop(columns=["gi", "ci", "j"]).to_csv(SONUC / "islemler_KGT_v3_topluluk.csv", index=False, float_format="%.6g")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(2, 1, figsize=(10, 7), dpi=120, sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
    fig.patch.set_facecolor("#fcfcfb")
    for ax in axs:
        ax.set_facecolor("#fcfcfb"); ax.grid(axis="y", color="#e5e4df", lw=0.6)
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)
        ax.spines["left"].set_color("#c3c2b7"); ax.spines["bottom"].set_color("#c3c2b7"); ax.tick_params(colors="#52514e", labelsize=9)
    for ad, s_, rk in (("KGT v3 topluluk", e, "#2a78d6"), ("BTC al-tut", b, "#eb6834")):
        axs[0].plot(s_.index, s_.values, color=rk, lw=2, label=ad)
        axs[0].annotate(f"{ad} ×{s_.values[-1]:.1f}", (s_.index[-1], s_.values[-1]), xytext=(4, 0), textcoords="offset points",
                        fontsize=9, color="#0b0b0b", va="center")
        axs[1].plot(s_.index, 100 * (s_ / s_.cummax() - 1), color=rk, lw=1.5)
    axs[0].set_yscale("log"); axs[0].axvline(KES, color="#52514e", lw=0.8, ls="--")
    axs[0].text(KES, axs[0].get_ylim()[1], " test dönemi →", fontsize=9, color="#52514e", va="top")
    axs[0].set_ylabel("Özsermaye (log, başlangıç = 1)", color="#52514e"); axs[1].set_ylabel("Düşüş %", color="#52514e")
    axs[0].set_title("KGT v3 — 6 gün başlangıçlı topluluk, %0.4 risk, masraf ve fonlama dahil", loc="left", fontsize=12, color="#0b0b0b")
    axs[0].legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout(); fig.savefig(SONUC / "egri_KGT_v3_topluluk.png"); plt.close(fig)
    with pd.option_context("display.width", 250, "display.float_format", "{:.2f}".format):
        print(oz.to_string()); print(yil.to_string())


def rapor():
    SONUC.mkdir(parents=True, exist_ok=True)
    V = ks.yukle()
    SIG, STOP = giris_sinyalleri(V)
    F = ks.ozellikler(V, TREND)
    sonuc = {}
    for ad, q in (("KGT", KGT), ("A_saf_trend", VARYANT_A)):
        e, t = calistir(V, q, SIG=SIG, STOP=STOP, F=F)
        sonuc[ad] = (e, t)
    e, t = sonuc["KGT"]
    b = btc_al_tut(V)
    oz = pd.concat({ad: ozetle(*sonuc[ad]) for ad in sonuc})
    bb = pd.DataFrame({"TÜM": metrik(b, pd.DataFrame({"R": []})),
                       "OOS 2024-2026/09": metrik(b[b.index >= KES] / b[b.index >= KES].iloc[0], pd.DataFrame({"R": []}))}).T
    oz = pd.concat([oz, pd.concat({"BTC_al_tut": bb})])
    oz.to_csv(SONUC / "ozet.csv", float_format="%.3f")
    yil = pd.DataFrame({ad: 100 * (sonuc[ad][0].resample("YE").last() / sonuc[ad][0].resample("YE").last().shift(1).fillna(1) - 1)
                        for ad in sonuc})
    by = b.resample("YE").last()
    yil["BTC_al_tut"] = 100 * (by / by.shift(1).fillna(1) - 1)
    yil.index = yil.index.year
    tt = t.copy(); tt["yil"] = tt.giris_zaman.dt.year
    yil["KGT_islem"] = tt.groupby("yil").size()
    yil["KGT_kazanma"] = tt.groupby("yil").R.apply(lambda x: 100 * (x > 0).mean())
    yil["KGT_pf"] = tt.groupby("yil").R.apply(lambda x: x[x > 0].sum() / -x[x <= 0].sum())
    yil.to_csv(SONUC / "yillik.csv", float_format="%.2f")
    coin = t.groupby("sembol").agg(islem=("R", "size"), kazanma=("R", lambda x: 100 * (x > 0).mean()),
                                   toplamR=("R", "sum"), ortR=("R", "mean")).sort_values("toplamR", ascending=False)
    coin.to_csv(SONUC / "coin.csv", float_format="%.3f")
    t.drop(columns=["gi", "ci", "j"]).to_csv(SONUC / "islemler_KGT.csv", index=False, float_format="%.6g")
    grafik({"KGT (B)": e, "A — saf trend": sonuc["A_saf_trend"][0], "BTC al-tut": b})
    with pd.option_context("display.width", 250, "display.float_format", "{:.2f}".format):
        print(oz.to_string()); print(yil.to_string()); print(coin.head(12).to_string()); print(coin.tail(8).to_string())
    sure = (t.cikis_zaman - t.giris_zaman).dt.total_seconds() / 86400
    print(f"işlem/yıl {len(t) / ((e.index[-1] - e.index[0]).days / 365.25):.0f}, ort. tutma {sure.mean():.1f} gün, "
          f"medyan {sure.median():.1f} gün, en uzun {sure.max():.0f} gün; çıkış sebepleri {t.sebep.value_counts().to_dict()}")
    print(f"ortalama fonlama/işlem (R): {(t.fonlama / (t.notional / t.giris * t.risk)).mean():.4f}")


def grafik(egriler):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    renk = {"KGT (B)": "#2a78d6", "A — saf trend": "#1baf7a", "BTC al-tut": "#eb6834"}
    fig, axs = plt.subplots(2, 1, figsize=(10, 7), dpi=120, sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
    for ax in axs:
        ax.set_facecolor("#fcfcfb")
        for s_ in ("top", "right"):
            ax.spines[s_].set_visible(False)
        ax.spines["left"].set_color("#c3c2b7"); ax.spines["bottom"].set_color("#c3c2b7")
        ax.tick_params(colors="#52514e", labelsize=9)
        ax.grid(axis="y", color="#e5e4df", lw=0.6)
    fig.patch.set_facecolor("#fcfcfb")
    sonlar = []
    for ad, e in egriler.items():
        e = e.resample("1D").last().dropna()
        axs[0].plot(e.index, e.values, color=renk[ad], lw=2, label=ad)
        sonlar.append([np.log10(e.values[-1]), ad, e.index[-1], e.values[-1]])
        dd = 100 * (e / e.cummax() - 1)
        axs[1].plot(dd.index, dd.values, color=renk[ad], lw=1.5)
    sonlar.sort()
    for i in range(1, len(sonlar)):      # uç etiketlerini log ölçekte en az 0.06 aralıkla ayır
        sonlar[i][0] = max(sonlar[i][0], sonlar[i - 1][0] + 0.06)
    for y, ad, x, v in sonlar:
        axs[0].annotate(f"{ad} ×{v:.1f}", (x, v), xytext=(x + pd.Timedelta(days=10), 10 ** y), fontsize=9,
                        color="#0b0b0b", va="center")
    axs[0].set_yscale("log")
    axs[0].axvline(KES, color="#52514e", lw=0.8, ls="--")
    axs[0].text(KES, axs[0].get_ylim()[1], " test dönemi →", fontsize=9, color="#52514e", va="top")
    axs[0].set_ylabel("Özsermaye (log, başlangıç = 1)", color="#52514e")
    axs[1].set_ylabel("Düşüş %", color="#52514e")
    axs[0].set_title("KGT — kripto trend stratejisi, masraf ve fonlama dahil", loc="left", fontsize=12, color="#0b0b0b")
    axs[0].legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout()
    fig.savefig(SONUC / "egri_KGT.png")
    plt.close(fig)


def rastgele(n_sim=40, tohum=7):
    """Rastgele giriş kıyası: aynı coin/yıl başına aynı sayıda giriş, yalnız günlük trend yukarı ve evrende olan
    saatlerde rastgele; aynı stop yüzdesi dağılımı, aynı çıkış ve yönetim kuralları."""
    V = ks.yukle()
    SIG, STOP = giris_sinyalleri(V)
    F = ks.ozellikler(V, TREND)
    S, _, _, _ = diziler(V, KGT, SIG=SIG, STOP=STOP, F=F)
    e0, t0 = calistir(V, KGT, SIG=SIG, STOP=STOP, F=F)
    # günlük EMA10>EMA20 filtresi (GPK ile aynı) ve işlem penceresi
    T, N = V["C"].shape
    uygun = np.zeros((T, N), bool)
    hr = V["zaman"].hour.to_numpy()
    for j in range(N):
        df, i0, i1 = coin_df(V, j)
        if df is None:
            continue
        d = ks._htf(df, "1D"); dc = d.close.to_numpy()
        e20 = g.ema(dc, 20)
        up = ((g.ema(dc, 10) > e20) & (dc > e20)).astype(float)       # v3 ile aynı rejim filtresi (Faz 9)
        uygun[i0:i1, j] = g.htf_hizala(df.index, d, {"u": up})["u"] > 0
    uygun &= (V["ONC"] < KGT["evren_n"]) & (hr[:, None] < 20)
    gercek = np.argwhere(S > 0)
    stop_pct = STOP[S > 0] / V["C"][S > 0]
    yil = V["zaman"].year.to_numpy()
    rng = np.random.default_rng(tohum)
    sonuc = []
    for k in range(n_sim):
        RS = np.zeros_like(S); RST = np.full_like(STOP, np.nan)
        for (ti, j), sp in zip(gercek, rng.permutation(stop_pct)):
            aday = np.flatnonzero(uygun[:, j] & (yil == yil[ti]))
            if len(aday) == 0:
                continue
            tt = rng.choice(aday)
            RS[tt, j] = 1; RST[tt, j] = sp * V["C"][tt, j]
        _, STP, IZ, CIK = diziler(V, KGT, SIG=RS, STOP=RST, F=F)
        e, t = portfoy(V, RS, RST, IZ, CIK, V["ONC"], KGT)
        m = metrik(e, t); mo = metrik(e[e.index >= KES], t[t.giris_zaman >= KES])
        sonuc.append(dict(pf=m["pf"], cagr=m["cagr"], maxdd=m["maxdd"], kazanma=m["kazanma"], oos_pf=mo["pf"], oos_cagr=mo["cagr"]))
        print(k, {a: round(b, 2) for a, b in sonuc[-1].items()}, flush=True)
    r = pd.DataFrame(sonuc)
    m0 = metrik(e0, t0); mo0 = metrik(e0[e0.index >= KES], t0[t0.giris_zaman >= KES])
    print("\nGERÇEK:", dict(pf=round(m0["pf"], 2), cagr=round(m0["cagr"], 1), maxdd=round(m0["maxdd"], 1),
                           oos_pf=round(mo0["pf"], 2), oos_cagr=round(mo0["cagr"], 1)))
    print("RASTGELE dağılım:\n", r.describe(percentiles=[0.05, 0.5, 0.95]).round(2).to_string())
    print("gerçekten iyi rastgele oranı: PF %.2f, CAGR %.2f, OOS PF %.2f" % (
        (r.pf >= m0["pf"]).mean(), (r.cagr >= m0["cagr"]).mean(), (r.oos_pf >= mo0["pf"]).mean()))
    r.to_csv(SONUC / "rastgele_kiyas.csv", index=False, float_format="%.3f")


def montecarlo(n=5000, blok=20, tohum=11):
    """Günlük getirilerin blok bootstrap'ı: 1 yıllık ve tüm dönem için getiri / maks. düşüş dağılımı.
    Önce `topluluk` çalıştırılmışsa gerçek kullanımdaki 6'lı topluluk getirileri, yoksa tek alt portföy kullanılır."""
    f = SONUC / "getiri_v3_topluluk.pkl"
    if f.exists():
        r = pd.read_pickle(f).to_numpy()
    else:
        e, t = calistir(ks.yukle(), KGT)
        r = e.resample("1D").last().pct_change().dropna().to_numpy()
    rng = np.random.default_rng(tohum)
    def yol(uzun):
        idx = []
        while len(idx) < uzun:
            s0 = rng.integers(0, len(r) - blok)
            idx.extend(range(s0, s0 + blok))
        x = np.cumprod(1 + r[idx[:uzun]])
        return x[-1] - 1, (1 - x / np.maximum.accumulate(x)).max()
    satir = []
    for ad, uzun in (("1 yıl", 365), ("3 yıl", 3 * 365)):
        s_ = np.array([yol(uzun) for _ in range(n)])
        satir.append(dict(ufuk=ad, getiri_p5=100 * np.percentile(s_[:, 0], 5), getiri_medyan=100 * np.median(s_[:, 0]),
                          getiri_p95=100 * np.percentile(s_[:, 0], 95), zarar_olasiligi=100 * (s_[:, 0] < 0).mean(),
                          maxdd_medyan=100 * np.median(s_[:, 1]), maxdd_p95=100 * np.percentile(s_[:, 1], 95),
                          maxdd_p99=100 * np.percentile(s_[:, 1], 99)))
    d = pd.DataFrame(satir)
    print(d.round(1).to_string(index=False))
    d.to_csv(SONUC / "montecarlo.csv", index=False, float_format="%.2f")


if __name__ == "__main__":
    {"rapor": rapor, "rastgele": rastgele, "montecarlo": montecarlo, "topluluk": topluluk}[sys.argv[1] if len(sys.argv) > 1 else "rapor"]()
