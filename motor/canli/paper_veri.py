"""Binance USDⓈ-M vadeli herkese açık REST veri istemcisi (API anahtarı YOK, imzalı uç YOK).

Uçlar: /fapi/v1/klines, /fapi/v1/fundingRate, /fapi/v1/exchangeInfo, /fapi/v1/time. Hepsi herkese açıktır.

Rate limit: Binance ağırlık sınırı dakikada 2400'dür. Yanıt başlığındaki `X-MBX-USED-WEIGHT-1M` izlenir; %75'i (1800) aşılırsa
dakika sonuna kadar beklenir. 429 -> `Retry-After` kadar bekle ve tekrar dene; 418 (IP yasağı) -> bekleme süresi loglanır ve
BinanceHata yükselir (otomatik kör tekrar yok). Ağ/5xx hataları üstel geri çekilmeyle `max_deneme` kez denenir, hâlâ
başarısızsa hata YÜKSELİR (sessiz yutma yok). Her yeniden deneme loglanır.

TradFi eşleme: DK_ (Dukascopy) sembol -> Binance TradFi perpetual sembolü. `esleme_dogrula(exchangeInfo)` her biri için
PERPETUAL + TRADING arar; bulamazsa neden döner (strateji 'veri yok' işaretlenir, uydurma yok).
"""
from __future__ import annotations

import functools
import logging
import time
from typing import Callable, Optional

import numpy as np
import pandas as pd

from motor.backtest.motor import SembolKurallari
from motor.canli import paper_takvim as tk

log = logging.getLogger("paper.veri")

FAPI = "https://fapi.binance.com"
WS_TABAN = "wss://fstream.binance.com"
AGIRLIK_ESIGI = 1800
ISTEK_ZAMAN_ASIMI = 20

# Strateji sembolü -> Binance USDⓈ-M sembolü. Kripto kendisi. TradFi: Binance'in kendi arşivindeki (data.binance.vision)
# sembol envanterinde (veri/sembol_envanteri.csv) bulunan karşılıklar; canlı doğrulama exchangeInfo ile yapılır.
ESLEME = {"DK_AAPL": "AAPLUSDT", "DK_MSFT": "MSFTUSDT", "DK_GOOGL": "GOOGLUSDT", "DK_AMZN": "AMZNUSDT", "DK_NVDA": "NVDAUSDT",
          "DK_META": "METAUSDT", "DK_TSLA": "TSLAUSDT", "DK_XAU": "XAUUSDT", "DK_WTI": "CLUSDT", "DK_COPPER": "COPPERUSDT"}


def binance_sembol(sembol: str) -> str:
    return ESLEME.get(sembol, sembol)


class BinanceHata(Exception):
    pass


