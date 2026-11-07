"""Durum sözleşmesinin kodu: şema sabitleri, ATOMİK yazıcılar, okuyucular ve doğrulayıcılar. Şema belgesi: DURUM_SOZLESMESI.md.

İLKE: bütün sayıları MOTOR hesaplar ve yazar; pano yalnız okuyup biçimler (motor ile pano asla farklı sayı göstermez).
Para tutarları metin olarak ("10720.00", Decimal ile 2 hane) saklanır; oranlar JSON sayısıdır (0.072 = %7.2).
Okuma hatası (dosya yok / bozuk JSON / şema uyumsuz) `DurumHatasi` ile YÜKSELİR; uydurma değer döndürülmez.
"""
from __future__ import annotations

import json
import os
from datetime import timedelta, datetime, timezone
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from typing import Iterable, Optional

SURUM = 1
DURUM_DIZINI = Path(__file__).resolve().parents[2] / "durum"       # .gitignore'da
DOSYALAR = {"ozet": "ozet.json", "stratejiler": "stratejiler.json", "islemler": "islemler.jsonl",
            "saglik": "saglik.json", "gecmis": "ozsermaye_gecmisi.json"}
# Genişletme (sürüm 1, eklemeli; pano bunlar yoksa eski görünümle çalışır): motor yazar, pano yalnız okur.
EK_DOSYALAR = {"maruziyet": "maruziyet.json", "maliyet": "maliyet.json", "reddedilen": "reddedilen.json",
               "olaylar": "olaylar.jsonl", "icgoruler": "icgoruler.json"}
KAYNAKLAR = ("backtest", "paper", "canli")
BANTLAR = ("p05_alti", "p05_p25", "p25_p50", "p50_p75", "p75_p95", "p95_ustu")


class DurumHatasi(Exception):
    """Durum dosyası yok / okunamıyor / şemaya uymuyor."""


# ----------------------------------------------------------------------------------------------- biçim yardımcıları
def para(x) -> str:
    """Para tutarı -> 2 haneli metin (Decimal, yarım-çifte yuvarlama). float repr üzerinden çevrilir (ikili kayma yok)."""
    if hasattr(x, "item"):               # numpy sayısı -> Python sayısı (repr 'np.float64(..)' vermesin)
        x = x.item()
    d = x if isinstance(x, Decimal) else Decimal(repr(x) if isinstance(x, float) else str(x))
    return str(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))


