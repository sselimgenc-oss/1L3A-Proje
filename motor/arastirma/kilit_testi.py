"""Kilitli dönem testi (Aşama 2, Katman 4). BAĞLAYICI YÖNTEM: sonuclar/kilit/ON_KAYIT.md (koşudan önce yazıldı).
Sonuçlar görüldükten sonra yöntem, ölçüt, grup listesi DEĞİŞTİRİLMEZ.

Akış (CLI `--asama`):
  gruplar : A/B/C/D listesini kurar -> sonuclar/kilit/gruplar.csv (KİLİT KAPALI; veri okunmaz).
  ayar    : her satır için ayarı seçer (KİLİT KAPALI; veri yalnız kilit öncesi) -> sonuclar/kilit/secilen_ayarlar.csv.
            Tek-grafik: wf_tarama ile aynı aday kümesi (aday_listesi), aynı motor/sembol kuralı, aynı skor
            (PF(R), eşitlikte çok işlem, sonra sıra) ve aynı asgari işlem (swing 15, diğer 30). Eğitim penceresi = kilitten
            önceki SON pencere: swing 730 gün, daytrade/scalp 365 gün, bitiş 2025-11-01. Portföy: wf_portfoy ile aynı
            (eğitim 730 gün, günlük Sharpe skoru, >=10 işlem, >=60 gün, karar 25 risk bütçesi).
  kilit   : KİLİT AÇILIR (kilit_ac=True, gerekçe sabit, açılış sonuclar/kilit_acilis.jsonl'a yazılır). Seçilen ayar
            DEĞİŞTİRİLMEDEN tam veride koşulur (islem_baslangic = kilit; ısınma kilit öncesi veriyle) ->
            sonuclar/kilit/kilit_ham.parquet, islemler/, gunluk/.
  rapor   : ölçütler, set testi (secim.py yeniden oynatıcı, tek kasa, sert limitler; portföy kolu %50/%50),
            ayırt edicilik (C vs D, Spearman) -> sonuc.csv, set.csv, RAPOR.md.

GRUP TANIMLARI (ON_KAYIT.md'nin uygulaması; belirsiz kalan noktaların KOŞUDAN ÖNCE verilen kararları)
  A = oneri.csv rol=secim; B = rol=yedek; C = final_aday_havuzu_tek_grafik.csv (51) + portföy sağlamları
  (saglamlik_portfoy/p3_*_v3.csv ve p3_kripto_v2.csv, saglam_mi=True).
  D (tek-grafik) = saglamlik/{k3_kripto,k3_dk_v2,k3_hisse_kisa}.csv içinde saglam_mi=False olanlar (C'de olmayan)
     + WF'den kalanlardan (wf/{k3_kripto,k3_dk_v2,k3_hisse_kisa}.csv, gecti=False, hata yok, OOS işlem >= 1 [WF PF'si
       tanımlı olsun diye]; C/D'de olmayan anahtar) rastgele 60 satır: numpy default_rng(42).choice(n, 60, replace=False)
       (satır sırası = dosya sırası k3_kripto, k3_dk_v2, k3_hisse_kisa).
  D (portföy) = ON_KAYIT yalnız tek-grafiği sayar; portföyde Sharpe karşılaştırması için, C'nin geldiği aynı dosyalarda
     saglam_mi=False olan portföy satırları (WF'yi karar 24 ile geçip sağlamlıktan kalanlar) D-portföy sayılır.
  Gruplar örtüşebilir (A ve B, C'nin alt kümesidir); anahtar = strateji|sembol(veya evren)|tf, sonuç satırı tektir.
  Aynı anahtar hem C hem D adayıysa C önceliklidir.

ÖLÇÜTLER (ON_KAYIT): aday = kilitli dönemde net > 0 VE PF >= 1.0 (işlem yok = kaldı). Set (A, tek kasa): net > 0, max düşüş
  <= %20, Sharpe > 0. Ayırt edicilik: medyan R (tek-grafik; satır başına işlem başı ortalama R'nin grup medyanı, >=1 işlemli
  satırlar) ve portföyde Sharpe medyanı: C > D.

Her aday görevi hata yakalar ve hatayı SATIRA yazar (sessiz yutma yok). Paralel en çok 4 süreç; kaldığı yerden devam eder.
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import time
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from motor.arastirma import secim as sec
from motor.arastirma import tarama
from motor.arastirma import wf_portfoy as wfp
from motor.arastirma import wf_tarama as wf
from motor.backtest.motor import backtest
from motor.portfoy import veri as pveri
from motor.portfoy.motor import portfoy_backtest
from motor.strateji import funding, kayit
from motor.veri import depo, kilit
from motor.veri.yeniden_ornekle import tf_mumlari

KOK = Path(__file__).resolve().parents[2]
KILIT = pd.Timestamp("2025-11-01", tz="UTC")
GEREKCE = "Katman 4 kilitli dönem testi, ON_KAYIT.md, kullanıcı onayı 2026-11-07"
CIKTI = KOK / "sonuclar" / "kilit"
TOHUM = 42
N_RASTGELE = 60
GUN = pd.Timedelta(days=1)
D_DOSYALARI = ("k3_kripto", "k3_dk_v2", "k3_hisse_kisa")
PORTFOY_SAGLAMLIK = ("p3_hepsi_v3", "p3_hisse_v3", "p3_hisse_emtia_v3", "p3_kripto_v2")   # C'nin geldiği dosyalar
SET_LIMIT = {"max_dusus": 0.20}


def _anahtar(strateji, sembol, tf) -> str:
    return f"{strateji}|{sembol}|{tf}"


# ============================================================================ 1. gruplar
def gruplari_kur(kok: Path = KOK) -> pd.DataFrame:
    """A/B/C/D listesi (veri okunmaz). Satır = benzersiz anahtar; A,B,C,D bool sütunları."""
    s = kok / "sonuclar"
    satirlar: dict = {}

    def ekle(tur, strateji, sembol, tf, grup, wf_dosya, d_kaynak=""):
        k = _anahtar(strateji, sembol, tf)
        if k not in satirlar:
            satirlar[k] = {"kimlik": k, "tur": tur, "strateji": strateji, "sembol": sembol, "tf": tf,
                           "wf_dosya": wf_dosya, "A": False, "B": False, "C": False, "D": False, "d_kaynak": ""}
        satirlar[k][grup] = True
        if d_kaynak and not satirlar[k]["d_kaynak"]:
            satirlar[k]["d_kaynak"] = d_kaynak

    # C: tek-grafik havuz + portföy sağlamları
    havuz = pd.read_csv(s / "final_aday_havuzu_tek_grafik.csv")
    for _, h in havuz.iterrows():
        ekle("tek", h.strateji, h.sembol, h.tf, "C", sec.etiket_sembol(h.sembol))
    portfoy_tum = {}
    for stem in PORTFOY_SAGLAMLIK:
        d = pd.read_csv(s / "saglamlik_portfoy" / f"{stem}.csv")
        portfoy_tum[stem] = d
        for _, r in d[d["saglam_mi"].astype(bool)].iterrows():
            ekle("portfoy", r.strateji, r.evren, r.tf, "C", stem)
    # A, B: oneri.csv
    oneri = pd.read_csv(s / "secim" / "oneri.csv")
    for _, o in oneri.iterrows():
        k = o.kimlik
        if k not in satirlar:
            raise ValueError(f"oneri.csv satırı C'de yok: {k}")
        satirlar[k]["A" if o.rol == "secim" else "B"] = True
    # D (tek): sağlamlıktan kalanlar
    for e in D_DOSYALARI:
        d = pd.read_csv(s / "saglamlik" / f"{e}.csv")
        for _, r in d[~d["saglam_mi"].astype(bool)].iterrows():
            if _anahtar(r.strateji, r.sembol, r.tf) in satirlar and satirlar[_anahtar(r.strateji, r.sembol, r.tf)]["C"]:
                continue
            ekle("tek", r.strateji, r.sembol, r.tf, "D", e, "saglamlik_kalan")
    # D (tek): WF'den kalanlardan rastgele 60
    havuzlar = []
    for e in D_DOSYALARI:
        d = pd.read_csv(s / "wf" / f"{e}.csv")
        d["hata"] = d["hata"].fillna("")
        d = d[(~d["gecti"].astype(bool)) & (d["hata"] == "") & (d["islem_sayisi"].fillna(0) >= 1)]
        for _, r in d.iterrows():
            k = _anahtar(r.strateji, r.sembol, r.tf)
            if k in satirlar:
                continue
            havuzlar.append((e, r.strateji, r.sembol, r.tf))
    gorulen, tekil = set(), []
    for x in havuzlar:                       # aynı anahtar iki dosyada olabilir: ilki
        k = _anahtar(*x[1:])
        if k not in gorulen:
            gorulen.add(k)
            tekil.append(x)
    idx = np.sort(np.random.default_rng(TOHUM).choice(len(tekil), size=min(N_RASTGELE, len(tekil)), replace=False))
    for i in idx:
        e, st, sm, tf = tekil[int(i)]
        ekle("tek", st, sm, tf, "D", e, "rastgele")
    # D (portföy): sağlamlıktan kalanlar
    for stem, d in portfoy_tum.items():
        for _, r in d[~d["saglam_mi"].astype(bool)].iterrows():
            if _anahtar(r.strateji, r.evren, r.tf) in satirlar and satirlar[_anahtar(r.strateji, r.evren, r.tf)]["C"]:
                continue
            ekle("portfoy", r.strateji, r.evren, r.tf, "D", stem, "saglamlik_kalan")
    df = pd.DataFrame(list(satirlar.values()))
    df["stil"] = [kayit.al(r.strateji).stil if r.tur == "tek" else "portfoy" for r in df.itertuples()]
    df["gruplar"] = ["".join(g for g in "ABCD" if r[g]) for _, r in df.iterrows()]
    return df


# ============================================================================ 2. ayar seçimi (KİLİT KAPALI)
def egitim_penceresi(stil: str, kilit_baslangic=KILIT) -> tuple:
    gun = wfp.EGITIM_GUN if stil == "portfoy" else wf.PENCERE_GUN[stil][0]
    return kilit_baslangic - pd.Timedelta(days=gun), kilit_baslangic


def _tek_veri(sembol, tf, veri_dizini, bitis, kilit_ac=False, gerekce=None):
    mumlar = tf_mumlari(sembol, tf, None, bitis, dizin=veri_dizini, kilit_ac=kilit_ac, gerekce=gerekce)
    try:
        fund = depo.funding_oku(sembol, None, bitis, dizin=veri_dizini, kilit_ac=kilit_ac, gerekce=gerekce)
    except FileNotFoundError:
        fund = None
    return mumlar, fund


def ayar_sec_tek(strateji: str, sembol: str, tf: str, veri_dizini=None, kilit_baslangic=KILIT,
                 min_islem: Optional[int] = None, izgara: bool = True, *, guncel: bool = False, gerekce: Optional[str] = None) -> dict:
    """KİLİT KAPALI (varsayılan). Tek-grafik ayar seçimi (modül belgesi). Veri `bitis=kilit_baslangic` ile kesilir (kilit_ac YOK).

    `guncel=True` (Aşama 4 hazırlık, kilit artık kullanılmış sayılır): veri sonuna kadar okunur (kilit_ac=True, `gerekce`
    zorunlu, günlüğe yazılır) ve eğitim penceresi VERİ SONUNDA biter (son mumun gününü izleyen gün 00:00, hariç); aday kümesi/skor/asgari işlem aynı."""
    stil = kayit.al(strateji).stil
    if guncel:
        mumlar, fund = _tek_veri(sembol, tf, veri_dizini, None, True, gerekce)
        if not len(mumlar):
            raise RuntimeError("güncel ayar seçimi: veri boş")
        kilit_baslangic = mumlar.index[-1].floor("D") + GUN      # eğitim bitişi (hariç) = son mumun gününün sonu
    else:
        mumlar, fund = _tek_veri(sembol, tf, veri_dizini, kilit_baslangic)
        if len(mumlar) and mumlar.index[-1] >= kilit_baslangic:
            raise RuntimeError("kilit sızıntısı: ayar seçiminde kilitli veri görüldü")
    adaylar, kurma_hata = wf.aday_listesi(strateji, izgara)
    kurallar = tarama.SEMBOL_KURALLARI.get(sembol, tarama.VARSAYILAN_KURAL)
    ay = wf.maliyet_ayarlari(kurallar)
    islemler, hatalar = {}, list(kurma_hata)
    n_kosu = 0
    for etiket, st in adaylar:
        try:
            r = backtest(funding.stratejiye_hazirla(st, mumlar, fund, sembol, tf), st, ay, fund)
        except Exception as e:  # noqa: BLE001  (aday hatası sayılır, satıra yazılır)
            hatalar.append((etiket, f"{type(e).__name__}: {e}"))
            continue
        n_kosu += 1
        if len(r.islemler):
            islemler[etiket] = r.islemler
    e0, e1 = egitim_penceresi(stil, kilit_baslangic)
    out = {"stil": stil, "egitim_bas": str(e0), "egitim_bit": str(e1), "n_aday": len(adaylar) + len(kurma_hata),
           "n_kosu": n_kosu, "n_aday_hatali": len(hatalar), "aday_hata_ornegi": hatalar[0][1][:160] if hatalar else "",
           "veri_son": str(mumlar.index[-1]) if len(mumlar) else ""}
    if n_kosu == 0:
        raise RuntimeError(f"hiç aday koşulamadı: {hatalar[0][1] if hatalar else 'aday yok'}")
    _, secimler = wf.secim_ve_oos(islemler, [(e0, e1, e1, e1 + GUN)], min_islem or wf.MIN_ISLEM[stil])
    s = secimler[0]
    out.update({"secilen_ayar": s["secilen"], "egitim_skor": s["egitim_pf"], "egitim_islem": s["egitim_islem"]})
    return out


def ayar_sec_portfoy(strateji: str, evren_ad: str, tf: str, veri_dizini=None, kilit_baslangic=KILIT,
                     evrenler: Optional[dict] = None, izgara: bool = True, *, guncel: bool = False,
                     gerekce: Optional[str] = None) -> dict:
    """KİLİT KAPALI (varsayılan). Portföy ayar seçimi (wf_portfoy ile aynı: 730 gün eğitim, günlük Sharpe, >=10 işlem, >=60 gün).
    `guncel=True`: veri sonuna kadar (kilit_ac=True, `gerekce` zorunlu); eğitim bitişi = evrenin son verisinin gününden
    bir sonraki gün 00:00 (son günlük getiri dahil)."""
    evren = tuple((evrenler or wfp.EVRENLER)[evren_ad])
    adaylar, atlanan = wfp.aday_listesi(strateji, evren, izgara)
    if not adaylar:
        raise RuntimeError("bu evrende uygun aday yok")
    if guncel:
        veriler, fundingler = pveri.veri_yukle(evren, tf, None, None, veri_dizini, kilit_ac=True, gerekce=gerekce)
        kilit_baslangic = max(v.index[-1] for v in veriler.values()).floor("D") + GUN
    else:
        veriler, fundingler = pveri.veri_yukle(evren, tf, None, kilit_baslangic, veri_dizini)     # kilit_ac YOK
        if any(len(v) and v.index[-1] >= kilit_baslangic for v in veriler.values()):
            raise RuntimeError("kilit sızıntısı: ayar seçiminde kilitli veri görüldü")
    ay = wfp.maliyet_ayarlari()
    hesaplar, hatalar = {}, []
    for etiket, st in adaylar:
        try:
            sembs = wfp.gerekli_semboller(st, evren)
            r = portfoy_backtest({x: veriler[x] for x in sembs}, st, ay, {x: fundingler[x] for x in sembs if x in fundingler})
        except Exception as e:  # noqa: BLE001  (aday hatası sayılır, satıra yazılır)
            hatalar.append((etiket, f"{type(e).__name__}: {e}"))
            continue
        gunluk = r.gunluk_ozsermaye.pct_change().fillna(0.0)
        q = r.pozisyon_gecmisi
        degisti = (q.diff().abs().fillna(0.0).sum(axis=1) > 0) if len(q) else pd.Series(dtype=bool)
        hesaplar[etiket] = wfp.AdayHesap(gunluk, r.islemler, float(r.maruziyet["brut"].mean()),
                                         [o["zaman"] for o in r.limit_olaylari], q.index[degisti.to_numpy()])
    if not hesaplar:
        raise RuntimeError(f"hiç aday koşulamadı: {hatalar[0][1] if hatalar else 'aday yok'}")
    e0, e1 = egitim_penceresi("portfoy", kilit_baslangic)
    _, _, secimler = wfp.secim_ve_oos(hesaplar, [(e0, e1, e1, e1 + 2 * GUN)], wfp.MIN_ISLEM_EGITIM, wfp.MIN_GUN_EGITIM)
    s = secimler[0]
    return {"stil": "portfoy", "egitim_bas": str(e0), "egitim_bit": str(e1), "n_aday": len(adaylar), "n_kosu": len(hesaplar),
            "n_aday_hatali": len(hatalar), "aday_hata_ornegi": hatalar[0][1][:160] if hatalar else "",
            "veri_son": str(max(v.index[-1] for v in veriler.values())), "secilen_ayar": s["secilen"],
            "egitim_skor": s["egitim_sharpe"], "egitim_islem": s["egitim_islem"]}


# ============================================================================ 3. kilitli dönem koşusu (KİLİT AÇIK)
def _ayar_bul_tek(strateji, etiket):
    adaylar, _ = wf.aday_listesi(strateji, True)
    for e, st in adaylar:
        if e == etiket:
            return st
    raise KeyError(f"seçilen ayar aday listesinde yok: {etiket}")


def kilit_kos_tek(strateji, sembol, tf, ayar_etiketi, veri_dizini=None, kilit_baslangic=KILIT,
                  kilit_ac=True, gerekce=GEREKCE) -> tuple:
    """Seçilen ayarı TAM veride koşar (kilit açık), işlemler yalnız `kilit_baslangic` ve sonrasında başlar.
    -> (metrik dict, işlem DataFrame)."""
    mumlar, fund = _tek_veri(sembol, tf, veri_dizini, None, kilit_ac, gerekce)
    st = _ayar_bul_tek(strateji, ayar_etiketi)
    kurallar = tarama.SEMBOL_KURALLARI.get(sembol, tarama.VARSAYILAN_KURAL)
    ay = wf.maliyet_ayarlari(kurallar)
    r = backtest(funding.stratejiye_hazirla(st, mumlar, fund, sembol, tf), st, ay, fund, islem_baslangic=kilit_baslangic)
    oos = r.islemler
    bit = mumlar.index[-1] + pd.Timedelta(1, "ns")
    n_bar = int((mumlar.index >= kilit_baslangic).sum())
    if len(oos):
        oos = oos[pd.DatetimeIndex(oos["giris_zamani"]) >= kilit_baslangic]
    m = wf.oos_metrikleri(oos, kilit_baslangic, bit)
    m.update(wf.al_tut_metrikleri(mumlar, kilit_baslangic, bit))
    if len(oos):
        m["medyan_r"] = float(np.median(np.nan_to_num(oos["r"].to_numpy(dtype=float))))
    m.update({"kilit_bar_sayisi": n_bar, "veri_son": str(mumlar.index[-1]), "ilk_giris": str(oos["giris_zamani"].min()) if len(oos) else ""})
    return m, oos


def kilit_kos_portfoy(strateji, evren_ad, tf, ayar_etiketi, veri_dizini=None, kilit_baslangic=KILIT,
                      kilit_ac=True, gerekce=GEREKCE, evrenler: Optional[dict] = None) -> tuple:
    """-> (metrik dict, işlem DataFrame, günlük DataFrame[oos_getiri, bh_getiri])."""
    evren = tuple((evrenler or wfp.EVRENLER)[evren_ad])
    adaylar, _ = wfp.aday_listesi(strateji, evren, True)
    st = dict(adaylar).get(ayar_etiketi)
    if st is None:
        raise KeyError(f"seçilen ayar aday listesinde yok: {ayar_etiketi}")
    veriler, fundingler = pveri.veri_yukle(evren, tf, None, None, veri_dizini, kilit_ac=kilit_ac, gerekce=gerekce)
    sembs = wfp.gerekli_semboller(st, evren)
    r = portfoy_backtest({x: veriler[x] for x in sembs}, st, wfp.maliyet_ayarlari(),
                         {x: fundingler[x] for x in sembs if x in fundingler}, islem_baslangic=kilit_baslangic)
    g = r.gunluk_ozsermaye.pct_change().fillna(0.0)
    g.index = pd.DatetimeIndex(g.index).floor("D")
    g = g.groupby(level=0).last()
    getiri = g[g.index >= kilit_baslangic].astype(float)
    oos = r.islemler
    if len(oos):
        oos = oos[pd.DatetimeIndex(oos["giris_zamani"]) >= kilit_baslangic]
    bit = max(v.index[-1] for v in veriler.values()) + pd.Timedelta(1, "ns")
    m = wfp.oos_metrikleri(getiri, oos)
    bh = wfp.al_tut_getirisi(veriler, evren, kilit_baslangic, bit)
    m.update(wfp.al_tut_metrikleri(bh))
    if len(oos):
        m["medyan_r"] = float(np.median(np.nan_to_num(oos["r"].to_numpy(dtype=float))))
        m["ortalama_r"] = float(np.nan_to_num(oos["r"].to_numpy(dtype=float)).mean())
        m["toplam_r"] = float(np.nan_to_num(oos["r"].to_numpy(dtype=float)).sum())
    m.update({"kilit_bar_sayisi": int(len(getiri)), "veri_son": str(bit - pd.Timedelta(1, "ns")),
              "ilk_giris": str(oos["giris_zamani"].min()) if len(oos) else ""})
    gun = pd.DataFrame({"oos_getiri": getiri, "bh_getiri": bh.reindex(getiri.index)})
    return m, oos, gun


# ============================================================================ 4. çalıştırıcı
_AY: dict = {}


def _isci(ayar):
    _AY.clear()
    _AY.update(ayar)


def _gorev_ayar(g: dict) -> dict:
    t0 = time.perf_counter()
    satir = {"kimlik": g["kimlik"], "tur": g["tur"], "strateji": g["strateji"], "sembol": g["sembol"], "tf": g["tf"],
             "hata": ""}
    try:
        if g["tur"] == "tek":
            satir.update(ayar_sec_tek(g["strateji"], g["sembol"], g["tf"], _AY.get("veri_dizini")))
        else:
            satir.update(ayar_sec_portfoy(g["strateji"], g["sembol"], g["tf"], _AY.get("veri_dizini")))
    except Exception as e:  # noqa: BLE001  (satıra yazılır)
        satir["hata"] = f"{type(e).__name__}: {e}"
    satir["sure_sn"] = time.perf_counter() - t0
    return satir


def _kid(kimlik: str) -> str:
    return kimlik.replace("|", "--")


def _gorev_kilit(g: dict) -> dict:
    t0 = time.perf_counter()
    cikti = Path(_AY["cikti"])
    satir = {"kimlik": g["kimlik"], "hata": "", "secilen_ayar": g["secilen_ayar"]}
    try:
        if g["tur"] == "tek":
            m, oos = kilit_kos_tek(g["strateji"], g["sembol"], g["tf"], g["secilen_ayar"], _AY.get("veri_dizini"))
            if len(oos):
                (cikti / "islemler").mkdir(parents=True, exist_ok=True)
                oos.to_parquet(cikti / "islemler" / f"{_kid(g['kimlik'])}.parquet", index=False)
        else:
            m, oos, gun = kilit_kos_portfoy(g["strateji"], g["sembol"], g["tf"], g["secilen_ayar"], _AY.get("veri_dizini"))
            (cikti / "gunluk").mkdir(parents=True, exist_ok=True)
            gun.to_parquet(cikti / "gunluk" / f"{_kid(g['kimlik'])}.parquet")
            if len(oos):
                (cikti / "islemler").mkdir(parents=True, exist_ok=True)
                oos.to_parquet(cikti / "islemler" / f"{_kid(g['kimlik'])}.parquet", index=False)
        satir.update(m)
    except Exception as e:  # noqa: BLE001  (satıra yazılır)
        satir["hata"] = f"{type(e).__name__}: {e}"
    satir["sure_sn"] = time.perf_counter() - t0
    return satir


def _yaz(df: pd.DataFrame, yol: Path):
    gecici = yol.with_suffix(".tmp")
    df.to_parquet(gecici, index=False)
    gecici.replace(yol)


def _paralel(gorevler: list, fn, yol_pq: Path, ayar: dict, surec: int, ilerleme=True) -> pd.DataFrame:
    """Biten görevler yol_pq'ya biriktirilir; var olan kimlikler atlanır (kaldığı yerden devam)."""
    onceki = pd.read_parquet(yol_pq) if yol_pq.exists() else pd.DataFrame()
    bitmis = set(onceki["kimlik"]) if len(onceki) else set()
    kalan = [g for g in gorevler if g["kimlik"] not in bitmis]
    yeni = []
    t0 = time.perf_counter()
    if ilerleme:
        print(f"[kilit] {yol_pq.name}: toplam {len(gorevler)}, bitmiş {len(bitmis)}, kalan {len(kalan)}", flush=True)

    def kaydet():
        _yaz(pd.concat([onceki, pd.DataFrame(yeni)], ignore_index=True) if len(onceki) else pd.DataFrame(yeni), yol_pq)

    def ekle(s):
        yeni.append(s)
        if len(yeni) % 5 == 0:
            kaydet()
        if ilerleme:
            print(f"[kilit] {len(yeni)}/{len(kalan)} {s['kimlik']} {s['hata'] or 'ok'} ({time.perf_counter() - t0:.0f} sn)", flush=True)

    if kalan:
        if surec <= 1:
            _isci(ayar)
            for g in kalan:
                ekle(fn(g))
        else:
            with mp.get_context("fork").Pool(min(surec, len(kalan)), _isci, (ayar,)) as havuz:
                for s in havuz.imap_unordered(fn, kalan, chunksize=1):
                    ekle(s)
        kaydet()
    return pd.read_parquet(yol_pq) if yol_pq.exists() else pd.DataFrame()


