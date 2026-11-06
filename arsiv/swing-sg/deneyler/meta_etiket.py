"""Meta-etiketleme denemesi: swing sinyallerinden hangisinin kazanacağını öğrenen filtre.

Strateji kuralları aynı kalır; model her sinyale sinyal günündeki bilgilerle kazanma olasılığı verir.
Eğitim 2015-2022 (IS), test 2023+ (OOS). Eşik ve boyutlama yalnız IS içi zaman sıralı çapraz doğrulamayla seçilir.
Karşılaştırma: mevcut sistem / filtreli sistem (düşük puanlı sinyal atlanır) / puana göre boyutlama.
"""
import sys
from copy import copy
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from swing import gostergeler as g  # noqa: E402
from swing.ayarlar import S1, S2, S3, SINIFLAR  # noqa: E402
from swing.calistir import OOS_BASLANGIC, islemler, veriler  # noqa: E402
from swing.motor import istatistik, portfoy  # noqa: E402
from swing.veri import ENDEKS_VERI  # noqa: E402

STR = {"S1_geri_cekilme": 0, "S2_kirilim": 1, "S3_asiri_satim": 2}
SNF = {"kripto": 0, "mag7": 1, "bist": 2, "emtia": 3}


def ozellik_tablolari():
    out = {}
    for ad, (df, sinif) in veriler().items():
        c, v = df["Close"], df["Volume"]
        a = g.atr(df, 14)
        e = ENDEKS_VERI.get(sinif)
        ec = e["Close"].reindex(df.index, method="ffill") if e is not None else c
        out[ad] = pd.DataFrame({
            "atr_pct": a / c, "rsi14": g.rsi(c, 14), "rsi2": g.rsi(c, 2),
            "d_ema20": c / g.ema(c, 20) - 1, "d_ema50": c / g.ema(c, 50) - 1, "d_sma200": c / g.sma(c, 200) - 1,
            "mom20": c / c.shift(20) - 1, "mom60": c / c.shift(60) - 1,
            "hacim": v / g.sma(v, 20), "vol_oran": g.atr(df, 5) / g.atr(df, 50),
            "end_mom20": ec / ec.shift(20) - 1, "end_d_sma50": ec / g.sma(ec, 50) - 1,
            "hafta_mom": c / c.shift(5) - 1, "gun": pd.Series(df.index.dayofweek, index=df.index),
        }, index=df.index)
    return out


def tablo(trades, F):
    rows = []
    for i, t in enumerate(trades):
        f = F[t.varlik]
        once = f.index[f.index < t.giris_tarih]
        if not len(once):
            continue
        x = f.loc[once[-1]].to_dict()  # sinyal günü (girişten önceki kapanış) bilgisi
        x.update(strateji=STR[t.strateji], sinif=SNF[t.sinif], stop_mes=abs(t.giris - t.stop0) / t.giris,
                 i=i, tarih=t.giris_tarih, y=float(t.R > 0))
        rows.append(x)
    return pd.DataFrame(rows)


PRM = dict(objective="binary", learning_rate=0.03, num_leaves=7, min_data_in_leaf=60, feature_fraction=0.8,
           bagging_fraction=0.8, bagging_freq=1, lambda_l2=5.0, verbose=-1, seed=0)
FEAT = None


def egit(D):
    return lgb.train(PRM, lgb.Dataset(D[FEAT], D["y"]), num_boost_round=150)


