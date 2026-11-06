"""Beklenti konisi ve batma olasılığı: her hesabın backtest günlük getirilerinden blok bootstrap Monte Carlo.

Kaynaklar (2023+ örneklem-dışı dönem; day trade 2023-10-20+):
  swing   : swing motoru portföy simülasyonu (S1+S2+S3, %1 risk)
  trend   : trend/birlesim kolları (BTC, ABD, emtia) eşit ağırlık
  algo    : algo-sg ortak/backtest_islemleri.csv  (A ve B kolları %50/%50; getiri kol özsermayesine göre)
  daytrade: day-trade-sg ortak/backtest_islemleri.csv (S10/S13/S15 filtresiz; ozs_getiri alt hesaba göre, 3 alt hesap)
  strateji: strateji-sg ortak/backtest_islemleri.csv (KGT %50: 6 alt portföy; KMN %50: 14 kaydırmalı defter)
Çıktı: karsilastirma/koni.json — gün 0..62 için %5/%25/%50/%75/%95 birikimli getiri; 60 gün / 1 yılda −%10, −%20 düşüşe
ulaşma olasılığı (1x/2x/3x kaldıraç).
"""
import io
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK / "swing-sg"))
BAS = pd.Timestamp("2023-01-01")
DALLAR = {"algo-sg": "claude/optimistic-franklin-9w0pdk", "day-trade-sg": "claude/confident-ramanujan-j7tq1t",
          "strateji-sg": "claude/dreamy-cannon-lsimjy"}


def ortak(repo, dosya="backtest_islemleri.csv"):
    d = DALLAR[repo]
    subprocess.run(["git", "-C", str(KOK / repo), "fetch", "-q", "origin", f"+refs/heads/{d}:refs/remotes/origin/{d}"], check=False)
    t = subprocess.run(["git", "-C", str(KOK / repo), "show", f"origin/{d}:ortak/{dosya}"],
                       capture_output=True, text=True, check=True).stdout
    return pd.read_csv(io.StringIO(t))


def gunluk(seri, bas):
    """Çıkış gününe göre toplanmış getirileri takvim günlük seriye çevirir (işlemsiz gün 0)."""
    s = seri.groupby(seri.index.normalize()).sum()
    idx = pd.date_range(max(bas, s.index.min()), s.index.max(), freq="D")
    return s.reindex(idx, fill_value=0.0)


def swing_r():
    from swing.ayarlar import S1, S2, S3, SINIFLAR
    from swing.calistir import islemler
    from swing.motor import portfoy
    tr = []
    for s, p in (("S1_geri_cekilme", S1), ("S2_kirilim", S2), ("S3_asiri_satim", S3)):
        tr += islemler(s, p, SINIFLAR[s])
    tr = [t for t in tr if t.giris_tarih >= BAS]
    p = portfoy(tr, detay=True)
    pnl = pd.Series([x[3] / x[2] for x in p["alinanlar"]],
                    index=pd.DatetimeIndex([x[0].cikis_tarih for x in p["alinanlar"]]))
    return gunluk(pnl, BAS)  # gerçekleşen getiri, giriş anındaki özsermayeye göre


def trend_r():
    import importlib
    B = importlib.import_module("trend.birlesim")
    k = pd.concat([B.kol_btc(), B.kol_abd_trend(), B.kol_emtia_dusukvol()], axis=1).fillna(0.0)
    r = k.mean(axis=1)
    r = r[r.index >= BAS]
    return r.reindex(pd.date_range(r.index.min(), r.index.max(), freq="D"), fill_value=0.0)


ALGO_OLCEK = 0.211 / 0.489  # dosyada pozisyon sınırı (en fazla 10/25) yok; ekibin portföy sonucuna (yıllık %21,1) ölçeklenir


def algo_r():
    t = ortak("algo-sg")
    s = pd.Series(t["getiri"].values * 0.5 * ALGO_OLCEK, index=pd.to_datetime(t["cikis_zamani"]).dt.tz_localize(None))
    return gunluk(s, BAS)


