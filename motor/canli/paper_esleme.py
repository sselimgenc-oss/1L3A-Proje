"""EN ÖNEMLİ TEST: kağıt motoru = backtest motoru.

Tekrar modu (geçmiş mumları sırayla 'canlıymış gibi' besler; canlı yolla AYNI Paper.baslat/adim kodu) ↔ backtest motoru
(tek-grafik: motor.backtest.motor.backtest; portföy: motor.portfoy.motor.portfoy_backtest; ikisi de limit_modu='uygula',
aynı maliyet/kayma, aynı sembol kuralları, aynı dönem: islem_baslangic=bas). Karşılaştırma işlem işlem: giriş/çıkış zamanı,
fiyat, miktar, brüt/komisyon/funding/net PnL (Decimal düzeyinde, mutlak fark <= 1e-9 para birimi) ve çıkış nedeni.

Karşılaştırma İZOLE koşar (tek strateji, kendi hesabı, grup payı 1): çekirdek davranışı budur. Paylı/ortak hesap davranışı
(sleeve, ortak limitler) backtestte karşılığı olmadığından ayrı testlerle (özellik testi) sınanır.
"""
from __future__ import annotations

import dataclasses
from decimal import Decimal
from typing import Optional

import pandas as pd

from motor.canli import paper as pp
from motor.strateji import funding as fnd

KARSILASTIRILAN = ["yon", "giris_zamani", "giris_fiyati", "cikis_zamani", "cikis_fiyati", "miktar", "brut_pnl", "komisyon",
                   "funding", "net_pnl", "cikis_nedeni"]
SAYISAL = ["giris_fiyati", "cikis_fiyati", "miktar", "brut_pnl", "komisyon", "funding", "net_pnl"]
TOL = Decimal("1e-9")
from motor.portfoy.motor import ISLEM_KOLONLARI  # noqa: E402


def izole(t):
    """Grup payı 1: tek strateji kendi hesabında (backtest ile karşılaştırma koşulu)."""
    return dataclasses.replace(t, grup_payi=Decimal(1))


def karsilastir(bt: pd.DataFrame, pa: pd.DataFrame, anahtar=("giris_zamani", "sembol")) -> dict:
    """İki işlem tablosunu satır satır karşılaştırır. -> özet sözlüğü; 'farklar' boşsa eşleşme tam (tam_esit).

    ZAMAN ETİKETİ: backtest motoru mum-içi çıkışların (stop/hedef/veri_sonu) zaman damgasını t + `aralik` ile yazar;
    `aralik` verinin kendisinden (ardışık mum farklarının medyanı) türetilir. Seanslı (DK_) verilerde bu medyan nominal mum
    süresinden büyüktür (gece/hafta sonu boşlukları), paper ise nominal mum süresini (t + tf) kullanır. Fiyat, miktar, PnL
    aynıdır; yalnız `cikis_zamani` etiketi farklıdır. Bu satırlar `zaman_etiketi_farki` altında ayrıca sayılır ve
    `tam_esit_zaman_haric` hesabına girmez; `tam_esit` bu farkı da fark sayar (gizlenmez)."""
    a = bt.copy()
    b = pa.copy()
    if "sembol" not in a.columns:
        a["sembol"] = ""
    if "sembol" not in b.columns:
        b["sembol"] = ""
    for d in (a, b):
        d["giris_zamani"] = pd.to_datetime(d["giris_zamani"], utc=True)
        d["cikis_zamani"] = pd.to_datetime(d["cikis_zamani"], utc=True)
    a = a.sort_values(["giris_zamani", "sembol"], kind="stable").reset_index(drop=True)
    b = b.sort_values(["giris_zamani", "sembol"], kind="stable").reset_index(drop=True)
    out = {"n_backtest": len(a), "n_paper": len(b), "n_esit": 0, "max_mutlak_fark": 0.0, "farklar": [], "zaman_etiketi_farki": 0,
           "diger_farklar": 0,
           "toplam_net_backtest": float(a["net_pnl"].sum()) if len(a) else 0.0,
           "toplam_net_paper": float(b["net_pnl"].sum()) if len(b) else 0.0}
    n = min(len(a), len(b))
    for i in range(n):
        ra, rb = a.iloc[i], b.iloc[i]
        sorun = []
        for c in ("yon", "giris_zamani", "cikis_zamani", "cikis_nedeni"):
            if ra[c] != rb[c]:
                sorun.append(f"{c}: bt={ra[c]} paper={rb[c]}")
        for c in SAYISAL:
            fark = abs(Decimal(repr(float(ra[c]))) - Decimal(repr(float(rb[c]))))
            out["max_mutlak_fark"] = max(out["max_mutlak_fark"], float(fark))
            if fark > TOL:
                sorun.append(f"{c}: bt={ra[c]} paper={rb[c]}")
        if sorun:
            out["farklar"].append({"sira": i, "giris": str(ra["giris_zamani"]), "sembol": ra["sembol"], "sorun": sorun})
            if len(sorun) == 1 and sorun[0].startswith("cikis_zamani") and ra["cikis_nedeni"] in ("stop", "hedef", "veri_sonu", "kismi_tam"):
                out["zaman_etiketi_farki"] += 1
            else:
                out["diger_farklar"] += 1
        else:
            out["n_esit"] += 1
    if len(a) != len(b):
        out["farklar"].append({"sira": n, "sorun": [f"işlem sayısı farklı: bt={len(a)} paper={len(b)}"]})
    out["tam_esit"] = (not out["farklar"]) and len(a) == len(b)
    out["tam_esit_zaman_haric"] = out["diger_farklar"] == 0 and len(a) == len(b)
    return out