def _siralama(gruplar: pd.DataFrame) -> list:
    g = gruplar.sort_values(["tur", "sembol", "tf", "strateji"]).to_dict("records")
    return g


def asama_gruplar(cikti: Path = CIKTI) -> pd.DataFrame:
    cikti.mkdir(parents=True, exist_ok=True)
    df = gruplari_kur()
    df.to_csv(cikti / "gruplar.csv", index=False)
    print(f"[kilit] gruplar.csv: {len(df)} satır; A={int(df.A.sum())} B={int(df.B.sum())} C={int(df.C.sum())} D={int(df.D.sum())}")
    return df


def asama_ayar(cikti: Path = CIKTI, surec: int = 4, veri_dizini=None) -> pd.DataFrame:
    """KİLİT KAPALI. gruplar.csv gerekir."""
    gruplar = pd.read_csv(cikti / "gruplar.csv")
    s = _paralel(_siralama(gruplar), _gorev_ayar, cikti / "ayar_ham.parquet", {"veri_dizini": veri_dizini}, surec)
    out = gruplar[["kimlik", "gruplar"]].merge(s, on="kimlik", how="left")
    out.to_csv(cikti / "secilen_ayarlar.csv", index=False)
    print(f"[kilit] secilen_ayarlar.csv: {len(out)} satır; hata {int((out['hata'].fillna('') != '').sum())}; "
          f"ayarsız {int((out['hata'].fillna('') == '').sum() - out['secilen_ayar'].notna().sum())}")
    return out


