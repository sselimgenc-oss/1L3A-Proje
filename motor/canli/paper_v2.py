"""Paper v2 seti (20 strateji: 10 + 6 kapanış adayı + 4 kapanış ek adayı, HER BİRİ KENDİ SANAL KASASINDA) — gerçek emir YOK, API anahtarı YOK.

Karar (kullanıcı onayı 2026-11-10, DURUM.md): paper seti = stratejiler/paper_v2_seti.json. Her strateji kendi 10.000 USD'lik
kasasında koşar (v2 holdout "tek başına tek kasa" ölçümüyle aynı), böylece şanslı olanlar tek tek elenebilir. Etiketler:
"dogrulandi" (resmi holdout kapısını geçti) ve "iyi_gorundu" (sonuç sonrası keşif — KANIT DEĞİL).

TASARIM (en az müdahale): mevcut `Paper` (tek hesap + tek PaperMotor; yalnız küçük eklemeler: tek_evren kararı, yüklemenin sözlükten yapılabilmesi) hesap başına
bir kez örneklenir (`HesapPaper`);
hepsi aynı veri kaynağını (CanliKaynak / TekrarKaynagi) paylaşır. `PaperKasalar` bunları sarar ve `Paper` ile aynı arayüzü sunar
(servis döngüsü, durum yazıcısı, Telegram aynen çalışır). Sert limitler (işlem başı %1 maliyet dahil, toplam stop riski %5, brüt 3x,
günlük -%3, kill -%20) HER HESABIN KENDİ PaperMotor'unda uygulanır; burada gevşetilen/aşılan bir şey yoktur. Üst düzey `durum/`
dosyaları 20 hesabın TOPLAMIDIR (pano için; toplamda sert limit uygulanmaz, hesapların toplamı gösterilir); her hesabın tam dosya seti
`durum/hesaplar/<kimlik>/` altındadır.

Risk ölçeği: işlem başı risk = s x %1 (s = 0.5 -> %0.5, maliyet dahil), holdout `strateji_olc` ile aynı. Portföy stratejisinde (pf__sabit_sepet)
holdout neti günlük getirinin s ile ölçeklenmesidir (pf_net = prod(1 + s x r) - 1): burada aynı ölçek grup payı (ağırlık ölçeği) olarak uygulanır.
Maliyet: sembol bazlı v2 maliyet tablosu (sonuclar/evren/v2/maliyet_tablosu_v2.csv), holdout'taki gibi.

Tekrar modu (`--tekrar`): geçmişi canlıymış gibi besler, canlı yolla AYNI kod. `--uyum`: 10 stratejiyi holdout dönemi üzerinde koşturup
holdout_kesif.csv / holdout.csv netleriyle karşılaştırır (kabul testi).
"""
from __future__ import annotations

import concurrent.futures as cf
import dataclasses
import hashlib
import json
import logging
import pickle
from decimal import Decimal
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from motor.backtest.motor import D
from motor.canli import paper as pp
from motor.canli import paper_sinyal as psg
from motor.canli.paper import Paper
from motor.canli.paper_kaynak import TekrarKaynagi
from motor.canli.paper_motor import PaperDesteklemiyorHatasi, PaperMotor, _enc, desteklenmeyen_cikis_alanlari
from motor.portfoy.motor import PortfoyAyarlari

log = logging.getLogger("paper.v2")
KOK = Path(__file__).resolve().parents[2]
SET_YOLU = KOK / "stratejiler" / "paper_v2_seti.json"
HAVUZ_CSV = KOK / "stratejiler" / "havuz_v2.csv"
TABLO_YOLU = KOK / "sonuclar" / "evren" / "v2" / "maliyet_tablosu_v2.csv"
SET_ADI = "paper_v2"
STATE_SURUM = 2
ETIKETLER = ("dogrulandi", "iyi_gorundu", "kapanis_aday", "kapanis_aday_ek")
KAPANIS_ETIKET = "kapanis_aday"                              # kapanış turu paper adayı — ileri dönem sınavı gerekli, yeterli değil
KAPANIS_EK_ETIKET = "kapanis_aday_ek"                        # ileri dönem sınavından SONRA seçildi (sonuç sonrası seçim); canlı adayı olamaz
KAPANIS_ETIKETLERI = (KAPANIS_ETIKET, KAPANIS_EK_ETIKET)
KAPANIS_DIZIN = KOK / "sonuclar" / "kapanis"
KAPANIS_LISTELER = ("kosu_listesi_asama1.csv", "kosu_listesi_asama2.csv")     # dondurulmuş koşu listeleri (+ .sha256)
HOLDOUT_BAS = pd.Timestamp("2025-11-08", tz="UTC")           # sabit.HOLDOUT_BAS ile aynı (tests/uyum testi kontrol eder)
UYUM_BIT = pd.Timestamp("2026-11-07", tz="UTC")              # holdout veri_sonu (2026-11-06 1g mumunun kapanışı)
UYUM_GEREKCE = "paper v2 tekrar uyum testi (kullanıcı onayı 2026-11-10)"
HESAP_DIZINI = "hesaplar"
HESAP_YAZIM_SN = 600                                         # hesap dosyaları: yeni satır işlendiyse en çok bu sıklıkta (toplam her turda)


class PaperV2Hatasi(RuntimeError):
    """v2 paper seti tanımı/durumu tutarsız (fail-closed: motor başlamaz)."""


# =============================================================================================== set tanımı
def kapanis_mi(k: dict) -> bool:
    """Set kaydı kapanış turu kaydı mı? ({"kaynak": "kapanis", "kimlik": ..., "liste": ...}; diğerleri {"strateji": ...} havuz kaydı)"""
    return k.get("kaynak") == "kapanis"


def hesap_adi(k: dict) -> str:
    """Set kaydının hesap/strateji kimliği (kapanış: HAM:... kimliği; diğerleri: havuz adı)."""
    return k["kimlik"] if kapanis_mi(k) else k["strateji"]


def hesap_dizin_adi(kimlik: str) -> str:
    """durum/hesaplar/<ad> klasör adı: dosya sisteminde güvenli (HAM:X005:664#v1 -> HAM_X005_664_v1). Havuz adları (dis__x, pf__x) aynen kalır."""
    return "".join(c if (c.isalnum() or c in "._-") else "_" for c in kimlik)


