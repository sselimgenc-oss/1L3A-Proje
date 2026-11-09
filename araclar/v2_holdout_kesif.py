"""v2 holdout KEŞİF koşusu (kullanıcı kararı 2026-11-09; SONUÇ SONRASI, ON_KAYIT_V2 0.3/0.4'ten bilinçli sapma).

Resmi holdout (set 2 strateji, GEÇTİ) bittikten sonra kıl payı kalan stratejiler holdout döneminde tek tek ölçülür.
Etiket: "sonuç sonrası keşif — kanıt değil". Resmi holdout dosyalarına dokunmaz; çıktı sonuclar/evren/v2/holdout_kesif/.
Ölçüm resmi holdout ile aynı fonksiyonla (holdout.strateji_olc): tek başına tek kasa, maliyet x1, s=0.5, K2 B=2000 (hk2).
Kaldığı yerden devam eder (strateji başına json).

Kullanım: PYTHONPATH=. python araclar/v2_holdout_kesif.py
"""
import json
from pathlib import Path

import pandas as pd

from motor.arastirma.v2 import holdout as ho
from motor.arastirma.v2 import ham as hm

KOK = Path("sonuclar/evren/v2")
CIKTI = KOK / "holdout_kesif"
S = 0.5
ETIKET = "sonuç sonrası keşif — kanıt değil (kullanıcı kararı 2026-11-09)"

GRUP = {  # 1-3: sağlamlık/test aşamasında kıl payı; 4: eleme'de tek kapıdan kalan (hata satırları hariç)
    "1_set_disi_saglam": ["dis__ama-egri-donus-filtresi", "dis__aroon-stochrsi-ema-dip", "dis__gauss-stoch-btc"],
    "2_izleme": ["dis__haftalik-macd-gunluk-ma", "dis__e0v1en"],
    "3_bh_alti": ["dis__one-mr1", "dis__sma200-ls"],
}


def adaylar() -> list:
    havuz = pd.read_csv("stratejiler/havuz_v2.csv")
    el = pd.read_csv(KOK / "eleme.csv")
    el["nk"] = el[["e1", "e2", "e3", "e4", "e5"]].eq(False).sum(axis=1)
    g4 = el[(el.nk == 1) & (el.hata.isna())].strateji.tolist()
    sira = [(g, s) for g, ss in GRUP.items() for s in ss] + [("4_eleme_tek_kapi", s) for s in g4]
    out = []
    for g, s in sira:
        r = havuz[havuz.strateji == s]
        if len(r) != 1:
            raise RuntimeError(f"{s}: havuzda {len(r)} satır")
        r = r.iloc[0].to_dict()
        etiket = hm.varsayilan_strateji(s)[0] if r["stil_v2"] != "portfoy" else "varsayilan"
        out.append({"grup": g, "strateji": s, "tf": r["tf"], "evren": r["evren"], "stil_v2": r["stil_v2"], "ayar": etiket,
                    "kilit_gorulmus": r["kilit_gorulmus"]})
    return out


def main():
    CIKTI.mkdir(parents=True, exist_ok=True)
    liste = adaylar()
    print(f"[kesif] {len(liste)} strateji", flush=True)
    tablo = KOK / "maliyet_tablosu_v2.csv"
    ho._YETKI["acik"] = True                       # bilinçli: kullanıcı kararıyla keşif koşusu (resmi holdout bitti)
    sag = ho.GercekSaglayici(tablo)
    bit = pd.Timestamp(sag.veri_sonu())
    bit = bit.tz_localize("UTC") if bit.tzinfo is None else bit.tz_convert("UTC")
    for i, k in enumerate(liste, 1):
        yol = CIKTI / f"{k['strateji']}--{k['tf']}.json"
        if yol.exists():
            continue
        ilk = {"islemler": {}, "sira": {}, "hatalar": {}, "pf_gunluk": {}}
        try:
            if k["stil_v2"] == "portfoy":
                ilk["pf_gunluk"][k["strateji"]] = sag.pf_gunluk(k)
            else:
                isl, sira, hat = sag.tek_islemler(k)
                ilk["islemler"][k["strateji"]], ilk["sira"][k["strateji"]], ilk["hatalar"][k["strateji"]] = isl, sira, hat
            olc = ho.strateji_olc(k, sag, S, tablo, bit, ilk)
        except Exception as e:  # noqa: BLE001  (satır 'hata' olur, sayılır, raporlanır)
            olc = {"hata": f"{type(e).__name__}: {e}"[:300]}
        yol.write_text(json.dumps({**k, **olc, "s": S, "veri_sonu": str(bit), "etiket": ETIKET}, ensure_ascii=False, default=float))
        print(f"[kesif] {i}/{len(liste)} {k['strateji']} {olc}", flush=True)
    rows = [json.loads(p.read_text()) for p in sorted(CIKTI.glob("*.json"))]
    pd.DataFrame(rows).to_csv(CIKTI / "holdout_kesif.csv", index=False)
    print("[kesif] bitti", flush=True)


if __name__ == "__main__":
    main()