def asama_kilit(cikti: Path = CIKTI, surec: int = 4, veri_dizini=None) -> pd.DataFrame:
    """KİLİT AÇILIR. Önkoşul: gruplar.csv ve secilen_ayarlar.csv (kilit kapalıyken yazılmış) var ve tüm gruplar kapsanıyor."""
    gp, ap = cikti / "gruplar.csv", cikti / "secilen_ayarlar.csv"
    if not gp.exists() or not ap.exists():
        raise RuntimeError("gruplar.csv ve secilen_ayarlar.csv kilit açılmadan ÖNCE yazılmış olmalı")
    gruplar, ayarlar = pd.read_csv(gp), pd.read_csv(ap)
    if set(gruplar["kimlik"]) - set(ayarlar["kimlik"]):
        raise RuntimeError("secilen_ayarlar.csv tüm grup satırlarını kapsamıyor")
    kilit.kilit_acilisi_yaz("*", "kilit testi başlangıcı (tüm adaylar)", GEREKCE)
    gorev = []
    for g in _siralama(gruplar):
        a = ayarlar[ayarlar["kimlik"] == g["kimlik"]].iloc[0]
        if isinstance(a["secilen_ayar"], str) and a["secilen_ayar"] and (pd.isna(a["hata"]) or a["hata"] == ""):
            g["secilen_ayar"] = a["secilen_ayar"]
            gorev.append(g)
    return _paralel(gorev, _gorev_kilit, cikti / "kilit_ham.parquet", {"veri_dizini": veri_dizini, "cikti": str(cikti)}, surec)


