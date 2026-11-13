"""Kapanış turu AŞAMA 1 koşu listesini üretir ve DONDURUR (ON_KAYIT_KAPANIS ek 4).

Çıktılar (sonuç görülmeden, gerçek mum verisi okunmadan):
  sonuclar/kapanis/kosu_listesi_asama1.csv          koşulacak + çözülemeyen kimlikler (BH ailesi = bu dosyanın satır sayısı)
  sonuclar/kapanis/kosu_listesi_asama1.csv.sha256   dosyanın SHA-256'sı
  sonuclar/kapanis/kosu_listesi_asama1_elenen.csv   durum=ELENDI_ON (eleme.csv ÇIKAR) kayıtları; koşulmaz, aileye girmez

Kaynaklar: G8 (kod_g8_kod_1..8 + kod_g8_modul VARYANTLAR; g8_mevcut_sinif.csv), K1 (ara/k1_nihai.csv), K2 (ara/k2_nihai.csv);
yalnız KOSULACAK satırlar. Aynı hipotez birleştirmesi (K katmanının kimliği kalır, `eslesme` G8 kimliğini yazar) ve eleme tablosu
(eleme/eleme.csv, ÇIKAR) burada uygulanır. Çözülemeyen satır COZULEMEDI durumuyla listede kalır (sessizce atılmaz).

Dondurma: dosya + .sha256 varsa ve yeni üretim farklıysa üzerine YAZILMAZ (hata); bilinçli yeniden dondurma `--yeniden-dondur`.
Bu modül ayrıca koşu betiğinin kullandığı sınıf/evren çözücülerini barındırır.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import inspect
import json
import pkgutil
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

KAPANIS = KOK / "sonuclar" / "kapanis"
LISTE_CSV = KAPANIS / "kosu_listesi_asama1.csv"
ELENEN_CSV = KAPANIS / "kosu_listesi_asama1_elenen.csv"
SUTUNLAR = ["kimlik", "katman", "kaynak_id", "sinif", "modul", "parametreler", "tf", "yon", "evren", "yaklasik",
            "emin_degil", "eslesme", "durum", "notlar"]
ELENEN_SUTUNLAR = SUTUNLAR + ["gerekce"]
G8_MODULLER = [f"kod_g8_kod_{i}" for i in range(1, 9)] + ["kod_g8_modul"]

# Aynı hipotez eşlemesi: G8 kimliği -> K katmanı kimliği (K katmanınınki kalır). X005:395#n: JSE VMA bant kuralları (K2 VmaBantKaynak).
ESLEME = {"HAM:X005:2": "HAM:X005:2", "HAM:X005:5#v1": "HAM:X005:5", "HAM:X005:83#v1": "HAM:X005:83",
          "HAM:X005:879#v1": "HAM:X005:879", **{f"HAM:X005:395#{n}#v1": f"HAM:X005:395#{n}" for n in range(1, 11)}}

# K2 kimliği -> sınıf adı (K2 dosyasında sinif=YENI; sınıflar motor/strateji/kapanis/k2_kaynak.py içindedir)
K2_YENI_SINIF = {"HAM:X005:879": "kapanis__flipper-s0879", "HAM:X005:83": "kapanis__donchian-ema-2r-s0083",
                 "HAM:A005:8": "kapanis__ichimoku-c4-arsiv", "HAM:A006:3": "kapanis__argus-gizli-boga-d3",
                 **{f"HAM:X005:395#{n}": "kapanis__vma-bant" for n in range(1, 11)}}


# ---------------------------------------------------------------- sınıf çözümü (koşu betiği de kullanır)
_SINIF_ONB: dict = {}


def sinif_haritasi() -> dict:
    """ad -> Strateji sınıfı (kapanış paketi önce, sonra genel kayıt defteri) ve ad -> portföy sınıfı ('pf__...')."""
    if _SINIF_ONB:
        return _SINIF_ONB
    from motor.portfoy.stratejiler import tum_portfoy_stratejileri
    from motor.strateji import kayit
    from motor.strateji.temel import Strateji
    tek: dict = {}
    paket = importlib.import_module("motor.strateji.kapanis")
    for m in pkgutil.iter_modules(paket.__path__):
        mod = importlib.import_module(f"motor.strateji.kapanis.{m.name}")
        adaylar = [c for _, c in inspect.getmembers(mod, inspect.isclass)]
        s = getattr(mod, "SINIFLAR", None)
        if isinstance(s, dict):
            adaylar += list(s.values())
        elif isinstance(s, (list, tuple)):
            adaylar += list(s)
        for c in adaylar:
            if isinstance(c, type) and issubclass(c, Strateji) and c is not Strateji and getattr(c, "ad", ""):
                tek.setdefault(c.ad, c)
    for ad, c in kayit.tum_stratejiler().items():
        tek.setdefault(ad, c)
    _SINIF_ONB.update({"tek": tek, "pf": dict(tum_portfoy_stratejileri())})
    return _SINIF_ONB


def sinif_coz(sinif: str, modul: str = ""):
    """-> (sınıf, portfoy_mu). 'yol/dosya.py:Sinif' biçimi ve `modul` alanı desteklenir. Bulunamazsa KeyError."""
    if "/" in sinif and ":" in sinif:
        yol, ad = sinif.rsplit(":", 1)
        mod = importlib.import_module(yol[:-3].replace("/", "."))
        return getattr(mod, ad), False
    h = sinif_haritasi()
    if sinif.startswith("pf__") and sinif in h["pf"]:
        return h["pf"][sinif], True
    if sinif in h["tek"]:
        return h["tek"][sinif], False
    if modul:
        mod = importlib.import_module(modul)
        for _, c in inspect.getmembers(mod, inspect.isclass):
            if getattr(c, "ad", None) == sinif:
                return c, False
    raise KeyError(f"sınıf bulunamadı: {sinif!r}")


def evren_coz(evren: str) -> tuple:
    """'kripto13' -> v2 evren_listesi('kripto'); 'A,B' -> açık liste."""
    if evren == "kripto13":
        from motor.arastirma.v2 import sabit
        return sabit.evren_listesi("kripto")
    semboller = tuple(s.strip() for s in evren.split(",") if s.strip())
    if not semboller:
        raise ValueError(f"evren çözülemedi: {evren!r}")
    return semboller


def strateji_kur(sinif: str, modul: str, parametreler: dict):
    """-> (strateji nesnesi | None, portfoy_mu). Portföy sınıfı burada kurulmaz (koşu `portfoy_kos` ile)."""
    cls, pf = sinif_coz(sinif, modul)
    if pf:
        cls(**parametreler)                    # parametre doğrulaması (bilinmeyen anahtar -> ValueError)
        return None, True
    return cls(**parametreler), False


# ---------------------------------------------------------------- kaynak okuyucular
def _csv_oku(yol: Path) -> list:
    with open(yol, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _json(o) -> str:
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _bos_satir(**kw) -> dict:
    s = {k: "" for k in SUTUNLAR}
    s.update(kw)
    return s


def g8_varyant_satirlari() -> list:
    out = []
    for ad in G8_MODULLER:
        mod = importlib.import_module(f"motor.strateji.kapanis.{ad}")
        for v in mod.VARYANTLAR:
            par = dict(v["parametreler"])
            yon = ""
            if "short" in par:
                yon = "iki" if par["short"] else "long"
            out.append(_bos_satir(
                kimlik=v["kimlik"], katman="G8", kaynak_id=re.sub(r"#v\d+$", "", v["kimlik"]), sinif=v["sinif"],
                modul=v.get("modul", ""), parametreler=_json(par), tf=v["tf"], yon=yon, evren="kripto13",
                yaklasik="1" if v.get("yaklasik") else "", emin_degil="1" if v.get("emin_degil") else "",
                notlar=f"kaynak={ad}.py"))
    return out


def g8_mevcut_satirlari(yol: Path) -> list:
    out = []
    for r in _csv_oku(yol):
        if r["karar"] != "KOSULACAK":
            continue
        ayar = json.loads(r["ayar"])
        ayarlar = ayar if isinstance(ayar, list) else [ayar]
        for i, a in enumerate(ayarlar, 1):
            kimlik = f"{r['kaynak_id']}#a{i}" if isinstance(ayar, list) else r["kaynak_id"]
            out.append(_bos_satir(
                kimlik=kimlik, katman="G8", kaynak_id=r["kaynak_id"], sinif=r["sinif"], parametreler=_json(a), tf=r["tf"],
                yon=r["yon"], evren=r["evren"] or "kripto13", emin_degil="1" if r["emin_degil"] else "",
                notlar="kaynak=g8_mevcut_sinif.csv"))
    return out


def k_satirlari(yol: Path, katman: str) -> list:
    out = []
    for r in _csv_oku(yol):
        if r["karar"] != "KOSULACAK":
            continue
        kid = r["kaynak_id"]
        ayar = json.loads(r["ayar"]) if r["ayar"].strip() else {}
        sinif, modul, par, durum, not_ = r["sinif"], "", ayar, "KOSULACAK", []
        if kid.startswith("AYAR:"):
            # AYAR:<hedef>:<ayar_id...> ; kaynak biçimi ek JSON'dan değil K1 nihai tablosundan okunur
            hedef = kid.split(":", 2)[1]
            sinif = hedef
        elif kid.startswith("KOD:"):
            ad = kid[4:]
            if sinif == "YENI":
                sinif = ad
        elif sinif == "YENI":
            sinif = K2_YENI_SINIF.get(kid, "YENI")
        out.append(_bos_satir(
            kimlik=kid, katman=katman, kaynak_id=kid, sinif=sinif, modul=modul, parametreler=_json(par), tf=r["tf"],
            yon=r["yon"], evren=r["evren"] or "kripto13", emin_degil="1" if r["emin_degil"] else "", durum=durum,
            notlar=" | ".join(not_ + [f"kaynak={yol.name}"])))
    return out


# ---------------------------------------------------------------- çözümleme (KOSULACAK / COZULEMEDI)
def _pf_varsayilan_mi(satir: dict) -> bool:
    return satir["kaynak_id"].startswith("KOD:") and satir["sinif"].startswith("pf__")


def coz_ve_isaretle(satir: dict) -> dict:
    """Satırın sınıfını/parametresini çözer; olmazsa durum=COZULEMEDI + neden. Sessiz düzeltme yok (yalnız aşağıdaki açık kurallar)."""
    par = json.loads(satir["parametreler"])
    nedenler = []
    try:
        cls, pf = sinif_coz(satir["sinif"], satir["modul"])
    except (KeyError, ImportError, AttributeError) as e:
        satir.update(durum="COZULEMEDI", notlar=(satir["notlar"] + f" | COZULEMEDI sınıf: {type(e).__name__}: {e}").strip(" |"))
        return satir
    if satir["kaynak_id"].startswith("AYAR:") and not (set(par) <= set(cls.varsayilan_parametreler)):
        fazla = sorted(set(par) - set(cls.varsayilan_parametreler))
        satir.update(durum="COZULEMEDI", notlar=(satir["notlar"] + " | COZULEMEDI: K1 kaynak biçimi mevcut sınıf parametreleriyle "
                     f"eşlenemedi (sınıfta olmayan anahtarlar: {fazla}); ek JSON ayarı kaynak biçimi değil, lider kararı gerekir").strip(" |"))
        return satir
    if _pf_varsayilan_mi(satir) and not (set(par) <= set(cls.varsayilan_parametreler)):
        # K1 nihai: mevcut pf sınıfı olduğu gibi; tablo ayarı kaynak kuralını betimler, kurucu parametresi değildir
        satir["parametreler"] = "{}"
        satir["yaklasik"] = "1"
        nedenler.append("ayar=sınıf varsayılanı (K1 tablosundaki anahtarlar sınıf parametresi değil; sınıf-kaynak farkı K1 notunda)")
        par = {}
    try:
        strateji_kur(satir["sinif"], satir["modul"], par)
    except (TypeError, ValueError, KeyError) as e:
        satir.update(durum="COZULEMEDI", notlar=(satir["notlar"] + f" | COZULEMEDI kurucu: {type(e).__name__}: {e}").strip(" |"))
        return satir
    if not cls.__module__.startswith("motor.") and not satir["modul"]:
        satir["modul"] = cls.__module__
    satir["durum"] = "KOSULACAK"
    if nedenler:
        satir["notlar"] = (satir["notlar"] + " | " + "; ".join(nedenler)).strip(" |")
    return satir


# ---------------------------------------------------------------- liste üretimi
# Lider kararı (sonuç görülmeden, 2026-11-13): kullanıcı "rotasyon/pairs evren dışı kalsın" dedi; K1'deki iki rotasyon
# ayarı da bu karara girer (üstelik kaynak biçimi mevcut sınıfla eşlenemiyor). Koşulmaz, aileye girmez.
_ROT = "kullanıcı kararı: rotasyon evren dışı (K1 ayarı mevcut sınıfla da eşlenemedi)"
LIDER_EVREN_DISI = {
    "AYAR:pf__rotasyon:d11j:rotasyon-skor-modlari-triplersi-bb:bb_uzaklik_k1": _ROT,
    "AYAR:pf__rotasyon:d11j:rotasyon-skor-modlari-triplersi-bb:triple_rsi_hacim_top5": _ROT,
}


def liste_uret(kapanis: Path = KAPANIS) -> tuple:
    """-> (liste satırları, elenenler, ozet sözlüğü). Deterministik (zaman damgası yok)."""
    eleme = {r["kimlik"]: r for r in _csv_oku(kapanis / "eleme" / "eleme.csv")}
    g8 = g8_varyant_satirlari() + g8_mevcut_satirlari(kapanis / "kod_girdi" / "g8_mevcut_sinif.csv")
    k = k_satirlari(kapanis / "ara" / "k1_nihai.csv", "K1") + k_satirlari(kapanis / "ara" / "k2_nihai.csv", "K2")
    g8_idler = [s["kimlik"] for s in g8]
    if len(set(g8_idler)) != len(g8_idler):
        raise ValueError("G8 kimlikleri tekil değil")
    eksik = [i for i in g8_idler if i not in eleme]
    fazla = [i for i in eleme if i not in set(g8_idler)]
    if eksik or fazla:
        raise ValueError(f"eleme.csv ile G8 kimlikleri uyuşmuyor: elemede yok={eksik[:5]}, G8'de yok={fazla[:5]}")
    k_idler = {s["kimlik"] for s in k}
    for g8_id, k_id in ESLEME.items():
        if g8_id not in set(g8_idler) or k_id not in k_idler:
            raise ValueError(f"eşleme tarafı bulunamadı: {g8_id} <-> {k_id}")
    twin_k = {v: kk for kk, v in ESLEME.items()}          # K kimliği -> G8 ikizi
    liste, elenen, birlesen = [], [], []
    for s in g8:
        if s["kimlik"] in ESLEME:
            birlesen.append((s["kimlik"], ESLEME[s["kimlik"]]))
            continue
        e = eleme[s["kimlik"]]
        if e["karar"] == "ÇIKAR":
            elenen.append({**s, "durum": "ELENDI_ON", "gerekce": e["gerekce"]})
        else:
            liste.append(coz_ve_isaretle(s))
    for s in k:
        ikiz = twin_k.get(s["kimlik"], "")
        s["eslesme"] = ikiz
        if s["kimlik"] in LIDER_EVREN_DISI:
            elenen.append({**s, "durum": "EVREN_DISI", "gerekce": LIDER_EVREN_DISI[s["kimlik"]]})
        elif ikiz and eleme[ikiz]["karar"] == "ÇIKAR":
            elenen.append({**s, "durum": "ELENDI_ON", "gerekce": eleme[ikiz]["gerekce"]})
        else:
            liste.append(coz_ve_isaretle(s))
    kimlikler = [s["kimlik"] for s in liste]
    if len(set(kimlikler)) != len(kimlikler):
        raise ValueError("liste kimlikleri tekil değil")
    guvenli = {re.sub(r"[^A-Za-z0-9._#=-]", "_", i) for i in kimlikler}
    if len(guvenli) != len(kimlikler):
        raise ValueError("kimlik_guvenli çakışması (kontrol noktası dosya adları)")
    sayac = {}
    for s in liste:
        sayac[s["katman"]] = sayac.get(s["katman"], 0) + 1
    ozet = {"satir": len(liste), "katman": sayac, "cozulemedi": sorted(s["kimlik"] for s in liste if s["durum"] == "COZULEMEDI"),
            "elenen": len(elenen), "birlestirilen": sorted(f"{a} -> {b}" for a, b in birlesen)}
    return liste, elenen, ozet


def _yaz(yol: Path, sutunlar: list, satirlar: list) -> bytes:
    import io
    tampon = io.StringIO(newline="")
    w = csv.DictWriter(tampon, fieldnames=sutunlar, lineterminator="\n")
    w.writeheader()
    for s in satirlar:
        w.writerow({k: s.get(k, "") for k in sutunlar})
    return tampon.getvalue().encode("utf-8")


def dondur(kapanis: Path = KAPANIS, yeniden: bool = False) -> dict:
    liste, elenen, ozet = liste_uret(kapanis)
    govde = _yaz(kapanis / "x", SUTUNLAR, liste)
    sha = hashlib.sha256(govde).hexdigest()
    liste_yolu = kapanis / "kosu_listesi_asama1.csv"
    sha_yolu = kapanis / "kosu_listesi_asama1.csv.sha256"
    if liste_yolu.exists() and not yeniden:
        eski = hashlib.sha256(liste_yolu.read_bytes()).hexdigest()
        if sha_yolu.exists() and sha_yolu.read_text().split()[0] != eski:
            raise RuntimeError("dondurulmuş liste .sha256 ile uyuşmuyor (dosya değiştirilmiş)")
        if eski != sha:
            raise RuntimeError(f"liste DONDURULMUŞ ve yeni üretim farklı (eski {eski[:12]}, yeni {sha[:12]}); "
                               "bilinçli değişiklik için --yeniden-dondur")
    liste_yolu.write_bytes(govde)
    sha_yolu.write_text(f"{sha}  {liste_yolu.name}\n")
    (kapanis / "kosu_listesi_asama1_elenen.csv").write_bytes(_yaz(kapanis / "y", ELENEN_SUTUNLAR, elenen))
    ozet["sha256"] = sha
    return ozet


def dogrula(kapanis: Path = KAPANIS) -> str:
    return dogrula_dosya(kapanis / "kosu_listesi_asama1.csv")


def dogrula_dosya(yol: Path) -> str:
    """Herhangi bir dondurulmuş koşu listesini (<liste>.csv + <liste>.csv.sha256) doğrular."""
    sha_yolu = yol.with_name(yol.name + ".sha256")
    if not yol.exists() or not sha_yolu.exists():
        raise FileNotFoundError("dondurulmuş liste ya da .sha256 yok")
    gercek = hashlib.sha256(yol.read_bytes()).hexdigest()
    if sha_yolu.read_text().split()[0] != gercek:
        raise RuntimeError("koşu listesi .sha256 ile uyuşmuyor: liste dondurulduktan sonra değiştirilmiş")
    return gercek


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Kapanış aşama 1 koşu listesini üret ve dondur")
    ap.add_argument("--yeniden-dondur", action="store_true", help="mevcut donmuş listenin üzerine bilinçli yaz")
    ap.add_argument("--dogrula", action="store_true", help="yalnız mevcut listenin SHA-256'sını doğrula")
    a = ap.parse_args(argv)
    if a.dogrula:
        print("tamam", dogrula())
        return 0
    o = dondur(yeniden=a.yeniden_dondur)
    print(f"satır (BH ailesi): {o['satir']}  katman: {o['katman']}  elenen(ön): {o['elenen']}")
    print(f"birleştirilen: {len(o['birlestirilen'])}  çözülemeyen: {len(o['cozulemedi'])}  sha256: {o['sha256']}")
    for i in o["cozulemedi"]:
        print("  COZULEMEDI", i)
    return 0


if __name__ == "__main__":
    sys.exit(main())
