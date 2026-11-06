"""Hızlı deneme: python3 -m tv.hizli <strateji> [SEMBOL ...] → tek enstrümanda işlem sayısı, kâr, KF (tam değerlendirme: tv.calistir)."""
import sys, importlib, numpy as np, pandas as pd
from tv import motor, veri, calistir
def main():
    ad = sys.argv[1]; syms = sys.argv[2:]
    mod = importlib.import_module(f"tv.stratejiler.{ad}")
    ev = calistir.evren(mod)
    if syms: ev = [e for e in ev if e[1] in syms]
    P = dict(mod.PARAM); tum = []
    for g, s, d in ev:
        S = mod.sinyal(d, **P)
        for B in (S["bacaklar"] if "bacaklar" in S else [S]):
            r = motor.calistir(d, B, g, s, 1.0, getattr(mod, "YON", 0), len(ev))
            t = motor.islem_tablosu(r)
            if len(t): tum.append(t)
        n = sum(len(x) for x in tum if (x.sembol == s).all())
        k = sum(x.kar.sum() for x in tum if (x.sembol == s).all())
        print(f"{s:8s} bar={len(d):6d} işlem={n:4d} kâr={k:9.1f}")
    if tum:
        T = pd.concat(tum); w = T.kar[T.kar > 0].sum(); l = -T.kar[T.kar < 0].sum()
        print(f"TOPLAM işlem={len(T)} kâr={T.kar.sum():.0f} KF={w/l if l>0 else np.inf:.2f} kazanma={(T.kar>0).mean():.2f}")
main()