# ============================================================================ 5. değerlendirme
def _wf_beklenti(gruplar: pd.DataFrame, kok: Path = KOK) -> pd.DataFrame:
    """Her satır için walk-forward OOS beklentisi (wf_* sütunları)."""
    onbellek, satirlar = {}, []
    for g in gruplar.itertuples():
        if g.tur == "tek":
            yol = kok / "sonuclar" / "wf" / f"{g.wf_dosya}.csv"
            anah = ["strateji", "sembol", "tf"]
        else:
            yol = kok / "sonuclar" / "wf_portfoy" / f"{g.wf_dosya}.csv"
            anah = ["strateji", "evren", "tf"]
        if yol not in onbellek:
            onbellek[yol] = pd.read_csv(yol)
        d = onbellek[yol]
        r = d[(d.strateji == g.strateji) & (d[anah[1]] == g.sembol) & (d.tf == g.tf)]
        o = {"kimlik": g.kimlik}
        if len(r):
            r = r.iloc[-1]
            o.update({"wf_net": r.get("net_getiri"), "wf_pf": r.get("profit_factor"), "wf_islem": r.get("islem_sayisi"),
                      "wf_sharpe": r.get("sharpe"), "wf_ortalama_r": r.get("ortalama_r"), "wf_max_dusus": r.get("max_dusus"),
                      "wf_bh_sharpe": r.get("bh_sharpe")})
        satirlar.append(o)
    return pd.DataFrame(satirlar)


