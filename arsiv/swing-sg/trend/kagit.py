"""Trend kolları kağıt al-sat motoru (10.000 $, 60 gün). Swing kağıt botundan tamamen bağımsızdır.

Her çalıştırmada veriler yeniden indirilir; kağıt döneminin başından bugüne kadar olan tüm kapanmış günlük mumlar
backtest koduyla (trend.motor, trend.stratejiler) yeniden oynatılır. Her kol kendi sermayesiyle çalışır.

  python -m trend.kagit --durum kagit_trend_durum
  KAGIT_BASLANGIC=2026-08-01 python -m trend.kagit --durum /tmp/d     # geçmiş dönemle deneme
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import motor as M
from . import stratejiler as S
from .test import rejim_serisi
from .veri import MALIYET, evren, panel, yukle

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK.parent / "scripts"))
from fetch_genis import EMTIA_ETF  # noqa: E402

KOL_AD = {"btc_trend": "BTC trend", "abd_trend": "ABD trend portföyü", "emtia_dusukvol": "Emtia ETF düşük vol."}


def ayar():
    c = json.loads((KOK / "kagit_config.json").read_text())
    if os.environ.get("KAGIT_BASLANGIC"):
        c["baslangic"] = os.environ["KAGIT_BASLANGIC"]
    bas = pd.Timestamp(c["baslangic"])
    return c, bas, bas + pd.Timedelta(days=c["gun"])


def kollar(son):
    """Her kol için (varlık verileri, hedef ağırlıklar W [kapanışta karar], maliyet)."""
    out = {}
    btc = yukle("BTC-USD")
    btc = btc[btc.index < son]
    out["btc_trend"] = ({"BTC-USD": btc}, pd.DataFrame({"BTC-USD": S.t1(btc)}), MALIYET["kripto"])
    dfs = {k: v[v.index < son] for k, v in evren("abd").items()}
    px = panel(dfs, "Close")
    W = S.agirliklar(px, S.skor_007p, "pozitif", None).mul(rejim_serisi("abd", px), axis=0)
    out["abd_trend"] = (dfs, W, MALIYET["abd"])
    dfs = {t: yukle(t) for t in EMTIA_ETF}
    dfs = {k: v[v.index < son] for k, v in dfs.items() if v is not None and len(v) > 300}
    px = panel(dfs, "Close")
    out["emtia_dusukvol"] = (dfs, S.agirliklar(px, S.skor_012, "top", 0.2), MALIYET["emtia"])
    return out


def degisiklikler(W, dfs, bas):
    """Ağırlık değişimleri: karar günü (kapanış) → uygulama ertesi açılış."""
    W = W[W.index >= bas - pd.Timedelta(days=1)]
    d = W.diff().fillna(0.0)
    if len(W):
        d.iloc[0] = 0.0
    sat = []
    for t in d.index:
        for a in d.columns[d.loc[t].abs() > 1e-9]:
            sonraki = dfs[a].index[dfs[a].index > t]
            sat.append(dict(karar=str(t.date()), varlik=a, eski=round(W.loc[t, a] - d.loc[t, a], 3),
                            yeni=round(W.loc[t, a], 3),
                            uygulama=str(sonraki[0].date()) if len(sonraki) else "bir sonraki açılış",
                            fiyat="%.6g" % dfs[a]["Open"].loc[sonraki[0]] if len(sonraki) else "-"))
    return sat


def calistir(dizin):
    dizin = Path(dizin)
    dizin.mkdir(parents=True, exist_ok=True)
    c, bas, son = ayar()
    simdi = pd.Timestamp.now(tz="UTC").tz_localize(None)
    eski = json.loads((dizin / "durum.json").read_text()) if (dizin / "durum.json").exists() else {}
    K = kollar(son)
    sermaye = float(c["sermaye"])
    egriler, kol_ozet, pozlar, tum_deg = {}, {}, [], []
    for ad, (dfs, W, mal) in K.items():
        r = M.portfoy_getirisi(dfs, W, mal)
        r = r[r.index >= bas]
        cap = sermaye * c["kollar"][ad]
        e = cap * (1 + r).cumprod() if len(r) else pd.Series(dtype=float)
        egriler[ad] = e
        kol_ozet[ad] = dict(ad=KOL_AD[ad], baslangic=round(cap, 2), deger=round(float(e.iloc[-1]) if len(e) else cap, 2))
        son_w = W.iloc[-1] if len(W) else pd.Series(dtype=float)
        tutulan = W.iloc[-2] if len(W) > 1 else son_w * 0
        ac = [a for a in W.columns if son_w.get(a, 0) > 1e-9]
        pozlar.append(dict(kol=KOL_AD[ad], toplam_agirlik=f"{son_w.sum():.0%}", adet=len(ac),
                           varliklar=", ".join(ac) if ac else "nakit",
                           yeni_giris=", ".join(a for a in ac if tutulan.get(a, 0) <= 1e-9) or "-",
                           cikis=", ".join(a for a in W.columns if tutulan.get(a, 0) > 1e-9 and a not in ac) or "-",
                           son_veri=str(max(d.index[-1] for d in dfs.values()).date())))
        tum_deg += [dict(kol=KOL_AD[ad], **x) for x in degisiklikler(W, dfs, bas)]
    gunler = pd.date_range(bas, max([e.index[-1] for e in egriler.values() if len(e)] + [bas]), freq="D")
    toplam = pd.Series(0.0, index=gunler)
    for ad, e in egriler.items():
        cap = sermaye * c["kollar"][ad]
        toplam += e.reindex(gunler, method="ffill").fillna(cap) if len(e) else cap
    deger = float(toplam.iloc[-1]) if len(toplam) else sermaye
    dd = float((toplam / toplam.cummax() - 1).min()) if len(toplam) else 0.0
    bitti = simdi >= son + pd.Timedelta(days=1)
    durum = dict(baslangic=str(bas.date()), bitis=str((son - pd.Timedelta(days=1)).date()), sermaye=sermaye,
                 guncelleme=simdi.strftime("%Y-%m-%d %H:%M UTC"), deger=round(deger, 2),
                 getiri=round(deger / sermaye - 1, 5), max_dusus=round(dd, 5), kollar=kol_ozet,
                 islem_sayisi=sum(1 for x in tum_deg if x["eski"] == 0 or x["yeni"] == 0), beklenti=c["beklenti"], bitti=bool(bitti),
                 son_rapor_gunu=eski.get("son_rapor_gunu"))
    toplam.rename("deger").round(2).to_frame().rename_axis("tarih").to_csv(dizin / "ozsermaye.csv")
    pd.DataFrame(tum_deg).to_csv(dizin / "islemler.csv", index=False)
    pd.DataFrame(pozlar).to_csv(dizin / "pozisyonlar.csv", index=False)
    ozet = ozet_md(durum, pozlar, tum_deg, dizin)
    (dizin / "ozet.md").write_text(ozet)
    bugun = str(simdi.date())
    if simdi >= bas and (durum["son_rapor_gunu"] != bugun or (bitti and not eski.get("bitti"))):
        baslik = "## Son değerlendirme (kağıt dönemi bitti)\n\n" if bitti else f"## Günlük rapor — {bugun}\n\n"
        (dizin / "gunluk_rapor.md").write_text(baslik + ozet.split("\n", 2)[2])
        durum["son_rapor_gunu"] = bugun
    (dizin / "durum.json").write_text(json.dumps(durum, ensure_ascii=False, indent=2))
    if bitti:
        (dizin / "BITTI").write_text(simdi.isoformat() + "\n")
    print(ozet)


def swing_karsilastirma(dizin):
    """Swing kağıt hesabının özsermayesi (iş akışı kagit-durum dalından kopyalar) ile 50/50 sanal birleşim."""
    f = dizin / "swing_ozsermaye.csv"
    t = dizin / "ozsermaye.csv"
    try:
        s = pd.read_csv(f, index_col=0, parse_dates=True)["deger"].dropna()
        tr = pd.read_csv(t, index_col=0, parse_dates=True)["deger"].dropna()
    except Exception:  # dosya yok/boş (swing hesabı henüz gün biriktirmedi) → karşılaştırma atlanır
        return ""
    if not len(s) or not len(tr):
        return ""
    g = pd.date_range(min(s.index[0], tr.index[0]), max(s.index[-1], tr.index[-1]), freq="D")
    s = s.reindex(g, method="ffill").fillna(10000)
    tr = tr.reindex(g, method="ffill").fillna(10000)
    bir = 0.5 * s + 0.5 * tr
    f2 = lambda x: f"{x.iloc[-1] / 10000 - 1:+.2%} (maks. düşüş {(x / x.cummax() - 1).min():.1%})"
    return ("\n### Swing hesabıyla karşılaştırma\n\n| Hesap | Getiri |\n|---|---|\n"
            f"| Swing (S1+S2+S3) | {f2(s)} |\n| Trend kolları | {f2(tr)} |\n| 50/50 sanal birleşim | {f2(bir)} |\n")


def ozet_md(d, pozlar, deg, dizin):
    sat = [f"# Trend kolları kağıt al-sat — {d['guncelleme']}", "",
           f"Dönem {d['baslangic']} → {d['bitis']} · gerçek para yoktur · swing kağıt hesabından bağımsızdır.", "",
           "| Değer | Getiri | Maks. düşüş | Giriş/çıkış emri |", "|---|---|---|---|",
           f"| {d['deger']:,.0f} $ | {d['getiri']:+.2%} | {d['max_dusus']:.1%} | {d['islem_sayisi']} |", "",
           "| Kol | Başlangıç | Değer | Getiri |", "|---|---|---|---|"]
    for k in d["kollar"].values():
        sat.append(f"| {k['ad']} | {k['baslangic']:,.0f} $ | {k['deger']:,.0f} $ | {k['deger'] / k['baslangic'] - 1:+.2%} |")
    b = d["beklenti"]
    sat += ["", f"Backtest beklentisi (örneklem-dışı): yıllık ~%{b['yillik_getiri'] * 100:.0f}, maks. düşüş "
                f"~%{abs(b['max_dusus']) * 100:.0f}, Sharpe ~{b['sharpe']}; 60 günde {b['60_gunde_getiri']}.", ""]
    sat += ["### Pozisyonlar (bir sonraki açılış itibarıyla)", ""]
    sat.append(pd.DataFrame(pozlar).to_markdown(index=False) if pozlar else "_yok_")
    sat += ["", "### Son giriş / çıkışlar", ""]
    gc = [x for x in deg if x["eski"] == 0 or x["yeni"] == 0]
    if gc:
        t = pd.DataFrame(gc)
        t["işlem"] = np.where(t["yeni"] > 0, "AL", "SAT")
        g = t.groupby(["kol", "uygulama", "işlem"])["varlik"].apply(lambda x: ", ".join(x)).reset_index()
        sat.append(g.tail(12).to_markdown(index=False))
    else:
        sat.append("_henüz yok_")
    sat.append(swing_karsilastirma(Path(dizin)))
    return "\n".join(sat) + "\n"


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--durum", required=True)
    calistir(a.parse_args().durum)
