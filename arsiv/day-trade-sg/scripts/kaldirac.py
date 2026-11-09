"""Kaldıraç testi (vadeli, izole teminat). Girdi: scripts/kaldirac_islem.py çıktıları.

(a) Aynı risk: kaldıraç yalnız teminatı azaltır. Tasfiye mesafesi = 1/L − %0,5; stop mesafesi
    bundan büyükse ve işlem içi en düşük fiyat (15dk low) bu seviyeye indiyse işlem tasfiye:
    getiri = −1/L (nominal) − maliyet. Fonlama: geçilen her 8s periyot için nominalin %0,01'i.
(b) Büyütme: işlem riski × L, tek/toplam maruziyet sınırları × L; günlük −%3 limiti × L (b1)
    veya sabit (b2). Tasfiye kuralı (a) ile aynı.

  python scripts/kaldirac.py <k21_0.pkl> <k21_200.pkl> <k23_0.pkl> <k23_200.pkl>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from daytrade.secili import PORTFOY  # noqa: E402
from kagit.motor import portfoy_ayri  # noqa: E402

LS = [1, 2, 3, 5, 10]
FON = 0.0001        # 8 saatlik fonlama ~%0,01 (nominal)
TAMPON = 0.005      # bakım teminatı / tasfiye tamponu
VADELI = 0.0005
ST = {"S10": "S10_trendday", "S13": "S13_falsebreak", "S15": "S15_tdpullback"}


def kaldirac_uygula(tr, L):
    t = tr.copy()
    stop = t["risk"] / t["entry"]
    t["R"] = t["R"] - FON * t["fonlama_n"] / stop
    t["tasfiye"] = False
    if L > 1:
        liq = 1 / L - TAMPON
        dus = (t["entry"] - t["en_dusuk"]) / t["entry"]
        m = (stop > liq) & (dus >= liq)
        t.loc[m, "R"] = (-1 / L - 2 * VADELI - FON * t.loc[m, "fonlama_n"]) / stop[m]
        t.loc[m, "tasfiye"] = True
    return t


def olc(al, bas, bit, sermaye):
    gun = pd.date_range(bas.floor("D"), bit.floor("D"), freq="D", tz="UTC")
    pnl = (al.groupby(al["exit_time"].dt.floor("D"))["kar_usd"].sum()
           .reindex(gun, fill_value=0.0) if len(al) else pd.Series(0.0, index=gun))
    eq = sermaye + pnl.cumsum()
    if (eq <= 0).any():
        return dict(cagr=-1.0, dd=-1.0, sharpe=np.nan, n=len(al),
                    tasfiye=int(al["tasfiye"].sum()) if len(al) else 0)
    yil = len(gun) / 365
    r = eq.pct_change().fillna(eq.iloc[0] / sermaye - 1)
    return dict(cagr=(eq.iloc[-1] / sermaye) ** (1 / yil) - 1,
                dd=(eq / np.maximum.accumulate(np.r_[sermaye, eq.to_numpy()])[1:] - 1).min(),
                sharpe=r.mean() / r.std() * np.sqrt(365) if r.std() > 0 else np.nan,
                n=len(al), tasfiye=int(al["tasfiye"].sum()) if len(al) else 0)


def kosu(tr, L, senaryo, bas, bit):
    t = kaldirac_uygula(tr[(tr["entry_time"] >= bas) & (tr["entry_time"] < bit)], L)
    c = dict(PORTFOY)
    if senaryo.startswith("b"):
        c.update(risk=c["risk"] * L, max_agirlik=c["max_agirlik"] * L,
                 max_toplam_agirlik=c["max_toplam_agirlik"] * L)
        if senaryo == "b1":
            c["gunluk_zarar_limiti"] = c["gunluk_zarar_limiti"] * L
    al = portfoy_ayri(t, c)
    return olc(al, bas, bit, c["sermaye"])


def main():
    k21_0, k21_2, k23_0, k23_2 = (pd.read_pickle(p) for p in sys.argv[1:5])
    T = pd.Timestamp
    donem = {
        "2021-01→2023-09": (T("2021-01-01", tz="UTC"), T("2023-10-01", tz="UTC"), "k21"),
        "2022 (stres)": (T("2022-01-01", tz="UTC"), T("2023-01-01", tz="UTC"), "k21"),
        "2023-10→2026-10": (T("2023-10-20", tz="UTC"), T("2026-10-06", tz="UTC"), "k23"),
    }
    veri = {("k21", ""): k21_0, ("k21", "R200"): k21_2, ("k23", ""): k23_0, ("k23", "R200"): k23_2}

    print("## Stop mesafesi dağılımı (giriş fiyatına göre %, yalnız alınabilecek tüm sinyaller)")
    print("| Strateji | Dönem | n | medyan | %75 | %95 | %99 | maks | güvenli L (%95) | güvenli L (%99) |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for kod, st in list(ST.items()) + [("Birleşik", None)]:
        for dn, kk in (("2021-01→2023-09", "k21"), ("2023-10→2026-10", "k23")):
            t = veri[(kk, "")]
            t = t if st is None else t[t["strategy"] == st]
            s = (t["risk"] / t["entry"]).to_numpy()
            q = np.quantile(s, [.5, .75, .95, .99])
            guv = [max([L for L in LS if qq < 1 / L - TAMPON] or [0]) for qq in q[2:]]
            print(f"| {kod} | {dn} | {len(s)} | {q[0]:.2%} | {q[1]:.2%} | {q[2]:.2%} | {q[3]:.2%} "
                  f"| {s.max():.2%} | {guv[0]}x | {guv[1]}x |")

    print("\n## İşlem düzeyi tasfiye (tüm sinyaller, portföy öncesi)")
    print("| Strateji | Dönem | " + " | ".join(f"{L}x" for L in LS[1:]) + " |")
    print("|---|---|" + "---|" * (len(LS) - 1))
    for kod, st in list(ST.items()) + [("Birleşik", None)]:
        for dn, kk in (("2021-01→2023-09", "k21"), ("2023-10→2026-10", "k23")):
            t = veri[(kk, "")]
            t = t if st is None else t[t["strategy"] == st]
            hs = []
            for L in LS[1:]:
                m = kaldirac_uygula(t, L)["tasfiye"]
                hs.append(f"{int(m.sum())} ({m.mean():.1%})")
            print(f"| {kod} | {dn} | " + " | ".join(hs) + " |")

    for senaryo, ad in (("a", "(a) Aynı risk — kaldıraç yalnız teminatı azaltır"),
                        ("b1", "(b1) Büyütme — risk, maruziyet ve günlük limit × L"),
                        ("b2", "(b2) Büyütme — risk ve maruziyet × L, günlük limit sabit −%3")):
        print(f"\n## {ad}")
        print("Hücre: yıllık getiri / maks. düşüş / Sharpe / tasfiye\n")
        for rj in ("", "R200"):
            print(f"\n### {'BTC SMA200 filtreli' if rj else 'Mevcut (filtresiz)'}")
            print("| Strateji | Dönem | " + " | ".join(f"{L}x" for L in LS) + " |")
            print("|---|---|" + "---|" * len(LS))
            for kod, st in list(ST.items()) + [("Birleşik", None)]:
                for dn, (bas, bit, kk) in donem.items():
                    t = veri[(kk, rj)]
                    t = t if st is None else t[t["strategy"] == st]
                    hs = []
                    for L in LS:
                        m = kosu(t, L, senaryo, bas, bit)
                        hs.append(f"{m['cagr']:+.1%} / {m['dd']:.1%} / {m['sharpe']:.2f} / {m['tasfiye']}")
                    print(f"| {kod} | {dn} | " + " | ".join(hs) + " |")


if __name__ == "__main__":
    main()
