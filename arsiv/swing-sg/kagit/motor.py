"""Swing kağıt al-sat motoru.

Her çalıştırmada kağıt döneminin başından bugüne kadar olan tüm kapanmış günlük mumlar, backtest koduyla
(swing.stratejiler + swing.motor) yeniden oynatılır. Açık pozisyonlar son kapanıştan değerlenir.

  python -m kagit.motor --durum kagit_durum
  KAGIT_BASLANGIC=2026-08-01 python -m kagit.motor --durum /tmp/d    # geçmiş dönemle deneme
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from swing.ayarlar import MAX_AGIRLIK, MAX_POZ, RISK, SECILI, SINIFLAR
from swing.motor import calistir, istatistik, portfoy
from swing.stratejiler import STRATEJILER
from swing.veri import ENDEKS_VERI, MALIYET, tum_veriler

KOK = Path(__file__).resolve().parent
KISA = {"S1_geri_cekilme": "S1", "S2_kirilim": "S2", "S3_asiri_satim": "S3"}


def ayar():
    c = json.loads((KOK / "config.json").read_text())
    if os.environ.get("KAGIT_BASLANGIC"):
        c["baslangic"] = os.environ["KAGIT_BASLANGIC"]
    bas = pd.Timestamp(c["baslangic"])
    return c, bas, bas + pd.Timedelta(days=c["gun"])


def islemleri_uret(veriler, bas, son):
    """Tüm strateji/varlık işlemleri (giriş >= bas) ve son mumda oluşan bekleyen emirler."""
    trades, bekleyen = [], []
    for ad, (df, sinif) in veriler.items():
        df = df[df.index < son]
        if len(df) < 260:
            continue
        for st, p in SECILI.items():
            if sinif not in SINIFLAR[st]:
                continue
            sig = STRATEJILER[st](df, {**p, "_endeks": ENDEKS_VERI.get(sinif)})
            # Kağıt hesap başlangıçta boştur: girişi başlangıçtan önceye düşen sinyaller yok sayılır. Aksi halde
            # dönem öncesinin (hesapta olmayan) pozisyonları motorda açık kalıp aynı varlıktaki yeni sinyalleri engeller.
            once = df.index[df.index < bas]
            if len(once):
                sig.loc[sig.index < once[-1], ["long", "short"]] = False
            mesgul = False
            for t in calistir(ad, sinif, df, sig, MALIYET[sinif], st):
                if t.giris_tarih >= bas:
                    trades.append(t)
                mesgul = mesgul or t.neden in ACIK
            s = sig.iloc[-1]
            if s["long"] and not mesgul:  # motor bu varlıkta zaten pozisyondaysa yeni sinyal emir olmaz
                lim = s.get("limit_long", np.nan)
                ref = lim if pd.notna(lim) else df["Close"].iloc[-1]
                bekleyen.append(dict(strateji=KISA[st], varlik=ad, sinif=sinif, sinyal_tarihi=str(df.index[-1].date()),
                                     emir=("limit %.6g" % lim) if pd.notna(lim) else "açılışta al",
                                     stop="%.6g" % s["stop_long"],
                                     stop_mesafe=f"{(ref - s['stop_long']) / ref:.1%}"))
    return trades, bekleyen


ACIK = ("acik", "veri_sonu")  # veri_sonu: çıkış sinyali son kapanışta oluştu, çıkış bir sonraki açılışta


def gunluk_egri(alinanlar, veriler, bas, bitis_gunu, sermaye):
    """Günlük piyasa değeri: kapanan işlemlerin gerçekleşen kârı + açık pozisyonların o günkü kapanıştan değeri
    (kısmi kâr alındıysa o kısım kısmi fiyattan sabitlenir)."""
    gunler = pd.date_range(bas, bitis_gunu, freq="D")
    deger = pd.Series(sermaye, index=gunler, dtype=float)
    for tr, w, ozs, pnl in alinanlar:
        c = veriler[tr.varlik][0]["Close"].reindex(gunler, method="ffill")
        acik_mi = tr.neden in ACIK
        brut = (c / tr.giris - 1) * tr.yon
        if tr.kismi_tarih is not None:
            kb = (tr.kismi_fiyat / tr.giris - 1) * tr.yon
            brut = brut.where(gunler < tr.kismi_tarih, 0.5 * kb + 0.5 * brut)
        mtm = ozs * w * (brut - MALIYET[tr.sinif])  # çıkış maliyeti dahil (muhafazakâr)
        icinde = (gunler >= tr.giris_tarih) & (True if acik_mi else (gunler < tr.cikis_tarih))
        deger[icinde] += mtm[icinde].fillna(0)
        if not acik_mi:
            deger[gunler >= tr.cikis_tarih] += pnl
    return deger


def calistir_kagit(dizin):
    dizin = Path(dizin)
    dizin.mkdir(parents=True, exist_ok=True)
    c, bas, son = ayar()
    eski = json.loads((dizin / "durum.json").read_text()) if (dizin / "durum.json").exists() else {}
    simdi = pd.Timestamp.now(tz="UTC").tz_localize(None)
    veriler = tum_veriler()
    trades, bekleyen = islemleri_uret(veriler, bas, son)
    sermaye = float(c["sermaye"])
    p = portfoy(trades, baslangic=sermaye, risk=RISK, max_poz=MAX_POZ, max_agirlik=MAX_AGIRLIK, detay=True) \
        if trades else {"alinanlar": []}
    alinanlar = p["alinanlar"]
    acik = [x for x in alinanlar if x[0].neden in ACIK]
    kapali = [x for x in alinanlar if x[0].neden not in ACIK]
    acik_varliklar = {x[0].varlik for x in acik}
    son_veri = max(df.index[-1] for df, _ in veriler.values())
    bitis_gunu = min(son_veri, son - pd.Timedelta(days=1))
    egri = gunluk_egri(alinanlar, veriler, bas, bitis_gunu, sermaye) if bitis_gunu >= bas else pd.Series(dtype=float)
    deger = float(egri.iloc[-1]) if len(egri) else sermaye
    gerceklesen = sermaye + sum(x[3] for x in kapali)
    dd = float((egri / egri.cummax() - 1).min()) if len(egri) else 0.0
    st = istatistik([x[0] for x in kapali])
    strateji_ozet = {}
    for k, kisa in KISA.items():
        s = istatistik([x[0] for x in kapali if x[0].strateji == k])
        strateji_ozet[kisa] = dict(kapanan=s.get("islem", 0), kazanma=s.get("kazanma_orani"),
                                   ort_R=s.get("ort_R"), acik=sum(1 for x in acik if x[0].strateji == k))
    bitti = simdi >= son + pd.Timedelta(days=1)
    durum = dict(
        baslangic=str(bas.date()), bitis=str((son - pd.Timedelta(days=1)).date()), sermaye=sermaye,
        guncelleme=simdi.strftime("%Y-%m-%d %H:%M UTC"), son_veri=str(son_veri.date()),
        deger=round(deger, 2), getiri=round(deger / sermaye - 1, 5), gerceklesen=round(gerceklesen, 2),
        max_dusus=round(dd, 5), kapanan_islem=st.get("islem", 0), kazanma_orani=st.get("kazanma_orani"),
        ort_R=st.get("ort_R"), acik_pozisyon=len(acik), strateji=strateji_ozet, beklenti=c["beklenti"],
        bitti=bool(bitti), son_rapor_gunu=eski.get("son_rapor_gunu"),
    )
    # --- kayıtlar
    satir = lambda x: dict(strateji=KISA[x[0].strateji], varlik=x[0].varlik, sinif=x[0].sinif,
                           giris_tarih=str(x[0].giris_tarih.date()), giris="%.6g" % x[0].giris,
                           stop="%.6g" % x[0].stop0, agirlik=f"{x[1]:.1%}", tutar=round(x[2] * x[1], 2),
                           cikis_tarih=str(x[0].cikis_tarih.date()), cikis="%.6g" % x[0].cikis, neden=x[0].neden,
                           getiri=f"{x[0].getiri:+.2%}", R=round(x[0].R, 2), kar_usd=round(x[3], 2))
    pd.DataFrame([satir(x) for x in kapali]).to_csv(dizin / "islemler.csv", index=False)
    pz = pd.DataFrame([{**satir(x), "cikis_tarih": "", "son_fiyat": "%.6g" % x[0].cikis,
                        "neden": "çıkış emri (açılışta sat)" if x[0].neden == "veri_sonu" else
                        ("açık, kısmi kâr alındı" if x[0].kismi_tarih is not None else "açık")} for x in acik]).drop(columns=["cikis"], errors="ignore")
    pz.to_csv(dizin / "pozisyonlar.csv", index=False)
    if len(egri):
        egri.rename("deger").round(2).to_frame().rename_axis("tarih").to_csv(dizin / "ozsermaye.csv")
    bek = [b for b in bekleyen if b["varlik"] not in acik_varliklar] if not bitti else []
    (dizin / "durum.json").write_text(json.dumps(durum, ensure_ascii=False, indent=2, default=float))
    ozet = ozet_md(durum, kapali, pz, bek)
    (dizin / "ozet.md").write_text(ozet)
    # --- günlük rapor (UTC günde bir kez) ve bitiş
    bugun = str(simdi.date())
    if simdi >= bas and (durum["son_rapor_gunu"] != bugun or bitti and not eski.get("bitti")):
        baslik = "## Son değerlendirme (kağıt dönemi bitti)\n\n" if bitti else f"## Günlük rapor — {bugun}\n\n"
        (dizin / "gunluk_rapor.md").write_text(baslik + ozet.split("\n", 2)[2])
        durum["son_rapor_gunu"] = bugun
        (dizin / "durum.json").write_text(json.dumps(durum, ensure_ascii=False, indent=2, default=float))
    if bitti:
        (dizin / "BITTI").write_text(simdi.isoformat() + "\n")
    print(ozet)


def _f(x, fmt):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else format(x, fmt)


def ozet_md(d, kapali, pz, bekleyen):
    sat = [f"# Swing kağıt al-sat — {d['guncelleme']}", "",
           f"Dönem {d['baslangic']} → {d['bitis']} · son veri {d['son_veri']} · gerçek para yoktur.", "",
           "| Değer | Getiri | Gerçekleşen | Maks. düşüş | Kapanan işlem | Kazanma | Ort. R | Açık |",
           "|---|---|---|---|---|---|---|---|",
           f"| {d['deger']:,.0f} $ | {d['getiri']:+.2%} | {d['gerceklesen']:,.0f} $ | {d['max_dusus']:.1%} | "
           f"{d['kapanan_islem']} | {_f(d['kazanma_orani'], '.0%')} | {_f(d['ort_R'], '+.2f')} | {d['acik_pozisyon']} |", "",
           "| Strateji | Kapanan | Kazanma | Ort. R | Açık |", "|---|---|---|---|---|"]
    for k, s in d["strateji"].items():
        sat.append(f"| {k} | {s['kapanan']} | {_f(s['kazanma'], '.0%')} | {_f(s['ort_R'], '+.2f')} | {s['acik']} |")
    b = d["beklenti"]
    sat += ["", f"Backtest beklentisi (örneklem-dışı): kazanma ~%{b['kazanma_orani'] * 100:.0f}, yıllık ~%"
                f"{b['yillik_getiri'] * 100:.0f}, maks. düşüş ~%{abs(b['max_dusus']) * 100:.0f}; 60 günde "
                f"{b['60_gunde_islem']} işlem, {b['60_gunde_getiri']}.", ""]
    sat += ["### Açık pozisyonlar", ""]
    if len(pz):
        sat.append(pz[["strateji", "varlik", "giris_tarih", "giris", "stop", "son_fiyat", "getiri", "agirlik",
                       "kar_usd", "neden"]].rename(columns={"neden": "durum"}).to_markdown(index=False))
    else:
        sat.append("_yok_")
    sat += ["", "### Bekleyen emirler (bir sonraki açılış)", ""]
    sat.append(pd.DataFrame(bekleyen).to_markdown(index=False) if bekleyen else "_yok_")
    sat += ["", "### Son kapanan işlemler", ""]
    if kapali:
        son = sorted(kapali, key=lambda x: x[0].cikis_tarih)[-10:]
        sat.append(pd.DataFrame([dict(strateji=KISA[x[0].strateji], varlik=x[0].varlik,
                                      giris=str(x[0].giris_tarih.date()), cikis=str(x[0].cikis_tarih.date()),
                                      neden=x[0].neden, getiri=f"{x[0].getiri:+.2%}", R=round(x[0].R, 2),
                                      kar_usd=round(x[3], 2)) for x in son]).to_markdown(index=False))
    else:
        sat.append("_henüz yok_")
    return "\n".join(sat) + "\n"


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--durum", required=True)
    calistir_kagit(a.parse_args().durum)
