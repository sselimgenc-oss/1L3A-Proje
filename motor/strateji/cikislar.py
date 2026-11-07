"""Çıkış modülleri. Motor bunları her mumun KAPANIŞINDA uygular; etki sonraki mumda başlar.

Saf fonksiyonlar (float); strateji hangisini istediğini CikisAyarlari ile seçer.
"""
from dataclasses import dataclass
from typing import Optional

import math


@dataclass(frozen=True)
class CikisAyarlari:
    atr_iz_suren_k: Optional[float] = None      # None: kapalı. Aksi halde stop = ekstrem -/+ k*ATR
    atr_periyot: int = 14
    zaman_cikisi_mum: Optional[int] = None      # N mum tutulduysa çık
    sabit_r_hedefi: Optional[float] = None      # hedef = giriş +/- R*risk (sinyalde hedef yoksa)
    basabas_r_esigi: Optional[float] = None     # örn. 1.0: kâr 1R'ye ulaşınca stop girişe çekilir
    # Kısmi kâr: ((r, oran), ...) örn. ((1.0, 0.25),) = 1R'de ilk pozisyonun %25'i kapanır.
    kismi: tuple = ()
    # --- Ek modüller (hepsi varsayılanda KAPALI; kaynak: stratejiler/cikis_modulleri_ek.csv) ---
    # 1) Kâra bağlı çok basamaklı stop: ((kar_esigi_R, stop_R), ...) örn. ((1.0, 0.0), (2.0, 1.0)):
    #    zirve +1R'ye ulaşınca stop girişe, +2R'ye ulaşınca +1R'ye çekilir. Stop asla gevşemez.
    stop_basamaklari: tuple = ()
    # 2a) Zamanla azalan kâr hedefi: ((tutulan_mum, hedef_kar_yuzde), ...) örn. ((0, 4.0), (30, 2.0), (60, 0.5)).
    #     Kapanıştaki kâr% >= o anki (en büyük tutulan_mum <= tutulan) hedef ise sonraki açılışta çıkılır (neden "roi").
    azalan_roi: tuple = ()
    # 2b) Zirveden geri çekilme: zirve kâr% >= geri_cekilme_min_kar_yuzde iken zirveden kâr% farkı >= geri_cekilme_yuzde
    #     ise çıkılır (neden "geri_cekilme").
    geri_cekilme_yuzde: Optional[float] = None
    geri_cekilme_min_kar_yuzde: float = 0.0
    # 3) Kâra bağlı RSI çıkışı: ((kar_yuzde, rsi_esik), ...), kar_yuzde > 0 zorunlu (YALNIZ kârdayken; zararda çalışmaz).
    #    Kâr% >= kar_yuzde olan en yüksek basamağın eşiği: long RSI >= eşik, short RSI <= 100-eşik ise çıkılır ("kar_rsi").
    kar_rsi_esikleri: tuple = ()
    rsi_periyot: int = 14
    # 4) Elder güvenli bölge stopu: çarpan (örn. 2.0). Long: son elder_n1 mumda aşağı penetrasyon ortalaması;
    #    stop = dip - çarpan*ortalama, son elder_n2 mumun en yükseği, yalnız yukarı. Short ayna (tepe, yalnız aşağı).
    elder_guvenli_bolge_k: Optional[float] = None
    elder_n1: int = 10
    elder_n2: int = 3
    # 6) Farley üç aşama: aşama1 ilk stop, aşama2 atr_iz_suren_k, aşama3 = hedefe giden yolun
    #    agresif_iz_esigi oranına (örn. 0.75) ulaşılınca daha dar agresif_iz_atr_k x ATR izi. Hedef (sinyal/sabit_r) gerekir.
    agresif_iz_esigi: Optional[float] = None
    agresif_iz_atr_k: Optional[float] = None
    # 7) Stop sonrası bekleme: stop/stop_gap çıkışından sonra N mum yeni giriş yok (neden "bekleme").
    stop_sonrasi_bekleme_mum: Optional[int] = None

    def __post_init__(self):
        def tup(ad, uzunluk=2):
            v = tuple(tuple(float(x) for x in e) for e in getattr(self, ad))
            if any(len(e) != uzunluk for e in v):
                raise ValueError(f"{ad}: her eleman {uzunluk} değerli olmalı")
            object.__setattr__(self, ad, v)
            return v
        for ad in ("stop_basamaklari", "azalan_roi", "kar_rsi_esikleri"):
            tup(ad)
        object.__setattr__(self, "stop_basamaklari", tuple(sorted(self.stop_basamaklari)))
        object.__setattr__(self, "azalan_roi", tuple(sorted(self.azalan_roi)))
        object.__setattr__(self, "kar_rsi_esikleri", tuple(sorted(self.kar_rsi_esikleri)))
        if any(e[0] <= 0 for e in self.stop_basamaklari):
            raise ValueError("stop_basamaklari: kar_esigi_R > 0 olmalı")
        if any(e[1] < 0 for e in self.azalan_roi):
            raise ValueError("azalan_roi: hedef kâr% >= 0 olmalı (zararda çıkış yok)")
        if any(e[0] <= 0 or not 0 < e[1] <= 100 for e in self.kar_rsi_esikleri):
            raise ValueError("kar_rsi_esikleri: kar_yuzde > 0 (yalnız kârdayken) ve 0 < rsi <= 100 olmalı")
        if self.geri_cekilme_yuzde is not None and self.geri_cekilme_yuzde <= 0:
            raise ValueError("geri_cekilme_yuzde > 0 olmalı")
        if self.elder_guvenli_bolge_k is not None and (self.elder_guvenli_bolge_k <= 0 or self.elder_n1 < 2
                                                       or self.elder_n2 < 1):
            raise ValueError("elder: k > 0, n1 >= 2, n2 >= 1 olmalı")
        if (self.agresif_iz_esigi is None) != (self.agresif_iz_atr_k is None):
            raise ValueError("agresif_iz_esigi ve agresif_iz_atr_k birlikte verilmeli")
        if self.agresif_iz_esigi is not None and not (0 < self.agresif_iz_esigi < 1 and self.agresif_iz_atr_k > 0):
            raise ValueError("agresif_iz_esigi 0-1 arası, agresif_iz_atr_k > 0 olmalı")
        if self.stop_sonrasi_bekleme_mum is not None and self.stop_sonrasi_bekleme_mum < 1:
            raise ValueError("stop_sonrasi_bekleme_mum >= 1 olmalı")