def kapanis_satiri(k: dict, kapanis_dizin: Path = KAPANIS_DIZIN) -> dict:
    """Kapanış kaydının dondurulmuş koşu listesindeki satırı. Doğrular: liste izinli ve SHA-256 tutuyor, kimlik listede, durum KOSULACAK,
    tf/evren set kaydıyla aynı, sınıf çözülüyor ve tek-grafik (portföy değil). Her sorun PaperV2Hatasi (sessiz düzeltme yok)."""
    import csv
    from araclar import kapanis_kosu_listesi as kl
    kimlik = k.get("kimlik")
    if not kimlik or k.get("liste") not in KAPANIS_LISTELER:
        raise PaperV2Hatasi(f"kapanış kaydı: 'kimlik' ve 'liste' ({KAPANIS_LISTELER}) zorunlu: {k}")
    yol = Path(kapanis_dizin) / k["liste"]
    try:
        kl.dogrula_dosya(yol)
    except (FileNotFoundError, RuntimeError) as e:
        raise PaperV2Hatasi(f"{kimlik}: dondurulmuş liste doğrulanamadı ({yol.name}): {e}") from e
    with open(yol, newline="", encoding="utf-8") as f:
        satir = next((r for r in csv.DictReader(f) if r["kimlik"] == kimlik), None)
    if satir is None:
        raise PaperV2Hatasi(f"{kimlik}: {yol.name} içinde yok")
    if satir["durum"] != "KOSULACAK":
        raise PaperV2Hatasi(f"{kimlik}: liste durumu {satir['durum']} (KOSULACAK değil)")
    if (satir["tf"], satir["evren"]) != (k["tf"], k["evren"]):
        raise PaperV2Hatasi(f"{kimlik}: set ({k['tf']}, {k['evren']}) listeyle ({satir['tf']}, {satir['evren']}) uyuşmuyor")
    if k["tur"] != "tek":
        raise PaperV2Hatasi(f"{kimlik}: kapanış kaydı tur='tek' olmalı")
    try:
        _, pf = kl.sinif_coz(satir["sinif"], satir["modul"])
    except (KeyError, ImportError, AttributeError) as e:
        raise PaperV2Hatasi(f"{kimlik}: sınıf çözülemedi ({satir['sinif']}): {type(e).__name__}: {e}") from e
    if pf:
        raise PaperV2Hatasi(f"{kimlik}: portföy sınıfı paper v2 kapanış kaydı olamaz")
    return satir


def set_yukle(yol: Path = SET_YOLU, havuz_yolu: Path = HAVUZ_CSV, kapanis_dizin: Path = KAPANIS_DIZIN) -> dict:
    """paper_v2_seti.json + havuz_v2.csv (+ kapanış kayıtları için dondurulmuş koşu listeleri) tutarlılığı. Tutarsızlık = PaperV2Hatasi
    (sessiz düzeltme yok)."""
    s = json.loads(Path(yol).read_text(encoding="utf-8"))
    if s.get("surum") != 1 or s.get("ad") != SET_ADI:
        raise PaperV2Hatasi(f"{yol}: tanınmayan sürüm/ad")
    if not (0 < float(s["s"]) <= 1):
        raise PaperV2Hatasi(f"s (risk ölçeği) (0, 1] olmalı: {s['s']}")
    if not float(s["baslangic_sermaye"]) > 0:
        raise PaperV2Hatasi("baslangic_sermaye > 0 olmalı")
    ad_listesi = [hesap_adi(k) for k in s["stratejiler"]]
    if len(set(ad_listesi)) != len(ad_listesi):
        raise PaperV2Hatasi("sette tekrarlı strateji")
    havuz = pd.read_csv(havuz_yolu).set_index("strateji")
    for k in s["stratejiler"]:
        if k["etiket"] not in ETIKETLER:
            raise PaperV2Hatasi(f"{hesap_adi(k)}: etiket {k['etiket']!r} geçersiz ({ETIKETLER})")
        if kapanis_mi(k):
            if k["etiket"] not in KAPANIS_ETIKETLERI:
                raise PaperV2Hatasi(f"{hesap_adi(k)}: kapanış kaydının etiketi {KAPANIS_ETIKET!r} ya da {KAPANIS_EK_ETIKET!r} olmalı")
            kapanis_satiri(k, kapanis_dizin)
            continue
        if k["etiket"] in KAPANIS_ETIKETLERI:
            raise PaperV2Hatasi(f"{hesap_adi(k)}: {k['etiket']!r} etiketi yalnız kapanış kaydına verilir")
        if k["tur"] not in ("tek", "pf"):
            raise PaperV2Hatasi(f"{k['strateji']}: tur 'tek' | 'pf' olmalı")
        if k["strateji"] not in havuz.index:
            raise PaperV2Hatasi(f"{k['strateji']}: havuz_v2.csv'de yok")
        h = havuz.loc[k["strateji"]]
        if (h["tf"], h["evren"]) != (k["tf"], k["evren"]) or (h["stil_v2"] == "portfoy") != (k["tur"] == "pf"):
            raise PaperV2Hatasi(f"{k['strateji']}: set ({k['tf']}, {k['evren']}, {k['tur']}) havuzla ({h['tf']}, {h['evren']}, {h['stil_v2']}) uyuşmuyor")
    return s


def set_imzasi(s: dict) -> str:
    """Durum dosyasının hangi sete ait olduğunu bağlayan imza (strateji, tf, evren, tür, etiket, s, sermaye; kapanış kaydında ek: liste adı).
    Havuz kayıtlarının imza girdisi 2026-11-10'daki 10'lu sürümle BİREBİR aynıdır (kapanış kaydı eklenmeden önceki imza `onceki_set_imzasi`)."""
    ozet = {"s": float(s["s"]), "sermaye": float(s["baslangic_sermaye"]),
            "k": [(hesap_adi(k), k["tf"], k["evren"], k["tur"], k["etiket"]) + ((k["liste"],) if kapanis_mi(k) else ()) for k in s["stratejiler"]]}
    return hashlib.sha256(json.dumps(ozet, sort_keys=True).encode()).hexdigest()[:16]


def onceki_set(s: dict) -> dict:
    """Kapanış kayıtları ÇIKARILMIŞ set (= kapanış eklemesinden önceki 10'lu set)."""
    return {**s, "stratejiler": [k for k in s["stratejiler"] if not kapanis_mi(k)]}


