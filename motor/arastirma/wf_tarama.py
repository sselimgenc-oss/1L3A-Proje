"""Hızlı walk-forward taraması (Aşama 2, Katman 3): her (strateji, sembol, tf) için OOS sonucu.

Yöntem (koşudan önce sabitlendi; sonuca bakılarak değiştirilmez)
  1. Aday ayar kümesi tarama.py ile aynı (varsayılan + kart + dış + ızgara). Aynı etkin ayara (parametre + çıkış
     ayarı) düşen kopyalar TEK aday sayılır. Her aday kilit öncesi TÜM veride BİR KEZ koşulur
     (limit_modu="olc", tarama ile aynı motor ayarı ve sembol kuralları); işlem listesi saklanır.
  2. Pencereler stile göre sabit uzunlukta kayar, test pencereleri uç uca gelir, örtüşmez (PENCERE_GUN):
       swing: eğitim 730 gün / test 180 gün;  daytrade ve scalp: eğitim 365 gün / test 90 gün.
  3. Her eğitim penceresinde aday skoru yalnız GİRİŞ ZAMANI eğitim penceresinde olan işlemlerin R değerlerinden
     hesaplanır: işlem sayısı >= MIN_ISLEM (swing 15, diğer 30) olanlar arasında PF(R) = (+R toplamı)/(-R toplamı)
     en yüksek olan seçilir; eşitlikte daha çok işlem; hâlâ eşitse aday sırası. Koşulu sağlayan yoksa o test
     penceresinde işlem yok. Seçilen adayın GİRİŞ ZAMANI test penceresinde olan işlemleri OOS'a eklenir.
     OOS işlemleri seçimde asla kullanılmaz.
  4. Pencere sınırı kuralları: eğitim skoruna yalnız girişi eğitim penceresinde VE kapanışı eğitim bitişinden
     önce/eşit olan işlemler girer (eğitim bittiğinde sonucu bilinmeyen açık işlem skora girmez; sızıntı yok).
     Test işlemleri GİRİŞ zamanıyla atanır; pozisyon test sınırını aşıp kapanabilir. Yaklaşıklıklar: aday tam
     veride koşulduğundan test başında önceki pencereden açık pozisyon yeni girişi engelleyebilir; ardışık
     pencerelerde farklı adaylar seçilirse OOS işlemleri zamanda çakışabilir (R toplamında yok sayılır).
  5. OOS metrikleri R üzerinden (sabit risk, işlem başı %1 sermaye, bileşik): net_getiri, PF(R), en iyi %5 hariç
     PF, max düşüş (işlem bazlı eğri), günlük sharpe (OOS aralığındaki tüm UTC günleri), long/short PF, yıl bazında
     PF/net (giriş yılına göre). Karar 13: eleme.degerlendir. Al-tut: aynı OOS aralığında 1x sembol.
  6. Deneme kaydı: (strateji, sembol, tf) başına bir satır: kombinasyon = aday sayısı, toplam_kosu = başarılı
     backtest sayısı; yalnız bu çağrıda YENİ biten görevler yazılır (devam eden koşuda çift sayma yok).

Kilit (karar 20): veri yalnız depo.mum_oku / depo.funding_oku ile okunur, kilit_ac yok.

Maliyet çarpanı (Katman 3b sağlamlık stresi): `maliyet_carpani` (varsayılan 1.0 = değişiklik yok) komisyon
(taker+maker) ve kaymayı (kayma_bps, stop_kayma_bps) çarpar; funding'e dokunmaz. Aday kümesi, pencere ve skor aynıdır.

CLI: python -m motor.arastirma.wf_tarama --etiket k3_kripto [--semboller ...] [--stratejiler ...] [--surec 4]
     [--umutsuzlari-atla] [--hatalari-yeniden] [--maliyet-carpani 1.0]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import multiprocessing as mp
import time
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from motor.arastirma import tarama
from motor.backtest import deneme_kaydi, eleme
from motor.backtest.motor import MotorAyarlari, backtest
from motor.backtest.walk_forward import pencereler_uret
from motor.strateji import funding, kayit
from motor.veri import depo
from motor.veri.yeniden_ornekle import tf_mumlari, yeniden_ornekle

KOK = Path(__file__).resolve().parents[2]
CIKTI_DIZINI = KOK / "sonuclar" / "wf"

# stil -> (eğitim gün, test gün); sabit uzunlukta kayan pencere, test pencereleri uç uca.
PENCERE_GUN = {"swing": (730, 180), "daytrade": (365, 90), "scalp": (365, 90)}
# stil -> eğitim penceresinde adayın seçilebilmesi için asgari işlem sayısı
MIN_ISLEM = {"swing": 15, "daytrade": 30, "scalp": 30}
RISK = 0.01                      # OOS özsermaye modeli: işlem başı sermayenin %1'i (R ile bileşik)
YILLAR = tuple(range(2020, 2026))
KAYDET_ARALIGI = 10


# ---------------------------------------------------------------------------- saf yardımcılar
def pf_hesapla(r) -> float:
    """PF = (+R toplamı)/(-R toplamı); kayıp yoksa kazanç varsa inf, yoksa nan."""
    r = np.asarray(r, dtype=float)
    k, z = r[r > 0].sum(), -r[r < 0].sum()
    if z > 0:
        return float(k / z)
    return math.inf if k > 0 else math.nan


class AdayIslemleri:
    """Bir adayın işlem listesi + pencere sorguları için kümülatif toplamlar (giriş zamanına göre)."""

    def __init__(self, islemler: pd.DataFrame):
        d = islemler.sort_values("giris_zamani", kind="stable").reset_index(drop=True)
        d["r"] = pd.to_numeric(d["r"], errors="coerce")
        self.n_nan_r = int(d["r"].isna().sum())
        d["r"] = d["r"].fillna(0.0)
        self.df = d
        self.giris = pd.DatetimeIndex(d["giris_zamani"])
        self.cikis = pd.DatetimeIndex(d["cikis_zamani"])
        if not self.cikis.is_monotonic_increasing:       # tek pozisyon: kapanışlar da giriş sırasındadır
            raise ValueError("işlemler çakışıyor: kapanış zamanları sıralı değil")
        r = d["r"].to_numpy(dtype=float)
        self._poz = np.r_[0.0, np.cumsum(np.where(r > 0, r, 0.0))]
        self._neg = np.r_[0.0, np.cumsum(np.where(r < 0, -r, 0.0))]

    def aralik(self, bas, bit) -> tuple:
        """Giriş zamanı [bas, bit) olan işlemlerin satır aralığı."""
        return int(self.giris.searchsorted(bas, "left")), int(self.giris.searchsorted(bit, "left"))

    def skor(self, bas, bit) -> tuple:
        """Eğitim skoru (işlem sayısı, PF(R)): girişi [bas, bit) ve kapanışı <= bit olan işlemler."""
        i, j = self.aralik(bas, bit)
        j = max(i, min(j, int(self.cikis.searchsorted(bit, "right"))))
        k, z = self._poz[j] - self._poz[i], self._neg[j] - self._neg[i]
        pf = k / z if z > 0 else (math.inf if k > 0 else math.nan)
        return j - i, float(pf)

    def dilim(self, bas, bit) -> pd.DataFrame:
        i, j = self.aralik(bas, bit)
        return self.df.iloc[i:j]


def secim_ve_oos(adaylar: dict, pencereler: list, min_islem: int) -> tuple:
    """adaylar: {etiket: DataFrame(işlemler)} (sıra önemli: eşitlikte önce gelen). pencereler:
    [(egitim_bas, egitim_bit, test_bas, test_bit)]. Seçim YALNIZ eğitim penceresindeki girişlerle yapılır.
    -> (oos_islemleri DataFrame, secimler [{pencere, test_bas, test_bit, secilen, egitim_pf, egitim_islem}])"""
    nesneler = {e: AdayIslemleri(df) for e, df in adaylar.items()}
    parcalar, secimler = [], []
    for w, (e0, e1, t0, t1) in enumerate(pencereler):
        en_iyi, en_anahtar = None, None
        for sira, (etiket, a) in enumerate(nesneler.items()):
            n, pf = a.skor(e0, e1)
            if n < min_islem or math.isnan(pf):
                continue
            anahtar = (pf, n, -sira)
            if en_anahtar is None or anahtar > en_anahtar:
                en_iyi, en_anahtar = etiket, anahtar
        kayit_ = {"pencere": w, "test_bas": str(t0), "test_bit": str(t1), "secilen": en_iyi,
                  "egitim_pf": None if en_anahtar is None else en_anahtar[0],
                  "egitim_islem": None if en_anahtar is None else en_anahtar[1]}
        secimler.append(kayit_)
        if en_iyi is not None:
            d = nesneler[en_iyi].dilim(t0, t1).copy()
            d["pencere"] = w
            d["ayar"] = en_iyi
            parcalar.append(d)
    oos = pd.concat(parcalar, ignore_index=True) if parcalar else pd.DataFrame()
    return oos, secimler


def _dd_gunluk(seri: pd.Series) -> float:
    zirve = seri.cummax()
    return float(((zirve - seri) / zirve).max())


def oos_metrikleri(oos: pd.DataFrame, oos_bas, oos_bit, risk: float = RISK) -> dict:
    """OOS işlemlerinden R tabanlı metrikler. eleme.degerlendir için 'metrikler' anahtarlarını da içerir."""
    m: dict = {"islem_sayisi": int(len(oos))}
    if len(oos) == 0:
        return m
    d = oos.sort_values("cikis_zamani", kind="stable")
    r = d["r"].to_numpy(dtype=float)
    ozs = np.r_[1.0, np.cumprod(1.0 + risk * r)]
    m["net_getiri"] = float(ozs[-1] - 1.0)
    m["toplam_r"] = float(r.sum())
    m["ortalama_r"] = float(r.mean())
    m["profit_factor"] = pf_hesapla(r)
    m["kazanma_orani"] = float((r > 0).mean())
    kes = max(1, math.ceil(0.05 * len(r)))
    m["en_iyi_yuzde5_haric_pf"] = pf_hesapla(np.sort(r)[::-1][kes:])
    m["max_dusus"] = _dd_gunluk(pd.Series(ozs))
    # günlük sharpe: OOS aralığındaki tüm UTC günleri (işlemsiz günler getiri 0)
    son = max(pd.Timestamp(oos_bit), d["cikis_zamani"].max())
    gunler = pd.date_range(pd.Timestamp(oos_bas).floor("D"), son.floor("D"), freq="D")
    gs = pd.Series(ozs[1:], index=pd.DatetimeIndex(d["cikis_zamani"])).groupby(lambda t: t.floor("D")).last()
    gs = gs.reindex(gs.index.union(gunler)).ffill().fillna(1.0).reindex(gunler)
    g = np.r_[1.0, gs.to_numpy()]
    getiri = g[1:] / g[:-1] - 1.0
    std = getiri.std(ddof=1) if len(getiri) > 1 else np.nan
    m["sharpe"] = float(getiri.mean() / std * np.sqrt(365)) if std and std > 0 else np.nan
    # long / short
    for ad, yon in (("long", 1), ("short", -1)):
        x = oos.loc[oos["yon"] == yon, "r"].to_numpy(dtype=float)
        m[f"n_{ad}"] = int(len(x))
        m[f"pf_{ad}"] = pf_hesapla(x) if len(x) else np.nan
    # yıl bazında (giriş yılı)
    yil = pd.DatetimeIndex(oos["giris_zamani"]).year
    for y in YILLAR:
        x = oos.loc[yil == y, "r"].to_numpy(dtype=float)
        m[f"n_{y}"] = int(len(x))
        m[f"pf_{y}"] = pf_hesapla(x) if len(x) else np.nan
        m[f"net_{y}"] = float(np.prod(1.0 + risk * x) - 1.0) if len(x) else np.nan
    return m


def al_tut_metrikleri(mumlar: pd.DataFrame, oos_bas, oos_bit) -> dict:
    """Aynı OOS aralığında 1x al-tut: ilk mumun açılışı -> son kapanış; günlük sharpe ve max düşüş."""
    m = mumlar[(mumlar.index >= oos_bas) & (mumlar.index < oos_bit)]
    if len(m) < 2:
        return {"bh_getiri": np.nan, "bh_sharpe": np.nan, "bh_max_dusus": np.nan}
    gun = m["kapanis"].groupby(m.index.floor("D")).last()
    g = np.r_[float(m["acilis"].iloc[0]), gun.to_numpy(dtype=float)]
    getiri = g[1:] / g[:-1] - 1.0
    std = getiri.std(ddof=1) if len(getiri) > 1 else np.nan
    return {"bh_getiri": float(g[-1] / g[0] - 1.0),
            "bh_sharpe": float(getiri.mean() / std * np.sqrt(365)) if std and std > 0 else np.nan,
            "bh_max_dusus": _dd_gunluk(pd.Series(g))}


def istikrar(secimler: list) -> dict:
    sec = [s["secilen"] for s in secimler if s["secilen"] is not None]
    if not sec:
        return {"n_farkli_ayar": 0, "en_sik_ayar": "", "en_sik_pay": np.nan}
    en, adet = pd.Series(sec).value_counts().iloc[[0]].reset_index().values[0]
    return {"n_farkli_ayar": len(set(sec)), "en_sik_ayar": str(en), "en_sik_pay": float(adet) / len(sec)}


# ---------------------------------------------------------------------------- görevler
def aday_listesi(ad: str, izgara: bool = True) -> tuple:
    """[(etiket, tur, arg, strateji_nesnesi_veya_hata)]; etkin ayarı (parametre + çıkış) aynı olanlar tek aday.
    Etiket: 'varsayilan' | 'kart:<id>' | 'dis:<id>' | 'izgara:<parametre json>'."""
    gorunen, cikti, hatalar = set(), [], []
    for tur, arg in tarama._ayar_listesi(ad, izgara):
        etiket = tarama._etiket_ayar(tur, arg)
        if tur == "izgara":
            etiket = f"izgara:{tarama._json(arg)}"
        try:
            s = tarama._strateji_kur(ad, tur, arg)
            kimlik = (tarama._json(s.parametreler), tarama._json(dataclasses.asdict(s.cikis_ayarlari)))
        except Exception as e:  # noqa: BLE001  (kurulamayan aday sayılır, hata olarak raporlanır)
            hatalar.append((etiket, f"{type(e).__name__}: {e}"))
            continue
        if kimlik in gorunen:
            continue
        gorunen.add(kimlik)
        cikti.append((etiket, s))
    return cikti, hatalar


def maliyet_ayarlari(kurallar, maliyet_carpani: float = 1.0) -> MotorAyarlari:
    """Araştırma modu motor ayarı; komisyon ve kayma `maliyet_carpani` ile çarpılır (1.0 = tarama ile aynı)."""
    if not maliyet_carpani > 0:
        raise ValueError("maliyet_carpani > 0 olmalı")
    v = MotorAyarlari(limit_modu="olc", kurallar=kurallar)
    return dataclasses.replace(
        v, komisyon_taker_yuzde=v.komisyon_taker_yuzde * maliyet_carpani,
        komisyon_maker_yuzde=v.komisyon_maker_yuzde * maliyet_carpani,
        kayma_bps=v.kayma_bps * maliyet_carpani, stop_kayma_bps=v.stop_kayma_bps * maliyet_carpani)


def gorevler_uret(stratejiler: Iterable[str], semboller: Iterable[str]) -> list:
    semboller = list(semboller)
    gorevler = []
    for ad in stratejiler:
        stil = kayit.al(ad).stil
        for tf in tarama.STRATEJI_TF.get(ad) or tarama.STIL_TF[stil]:
            for sembol in semboller:
                gorevler.append({"strateji": ad, "stil": stil, "sembol": sembol, "tf": tf})
    gorevler.sort(key=lambda g: (g["sembol"], g["tf"]))
    return gorevler


_AYAR: dict = {}
_ONBELLEK: dict = {}


def _isci_baslat(ayar: dict):
    _AYAR.clear()
    _AYAR.update(ayar)
    _ONBELLEK.clear()


def _veri(sembol: str, tf: str):
    k = (sembol, tf)
    if k not in _ONBELLEK:
        if len(_ONBELLEK) >= 4:
            _ONBELLEK.clear()
        d = _AYAR["veri_dizini"]
        # kilit_ac YOK: kilitli dönem depo tarafından kesilir (karar 20).
        # 5m varsa 5m'den; yoksa tf >= 1h için 1h'den; olmazsa açık hata (tf_mumlari).
        mumlar = tf_mumlari(sembol, tf, _AYAR["baslangic"], _AYAR["bitis"], dizin=d)
        try:
            fund = depo.funding_oku(sembol, _AYAR["baslangic"], _AYAR["bitis"], dizin=d)
        except FileNotFoundError:
            fund = None                      # funding dosyası yok (ör. Dukascopy verisi)
        _ONBELLEK[k] = (mumlar, fund)
    return _ONBELLEK[k]


def islem_yolu(cikti_dizini: Path, etiket: str, strateji: str, sembol: str, tf: str) -> Path:
    return Path(cikti_dizini) / "islemler" / etiket / f"{strateji}--{sembol}--{tf}.parquet"


def gorev_calistir(g: dict) -> dict:
    """Tek (strateji, sembol, tf): adayları koş, walk-forward OOS'u kur, özet satırı döner."""
    t0 = time.perf_counter()
    satir = {"strateji": g["strateji"], "stil": g["stil"], "sembol": g["sembol"], "tf": g["tf"], "hata": ""}
    try:
        _gorev_icerik(g, satir)
    except Exception as e:  # noqa: BLE001  (satıra yazılır, tarama durmaz)
        satir["hata"] = f"{type(e).__name__}: {e}"
        satir.setdefault("gecti", False)
        satir.setdefault("nedenler", "hata")
    satir["sure_sn"] = time.perf_counter() - t0
    return satir


