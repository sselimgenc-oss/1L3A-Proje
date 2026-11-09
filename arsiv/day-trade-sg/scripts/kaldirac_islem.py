"""Kaldıraç testi için işlem üretici: seçili stratejiler, vadeli maliyet, işlem içi en kötü fiyat
ve fonlama periyodu sayısı. Çıktı: pickle.

  DAYTRADE_CACHE=... BTC_GUNLUK=... python scripts/kaldirac_islem.py <cikti.pkl> [--ekstra A,B] [--rejim 200]
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from daytrade.backtest import simulate  # noqa: E402
from daytrade.runner import bundle  # noqa: E402
from daytrade.secili import SECILI  # noqa: E402
from daytrade.strategies import STRATEGIES  # noqa: E402

VADELI = 0.0005   # taker ~%0,05/yön (kayma dahil kabul)

ap = argparse.ArgumentParser()
ap.add_argument("cikti")
ap.add_argument("--ekstra", default="")
ap.add_argument("--rejim", type=int, default=0)
a = ap.parse_args()
os.environ["EKSTRA"] = a.ekstra
from kripto_tara import kripto  # noqa: E402

out = []
for inst in kripto("15m"):
    df = bundle(inst, "15m")
    if df is None:
        continue
    low = df["low"].to_numpy()
    pos = pd.Series(np.arange(len(df)), index=df.index)
    for st, p in SECILI.items():
        prm = dict(p, rejim=a.rejim) if a.rejim else p
        tr = simulate(df, STRATEGIES[st][0](df, **prm), VADELI, inst.symbol, st)
        if tr.empty:
            continue
        i0 = pos.reindex(tr["entry_time"]).to_numpy()
        i1 = pos.reindex(tr["exit_time"]).to_numpy()
        tr["en_dusuk"] = [low[x:y + 1].min() for x, y in zip(i0, i1)]
        # fonlama: 00/08/16 UTC anlarından işlem süresince (çıkış anı hariç) geçilen sayı
        cik = tr["exit_time"] + pd.Timedelta(minutes=15)
        tr["fonlama_n"] = [len(pd.date_range(e.ceil("8h"), c - pd.Timedelta(seconds=1), freq="8h"))
                           for e, c in zip(tr["entry_time"], cik)]
        tr["asset_class"] = "crypto"
        sb = tr["entry_time"] - pd.Timedelta(minutes=15)
        f = df.reindex(sb)
        tr["skor"] = (tr["dir"].to_numpy() * ((f["close"] - f["dopen"]) / f["atr_d"]).to_numpy())
        out.append(tr)
t = pd.concat(out, ignore_index=True)
t.to_pickle(a.cikti)
print(a.cikti, len(t), t["entry_time"].min(), t["entry_time"].max())