def aday_karari(net, pf, islem, hata="", ayar_var=True) -> tuple:
    """ON_KAYIT: net > 0 ve PF >= 1.0. -> (gecti, neden)."""
    if hata:
        return False, "hata"
    if not ayar_var:
        return False, "ayar seçilemedi (eğitimde yeterli işlem yok)"
    if not islem or islem <= 0:
        return False, "kilitli dönemde işlem yok"
    if not (isinstance(net, (int, float)) and net > 0):
        return False, "net <= 0"
    if not (pf >= 1.0):          # inf >= 1.0 doğru
        return False, "PF < 1.0"
    return True, ""


def sonuc_tablosu(cikti: Path = CIKTI, kok: Path = KOK) -> pd.DataFrame:
    gruplar = pd.read_csv(cikti / "gruplar.csv")
    ayar = pd.read_csv(cikti / "secilen_ayarlar.csv")
    ham = pd.read_parquet(cikti / "kilit_ham.parquet") if (cikti / "kilit_ham.parquet").exists() else pd.DataFrame({"kimlik": []})
    ham = ham.rename(columns={"hata": "kilit_hata", "secilen_ayar": "_sa", "sure_sn": "kilit_sure_sn"})
    ayar_k = ayar.rename(columns={"hata": "ayar_hata"})[["kimlik", "secilen_ayar", "egitim_skor", "egitim_islem", "egitim_bas",
                                                          "egitim_bit", "n_aday", "n_kosu", "ayar_hata"]]
    df = gruplar.merge(ayar_k, on="kimlik", how="left").merge(ham.drop(columns=["_sa"], errors="ignore"), on="kimlik", how="left")
    df = df.merge(_wf_beklenti(gruplar, kok), on="kimlik", how="left")
    df["ayar_hata"] = df["ayar_hata"].fillna("")
    df["kilit_hata"] = df["kilit_hata"].fillna("") if "kilit_hata" in df else ""
    df["hata"] = (df["ayar_hata"] + " " + df["kilit_hata"]).str.strip()
    df = df.rename(columns={"net_getiri": "kilit_net", "profit_factor": "kilit_pf", "islem_sayisi": "kilit_islem",
                            "kazanma_orani": "kilit_kazanma", "max_dusus": "kilit_max_dusus", "toplam_r": "kilit_toplam_r",
                            "ortalama_r": "kilit_ortalama_r", "medyan_r": "kilit_medyan_r", "sharpe": "kilit_sharpe"})
    for c in ("kilit_net", "kilit_pf", "kilit_islem", "kilit_max_dusus", "kilit_sharpe", "kilit_ortalama_r", "kilit_medyan_r"):
        if c not in df:
            df[c] = np.nan
    karar = [aday_karari(r.kilit_net, r.kilit_pf, r.kilit_islem if pd.notna(r.kilit_islem) else 0, r.hata,
                         isinstance(r.secilen_ayar, str) and bool(r.secilen_ayar)) for r in df.itertuples()]
    df["gecti"] = [k[0] for k in karar]
    df["neden"] = [k[1] for k in karar]
    df["karar"] = np.where(df["gecti"], "gecti", "kaldi")
    df["pf_bilgi_1_2"] = df["kilit_pf"] >= 1.2
    df["pf_fark"] = df["kilit_pf"] - pd.to_numeric(df["wf_pf"], errors="coerce")
    df["bh_getiri_kilit"] = df.get("bh_getiri")
    return df


