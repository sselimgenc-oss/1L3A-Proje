"""Beklenti konisi (pano öncelik 5a): paper başlangıcından itibaren gün gün beklenen özsermaye getirisi aralığı. Hesap BURADA (motor tarafı).

KAYNAK (beklenti aralıklarıyla AYNI): final setin örneklem-DIŞI günlük getirisi (walk-forward OOS + kilitli dönem; `motor.arastirma.beklenti`
`kol_ve_set`, kollar 50/50, yedi stratejinin OOS'ta bulunduğu kesişim günleri). Bu seri `sonuclar/final/beklenti_koni_havuzu.csv` olarak repoda
tutulur (ağır parquet dosyaları sunucuda yoktur); üretici: `python -m motor.canli.koni --havuz-yaz` (yalnız yerel parquet dosyalarını okur, backtest koşmaz).

YÖNTEM: hareketli blok bootstrap (`beklenti_araliklari.csv` ile aynı: blok 14 gün, 10 000 yol, tohum 42; blok bir segment (ardışık gün) içinde kalır).
Her yol havuz günlerinden blokları art arda ekleyip UFUK_GUN güne keser; gün g için birikimli net getiri (bileşik) yüzdelikleri %5/%25/%50/%75/%95.
Ad hoc genişletme/daraltma YOK (eski panonun normal yaklaşım genişletmesi bilerek alınmadı).

LOOKAHEAD YOK / SABİTLEME: koni yalnız `baz_gun` (gün 0 = paper'ın ilk gününden önceki gün) DAHİL öncesi havuz günleriyle üretilir; paper'ın gerçekleşen
günleri havuza girmez ve koni sonradan yeniden ayarlanmaz. Havuz dosyası bu yüzden kodda sabitlenmiş sha256'ya bağlıdır (`HAVUZ_SHA256`): dosya değişirse
koni üretilmez (null + neden) ve değişikliği bilinçli bir kod/commit kararı yapar. Tohum sabittir: aynı havuz + aynı baz gün -> birebir aynı koni.
Backtest görünümünde baz gün backtest döneminin ilk gününden öncedir; o dönemin içindeki günler havuzdan çıkarılır (bağımsız koni).

DÜRÜSTLÜK: set, WF OOS sonuçlarına bakılarak seçildi (aralıklar iyimser olabilir); havuz çoğunlukla kripto boğa/ayı karışımı; blok bootstrap durağanlık
varsayar; backtest havuzu kârı işlemin KAPANDIĞI güne yazar, paper gerçekleşen eğrisi ise açık pozisyonu günlük değerler (kısa ufukta paper eğrisi daha
pürüzsüz olabilir). Seçim yönteminin öngörü gücü kilit testinde zayıf çıktı (sonuclar/kilit/RAPOR.md): koni bir söz değil, kaba bir referanstır.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np

from motor.canli import durum as d

KOK = Path(__file__).resolve().parents[2]
HAVUZ_CSV = KOK / "sonuclar" / "final" / "beklenti_koni_havuzu.csv"
# Havuz dosyasının KAYITLI sha256'sı (koninin paper başlangıcında sabitlendiğinin kanıtı). Havuzu yenilemek bilinçli kararla bu sabiti değiştirir.
HAVUZ_SHA256 = "4cde6cdda3f91457619d79dc61a86b03ddb5c845f16a05a100023151c33658d4"
UFUK_GUN = 112                      # 16 hafta (en erken paper değerlendirmesi 8 hafta = 56 gün; 2 katı gösterilir)
BLOK_GUN = 14                       # beklenti_araliklari.csv ile aynı
N_ORNEK = 10_000                    # aynı
TOHUM = 42                          # aynı
YUZDELIKLER = (5, 25, 50, 75, 95)
ISARETLER = ({"gun_no": 56, "etiket": "8 hafta (en erken değerlendirme)"},)
KEY = ("p05", "p25", "p50", "p75", "p95")


# ---------------------------------------------------------------------------- havuz
def sha256_dosya(yol: Path) -> str:
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def havuz_uret(kok: Path = KOK) -> list:
    """Yerel parquet dosyalarından set günlük getirisi (beklenti_araliklari.csv'nin set satırlarıyla aynı seri). -> [(gun 'YYYY-MM-DD', ret)]."""
    from motor.arastirma import beklenti as bek      # ağır içe aktarma yalnız üretimde
    from motor.arastirma import final_set
    set_ = final_set.yukle(kok / "stratejiler" / "final_set.json")
    v = bek.varliklar_yukle(set_, kok)
    ks = bek.kesisim_gunleri(v)
    tablo = bek.kol_ve_set(set_, v, ks)["set"]
    return [(str(ix.date()), float(r)) for ix, r in zip(tablo.index, tablo["ret"])]


def havuz_yaz(yol: Path = HAVUZ_CSV, kok: Path = KOK) -> Path:
    satirlar = havuz_uret(kok)
    with open(yol, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(("gun", "ret"))
        for g, r in satirlar:
            w.writerow((g, repr(r)))
    return Path(yol)


def havuz_oku(yol: Path = HAVUZ_CSV) -> list:
    """-> [(gun, ret)] gün sırasıyla. Dosya yoksa FileNotFoundError (açık)."""
    with open(yol, encoding="utf-8", newline="") as f:
        satirlar = [(r["gun"], float(r["ret"])) for r in csv.DictReader(f)]
    for g, r in satirlar:
        if not math.isfinite(r):
            raise ValueError(f"koni havuzu: sonlu olmayan getiri ({g})")
    if [g for g, _ in satirlar] != sorted(g for g, _ in satirlar):
        raise ValueError("koni havuzu: günler sıralı değil")
    return satirlar


def _gun_no(g: str) -> int:
    return date.fromisoformat(g).toordinal()


def _gecerli_baslangiclar(gunler: np.ndarray, blok: int) -> np.ndarray:
    """Blok bir segment (ardışık gün) içinde kalacak başlangıç indeksleri."""
    L = len(gunler)
    if L < blok:
        return np.array([], dtype=int)
    atlama = np.r_[0, (np.diff(gunler) != 1).astype(int)]
    seg = np.cumsum(atlama)
    return np.array([i for i in range(L - blok + 1) if seg[i] == seg[i + blok - 1]], dtype=int)


def yollar(havuz: list, ufuk: int = UFUK_GUN, blok: int = BLOK_GUN, n: int = N_ORNEK, tohum: int = TOHUM) -> Optional[np.ndarray]:
    """Birikimli net getiri yolları (n x ufuk); gün g (1..ufuk) sütun g-1. Geçerli blok yoksa None."""
    gunler = np.array([_gun_no(g) for g, _ in havuz], dtype=np.int64)
    ret = np.array([r for _, r in havuz], dtype=float)
    ok = _gecerli_baslangiclar(gunler, blok)
    if len(ok) == 0:
        return None
    rng = np.random.default_rng(tohum)
    nb = math.ceil(ufuk / blok)
    bas = ok[rng.integers(len(ok), size=(n, nb))]
    idx = (bas[:, :, None] + np.arange(blok)[None, None, :]).reshape(n, nb * blok)[:, :ufuk]
    return np.cumprod(1.0 + ret[idx], axis=1) - 1.0


def _bant(deger: float, q: dict) -> str:
    return d.bant_bul(deger, q["p05"], q["p25"], q["p50"], q["p75"], q["p95"])


def _gun_str(baz_gun: str, no: int) -> str:
    return str(date.fromisoformat(baz_gun) + timedelta(days=no))


# ---------------------------------------------------------------------------- durum dosyası
def olustur(kaynak: str, zaman: str, baz_gun: str, gerceklesen: Optional[list], havuz_yolu: Path = HAVUZ_CSV,
            sha_kayitli: Optional[str] = HAVUZ_SHA256, ufuk: int = UFUK_GUN, n: int = N_ORNEK) -> dict:
    """koni.json içeriği.
    baz_gun: gün 0 (paper'ın ilk gününden önceki gün, 'YYYY-MM-DD'); koni yalnız bu güne KADAR olan havuz günleriyle üretilir.
    gerceklesen: [{'gun': 'YYYY-MM-DD', 'getiri': float}] gerçekleşen birikimli net getiri (başlangıç özsermayesine göre; baz günü dahil olabilir) | None.
    sha_kayitli: havuz dosyasının kayıtlı sha256'sı; None = denetim yok (yalnız testler)."""
    govde = {**d._zarf("koni", kaynak, zaman), "baz_gun": baz_gun, "ufuk_gun": ufuk, "blok_gun": BLOK_GUN, "n_ornek": n, "tohum": TOHUM,
             "yuzdelikler": list(YUZDELIKLER), "isaretler": [x for x in ISARETLER if x["gun_no"] <= ufuk],
             "yontem": f"Hareketli blok bootstrap ({BLOK_GUN} günlük bloklar, {n} yol, tohum {TOHUM}) final setin örneklem-dışı günlük getirisinden "
                       "(beklenti_araliklari.csv ile aynı kaynak); gün g = birikimli net getiri yüzdelikleri.",
             "sabitleme": "Koni baz günden önceki verilerle üretilir ve sonradan yeniden ayarlanmaz (gerçekleşen günler havuza girmez; havuz dosyası kayıtlı sha256'ya bağlı).",
             "notlar": ["Set, walk-forward OOS sonuçlarına bakılarak seçildi: koni iyimser olabilir; havuz çoğunlukla kripto boğa/ayı karışımı.",
                        "Backtest havuzu kârı işlem kapanış gününe yazar, paper gerçekleşen eğrisi açık pozisyonu günlük değerler: kısa ufukta eğri koniden pürüzsüz olabilir.",
                        "Kilit testinde seçim yönteminin öngörü gücü zayıf çıktı: bant bir söz değil, kaba bir referanstır; tek başına karar için kullanılmaz."]}
    govde["gerceklesen"] = None
    govde["koni"], govde["koni_neden"], govde["konum"], govde["konum_neden"], govde["havuz"] = None, None, None, None, None

    def bos(neden: str) -> dict:
        govde["koni_neden"], govde["konum_neden"] = neden, neden
        return govde

    try:
        tum = havuz_oku(havuz_yolu)
    except FileNotFoundError:
        return bos(f"koni havuzu dosyası yok: {Path(havuz_yolu).name} (python -m motor.canli.koni --havuz-yaz)")
    sha = sha256_dosya(Path(havuz_yolu))
    uyum = "kayit_yok" if sha_kayitli is None else ("eslesti" if sha == sha_kayitli else "uyusmuyor")
    havuz = [(g, r) for g, r in tum if g <= baz_gun]               # LOOKAHEAD YOK: baz gün sonrası havuza girmez
    govde["havuz"] = {"kaynak": "set günlük getirisi (WF OOS + kilitli dönem, kollar 50/50; beklenti_araliklari.csv set satırlarıyla aynı seri)",
                      "dosya": Path(havuz_yolu).name, "sha256": sha, "kayitli_sha256": sha_kayitli, "dogrulama": uyum,
                      "tum_gun_sayisi": len(tum), "gun_sayisi": len(havuz), "bas": havuz[0][0] if havuz else None, "bit": havuz[-1][0] if havuz else None,
                      "baz_gun_sonrasi_cikarilan": len(tum) - len(havuz)}
    if uyum == "uyusmuyor":
        return bos("havuz dosyası kayıtlı sha256 ile uyuşmuyor: koni sabitlenmemiş sayılır, üretilmedi (HAVUZ_SHA256 bilinçli güncellenmeli)")
    y = yollar(havuz, ufuk, BLOK_GUN, n)
    if y is None:
        return bos(f"baz günden ({baz_gun}) önceki havuzda {BLOK_GUN} günlük ardışık blok yok ({len(havuz)} gün): koni üretilemedi")
    q = np.percentile(y, YUZDELIKLER, axis=0)
    koni = [{"gun_no": 0, "gun": baz_gun, **{k: 0.0 for k in KEY}}]
    for g in range(1, ufuk + 1):
        koni.append({"gun_no": g, "gun": _gun_str(baz_gun, g), **{k: float(q[i, g - 1]) for i, k in enumerate(KEY)}})
    govde["koni"] = koni
    if gerceklesen is None:
        govde["konum_neden"] = "gerçekleşen özsermaye geçmişi yok"
        return govde
    gz = []
    for x in gerceklesen:
        no = (date.fromisoformat(x["gun"]) - date.fromisoformat(baz_gun)).days
        if no < 0 or x.get("getiri") is None:
            continue
        gz.append({"gun_no": no, "gun": x["gun"], "getiri": d.sayi(x["getiri"])})
    govde["gerceklesen"] = gz
    if not gz or gz[-1]["gun_no"] < 1:
        govde["konum_neden"] = "paper'ın tamamlanmış günü henüz yok (gün 0 yalnız başlangıç)"
        return govde
    ic = [x for x in gz if x["gun_no"] <= ufuk]
    if not ic:
        govde["konum_neden"] = f"gerçekleşen günler koni ufkunun ({ufuk} gün) dışında"
        return govde
    son = ic[-1]
    satir = koni[son["gun_no"]]
    col = y[:, son["gun_no"] - 1]
    sira = float(((col < son["getiri"]).sum() + 0.5 * (col == son["getiri"]).sum()) / len(col))   # orta sıra: simüle yolların bu kadarından daha kötü
    govde["konum"] = {"gun_no": son["gun_no"], "gun": son["gun"], "getiri": son["getiri"], **{k: satir[k] for k in KEY},
                      "bant": _bant(son["getiri"], satir), "yuzdelik_sira": sira,
                      "not": None if son is gz[-1] else f"gerçekleşen {gz[-1]['gun_no']}. güne kadar sürdü; konum koni ufkundaki son gün ({son['gun_no']}) içindir"}
    return govde


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Beklenti konisi havuzu (yerel parquet dosyalarından) ve doğrulama")
    ap.add_argument("--havuz-yaz", action="store_true", help=f"{HAVUZ_CSV.name} dosyasını yeniden üretir (sha256 sabitini sonra elle güncelle)")
    a = ap.parse_args(argv)
    if a.havuz_yaz:
        yol = havuz_yaz()
        print(f"{yol} yazıldı; sha256 = {sha256_dosya(yol)}")
        return 0
    print(f"{HAVUZ_CSV.name}: sha256 = {sha256_dosya(HAVUZ_CSV)} (kayıtlı: {HAVUZ_SHA256})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
