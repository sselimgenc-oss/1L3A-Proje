"""Strateji kaydı: paketleri tarar, kalite kapısı (`dogrula`) ve kart ayarları.

Kart ayarı: stratejiler/kart_ayarlari/<aile_id>.json (biçim: o klasörün README.md'si).
"""
from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
from itertools import product
from pathlib import Path

from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.temel import Strateji

KOK = Path(__file__).resolve().parents[2]
KART_AYAR_DIZINI = KOK / "stratejiler" / "kart_ayarlari"
KART_HAM_DIZINI = KOK / "veri" / "kartlar_ham"
AILELER_YOLU = KOK / "stratejiler" / "aileler.json"
PAKETLER = ("swing", "daytrade", "scalp", "onceki", "dis")
STILLER = {"scalp", "daytrade", "swing"}
MAKS_IZGARA = 27
_CIKIS_ALANLARI = {"atr_iz_suren_k", "atr_periyot", "zaman_cikisi_mum", "sabit_r_hedefi", "basabas_r_esigi", "kismi",
                   "stop_basamaklari", "azalan_roi", "geri_cekilme_yuzde", "geri_cekilme_min_kar_yuzde",
                   "kar_rsi_esikleri", "rsi_periyot", "elder_guvenli_bolge_k", "elder_n1", "elder_n2",
                   "agresif_iz_esigi", "agresif_iz_atr_k", "stop_sonrasi_bekleme_mum",
                   "yalniz_karda_cikis", "yalniz_karda_min_kar_yuzde", "min_tutma_mum", "yasa_bagli_zarar_cikisi",
                   "kapanis_chandelier_k", "kapanis_chandelier_periyot", "kismi_yuzde"}


def _modul_adlari() -> list[str]:
    adlar = ["motor.strateji.ma_kesisim"]
    for paket in PAKETLER:
        p = importlib.import_module(f"motor.strateji.{paket}")
        for m in pkgutil.iter_modules(p.__path__):
            adlar.append(f"{p.__name__}.{m.name}")
    return adlar


def _tara() -> tuple[dict[str, type], list[str]]:
    sonuc: dict[str, type] = {}
    sorunlar: list[str] = []
    for mod_adi in _modul_adlari():
        mod = importlib.import_module(mod_adi)
        for _, sinif in inspect.getmembers(mod, inspect.isclass):
            if sinif.__module__ != mod.__name__ or not issubclass(sinif, Strateji) or sinif is Strateji:
                continue
            if not sinif.ad:
                continue
            if sinif.ad in sonuc:
                sorunlar.append(f"{sinif.ad}: ad birden fazla sınıfta ({sonuc[sinif.ad].__module__}, {mod_adi})")
                continue
            sonuc[sinif.ad] = sinif
    return sonuc, sorunlar


def tum_stratejiler() -> dict[str, type]:
    """ad -> sınıf. Aynı ad iki kez tanımlıysa ValueError."""
    sonuc, sorunlar = _tara()
    if sorunlar:
        raise ValueError("; ".join(sorunlar))
    return sonuc


def al(ad: str) -> type:
    kayit = tum_stratejiler()
    if ad not in kayit:
        raise KeyError(f"Strateji yok: {ad!r}")
    return kayit[ad]


def stile_gore(stil: str) -> dict[str, type]:
    return {a: s for a, s in tum_stratejiler().items() if s.stil == stil}


# ---------------------------------------------------------------- kart ayarları
def kart_ayarlari(ad: str) -> list:
    yol = KART_AYAR_DIZINI / f"{ad}.json"
    if not yol.exists():
        return []
    return json.loads(yol.read_text(encoding="utf-8"))


def kart_ayarli_strateji(ad: str, kart_id: str) -> Strateji:
    sinif = al(ad)
    for kayit in kart_ayarlari(ad):
        if kayit["kart_id"] == kart_id:
            par = dict(kayit.get("parametreler") or {})
            bilinmeyen = set(par) - set(sinif.varsayilan_parametreler)
            if bilinmeyen:
                raise ValueError(f"{ad}/{kart_id}: sınıfta olmayan parametre: {sorted(bilinmeyen)}")
            cikis = kayit.get("cikis_ayarlari")
            if cikis is not None:
                cikis = dict(cikis)
                for alan in ("kismi", "stop_basamaklari", "azalan_roi", "kar_rsi_esikleri",
                             "yasa_bagli_zarar_cikisi", "kismi_yuzde"):
                    if alan in cikis:
                        cikis[alan] = tuple(tuple(x) for x in cikis[alan])
                cikis = CikisAyarlari(**cikis)
            return sinif(cikis_ayarlari=cikis, **par)
    raise KeyError(f"{ad}: kart ayarı yok: {kart_id!r}")


