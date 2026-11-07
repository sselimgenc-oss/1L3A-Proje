"""Portföy walk-forward'ı (Aşama 2, karar 23): her (portföy stratejisi, evren, tf) için OOS sonucu.

Felsefe `wf_tarama` ile aynıdır; farklar portföy doğasından gelir. YÖNTEM (koşudan önce sabitlendi; sonuca bakılarak
DEĞİŞTİRİLMEZ)

  1. Aday ayar kümesi (sınıf başına) = csv bağlantı ayarları (`baglama.BAGLAMA`, etiket "csv:<satır>") + sınıf
     varsayılanı ("varsayilan") + parametre ızgarası ("izgara:<json>", <= 27). Her adayın alt evreni (`semboller`)
     koşunun evreniyle KESİŞTİRİLİR; sınıfın asgari sembol/çift/ek-sembol (rejim, referans) koşulu sağlanmıyorsa aday
     ATLANIR (hiçbiri uygun değilse görev "atlandi" yazılır, deneme sayılmaz). Aynı etkin parametreler (JSON) TEK aday.
     Her aday kilit öncesi TÜM veride BİR KEZ koşulur (`portfoy_backtest`, limit_modu="olc": günlük -%3 ve %20 kill
     switch'i işlemi durdurmaz, olay olarak kaydedilir — wf_tarama ile aynı, SADECE araştırma; işlem başı %1 risk ve 3x
     brüt her zaman uygulanır). Günlük getiri = UTC gün sonu MTM özsermayesinin yüzde değişimi.
  2. Pencereler: eğitim 730 gün / test 180 gün, uç uca, örtüşmeyen test pencereleri (`pencereler_uret`).
  3. SEÇİM SKORU (sabit): eğitim penceresindeki günlük getirilerin Sharpe'ı = ort/std * sqrt(365) (portföy için PF(R)
     yerine; işlem sayısı az olan rotasyonlarda PF(R) kararsızdır). Aday, eğitim penceresinde GİRİŞ yapılmış en az
     MIN_ISLEM_EGITIM (10) işlem VE en az MIN_GUN_EGITIM (60) gün VE std > 0 koşulunu sağlamalıdır; en yüksek skor seçilir
     (eşitlikte daha çok işlem, sonra aday sırası). Koşul sağlayan yoksa o test penceresinde işlem yok (getiri 0).
     Seçilen adayın TEST penceresindeki günlük getirileri ve girişi test penceresinde olan işlemleri OOS'a eklenir.
     OOS verisi seçimde asla kullanılmaz (seçim yalnız eğitim aralığındaki günlük getirileri ve girişleri görür).
     Yaklaşıklıklar: aday tam veride koşulduğundan özsermaye yolu pencereden bağımsızdır (boyutlandırma, geçmiş yolun
     bileşik etkisini içerir, gelecek bilgi içermez); eğitim bitişinde açık pozisyonlar MTM olarak skora girer.
  4. OOS metrikleri: OOS aralığındaki TÜM günler (seçim olmayan pencereler getiri 0). net_getiri (bileşik), günlük
     Sharpe, max düşüş, işlem sayısı, PF(R) (işlem R'lerinden), en iyi %5 hariç PF, long/short PF, yıl bazında net/PF/işlem
     (giriş yılı), 2022 ayrıca sütun (net_2022, bh_net_2022). `gecti` = KARAR 24 (`eleme.portfoy_degerlendir`: OOS >= 1095 gün,
     >= 20 yeniden dengeleme [pozisyon vektörünün değiştiği gün], net > 0, Sharpe >= 0.5, max düşüş <= %20, en iyi %5 GÜN
     hariç net > 0); karar 13 sonucu `gecti_k13`/`nedenler_k13` sütunlarında kalır. Risk bütçesi karar 25: ağırlık kolu
     toplam stop riski <= %5 (pozisyon başına %1 değil).
  5. AL-TUT KIYASI: koşu evreninin (EVRENLER) eşit ağırlıklı al-tut sepeti (OOS başlangıcından önceki günün kapanışında
     eşit değerli alım, hiç dengeleme yok, o gün fiyatı olanlar). Sharpe aynı gün-takvimiyle hesaplanır. UYARI: motor %1
     işlem riski ve ATR felaket stopu yüzünden brüt maruziyet çoğu zaman 1x'in çok altındadır (ort_brut sütunu); bu
     yüzden getiri kıyası değil SHARPE ve düşüş kıyası anlamlıdır (sharpe_ustu sütunu).
  6. Deneme kaydı: (strateji, sembol=evren etiketi, aralik=tf) başına bir satır: kombinasyon = aday sayısı, pencere sayısı,
     toplam_kosu = başarılı backtest sayısı; yalnız bu çağrıda YENİ biten görevler yazılır (devam eden koşuda çift sayma yok).

Kilit (karar 20): veri yalnız `motor.portfoy.veri.veri_yukle` (depo.mum_oku) ile okunur; kilit_ac YOK.
Paralel: görev başına bir süreç (fork), kaldığı yerden devam (parquet), çıktı `sonuclar/wf_portfoy/<etiket>.csv`.

CLI: python -m motor.arastirma.wf_portfoy --etiket p3_kripto --evren kripto [--stratejiler pf__rotasyon ...] [--surec 4]
     [--tf 1d] [--hatalari-yeniden] [--maliyet-carpani 1.0] [--izgara-yok]
"""
from __future__ import annotations

