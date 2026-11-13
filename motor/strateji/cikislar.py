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
    # --- Pozisyon bilinçli çıkışlar (hepsi varsayılanda KAPALI; kapanışta değerlendirilir, çıkış sonraki açılışta) ---
    # 8) Yalnız kârda sinyal çıkışı (Freqtrade exit_profit_only): cikis/cikis_long/cikis_short sinyali, kapanış kârı
    #    (kâr% > yalniz_karda_min_kar_yuzde) iken uygulanır; aksi halde yok sayılır. Stop/zaman/diğer çıkışlar etkilenmez.
    yalniz_karda_cikis: bool = False
    yalniz_karda_min_kar_yuzde: float = 0.0
    # 9) Asgari tutma: tutulan mum < min_tutma_mum iken SİNYAL çıkışı yapılmaz (stop/hedef her zaman geçerli).
    min_tutma_mum: Optional[int] = None
    # 10) Yasa bağlı zarar çıkışı: ((tutulan_mum_esigi, zarar_yuzde), ...) tutulan >= eşik ve zarar% >= zarar_yuzde ise çık
    #     (neden "yasa_zarar"). Örn. ((20, 7.5),).
    yasa_bagli_zarar_cikisi: tuple = ()
    # 11) Kapanış bazlı chandelier: long kapanış <= (girişten beri en yüksek HIGH) - k*ATR ise çık (short ayna; neden
    #     "kapanis_chandelier"). atr_iz_suren_k bar içi stopdur; bu kapanışa göredir.
    kapanis_chandelier_k: Optional[float] = None
    kapanis_chandelier_periyot: int = 14
    # 12) Yüzde cinsinden kısmi kâr: ((kar_yuzde, oran), ...) giriş fiyatına göre kâr% seviyesinde ilk miktarın `oran`ı
    #     kapanır (mevcut `kismi` R cinsindendir; aynı mekanizmayla işlenir).
    kismi_yuzde: tuple = ()

    def __post_init__(self):
        def tup(ad, uzunluk=2):
            v = tuple(tuple(float(x) for x in e) for e in getattr(self, ad))
            if any(len(e) != uzunluk for e in v):
                raise ValueError(f"{ad}: her eleman {uzunluk} değerli olmalı")
            object.__setattr__(self, ad, v)
            return v
        for ad in ("stop_basamaklari", "azalan_roi", "kar_rsi_esikleri", "yasa_bagli_zarar_cikisi", "kismi_yuzde"):
            tup(ad)
        object.__setattr__(self, "yasa_bagli_zarar_cikisi", tuple(sorted(self.yasa_bagli_zarar_cikisi)))
        object.__setattr__(self, "kismi_yuzde", tuple(sorted(self.kismi_yuzde)))
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
        if self.min_tutma_mum is not None and self.min_tutma_mum < 1:
            raise ValueError("min_tutma_mum >= 1 olmalı")
        if any(e[0] < 0 or e[1] <= 0 for e in self.yasa_bagli_zarar_cikisi):
            raise ValueError("yasa_bagli_zarar_cikisi: mum >= 0 ve zarar_yuzde > 0 olmalı")
        if self.kapanis_chandelier_k is not None and (self.kapanis_chandelier_k <= 0 or self.kapanis_chandelier_periyot < 1):
            raise ValueError("kapanis_chandelier_k > 0 ve periyot >= 1 olmalı")
        if any(e[0] <= 0 or not 0 < e[1] <= 1 for e in self.kismi_yuzde):
            raise ValueError("kismi_yuzde: kar_yuzde > 0 ve 0 < oran <= 1 olmalı")


@dataclass(frozen=True)
class PozisyonDurumu:
    """Strateji `pozisyon_cikisi(durum) -> bool` kancasına her mum KAPANIŞINDA verilen açık pozisyon özeti.
    Yalnız kapanmış mumlardan hesaplanır (lookahead yok). mum_indeksi: mumlar DataFrame'indeki bu kapanan mumun
    konumu (strateji kendi sinyaller() çıktısına/göstergelerine bakabilir; i'den sonrasına bakmamalıdır)."""
    yon: int
    giris_fiyati: float
    giris_mum_indeksi: int
    mum_indeksi: int
    tutulan_mum: int
    en_yuksek: float          # girişten (giriş mumu dahil) beri en yüksek HIGH
    en_dusuk: float           # girişten beri en düşük LOW
    kapanis: float
    kar_yuzde: float          # kapanışa göre, yöne duyarlı


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


def yasa_zarar_doldu(tutulan: int, kar: float, tablo: tuple) -> bool:
    """tablo: ((mum, zarar%), ...). tutulan >= mum ve zarar% (= -kar) >= zarar_yuzde olan bir satır varsa True."""
    return any(tutulan >= mum and -kar >= zarar for mum, zarar in tablo)


def kapanis_chandelier_doldu(yon: int, kapanis: float, ekstrem: float, atr: float, k: float) -> bool:
    if math.isnan(atr):
        return False
    return kapanis <= ekstrem - k * atr if yon == 1 else kapanis >= ekstrem + k * atr


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