def tek_esle(t, mumlar: pd.DataFrame, fund, kurallar: dict, bas, bit=None, pencere: Optional[dict] = None,
             ayarlar=None) -> dict:
    """Tek-grafik stratejisi: backtest(limit_modu='uygula', islem_baslangic=bas) ↔ tekrar modu."""
    from motor.arastirma import wf_tarama as wf
    from motor.backtest.motor import backtest
    bas = pd.Timestamp(bas)
    if bit is not None:
        mumlar = mumlar[mumlar.index < pd.Timestamp(bit)]
    kural = kurallar[t.sembol]
    ay = dataclasses.replace(wf.maliyet_ayarlari(kural), limit_modu="uygula")
    r = backtest(fnd.stratejiye_hazirla(t.nesne, mumlar, fund, t.sembol, t.tf), t.nesne, ay, fund, islem_baslangic=bas)
    bt = r.islemler[pd.DatetimeIndex(r.islemler["giris_zamani"]) >= bas] if len(r.islemler) else r.islemler
    p = pp.tekrar_calistir([izole(t)], {(t.sembol, t.tf): mumlar}, {t.sembol: fund} if fund is not None else {},
                           {t.sembol: kural}, bas, None, ayarlar, pencere)
    out = karsilastir(bt, pd.DataFrame(p.motor.islemler, columns=ISLEM_KOLONLARI))
    out["kimlik"] = t.kimlik
    out["motor"] = "backtest.motor.backtest"
    out["reddedilen_paper"] = len(p.motor.reddedilenler)
    out["reddedilen_backtest"] = len(r.reddedilenler)
    return out


def pf_esle(t, veriler: dict, fundingler: dict, kurallar: dict, bas, bit=None, pencere: Optional[dict] = None,
            ayarlar=None) -> dict:
    """Portföy stratejisi: portfoy_backtest(limit_modu='uygula', islem_baslangic=bas) ↔ tekrar modu."""
    from motor.arastirma import wf_portfoy as wfp
    from motor.portfoy.motor import portfoy_backtest
    bas = pd.Timestamp(bas)
    if bit is not None:
        veriler = {s: v[v.index < pd.Timestamp(bit)] for s, v in veriler.items()}
    sem = list(t.evren)
    ay = dataclasses.replace(wfp.maliyet_ayarlari(), limit_modu="uygula", kurallar=dict(kurallar))
    r = portfoy_backtest({s: veriler[s] for s in sem}, t.nesne, ay, {s: fundingler[s] for s in sem if s in fundingler},
                         islem_baslangic=bas)
    bt = r.islemler[pd.DatetimeIndex(r.islemler["giris_zamani"]) >= bas] if len(r.islemler) else r.islemler
    p = pp.tekrar_calistir([izole(t)], {(s, t.tf): veriler[s] for s in sem}, {s: fundingler[s] for s in sem if s in fundingler},
                           kurallar, bas, None, ayarlar, pencere)
    out = karsilastir(bt, pd.DataFrame(p.motor.islemler, columns=ISLEM_KOLONLARI))
    out["kimlik"] = t.kimlik
    out["motor"] = "portfoy.motor.portfoy_backtest"
    out["reddedilen_paper"] = len(p.motor.reddedilenler)
    out["reddedilen_backtest"] = len(r.reddedilenler)
    out["kirpma_paper"] = len(p.motor.kirpmalar)
    out["kirpma_backtest"] = len(r.kirpmalar)
    return out


