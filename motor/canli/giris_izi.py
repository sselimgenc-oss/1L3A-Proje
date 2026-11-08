"""Sürüm izi + giriş gerekçesi (pano öncelik 4; envanter F40, F23 temeli). Paper işlem kaydına (`islemler.jsonl`) her işlem için:

  `ayar_surumu`     {hash, set_dosyasi, ayar, strateji}: kullanılan parametre setinin kısa hash'i. Hash = sha256("strateji_adı|ayar_etiketi")[:12].
                    Ayar etiketi (guncel_ayarlar.csv / final_set.json'daki `ayar`) aday listesinde parametre kümesini TEK anlamlı tanımlar
                    (`izgara:{...}` parametreleri açıkça taşır, `csv:N` aday listesinin N. satırıdır). Ayar yenilemesi (180/90 gün) etiketi,
                    dolayısıyla hash'i değiştirir: eski/yeni ayarın işlemleri karışmaz.
  `giris_gerekcesi` stratejinin SİNYAL ANINDA (karar mumunun kapanışında) bilinen değerlerinden kurallı açıklama.
                    Stratejiler koşul metni üretmez; bu yüzden GENEL ŞABLON (`genel/1`): strateji adı + yön + sinyal mumu zamanı +
                    kapanış fiyatı + stop/hedef mesafesi + sinyal tablosundaki ek sütunlar (göstergeler) + çıkış kuralları.
                    Hepsi karar anında elde olan satırdan okunur (mumlar <= t): LOOKAHEAD YOK. Giriş dolumu (sonraki açılış) sonradan bilinir
                    ve gerekçeye girmez (dolum fiyatı zaten işlem satırındadır).

Gerekçe ve sürüm, karar anında üretilir ve motorda pozisyon açılırken pozisyona bağlanır (paper_motor.karar_meta / giris_meta);
kapanan işlem satırına yazılır. Eski kayıtlarda (bu özellikten önce) alanlar `null`dır.
"""
from __future__ import annotations

import hashlib
import math
from typing import Optional

import pandas as pd

from motor.canli import durum as d

SABLON = "genel/1"
STANDART_SUTUNLAR = ("yon", "stop", "hedef", "cikis", "cikis_long", "cikis_short", "zaman_cikisi_mum")
MAX_GOSTERGE = 12


def ayar_surumu(strateji_ad: str, ayar_etiketi: str, set_dosyasi: str) -> dict:
    h = hashlib.sha256(f"{strateji_ad}|{ayar_etiketi}".encode("utf-8")).hexdigest()[:12]
    return {"hash": h, "set_dosyasi": set_dosyasi, "ayar": ayar_etiketi, "strateji": strateji_ad}