def daytrade_r():
    t = ortak("day-trade-sg")
    t = t[t["strateji_kod"].isin(["S10", "S13", "S15"])]
    s = pd.Series(t["ozs_getiri"].values / 3.0, index=pd.to_datetime(t["cikis_zamani"]).dt.tz_localize(None))
    return gunluk(s, pd.Timestamp("2023-10-20"))


def strateji_r():
    # ekibin günlük bileşik, her gün dengelenmiş KGT+KMN 50/50 serisi (işlem toplamından daha doğru)
    t = ortak("strateji-sg", "backtest_gunluk_getiri.csv")
    t.index = pd.to_datetime(t.iloc[:, 0])
    r = t["KGT_KMN_50_50"].astype(float)
    return r[r.index >= BAS]


def bootstrap(r, ufuk, n=3000, blok=5, kaldirac=1.0, seed=0):
    rng = np.random.default_rng(seed)
    x = r.values * kaldirac
    m = len(x)
    bloklar = int(np.ceil(ufuk / blok))
    bas = rng.integers(0, m - blok, size=(n, bloklar))
    yollar = np.stack([x[b:b + blok] for b in bas.ravel()]).reshape(n, bloklar * blok)[:, :ufuk]
    return np.cumprod(1 + yollar, axis=1)


def ozet(r):
    yol = bootstrap(r, 62)
    yol = np.concatenate([np.ones((yol.shape[0], 1)), yol], axis=1)
    q = np.percentile(yol - 1, [5, 25, 50, 75, 95], axis=0)
    # Backtest serileri kârı işlemin kapandığı güne yazar (çok gün sıfır); canlı hesap ise açık pozisyonu her gün
    # değerler. Kısa ufukta bu koniyi yapay olarak daraltır, bu yüzden bant normal yaklaşımla (μg ± zσ√g) genişletilir.
    g = np.arange(q.shape[1]); mu, sd = r.mean(), r.std()
    for i, z in ((0, -1.645), (1, -0.674), (3, 0.674), (4, 1.645)):
        nrm = mu * g + z * sd * np.sqrt(g)
        q[i] = np.minimum(q[i], nrm) if z < 0 else np.maximum(q[i], nrm)
    koni = [[g] + [round(float(q[i, g]), 5) for i in range(5)] for g in range(yol.shape[1])]
    ruin = {}
    for L in (1, 2, 3):
        for ufuk, ad in ((60, "60g"), (365, "1y")):
            y = bootstrap(r, ufuk, n=2000, kaldirac=L, seed=L)
            dd = (y / np.maximum.accumulate(np.maximum(y, 1.0), axis=1) - 1).min(axis=1)
            ruin[f"{L}x_{ad}"] = {"-10": round(float((dd <= -0.10).mean()), 3), "-20": round(float((dd <= -0.20).mean()), 3),
                                  "-30": round(float((dd <= -0.30).mean()), 3)}
    yillik = (1 + r).prod() ** (365 / len(r)) - 1
    return dict(koni=koni, ruin=ruin, gun_sayisi=int(len(r)), yillik=round(float(yillik), 4),
                baslangic=str(r.index.min().date()), bitis=str(r.index.max().date()))


if __name__ == "__main__":
    out = {}
    for ad, f in (("swing", swing_r), ("trend", trend_r), ("algo", algo_r), ("daytrade", daytrade_r), ("strateji", strateji_r)):
        try:
            r = f()
            out[ad] = ozet(r)
            k = out[ad]["koni"][60]
            print(f"{ad:9s} {out[ad]['baslangic']}→{out[ad]['bitis']} yıllık %{out[ad]['yillik']*100:5.1f} | 60. gün %5 {k[1]:+.1%} medyan {k[3]:+.1%} %95 {k[5]:+.1%} | "
                  f"60 günde −%10 olasılığı 1x {out[ad]['ruin']['1x_60g']['-10']:.0%} 2x {out[ad]['ruin']['2x_60g']['-10']:.0%} 3x {out[ad]['ruin']['3x_60g']['-10']:.0%}")
        except Exception as e:  # bir kaynak bozuksa diğerleri yine üretilir
            print(f"{ad}: HATA {e}")
    Path(__file__).with_name("koni.json").write_text(json.dumps(out, ensure_ascii=False))