import argparse
import dataclasses
import itertools
import json
import math
import multiprocessing as mp
import time
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd

from motor.backtest import deneme_kaydi, eleme
from motor.backtest.walk_forward import pencereler_uret
from motor.portfoy import veri as pveri
from motor.portfoy.motor import PortfoyAyarlari, portfoy_backtest
from motor.portfoy.stratejiler import tum_portfoy_stratejileri
from motor.portfoy.stratejiler.baglama import BAGLAMA
from motor.portfoy.stratejiler.ortak import EMTIA, HEPSI, HISSE, KRIPTO

KOK = Path(__file__).resolve().parents[2]
CIKTI_DIZINI = KOK / "sonuclar" / "wf_portfoy"

EVRENLER = {"kripto": KRIPTO, "hisse": HISSE, "emtia": EMTIA, "hepsi": HEPSI}
EGITIM_GUN, TEST_GUN = 730, 180
MIN_ISLEM_EGITIM = 10
MIN_GUN_EGITIM = 60
SECIM_SKORU = "gunluk_sharpe"
YILLAR = tuple(range(2020, 2026))
KAYDET_ARALIGI = 1
GUN = pd.Timedelta(days=1)


# ---------------------------------------------------------------------------- saf yardımcılar
def sharpe_gunluk(r) -> float:
    r = np.asarray(r, dtype=float)
    if len(r) < 2:
        return math.nan
    sd = r.std(ddof=1)
    return float(r.mean() / sd * math.sqrt(365)) if sd > 0 else math.nan


def pf_hesapla(r) -> float:
    r = np.asarray(r, dtype=float)
    k, z = r[r > 0].sum(), -r[r < 0].sum()
    if z > 0:
        return float(k / z)
    return math.inf if k > 0 else math.nan


def max_dusus(getiri: np.ndarray) -> float:
    ozs = np.r_[1.0, np.cumprod(1.0 + np.asarray(getiri, dtype=float))]
    zirve = np.maximum.accumulate(ozs)
    return float(((zirve - ozs) / zirve).max())