def ayirt_edicilik(df: pd.DataFrame) -> dict:
    out: dict = {}
    tek = df[df.tur == "tek"]
    c, d = tek[tek.C], tek[tek.D]

    def med(x, col):
        v = pd.to_numeric(x[col], errors="coerce").dropna()
        return float(v.median()) if len(v) else math.nan

    for ad, kume in (("C", c), ("D", d), ("D_saglamlik_kalan", d[d.d_kaynak == "saglamlik_kalan"]), ("D_rastgele", d[d.d_kaynak == "rastgele"])):
        islemli = kume[pd.to_numeric(kume["kilit_islem"], errors="coerce").fillna(0) >= 1]
        out[f"tek_{ad}"] = {"n": int(len(kume)), "n_islemli": int(len(islemli)), "medyan_ortalama_r": med(islemli, "kilit_ortalama_r"),
                            "medyan_pf": med(islemli, "kilit_pf"), "gecen_oran": float(kume["gecti"].mean()) if len(kume) else math.nan,
                            "medyan_ortalama_r_islemsiz_0": float(pd.to_numeric(kume["kilit_ortalama_r"], errors="coerce").fillna(0.0).median()) if len(kume) else math.nan}
    out["tek_C_gt_D"] = bool(out["tek_C"]["medyan_ortalama_r"] > out["tek_D"]["medyan_ortalama_r"]) \
        if np.isfinite(out["tek_C"]["medyan_ortalama_r"]) and np.isfinite(out["tek_D"]["medyan_ortalama_r"]) else None
    pf = df[df.tur == "portfoy"]
    for ad, kume in (("C", pf[pf.C]), ("D", pf[pf.D])):
        out[f"portfoy_{ad}"] = {"n": int(len(kume)), "medyan_sharpe": med(kume, "kilit_sharpe"),
                                "gecen_oran": float(kume["gecti"].mean()) if len(kume) else math.nan}
    out["portfoy_C_gt_D"] = bool(out["portfoy_C"]["medyan_sharpe"] > out["portfoy_D"]["medyan_sharpe"]) \
        if np.isfinite(out["portfoy_C"]["medyan_sharpe"]) and np.isfinite(out["portfoy_D"]["medyan_sharpe"]) else None
    # Spearman: WF OOS PF ~ kilitli PF (tüm A+B+C+D satırları)
    x = pd.DataFrame({"wf": pd.to_numeric(df["wf_pf"], errors="coerce"), "kilit": pd.to_numeric(df["kilit_pf"], errors="coerce"),
                      "n": pd.to_numeric(df["kilit_islem"], errors="coerce"), "tur": df["tur"]}).dropna(subset=["wf", "kilit"])

    def spearman(z):
        return float(z["wf"].rank().corr(z["kilit"].rank())) if len(z) > 2 else math.nan

    out["spearman_tum"] = {"n": int(len(x)), "rho": spearman(x)}
    out["spearman_tek"] = {"n": int((x.tur == "tek").sum()), "rho": spearman(x[x.tur == "tek"])}
    out["spearman_en_az_10_islem"] = {"n": int((x.n >= 10).sum()), "rho": spearman(x[x.n >= 10])}
    return out


