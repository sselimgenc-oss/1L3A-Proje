"""Panel için standart backtest işlem listesi: ortak/backtest_islemleri.csv.

Girdi: scripts/kaldirac_islem.py çıktıları (vadeli maliyet %0,05/yön). Kağıt bot spot maliyetle
(%0,08/yön) çalıştığı için R spota çevrilir: R −= 2·0,0003·giriş/risk (çıkış≈giriş yaklaşımı).
Portföy kuralları botla aynı (PORTFOY, ayrı alt hesap); yalnız portföyün aldığı işlemler yazılır.
  getiri = işlemin fiyat getirisi (maliyet dahil) = R · stop%
  risk   = işlemin özsermaye riski = ağırlık · stop% (≤ %0,5)
  ozs_getiri = işlemin özsermayeye etkisi = getiri · ağırlık

  python scripts/ortak_islemler.py k21_0.pkl k21_200.pkl k23_0.pkl k23_200.pkl
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402

from daytrade.secili import PORTFOY  # noqa: E402
from kagit.motor import portfoy_ayri  # noqa: E402

SPOT, VADELI = 0.0008, 0.0005
KOD = {"S10_trendday": "S10", "S13_falsebreak": "S13", "S15_tdpullback": "S15"}
k21_0, k21_2, k23_0, k23_2 = (pd.read_pickle(p) for p in sys.argv[1:5])
out = []
for ek, a, b in (("", k21_0, k23_0), ("_sma200", k21_2, k23_2)):
    t = pd.concat([a[a["entry_time"] >= "2021-01-01"], b], ignore_index=True)
    stop = t["risk"] / t["entry"]
    t["R"] = t["R"] - 2 * (SPOT - VADELI) * t["entry"] / t["risk"]
    t = t[2 * SPOT / stop <= 0.2]                      # botun max_cost_R filtresi
    al = portfoy_ayri(t, dict(PORTFOY))
    s = al["risk"] / al["entry"]
    out.append(pd.DataFrame({
        "strateji_kod": al["strategy"].map(KOD) + ek,
        "giris_zamani": al["entry_time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cikis_zamani": (al["exit_time"] + pd.Timedelta(minutes=15)).dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "R": al["R"].round(4),
        "getiri": (al["R"] * s).round(6),
        "risk": (al["agirlik"] * s).round(6),
        "sembol": al["symbol"],
        "ozs_getiri": (al["R"] * s * al["agirlik"]).round(6),
    }))
o = pd.concat(out).sort_values(["strateji_kod", "giris_zamani"])
o.to_csv("ortak/backtest_islemleri.csv", index=False)
print(o.groupby("strateji_kod").agg(n=("R", "size"), wr=("R", lambda r: (r > 0).mean()),
                                     ortR=("R", "mean"), risk=("risk", "mean"),
                                     bas=("giris_zamani", "min"), son=("giris_zamani", "max")).round(3))