class AdayHesap:
    """Bir adayın tam-veri sonucu: günlük getiri (UTC günü, indeks gün başlangıcı) + işlemler + brüt maruziyet + limit olayları."""

    def __init__(self, gunluk: pd.Series, islemler: pd.DataFrame, ort_brut: float = math.nan, limit_olay=(),
                 dengeleme_gunleri=()):
        g = gunluk.copy()
        g.index = pd.DatetimeIndex(g.index).floor("D")
        self.gunluk = g.groupby(level=0).last().astype(float)
        d = islemler.sort_values("giris_zamani", kind="stable").reset_index(drop=True) if len(islemler) else islemler
        if len(d):
            d["r"] = pd.to_numeric(d["r"], errors="coerce")
        self.islemler = d
        self.giris = pd.DatetimeIndex(d["giris_zamani"]) if len(d) else pd.DatetimeIndex([], tz="UTC")
        self.ort_brut = ort_brut
        self.limit_olay = [pd.Timestamp(t) for t in limit_olay]
        # yeniden dengeleme günü = pozisyon vektörünün (sembol başına net miktar) değiştiği UTC günü
        self.dengeleme = pd.DatetimeIndex(sorted(set(pd.DatetimeIndex(dengeleme_gunleri).floor("D")))) \
            if len(dengeleme_gunleri) else pd.DatetimeIndex([], tz="UTC")

    def egitim_skoru(self, bas, bit) -> tuple:
        """(gun, işlem, Sharpe): YALNIZ [bas, bit) içi günlük getiriler ve bu aralıkta girilen işlemler."""
        g = self.gunluk[(self.gunluk.index >= bas) & (self.gunluk.index < bit)]
        n = int(((self.giris >= bas) & (self.giris < bit)).sum())
        return len(g), n, sharpe_gunluk(g.to_numpy())

    def test_getirisi(self, bas, bit) -> pd.Series:
        return self.gunluk[(self.gunluk.index >= bas) & (self.gunluk.index < bit)]

    def test_islemleri(self, bas, bit) -> pd.DataFrame:
        if not len(self.islemler):
            return self.islemler
        return self.islemler[(self.giris >= bas) & (self.giris < bit)]

    def dengeleme_sayisi(self, bas, bit) -> int:
        return int(((self.dengeleme >= bas) & (self.dengeleme < bit)).sum())

    def limit_olay_sayisi(self, bas, bit) -> int:
        return sum(1 for t in self.limit_olay if bas <= t < bit)


def secim_ve_oos(adaylar: dict, pencereler: list, min_islem: int = MIN_ISLEM_EGITIM, min_gun: int = MIN_GUN_EGITIM):
    """adaylar: {etiket: AdayHesap} (sıra önemli: eşitlikte önce gelen). pencereler: [(e0, e1, t0, t1)].
    Seçim YALNIZ eğitim penceresindeki günlük getiri ve girişlerle yapılır.
    -> (oos_getiri Series [tüm OOS günleri; seçimsiz pencereler 0], oos_islemleri DataFrame, secimler list)"""
    oos_bas, oos_bit = pencereler[0][2], pencereler[-1][3]
    gunler = pd.date_range(oos_bas.floor("D"), oos_bit - GUN, freq="D", tz="UTC")
    getiri = pd.Series(0.0, index=gunler)
    islem_parcalari, secimler = [], []
    for w, (e0, e1, t0, t1) in enumerate(pencereler):
        en_iyi, anahtar_en = None, None
        for sira, (etiket, a) in enumerate(adaylar.items()):
            n_gun, n_islem, sk = a.egitim_skoru(e0, e1)
            if n_gun < min_gun or n_islem < min_islem or not np.isfinite(sk):
                continue
            anahtar = (sk, n_islem, -sira)
            if anahtar_en is None or anahtar > anahtar_en:
                en_iyi, anahtar_en = etiket, anahtar
        kayit = {"pencere": w, "egitim_bas": str(e0), "test_bas": str(t0), "test_bit": str(t1), "secilen": en_iyi,
                 "egitim_sharpe": None if anahtar_en is None else anahtar_en[0],
                 "egitim_islem": None if anahtar_en is None else anahtar_en[1]}
        if en_iyi is not None:
            a = adaylar[en_iyi]
            g = a.test_getirisi(t0, t1)
            getiri.loc[getiri.index.intersection(g.index)] = g.reindex(getiri.index.intersection(g.index)).to_numpy()
            d = a.test_islemleri(t0, t1).copy()
            if len(d):
                d["pencere"], d["ayar"] = w, en_iyi
                islem_parcalari.append(d)
            kayit["brut"] = a.ort_brut
            kayit["limit_olay"] = a.limit_olay_sayisi(t0, t1)
            kayit["dengeleme"] = a.dengeleme_sayisi(t0, t1)
        secimler.append(kayit)
    oos = pd.concat(islem_parcalari, ignore_index=True) if islem_parcalari else pd.DataFrame()
    return getiri, oos, secimler


