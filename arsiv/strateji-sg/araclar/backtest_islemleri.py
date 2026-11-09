"""Panel için standart backtest işlem listesi: ortak/backtest_islemleri.csv (KGT v3 işlemleri + KMN 14 günlük dönemleri).

KGT: 6 gün başlangıçlı topluluğun tüm işlemleri (sonuclar/kripto/islemler_KGT_v3_topluluk.csv). getiri = işlem kâr/zararı /
  alt portföyün girişteki özsermayesi (masraf + fonlama dahil); risk = 0.004 (işlem başına alt portföy riski);
  sermaye_payi = 1/6 (alt portföyün toplam KGT sermayesindeki payı). Toplam KGT'ye katkı = getiri x sermaye_payi.
KMN: 14 dengeleme kaydırmasının her biri için dengelemeden bir sonraki dengelemeye dönem getirisi (ağırlık kayması, devir
  masrafı ve fonlama dahil; backtest.momentum.getiri_kayma ile aynı). R boş; risk = brüt maruziyet (1.0, kaldıraçsız);
  sermaye_payi = 1/14. Dönem sonu = bir sonraki dengeleme günü kapanışı (00:00 UTC).
Kullanım: python3 -m araclar.backtest_islemleri
"""
from pathlib import Path
import numpy as np
import pandas as pd
from backtest import momentum as M, kripto_strateji as ks

KOK = Path(__file__).resolve().parent.parent
KMN = dict(mod="notr", N=30, L=14, S=0, K=5, H=14, agirlik="ters_oyn", skor="risk", gecmis_gun=90, kayma=True)


def main():
    t = pd.read_csv(KOK / "sonuclar" / "kripto" / "islemler_KGT_v3_topluluk.csv")
    kgt = pd.DataFrame(dict(strateji_kod="KGT", giris_zamani=t.giris_zaman, cikis_zamani=t.cikis_zaman, R=t.R,
                            getiri=t.pnl_ozs, risk=0.004, sermaye_payi=1 / 6, alt_portfoy="gun_bas_" + t.gun_bas.astype(str),
                            sembol=t.sembol, sebep=t.sebep))
    D = M.gunluk_panel(ks.yukle())
    satir = []
    for k in range(KMN["H"]):
        W = M.agirliklar(D, KMN, k)
        r = M.getiri_kayma(D, W)
        brut = W.abs().sum(axis=1)
        reb = W.index[(np.arange(len(W)) % KMN["H"] == k) & (brut.to_numpy() > 0)]
        for a, b in zip(reb[:-1], reb[1:]):
            g = (1 + r[(r.index > a) & (r.index <= b)]).prod() - 1
            satir.append(dict(strateji_kod="KMN", giris_zamani=a + pd.Timedelta(days=1), cikis_zamani=b + pd.Timedelta(days=1),
                              R=np.nan, getiri=g, risk=float(brut.loc[a]), sermaye_payi=1 / KMN["H"],
                              alt_portfoy=f"kaydirma_{k}", sembol="", sebep="dengeleme"))
    kmn = pd.DataFrame(satir)
    d = pd.concat([kgt, kmn]).sort_values(["strateji_kod", "giris_zamani"])
    (KOK / "ortak").mkdir(exist_ok=True)
    d.to_csv(KOK / "ortak" / "backtest_islemleri.csv", index=False, float_format="%.6g")
    print(d.groupby("strateji_kod").agg(n=("getiri", "size"), ort=("getiri", "mean"), ilk=("giris_zamani", "min"),
                                        son=("cikis_zamani", "max")))


if __name__ == "__main__":
    main()
