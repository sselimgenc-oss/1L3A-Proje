"""Hayatta kalma yanlılığı stres testi: swing stratejileri (aynı parametreler) bugün ilk 25'te olmayan /
çöken / listeden çıkan 25 coin üzerinde. Ana kripto evreniyle karşılaştırılır."""
import glob
import os

import pandas as pd

from swing.ayarlar import SECILI, SINIFLAR
from swing.calistir import OOS_BASLANGIC, islemler
from swing.motor import calistir, istatistik, portfoy
from swing.stratejiler import STRATEJILER
from swing.veri import ENDEKS_VERI, KOK, MALIYET, tum_veriler, yukle


def stres_islemleri():
    tum_veriler()  # ENDEKS_VERI'yi (BTC rejimi) doldurur
    out = []
    for f in sorted(glob.glob(os.path.join(KOK, "data", "stres", "*.csv"))):
        ad = os.path.basename(f)[:-4]
        df = yukle(ad, os.path.dirname(f))
        df = df[df.index >= "2017-01-01"]
        if len(df) < 300:
            continue
        for st, p in SECILI.items():
            if "kripto" not in SINIFLAR[st]:
                continue
            sig = STRATEJILER[st](df, {**p, "_endeks": ENDEKS_VERI.get("kripto")})
            out += calistir(ad, "kripto", df, sig, MALIYET["kripto"], st)
    return out


def satir(ad, tr):
    rows = []
    for per, f in (("tüm", lambda t: True), ("IS", lambda t: t.giris_tarih < OOS_BASLANGIC),
                   ("OOS", lambda t: t.giris_tarih >= OOS_BASLANGIC)):
        s = istatistik([t for t in tr if f(t)])
        if s.get("islem"):
            rows.append(dict(evren=ad, donem=per, islem=s["islem"], kazanma=f"{s['kazanma_orani']:.1%}",
                             PF_R=f"{s['kar_faktoru_R']:.2f}", ort_R=f"{s['ort_R']:+.2f}"))
    return rows


if __name__ == "__main__":
    ana = []
    for st, p in SECILI.items():
        if "kripto" in SINIFLAR[st]:
            ana += islemler(st, p, ["kripto"])
    stres = stres_islemleri()
    rows = satir("Ana evren (bugünün ilk 25'i)", ana) + satir("Stres evreni (25 eski/çöken coin)", stres)
    for st in SECILI:
        rows += satir(f"  stres — {st}", [t for t in stres if t.strateji == st])
    d = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(d.to_string(index=False))
    p_ana, p_st = portfoy(ana), portfoy(stres)
    print(f"Portföy ana: CAGR {p_ana['yillik_getiri']:.1%} DD {p_ana['max_dusus']:.1%} | "
          f"stres: CAGR {p_st['yillik_getiri']:.1%} DD {p_st['max_dusus']:.1%}")
    with open(os.path.join(KOK, "deneyler", "HAYATTA_KALMA.md"), "w", encoding="utf-8") as f:
        f.write("# Hayatta kalma yanlılığı stres testi (swing, kripto)\n\n"
                "Aynı parametreler; stres evreni: LUNA, FTT, EOS, XMR, MATIC, WAVES, ALGO, THETA, XTZ, VET, ATOM, FIL, "
                "EGLD, AXS, SAND, MANA, CRV, SNX, COMP, MKR, ZEC, DASH, NEO, IOTA, KSM (Yahoo, 2017+).\n\n")
        f.write(d.to_markdown(index=False) + "\n\n")
        f.write(f"Portföy (yalnız kripto işlemleri, %1 risk): ana CAGR {p_ana['yillik_getiri']:.1%} / DD "
                f"{p_ana['max_dusus']:.1%} — stres CAGR {p_st['yillik_getiri']:.1%} / DD {p_st['max_dusus']:.1%}\n")