def onceki_set_imzasi(s: dict) -> str:
    return set_imzasi(onceki_set(s))


def set16(s: dict) -> dict:
    """`kapanis_aday_ek` kayıtları ÇIKARILMIŞ set (= 2026-11-14 ilk eklemedeki 16'lı set)."""
    return {**s, "stratejiler": [k for k in s["stratejiler"] if k["etiket"] != KAPANIS_EK_ETIKET]}


def set16_imzasi(s: dict) -> str:
    return set_imzasi(set16(s))


def gecis_imzalari(s: dict) -> dict:
    """İzinli tek seferlik geçiş: {kayıtlı imza: o imzalı setin DIŞINDA kalıp sıfırdan açılabilecek hesap adları}.
    10'lu imza -> tüm kapanış hesapları (16 + ek); 16'lı imza -> yalnız `kapanis_aday_ek` hesapları. Başka her imza açık hatadır."""
    kapanis_ad = {hesap_adi(k) for k in s["stratejiler"] if kapanis_mi(k)}
    ek_ad = {hesap_adi(k) for k in s["stratejiler"] if k["etiket"] == KAPANIS_EK_ETIKET}
    out = {}
    if kapanis_ad:
        out[onceki_set_imzasi(s)] = kapanis_ad
    if ek_ad:
        out[set16_imzasi(s)] = ek_ad
    return out


def fail_closed_kontrol(tanimlar: list) -> None:
    """Paper motorunun uygulamadığı çıkış alanını kullanan strateji = AÇIK HATA (backtest'ten sessizce farklı davranmasın; DURUM.md Y-2).
    PaperMotor.birim_ekle de aynı kontrolü yapar; burada servis açılmadan, hangi stratejinin sorunlu olduğu adıyla bildirilir."""
    sorunlar = []
    for t in tanimlar:
        if t.kol == "portfoy":
            continue
        kapsam_disi = desteklenmeyen_cikis_alanlari(t.nesne.cikis_ayarlari)
        if getattr(t.nesne, "pozisyon_cikisi", None) is not None:        # strateji kancası (backtest her kapanışta çağırır; paper çağırmaz)
            kapsam_disi.append("pozisyon_cikisi (kanca)")
        if kapsam_disi:
            sorunlar.append(f"{t.kimlik}: {', '.join(kapsam_disi)}")
    if sorunlar:
        raise PaperDesteklemiyorHatasi(
            "paper v2 seti BAŞLAMAZ: şu strateji(ler) paper motorunun uygulamadığı çıkış ayarlarını kullanıyor "
            "(backtest'te uygulanıp paper'da sessizce yok sayılırdı): " + "; ".join(sorunlar))


def tanimlari_yukle(s: Optional[dict] = None) -> list:
    """Set -> StratejiTanim listesi (v2 VARSAYILAN ayarlar; evren/tf holdout ile aynı). tek: kol='tek_evren' (tüm evren TEK hesapta);
    pf: kol='portfoy' (grup payı = s)."""
    from motor.arastirma import wf_portfoy as wfp
    from motor.arastirma.v2 import ham as hm, sabit
    s = s or set_yukle()
    havuz = pd.read_csv(HAVUZ_CSV).set_index("strateji")
    out = []
    for k in s["stratejiler"]:
        if kapanis_mi(k):
            out.append(_kapanis_tanimi(k, s))
            continue
        ad, tf = k["strateji"], k["tf"]
        stil = havuz.loc[ad, "stil_v2"]
        ev = sabit.evren_listesi(k["evren"])
        if k["tur"] == "pf":
            nesne = hm.varsayilan_pf(ad, ev)
            if nesne is None:
                raise PaperV2Hatasi(f"{ad}: varsayılan ayar evrende uygun değil")
            evren = tuple(wfp.gerekli_semboller(nesne, ev))
            out.append(psg.StratejiTanim(ad, stil, "portfoy", ad, "", tf, "varsayilan", nesne, ad, Decimal(repr(float(s["s"]))), evren,
                                         etiket=k["etiket"], ayar_dosyasi="paper_v2_seti.json (v2 varsayılan ayar)"))
        else:
            ayar, nesne = hm.varsayilan_strateji(ad)
            out.append(psg.StratejiTanim(ad, stil, "tek_evren", nesne.ad, "", tf, ayar, nesne, ad, Decimal(1), tuple(ev),
                                         etiket=k["etiket"], ayar_dosyasi="paper_v2_seti.json (v2 varsayılan ayar)"))
    fail_closed_kontrol(out)
    return out


def _kapanis_tanimi(k: dict, s: dict):
    """Kapanış kaydı -> StratejiTanim: sınıf + parametre + TF + evren dondurulmuş koşu listesinden, strateji nesnesi backtest'in kullandığı
    `kapanis_kosu_listesi.strateji_kur` ile (birebir aynı nesne). Her kayıt kendi kasası: tek_evren, pay 1, aynı s/başlangıç sermayesi."""
    from araclar import kapanis_kosu_listesi as kl
    satir = kapanis_satiri(k)
    nesne, pf = kl.strateji_kur(satir["sinif"], satir["modul"], json.loads(satir["parametreler"]))
    if pf or nesne is None:
        raise PaperV2Hatasi(f"{k['kimlik']}: portföy sınıfı")
    ev = kl.evren_coz(satir["evren"])
    return psg.StratejiTanim(k["kimlik"], getattr(nesne, "stil", "") or "swing", "tek_evren", nesne.ad, "", k["tf"], "varsayilan", nesne,
                             k["kimlik"], Decimal(1), tuple(ev), etiket=k["etiket"],
                             ayar_dosyasi=f"{k['liste']} (kapanış koşu listesi, SHA-256 doğrulandı)")