def zaman_str(t) -> str:
    """datetime/pandas.Timestamp -> 'YYYY-MM-DDTHH:MM:SSZ' (UTC)."""
    if isinstance(t, str):
        return t
    if getattr(t, "tzinfo", None) is None:
        raise ValueError("zaman saat dilimli (UTC) olmalı")
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def zaman_oku(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def sayi(x) -> Optional[float]:
    """float (NaN/inf -> None; JSON'da geçersizdir)."""
    if x is None:
        return None
    f = float(x)
    return f if f == f and f not in (float("inf"), float("-inf")) else None


def bant_bul(deger: float, p05: float, p25: float, p50: float, p75: float, p95: float) -> str:
    """Değerin beklenti aralığındaki yeri (yüzdelik bandı). Motor tarafında hesaplanır, durum dosyasına yazılır."""
    if deger < p05:
        return "p05_alti"
    if deger < p25:
        return "p05_p25"
    if deger < p50:
        return "p25_p50"
    if deger < p75:
        return "p50_p75"
    if deger <= p95:
        return "p75_p95"
    return "p95_ustu"


def konum(metrik: str, deger: float, q: dict, hafta: int) -> dict:
    """q: {p05,p25,p50,p75,p95,alarm_yonu,alarm_esigi}. alarm: net için deger < alarm_esigi, düşüş için deger > alarm_esigi."""
    alarm = None
    if hafta == 8 and q.get("alarm_yonu") in ("alt", "ust") and q.get("alarm_esigi") is not None:
        alarm = bool(deger < q["alarm_esigi"]) if q["alarm_yonu"] == "alt" else bool(deger > q["alarm_esigi"])
    return {"deger": sayi(deger), "p05": q["p05"], "p25": q["p25"], "p50": q["p50"], "p75": q["p75"], "p95": q["p95"],
            "bant": bant_bul(deger, q["p05"], q["p25"], q["p50"], q["p75"], q["p95"]), "alarm": alarm}


# ----------------------------------------------------------------------------------------------- atomik yazma
def _gecici(yol: Path) -> Path:
    return yol.with_name(f".{yol.name}.tmp-{os.getpid()}")


def atomik_yaz_metin(yol, metin: str) -> Path:
    """Geçici dosya (aynı dizin) + fsync + os.replace: okuyucu ya eski ya yeni TAM dosyayı görür. Hata olursa geçici silinir."""
    yol = Path(yol)
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = _gecici(yol)
    try:
        with open(gecici, "w", encoding="utf-8", newline="\n") as f:
            f.write(metin)
            f.flush()
            os.fsync(f.fileno())
        os.replace(gecici, yol)
    except BaseException:
        gecici.unlink(missing_ok=True)
        raise
    return yol


def atomik_yaz_json(yol, veri: dict) -> Path:
    return atomik_yaz_metin(yol, json.dumps(veri, ensure_ascii=False, indent=1, allow_nan=False) + "\n")


def atomik_yaz_jsonl(yol, satirlar: Iterable[dict]) -> Path:
    return atomik_yaz_metin(yol, "".join(json.dumps(s, ensure_ascii=False, allow_nan=False) + "\n" for s in satirlar))


# ----------------------------------------------------------------------------------------------- şema doğrulama
def _iste(d, anahtarlar, ad):
    if not isinstance(d, dict):
        raise DurumHatasi(f"{ad}: nesne bekleniyordu")
    eksik = [a for a in anahtarlar if a not in d]
    if eksik:
        raise DurumHatasi(f"{ad}: eksik alan(lar): {', '.join(eksik)}")


def _zaman_dogrula(s, ad):
    try:
        zaman_oku(s)
    except (TypeError, ValueError) as e:
        raise DurumHatasi(f"{ad}: geçersiz zaman '{s}' (YYYY-MM-DDTHH:MM:SSZ bekleniyordu)") from e


def _para_dogrula(s, ad):
    try:
        if not isinstance(s, str):
            raise ValueError
        Decimal(s)
    except Exception as e:  # noqa: BLE001
        raise DurumHatasi(f"{ad}: para alanı metin (Decimal) olmalı: {s!r}") from e


def _ortak(d, ad, sema):
    _iste(d, ("sema", "surum", "zaman", "kaynak"), ad)
    if d["sema"] != sema:
        raise DurumHatasi(f"{ad}: şema '{d['sema']}' != '{sema}'")
    if d["surum"] != SURUM:
        raise DurumHatasi(f"{ad}: sürüm {d['surum']} desteklenmiyor (bekleniyor {SURUM})")
    if d["kaynak"] not in KAYNAKLAR:
        raise DurumHatasi(f"{ad}: kaynak {d['kaynak']!r} geçersiz")
    _zaman_dogrula(d["zaman"], ad)
    if "yazildi_zaman" in d:
        _zaman_dogrula(d["yazildi_zaman"], f"{ad}.yazildi_zaman")


OZET_RISK = ("gunluk_kayip", "kaldirac", "kill_switch", "acik_stop_riski")


def dogrula_ozet(d: dict) -> dict:
    _ortak(d, "ozet.json", "1l3a.durum.ozet")
    _iste(d, ("baslangic_ozsermaye", "ozsermaye", "toplam_pnl", "toplam_getiri", "gun_pnl", "gun_getiri", "zirve_ozsermaye",
              "zirveden_dusus", "max_dusus", "risk", "sayaclar", "donem", "yazim_zamani"), "ozet.json")
    for a in ("baslangic_ozsermaye", "ozsermaye", "toplam_pnl", "gun_pnl", "zirve_ozsermaye"):
        _para_dogrula(d[a], f"ozet.{a}")
    _iste(d["risk"], OZET_RISK, "ozet.risk")
    for a in ("gunluk_kayip", "kaldirac", "acik_stop_riski"):
        _iste(d["risk"][a], ("deger", "limit", "kullanim"), f"ozet.risk.{a}")
    _iste(d["risk"]["kill_switch"], ("dusus", "limit", "mesafe", "tetiklendi"), "ozet.risk.kill_switch")
    return d


def dogrula_stratejiler(d: dict) -> dict:
    _ortak(d, "stratejiler.json", "1l3a.durum.stratejiler")
    _iste(d, ("stratejiler", "beklenti_penceresi_hafta", "set"), "stratejiler.json")
    for i, s in enumerate(d["stratejiler"]):
        _iste(s, ("kimlik", "ajan", "kol", "ozsermaye_katkisi", "katki_getiri", "acik_pozisyonlar", "son_islem",
                  "islem_sayisi", "kazanma_orani", "beklenti"), f"stratejiler[{i}]")
        _para_dogrula(s["ozsermaye_katkisi"], f"stratejiler[{i}].ozsermaye_katkisi")
        if not isinstance(s["acik_pozisyonlar"], list):
            raise DurumHatasi(f"stratejiler[{i}].acik_pozisyonlar liste olmalı")
        for hf, b in s["beklenti"].items():
            _iste(b, ("net_getiri", "max_dusus"), f"stratejiler[{i}].beklenti[{hf}]")
            for m in ("net_getiri", "max_dusus"):
                _iste(b[m], ("deger", "p05", "p25", "p50", "p75", "p95", "bant", "alarm"), f"stratejiler[{i}].beklenti[{hf}].{m}")
                if b[m]["bant"] not in BANTLAR:
                    raise DurumHatasi(f"stratejiler[{i}].beklenti[{hf}].{m}: bant {b[m]['bant']!r} geçersiz")
    _iste(d["set"], ("beklenti",), "stratejiler.set")
    return d


ISLEM_ALANLARI = ("zaman", "kimlik", "sembol", "yon", "giris_zamani", "giris_fiyati", "cikis_zamani", "cikis_fiyati", "miktar",
                  "r", "net_pnl_yerel", "set_katki_usd", "cikis_nedeni")


def dogrula_islem(s: dict, ad="islemler.jsonl") -> dict:
    _iste(s, ISLEM_ALANLARI, ad)
    _zaman_dogrula(s["zaman"], ad)
    if s["yon"] not in ("long", "short"):
        raise DurumHatasi(f"{ad}: yon 'long'/'short' olmalı")
    return s


def dogrula_saglik(d: dict) -> dict:
    _ortak(d, "saglik.json", "1l3a.durum.saglik")
    _iste(d, ("son_calisma", "durum", "bayat_denetimi", "dosya_esik_dk", "veri", "servis", "uyarilar"), "saglik.json")
    _zaman_dogrula(d["son_calisma"], "saglik.son_calisma")
    for i, v in enumerate(d["veri"]):
        _iste(v, ("sembol", "tf", "son_mum_zamani", "bayatlik_dk", "esik_dk", "bayat"), f"saglik.veri[{i}]")
    return d


def dogrula_gecmis(d: dict) -> dict:
    _ortak(d, "ozsermaye_gecmisi.json", "1l3a.durum.gecmis")
    _iste(d, ("noktalar",), "ozsermaye_gecmisi.json")
    for i, n in enumerate(d["noktalar"]):
        _iste(n, ("gun", "ozsermaye"), f"gecmis.noktalar[{i}]")
        _para_dogrula(n["ozsermaye"], f"gecmis.noktalar[{i}].ozsermaye")
    return d


# ----------------------------------------------------------------------------------------------- yazıcılar (motor çağırır)
def _zarf(sema: str, kaynak: str, zaman: str) -> dict:
    return {"sema": f"1l3a.durum.{sema}", "surum": SURUM, "zaman": zaman, "kaynak": kaynak}


def ozet_olustur(*, kaynak: str, zaman: str, yazim_zamani: str, donem: Optional[dict], baslangic_ozsermaye, ozsermaye, gun_pnl,
                 gun_getiri: float, zirve_ozsermaye, max_dusus: float, risk: dict, sayaclar: dict, notlar: Optional[list] = None,
                 ekstra: Optional[dict] = None) -> dict:
    """Bütün değerler MOTOR tarafından hesaplanmış olarak verilir; bu fonksiyon yalnız biçimler/şemaya koyar (zirveden düşüş ve
    toplam PnL de motorun verdiği özsermayelerden Decimal ile türetilir: bunlar tanım gereği fark/oran)."""
    bas, oz, zirve = Decimal(para(baslangic_ozsermaye)), Decimal(para(ozsermaye)), Decimal(para(zirve_ozsermaye))
    d = _zarf("ozet", kaynak, zaman)
    d.update({"yazim_zamani": yazim_zamani, "donem": donem, "baslangic_ozsermaye": para(bas), "ozsermaye": para(oz),
              "toplam_pnl": para(oz - bas), "toplam_getiri": sayi((oz - bas) / bas), "gun_pnl": para(gun_pnl),
              "gun_getiri": sayi(gun_getiri), "zirve_ozsermaye": para(zirve),
              "zirveden_dusus": sayi((zirve - oz) / zirve) if zirve > 0 else 0.0, "max_dusus": sayi(max_dusus),
              "risk": risk, "sayaclar": sayaclar, "notlar": notlar or []})
    d["baslangictan_pnl"] = d["toplam_pnl"]                       # pano etiketi: başlangıçtan beri K/Z (toplam_pnl ile aynı sayı)
    d.update(ekstra or {})
    return dogrula_ozet(d)


def risk_blogu(*, gunluk_kayip: Optional[float], gunluk_limit: float, kaldirac: Optional[float], kaldirac_limit: float,
               zirveden_dusus: float, kill_limit: float, acik_stop_riski: Optional[float], stop_risk_limit: float,
               kaldirac_not: str = "", gunluk_limit_tetiklendi: bool = False) -> dict:
    """Limit kullanımı = değer / limit (motor yazar). Ölçülmeyen değer None (pano '—' gösterir, uydurma yok)."""
    def kul(v, lim):
        return None if v is None else sayi(v / lim)
    return {
        "gunluk_kayip": {"deger": sayi(gunluk_kayip), "limit": gunluk_limit, "kullanim": kul(gunluk_kayip, gunluk_limit),
                         "tetiklendi": bool(gunluk_limit_tetiklendi)},
        "kaldirac": {"deger": sayi(kaldirac), "limit": kaldirac_limit, "kullanim": kul(kaldirac, kaldirac_limit), "not": kaldirac_not},
        "kill_switch": {"dusus": sayi(zirveden_dusus), "limit": kill_limit, "mesafe": sayi(kill_limit - zirveden_dusus),
                        "tetiklendi": bool(zirveden_dusus >= kill_limit)},
        "acik_stop_riski": {"deger": sayi(acik_stop_riski), "limit": stop_risk_limit, "kullanim": kul(acik_stop_riski, stop_risk_limit)},
    }


def yaz_hepsi(dizin, *, ozet: dict, stratejiler: dict, islemler: list, saglik: dict, gecmis: dict,
              ekstra: Optional[dict] = None, yazildi: Optional[datetime] = None) -> Path:
    """Dosyaları doğrulayıp ATOMİK yazar (her dosya kendi içinde atomiktir; yazım sırası: ek dosyalar, islemler, gecmis,
    stratejiler, saglik, ozet -> ozet.json en son: ozet'i gören okuyucu diğerlerinin aynı turdan olduğunu varsayabilir).
    `ekstra`: {'maruziyet'|'maliyet'|'reddedilen'|'icgoruler': dict, 'olaylar': [satır dict]} (EK_DOSYALAR).
    Her JSON dosyasına `yazildi_zaman` (UTC ISO, dosyanın diske yazıldığı an; hepsinde aynı) eklenir: pano tarayıcıda
    'şimdi - yazildi_zaman' ile dosya bayatlığını gösterir."""
    dizin = Path(dizin)
    ekstra = dict(ekstra or {})
    yz = zaman_str(yazildi or datetime.now(timezone.utc))
    dogrula_stratejiler(stratejiler), dogrula_saglik(saglik), dogrula_gecmis(gecmis), dogrula_ozet(ozet)
    for s in islemler:
        dogrula_islem(s)
    bilinmeyen = set(ekstra) - set(EK_DOSYALAR)
    if bilinmeyen:
        raise DurumHatasi(f"bilinmeyen ek dosya(lar): {sorted(bilinmeyen)}")
    for ad, v in ekstra.items():
        if ad == "olaylar":
            for no, o in enumerate(v):
                _iste(o, ("zaman", "tur", "mesaj"), f"olaylar[{no}]")
                _zaman_dogrula(o["zaman"], f"olaylar[{no}]")
        else:
            _ortak(v, EK_DOSYALAR[ad], f"1l3a.durum.{ad}")
    for ad, v in ekstra.items():
        if ad == "olaylar":
            atomik_yaz_jsonl(dizin / EK_DOSYALAR[ad], v)
        else:
            v["yazildi_zaman"] = yz
            atomik_yaz_json(dizin / EK_DOSYALAR[ad], v)
    atomik_yaz_jsonl(dizin / DOSYALAR["islemler"], islemler)
    for k, v in (("gecmis", gecmis), ("stratejiler", stratejiler), ("saglik", saglik), ("ozet", ozet)):
        v["yazildi_zaman"] = yz
        atomik_yaz_json(dizin / DOSYALAR[k], v)
    return dizin


def ek_oku(dizin, ad: str):
    """Ek dosya (EK_DOSYALAR). Yoksa None (eski motor); bozuksa DurumHatasi. 'olaylar' -> liste."""
    yol = Path(dizin) / EK_DOSYALAR[ad]
    if not yol.exists():
        return None
    if ad == "olaylar":
        out = []
        for no, satir in enumerate(yol.read_text(encoding="utf-8").splitlines(), 1):
            if satir.strip():
                try:
                    out.append(json.loads(satir))
                except json.JSONDecodeError as e:
                    raise DurumHatasi(f"{yol.name}:{no}: bozuk JSON satırı ({e})") from e
        return out
    d = _json_oku(yol)
    _ortak(d, yol.name, f"1l3a.durum.{ad}")
    return d


def islem_ekle(dizin, islem: dict) -> None:
    """Canlı/paper için tek satır ekleme (O_APPEND + fsync). Satır tam yazılmadan çökerse son satır bozuk kalabilir; okuyucu bunu
    HATA olarak bildirir (sessiz atlamaz)."""
    dogrula_islem(islem)
    yol = Path(dizin) / DOSYALAR["islemler"]
    yol.parent.mkdir(parents=True, exist_ok=True)
    with open(yol, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(islem, ensure_ascii=False, allow_nan=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


# ----------------------------------------------------------------------------------------------- okuyucular (pano çağırır)
def _json_oku(yol: Path) -> dict:
    if not yol.exists():
        raise DurumHatasi(f"{yol.name}: dosya yok")
    try:
        return json.loads(yol.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise DurumHatasi(f"{yol.name}: bozuk JSON ({e})") from e


def oku_ozet(dizin) -> dict:
    return dogrula_ozet(_json_oku(Path(dizin) / DOSYALAR["ozet"]))


def oku_stratejiler(dizin) -> dict:
    return dogrula_stratejiler(_json_oku(Path(dizin) / DOSYALAR["stratejiler"]))


def oku_saglik(dizin) -> dict:
    return dogrula_saglik(_json_oku(Path(dizin) / DOSYALAR["saglik"]))


def oku_gecmis(dizin) -> dict:
    return dogrula_gecmis(_json_oku(Path(dizin) / DOSYALAR["gecmis"]))


def oku_islemler(dizin) -> list:
    yol = Path(dizin) / DOSYALAR["islemler"]
    if not yol.exists():
        raise DurumHatasi(f"{yol.name}: dosya yok")
    out = []
    for no, satir in enumerate(yol.read_text(encoding="utf-8").splitlines(), 1):
        if not satir.strip():
            continue
        try:
            out.append(dogrula_islem(json.loads(satir), f"{yol.name}:{no}"))
        except json.JSONDecodeError as e:
            raise DurumHatasi(f"{yol.name}:{no}: bozuk JSON satırı ({e})") from e
    return out


def oku_hepsi(dizin) -> tuple:
    """-> (veri {'ozet','stratejiler','islemler','saglik','gecmis': dict|list|None}, sorunlar [metin]).
    Her dosya bağımsız okunur; sorunlu olanın değeri None'dır ve sorun listesine açık metin eklenir."""
    veri, sorunlar = {}, []
    for ad, fn in (("ozet", oku_ozet), ("stratejiler", oku_stratejiler), ("islemler", oku_islemler), ("saglik", oku_saglik),
                   ("gecmis", oku_gecmis)):
        try:
            veri[ad] = fn(dizin)
        except DurumHatasi as e:
            veri[ad] = None
            sorunlar.append(str(e))
    return veri, sorunlar


# ----------------------------------------------------------------------------------------------- beklenti aralıkları (CSV)
def beklenti_oku(yol) -> dict:
    """sonuclar/final/beklenti_araliklari.csv -> {kimlik: {(hafta, metrik): {p05..p95, alarm_yonu, alarm_esigi}}}. Yoksa DurumHatasi."""
    import csv
    yol = Path(yol)
    if not yol.exists():
        raise DurumHatasi(f"{yol.name}: beklenti aralıkları dosyası yok (python -m motor.arastirma.beklenti)")
    out: dict = {}
    with open(yol, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            es = r["alarm_esigi"]
            out.setdefault(r["kimlik"], {})[(int(r["pencere_hafta"]), r["metrik"])] = {
                **{k: float(r[k]) for k in ("p05", "p25", "p50", "p75", "p95")}, "alarm_yonu": r["alarm_yonu"],
                "alarm_esigi": float(es) if es not in ("", None) else None}
    return out


def bayat_esigi_dk(tf: str) -> int:
    """Veri bayatlık eşiği (dakika) = 2 x mum süresi + 10 (tf: 'm','h','d' son ekli)."""
    birim = {"m": 1, "h": 60, "d": 1440}[tf[-1]]
    return 2 * int(tf[:-1]) * birim + 10


def veri_yasi_dk(son_mum_acilis, tf: str, simdi) -> int:
    """Veri yaşı (dk) = simdi - son mumun KAPANIŞI (açılış + mum süresi). Mum henüz kapanmamışsa (negatif) 0.
    Paper motoru yazar; pano hesap yapmaz."""
    birim = {"m": 1, "h": 60, "d": 1440}[tf[-1]]
    kapanis = zaman_oku(zaman_str(son_mum_acilis)) + timedelta(minutes=int(tf[:-1]) * birim)
    return max(0, int((simdi - kapanis).total_seconds() // 60))
