"""Dukascopy (datafeed.dukascopy.com) 1 dakikalık BID mumlarından 5m veri üretme.

Neden: Binance'te hisse/altın/petrol/bakır geçmişi kısa (2025-12 sonrası = kilitli dönem). Uzun geçmiş Dukascopy'den
gelir; canlı işlem ileride Binance TradFi perp'lerinde olacak. Bizdeki sembol adları `DK_` önekli (ör. DK_AAPL) ve
mevcut Binance verisine (NVDAUSDT vb.) dokunmaz.

Dosya düzeni (Dukascopy tarafı; AY 0-İNDEKSLİ: Ocak=00)
  datafeed/<SYM>/<YYYY>/BID_candles_day_1.bi5        yıllık günlük mumlar (hangi günde işlem var? -> yalnız o günler istenir)
  datafeed/<SYM>/<YYYY>/<MM>/<DD>/BID_candles_min_1.bi5   günlük 1 dakikalık mumlar
Kayıt (LZMA sıkıştırılmış, büyük-endian, 24 bayt): zaman_ofseti(sn, uint32), açılış, KAPANIŞ, düşük, yüksek (uint32,
nokta ölçekli: fiyat = değer / NOKTA) , hacim (float32). Sıra açılış-KAPANIŞ-düşük-yüksek (gerçek dosyayla doğrulandı).
Zaman ofseti günlük dosyada gün başından, yıllık günlük dosyada yıl başından (UTC) itibarendir.
Dukascopy "işlem yok" dakikalarını önceki kapanışla düz mum (hacim 0) olarak doldurur; bu mumlar ATILIR
(sözleşme: eksik mum doldurulmaz).

Önbellek: ham dosyalar `veri/mumlar/_ham/dukascopy/<SYM>/...` altında. 404 ya da boş (200, 0 bayt) yanıt `.yok`
işaretiyle kaydedilir ve bir daha istenmez. Geçici hatalar (503, bağlantı kopması) üstel geri çekilmeyle tekrar denenir;
yine de başarısız günler önbelleğe YAZILMAZ ve `basarisiz_gunler.json` dosyasına listelenir (sessizce atlanmaz);
aynı komutla yeniden çalıştırınca yalnız eksik günler istenir (kaldığı yerden devam).

SAATLİK MOD (`--aralik 1h`): dakikalık indirme çok yavaş olduğundan swing (4h/1d) ve daytrade 1h için AYLIK saatlik dosya
kullanılır: datafeed/<SYM>/<YYYY>/<MM 0-indeksli>/BID_candles_hour_1.bi5 (24 bayt kayıt, aynı sıra; ofset AY BAŞINDAN
saniye). Yıllık saatlik dosya yoktur (404). Aynı önbellek kökü/İstemci/geri çekilme, hacim<=0 düz mumlar atılır, aynı
NOKTA ve bölünme düzeltmesi; çıktı `veri/mumlar/DK_<X>/1h.parquet`. Bitiş (`--bitis`, hariç) ayını kapsayan son ay dosyası
yenilenir (devam eden ay kısmi olabilir); dosyası henüz yoksa (404) o ay ATLANIR (dakikalıktan türetme yapılmaz). 1h mumu
XX:00'da başlar; hisse seansı 13:30/14:30 UTC açıldığı için seansın ilk 1h mumu yalnız yarım saatlik işlem içerir.
Başarısız aylar `basarisiz_aylar_<SEMBOL>.json` dosyasına yazılır.

Bölünme (split): bkz. `bolunme_duzelt` ve `BOLUNME_DOSYASI`.
CLI: python -m motor.veri.dukascopy --semboller DK_AAPL DK_XAU [--baslangic YYYY-MM] [--bitis YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import json
import lzma
import struct
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from motor.veri.depo import MUM_DIZINI, MUM_SUTUNLARI, mum_yolu
from motor.veri.indir import _bos_mum, _yaz

TABAN_URL = "https://datafeed.dukascopy.com/datafeed"
HAM_DIZIN = MUM_DIZINI / "_ham" / "dukascopy"
BOLUNME_DOSYASI = HAM_DIZIN / "bolunmeler.json"   # isteğe bağlı geçersiz kılma; yoksa BOLUNMELER kullanılır
# Dukascopy hisse verisi HAM'dır (bölünme düzeltilmemiş: bölünme öncesi fiyatlar oran kadar yüksek, Yahoo ile
# oran tam bölünme katsayısı çıktı). Tarihler Yahoo chart API `events=split` (2026-11-06). Sıçrama bölünme gününün
# kendisinde (UTC 00:00) olur; öncesi oran'a bölünür, hacim oran ile çarpılır.
BOLUNMELER = {
    "DK_AAPL": [("2020-08-31", 4.0)],
    "DK_NVDA": [("2021-07-20", 4.0), ("2024-06-10", 10.0)],
    "DK_TSLA": [("2020-08-31", 5.0), ("2022-08-25", 3.0)],
    "DK_AMZN": [("2022-06-06", 20.0)],
    "DK_GOOGL": [("2022-07-18", 20.0)],
}
KAYIT_BAYT = 24
BITIS_VARSAYILAN = "2026-11-01"   # hariç: son gün 2026-10-31
ARAMA_BASLANGIC_YILI = 2008

# bizim sembol -> Dukascopy adı. DK_META: Dukascopy'de METAUSUSD'de HİÇ veri yok (404); tüm geçmiş (2017-01-26 ..
# bugün, yeniden adlandırma sonrası dahil) FBUSUSD altında tek parça sürüyor -> FBUSUSD kullanılır.
SEMBOLLER = {
    "DK_AAPL": "AAPLUSUSD", "DK_MSFT": "MSFTUSUSD", "DK_GOOGL": "GOOGLUSUSD", "DK_AMZN": "AMZNUSUSD",
    "DK_NVDA": "NVDAUSUSD", "DK_META": "FBUSUSD", "DK_TSLA": "TSLAUSUSD",
    "DK_XAU": "XAUUSD", "DK_WTI": "LIGHTCMDUSD", "DK_COPPER": "COPPERCMDUSD",
    # son1ay (E014 makro rotasyon vekilleri): SPY -> S&P 500 endeks CFD'si, TLT -> ABD uzun vadeli T-Bond CFD'si
    "DK_SPX": "USA500IDXUSD", "DK_UST": "USTBONDTRUSD",
}
# Eski ad (şirket adı değişimi): ana adın ilk verisinden ÖNCEKİ günler bu adla çekilir. Şu an kullanılmıyor.
ESKI_AD: dict[str, str] = {}
# 1 fiyat birimi = 1/NOKTA. Varsayılan 1000; Yahoo karşılaştırmasıyla doğrulanır (rapor).
# Bakır (COPPERCMDUSD, $/lb) 10000 ölçekli (1000 ile Yahoo HG=F'nin 10 katı çıktı).
NOKTA = {s: 1000 for s in SEMBOLLER}
NOKTA["DK_COPPER"] = 10000


# ------------------------------------------------------------------ çözme / birleştirme
def bi5_coz(bayt: bytes, taban_zaman: pd.Timestamp, nokta: int, hacimsiz_at: bool = True) -> pd.DataFrame:
    """LZMA'lı bi5 -> 1m (ya da günlük) mum tablosu. İndeks UTC açılış zamanı (taban_zaman + ofset).
    Sütunlar: acilis, yuksek, dusuk, kapanis, hacim. hacimsiz_at: hacim<=0 (Dukascopy'nin düz dolgu mumu) satırları atar."""
    if not bayt:
        return _bos_ham()
    veri = lzma.decompress(bayt)
    if len(veri) % KAYIT_BAYT:
        raise ValueError(f"bi5 uzunluğu 24'ün katı değil: {len(veri)}")
    if not veri:
        return _bos_ham()
    a = np.frombuffer(veri, dtype=np.dtype([("t", ">u4"), ("o", ">u4"), ("c", ">u4"), ("l", ">u4"),
                                            ("h", ">u4"), ("v", ">f4")]))
    df = pd.DataFrame({
        "acilis": a["o"].astype("float64") / nokta, "yuksek": a["h"].astype("float64") / nokta,
        "dusuk": a["l"].astype("float64") / nokta, "kapanis": a["c"].astype("float64") / nokta,
        "hacim": a["v"].astype("float64")})
    df.index = pd.DatetimeIndex(taban_zaman + pd.to_timedelta(a["t"].astype("int64"), unit="s"), name="zaman")
    if hacimsiz_at:
        df = df[df["hacim"] > 0]
    return df


def _bos_ham() -> pd.DataFrame:
    df = pd.DataFrame({c: pd.Series(dtype="float64") for c in ["acilis", "yuksek", "dusuk", "kapanis", "hacim"]})
    df.index = pd.DatetimeIndex([], tz="UTC", name="zaman")
    return df


def bi5_yaz(kayitlar: list[tuple], yol: Path) -> None:
    """Test/yardımcı: (ofset, açılış, kapanış, düşük, yüksek, hacim) listesini bi5 olarak yazar (ölçekli tamsayılar)."""
    ham = b"".join(struct.pack(">5If", *k) for k in kayitlar)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_bytes(lzma.compress(ham))


def bir_dakikadan_5m(m1: pd.DataFrame) -> pd.DataFrame:
    """1m -> 5m (UTC 5 dk sınırlarına hizalı, sözleşme sütunları). Eksik 1m mum doldurulmaz; 5m mum, içinde en az bir
    1m mum varsa oluşur (düz dolgu mumları zaten atılmıştır). quote_hacim = hacim*kapanis (yaklaşık), islem_sayisi = 0."""
    if m1.empty:
        return _bos_mum()
    g = m1.groupby(m1.index.floor("5min"))
    c = pd.DataFrame({"acilis": g["acilis"].first(), "yuksek": g["yuksek"].max(), "dusuk": g["dusuk"].min(),
                      "kapanis": g["kapanis"].last(), "hacim": g["hacim"].sum()})
    c["quote_hacim"] = c["hacim"] * c["kapanis"]
    c["islem_sayisi"] = np.int64(0)
    c.index.name = "zaman"
    return c[MUM_SUTUNLARI].astype({"islem_sayisi": "int64"})


def bolunme_duzelt(df: pd.DataFrame, bolunmeler: list[tuple[str, float]]) -> pd.DataFrame:
    """Hisse bölünmesi düzeltmesi (geriye dönük): bölünme tarihinden (UTC gün başı) ÖNCEKİ mumların fiyatı oran'a bölünür,
    hacmi oran ile çarpılır (quote_hacim değişmez). bolunmeler: [("2024-06-10", 10.0), ...] (oran = yeni/eski hisse, 10:1 için 10).
    Ham veri zaten düzeltilmişse bu çağrı YAPILMAZ (bkz. rapor)."""
    df = df.copy()
    for tarih, oran in bolunmeler:
        onceki = df.index < pd.Timestamp(tarih, tz="UTC")
        for c in ("acilis", "yuksek", "dusuk", "kapanis"):
            df.loc[onceki, c] = df.loc[onceki, c] / oran
        df.loc[onceki, "hacim"] = df.loc[onceki, "hacim"] * oran
    return df


# --------------------------------------------------------------------------- ağ
class AgHatasi(RuntimeError):
    pass


class Istemci:
    """requests üstünde: iş parçacığı başına oturum, istekler arası bekleme, üstel geri çekilme."""

    def __init__(self, bekleme: float = 0.1, deneme: int = 8, taban_bekleme: float = 1.0, tavan_bekleme: float = 30.0):
        self.bekleme, self.deneme = bekleme, deneme
        self.taban_bekleme, self.tavan_bekleme = taban_bekleme, tavan_bekleme
        self._yerel = threading.local()

    def _oturum(self) -> requests.Session:
        if not hasattr(self._yerel, "s"):
            s = requests.Session()
            s.headers["User-Agent"] = "Mozilla/5.0"
            self._yerel.s = s
        return self._yerel.s

    def getir(self, yol: str) -> bytes | None:
        """200 -> bayt (boş olabilir); 404 -> None; geçici hata -> tekrar, tükenirse AgHatasi."""
        son = ""
        for d in range(self.deneme):
            time.sleep(self.bekleme)
            try:
                r = self._oturum().get(f"{TABAN_URL}/{yol}", timeout=40)
                if r.status_code == 200:
                    return r.content
                if r.status_code == 404:
                    return None
                son = f"HTTP {r.status_code}"
            except requests.RequestException as e:
                son = f"{type(e).__name__}"
                self._yerel.__dict__.pop("s", None)  # bozuk bağlantıyı bırak
            time.sleep(min(self.taban_bekleme * 2 ** d, self.tavan_bekleme))
        raise AgHatasi(f"{yol}: {son} ({self.deneme} deneme)")


# --------------------------------------------------------------------- önbellek
def _ham_yol(ham: Path, dk_ad: str, *parca: str) -> Path:
    return ham.joinpath(dk_ad, *parca)


def onbellekte_mi(ham: Path, dk_ad: str, yol_parcalari: tuple[str, ...]) -> bool:
    yol = _ham_yol(ham, dk_ad, *yol_parcalari)
    return yol.exists() or yol.with_name(yol.name + ".yok").exists()


def onbellekli_getir(istemci, ham: Path, dk_ad: str, yol_parcalari: tuple[str, ...], yenile: bool = False):
    """Önbellekten ya da ağdan bayt döner. 404/boş -> None ve `.yok` işareti (bir daha istenmez).
    Geçici hata -> AgHatasi (önbelleğe yazılmaz). yenile=True: önbelleği yok say (devam eden yıl için)."""
    yol = _ham_yol(ham, dk_ad, *yol_parcalari)
    yok = yol.with_name(yol.name + ".yok")
    if not yenile:
        if yok.exists():
            return None
        if yol.exists():
            return yol.read_bytes()
    bayt = istemci.getir("/".join([dk_ad, *yol_parcalari]))
    yol.parent.mkdir(parents=True, exist_ok=True)
    if not bayt:
        yok.touch()
        if yol.exists():
            yol.unlink()
        return None
    gecici = yol.with_name(yol.name + ".tmp")
    gecici.write_bytes(bayt)
    gecici.replace(yol)
    if yok.exists():
        yok.unlink()
    return bayt


def _gun_parcalari(g: date) -> tuple[str, ...]:
    return (f"{g.year:04d}", f"{g.month - 1:02d}", f"{g.day:02d}", "BID_candles_min_1.bi5")


def _gun_ham_yolu(ham: Path, dk_ad: str, g: date) -> Path:
    """Günlük dakika dosyasının önbellek yolu (Dukascopy yolunun aynısı)."""
    return _ham_yol(ham, dk_ad, *_gun_parcalari(g))


def islem_gunleri(istemci, ham: Path, dk_ad: str, baslangic_yili: int, bitis: date, nokta: int) -> list[date]:
    """Günlük mumlardan hacmi olan günler (yalnız bu günlerin dakika dosyası istenir).
    Tamamlanmış yıllar yıllık dosyadan; İÇİNDE BULUNULAN yıl için yıllık dosya yoktur (404), aylık günlük dosyalar
    (`<YYYY>/<MM>/BID_candles_day_1.bi5`) kullanılır ve her çalıştırmada yenilenir."""
    gunler = []
    simdi_yil = date.today().year
    for yil in range(baslangic_yili, bitis.year + 1):
        if yil < simdi_yil:
            bayt = onbellekli_getir(istemci, ham, dk_ad, (f"{yil:04d}", "BID_candles_day_1.bi5"))
            parcalar = [(bayt, pd.Timestamp(f"{yil}-01-01", tz="UTC"))]
        else:
            parcalar = []
            for ay in range(1, 13):
                if date(yil, ay, 1) >= bitis:
                    break
                yol_p = (f"{yil:04d}", f"{ay - 1:02d}", "BID_candles_day_1.bi5")
                try:
                    b = onbellekli_getir(istemci, ham, dk_ad, yol_p, yenile=True)
                except AgHatasi as e:
                    onb = _ham_yol(ham, dk_ad, *yol_p)
                    if not onb.exists():
                        raise
                    print(f"UYARI: {e}; eski önbellek kullanıldı", flush=True)
                    b = onb.read_bytes()
                parcalar.append((b, pd.Timestamp(yil, ay, 1, tz="UTC")))
        for bayt, taban in parcalar:
            if bayt:
                gun = bi5_coz(bayt, taban, nokta)
                gunler += [t.date() for t in gun.index if t.date() < bitis]
    return gunler


# --------------------------------------------------------------------- indirme
def gunleri_indir(istemci, ham: Path, dk_ad: str, gunler: list[date], es_zamanli: int = 3,
                  log=None) -> tuple[int, int, list[date]]:
    """Dakika dosyalarını indirir. (indirilen_yeni, veri_yok, basarisiz_gunler) döner."""
    yeni = yok = 0
    basarisiz: list[date] = []
    bekleyen = [g for g in gunler if not onbellekte_mi(ham, dk_ad, _gun_parcalari(g))]

    def is_(g):
        try:
            return g, onbellekli_getir(istemci, ham, dk_ad, _gun_parcalari(g)), None
        except AgHatasi as e:
            return g, None, str(e)

    with ThreadPoolExecutor(max_workers=es_zamanli) as havuz:
        for i, (g, bayt, hata) in enumerate(havuz.map(is_, bekleyen), 1):
            if hata:
                basarisiz.append(g)
                if log:
                    log(f"  BAŞARISIZ {dk_ad} {g}: {hata}")
            elif bayt is None:
                yok += 1
            else:
                yeni += 1
            if log and i % 50 == 0:
                log(f"  {dk_ad}: {i}/{len(bekleyen)} gün (yeni {yeni}, yok {yok}, başarısız {len(basarisiz)})")
    return yeni, yok, basarisiz


# ------------------------------------------------------------------ sembol akışı
def _gunleri_oku(ham: Path, dk_ad: str, gunler: list[date], nokta: int) -> pd.DataFrame:
    parcalar = []
    for g in gunler:
        yol = _gun_ham_yolu(ham, dk_ad, g)
        if yol.exists():
            parcalar.append(bi5_coz(yol.read_bytes(), pd.Timestamp(g, tz="UTC"), nokta))
    parcalar = [p for p in parcalar if len(p)]
    return pd.concat(parcalar) if parcalar else _bos_ham()


def bolunmeler_oku(sembol: str, dosya: Path | None = None) -> list[tuple[str, float]]:
    """Bölünme listesi. `dosya` verilirse ({"DK_NVDA": [["2024-06-10", 10.0], ...]}) o; verilmezse BOLUNMELER."""
    if dosya is None:
        return list(BOLUNMELER.get(sembol, []))
    if not dosya.exists():
        return []
    return [(t, float(o)) for t, o in json.loads(dosya.read_text(encoding="utf-8")).get(sembol, [])]


def sembol_indir(sembol: str, baslangic: str | None = None, bitis: str = BITIS_VARSAYILAN,
                 dizin: Path | None = None, istemci=None, es_zamanli: int = 3, log=print,
                 bolunme_dosyasi: Path | None = None) -> dict:
    """Bir DK_ sembolünü indirir, 5m parquet yazar. Dönen sözlük: ilk, son, mum_sayisi, basarisiz (gün listesi).
    baslangic: 'YYYY-MM' (verilmezse Dukascopy'deki en eski veriden). Eski ad (ESKI_AD) varsa eski tarih ondan alınır."""
    if sembol not in SEMBOLLER:
        raise KeyError(f"Bilinmeyen sembol: {sembol} (bilinenler: {sorted(SEMBOLLER)})")
    dizin = dizin or MUM_DIZINI
    ham = dizin / "_ham" / "dukascopy"
    istemci = istemci or Istemci()
    nokta = NOKTA[sembol]
    bitis_g = date.fromisoformat(bitis)
    bas_yil = int(baslangic[:4]) if baslangic else ARAMA_BASLANGIC_YILI
    adlar = [SEMBOLLER[sembol]] + ([ESKI_AD[sembol]] if sembol in ESKI_AD else [])

    gun_ad: dict[date, str] = {}   # gün -> hangi Dukascopy adından okunacak (ana ad öncelikli)
    for ad in reversed(adlar):     # önce eski ad, sonra ana ad üstüne yazar
        for g in islem_gunleri(istemci, ham, ad, bas_yil, bitis_g, nokta):
            gun_ad[g] = ad
    if baslangic:
        bas_g = date.fromisoformat(baslangic + "-01")
        gun_ad = {g: a for g, a in gun_ad.items() if g >= bas_g}
    log(f"{sembol}: {len(gun_ad)} işlem günü" + (f" ({min(gun_ad)} .. {max(gun_ad)})" if gun_ad else ""))

    basarisiz: list[date] = []
    for ad in adlar:
        gunler = sorted(g for g, a in gun_ad.items() if a == ad)
        _, _, b = gunleri_indir(istemci, ham, ad, gunler, es_zamanli, log)
        basarisiz += b
    parcalar = []
    for ad in adlar:
        parcalar.append(_gunleri_oku(ham, ad, sorted(g for g, a in gun_ad.items() if a == ad), nokta))
    m1 = pd.concat([p for p in parcalar if len(p)]) if any(len(p) for p in parcalar) else _bos_ham()
    m1 = m1[~m1.index.duplicated(keep="last")].sort_index()
    m5 = bir_dakikadan_5m(m1)
    bol = bolunmeler_oku(sembol, bolunme_dosyasi)
    if bol and len(m5):
        m5 = bolunme_duzelt(m5, bol)
    yol = mum_yolu(sembol, "5m", dizin)
    if len(m5):
        _yaz(m5, yol)
    bas_yaz = sorted(set(basarisiz))
    kayit = dizin / "_ham" / "dukascopy" / f"basarisiz_gunler_{sembol}.json"
    kayit.parent.mkdir(parents=True, exist_ok=True)
    kayit.write_text(json.dumps([str(g) for g in bas_yaz]), encoding="utf-8")
    if bas_yaz:
        log(f"{sembol}: UYARI {len(bas_yaz)} gün indirilemedi (yeniden çalıştırınca denenir): {kayit}")
    return {"sembol": sembol, "ilk": m5.index[0] if len(m5) else None, "son": m5.index[-1] if len(m5) else None,
            "mum_sayisi": len(m5), "basarisiz": bas_yaz}


# ------------------------------------------------------------------ saatlik mod
def _ay_parcalari(yil: int, ay: int) -> tuple[str, ...]:
    return (f"{yil:04d}", f"{ay - 1:02d}", "BID_candles_hour_1.bi5")


def _aylar(bas_yil: int, bitis: date) -> list[tuple[int, int]]:
    """[(yıl, ay)] bas_yil Ocak .. bitis'in (hariç) son gününü içeren ay."""
    son = bitis - timedelta(days=1)
    return [(y, m) for y in range(bas_yil, son.year + 1) for m in range(1, 13) if (y, m) <= (son.year, son.month)]


def saatlik_indir(sembol: str, baslangic: str | None = None, bitis: str = BITIS_VARSAYILAN,
                  dizin: Path | None = None, istemci=None, es_zamanli: int = 3, log=print,
                  bolunme_dosyasi: Path | None = None, bugun: date | None = None) -> dict:
    """Aylık saatlik dosyalardan 1h parquet yazar. Dönen: sembol, ilk, son, mum_sayisi, basarisiz (ay listesi 'YYYY-MM').
    İçinde bulunulan ay (bugun) ve bitis'i kapsayan ay önbelleği yok sayılıp yenilenir; 404 olan ay atlanır."""
    if sembol not in SEMBOLLER:
        raise KeyError(f"Bilinmeyen sembol: {sembol} (bilinenler: {sorted(SEMBOLLER)})")
    dizin = dizin or MUM_DIZINI
    ham = dizin / "_ham" / "dukascopy"
    istemci = istemci or Istemci()
    nokta, dk_ad = NOKTA[sembol], SEMBOLLER[sembol]
    bitis_g = date.fromisoformat(bitis)
    bugun = bugun or date.today()
    bas_yil = int(baslangic[:4]) if baslangic else ARAMA_BASLANGIC_YILI
    aylar = _aylar(bas_yil, bitis_g)
    if baslangic:
        aylar = [a for a in aylar if a >= (int(baslangic[:4]), int(baslangic[5:7]))]
    son_ay = _aylar(bas_yil, bitis_g)[-1] if aylar else None

    def is_(ya):
        y, a = ya
        yenile = ya == son_ay or ya >= (bugun.year, bugun.month)
        try:
            return ya, onbellekli_getir(istemci, ham, dk_ad, _ay_parcalari(y, a), yenile=yenile), None
        except AgHatasi as e:
            onb = _ham_yol(ham, dk_ad, *_ay_parcalari(y, a))
            if yenile and onb.exists():     # eski önbellek varsa onunla devam
                return ya, onb.read_bytes(), None
            return ya, None, str(e)

    parcalar, basarisiz = [], []
    with ThreadPoolExecutor(max_workers=es_zamanli) as havuz:
        for i, (ya, bayt, hata) in enumerate(havuz.map(is_, aylar), 1):
            if hata:
                basarisiz.append(f"{ya[0]:04d}-{ya[1]:02d}")
                log(f"  BAŞARISIZ {dk_ad} {ya[0]}-{ya[1]:02d}: {hata}")
            elif bayt:
                parcalar.append(bi5_coz(bayt, pd.Timestamp(ya[0], ya[1], 1, tz="UTC"), nokta))
            if i % 40 == 0:
                log(f"  {dk_ad}: {i}/{len(aylar)} ay")
    parcalar = [p for p in parcalar if len(p)]
    h1 = pd.concat(parcalar) if parcalar else _bos_ham()
    h1 = h1[~h1.index.duplicated(keep="last")].sort_index()
    h1 = h1[h1.index < pd.Timestamp(bitis_g, tz="UTC")]
    h1["quote_hacim"] = h1["hacim"] * h1["kapanis"]
    h1["islem_sayisi"] = np.int64(0)
    h1 = h1[MUM_SUTUNLARI].astype({"islem_sayisi": "int64"})
    h1.index.name = "zaman"
    bol = bolunmeler_oku(sembol, bolunme_dosyasi)
    if bol and len(h1):
        h1 = bolunme_duzelt(h1, bol)
    if len(h1):
        _yaz(h1, mum_yolu(sembol, "1h", dizin))
    kayit = ham / f"basarisiz_aylar_{sembol}.json"
    kayit.parent.mkdir(parents=True, exist_ok=True)
    kayit.write_text(json.dumps(sorted(basarisiz)), encoding="utf-8")
    if basarisiz:
        log(f"{sembol}: UYARI {len(basarisiz)} ay indirilemedi (yeniden çalıştırınca denenir): {kayit}")
    return {"sembol": sembol, "ilk": h1.index[0] if len(h1) else None, "son": h1.index[-1] if len(h1) else None,
            "mum_sayisi": len(h1), "basarisiz": sorted(basarisiz)}


def seans_raporu(m5: pd.DataFrame) -> pd.Series:
    """UTC saat -> mum sayısı (hangi saatlerde veri var?)."""
    return m5.groupby(m5.index.hour).size()


# ------------------------------------------------------------------------ CLI
def main(argv=None):
    p = argparse.ArgumentParser(description="Dukascopy 1m BID mumlarından DK_ sembollerinin 5m verisini üret")
    p.add_argument("--semboller", nargs="+", required=True)
    p.add_argument("--baslangic", help="YYYY-MM (verilmezse mevcut en eski veriden)")
    p.add_argument("--bitis", default=BITIS_VARSAYILAN, help="YYYY-MM-DD (hariç), varsayılan 2026-11-01")
    p.add_argument("--es-zamanli", type=int, default=3)
    p.add_argument("--aralik", choices=["5m", "1h"], default="5m",
                   help="5m: günlük dakika dosyaları (yavaş); 1h: aylık saatlik dosyalar (hızlı, swing/daytrade için)")
    a = p.parse_args(argv)
    istemci = Istemci()
    for s in a.semboller:
        for tur in range(1, 101):   # sunucu uzun süre kapalı kalabilir: yüksek sesle bekle, önbellekten devam et
            try:
                f = saatlik_indir if a.aralik == "1h" else sembol_indir
                r = f(s, a.baslangic, a.bitis, istemci=istemci, es_zamanli=a.es_zamanli,
                      log=lambda m: print(m, flush=True))
                break
            except AgHatasi as e:
                print(f"{s}: AĞ HATASI (tur {tur}/100): {e}; 60 sn sonra yeniden", flush=True)
                time.sleep(60)
        else:
            raise AgHatasi(f"{s}: 100 tur sonunda vazgeçildi")
        print(f"{s}: {r['ilk']} -> {r['son']}, {r['mum_sayisi']} {a.aralik} mum, başarısız: {len(r['basarisiz'])}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