def hesap_ayarlari(t, s: dict, tablo_yolu: Path = TABLO_YOLU) -> PortfoyAyarlari:
    """Hesap başına motor ayarı: risk = s x %1 (maliyet dahil; sert tavan %1 aşılamaz), limit_modu 'uygula', sembol bazlı v2 maliyet tablosu.
    Tabloda olmayan sembol açık hata (evren_maliyet: sessiz varsayılan yok)."""
    from motor.arastirma import evren_maliyet
    from motor.arastirma.v2 import sabit
    ms = {x: evren_maliyet.sembol_maliyeti(x, 1.0, tablo_yolu) for x in t.veri_semboller}
    if not ms:
        ms = {}
    mx = lambda i: max(v[i] for v in ms.values()) if ms else None          # noqa: E731
    kw = {}
    if ms:
        kw = dict(komisyon_taker_yuzde=mx(0), komisyon_maker_yuzde=mx(1), kayma_bps=mx(2), stop_kayma_bps=mx(3))
    return PortfoyAyarlari(baslangic_sermaye=float(s["baslangic_sermaye"]), risk_yuzde=float(s["s"]) * sabit.ISLEM_RISK * 100,
                           limit_modu="uygula", maliyet_sembol=ms or None, **kw)


def maliyet_modelleri(hesaplar: dict) -> dict:
    """Bütünlük kontrolü için: {hesap kimliği: maliyet_modeli(hesap ayarları)} (guven.maliyet_modeli alanları; maliyet_sembol dahil)."""
    from motor.canli import guven as gv
    return {k: gv.maliyet_modeli(h.ayarlar) for k, h in hesaplar.items()}


def cevrimdisi_maliyet_modeli(s: Optional[dict] = None, tablo_yolu: Path = TABLO_YOLU) -> dict:
    """Sunucudaki `PaperKasalar`ın bütünlük modeliyle AYNI değer, Binance'e bağlanmadan (kayıt yazmak için: `guven --kaydet`).
    Sunucu, exchangeInfo'da karşılığı olmayan sembolleri evrenden düşürüp hesap ayarlarını ondan sonra kurar; burada aynı düşürme
    `paper_veri.ESLEME`'ye göre yapılır (DK_ sembolü ESLEME'de yoksa karşılığı yok). Sunucuda başka bir sembol düşerse bütünlük 'uyuşmuyor'
    gösterir (gizlenmez) ve kayıt kullanıcı onayıyla yenilenir."""
    from motor.canli import guven as gv
    from motor.canli import paper_veri as pv
    s = s or set_yukle()
    tanimlar = tanimlari_yukle(s)
    esl = {x: ((pv.binance_sembol(x), None) if (not x.startswith("DK_") or x in pv.ESLEME) else (None, "çevrimdışı: ESLEME'de yok"))
           for t in tanimlar for x in t.veri_semboller}
    pp._tanimlara_veri_yok_isle(tanimlar, esl)
    return {t.kimlik: gv.maliyet_modeli(hesap_ayarlari(t, s, tablo_yolu)) for t in tanimlar}


# =============================================================================================== hesaplar
class HesapPaper(Paper):
    """Tek stratejinin kendi kasası. Olaylar üst `PaperKasalar`a (hesap kimliği önekiyle) iletilir."""

    def __init__(self, tanim, kaynak, kurallar: dict, ayarlar, ust=None, **kw):
        self.ust = ust
        self.butunluk_profili = "v2"
        super().__init__([tanim], kaynak, {s: kurallar[s] for s in tanim.veri_semboller if not tanim.veri_yok}, ayarlar, **kw)
        self.kimlik = tanim.kimlik

    def butunluk_maliyet(self) -> dict:
        return self.ust.butunluk_maliyet() if self.ust is not None else maliyet_modelleri({self.kimlik: self})

    def olay_ekle(self, tur: str, mesaj: str, zaman=None, bildir: bool = True):
        if self.ust is not None:
            return self.ust.olay_ekle(tur, f"[{self.kimlik}] {mesaj}", zaman if zaman is not None else self.motor.son_zaman, bildir)
        return super().olay_ekle(tur, mesaj, zaman, bildir)


def _birlestir_gunluk(seriler: list, baslangic: Decimal) -> dict:
    """Hesapların {gün: gün sonu özsermaye} sözlüklerinin toplamı. Bir hesapta o gün kaydı yoksa o hesabın son bilinen değeri
    (ilk kayıttan önce başlangıç sermayesi) kullanılır. Gün sırası: tüm hesapların günlerinin birleşimi."""
    gunler = sorted({g for s in seriler for g in s})
    out = {}
    son = [baslangic] * len(seriler)
    for g in gunler:
        for i, s in enumerate(seriler):
            if g in s:
                son[i] = D(s[g])
        out[g] = sum(son, Decimal(0))
    return out


class ToplamMotor:
    """20 hesabın toplamını `PaperMotor` benzeri salt-okunur görünümde sunar (paper_durum.olustur için). `yenile()` listeleri/toplamları
    yeniden kurar; hesapların hiçbirinin durumunu DEĞİŞTİRMEZ. Sert limitler burada UYGULANMAZ (hesap başına uygulanır)."""

    def __init__(self, ust: "PaperKasalar"):
        self.ust = ust
        self.askida = {"acik": {}, "kol": {}, "birimler": {}, "son_kap": {}}
        self.tsi_aktarildi = False
        self.yenile()

    def _motorlar(self) -> list:
        return [h.motor for h in self.ust.hesaplar.values()]

    @property
    def _acil(self):
        return any(m._acil for m in self._motorlar())

    @_acil.setter
    def _acil(self, v):
        for m in self._motorlar():
            m._acil = v

    def yenile(self) -> None:
        ms = self._motorlar()
        bas = D(self.ust.baslangic_hesap)
        self.islemler = sorted((x for m in ms for x in m.islemler), key=lambda x: pd.Timestamp(x["cikis_zamani"]))
        self.reddedilenler = sorted((x for m in ms for x in m.reddedilenler), key=lambda x: pd.Timestamp(x["zaman"]))
        self.kirpmalar = sorted((x for m in ms for x in m.kirpmalar), key=lambda x: pd.Timestamp(x["zaman"]))
        self.limit_olaylari = sorted((x for m in ms for x in m.limit_olaylari), key=lambda x: pd.Timestamp(x["zaman"]))
        self.maliyet_log = sorted((x for m in ms for x in m.maliyet_log), key=lambda x: pd.Timestamp(x["zaman"]))
        self.acik = {k: p for m in ms for k, p in m.acik.items()}
        self.tum_kollar = [k for m in ms for k in m.tum_kollar]
        self.birimler = {a: b for m in ms for a, b in m.birimler.items()}
        self.son_kap = {}
        for m in ms:
            for s, v in m.son_kap.items():
                if v == v or s not in self.son_kap:
                    self.son_kap[s] = v
        self.nakit = sum((m.nakit for m in ms), Decimal(0))
        self.kill = any(m.kill for m in ms)
        self.gunluk_blok = any(m.gunluk_blok for m in ms)
        self.gunluk_limit_sayisi = sum(m.gunluk_limit_sayisi for m in ms)
        self.gun = max((m.gun for m in ms if m.gun is not None), default=None)
        self.gun_basi = sum((m.gun_basi for m in ms), Decimal(0))
        self.son_zaman = max((m.son_zaman for m in ms if m.son_zaman is not None), default=None)
        n = len(ms)
        self.gun_kapanis = _birlestir_gunluk([m.gun_kapanis for m in ms], bas / n if n else bas)
        self.gun_kapanis_tsi = _birlestir_gunluk([m.gun_kapanis_tsi for m in ms], bas / n if n else bas)
        E = self.ozsermaye()
        self.zirve = max([bas, E] + [D(v) for v in self.gun_kapanis.values()])
        self.ozs_son = E

    def ozsermaye(self, fiyatlar: Optional[dict] = None) -> Decimal:
        return sum((m.ozsermaye(fiyatlar) for m in self._motorlar()), Decimal(0))

    def brut_kaldirac(self) -> Optional[float]:
        E = self.ozsermaye()
        if E <= 0:
            return None
        return float(sum((D(m.brut_kaldirac() or 0.0) * m.ozsermaye() for m in self._motorlar()), Decimal(0)) / E)

    def acik_stop_riski(self) -> float:
        E = self.ozsermaye()
        return float(sum((D(m.acik_stop_riski()) * m.ozsermaye() for m in self._motorlar()), Decimal(0)) / E) if E > 0 else 0.0

    def askida_ozeti(self) -> list:
        return [x for m in self._motorlar() for x in m.askida_ozeti()]


