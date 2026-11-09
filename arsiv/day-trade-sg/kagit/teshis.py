"""Teşhis: kağıt botu neden işlem açmıyor? (yalnız deneme iş akışında çalışır; durum yazmaz)

Aynı veriyle dört çeşitleme oynatılır ve gün gün işlem sayıları karşılaştırılır:
  canli      : botun gerçek ayarları
  btc_yok    : BTC 4s filtresi kapalı
  maliyet_yok: maliyet/risk eşiği (max_cost_R=0.2) gevşetilmiş
  ikisi      : ikisi birden
Ayrıca BTC 4s EMA20 > EMA50 koşulunun gün bazında açık olduğu oran yazılır.
"""
from __future__ import annotations

import copy
import functools
import json
import sys
from pathlib import Path

import pandas as pd

from kagit import motor as M


def oynat(insts, tf, bas, son, surumler, btc=True, maliyet=True):
    sv = copy.deepcopy(surumler)
    for s in sv:
        for cfg in s["stratejiler"].values():
            cfg.setdefault("params", {})["btc_filter"] = btc and cfg["params"].get("btc_filter", False)
    asil = M.simulate
    if not maliyet:
        M.simulate = functools.partial(asil, max_cost_R=10.0)
    try:
        tr, _ = M.islemleri_uret(insts, tf, bas, son, sv)
    finally:
        M.simulate = asil
    return tr


def main(dizin):
    dizin = Path(dizin)
    dizin.mkdir(parents=True, exist_ok=True)
    c, bas, bitis, surumler = M.ayar()
    insts = M.evren(dizin)
    tf = c["giris_tf"]
    M.veri_guncelle(insts, tf, bas)
    son = pd.Timestamp.now(tz="UTC").floor("15min")
    sonuc = {}
    for ad, b, m in [("canli", True, True), ("btc_yok", False, True), ("maliyet_yok", True, False), ("ikisi", False, False)]:
        tr = oynat(insts, tf, bas, son, surumler, btc=b, maliyet=m)
        if len(tr):
            g = pd.to_datetime(tr["entry_time"]).dt.date.astype(str)
            sonuc[ad] = g.value_counts().sort_index()
            print(f"{ad}: {len(tr)} işlem; strateji: {tr['strategy'].value_counts().to_dict() if 'strategy' in tr else '-'}")
        else:
            sonuc[ad] = pd.Series(dtype=int)
            print(f"{ad}: 0 işlem")
    T = pd.DataFrame(sonuc).fillna(0).astype(int).sort_index()
    b_inst = next(i for i in insts if i.symbol == "BTCUSDT")
    e, h1, h4 = M.D.load(b_inst, tf), M.D.load(b_inst, "1h"), M.D.load(b_inst, "4h")
    if h4 is None or len(h4) < 210:
        h4 = M.D.resample(h1, "4h")
    df = M.build(b_inst, e[e.index >= bas - pd.Timedelta(days=M.ISINMA_GUN)], h1, h4, tf)
    up = (df["h4_ema20"] > df["h4_ema50"]).astype(float)
    up = up[up.index >= bas].groupby(up[up.index >= bas].index.date).mean().round(2)
    up.index = up.index.astype(str)
    T["btc_4s_yukari_orani"] = up.reindex(T.index.union(up.index)).reindex(T.index)
    T = T.reindex(sorted(set(T.index) | set(up.index)))
    T["btc_4s_yukari_orani"] = up.reindex(T.index)
    T = T.fillna({k: 0 for k in sonuc})
    md = T.to_string()
    print(T.to_string())
    (dizin / "teshis.md").write_text(md)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/teshis")
