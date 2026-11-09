"""Nihai backtest: iki stratejiyi tüm enstrümanlarda çalıştırır, sonuclar/ klasörüne yazar.

Kullanım:  python3 -m backtest.veri      # veriyi hazırla (bir kez)
           python3 -m backtest.calistir  # backtest + rapor tabloları + grafikler
"""
from pathlib import Path
import numpy as np
import pandas as pd
from . import arastirma as A, strateji as st, konfig as K
from .motor import backtest, ozet

SONUC = Path(__file__).resolve().parent.parent / "sonuclar"

STRATEJILER = {
    "SAKK_5dk": dict(tf="M5", fonk=st.kutu_kirilim, ortak=K.SAKK_ORTAK, ozel=K.SAKK_KUTU),
    "GPK_1s": dict(tf="H1", fonk=st.gunluk_kirilim, ortak=K.GPK_ORTAK, ozel=K.GPK_GUN),
}


def mevcut_semboller(tf):
    return [s for s in ["XU030", "SPX", "XAUUSD", "UKOIL", "BTCUSDT"] if (A.VERI / f"{s}_{tf}.pkl").exists()]


def islemler(ad, sym):
    k = STRATEJILER[ad]
    df = A.veri(sym, k["tf"])
    p = dict(k["ortak"], **k["ozel"][sym])
    r = k["fonk"](df, p)
    return backtest(df, *r[:3], A.MALIYET[sym], *r[3:]), df


def main():
    SONUC.mkdir(exist_ok=True)
    ozet_satir, yil_satir, egriler = [], [], {}
    for ad, k in STRATEJILER.items():
        for sym in mevcut_semboller(k["tf"]):
            t, df = islemler(ad, sym)
            t.drop(columns=["gi", "ci"]).to_csv(SONUC / f"islemler_{ad}_{sym}.csv", index=False, float_format="%.6g")
            is_, oos, kes = A.bolum(t, df.index)
            for bol, x in (("TÜM", t), ("IS", is_), ("OOS", oos)):
                o = ozet(x)
                yil = (df.index[-1] - df.index[0]).days / 365.25 if bol == "TÜM" else np.nan
                ozet_satir.append(dict(strateji=ad, sembol=sym, bolum=bol, baslangic=df.index[0].date(),
                                       bitis=df.index[-1].date(), oos_baslangic=kes.date(), **o,
                                       yillik_islem=o["islem"] / yil if bol == "TÜM" else np.nan))
            for y, x in t.groupby(t.giris_zaman.dt.year):
                yil_satir.append(dict(strateji=ad, sembol=sym, yil=y, **ozet(x)))
            egriler[(ad, sym)] = t.set_index("cikis_zaman").R.cumsum()
    oz = pd.DataFrame(ozet_satir)
    oz["kullan"] = np.where((oz.bolum == "TÜM"), np.where(
        (oz.pf > 1) & (oz.kazanma >= 45) & (oz.merge(oz[oz.bolum == "OOS"][["strateji", "sembol", "pf"]],
                                                     on=["strateji", "sembol"], suffixes=("", "_oos")).pf_oos.values > 1),
        "EVET", "HAYIR"), "")
    oz.to_csv(SONUC / "ozet.csv", index=False, float_format="%.3f")
    pd.DataFrame(yil_satir).to_csv(SONUC / "yillik.csv", index=False, float_format="%.3f")
    grafik(egriler)
    with pd.option_context("display.width", 250, "display.max_columns", 30, "display.float_format", "{:.2f}".format):
        print(oz[["strateji", "sembol", "bolum", "islem", "kazanma", "pf", "ortR", "toplamR", "getiri_pct", "maxdd_pct",
                  "yillik_islem", "kullan"]].to_string(index=False))


def grafik(egriler):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    renk = {"SPX": "#2a78d6", "XAUUSD": "#eb6834", "UKOIL": "#1baf7a", "BTCUSDT": "#eda100", "XU030": "#e87ba4"}
    for ad in STRATEJILER:
        fig, ax = plt.subplots(figsize=(10, 5), dpi=120)
        fig.patch.set_facecolor("#fcfcfb"); ax.set_facecolor("#fcfcfb")
        for (a, sym), e in egriler.items():
            if a != ad:
                continue
            ax.plot(e.index, e.values, color=renk[sym], lw=2, label=sym)
            ax.annotate(f"{sym} {e.values[-1]:+.0f}R", (e.index[-1], e.values[-1]), xytext=(4, 0),
                        textcoords="offset points", fontsize=9, color="#0b0b0b", va="center")
        ax.axhline(0, color="#52514e", lw=0.8)
        ax.grid(axis="y", color="#e5e4df", lw=0.6)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.spines["left"].set_color("#c3c2b7"); ax.spines["bottom"].set_color("#c3c2b7")
        ax.tick_params(colors="#52514e", labelsize=9)
        ax.set_ylabel("Kümülatif getiri (R, masraflar dahil)", color="#52514e")
        ax.set_title(f"{ad} — sermaye eğrisi (işlem başına 1R risk)", loc="left", color="#0b0b0b", fontsize=12)
        ax.legend(frameon=False, fontsize=9, loc="upper left")
        fig.tight_layout()
        fig.savefig(SONUC / f"egri_{ad}.png")
        plt.close(fig)


if __name__ == "__main__":
    main()
