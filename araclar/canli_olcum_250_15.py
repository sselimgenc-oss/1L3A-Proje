"""Ölçüm (GEÇMİŞ, v2 geliştirme dönemi; holdout okunmaz): 250 USD kasa + %1,5 işlem riski ile CANLI_LIMITLER yeniden oynatması
ve KİLİTLİ swing seçim kuralı (sonuclar/canli/CANLI_PLAN.md). `canli_boyut_yeniden_oynat.oyna` aynen kullanılır; yalnız kasa ve işlem başı risk değişir.

Kullanım:  python araclar/canli_olcum_250_15.py --onbellek DIZIN
Çıktı: sonuclar/canli/olcum_250_15.csv, OLCUM_250_15.md, SWING_SECIM.md
Swing kuralı: T = en büyük tek işlem R / toplam net R (toplam <= 0 -> düşer); K = R>3 işlemlerin atlanan payı (250/%1,5 oynatma);
puan = T sırası + K sırası (1 = en iyi; eşitlik payında en iyi sıra); eşitlikte küçük T; sonra alfabetik. Paper / getiri / Sharpe KULLANILMAZ.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import canli_atlanan_teshis as te                           # noqa: E402
import canli_boyut_yeniden_oynat as oy                      # noqa: E402
from motor.canli.borsa import canli_limitler as cl          # noqa: E402

KASA, RISK, ESIK_ATLANAN = 250.0, 0.015, 0.5
ADAYLAR = ["dis__haftalik-macd-gunluk-ma", "dis__lube", "dis__gauss-stoch-eth", "dis__hma-atr-rider"]
NEDENLER = te.NEDENLER


def oynat(tr, mt):
    oy.KASA_USD = KASA
    lim = dataclasses.replace(cl.CANLI_LIMITLER, islem_basi_max_kayip_oran=RISK)
    kayit = []
    r = oy.oyna(tr, mt, "canli", kayit=kayit, boyut_ek=dict(limitler=lim))
    return r, te.sinyal_tablosu(tr, kayit)


def olc(onbellek: Path):
    st = json.loads(oy.SET_YOLU.read_text(encoding="utf-8"))
    satir, hamlar = [], {}
    for k in st["stratejiler"]:
        ad = k["strateji"]
        if k["tur"] != "tek":
            continue
        dos = sorted(onbellek.glob(f"{ad}--*--islem.parquet"))
        if not dos:
            continue
        tr = pd.concat([pd.read_parquet(f) for f in dos], ignore_index=True)
        mt = pd.concat([pd.read_parquet(f) for f in sorted(onbellek.glob(f"{ad}--*--mtm.parquet"))], ignore_index=True)
        r, d = oynat(tr, mt)
        at = d[d["durum"] == "atlandi"]
        b3 = d[d["r"] > 3]
        row = dict(strateji=ad, sinyal=len(d), alinan=int((d["durum"] == "alindi").sum()), atlanan=len(at), atlanan_yuzde=round(100 * len(at) / len(d), 1))
        for n in NEDENLER:
            row[f"atlanan_{n}"] = int((at["neden"] == n).sum())
        row.update(r3_sinyal=len(b3), r3_atlanan=int((b3["durum"] == "atlandi").sum()),
                   r3_atlanan_pay=round(float((b3["durum"] == "atlandi").mean()), 4) if len(b3) else float("nan"),
                   son_ozsermaye_usd=round(r["son_ozsermaye"], 2), maks_dusus=round(r["maks_dusus"], 4),
                   kill="evet" if r["kill_tarihi"] else "hayir", kill_tarihi=r["kill_tarihi"],
                   toplam_net_r=round(float(d["r"].sum()), 3), en_buyuk_r=round(float(d["r"].max()), 3),
                   bayrak_50="EVET" if len(at) / len(d) > ESIK_ATLANAN else "")
        satir.append(row)
        hamlar[ad] = d
    return pd.DataFrame(satir), hamlar


def sec(df: pd.DataFrame) -> tuple:
    rows = []
    for ad in ADAYLAR:
        x = df[df["strateji"] == ad]
        if not len(x):
            rows.append(dict(strateji=ad, T=float("nan"), K=float("nan"), not_="veri yok -> düşer"))
            continue
        x = x.iloc[0]
        if x["toplam_net_r"] <= 0:
            rows.append(dict(strateji=ad, T=float("nan"), K=float(x["r3_atlanan_pay"]), toplam_r=x["toplam_net_r"], en_buyuk_r=x["en_buyuk_r"], not_="toplam net R <= 0 -> düşer"))
            continue
        k = float(x["r3_atlanan_pay"])
        rows.append(dict(strateji=ad, T=round(x["en_buyuk_r"] / x["toplam_net_r"], 4), K=0.0 if pd.isna(k) else round(k, 4), toplam_r=x["toplam_net_r"],
                         en_buyuk_r=x["en_buyuk_r"], not_="" if not pd.isna(k) else "R>3 işlem yok: K=0"))
    t = pd.DataFrame(rows)
    kal = t[t["T"].notna()].copy()
    kal["T_sira"] = kal["T"].rank(method="min").astype(int)
    kal["K_sira"] = kal["K"].rank(method="min").astype(int)
    kal["puan"] = kal["T_sira"] + kal["K_sira"]
    kal = kal.sort_values(["puan", "T", "strateji"], kind="stable").reset_index(drop=True)
    kal["sira"] = range(1, len(kal) + 1)
    return t, kal


def md(df, fmt=None):
    return te.md_tablo(df, fmt)


def olcum_md(df):
    g = df[["strateji", "atlanan_yuzde", "r3_atlanan_pay", "son_ozsermaye_usd", "maks_dusus", "kill", "kill_tarihi", "bayrak_50"]].copy()
    g["r3_atlanan_pay"] = g["r3_atlanan_pay"].map(lambda x: "-" if pd.isna(x) else f"{100 * x:.0f}%")
    g["maks_dusus"] = g["maks_dusus"].map(lambda x: f"{100 * x:.1f}%")
    g["atlanan_yuzde"] = g["atlanan_yuzde"].map(lambda x: f"{x:.1f}%")
    n = df[["strateji", "sinyal", "alinan", "atlanan"] + [f"atlanan_{x}" for x in NEDENLER]].copy()
    bay = df[df["bayrak_50"] == "EVET"]["strateji"].tolist()
    L = ["# Ölçüm: 250 USD kasa, işlem başı %1,5 risk (geçmiş yeniden oynatma)", "",
         "**Bu geçmiş bir ölçümdür, gelecek tahmini değildir.** Yalnız v2 GELİŞTİRME dönemi (holdout okunmadı). Her strateji tek başına, 250 USD kasayla; "
         "işlem başı stopta kayıp tavanı %1,5 (maliyet dahil), diğer CANLI_LIMITLER kuralları aynı. Min tutar tablosu: BTCUSDT 100, ETHUSDT 20, diğerleri 5 USDT "
         "(tutucu varsayım). Araç: `araclar/canli_olcum_250_15.py` (mevcut `canli_boyut_yeniden_oynat.oyna` aynen kullanıldı). Ayrıntı: `olcum_250_15.csv`.", "",
         "Basit okuma: **atlanan %** = strateji sinyal verdi ama küçük kasa/min tutar/risk bütçesi yüzünden işleme girilemedi. **R>3 atlanan payı** = "
         "en değerli (büyük kazançlı) işlemlerin ne kadarının kaçırıldığı.", "", "## Özet", "", md(g), "",
         "## Atlanan sinyaller, nedene göre (adet)", "", md(n), "",
         "Neden kodları: `min_tutar` (hesaplanan tutar borsa minimumunun altı), `risk_butcesi_dolu` (toplam açık stop riski %6 dolu), `brut_tavan` (brüt 1,5x dolu), "
         "`stop_cok_uzak` (stop > %25), `gunluk_blok`, `kill_sonrasi`, `diger`.", "",
         "## Bayrak (CANLI_PLAN.md ölçüm şartı)", "",
         f"Atlanan sinyal oranı > %50 olan stratejiler: **{', '.join(bay) if bay else 'yok'}**. Plana göre bunlar %1,5 yerine **%2 ile başlar** (15m'de takvim %2 -> %3). "
         "Not: Aşama 1 kadrosunda yalnız dis__e0v1en ve dis__ewo-ema-ofset 15m'dir; ikisi de %50'nin altında (bayraksız). Swing stratejileri planda %1,5 SABİT yazıldığından, "
         "swing adayı bayraklıysa (aşağıdaki tablo) bu planın boşluğudur: karar kullanıcıda.", ""]
    (oy.CIKTI / "OLCUM_250_15.md").write_text("\n".join(L), encoding="utf-8")


def swing_md(t, kal):
    sec2 = kal["strateji"].tolist()
    dus = t[t["T"].isna()]
    f = kal[["sira", "strateji", "T", "K", "T_sira", "K_sira", "puan", "toplam_r", "en_buyuk_r"]].copy()
    L = ["# Swing seçimi (KİLİTLİ kural uygulandı)", "",
         "**Seçim, 2026-12-08 sadakat kontrolünü geçmeleri şartıyla geçerli; geçemeyen düşer ve sıradaki alınır.**", "",
         "Kural: `CANLI_PLAN.md` -> SWING SEÇİM KURALI (değiştirilmedi). Girdi yalnız v2 GELİŞTİRME dönemi işlem listesi (holdout okunmadı) ve 250 USD / %1,5 yeniden oynatma "
         "(`olcum_250_15.csv`). Paper sonucu, getiri ve Sharpe kullanılmadı.", "",
         "- T = en büyük tek işlemin R'si / toplam net R (küçük = iyi). Toplam net R <= 0 ise aday düşer.",
         "- K = 250 USD, %1,5, CANLI_LIMITLER yeniden oynatmasında R>3 işlemlerin ATLANAN payı (küçük = iyi).",
         "- Sıra puanı = T sırası + K sırası (1 = en iyi; aynı değerde olanlar aynı (en iyi) sırayı alır). En düşük puan kazanır; eşitlikte küçük T; o da eşitse alfabetik.", "",
         "## Tablo (puana göre sıralı)", "",
         md(f, {"T": lambda x: f"{x:.4f}", "K": lambda x: f"{100 * x:.1f}%", "toplam_r": lambda x: f"{x:.1f}", "en_buyuk_r": lambda x: f"{x:.1f}"}), ""]
    if len(dus):
        L += ["Düşenler: " + "; ".join(f"{r.strateji} ({r.not_})" for r in dus.itertuples()), ""]
    L += ["## Seçilen iki strateji", "", f"1. **{sec2[0]}**", f"2. **{sec2[1]}**", "",
          "Eşitlik notu: " + ("puan eşitliği vardı, T küçük olan öne alındı." if len(kal) > 1 and (kal["puan"].iloc[0] == kal["puan"].iloc[1]) else "puan eşitliği yok."), "",
          "## Tam sıralı liste (yedek sırası; mekanik)", "",
          "Seçilen bir aday 2026-12-08 sadakat kontrolünü geçemezse düşer; yerine bu listede sıradaki, kontrolü geçmiş aday alınır (kural dışı aday alınmaz):", ""]
    L += [f"{r.sira}. {r.strateji} (puan {r.puan}, T {r.T:.4f}, K {100 * r.K:.1f}%)" for r in kal.itertuples()]
    L += ["", "Kalan aday sayısı 2'den azsa Aşama 1 eksik sayıyla başlar (kural 5).", ""]
    (oy.CIKTI / "SWING_SECIM.md").write_text("\n".join(L), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--onbellek", required=True)
    a = ap.parse_args(argv)
    df, _ = olc(Path(a.onbellek))
    oy.CIKTI.mkdir(parents=True, exist_ok=True)
    df.to_csv(oy.CIKTI / "olcum_250_15.csv", index=False)
    t, kal = sec(df)
    olcum_md(df)
    swing_md(t, kal)
    print(df.to_string())
    print(kal.to_string())


if __name__ == "__main__":
    main()