def _ham_kart_idleri() -> set[str]:
    idler: set[str] = set()
    for yol in KART_HAM_DIZINI.rglob("*.json"):
        try:
            for k in json.loads(yol.read_text(encoding="utf-8")):
                if isinstance(k, dict) and "kart_id" in k:
                    idler.add(k["kart_id"])
        except (ValueError, OSError):
            continue
    return idler


# ---------------------------------------------------------------- kalite kapısı
def dogrula() -> list[str]:
    """Sorun listesi; boşsa her şey yolunda."""
    kayit, sorunlar = _tara()
    for ad, s in kayit.items():
        if s.stil not in STILLER:
            sorunlar.append(f"{ad}: geçersiz stil {s.stil!r}")
        try:
            ornek = s()
        except Exception as e:  # noqa: BLE001
            sorunlar.append(f"{ad}: varsayılan parametrelerle örneklenemedi: {e!r}")
            continue
        n = 1
        for degerler in s.parametre_izgarasi.values():
            n *= len(degerler)
        if n > MAKS_IZGARA:
            sorunlar.append(f"{ad}: ızgara {n} kombinasyon (> {MAKS_IZGARA})")
        dis = set(s.parametre_izgarasi) - set(s.varsayilan_parametreler)
        if dis:
            sorunlar.append(f"{ad}: ızgara anahtarı varsayilan_parametreler'de yok: {sorted(dis)}")
        ca = ornek.cikis_ayarlari
        ayarda_cikis = any(getattr(ca, a) not in (None, ()) for a in
                           ("atr_iz_suren_k", "zaman_cikisi_mum", "sabit_r_hedefi", "azalan_roi",
                            "geri_cekilme_yuzde", "kar_rsi_esikleri", "yasa_bagli_zarar_cikisi", "kapanis_chandelier_k"))
        if not ornek.cikis_var_mi() and not ayarda_cikis:
            sorunlar.append(f"{ad}: çıkış yok (cikis_var_mi False ve CikisAyarlari'nda çıkış yok)")
    sorunlar += _kart_ayar_sorunlari(kayit)
    return sorunlar


def _kart_ayar_sorunlari(kayit: dict[str, type]) -> list[str]:
    if not KART_AYAR_DIZINI.exists():
        return []
    sorunlar: list[str] = []
    ham = _ham_kart_idleri()
    aileler = {a["aile_id"]: a for a in json.loads(AILELER_YOLU.read_text(encoding="utf-8"))} \
        if AILELER_YOLU.exists() else {}
    for yol in sorted(KART_AYAR_DIZINI.glob("*.json")):
        ad = yol.stem
        if ad not in kayit:
            sorunlar.append(f"kart_ayarlari/{yol.name}: bu adla strateji yok")
            continue
        sinif = kayit[ad]
        try:
            liste = json.loads(yol.read_text(encoding="utf-8"))
        except ValueError as e:
            sorunlar.append(f"kart_ayarlari/{yol.name}: geçersiz JSON: {e}")
            continue
        for k in liste:
            kid = k.get("kart_id")
            on = f"kart_ayarlari/{yol.name}[{kid}]"
            if set(k) - {"kart_id", "parametreler", "cikis_ayarlari", "not"}:
                sorunlar.append(f"{on}: bilinmeyen anahtar {sorted(set(k) - {'kart_id', 'parametreler', 'cikis_ayarlari', 'not'})}")
            if ham and kid not in ham:
                sorunlar.append(f"{on}: kart_id veri/kartlar_ham içinde yok")
            if ad in aileler and kid not in aileler[ad]["kaynak_kartlar"]:
                sorunlar.append(f"{on}: kart_id ailenin kaynak_kartlar listesinde değil")
            bil = set(k.get("parametreler") or {}) - set(sinif.varsayilan_parametreler)
            if bil:
                sorunlar.append(f"{on}: sınıfta olmayan parametre {sorted(bil)}")
            c = k.get("cikis_ayarlari")
            if c is not None and set(c) - _CIKIS_ALANLARI:
                sorunlar.append(f"{on}: bilinmeyen cikis_ayarlari anahtarı {sorted(set(c) - _CIKIS_ALANLARI)}")
            if not bil and (c is None or not set(c) - _CIKIS_ALANLARI):
                try:
                    kart_ayarli_strateji(ad, kid)
                except Exception as e:  # noqa: BLE001
                    sorunlar.append(f"{on}: kurulamadı: {e!r}")
    return sorunlar
