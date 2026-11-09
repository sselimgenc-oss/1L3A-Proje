"""Sağlamlık: BIST hisselerini USD'ye çevirip (TL enflasyon etkisini ayıklayarak) stratejileri yeniden test et."""
import pandas as pd
from swing.ayarlar import SECILI
from swing.motor import calistir, istatistik
from swing.stratejiler import STRATEJILER
from swing.veri import KOK, MALIYET, tum_veriler

kur = pd.read_csv(f"{KOK}/data/yardimci/USDTRY.csv", parse_dates=["Date"]).set_index("Date")["Close"]
for st, p in SECILI.items():
    tl, usd = [], []
    for ad, (df, sinif) in tum_veriler().items():
        if sinif != "bist":
            continue
        k = kur.reindex(df.index, method="ffill")
        du = df.copy()
        for c in ("Open", "High", "Low", "Close"):
            du[c] = df[c] / k
        du = du.dropna()
        f = STRATEJILER[st]
        tl += calistir(ad, sinif, df, f(df, p), MALIYET[sinif], st)
        usd += calistir(ad, sinif, du, f(du, p), MALIYET[sinif], st)
    for nm, tr in (("TL ", tl), ("USD", usd)):
        s = istatistik(tr)
        print(f"{st:16s} {nm} n={s['islem']:4d} WR={s['kazanma_orani']:.1%} PF_R={s['kar_faktoru_R']:.2f} ortR={s['ort_R']:+.2f}")