def _gorev_icerik(g: dict, satir: dict):
    ad, sembol, tf, stil = g["strateji"], g["sembol"], g["tf"], g["stil"]
    mumlar, fund = _veri(sembol, tf)
    adaylar, kurma_hatalari = aday_listesi(ad, _AYAR.get("izgara", True))
    kurallar = tarama.SEMBOL_KURALLARI.get(sembol, tarama.VARSAYILAN_KURAL)
    ay = maliyet_ayarlari(kurallar, _AYAR.get("maliyet_carpani", 1.0))
    islemler, hatalar, nan_r = {}, list(kurma_hatalari), 0
    n_kosu = 0
    for etiket, s in adaylar:
        try:
            r = backtest(funding.stratejiye_hazirla(s, mumlar, fund, sembol, tf), s, ay, fund)
        except Exception as e:  # noqa: BLE001  (aday hatası sayılır, raporlanır)
            hatalar.append((etiket, f"{type(e).__name__}: {e}"))
            continue
        n_kosu += 1
        if len(r.islemler):
            islemler[etiket] = r.islemler
    satir.update({"n_aday": len(adaylar) + len(kurma_hatalari), "n_kosu": n_kosu, "n_aday_hatali": len(hatalar),
                  "aday_hata_ornegi": hatalar[0][1][:120] if hatalar else ""})
    if n_kosu == 0:
        raise RuntimeError(f"hiç aday koşulamadı: {hatalar[0][1] if hatalar else 'aday yok'}")
    egitim, test = _AYAR["pencere_gun"][stil]
    pencereler = pencereler_uret(mumlar.index[0].floor("D"), mumlar.index[-1] + pd.Timedelta(1, "ns"), egitim, test)
    satir["n_pencere"] = len(pencereler)
    if not pencereler:
        satir.update({"gecti": False, "nedenler": "veri pencereye yetmiyor"})
        return
    oos_bas, oos_bit = pencereler[0][2], pencereler[-1][3]
    oos, secimler = secim_ve_oos(islemler, pencereler, _AYAR["min_islem"][stil])
    satir.update({"oos_bas": str(oos_bas), "oos_bit": str(oos_bit),
                  "n_islemli_pencere": sum(s["secilen"] is not None for s in secimler),
                  "secimler": json.dumps(secimler, ensure_ascii=False, default=str)})
    satir.update(istikrar(secimler))
    m = oos_metrikleri(oos, oos_bas, oos_bit)
    satir.update(m)
    satir.update(al_tut_metrikleri(mumlar, oos_bas, oos_bit))
    k = eleme.degerlendir({"metrikler": m} if len(oos) else {})
    satir["gecti"] = bool(k["gecti"])
    satir["nedenler"] = "; ".join(k["nedenler"])
    if len(oos):
        yol = islem_yolu(_AYAR["cikti_dizini"], _AYAR["etiket"], ad, sembol, tf)
        yol.parent.mkdir(parents=True, exist_ok=True)
        oos.to_parquet(yol, index=False)


