"""Kapanış turunun tek grafik ham koşusu ve bağımsız araştırma hesabı.

Mum/işlem maliyetinde v2 yardımcıları kullanılır. Mevcut backtest motoru
pozisyonu sert %1 limitiyle üretir; kabul edilen ham R işlemleri ayrı araştırma
hesabında %1,5 risk ve zirveden %30 kill ile yeniden oynatılır. Portföy
stratejileri bu modüle verilmez.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from motor.arastirma import evren_maliyet, secim, wf_evren
from motor.arastirma.v2 import eleme, ham as v2_ham
from motor.backtest.motor import backtest
from motor.strateji import funding
from motor.strateji.temel import Strateji


def tek_ham_kos(
    strateji: Strateji,
    sembol: str,
    tf: str,
    carpan: float,
    tablo_yolu: Path,
    veri_al=None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Bir sembolü v2 maliyetiyle çalıştır; (ham işlem, günlük MTM, mumlar)."""
    if carpan not in (1.0, 2.0):
        raise ValueError(f"kapanış maliyet çarpanı 1 veya 2 olmalı: {carpan}")
    veri_al = v2_ham.veri_oku if veri_al is None else veri_al
    mumlar, fonlama = veri_al(sembol, tf)
    v2_ham.sizinti_kontrol(sembol, tf, mumlar, fonlama)
    if mumlar is None or mumlar.empty:
        raise FileNotFoundError(f"{sembol} {tf}: geliştirme döneminde mum yok")
    kural = wf_evren.tarama.SEMBOL_KURALLARI.get(sembol, wf_evren.tarama.VARSAYILAN_KURAL)
    ayarlar = evren_maliyet.maliyet_ayarlari(sembol, kural, carpan, tablo_yolu)
    hazir = funding.stratejiye_hazirla(strateji, mumlar, fonlama, sembol, tf)
    sonuc = backtest(hazir, strateji, ayarlar, fonlama)
    ham, mtm = v2_ham.islem_hazirla(sonuc.islemler, sembol, tf, carpan, mumlar, tablo_yolu)
    return ham, mtm, mumlar


def kendi_hesabi_oynat(
    hamlar: dict[str, pd.DataFrame],
    semboller: tuple[str, ...],
    analiz_bas,
    analiz_bit,
    carpan: float,
    tablo_yolu: Path,
) -> tuple[dict, pd.DataFrame]:
    """Tek stratejinin 13 semboldeki işlemlerini tek araştırma hesabında oynatır."""
    if carpan not in (1.0, 2.0):
        raise ValueError(f"kapanış maliyet çarpanı 1 veya 2 olmalı: {carpan}")
    if set(hamlar) != set(semboller):
        raise ValueError(f"ham sembol kümesi evrenle farklı: eksik={set(semboller)-set(hamlar)}")
    parcalar = []
    for sembol in semboller:
        parca = hamlar[sembol]
        if not parca.empty:
            parca = parca[pd.DatetimeIndex(parca["giris_zamani"]) >= pd.Timestamp(analiz_bas)].copy()
            parca["sembol"] = sembol
            parcalar.append(parca)
    if not parcalar:
        return {"islem_sayisi": 0, "kill_olayi": 0, "profit_factor": float("nan"),
                "net_getiri": 0.0, "kabul": [], "r_enstruman": {}, "r_yil": {}}, pd.DataFrame()
    oos = pd.concat(parcalar, ignore_index=True)
    oos["maliyet_payi"] = eleme.maliyet_payi_v2(oos, carpan, tablo_yolu)
    tablo = wf_evren.oynatma_tablosu(oos, semboller)
    ayar = secim.OynatmaAyari(risk=0.015, kill=0.30)
    metrik = wf_evren.kasa_metrikleri(tablo, analiz_bas, analiz_bit, ayar=ayar)
    kabul = metrik["kabul"]
    kayit = tablo.iloc[kabul]
    metrik["r_enstruman"] = kayit.groupby("sembol")["r"].sum().to_dict()
    yillar = pd.DatetimeIndex(kayit["giris"]).year
    metrik["r_yil"] = pd.Series(kayit["r"].to_numpy(), index=yillar).groupby(level=0).sum().to_dict()
    return metrik, tablo