def net_en_iyi5_gun_haric(r) -> float:
    """En iyi %5 GÜN (en az 1) çıkarılınca kalan günlerin bileşik net getirisi."""
    r = np.sort(np.asarray(r, dtype=float))[::-1]
    if len(r) == 0:
        return math.nan
    kes = max(1, math.ceil(0.05 * len(r)))
    return float(np.prod(1.0 + r[kes:]) - 1.0)


def oos_metrikleri(getiri: pd.Series, oos: pd.DataFrame, yeniden_dengeleme: Optional[int] = None) -> dict:
    """OOS günlük getirisi + OOS işlemlerinden metrikler. eleme.degerlendir anahtarlarını içerir."""
    r = getiri.to_numpy(dtype=float)
    m: dict = {"islem_sayisi": int(len(oos))}
    m["net_getiri"] = float(np.prod(1.0 + r) - 1.0)
    m["sharpe"] = sharpe_gunluk(r)
    m["max_dusus"] = max_dusus(r)
    m["aktif_gun_orani"] = float((r != 0).mean())
    m["oos_gun"] = int(len(r))                                  # karar 24: OOS süresi (gün)
    m["yeniden_dengeleme"] = None if yeniden_dengeleme is None else int(yeniden_dengeleme)
    m["net_en_iyi5_gun_haric"] = net_en_iyi5_gun_haric(r)
    if len(oos):
        rr = np.nan_to_num(oos["r"].to_numpy(dtype=float), nan=0.0)
        m["n_nan_r"] = int(oos["r"].isna().sum())
        m["profit_factor"] = pf_hesapla(rr)
        m["kazanma_orani"] = float((rr > 0).mean())
        kes = max(1, math.ceil(0.05 * len(rr)))
        m["en_iyi_yuzde5_haric_pf"] = pf_hesapla(np.sort(rr)[::-1][kes:])
        for ad, yon in (("long", 1), ("short", -1)):
            x = np.nan_to_num(oos.loc[oos["yon"] == yon, "r"].to_numpy(dtype=float), nan=0.0)
            m[f"n_{ad}"] = int(len(x))
            m[f"pf_{ad}"] = pf_hesapla(x) if len(x) else math.nan
    yil_idx = getiri.index.year
    for y in YILLAR:
        x = getiri[yil_idx == y].to_numpy(dtype=float)
        m[f"net_{y}"] = float(np.prod(1.0 + x) - 1.0) if len(x) else math.nan
        if len(oos):
            yy = pd.DatetimeIndex(oos["giris_zamani"]).year == y
            xr = np.nan_to_num(oos.loc[yy, "r"].to_numpy(dtype=float), nan=0.0)
            m[f"n_{y}"] = int(len(xr))
            m[f"pf_{y}"] = pf_hesapla(xr) if len(xr) else math.nan
    return m


def al_tut_getirisi(veriler: dict, evren: Iterable[str], oos_bas, oos_bit) -> pd.Series:
    """Evrenin eşit ağırlıklı al-tut günlük getirisi (OOS günleri). Taban = OOS'tan bir önceki günün kapanışı; o gün
    fiyatı olmayan semboller sepete girmez. Hiç dengeleme yok (değer kayar)."""
    gunler = pd.date_range(oos_bas.floor("D") - GUN, oos_bit - GUN, freq="D", tz="UTC")
    kap = pd.DataFrame({s: veriler[s]["kapanis"].groupby(veriler[s].index.floor("D")).last()
                        for s in evren if s in veriler})
    kap = kap.reindex(kap.index.union(gunler)).ffill().reindex(gunler)
    taban = kap.iloc[0]
    uye = taban.notna()
    if not uye.any():
        return pd.Series(np.nan, index=gunler[1:])
    deger = (kap.loc[:, uye] / taban[uye]).mean(axis=1)
    g = deger.pct_change().iloc[1:]
    return g