# ---------------------------------------------------------------------------- ana akış
def umutsuz_stratejiler(k2_dosyalari: Iterable[Path]) -> set:
    df = pd.concat([pd.read_parquet(p) for p in k2_dosyalari], ignore_index=True)
    u = tarama.umutsuz_mu(df)
    return set(u[u].index)


VARSAYILAN_K2 = (KOK / "sonuclar" / "tarama" / "k2_ana.parquet", KOK / "sonuclar" / "tarama" / "k2_izgara.parquet")


def _yaz(df: pd.DataFrame, yol: Path):
    gecici = yol.with_suffix(".parquet.tmp")
    df.to_parquet(gecici, index=False)
    gecici.replace(yol)


def wf_tara(etiket: str, stratejiler: Optional[Iterable[str]] = None,
            semboller: Iterable[str] = tarama.VARSAYILAN_SEMBOLLER, surec: int = 4,
            umutsuzlari_atla: bool = False, k2_dosyalari: Iterable[Path] = VARSAYILAN_K2,
            cikti_dizini: Optional[Path] = None, veri_dizini: Optional[Path] = None, baslangic=None, bitis=None,
            pencere_gun: Optional[dict] = None, min_islem: Optional[dict] = None, izgara: bool = True,
            hatalari_yeniden: bool = False, deneme_kaydi_yolu=None, ilerleme: bool = True,
            maliyet_carpani: float = 1.0) -> pd.DataFrame:
    stratejiler = list(stratejiler) if stratejiler is not None else list(kayit.tum_stratejiler())
    if umutsuzlari_atla:
        u = umutsuz_stratejiler(k2_dosyalari)
        atlanan = [s for s in stratejiler if s in u]
        stratejiler = [s for s in stratejiler if s not in u]
        if ilerleme:
            print(f"[wf] umutsuz atlanan: {len(atlanan)}", flush=True)
    cikti_dizini = Path(cikti_dizini) if cikti_dizini is not None else CIKTI_DIZINI
    cikti_dizini.mkdir(parents=True, exist_ok=True)
    yol_pq = cikti_dizini / f"{etiket}.parquet"
    onceki = pd.read_parquet(yol_pq) if yol_pq.exists() else pd.DataFrame()
    if hatalari_yeniden and len(onceki):
        onceki = onceki[onceki["hata"] == ""]
    bitmis = set(zip(onceki["strateji"], onceki["sembol"], onceki["tf"])) if len(onceki) else set()
    tum = gorevler_uret(stratejiler, semboller)
    kalan = [g for g in tum if (g["strateji"], g["sembol"], g["tf"]) not in bitmis]
    if ilerleme:
        print(f"[wf] {etiket}: toplam {len(tum)} görev, bitmiş {len(tum) - len(kalan)}, kalan {len(kalan)}", flush=True)
    ayar = {"veri_dizini": veri_dizini, "baslangic": baslangic, "bitis": bitis, "izgara": izgara,
            "pencere_gun": pencere_gun or PENCERE_GUN, "min_islem": min_islem or MIN_ISLEM,
            "cikti_dizini": cikti_dizini, "etiket": etiket, "maliyet_carpani": maliyet_carpani}

    yeni, bekleyen = [], []
    t0 = time.perf_counter()

    def kaydet(son: bool = False):
        if not bekleyen and not son:
            return
        tum_df = pd.concat([onceki, pd.DataFrame(yeni)], ignore_index=True) if yeni else onceki
        if len(tum_df):
            _yaz(tum_df, yol_pq)
        # deneme kaydı: özet diske yazıldıktan SONRA, yalnız yeni biten görevler (çift sayma yok)
        for s in bekleyen:
            if s["hata"] == "" and s.get("n_kosu"):
                deneme_kaydi.kaydet(s["strateji"], s["sembol"], s["tf"], s["n_aday"], s.get("n_pencere", 0),
                                    s["n_kosu"], deneme_kaydi_yolu)
        bekleyen.clear()

    def ekle(satir):
        yeni.append(satir)
        bekleyen.append(satir)
        if len(bekleyen) >= KAYDET_ARALIGI:
            kaydet()
        if ilerleme and len(yeni) % 10 == 0:
            gecen = time.perf_counter() - t0
            print(f"[wf] {len(yeni)}/{len(kalan)}  {gecen:.0f} sn  (tahmini kalan {gecen / len(yeni) * (len(kalan) - len(yeni)):.0f} sn)",
                  flush=True)

    if kalan:
        if surec <= 1:
            _isci_baslat(ayar)
            for g in kalan:
                ekle(gorev_calistir(g))
        else:
            with mp.get_context("fork").Pool(surec, _isci_baslat, (ayar,)) as havuz:
                for satir in havuz.imap_unordered(gorev_calistir, kalan, chunksize=1):
                    ekle(satir)
    kaydet(son=True)
    sonuc = pd.read_parquet(yol_pq) if yol_pq.exists() else pd.DataFrame()
    if len(sonuc):
        sonuc.to_csv(cikti_dizini / f"{etiket}.csv", index=False)
    if ilerleme:
        print(f"[wf] bitti: {len(yeni)} yeni görev, {time.perf_counter() - t0:.1f} sn -> {yol_pq}", flush=True)
    return sonuc


def main(argv=None):
    ap = argparse.ArgumentParser(description="Hızlı walk-forward taraması (Aşama 2 Katman 3)")
    ap.add_argument("--etiket", required=True)
    ap.add_argument("--stratejiler", nargs="*", default=None)
    ap.add_argument("--semboller", nargs="*", default=list(tarama.VARSAYILAN_SEMBOLLER))
    ap.add_argument("--surec", type=int, default=4)
    ap.add_argument("--umutsuzlari-atla", action="store_true")
    ap.add_argument("--hatalari-yeniden", action="store_true")
    ap.add_argument("--maliyet-carpani", type=float, default=1.0)
    a = ap.parse_args(argv)
    s = wf_tara(a.etiket, a.stratejiler, a.semboller, a.surec, a.umutsuzlari_atla, hatalari_yeniden=a.hatalari_yeniden,
                maliyet_carpani=a.maliyet_carpani)
    if len(s):
        print(f"geçen: {int(s['gecti'].sum())}/{len(s)}  hatalı: {int((s['hata'] != '').sum())}")


if __name__ == "__main__":
    main()