def set_testi(df: pd.DataFrame, cikti: Path = CIKTI) -> pd.DataFrame:
    """A grubu: tek-grafik kolları secim.yeniden_oyna ile tek kasada (sert limitler), portföy kolu günlük getiriyle
    %50/%50 (secim.harmanla)."""
    A = df[df.A]
    tek = A[A.tur == "tek"]
    port = A[A.tur == "portfoy"]
    satirlar = []
    parcalar = {}
    for r in tek.itertuples():
        yol = cikti / "islemler" / f"{_kid(r.kimlik)}.parquet"
        if yol.exists():
            parcalar[r.kimlik] = (pd.read_parquet(yol), r.sembol)
    tek_getiri = None
    if parcalar:
        bit = max(pd.Timestamp(v) for v in tek["veri_son"].dropna())
        oy = sec.yeniden_oyna(sec.islem_tablosu_hazirla(parcalar), sec.OynatmaAyari(), bas=KILIT, bit=bit)
        tek_getiri = oy["getiri"]
        o = sec.seri_ozeti(tek_getiri)
        satirlar.append({"kol": "tek_grafik", "net": o["getiri"], "sharpe": o["sharpe"], "max_dusus": o["max_dusus"], "gun": o["gun"],
                         "islem_kabul": oy["sayac"]["giris_kabul"], "islem_reddedilen": oy["sayac"]["reddedilen"],
                         "kirpilan": oy["sayac"]["kirpilan"], "gunluk_limit": oy["sayac"]["gunluk_limit_olayi"],
                         "kill": oy["sayac"]["kill_olayi"], "n_kol": len(parcalar), "n_kol_islemsiz": int(len(tek) - len(parcalar))})
    port_getiri = None
    gunluk = []
    for r in port.itertuples():
        yol = cikti / "gunluk" / f"{_kid(r.kimlik)}.parquet"
        if yol.exists():
            gunluk.append(pd.read_parquet(yol)["oos_getiri"].astype(float).rename(r.kimlik))
    if gunluk:
        g = pd.concat(gunluk, axis=1)
        g = g.loc[g.dropna().index.min():g.dropna().index.max()] if g.dropna().shape[0] else g
        port_getiri = g.mean(axis=1)
        o = sec.seri_ozeti(port_getiri)
        satirlar.append({"kol": "portfoy", "net": o["getiri"], "sharpe": o["sharpe"], "max_dusus": o["max_dusus"], "gun": o["gun"],
                         "n_kol": len(gunluk), "n_kol_islemsiz": int(len(port) - len(gunluk))})
    if tek_getiri is not None and port_getiri is not None:
        tg = tek_getiri.copy()
        tg.index = pd.DatetimeIndex(tg.index).tz_convert("UTC") if pd.DatetimeIndex(tg.index).tz is not None else pd.DatetimeIndex(tg.index).tz_localize("UTC")
        pg = port_getiri.copy()
        pg.index = pd.DatetimeIndex(pg.index).tz_convert("UTC") if pd.DatetimeIndex(pg.index).tz is not None else pd.DatetimeIndex(pg.index).tz_localize("UTC")
        h = sec.harmanla(tg, pg, 0.5)
        o = h["ozet"]
        gec = bool(o["getiri"] > 0 and o["max_dusus"] <= SET_LIMIT["max_dusus"] and o["sharpe"] > 0)
        satirlar.append({"kol": "set_harman_50_50", "net": o["getiri"], "sharpe": o["sharpe"], "max_dusus": o["max_dusus"],
                         "gun": o["gun"], "n_kol": len(parcalar) + len(gunluk), "gecti": gec,
                         "karar": "gecti" if gec else "kaldi",
                         "yillik": json.dumps(h["yillik"])})
    elif tek_getiri is not None or port_getiri is not None:
        satirlar.append({"kol": "set_harman_50_50", "karar": "kaldi", "gecti": False, "neden": "bir kol hesaplanamadı"})
    return pd.DataFrame(satirlar)


# ============================================================================ 6. rapor
def _p(x, d=1):
    return "-" if x is None or (isinstance(x, float) and not np.isfinite(x)) or pd.isna(x) else f"{x * 100:.{d}f}%"


def _f(x, d=2):
    return "-" if x is None or pd.isna(x) or (isinstance(x, float) and not np.isfinite(x) and not np.isinf(x)) else f"{x:.{d}f}"