# ---------------------------------------------------------------------------- CLI: kilitli dönem üzerinde 7 strateji
KILIT = pd.Timestamp("2025-11-01", tz="UTC")
GEREKCE = "Aşama 4: paper tekrar modu ↔ backtest eşleşme testi (kilit kullanılmış sayılır, ON_KAYIT)"


def kilit_calistir(secimler=None, gun: Optional[int] = None, pencere: Optional[dict] = None, ayar_kaynagi: str = "kilit",
                   veri_dizini=None) -> list:
    """7 stratejiyi kilitli dönemde karşılaştırır (yerel veri gerekir). ayar_kaynagi='kilit': kilit testindeki ayarlar."""
    from motor.arastirma import kilit_testi as kt
    from motor.arastirma import tarama
    from motor.portfoy import veri as pveri
    from motor.portfoy.motor import sembol_kurali, PortfoyAyarlari
    tanimlar = pp.psg.tanimlari_yukle(ayar_kaynagi=ayar_kaynagi)
    bit = KILIT + pd.Timedelta(days=gun) if gun else None
    out = []
    for t in tanimlar:
        if secimler and t.kimlik not in secimler:
            continue
        if t.kol == "tek_grafik":
            mum, fund = kt._tek_veri(t.sembol, t.tf, veri_dizini, bit, True, GEREKCE)
            kur = {t.sembol: tarama.SEMBOL_KURALLARI.get(t.sembol, tarama.VARSAYILAN_KURAL)}
            out.append(tek_esle(t, mum, fund, kur, KILIT, bit, pencere))
        else:
            ver, fn = pveri.veri_yukle(t.evren, t.tf, None, bit, veri_dizini, kilit_ac=True, gerekce=GEREKCE)
            kur = {s: sembol_kurali(s, PortfoyAyarlari()) for s in t.evren}
            out.append(pf_esle(t, ver, fn, kur, KILIT, bit, pencere))
    return out


def main(argv=None):
    import argparse
    import json
    from pathlib import Path
    ap = argparse.ArgumentParser(description="Kağıt motoru = backtest motoru eşleşme testi (kilitli dönem)")
    ap.add_argument("--gun", type=int, default=None, help="kilit başlangıcından itibaren N gün (varsayılan: tüm dönem)")
    ap.add_argument("--pencere", type=int, default=0, help="strateji girdisi son N bar (0: tüm geçmiş = backtest ile aynı girdi)")
    ap.add_argument("--kimlik", nargs="*")
    ap.add_argument("--ayar", default="kilit", choices=["kilit", "guncel"])
    ap.add_argument("--cikti", default=None)
    a = ap.parse_args(argv)
    from motor.arastirma.tarama import STIL_TF  # noqa: F401
    pen = None
    if a.pencere:
        pen = {tf: a.pencere for tf in ("30m", "1h", "4h", "1d")}
    sonuc = kilit_calistir(a.kimlik, a.gun, pen, a.ayar)
    for r in sonuc:
        durum = ("TAM EŞİT" if r["tam_esit"] else
                 (f"EŞİT (yalnız {r['zaman_etiketi_farki']} çıkış zaman ETİKETİ farkı)" if r["tam_esit_zaman_haric"] else "FARK VAR"))
        print(f"{r['kimlik']:<45} bt={r['n_backtest']:>3} paper={r['n_paper']:>3} eşit={r['n_esit']:>3} "
              f"max|fark|={r['max_mutlak_fark']:.2e} net(bt/paper)={r['toplam_net_backtest']:.4f}/{r['toplam_net_paper']:.4f} {durum}")
        for f in r["farklar"][:5]:
            print("    ", f)
    if a.cikti:
        Path(a.cikti).parent.mkdir(parents=True, exist_ok=True)
        Path(a.cikti).write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return 0 if all(r["tam_esit_zaman_haric"] for r in sonuc) else 1


if __name__ == "__main__":
    raise SystemExit(main())