class PaperKasalar(Paper):
    """20 bağımsız hesap; `Paper` arayüzünün servis/durum yazıcısının kullandığı alt kümesi. (Paper.__init__ BİLEREK çağrılmaz:
    tek hesap/tek motor varsayımı burada geçerli değildir; ortak kalp atışı/olay kodu miras alınır.)"""

    butunluk_profili = "v2"             # guven.butunluk: v2 dosyaları + kayıt butunluk_kayit_v2_20.json

    def __init__(self, tanimlar: list, kaynak: TekrarKaynagi, kurallar: dict, s: Optional[dict] = None,
                 durum_yolu: Optional[Path] = None, her_satir_kaydet: bool = False, tablo_yolu: Path = TABLO_YOLU,
                 tetikleyen_hemen_kapat: bool = True):
        self.set_ = s or set_yukle()
        self.kaynak = kaynak
        self.durum_yolu = Path(durum_yolu) if durum_yolu else None
        self.her_satir_kaydet = her_satir_kaydet
        self.tanimlar = [t for t in tanimlar if not t.veri_yok]
        self.veri_yok = [t for t in tanimlar if t.veri_yok]
        self.tanim_ad = {t.kimlik: t for t in self.tanimlar}
        self.baslatildi = False
        self._son_gec = 0
        self.satir_sayisi = 0
        self.uyarilar: list = []
        self.olaylar: list = []
        self.bildirim = None
        self.pf_sutunlar: dict = {}
        self._askida_kayit = {"ayarlar": {}, "pf_sutunlar": {}}
        self.kalp_atisi = None
        self.baslangic_zamani = None
        self.onceki_kalp = None
        self.son_kesinti = None
        self._kalp_yazilan = None
        self.son_ozet = None
        self._karar_onbellek = None
        self.hesaplar: dict = {}
        self.yeni_hesaplar: list = []              # yukle(): kayıtta olmayıp SIFIRDAN açılacak (başlatılması gereken) kapanış hesapları
        for t in tanimlar:
            self.hesaplar[t.kimlik] = HesapPaper(t, kaynak, kurallar, hesap_ayarlari(t, self.set_, tablo_yolu), ust=self,
                                                 tetikleyen_hemen_kapat=tetikleyen_hemen_kapat)
        self.baslangic_hesap = float(self.set_["baslangic_sermaye"]) * len(self.hesaplar)
        self.ayarlar = PortfoyAyarlari(baslangic_sermaye=self.baslangic_hesap, risk_yuzde=float(self.set_["s"]) * 1.0,
                                       limit_modu="uygula")
        self.motor = ToplamMotor(self)
        self._hesap_yazilan: dict = {}

    def butunluk_maliyet(self) -> dict:
        return maliyet_modelleri(self.hesaplar)

    # ------------------------------------------------------------------ Paper arayüzü (toplam görünüm)
    @property
    def karar_onbellek(self):
        return self._karar_onbellek

    @karar_onbellek.setter
    def karar_onbellek(self, v):
        self._karar_onbellek = v
        for h in self.hesaplar.values():
            h.karar_onbellek = v

    @property
    def birimler(self) -> list:
        return [b for h in self.hesaplar.values() for b in h.birimler]

    @property
    def strateji_gun(self) -> dict:
        return {k: v for h in self.hesaplar.values() for k, v in h.strateji_gun.items()}

    @property
    def strateji_gun_tsi(self) -> dict:
        return {k: v for h in self.hesaplar.values() for k, v in h.strateji_gun_tsi.items()}

    def baslat(self, simdi):
        for h in self.hesaplar.values():
            h.baslat(simdi)
        self.baslatildi = True
        self.motor.yenile()

    def adim(self, simdi, son_satir_bayragi: bool = False) -> int:
        if not self.baslatildi:
            raise RuntimeError("önce baslat(simdi) ya da yukle()")
        n = sum(h.adim(simdi, son_satir_bayragi) for h in self.hesaplar.values())
        self._son_gec = sum(h._son_gec for h in self.hesaplar.values())
        self.satir_sayisi += n
        self.motor.yenile()
        if self.her_satir_kaydet and self.durum_yolu and n:
            self.kaydet()
        return n

    # ------------------------------------------------------------------ kalıcılık
    def durum_sozlugu(self) -> dict:
        return {"surum": STATE_SURUM, "set": SET_ADI, "set_imza": set_imzasi(self.set_), "baslangic_sermaye": self.baslangic_hesap,
                "hesaplar": {k: h.durum_sozlugu() for k, h in self.hesaplar.items()},
                "satir_sayisi": self.satir_sayisi, "uyarilar": self.uyarilar, "olaylar": self.olaylar,
                "kalp_atisi": self.kalp_atisi, "son_ozet": self.son_ozet}

    def yukle(self, yol: Optional[Path] = None, ayar_guncelle: bool = False, olay_yaz: bool = True) -> bool:
        """Kayıtlı durumu yükler. Eski 7'li set kaydı (ya da farklı set imzası) AÇIK HATA: sessizce üzerine yazılmaz/okunmaz."""
        from motor.canli.paper_motor import _dec
        yol = Path(yol or self.durum_yolu)
        if not yol.exists():
            return False
        d = _dec(json.loads(yol.read_text(encoding="utf-8")))
        if d.get("set") != SET_ADI or "hesaplar" not in d:
            raise PaperV2Hatasi(
                f"{yol}: bu durum dosyası v2 paper setine ait değil (eski 7'li set ya da başka kayıt). Eski durum SİLİNMEZ; "
                f"yeni sete temiz başlamak için eski durum dizinini kenara alın (deploy/KURULUM.md 'v2 paper setine geçiş') ya da "
                f"--durum ile boş bir dizin verin.")
        yeni_adlar: list = []
        if d.get("set_imza") != set_imzasi(self.set_):
            # TEK SEFERLİK izinli geçiş (2026-11-14): kayıt, 10'lu (kapanışsız) ya da 16'lı (kapanis_aday_ek'siz) setin imzasını taşıyor.
            # Mevcut hesaplar AYNEN yüklenir; kayıtta olmayan kapanış hesapları sıfırdan açılır. Başka her imza farkı açık hatadır.
            izinli = gecis_imzalari(self.set_)
            if d.get("set_imza") in izinli:
                yeni_adlar = [k for k in self.hesaplar if k not in d["hesaplar"]]
                if any(k not in izinli[d["set_imza"]] for k in yeni_adlar):
                    raise PaperV2Hatasi(f"{yol}: kayıtta olmayan hesaplar yalnız kapanış kayıtları olabilir: {yeni_adlar}")
            else:
                raise PaperV2Hatasi(f"{yol}: kayıtlı set imzası {d.get('set_imza')} != şimdiki {set_imzasi(self.set_)} "
                                    f"(strateji/tf/evren/etiket/s/sermaye değişmiş). Bilinçli değişiklikse eski durumu kenara alıp temiz başlayın.")
        eksik = [k for k in self.hesaplar if k not in d["hesaplar"] and k not in yeni_adlar]
        if eksik:
            raise PaperV2Hatasi(f"{yol}: kayıtta şu hesaplar yok: {eksik}")
        self.uyarilar = list(d.get("uyarilar", []))
        self.olaylar = list(d.get("olaylar", []))
        self.kalp_atisi = d.get("kalp_atisi")
        self.son_ozet = d.get("son_ozet")
        self.satir_sayisi = d.get("satir_sayisi", 0)
        for k, h in self.hesaplar.items():
            if k not in yeni_adlar:
                h.sozlukten_yukle(d["hesaplar"][k], ayar_guncelle, olay_yaz)
        self.yeni_hesaplar = [k for k in self.hesaplar if k in yeni_adlar]
        self.baslatildi = True
        self.motor.yenile()
        return True

    def yeni_hesaplari_baslat(self, simdi) -> list:
        """`yukle` geçişte (kapanış kayıtları eklendi) sıfırdan açılacak hesaplar bıraktıysa onları başlatır (`Paper.baslat`: son kapanmış barın
        kararları kurulur; dolum yok). Mevcut hesaplara dokunmaz. -> başlatılan hesap kimlikleri."""
        bas = list(self.yeni_hesaplar)
        for k in bas:
            self.hesaplar[k].baslat(simdi)
            self.olay_ekle("yeni_hesap", f"[{k}] kapanış turu paper adayı: kasa SIFIRDAN açıldı (kayıtlı durum yoktu)", simdi, False)
        self.yeni_hesaplar = []
        self.motor.yenile()
        return bas

    def kaydet(self, yol: Optional[Path] = None):
        from motor.canli.durum import atomik_yaz_json
        atomik_yaz_json(Path(yol or self.durum_yolu), _enc(self.durum_sozlugu()))


