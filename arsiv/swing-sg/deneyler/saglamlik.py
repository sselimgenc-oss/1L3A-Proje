"""Sağlamlık: (1) parametre duyarlılığı (her parametre tek tek oynatılır), (2) 2x maliyet, (3) Monte Carlo."""
import numpy as np
import pandas as pd
from swing import veri
from swing.ayarlar import SECILI, SINIFLAR
from swing.calistir import islemler
from swing.motor import istatistik, portfoy

OYNAT = {
    "S1_geri_cekilme": dict(hizli=[8, 12, 20], rsi_esik=[55, 60, 70], kismi_R=[0.75, 1.25], stop_atr=[0.5, 1.5],
                            max_gun=[20, 40], bakis=[2, 4]),
    "S2_kirilim": dict(kanal=[15, 25, 30], sikisma=[0.8, 1.0], kismi_R=[1.0, 2.0], stop_atr=[1.5, 2.5],
                       iz_atr=[3, 5], cikis_kanal=[10, 30]),
    "S3_asiri_satim": dict(esik=[5, 15], trend_sma=[150, 250], stop_atr=[1.5, 2.5], limit_atr=[0.25, 0.75],
                           cikis_sma=[5, 15], max_gun=[7, 15]),
}
rows = []
for st, p in SECILI.items():
    b = istatistik(islemler(st, p, SINIFLAR[st]))
    rows.append(dict(strateji=st, param="TABAN", deger="", n=b["islem"], WR=b["kazanma_orani"], R=b["ort_R"]))
    for k, vals in OYNAT[st].items():
        for v in vals:
            s = istatistik(islemler(st, {**p, k: v}, SINIFLAR[st]))
            rows.append(dict(strateji=st, param=k, deger=v, n=s["islem"], WR=s["kazanma_orani"], R=s["ort_R"]))
df = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(df.round(3).to_string(index=False))
df.to_csv("deneyler/saglamlik_param.csv", index=False)

# 2x maliyet
orj = dict(veri.MALIYET)
for k in veri.MALIYET:
    veri.MALIYET[k] = orj[k] * 2
hep = sum((islemler(st, p, SINIFLAR[st]) for st, p in SECILI.items()), [])
s, pf = istatistik(hep), portfoy(hep)
print(f"\n2x MALİYET: n={s['islem']} WR={s['kazanma_orani']:.1%} R={s['ort_R']:.2f} CAGR={pf['yillik_getiri']:.1%} DD={pf['max_dusus']:.1%}")
veri.MALIYET.update(orj)

# Monte Carlo: işlem getirilerini yeniden örnekle (bootstrap), sıralı R dizisinden maksimum düşüş dağılımı
hep = sum((islemler(st, p, SINIFLAR[st]) for st, p in SECILI.items()), [])
R = np.array([t.R for t in hep])
rng = np.random.default_rng(42)
dds, sons = [], []
for _ in range(2000):
    x = rng.choice(R, size=len(R), replace=True) * 0.01  # işlem başı %1 risk, sıralı (en kötü durum: eşzamanlılık yok)
    e = np.cumprod(1 + x)
    dds.append((e / np.maximum.accumulate(e) - 1).min())
    sons.append(e[-1])
print(f"Monte Carlo (sıralı, %1 risk): maxDD medyan={np.median(dds):.1%} %5 kötü={np.percentile(dds, 5):.1%}; "
      f"kayıpla biten oran={np.mean(np.array(sons) < 1):.1%}")
