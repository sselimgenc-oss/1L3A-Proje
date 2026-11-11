"""TEŞHİS (strateji/limit önerisi DEĞİL): CANLI_LIMITLER yeniden oynatmasında hangi sinyaller ALINDI / ATLANDI, neden, ve atlananların R'si.

Yeniden oynatma mantığı `canli_boyut_yeniden_oynat.oyna` ile AYNIDIR (oradaki isteğe bağlı `kayit` kancası kullanılır; sonuçlar değişmez).
Varsayımsal senaryolar yalnız 'ne olurdu' sorusudur: min tutar yok / toplam açık risk ve brüt bütçesi sınırsız (yalnız işlem başı %3 kayıp,
işlem başı nominal ve marj tavanı kalır).
Yalnız v2 GELİŞTİRME dönemi (önbellekteki işlem listeleri); holdout okunmaz.

Kullanım:  python araclar/canli_atlanan_teshis.py --onbellek DIZIN
Çıktı: sonuclar/canli/atlanan_teshis.csv (sinyal başına), atlanan_teshis_ozet.csv (strateji x neden), ATLANAN_TESHIS.md
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

import canli_boyut_yeniden_oynat as oy                      # noqa: E402
from motor.canli.borsa import canli_limitler as cl          # noqa: E402

NEDENLER = ["min_tutar", "risk_butcesi_dolu", "brut_tavan", "stop_cok_uzak", "gunluk_blok", "kill_sonrasi", "diger"]
SENARYOLAR = {
    "gercek": None,
    "min_tutar_yok": dict(min_tutar_yok=True),
    "risk_butcesi_sinirsiz": dict(limitler=dataclasses.replace(cl.CANLI_LIMITLER, toplam_stop_riski_oran=1e9, brut_nominal_kat=1e9)),
}


def sinyal_tablosu(tr: pd.DataFrame, kayit: list) -> pd.DataFrame:
    """Her sinyal (işlem) için durum/neden; kayıt olmayan (oynatma aralığı dışı) sinyal 'diger' sayılır."""
    k = pd.DataFrame(kayit, columns=["sembol", "islem_no", "durum", "neden", "qty"])
    d = tr.merge(k, on=["sembol", "islem_no"], how="left")
    d["durum"] = d["durum"].fillna("atlandi")
    d["neden"] = d["neden"].where(d["durum"] == "atlandi", "").fillna("diger").replace("", "")
    d.loc[(d["durum"] == "atlandi") & (d["neden"] == ""), "neden"] = "diger"
    return d


def ozet(d: pd.DataFrame) -> dict:
    a, s = d[d["durum"] == "alindi"], d[d["durum"] == "atlandi"]
    toplam_poz = d.loc[d["r"] > 0, "r"].sum()
    b3 = d[d["r"] > 3]
    return dict(sinyal=len(d), alinan=len(a), atlanan=len(s), alinan_ort_r=a["r"].mean() if len(a) else float("nan"), alinan_top_r=a["r"].sum(),
                atlanan_ort_r=s["r"].mean() if len(s) else float("nan"), atlanan_top_r=s["r"].sum(),
                r3_toplam=len(b3), r3_atlanan=int((b3["durum"] == "atlandi").sum()),
                r3_atlanan_pay=float((b3["durum"] == "atlandi").mean()) if len(b3) else float("nan"),
                poz_r_atlanan_pay=float(s.loc[s["r"] > 0, "r"].sum() / toplam_poz) if toplam_poz > 0 else float("nan"))


def calistir(onbellek: Path):
    st = json.loads(oy.SET_YOLU.read_text(encoding="utf-8"))
    tum, senaryo_sonuc = [], []
    for k in st["stratejiler"]:
        ad = k["strateji"]
        if k["tur"] != "tek":
            continue
        dosyalar = sorted(onbellek.glob(f"{ad}--*--islem.parquet"))
        if not dosyalar:
            continue
        tr = pd.concat([pd.read_parquet(f) for f in dosyalar], ignore_index=True)
        mt = pd.concat([pd.read_parquet(f) for f in sorted(onbellek.glob(f"{ad}--*--mtm.parquet"))], ignore_index=True)
        for sen, ek in SENARYOLAR.items():
            kayit = []
            r = oy.oyna(tr, mt, "canli", kayit=kayit, boyut_ek=ek)
            d = sinyal_tablosu(tr, kayit)
            d.insert(0, "senaryo", sen)
            if sen == "gercek":
                tum.append(d)
            a = d[d["durum"] == "alindi"]
            senaryo_sonuc.append(dict(strateji=ad, senaryo=sen, islem=r["islem"], alinan_top_r=a["r"].sum(), son_ozsermaye=r["son_ozsermaye"], cagr=r["cagr"],
                                      maks_dusus=r["maks_dusus"], kill=r["kill_tarihi"], min_tutar=r["min_tutar"], gunluk_blok=r["gunluk_blok"]))
    return pd.concat(tum, ignore_index=True), pd.DataFrame(senaryo_sonuc)


def md_tablo(df: pd.DataFrame, fmt: dict | None = None) -> str:
    fmt = fmt or {}
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        out.append("| " + " | ".join((fmt[c](r[c]) if c in fmt else str(r[c])) for c in cols) + " |")
    return "\n".join(out)


def f2(x):
    return "-" if pd.isna(x) else f"{x:.2f}"


def pct(x):
    return "-" if pd.isna(x) else f"{100 * x:.0f}%"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--onbellek", required=True)
    a = ap.parse_args(argv)
    d, sen = calistir(Path(a.onbellek))
    oy.CIKTI.mkdir(parents=True, exist_ok=True)
    d2 = d.copy()
    for c in ("giris_zamani", "cikis_zamani"):
        d2[c] = d2[c].astype(str)
    d2.drop(columns=["senaryo"]).to_csv(oy.CIKTI / "atlanan_teshis.csv", index=False)
    ozet_satir = []
    L = ["# Atlanan sinyal teşhisi (CANLI_LIMITLER yeniden oynatma)", "",
         "**Bu bir TEŞHİSTİR; öneri ya da limit değişikliği değildir.** Geçmiş (v2 geliştirme dönemi, holdout okunmadı) üzerinde, strateji başına 165 USD kasa, "
         "min tutar tablosu BTC 100 / ETH 20 / diğer 5 USDT. R = işlemin backtest R'si (net K/Z / stopa risk). Atlanan işlemin R'si 'alınsaydı olacak R'dir (boyuttan bağımsız).", "",
         "Neden kodları: `min_tutar` (hesaplanan tutar min tutarın altı), `risk_butcesi_dolu` (toplam açık stop riski %6 bütçesi dolu), `brut_tavan` (brüt nominal 1.5x dolu), "
         "`stop_cok_uzak` (stop mesafesi > %25), `gunluk_blok` (günlük -%6 sonrası yeni giriş yok), `kill_sonrasi` (strateji kill sonrası), `diger` (geçersiz stop / kasa yok).", ""]
    # 1) özet
    tab = []
    for ad, g in d.groupby("strateji", sort=False):
        o = ozet(g)
        tab.append(dict(strateji=ad, **o))
    ot = pd.DataFrame(tab)
    L += ["## 1. Alınan ve atlanan: genel", "", md_tablo(ot, {c: f2 for c in ("alinan_ort_r", "alinan_top_r", "atlanan_ort_r", "atlanan_top_r")} | {"r3_atlanan_pay": pct, "poz_r_atlanan_pay": pct}), "",
          "`r3_*`: R>3 olan işlemler; `r3_atlanan_pay`: bunların atlanan payı. `poz_r_atlanan_pay`: stratejinin toplam POZİTİF R'sinin atlananlardan gelen payı.", ""]
    # 2) neden kırılımı
    L += ["## 2. Nedene göre kırılım", ""]
    kir = []
    for ad, g in d.groupby("strateji", sort=False):
        toplam_poz = g.loc[g["r"] > 0, "r"].sum()
        for n in NEDENLER:
            s = g[(g["durum"] == "atlandi") & (g["neden"] == n)]
            b3 = g[g["r"] > 3]
            kir.append(dict(strateji=ad, neden=n, adet=len(s), ort_r=s["r"].mean() if len(s) else float("nan"), top_r=s["r"].sum(),
                            r3_atlanan=int((s["r"] > 3).sum()), r3_pay=((s["r"] > 3).sum() / len(b3)) if len(b3) else float("nan"),
                            poz_r_pay=(s.loc[s["r"] > 0, "r"].sum() / toplam_poz) if toplam_poz > 0 else float("nan")))
    kt = pd.DataFrame(kir)
    kt.to_csv(oy.CIKTI / "atlanan_teshis_ozet.csv", index=False)
    L += [md_tablo(kt[kt["adet"] > 0], {"ort_r": f2, "top_r": f2, "r3_pay": pct, "poz_r_pay": pct}), "",
          "`r3_pay`: stratejideki TÜM R>3 işlemlerin yüzde kaçı bu nedenle atlandı; `poz_r_pay`: toplam pozitif R'nin yüzde kaçı bu nedenle atlanan işlemlerden.", ""]
    # 3) iki strateji: en büyük 10
    L += ["## 3. En büyük 10 R'li işlem (jt-awesome-osilator, voltarget-trend)", ""]
    for ad in ("jt-awesome-osilator", "voltarget-trend"):
        g = d[d["strateji"] == "dis__" + ad].nlargest(10, "r")
        L += [f"### {ad}", ""]
        if not len(g):
            L += ["(veri yok)", ""]
            continue
        t = pd.DataFrame({"sembol": g["sembol"], "giris": g["giris_zamani"].dt.strftime("%Y-%m-%d"), "yon": g["yon"], "R": g["r"], "durum": g["durum"], "neden": g["neden"]})
        L += [md_tablo(t, {"R": f2}), ""]
    # 4) varsayımsal
    L += ["## 4. Varsayımsal senaryolar (YALNIZ TEŞHİS, öneri değil)", "",
          "- `min_tutar_yok`: min tutar kontrolü kapalı (BTC/ETH küçük hesapta alınamayan işlemler alınmış olsaydı).",
          "- `risk_butcesi_sinirsiz`: toplam açık stop riski (%6) ve brüt nominal (1.5x) bütçesi kapalı; yalnız işlem başı %3 kayıp + işlem başı nominal/marj tavanı kalır.", ""]
    st = sen.copy()
    L += [md_tablo(st, {"alinan_top_r": f2, "son_ozsermaye": f2, "cagr": lambda x: f"{100 * x:.1f}%", "maks_dusus": lambda x: f"{100 * x:.1f}%"}), ""]
    (oy.CIKTI / "ATLANAN_TESHIS.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