# =============================================================================================== durum dosyaları (toplam + hesap)
def hesap_ozeti(h: HesapPaper) -> dict:
    """Pano için hesap satırı (stratejiler.json -> stratejiler[].hesap): her sayı motordan."""
    m = h.motor
    bas = D(h.ayarlar.baslangic_sermaye)
    E = m.ozsermaye()
    zirve = max(m.zirve, E)
    from motor.canli import durum as d
    return {"baslangic": d.para(bas), "ozsermaye": d.para(E), "getiri": d.sayi((E - bas) / bas),
            "zirveden_dusus": d.sayi((zirve - E) / zirve if zirve > 0 else 0.0), "kill": bool(m.kill), "gunluk_blok": bool(m.gunluk_blok),
            "risk_yuzde": h.ayarlar.risk_yuzde, "kaldirac": d.sayi(m.brut_kaldirac()), "acik_stop_riski": d.sayi(m.acik_stop_riski())}


def durum_yaz(p: PaperKasalar, kaynak, dizin: Path, simdi, servis=None, kaynak_adi="paper", veri_dizini: Optional[Path] = None,
              hesaplari_yaz: bool = True) -> dict:
    """Üst düzey (toplam) + hesap başına durum dosyaları. Toplam her çağrıda; hesap dosyaları yeni satır işlendiyse ve en çok
    HESAP_YAZIM_SN'de bir (olustur ağırdır). -> toplam olusturucu çıktısı."""
    from motor.canli import durum as d
    from motor.canli import paper_durum as pdr
    dizin = Path(dizin)
    p.motor.yenile()
    p.uyarilar = p.uyarilar[-50:]
    sag = kaynak.saglik_veri() if hasattr(kaynak, "saglik_veri") else [
        {"sembol": s, "tf": tf, "son_mum_acilis": df.index[-1], "mum_indeksi": df.index} for (s, tf), df in kaynak.mumlar.items()]
    notlar = [f"VERİ YOK: {t.kimlik} — {t.veri_yok}" for t in p.veri_yok]
    bilgi, uyari = pp.disarida_metinleri(pp.disarida_gruplari(p.tanimlar))
    if bilgi:
        notlar.append(bilgi + " — ayrıntı: SAĞLIK sekmesi, saglik.json evren_disi")
    notlar += uyari
    notlar.append(f"PAPER v2 SETİ: {len(p.hesaplar)} strateji, HER BİRİ KENDİ {float(p.set_['baslangic_sermaye']):,.0f} USD kasasında; üst düzey sayılar kasaların TOPLAMIDIR "
                  "(toplamda sert limit uygulanmaz; limitler her kasada ayrıdır, bkz. stratejiler[].hesap ve durum/hesaplar/<klasör>/). "
                  "'dogrulandi' = resmi holdout kapısını geçti; 'iyi_gorundu' = sonuç sonrası keşif, KANIT DEĞİL; "
                  "'kapanis_aday' = kapanış turu paper adayı — ileri dönem sınavı gerekli, yeterli değil; "
                  "'kapanis_aday_ek' = ileri dönem sınavından SONRA seçildi (sonuç sonrası seçim), canlı adayı olamaz.")
    o = pdr.olustur(p, simdi, kaynak_saglik=sag, olaylar=p.olaylar, uyarilar=p.uyarilar, servis=servis, kaynak=kaynak_adi,
                    veri_yok_notlari=notlar, veri_dizini=veri_dizini)
    for sj in o["stratejiler"]["stratejiler"]:
        h = p.hesaplar.get(sj["kimlik"])
        if h is not None:
            sj["hesap"] = hesap_ozeti(h)
    d.yaz_hepsi(dizin, ozet=o["ozet"], stratejiler=o["stratejiler"], islemler=o["islemler"], saglik=o["saglik"],
                gecmis=o["gecmis"], ekstra=o["ekstra"])
    if hesaplari_yaz:
        simdi_ts = pd.Timestamp(simdi)
        for k, h in p.hesaplar.items():
            if not h.tanimlar:
                continue
            son = p._hesap_yazilan.get(k)
            if son is not None and son[0] == h.satir_sayisi and (simdi_ts - son[1]).total_seconds() < HESAP_YAZIM_SN:
                continue
            serier = {(s, h.tanimlar[0].tf) for s in h.tanimlar[0].veri_semboller}
            sag_h = [x for x in sag if (x["sembol"], x["tf"]) in serier]
            oh = pdr.olustur(h, simdi, kaynak_saglik=sag_h, olaylar=[e for e in p.olaylar if e["mesaj"].startswith(f"[{k}]")],
                             uyarilar=[], servis=servis, kaynak=kaynak_adi, veri_dizini=veri_dizini)
            for sj in oh["stratejiler"]["stratejiler"]:
                sj["hesap"] = hesap_ozeti(h)
            d.yaz_hepsi(dizin / HESAP_DIZINI / hesap_dizin_adi(k), ozet=oh["ozet"], stratejiler=oh["stratejiler"], islemler=oh["islemler"],
                        saglik=oh["saglik"], gecmis=oh["gecmis"], ekstra=oh["ekstra"])
            p._hesap_yazilan[k] = (h.satir_sayisi, simdi_ts)
    return o