if __name__ == "__main__":
    tr = []
    for s, prm in (("S1_geri_cekilme", S1), ("S2_kirilim", S2), ("S3_asiri_satim", S3)):
        tr += islemler(s, prm, SINIFLAR[s])
    F = ozellik_tablolari()
    D = tablo(tr, F)
    FEAT = [c for c in D.columns if c not in ("i", "tarih", "y")]
    IS = D[D["tarih"] < OOS_BASLANGIC]
    OOS = D[D["tarih"] >= OOS_BASLANGIC]
    # IS içinde yürüyen doğrulama: her yıl için önceki yıllarla eğit, o yılı tahmin et
    IS = IS.copy()
    IS["p"] = np.nan
    for yil in range(2018, 2023):
        egt = IS[IS["tarih"] < pd.Timestamp(f"{yil}-01-01") - pd.Timedelta(days=35)]
        te = IS["tarih"].dt.year == yil
        if len(egt) > 200:
            IS.loc[te, "p"] = egit(egt).predict(IS.loc[te, FEAT])
    isv = IS.dropna(subset=["p"])
    from scipy.stats import spearmanr  # noqa
    print(f"IS yürüyen doğrulama: {len(isv)} sinyal, puan–kazanç Spearman {spearmanr(isv['p'], isv['y']).correlation:+.3f}")
    for q in (0.2, 0.3, 0.4):
        esik = isv["p"].quantile(q)
        alt, ust = isv[isv["p"] <= esik], isv[isv["p"] > esik]
        print(f"  alt %{q*100:.0f}: KO %{alt['y'].mean()*100:.1f}  üst: KO %{ust['y'].mean()*100:.1f}")
    esik_q = 0.3
    esik = isv["p"].quantile(esik_q)
    # Son model: tüm IS ile eğit, OOS'u puanla (OOS seçimde hiç kullanılmadı)
    m = egit(IS)
    OOS = OOS.copy()
    OOS["p"] = m.predict(OOS[FEAT])
    print(f"OOS: {len(OOS)} sinyal, Spearman {spearmanr(OOS['p'], OOS['y']).correlation:+.3f}, "
          f"alt %30 KO %{OOS[OOS['p'] <= esik]['y'].mean()*100:.1f} / üst KO %{OOS[OOS['p'] > esik]['y'].mean()*100:.1f}")
    puan = {int(r.i): r.p for r in pd.concat([isv, OOS]).itertuples()}

    def sistem(ad, secim):
        o = [t for j, t in enumerate(tr) if t.giris_tarih >= OOS_BASLANGIC and secim(j)]
        p = portfoy(o)
        s_ = istatistik(o)
        print(f"{ad:34s} OOS n={s_['islem']:4d} KO %{s_['kazanma_orani']*100:4.1f} ortR {s_['ort_R']:+.2f} | "
              f"yıllık %{p['yillik_getiri']*100:4.1f} düşüş %{p['max_dusus']*100:5.1f} Sharpe {p['sharpe_aylik']:.2f}")
    sistem("Mevcut sistem", lambda j: True)
    sistem("Filtre: alt %30 puan atlanır", lambda j: puan.get(j, 1) > esik)
    # Boyutlama: puana göre R ölçekle (yüksek puan 1,5x, düşük 0,5x) — getiri ölçeklenir, risk bütçesi ortalamada aynı
    yuksek = isv["p"].quantile(0.7)
    o = []
    for j, t in enumerate(tr):
        if t.giris_tarih < OOS_BASLANGIC:
            continue
        u = copy(t)
        p_ = puan.get(j, esik)
        k = 1.5 if p_ > yuksek else (0.5 if p_ <= esik else 1.0)
        u.stop0 = t.giris - (t.giris - t.stop0) / k  # stop mesafesi küçülünce portföy aynı riskle daha büyük pozisyon alır
        o.append(u)
    p = portfoy(o)
    print(f"{'Boyutlama: puana göre 0,5x/1x/1,5x':34s} OOS yıllık %{p['yillik_getiri']*100:4.1f} düşüş %{p['max_dusus']*100:5.1f} Sharpe {p['sharpe_aylik']:.2f}")
    onem = pd.Series(m.feature_importance("gain"), index=FEAT).sort_values(ascending=False)
    print("En etkili özellikler:", ", ".join(f"{k}" for k in onem.index[:6]))