def _f(x) -> Optional[float]:
    """JSON-güvenli sayı: NaN/inf/sayı olmayan -> None."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _oran(a: Optional[float], b: Optional[float]) -> Optional[float]:
    return abs(a - b) / abs(a) if a and b is not None else None


def _yuzde(x: Optional[float]) -> str:
    return "—" if x is None else f"%{x * 100:.2f}"


def _fiyat(x: Optional[float]) -> str:
    return "—" if x is None else f"{x:.8g}"


def _sinyal_zamanlari(acilis, aralik) -> tuple:
    a = pd.Timestamp(acilis)
    a = a.tz_localize("UTC") if a.tzinfo is None else a.tz_convert("UTC")
    return d.zaman_str(a), d.zaman_str(a + aralik)


def _gostergeler(satir: pd.Series) -> dict:
    """Sinyal satırındaki standart olmayan SAYISAL sütunlar (strateji göstergeleri); karar mumunun değerleri."""
    out = {}
    for ad, v in satir.items():
        if ad in STANDART_SUTUNLAR or isinstance(v, (bool,)):
            continue
        f = _f(v)
        if f is not None:
            out[str(ad)] = f
        if len(out) >= MAX_GOSTERGE:
            break
    return out


def _cikis_kurallari(ca) -> dict:
    """Çıkış ayarlarından yalnız tanımlı olanlar (strateji parametresi; sinyal anında bellidir)."""
    kur = {}
    for ad in ("atr_iz_suren_k", "sabit_r_hedefi", "zaman_cikisi_mum", "basabas_r_esigi"):
        v = getattr(ca, ad, None)
        if v:
            kur[ad] = _f(v)
    if getattr(ca, "kismi", None):
        kur["kismi"] = [[_f(r), _f(o)] for r, o in ca.kismi]
    return kur


def _metin(g: dict) -> str:
    parca = [f"{g['strateji']} ({g['sembol']} {g['tf']}): {g['yon'].upper()} sinyali; sinyal mumu {g['sinyal_mumu_acilis']} → {g['sinyal_mumu_kapanis']} "
             f"(kapanış {_fiyat(g['sinyal_kapanis_fiyati'])})."]
    if g.get("stop") is not None:
        parca.append(f"Stop {_fiyat(g['stop'])} (kapanıştan {_yuzde(g['stop_mesafe_oran'])} uzakta).")
    else:
        parca.append("Stop: sinyalde yok.")
    if g.get("hedef") is not None:
        parca.append(f"Hedef {_fiyat(g['hedef'])} (kapanıştan {_yuzde(g['hedef_mesafe_oran'])}).")
    elif (g.get("cikis_kurallari") or {}).get("sabit_r_hedefi"):
        parca.append(f"Hedef: {g['cikis_kurallari']['sabit_r_hedefi']:g}R (giriş dolumunda belirlenir).")
    if g.get("hedef_agirlik") is not None:
        parca.append(f"Hedef ağırlık {g['hedef_agirlik']:+.4f} (strateji ağırlığı).")
    if g.get("gostergeler"):
        parca.append("Göstergeler: " + ", ".join(f"{k}={v:.6g}" for k, v in g["gostergeler"].items()) + ".")
    parca.append("Koşul metni strateji tarafından üretilmez: genel şablon (genel/1).")
    return " ".join(parca)


def gerekce_tek(t, mumlar: pd.DataFrame, sig: pd.DataFrame, yon: int, stop, hedef) -> dict:
    """Tek-grafik sinyali. `mumlar`/`sig` karar anına kadardır (son satır = sinyal mumu); `t`: StratejiTanim."""
    from motor.veri.depo import aralik_suresi
    son = sig.iloc[-1]
    acilis, kapanis = _sinyal_zamanlari(mumlar.index[-1], aralik_suresi(t.tf))
    c = _f(mumlar["kapanis"].iloc[-1])
    stop, hedef = _f(stop), _f(hedef)
    g = {"sablon": SABLON, "kaynak": "genel_sablon", "strateji": t.strateji_ad, "kimlik": t.kimlik, "sembol": t.sembol, "tf": t.tf,
         "yon": "long" if yon == 1 else "short", "sinyal_mumu_acilis": acilis, "sinyal_mumu_kapanis": kapanis, "sinyal_kapanis_fiyati": c,
         "stop": stop, "stop_mesafe_oran": _oran(c, stop), "hedef": hedef, "hedef_mesafe_oran": _oran(c, hedef), "hedef_agirlik": None,
         "gostergeler": _gostergeler(son), "cikis_kurallari": _cikis_kurallari(t.nesne.cikis_ayarlari)}
    g["metin"] = _metin(g)
    return g


def gerekce_agirlik(t, sembol: str, acilis, kapanis_fiyati, w: float, stop) -> dict:
    """Portföy (hedef ağırlık) kararı; sembol başına. `acilis`: sinyal mumunun açılışı (ortak eksenin son satırı)."""
    from motor.veri.depo import aralik_suresi
    a, k = _sinyal_zamanlari(acilis, aralik_suresi(t.tf))
    c, stop = _f(kapanis_fiyati), _f(stop)
    g = {"sablon": SABLON, "kaynak": "genel_sablon", "strateji": t.strateji_ad, "kimlik": t.kimlik, "sembol": sembol, "tf": t.tf,
         "yon": "long" if w > 0 else "short", "sinyal_mumu_acilis": a, "sinyal_mumu_kapanis": k, "sinyal_kapanis_fiyati": c,
         "stop": stop, "stop_mesafe_oran": _oran(c, stop), "hedef": None, "hedef_mesafe_oran": None, "hedef_agirlik": _f(w),
         "gostergeler": {}, "cikis_kurallari": {}}
    g["metin"] = _metin(g)
    return g