# =============================================================================================== tekrar modu
class TekrarKaynagiV2(TekrarKaynagi):
    """Tekrar kaynağı + motor için araştırma varsayımı funding'i (ON_KAYIT_V2 1.2): DK_ sembolünde (Binance TradFi funding geçmişi yerelde yok)
    LONG her 8 saat için nominalin %0.01'ini öder (motorda short'a gelir yazılmaz: PaperMotor.funding_short_sifir). STRATEJİYE verilen
    funding_df DEĞİŞMEZ (stratejiler bu varsayımı görmez; holdout'ta da görmediler)."""

    def __init__(self, mumlar: dict, fundingler: Optional[dict] = None, pencere: Optional[dict] = None, tradfi_oran: float = 0.0001):
        super().__init__(mumlar, fundingler, pencere)
        self.motor_funding: dict = {}
        for (s, tf), df in mumlar.items():
            if s.startswith("DK_") and s not in self.motor_funding and len(df):
                idx = pd.date_range(df.index[0].floor("D"), df.index[-1].ceil("D") + pd.Timedelta(days=1), freq="8h", tz="UTC")
                self.motor_funding[s] = pd.DataFrame({"oran": np.full(len(idx), float(tradfi_oran))}, index=idx)

    def funding_dizisi(self, sembol: str):
        f = self.motor_funding.get(sembol)
        if f is not None:
            return f.index, f["oran"].to_numpy(dtype=float)
        return super().funding_dizisi(sembol)


def veri_yukle(tanimlar: list, veri_dizini=None, gerekce: str = UYUM_GEREKCE, bit=None) -> tuple:
    """Yerel veri (araştırma yükleyicileriyle AYNI; holdout dönemini de kapsar -> kilit_ac + gerekce kayda geçer). Verisi bulunamayan sembol
    evrenden DÜŞER ve `t.disarida`ya yazılır (holdout `tek_islemler` de bu sembolleri atlar; sessiz değil: durum dosyasında görünür).
    -> (mumlar {(s,tf)}, fundingler {s})."""
    from motor.portfoy import veri as pveri
    from motor.veri import depo
    mumlar, fund = {}, {}
    for t in tanimlar:
        kalan = []
        for s in t.veri_semboller:
            if (s, t.tf) not in mumlar:
                try:
                    df = pveri.mum_yukle(s, t.tf, None, bit, veri_dizini, kilit_ac=True, gerekce=gerekce)
                except (FileNotFoundError, ValueError) as e:
                    t.disarida[s] = f"yerel veri yok: {type(e).__name__}"
                    continue
                if not len(df):
                    t.disarida[s] = "yerel veri boş"
                    continue
                mumlar[(s, t.tf)] = df.drop(columns="eksik") if "eksik" in df.columns else df
            kalan.append(s)
            if s not in fund and depo.funding_yolu(s, veri_dizini).exists():
                fund[s] = depo.funding_oku(s, None, bit, dizin=veri_dizini, kilit_ac=True, gerekce=gerekce)
        _evren_daralt(t, kalan)
    return mumlar, fund