def al_tut_metrikleri(g: pd.Series) -> dict:
    r = g.dropna().to_numpy(dtype=float)
    if len(r) < 2:
        return {"bh_getiri": math.nan, "bh_sharpe": math.nan, "bh_max_dusus": math.nan}
    m = {"bh_getiri": float(np.prod(1.0 + r) - 1.0), "bh_sharpe": sharpe_gunluk(r), "bh_max_dusus": max_dusus(r)}
    for y in YILLAR:
        x = g[g.index.year == y].dropna().to_numpy(dtype=float)
        m[f"bh_net_{y}"] = float(np.prod(1.0 + x) - 1.0) if len(x) else math.nan
    return m


def istikrar(secimler: list) -> dict:
    sec = [s["secilen"] for s in secimler if s["secilen"] is not None]
    if not sec:
        return {"n_farkli_ayar": 0, "en_sik_ayar": "", "en_sik_pay": math.nan}
    vc = pd.Series(sec).value_counts()
    return {"n_farkli_ayar": len(set(sec)), "en_sik_ayar": str(vc.index[0]), "en_sik_pay": float(vc.iloc[0]) / len(sec)}


# ---------------------------------------------------------------------------- aday kümesi
def _json(d: dict) -> str:
    return json.dumps(d, sort_keys=True, ensure_ascii=False, default=lambda o: list(o) if isinstance(o, tuple) else str(o))


def aday_listesi(sinif_ad: str, evren: Iterable[str], izgara: bool = True) -> tuple:
    """-> ([(etiket, strateji)], [atlanan (etiket, neden)]). Alt evren koşu evreniyle kesiştirilir; etkin parametreleri
    aynı olanlar tek aday."""
    sinif = tum_portfoy_stratejileri()[sinif_ad]
    evren = tuple(evren)
    kaynaklar = [(f"csv:{b['satir']}", dict(b["ayar"])) for b in BAGLAMA if b["sinif"] == sinif_ad]
    kaynaklar.append(("varsayilan", {}))
    if izgara and sinif.parametre_izgarasi:
        anahtarlar = list(sinif.parametre_izgarasi)
        for kombo in itertools.product(*(sinif.parametre_izgarasi[k] for k in anahtarlar)):
            p = dict(zip(anahtarlar, kombo))
            kaynaklar.append((f"izgara:{_json(p)}", p))
    adaylar, atlanan, gorunen = [], [], set()
    for etiket, p in kaynaklar:
        try:
            st = sinif(**p)
            etkin = st.etkin_semboller(evren)
            st = st.yeni(semboller=etkin) if etkin else st
            if not st.uygun_mu(evren):
                atlanan.append((etiket, f"evrende yeterli sembol/çift/ek sembol yok (etkin: {list(etkin)})"))
                continue
        except Exception as e:  # noqa: BLE001  (kurulamayan aday raporlanır)
            atlanan.append((etiket, f"{type(e).__name__}: {e}"))
            continue
        kimlik = _json(st.parametreler)
        if kimlik in gorunen:
            continue
        gorunen.add(kimlik)
        adaylar.append((etiket, st))
    return adaylar, atlanan


def gerekli_semboller(st, evren: Iterable[str]) -> list:
    """Adayın veri olarak kullanacağı semboller (alt evren + ek: rejim/referans), evren sırasıyla."""
    gerek = set(st.etkin_semboller(evren)) | {s for s in st.ek_semboller() if s}
    return [s for s in evren if s in gerek]


# ---------------------------------------------------------------------------- görevler
_AYAR: dict = {}
_ONBELLEK: dict = {}


def _isci_baslat(ayar: dict):
    _AYAR.clear()
    _AYAR.update(ayar)
    _ONBELLEK.clear()


def _veri(evren: tuple, tf: str):
    k = (evren, tf)
    if k not in _ONBELLEK:
        _ONBELLEK.clear()
        # kilit_ac YOK: kilitli dönem depo tarafından kesilir (karar 20)
        _ONBELLEK[k] = pveri.veri_yukle(evren, tf, _AYAR["baslangic"], _AYAR["bitis"], _AYAR["veri_dizini"])
    return _ONBELLEK[k]


def islem_yolu(cikti_dizini: Path, etiket: str, strateji: str, evren: str, tf: str, tur: str) -> Path:
    return Path(cikti_dizini) / tur / etiket / f"{strateji}--{evren}--{tf}.parquet"