class FapiIstemci:
    def __init__(self, taban: str = FAPI, oturum=None, uyku: Callable = time.sleep, saat: Callable = time.time,
                 max_deneme: int = 5):
        import requests
        self.taban = taban
        self.oturum = oturum or requests.Session()
        self.uyku, self.saat = uyku, saat
        self.max_deneme = max_deneme
        self.kullanilan_agirlik = 0
        self.agirlik_zamani = 0.0

    def _agirlik_bekle(self):
        simdi = self.saat()
        if simdi - self.agirlik_zamani >= 60:
            self.kullanilan_agirlik = 0
        if self.kullanilan_agirlik >= AGIRLIK_ESIGI:
            bekle = max(1.0, 60 - (simdi - self.agirlik_zamani))
            log.warning("rate limit: dakikalık ağırlık %d >= %d; %.0f sn bekleniyor", self.kullanilan_agirlik, AGIRLIK_ESIGI, bekle)
            self.uyku(bekle)
            self.kullanilan_agirlik = 0

    def get(self, yol: str, params: Optional[dict] = None):
        son_hata = None
        for deneme in range(1, self.max_deneme + 1):
            self._agirlik_bekle()
            try:
                r = self.oturum.get(self.taban + yol, params=params, timeout=ISTEK_ZAMAN_ASIMI)
            except Exception as e:  # noqa: BLE001  (ağ hatası: loglanır, tekrar denenir, sonunda yükseltilir)
                son_hata = e
                bekle = min(2 ** deneme, 60)
                log.warning("GET %s ağ hatası (%d/%d): %r; %d sn sonra tekrar", yol, deneme, self.max_deneme, e, bekle)
                self.uyku(bekle)
                continue
            w = r.headers.get("X-MBX-USED-WEIGHT-1M")
            if w is not None:
                self.kullanilan_agirlik, self.agirlik_zamani = int(w), self.saat()
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                bekle = int(r.headers.get("Retry-After", 60))
                log.warning("GET %s 429 (rate limit); Retry-After=%s sn", yol, bekle)
                self.uyku(bekle)
                son_hata = BinanceHata(f"429 {yol}")
                continue
            if r.status_code == 418:
                raise BinanceHata(f"418 IP yasağı ({yol}); Retry-After={r.headers.get('Retry-After')} sn. Otomatik tekrar yok.")
            if r.status_code == 451:
                raise BinanceHata(f"451 konum kısıtı ({yol}): bu makineden Binance vadeli erişimi engelli. {r.text[:200]}")
            if 500 <= r.status_code < 600:
                son_hata = BinanceHata(f"{r.status_code} {yol}")
                bekle = min(2 ** deneme, 60)
                log.warning("GET %s sunucu hatası %d (%d/%d); %d sn sonra tekrar", yol, r.status_code, deneme, self.max_deneme, bekle)
                self.uyku(bekle)
                continue
            raise BinanceHata(f"{r.status_code} {yol} {params}: {r.text[:300]}")
        raise BinanceHata(f"{yol}: {self.max_deneme} denemede başarısız: {son_hata!r}")

    # ------------------------------------------------------------------ uçlar
    def sunucu_zamani(self) -> pd.Timestamp:
        return pd.Timestamp(self.get("/fapi/v1/time")["serverTime"], unit="ms", tz="UTC")

    def exchange_info(self) -> dict:
        return self.get("/fapi/v1/exchangeInfo")

    def klines(self, sembol: str, aralik: str, bas=None, bit=None, simdi=None) -> pd.DataFrame:
        """[bas, bit) açılış zamanlı KAPANMIŞ mumlar (kapanışı simdi'den önce). 1500'lük sayfalarla."""
        simdi = pd.Timestamp(simdi) if simdi is not None else pd.Timestamp(self.saat(), unit="s", tz="UTC")
        bas_ms = int(pd.Timestamp(bas).value // 10**6) if bas is not None else None
        bit_ms = int(pd.Timestamp(bit).value // 10**6) if bit is not None else None
        satir = []
        while True:
            p = {"symbol": sembol, "interval": aralik, "limit": 1500}
            if bas_ms is not None:
                p["startTime"] = bas_ms
            if bit_ms is not None:
                p["endTime"] = bit_ms
            parca = self.get("/fapi/v1/klines", p)
            if not parca:
                break
            satir += parca
            if len(parca) < 1500:
                break
            bas_ms = parca[-1][0] + 1
        return klines_df(satir, simdi)

    def funding(self, sembol: str, bas=None) -> pd.DataFrame:
        bas_ms = int(pd.Timestamp(bas).value // 10**6) if bas is not None else None
        satir = []
        while True:
            p = {"symbol": sembol, "limit": 1000}
            if bas_ms is not None:
                p["startTime"] = bas_ms
            parca = self.get("/fapi/v1/fundingRate", p)
            if not parca:
                break
            satir += parca
            if len(parca) < 1000:
                break
            bas_ms = parca[-1]["fundingTime"] + 1
        if not satir:
            return pd.DataFrame({"oran": np.array([], dtype=float)}, index=pd.DatetimeIndex([], tz="UTC", name="zaman"))
        df = pd.DataFrame({"oran": [float(x["fundingRate"]) for x in satir]},
                          index=pd.DatetimeIndex([pd.Timestamp(x["fundingTime"], unit="ms", tz="UTC") for x in satir], name="zaman"))
        return df[~df.index.duplicated(keep="last")].sort_index()


def klines_df(satir: list, simdi: pd.Timestamp) -> pd.DataFrame:
    """Binance kline dizisi -> araştırma verisiyle aynı sütunlar. Henüz kapanmamış mum (closeTime >= simdi) ATILIR."""
    kolon = ["acilis", "yuksek", "dusuk", "kapanis", "hacim", "quote_hacim", "islem_sayisi"]
    if not satir:
        return pd.DataFrame({c: np.array([], dtype=float) for c in kolon}, index=pd.DatetimeIndex([], tz="UTC", name="zaman"))
    simdi_ms = int(simdi.value // 10**6)
    k = [x for x in satir if int(x[6]) < simdi_ms]
    idx = pd.DatetimeIndex([pd.Timestamp(int(x[0]), unit="ms", tz="UTC") for x in k], name="zaman")
    df = pd.DataFrame({"acilis": [float(x[1]) for x in k], "yuksek": [float(x[2]) for x in k], "dusuk": [float(x[3]) for x in k],
                       "kapanis": [float(x[4]) for x in k], "hacim": [float(x[5]) for x in k],
                       "quote_hacim": [float(x[7]) for x in k], "islem_sayisi": [int(x[8]) for x in k]}, index=idx)
    df["islem_sayisi"] = df["islem_sayisi"].astype("int64")
    return df[~df.index.duplicated(keep="last")].sort_index()


# ---------------------------------------------------------------------------- exchangeInfo filtreleri
def kurallar_cikar(bilgi: dict) -> dict:
    """exchangeInfo -> {binance_sembol: SembolKurallari}. Piyasa emri filtreleri (MARKET_LOT_SIZE) varsa onlar, yoksa LOT_SIZE."""
    out = {}
    for s in bilgi.get("symbols", []):
        f = {x["filterType"]: x for x in s.get("filters", [])}
        if "PRICE_FILTER" not in f or ("LOT_SIZE" not in f and "MARKET_LOT_SIZE" not in f):
            continue
        lot = f.get("MARKET_LOT_SIZE") or f["LOT_SIZE"]
        if float(lot.get("stepSize", 0)) == 0:
            lot = f["LOT_SIZE"]
        mn = f.get("MIN_NOTIONAL", {})
        out[s["symbol"]] = SembolKurallari(tick_size=float(f["PRICE_FILTER"]["tickSize"]), step_size=float(lot["stepSize"]),
                                            min_qty=float(lot["minQty"]), min_notional=float(mn.get("notional", 5.0)))
    return out


# Binance TradFi (hisse/emtia) sürekli sözleşmeleri exchangeInfo'da "TRADIFI_PERPETUAL" türüyle gelir (sunucuda görüldü, 2026-11-07).
SUREKLI_TURLER = ("PERPETUAL", "TRADIFI_PERPETUAL")
TRADFI_TURU = "TRADIFI_PERPETUAL"


def tradfi_mi(sembol: str) -> bool:
    """Strateji sembolü Binance TradFi perpetual'ında mı işlem görür? Projede TradFi sembolleri `DK_` önekli (Dukascopy araştırma verisi);
    canlı karşılıkları ESLEME'de. Funding'i araştırmada YOKTUR (kullanıcı kararı 2026-11-09: paper öder, ayrı tutar, beklenti kıyası hariç)."""
    return sembol.startswith("DK_")


def tradfi_sinif_uyusmazliklari(bilgi: dict, sembollar: list) -> list:
    """exchangeInfo contractType (TRADIFI_PERPETUAL) ile `tradfi_mi` sınıflaması çelişen semboller için açıklama listesi (boş: tutarlı).
    exchangeInfo'da olmayan sembol burada sayılmaz (esleme_dogrula 'veri yok' yapar)."""
    tablo = {s["symbol"]: s for s in bilgi.get("symbols", [])}
    out = []
    for s in sembollar:
        x = tablo.get(binance_sembol(s))
        if x is not None and (x.get("contractType") == TRADFI_TURU) != tradfi_mi(s):
            out.append(f"{s} ({binance_sembol(s)}): contractType {x.get('contractType')} ama tradfi_mi={tradfi_mi(s)}; "
                       "TradFi funding ayrımı bu sembolde yanlış olabilir")
    return out


def esleme_dogrula(bilgi: dict, sembollar: list) -> dict:
    """Her strateji sembolü için (binance_sembol, None) ya da (None, neden). Sürekli sözleşme (SUREKLI_TURLER) + TRADING aranır."""
    tablo = {s["symbol"]: s for s in bilgi.get("symbols", [])}
    out = {}
    for s in sembollar:
        b = binance_sembol(s)
        x = tablo.get(b)
        if x is None:
            out[s] = (None, f"{b} Binance USDⓈ-M exchangeInfo'da yok")
        elif x.get("contractType") not in SUREKLI_TURLER:
            out[s] = (None, f"{b} sürekli sözleşme değil ({x.get('contractType')})")
        elif x.get("status") != "TRADING":
            out[s] = (None, f"{b} durumu {x.get('status')} (TRADING değil)")
        else:
            out[s] = (b, None)
    return out


# ---------------------------------------------------------------------------- mum çerçeveleri
def mumlar(ist: FapiIstemci, sembol: str, tf: str, bas, simdi) -> pd.DataFrame:
    """Strateji sembolü + tf için araştırma verisiyle AYNI yapıda mum çerçevesi (kapanmış barlar).
    Kripto: doğrudan klines. TradFi (DK_): Binance TradFi perp 5m mumları -> seans süzgeci (paper_takvim) -> seans modunda
    yeniden örnekleme (motor.veri.yeniden_ornekle, araştırma ile aynı kural) -> kapanmamış kova atılır."""
    from motor.veri.depo import aralik_suresi
    from motor.veri.yeniden_ornekle import _seans_ayari, yeniden_ornekle
    b = binance_sembol(sembol)
    if tk.tur(sembol) == "kripto":
        return ist.klines(b, tf, bas, None, simdi)
    ham = ist.klines(b, "5m", bas, None, simdi)
    ham = ham[tk.seans_maskesi(sembol, ham.index)]
    if not len(ham):
        return ham
    if tf == "5m":
        return ham
    # 'eksik' eşiği SABİT beklenen mum sayısından (takvimden) türetilir: canlı pencere 1-2 gündür, medyanı araştırmadaki uzun
    # geçmişin medyanını temsil etmez (ör. yalnız Pazar kovası içeren pencerede Pazar emtia barı 'tam' sayılırdı; araştırmada atılır).
    df = yeniden_ornekle(ham, tf, kaynak="5m", eksikleri_at=True, beklenen_sayi=beklenen_mum_sayisi(sembol, tf), **_seans_ayari(sembol))
    # kova sonu: yerel hizalı 4h kovalarında kapanış = açılış + tf; kapanmamış kovayı at
    kapanis = df.index + aralik_suresi(tf)
    return df[kapanis <= pd.Timestamp(simdi)]


# ---------------------------------------------------------------------------- seanslı kovalarda beklenen mum sayısı
BEKLENEN_REFERANS = ("2024-01-01", "2025-01-01")      # takvim referans dönemi (1 yıl: DST'nin iki yarısı + tatiller; medyan sağlam)


@functools.lru_cache(maxsize=None)
def beklenen_mum_sayisi(sembol: str, tf: str) -> float:
    """Seanslı sembolün `tf` kovasındaki TAM seans 5m mum sayısı: referans yılın 5m ızgarası seans süzgecinden (paper_takvim) geçirilir,
    `yeniden_ornekle` ile AYNI kova kuralıyla sayılır ve MEDYAN alınır. Araştırma yolu aynı kuralı uzun geçmişin gerçek medyanıyla
    uygular; tam veride ikisi aynı sayıdır. Böylece canlı (kısa pencere) ve araştırma aynı 'eksik' kararını verir."""
    from motor.veri.depo import aralik_suresi
    from motor.veri.yeniden_ornekle import _seans_ayari, kova_anahtari
    izgara = pd.date_range(*BEKLENEN_REFERANS, freq="5min", tz="UTC", inclusive="left")
    izgara = izgara[tk.seans_maskesi(sembol, izgara)]
    anahtar = kova_anahtari(izgara, aralik_suresi(tf), _seans_ayari(sembol).get("yerel"))
    anahtar = anahtar[~anahtar.isna()]
    return float(pd.Series(1, index=anahtar).groupby(level=0).count().median())


def kova_bekleniyor(sembol: str, tf: str, t) -> bool:
    """`t` açılışlı `tf` kovasında bu sembolün (eksik sayılmayacak) bir mumu beklenir mi? Kripto: her zaman. Seanslı: kovadaki seans
    5m mumu sayısı >= SEANS_ESIK_ORANI x beklenen (yeniden_ornekle 'eksik' kuralının tersi; hafta sonu/tatil/Pazar emtia kovası: hayır)."""
    if tk.tur(sembol) == "kripto":
        return True
    from motor.veri.depo import aralik_suresi
    from motor.veri.yeniden_ornekle import SEANS_ESIK_ORANI, _seans_ayari, kova_anahtari
    t = pd.Timestamp(t)
    a = aralik_suresi(tf)
    izgara = pd.date_range(t - pd.Timedelta(hours=12), t + a + pd.Timedelta(hours=12), freq="5min", inclusive="left")
    izgara = izgara[tk.seans_maskesi(sembol, izgara)]
    n = int((kova_anahtari(izgara, a, _seans_ayari(sembol).get("yerel")) == t).sum())
    return n >= SEANS_ESIK_ORANI * beklenen_mum_sayisi(sembol, tf)