def _evren_daralt(t, kalan: list) -> None:
    """Evrenden semboller düştüyse tanım evrenini daraltır (tek_evren/portföy). Boş kaldıysa 'veri yok'."""
    if t.kol == "tek_grafik" or list(t.veri_semboller) == list(kalan):
        return
    if not kalan:
        t.veri_yok = "; ".join(f"{s}: {n}" for s, n in t.disarida.items()) or "evren boş"
        return
    if t.kol == "portfoy":
        t.veri_yok = "portföy evreninde eksik sembol: " + "; ".join(f"{s}: {n}" for s, n in t.disarida.items())
        return
    t.evren = tuple(kalan)


def kurallar_tekrar(tanimlar: list) -> dict:
    from motor.arastirma import tarama
    return {s: tarama.SEMBOL_KURALLARI.get(s, tarama.VARSAYILAN_KURAL) for t in tanimlar for s in t.veri_semboller}


PENCERE = pp.PENCERE                                          # canlıyla AYNI pencere (son N bar); tekrar modu da bunu kullanır


def kasalar_kur(tanimlar: list, mumlar: dict, fund: dict, s: Optional[dict] = None, pencere: Optional[dict] = None,
                onbellek: Optional[dict] = None, tradfi_varsayim: bool = True) -> PaperKasalar:
    """Tekrar modu için hesapları kurar (henüz başlatmaz). tradfi_varsayim: DK_ sembolünde araştırma funding varsayımı (yalnız tekrar)."""
    kaynak_sinifi = TekrarKaynagiV2 if tradfi_varsayim else TekrarKaynagi
    kaynak = kaynak_sinifi(mumlar, fund, pencere if pencere is not None else {tf: PENCERE[tf] for tf in PENCERE})
    p = PaperKasalar([t for t in tanimlar], kaynak, kurallar_tekrar(tanimlar), s)
    if tradfi_varsayim:
        dk = frozenset(x for t in tanimlar for x in t.veri_semboller if x.startswith("DK_"))
        for h in p.hesaplar.values():
            h.motor.funding_short_sifir = dk
    p.karar_onbellek = onbellek
    return p


def kos(p: PaperKasalar, bas, bit, kapat: bool = True) -> PaperKasalar:
    """Geçmişi canlıymış gibi besler (Paper.baslat / Paper.adim: canlı yolla AYNI kod). kapat: sonda açık pozisyonlar 'veri_sonu' ile kapanır
    (holdout ham işlemleri veri sonunda kapanır)."""
    bas = pd.Timestamp(bas)
    bas = bas.tz_localize("UTC") if bas.tzinfo is None else bas.tz_convert("UTC")
    p.baslat(bas)
    p.adim(pd.Timestamp(bit), son_satir_bayragi=kapat)
    return p


def tekrar_kasalar(tanimlar: list, mumlar: dict, fund: dict, bas, bit, s: Optional[dict] = None, pencere: Optional[dict] = None,
                   onbellek: Optional[dict] = None, tradfi_varsayim: bool = True, kapat: bool = True) -> PaperKasalar:
    return kos(kasalar_kur(tanimlar, mumlar, fund, s, pencere, onbellek, tradfi_varsayim), bas, bit, kapat)


# ---------------------------------------------------------------------------- karar önbelleği (saf fonksiyon belleği; paralel)
def _karar_isci(arg) -> tuple:
    """(tanim, sembol, mum çerçevesi, funding, pencere, bas, bit, dosya) -> (dosya, adet). tek_karar'ı paper'daki gibi çağırır."""
    t, s, df, fd, pencere_n, bas, bit, dosya = arg
    alt = t.alt_tanim(s)
    kaynak = TekrarKaynagi({(s, t.tf): df}, {s: fd} if fd is not None else {}, {t.tf: pencere_n})
    out = {}
    for ts in df.index[(df.index >= bas) & (df.index < bit)]:
        out[ts] = psg.tek_karar(alt, kaynak.gecmis(s, t.tf, ts), kaynak.funding_df(s))[alt.kimlik]
    tmp = Path(str(dosya) + ".tmp")
    tmp.write_bytes(pickle.dumps(out))
    tmp.replace(dosya)
    return str(dosya), len(out)


def karar_onbellegi_olustur(tanimlar: list, mumlar: dict, fund: dict, bas, bit, dizin: Path, surec: int = 4,
                            pencere: Optional[dict] = None, geri_bildirim=print) -> dict:
    """tek_evren stratejilerinin (sembol, bar) kararlarını EXACT paper yoluyla (tek_karar, aynı pencere) önceden hesaplar (süreçler arası paralel,
    sembol başına dosya; kaldığı yerden devam eder). Bu bir kısayoldur, ayrı bir hesap değildir: Paper._karar aynı anahtarı önbellekte bulursa
    aynı sonucu alır. -> {(kol_kimligi, zaman): karar}."""
    dizin = Path(dizin)
    dizin.mkdir(parents=True, exist_ok=True)
    pencere = pencere if pencere is not None else PENCERE
    bas = pd.Timestamp(bas) - pd.Timedelta(days=10)                     # baslat: her sembolün KENDİ son barı (hafta sonu/tatil payı)
    isler, dosyalar = [], {}
    for t in tanimlar:
        if t.kol != "tek_evren":
            continue
        n = pencere.get(t.tf, 1500)
        for s in t.evren:
            dosya = dizin / f"{t.kimlik}--{s}--{t.tf}.pkl"
            dosyalar[(t.kimlik, s)] = (t, dosya)
            if dosya.exists():
                continue
            df = mumlar[(s, t.tf)]
            i0 = max(0, df.index.searchsorted(bas) - n)
            isler.append((t, s, df.iloc[i0:], fund.get(s), n, bas, pd.Timestamp(bit), dosya))
    if isler:
        geri_bildirim(f"[onbellek] {len(isler)} (strateji, sembol) işi, {surec} süreç")
        if surec <= 1:
            for a in isler:
                geri_bildirim(f"[onbellek] {a[0].kimlik} {a[1]}: {_karar_isci(a)[1]} karar")
        else:
            with cf.ProcessPoolExecutor(max_workers=surec) as ex:
                for yol, adet in ex.map(_karar_isci, isler):
                    geri_bildirim(f"[onbellek] {Path(yol).name}: {adet} karar")
    out = {}
    for (_, s), (t, dosya) in dosyalar.items():
        alt = t.alt_tanim(s).kimlik
        for ts, k in pickle.loads(Path(dosya).read_bytes()).items():
            out[(alt, ts)] = k
    return out