def maliyet_ayarlari(maliyet_carpani: float = 1.0) -> PortfoyAyarlari:
    if not maliyet_carpani > 0:
        raise ValueError("maliyet_carpani > 0 olmalı")
    v = PortfoyAyarlari(limit_modu="olc")
    return dataclasses.replace(
        v, komisyon_taker_yuzde=v.komisyon_taker_yuzde * maliyet_carpani,
        komisyon_maker_yuzde=v.komisyon_maker_yuzde * maliyet_carpani, kayma_bps=v.kayma_bps * maliyet_carpani,
        stop_kayma_bps=v.stop_kayma_bps * maliyet_carpani)


def gorevler_uret(stratejiler: Iterable[str], evren_ad: str, tf: str) -> list:
    return [{"strateji": s, "evren": evren_ad, "tf": tf} for s in stratejiler]


def gorev_calistir(g: dict) -> dict:
    t0 = time.perf_counter()
    satir = {"strateji": g["strateji"], "evren": g["evren"], "tf": g["tf"], "hata": ""}
    try:
        _gorev_icerik(g, satir)
    except Exception as e:  # noqa: BLE001  (satıra yazılır, koşu durmaz)
        satir["hata"] = f"{type(e).__name__}: {e}"
        satir.setdefault("gecti", False)
        satir.setdefault("nedenler", "hata")
    satir["sure_sn"] = time.perf_counter() - t0
    return satir


def _gorev_icerik(g: dict, satir: dict):
    ad, evren_ad, tf = g["strateji"], g["evren"], g["tf"]
    evren = tuple(_AYAR["evrenler"][evren_ad])
    adaylar, atlanan = aday_listesi(ad, evren, _AYAR.get("izgara", True))
    satir.update({"n_aday": len(adaylar), "n_atlanan": len(atlanan),
                  "atlanan_ornek": atlanan[0][1][:160] if atlanan else ""})
    if not adaylar:
        satir.update({"atlandi": True, "gecti": False, "nedenler": "bu evrende uygun aday yok",
                      "n_kosu": 0, "n_aday_hatali": 0})
        return
    veriler, fundingler = _veri(evren, tf)
    ay = maliyet_ayarlari(_AYAR.get("maliyet_carpani", 1.0))
    hesaplar, hatalar = {}, []
    for etiket, st in adaylar:
        try:
            sec = gerekli_semboller(st, evren)
            v = {s: veriler[s] for s in sec}
            f = {s: fundingler[s] for s in sec if s in fundingler}
            r = portfoy_backtest(v, st, ay, f)
        except Exception as e:  # noqa: BLE001  (aday hatası sayılır, raporlanır)
            hatalar.append((etiket, f"{type(e).__name__}: {e}"))
            continue
        gunluk = r.gunluk_ozsermaye.pct_change().fillna(0.0)
        q = r.pozisyon_gecmisi
        degisti = (q.diff().abs().fillna(0.0).sum(axis=1) > 0) if len(q) else pd.Series(dtype=bool)
        hesaplar[etiket] = AdayHesap(gunluk, r.islemler, float(r.maruziyet["brut"].mean()),
                                     [o["zaman"] for o in r.limit_olaylari], q.index[degisti.to_numpy()])
    satir.update({"atlandi": False, "n_kosu": len(hesaplar), "n_aday_hatali": len(hatalar),
                  "aday_hata_ornegi": hatalar[0][1][:160] if hatalar else ""})
    if not hesaplar:
        raise RuntimeError(f"hiç aday koşulamadı: {hatalar[0][1] if hatalar else 'aday yok'}")
    bas = min(df.index[0] for df in veriler.values()).floor("D")
    bit = max(df.index[-1] for df in veriler.values()) + pd.Timedelta(1, "ns")
    pencereler = pencereler_uret(bas, bit, _AYAR["egitim_gun"], _AYAR["test_gun"])
    satir["n_pencere"] = len(pencereler)
    if not pencereler:
        satir.update({"gecti": False, "nedenler": "veri pencereye yetmiyor"})
        return
    oos_bas, oos_bit = pencereler[0][2], pencereler[-1][3]
    getiri, oos, secimler = secim_ve_oos(hesaplar, pencereler, _AYAR["min_islem"], _AYAR["min_gun"])
    satir.update({"oos_bas": str(oos_bas), "oos_bit": str(oos_bit),
                  "n_islemli_pencere": sum(s["secilen"] is not None for s in secimler),
                  "secimler": json.dumps(secimler, ensure_ascii=False, default=str)})
    satir.update(istikrar(secimler))
    brutlar = [s["brut"] for s in secimler if s.get("brut") is not None and np.isfinite(s.get("brut", np.nan))]
    satir["ort_brut"] = float(np.mean(brutlar)) if brutlar else math.nan
    satir["limit_olay_oos"] = int(sum(s.get("limit_olay", 0) for s in secimler))
    m = oos_metrikleri(getiri, oos, int(sum(s.get("dengeleme", 0) for s in secimler)))
    satir.update(m)
    bh = al_tut_getirisi(veriler, evren, oos_bas, oos_bit)
    satir.update(al_tut_metrikleri(bh))
    satir["sharpe_ustu"] = bool(np.isfinite(m["sharpe"]) and np.isfinite(satir["bh_sharpe"]) and m["sharpe"] > satir["bh_sharpe"])
    # karar 13 sütunu (karşılaştırma için kalır) ve karar 24 (portföy ölçütü: `gecti` budur)
    k13 = eleme.degerlendir({"metrikler": m} if m["islem_sayisi"] else {})
    satir["gecti_k13"] = bool(k13["gecti"])
    satir["nedenler_k13"] = "; ".join(k13["nedenler"])
    k = eleme.portfoy_degerlendir({"metrikler": m})
    satir["gecti"] = bool(k["gecti"])
    satir["nedenler"] = "; ".join(k["nedenler"])
    gun_yolu = islem_yolu(_AYAR["cikti_dizini"], _AYAR["etiket"], ad, evren_ad, tf, "gunluk")
    gun_yolu.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"oos_getiri": getiri, "bh_getiri": bh.reindex(getiri.index)}).to_parquet(gun_yolu)
    if len(oos):
        yol = islem_yolu(_AYAR["cikti_dizini"], _AYAR["etiket"], ad, evren_ad, tf, "islemler")
        yol.parent.mkdir(parents=True, exist_ok=True)
        oos.to_parquet(yol, index=False)


