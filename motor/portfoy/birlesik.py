"""Tek-grafik stratejilerini birden çok sembolde AYNI sermaye ve AYNI sert limitler altında çalıştıran sarmalayıcı
(karar 23b). Canlıdaki "ajan başına ~3 strateji x birden çok enstrüman" düzeninin backtest'i.

Her (strateji, sembol) bir KOL'dür. Sinyaller kolun KENDİ sembol verisinden `Strateji.sinyaller` ile üretilir (tek-grafik
kuralları: stop/hedef/yönlü çıkış/iz süren stop/başabaş/kısmi/zaman çıkışı); işlemler ortak hesapta, ortak
özsermaye üzerinden boyutlanır. Portföy motorunun sert limitleri (işlem başı %1, brüt 3x, günlük %3, kill %20) ve
ek ayarlar geçerlidir:
  - toplam_risk_tavani_yuzde (varsayılan 5): açık pozisyonların stopa kadar toplam riski özsermayenin bu yüzdesini
    aşamaz; yeni giriş kalan bütçeye KIRPILIR (bütçe bitmişse reddedilir: "toplam_risk_tavani").
  - max_pozisyon (varsayılan None): aynı anda açık kol sayısı.
Her kolun pozisyonu AYRIDIR (borsada tek yönlü modda aynı sembolün zıt yönlü iki kolu netleşirdi; burada netleşme
modellenmez -> komisyon biraz yüksek, brüt maruziyet muhafazakâr hesaplanır).

Tek kolda tek-grafik motoruyla (`motor.backtest.motor.backtest`) aynı sonucu beklersiniz; bilinen FARKLAR:
  1. Brüt tavan: dolumda nominal <= 3x/(1+3*taker)*özsermaye (komisyon payı); tek-grafik motoru tam 3x'e izin verir.
     Kaldıraç tavanına dayanan (dar stoplu) pozisyonlar bu yüzden ~%0.15 daha küçük olur.
  2. Kapanışta brüt > 3x olursa ertesi açılışta oranla küçültülür ("kaldirac_azalt"); tek-grafik motorunda yok.
  3. Boyutlandırma özsermayesi dolum anındaki MTM'dir (tek kolda nakitle aynı; çok kolda diğer pozisyonların K/Z'si dahil).
  4. İşlem satırı `cikis_fiyati` kısmi çıkışlarda ağırlıklı ortalamadır (tek-grafikte son parça); `miktar` tepe miktardır.
  5. Günlük kayıp/kill switch aynı kurallarla ama portföy özsermayesi üzerinden.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from motor.backtest.motor import CikisYokHatasi, MESAJ_CIKIS_YOK
from motor.portfoy.motor import Kol, PortfoyAyarlari, SonucPortfoy, _Motor
from motor.portfoy.temel import ortak_eksen
from motor.strateji import gostergeler as gst
from motor.strateji.temel import SINYAL_SUTUNLARI, Strateji


@dataclass
class KolTanimi:
    strateji: Strateji
    sembol: str


def _kol_kur(no: int, strateji: Strateji, sembol: str, mumlar: pd.DataFrame, eksen) -> Kol:
    ca = strateji.cikis_ayarlari
    if not (strateji.cikis_var_mi() or ca.atr_iz_suren_k or ca.zaman_cikisi_mum or ca.sabit_r_hedefi):
        raise CikisYokHatasi(f"{strateji.ad}/{sembol}: {MESAJ_CIKIS_YOK}")
    sig = strateji.sinyaller(mumlar)
    if not sig.index.equals(mumlar.index):
        raise ValueError("sinyaller() mumlarla aynı indeksi dönmeli")
    eksik = [c for c in SINYAL_SUTUNLARI if c not in sig.columns]
    if eksik:
        raise ValueError(f"Sinyal sütunları eksik: {eksik}")
    if np.any((sig["yon"].to_numpy(dtype=int) != 0) & sig["stop"].isna().to_numpy()):
        raise ValueError("Giriş sinyali olan her satırda stop zorunlu")

    def yeniden(seri, bos, tip):
        return seri.reindex(eksen).fillna(bos).to_numpy(dtype=tip)

    cikis = yeniden(sig["cikis"], False, bool)
    cl = (cikis | yeniden(sig["cikis_long"], False, bool)) if "cikis_long" in sig.columns else cikis
    cs = (cikis | yeniden(sig["cikis_short"], False, bool)) if "cikis_short" in sig.columns else cikis
    zc = (sig["zaman_cikisi_mum"].reindex(eksen).to_numpy(dtype=float) if "zaman_cikisi_mum" in sig.columns
          else np.full(len(eksen), np.nan))
    atr = (gst.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], ca.atr_periyot).reindex(eksen).to_numpy()
           if ca.atr_iz_suren_k else np.full(len(eksen), np.nan))
    return Kol(kimlik=f"{no}:{strateji.ad}|{sembol}", sembol=sembol, mod="sinyal", strateji_ad=strateji.ad,
               s_yon=yeniden(sig["yon"], 0, int), s_stop=sig["stop"].reindex(eksen).to_numpy(dtype=float),
               s_hedef=sig["hedef"].reindex(eksen).to_numpy(dtype=float),
               s_cikis_l=cl, s_cikis_s=cs, s_zc=zc, atr=atr, cikis_ayarlari=ca)


def birlesik_backtest(veriler: dict, kollar, ayarlar: PortfoyAyarlari = None, fundingler: Optional[dict] = None,
                      toplam_risk_tavani_yuzde: Optional[float] = 5.0, max_pozisyon: Optional[int] = None,
                      islem_baslangic: Optional[pd.Timestamp] = None) -> SonucPortfoy:
    """kollar: [(Strateji, sembol), ...] ya da [KolTanimi, ...]. Her sembol `veriler`de olmalı.
    Ayar çakışmasında fonksiyon argümanları (toplam_risk_tavani_yuzde, max_pozisyon) `ayarlar` alanlarını ezer."""
    ayarlar = ayarlar or PortfoyAyarlari()
    ayarlar = PortfoyAyarlari(**{**ayarlar.__dict__, "toplam_risk_tavani_yuzde": toplam_risk_tavani_yuzde,
                                 "max_pozisyon": max_pozisyon})
    tanimlar = [k if isinstance(k, KolTanimi) else KolTanimi(*k) for k in kollar]
    if not tanimlar:
        raise ValueError("en az bir kol gerekli")
    eksik = sorted({k.sembol for k in tanimlar} - set(veriler))
    if eksik:
        raise ValueError(f"verisi olmayan semboller: {eksik}")
    eksen = ortak_eksen(veriler)
    kol_listesi = [_kol_kur(no, k.strateji, k.sembol, veriler[k.sembol], eksen) for no, k in enumerate(tanimlar)]
    return _Motor(veriler, kol_listesi, ayarlar, fundingler, eksen, islem_baslangic).calistir()