def r_hedef_fiyati(yon: int, giris: float, risk_birim: float, r: float) -> float:
    return giris + yon * r * risk_birim


def iz_suren_stop(yon: int, stop: float, ekstrem: float, atr: float, k: float) -> float:
    """ekstrem: girişten beri en yüksek (long) / en düşük (short) fiyat. Stop asla gevşemez."""
    if math.isnan(atr):
        return stop
    yeni = ekstrem - yon * k * atr
    return max(stop, yeni) if yon == 1 else min(stop, yeni)


def basabasa_cek(yon: int, stop: float, giris: float, ekstrem: float,
                 risk_birim: float, r_esik: float) -> float:
    if yon * (ekstrem - giris) >= r_esik * risk_birim:
        return max(stop, giris) if yon == 1 else min(stop, giris)
    return stop


def zaman_doldu(tutulan_mum: int, limit: Optional[int]) -> bool:
    return limit is not None and tutulan_mum >= limit



def stop_basamagi(yon: int, stop: float, giris: float, ekstrem: float, risk_birim: float, basamaklar: tuple) -> float:
    """basamaklar: ((kar_esigi_R, stop_R), ...). Ulaşılan en yüksek basamağın stopu; stop asla gevşemez."""
    ilerleme = yon * (ekstrem - giris) / risk_birim
    yeni = stop
    for esik, stop_r in basamaklar:
        if ilerleme >= esik:
            hedef = giris + yon * stop_r * risk_birim
            yeni = max(yeni, hedef) if yon == 1 else min(yeni, hedef)
    return yeni


def kar_yuzde(yon: int, giris: float, fiyat: float) -> float:
    return yon * (fiyat - giris) / giris * 100.0


def azalan_roi_doldu(tutulan: int, kar: float, tablo: tuple) -> bool:
    """tablo: ((mum, hedef_kar%), ...) mum'a göre sıralı; en büyük mum <= tutulan satırı geçerlidir."""
    hedef = None
    for mum, yuzde in tablo:
        if tutulan >= mum:
            hedef = yuzde
    return hedef is not None and kar >= hedef


def geri_cekilme_doldu(zirve_kar: float, kar: float, esik: Optional[float], min_zirve: float) -> bool:
    return esik is not None and zirve_kar >= min_zirve and zirve_kar - kar >= esik


def kar_rsi_doldu(yon: int, kar: float, rsi: float, tablo: tuple) -> bool:
    """YALNIZ kârdayken (kar > 0). Eşik, kâr% >= kar_yuzde olan en yüksek basamaktan alınır."""
    if not tablo or math.isnan(rsi) or kar <= 0:
        return False
    esik = None
    for kar_esigi, rsi_esik in tablo:
        if kar >= kar_esigi:
            esik = rsi_esik
    if esik is None:
        return False
    return rsi >= esik if yon == 1 else rsi <= 100.0 - esik


def elder_guvenli_bolge(fiyat_dizi, i: int, n1: int, n2: int, k: float, yon: int = 1) -> float:
    """Elder güvenli bölge (hikyuu SAFTYLOSS ile aynı mantık). fiyat_dizi: long için düşük, short için yüksek.
    Her j (son n2 mum) için: j'ye kadar n1-1 çiftte long'da düşüşlerin (short'ta yükselişlerin) ortalama penetrasyonu;
    long: dizi[j] - k*ort, n2 içinde en yüksek; short: dizi[j] + k*ort, n2 içinde en düşük. Veri yetmezse nan."""
    if i + 1 < n1 + n2 - 1:
        return math.nan
    sonuc = math.nan
    for j in range(i + 1 - n2, i + 1):
        toplam, adet = 0.0, 0
        for m in range(j + 2 - n1, j + 1):
            onceki, simdi = fiyat_dizi[m - 1], fiyat_dizi[m]
            fark = (onceki - simdi) * yon
            if fark > 0:
                toplam += fark
                adet += 1
        deger = fiyat_dizi[j] - yon * k * toplam / adet if adet else fiyat_dizi[j]
        if math.isnan(deger):
            continue
        if math.isnan(sonuc) or (deger > sonuc if yon == 1 else deger < sonuc):
            sonuc = deger
    return sonuc