# ---------------------------------------------------------------------------- ana akış
def _yaz(df: pd.DataFrame, yol: Path):
    gecici = yol.with_suffix(".parquet.tmp")
    df.to_parquet(gecici, index=False)
    gecici.replace(yol)


def wf_portfoy(etiket: str, stratejiler: Optional[Iterable[str]] = None, evren: str = "kripto",
               semboller: Optional[Iterable[str]] = None, tf: str = "1d", surec: int = 4,
               cikti_dizini: Optional[Path] = None, veri_dizini: Optional[Path] = None, baslangic=None, bitis=None,
               egitim_gun: int = EGITIM_GUN, test_gun: int = TEST_GUN, min_islem: int = MIN_ISLEM_EGITIM,
               min_gun: int = MIN_GUN_EGITIM, izgara: bool = True, hatalari_yeniden: bool = False,
               deneme_kaydi_yolu=None, ilerleme: bool = True, maliyet_carpani: float = 1.0) -> pd.DataFrame:
    stratejiler = list(stratejiler) if stratejiler is not None else sorted(tum_portfoy_stratejileri())
    bilinmeyen = [s for s in stratejiler if s not in tum_portfoy_stratejileri()]
    if bilinmeyen:
        raise ValueError(f"bilinmeyen portföy stratejileri: {bilinmeyen}")
    evrenler = dict(EVRENLER)
    if semboller is not None:
        evrenler[evren] = tuple(semboller)
    elif evren not in evrenler:
        raise ValueError(f"bilinmeyen evren: {evren} (seçenekler: {sorted(evrenler)})")
    cikti_dizini = Path(cikti_dizini) if cikti_dizini is not None else CIKTI_DIZINI
    cikti_dizini.mkdir(parents=True, exist_ok=True)
    yol_pq = cikti_dizini / f"{etiket}.parquet"
    onceki = pd.read_parquet(yol_pq) if yol_pq.exists() else pd.DataFrame()
    if hatalari_yeniden and len(onceki):
        onceki = onceki[onceki["hata"] == ""]
    bitmis = set(zip(onceki["strateji"], onceki["evren"], onceki["tf"])) if len(onceki) else set()
    tum = gorevler_uret(stratejiler, evren, tf)
    kalan = [g for g in tum if (g["strateji"], g["evren"], g["tf"]) not in bitmis]
    if ilerleme:
        print(f"[wfp] {etiket}: toplam {len(tum)} görev, bitmiş {len(tum) - len(kalan)}, kalan {len(kalan)}", flush=True)
    ayar = {"veri_dizini": veri_dizini, "baslangic": baslangic, "bitis": bitis, "izgara": izgara,
            "egitim_gun": egitim_gun, "test_gun": test_gun, "min_islem": min_islem, "min_gun": min_gun,
            "cikti_dizini": cikti_dizini, "etiket": etiket, "maliyet_carpani": maliyet_carpani, "evrenler": evrenler}
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
                deneme_kaydi.kaydet(s["strateji"], s["evren"], s["tf"], s["n_aday"], s.get("n_pencere", 0),
                                    s["n_kosu"], deneme_kaydi_yolu)
        bekleyen.clear()

    def ekle(satir):
        yeni.append(satir)
        bekleyen.append(satir)
        if len(bekleyen) >= KAYDET_ARALIGI:
            kaydet()
        if ilerleme:
            print(f"[wfp] {len(yeni)}/{len(kalan)} {satir['strateji']} {satir['hata'] or 'ok'} "
                  f"({time.perf_counter() - t0:.0f} sn)", flush=True)

    if kalan:
        if surec <= 1:
            _isci_baslat(ayar)
            for g in kalan:
                ekle(gorev_calistir(g))
        else:
            with mp.get_context("fork").Pool(min(surec, len(kalan)), _isci_baslat, (ayar,)) as havuz:
                for satir in havuz.imap_unordered(gorev_calistir, kalan, chunksize=1):
                    ekle(satir)
    kaydet(son=True)
    sonuc = pd.read_parquet(yol_pq) if yol_pq.exists() else pd.DataFrame()
    if len(sonuc):
        sonuc.to_csv(cikti_dizini / f"{etiket}.csv", index=False)
    if ilerleme:
        print(f"[wfp] bitti: {len(yeni)} yeni görev, {time.perf_counter() - t0:.1f} sn -> {yol_pq}", flush=True)
    return sonuc