def rapor_yaz(df: pd.DataFrame, st: pd.DataFrame, ay: dict, cikti: Path = CIKTI) -> str:
    L = []
    acilis = KOK / "sonuclar" / "kilit_acilis.jsonl"
    n_ac = sum(1 for _ in open(acilis, encoding="utf-8")) if acilis.exists() else 0
    L.append("# Kilitli dönem testi — sonuç raporu\n")
    L.append(f"Kilitli dönem: {KILIT.date()} -> veri sonu. Yöntem ve ölçütler `ON_KAYIT.md`'de koşudan önce sabitlendi; "
             "sonuçlara bakılarak hiçbir şey değiştirilmedi.\n")
    L.append(f"Kilit açılış kaydı: `sonuclar/kilit_acilis.jsonl` ({n_ac} satır; her veri okuması + başlangıç kaydı). "
             f"Gerekçe: \"{GEREKCE}\".\n")
    sa = st[st.kol == "set_harman_50_50"]
    A_ = df[df.A]
    set_gecti = bool(len(sa) and sa.iloc[0].get("karar") == "gecti")
    L.append("## Kısa özet (sade)\n")
    L.append(f"- A grubu (final set, {len(A_)} aday): {int(A_.gecti.sum())} tanesi tek tek ölçütü geçti (net > 0 ve PF >= 1.0), "
             f"{int((~A_.gecti).sum())} tanesi kaldı.")
    L.append(f"- Set (tek kasa, sert limitler, portföy kolu %50/%50): **{'GEÇTİ' if set_gecti else 'KALDI'}**.")
    for ad in ("B", "C", "D"):
        k = df[df[ad]]
        L.append(f"- {ad} grubu: {len(k)} satırın {int(k.gecti.sum())} tanesi geçti ({_p(k.gecti.mean())}).")
    tc, td = ay["tek_C"]["medyan_ortalama_r"], ay["tek_D"]["medyan_ortalama_r"]
    L.append(f"- Elemelerimiz ayırt ediyor mu? Tek-grafikte C'nin medyan işlem başı R'si {_f(tc, 3)}, D'ninki {_f(td, 3)} "
             f"-> ölçüt (C > D): **{'sağlandı' if ay['tek_C_gt_D'] else 'SAĞLANMADI'}**. Portföyde medyan Sharpe C {_f(ay['portfoy_C']['medyan_sharpe'])} "
             f"(n={ay['portfoy_C']['n']}), D {_f(ay['portfoy_D']['medyan_sharpe'])} (n={ay['portfoy_D']['n']}).")
    L.append(f"- Walk-forward PF ile kilitli PF arasındaki Spearman korelasyonu: {_f(ay['spearman_tum']['rho'], 3)} "
             f"(n={ay['spearman_tum']['n']}); 0'a yakınsa walk-forward başarısı kilitli dönemi öngörmemiş demektir.")
    L.append("- ON_KAYIT 'sonuca göre': " + ("A seti ölçütü geçti -> Aşama 3 (Pano) ve Aşama 4 (paper trading) bu setle başlar."
                                          if set_gecti else "A seti ölçütü geçmedi -> kilitli döneme bakarak yeniden seçim YAPILMAZ; kullanıcıyla karar."))
    L.append("")
    L.append("## Dürüstlük notları\n")
    L.append("- Ayar seçimi kilit KAPALIYKEN, yalnız 2025-11-01 öncesi veriyle yapıldı (`secilen_ayarlar.csv`, `gruplar.csv` kilit açılmadan önce yazıldı).")
    L.append("- Her aşama bir kez koşuldu; sonuç görüldükten sonra yöntem/ölçüt/liste değişmedi, kod hatası yüzünden yeniden koşu olmadı.")
    L.append("- Gruplar örtüşür (A ve B, C'nin alt kümesidir). D-portföy tanımı ON_KAYIT'ta açık değildi; koşudan önce "
             "'sağlamlıktan kalan portföy satırları' olarak belirlendi (modül belgesi).")
    L.append("- Araştırma modu motoru (walk-forward ile aynı): günlük -%3 ve %20 kill switch işlemi durdurmaz. "
             "Portföy kollarının max düşüşü bu yüzden %20'yi aşabilir (bkz. tablo); set testinde sert limitler yeniden oynatıcıyla uygulandı.")
    L.append("- Örneklem küçük: A kollarında 12-55 işlem; tek yıllık tek dönem. Sonuç kesin hüküm değil, bir tanık.\n")
    L.append("## Set sonucu (A grubu, tek kasa, sert limitler)\n")
    if len(sa):
        r = sa.iloc[0]
        L.append(f"**Karar: {str(r.get('karar', '-')).upper()}** (ölçüt: net > 0, max düşüş <= %20, Sharpe > 0)\n")
    L.append("| kol | net | Sharpe | max düşüş | gün |\n|---|---|---|---|---|")
    for r in st.itertuples():
        L.append(f"| {r.kol} | {_p(getattr(r, 'net', np.nan))} | {_f(getattr(r, 'sharpe', np.nan))} | {_p(getattr(r, 'max_dusus', np.nan))} | {getattr(r, 'gun', '')} |")
    L.append("")
    A = df[df.A].sort_values(["tur", "kimlik"])
    L.append("## A grubu (final set)\n")
    L.append("| strateji | sembol | tf | seçilen ayar | işlem | net | PF | max düşüş | WF PF | WF net | al-tut | ölçüt |\n|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in A.itertuples():
        bh = r.bh_getiri if pd.notna(getattr(r, "bh_getiri", np.nan)) else np.nan
        L.append(f"| {r.strateji} | {r.sembol} | {r.tf} | {str(r.secilen_ayar)[:40]} | {_f(r.kilit_islem, 0)} | {_p(r.kilit_net)} | {_f(r.kilit_pf)} | "
                 f"{_p(r.kilit_max_dusus)} | {_f(r.wf_pf)} | {_p(r.wf_net)} | {_p(bh)} | {r.karar}{' (' + r.neden + ')' if r.neden else ''} |")
    L.append("")
    for ad in ("B", "C", "D"):
        k = df[df[ad]]
        isl = k[pd.to_numeric(k["kilit_islem"], errors="coerce").fillna(0) >= 1]
        L.append(f"## {ad} grubu özeti\n")
        L.append(f"- Satır: {len(k)}; geçen: {int(k.gecti.sum())} ({_p(k.gecti.mean())}); işlemli: {len(isl)}; "
                 f"hatalı: {int((k.hata.fillna('') != '').sum())}; ayarsız: {int(k.secilen_ayar.isna().sum())}")
        L.append(f"- Medyan kilitli PF (işlemli): {_f(isl.kilit_pf.median())}; medyan işlem başı R: {_f(isl.kilit_ortalama_r.median(), 3)}\n")
    L.append("## Ayırt edicilik (C vs D)\n")
    for k, v in ay.items():
        L.append(f"- {k}: `{json.dumps(v, ensure_ascii=False, default=str)}`")
    L.append("")
    L.append("## Tüm satırlar\n")
    L.append("Ayrıntı: `sonuc.csv` (her satır), `set.csv`, `secilen_ayarlar.csv`, `gruplar.csv`.\n")
    (cikti / "RAPOR.md").write_text("\n".join(L), encoding="utf-8")
    return "\n".join(L)


def asama_rapor(cikti: Path = CIKTI) -> tuple:
    df = sonuc_tablosu(cikti)
    df.to_csv(cikti / "sonuc.csv", index=False)
    ay = ayirt_edicilik(df)
    (cikti / "ayirt_edicilik.json").write_text(json.dumps(ay, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    st = set_testi(df, cikti)
    st.to_csv(cikti / "set.csv", index=False)
    rapor_yaz(df, st, ay, cikti)
    return df, st, ay


def main(argv=None):
    ap = argparse.ArgumentParser(description="Kilitli dönem testi (Katman 4) — ON_KAYIT.md")
    ap.add_argument("--asama", required=True, choices=["gruplar", "ayar", "kilit", "rapor"])
    ap.add_argument("--surec", type=int, default=4)
    a = ap.parse_args(argv)
    surec = min(a.surec, 4)
    if a.asama == "gruplar":
        asama_gruplar()
    elif a.asama == "ayar":
        asama_ayar(surec=surec)
    elif a.asama == "kilit":
        asama_kilit(surec=surec)
    else:
        asama_rapor()


if __name__ == "__main__":
    main()