def main(argv=None):
    ap = argparse.ArgumentParser(description="Portföy walk-forward (Aşama 2, karar 23)")
    ap.add_argument("--etiket", required=True)
    ap.add_argument("--stratejiler", nargs="*", default=None)
    ap.add_argument("--evren", default="kripto", choices=sorted(EVRENLER))
    ap.add_argument("--semboller", nargs="*", default=None, help="evren sembollerini ezer (etiket --evren adıyla kalır)")
    ap.add_argument("--tf", default="1d")
    ap.add_argument("--surec", type=int, default=4)
    ap.add_argument("--hatalari-yeniden", action="store_true")
    ap.add_argument("--maliyet-carpani", type=float, default=1.0)
    ap.add_argument("--izgara-yok", action="store_true")
    a = ap.parse_args(argv)
    s = wf_portfoy(a.etiket, a.stratejiler, a.evren, a.semboller, a.tf, a.surec, hatalari_yeniden=a.hatalari_yeniden,
                   maliyet_carpani=a.maliyet_carpani, izgara=not a.izgara_yok)
    if len(s):
        print(f"geçen: {int(s['gecti'].sum())}/{len(s)}  hatalı: {int((s['hata'] != '').sum())}  "
              f"atlanan: {int(s['atlandi'].fillna(False).sum()) if 'atlandi' in s else 0}")


if __name__ == "__main__":
    main()
