"""Borsa filtreleri (exchangeInfo) ve CANLI_LIMITLER'e uyumlu emir boyutlandırma (kullanıcı kararı 2026-11-11; kural ve sayılar
`canli_limitler.py`'de, burada sayı yoktur).

KURAL: miktar HER ZAMAN aşağı yuvarlanır. Hesaplanan miktar minimumun altında kalırsa YUKARI YUVARLANMAZ (kayıp sınırı aşılırdı):
işlem atlanır (neden `min_tutar_alti`). Nihai emir, YUVARLANMIŞ miktarla ve güncel kasayla tekrar doğrulanır (`limit_ihlalleri`).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Optional

from motor.canli.borsa import canli_limitler as cl

D = Decimal


class KuralHatasi(KeyError):
    pass


@dataclass(frozen=True)
class SembolKurali:
    sembol: str
    tick: Decimal
    step: Decimal            # LOT_SIZE
    min_qty: Decimal
    max_qty: Decimal
    market_step: Decimal     # MARKET_LOT_SIZE (yoksa LOT_SIZE)
    market_min: Decimal
    market_max: Decimal
    min_notional: Decimal


def kural_cikar(bilgi: dict, sembol: str) -> SembolKurali:
    """exchangeInfo -> tek sembol kuralı (Decimal). Eksik/bozuk filtre = KuralHatasi (tahmin yok)."""
    for s in bilgi.get("symbols", []):
        if s.get("symbol") != sembol:
            continue
        f = {x["filterType"]: x for x in s.get("filters", [])}
        if "PRICE_FILTER" not in f or "LOT_SIZE" not in f:
            raise KuralHatasi(f"{sembol}: PRICE_FILTER/LOT_SIZE yok")
        lot = f["LOT_SIZE"]
        ml = f.get("MARKET_LOT_SIZE") or lot
        mstep = D(str(ml.get("stepSize", "0")))
        if mstep == 0:
            ml, mstep = lot, D(str(lot["stepSize"]))
        mn = f.get("MIN_NOTIONAL") or f.get("NOTIONAL") or {}
        notional = D(str(mn.get("notional", mn.get("minNotional", "5"))))
        k = SembolKurali(sembol, D(str(f["PRICE_FILTER"]["tickSize"])), D(str(lot["stepSize"])), D(str(lot["minQty"])),
                         D(str(lot.get("maxQty", "1e12"))), mstep, D(str(ml["minQty"])), D(str(ml.get("maxQty", "1e12"))), notional)
        if k.tick <= 0 or k.step <= 0 or k.market_step <= 0:
            raise KuralHatasi(f"{sembol}: tick/step sıfır")
        return k
    raise KuralHatasi(f"{sembol}: exchangeInfo'da yok")


def asagi(x: Decimal, adim: Decimal) -> Decimal:
    return (D(x) / adim).to_integral_value(rounding=ROUND_FLOOR) * adim


def yukari(x: Decimal, adim: Decimal) -> Decimal:
    return (D(x) / adim).to_integral_value(rounding=ROUND_CEILING) * adim


def miktar_yuvarla(qty: Decimal, k: SembolKurali) -> Decimal:
    """Piyasa emri miktarı: MARKET_LOT_SIZE adımına AŞAĞI, üst sınıra kırp."""
    return asagi(min(D(qty), k.market_max), k.market_step)


def stop_yuvarla(stop: Decimal, yon: int, k: SembolKurali) -> Decimal:
    """Koruyucu stop tick'e girişe DOĞRU (sıkı) yuvarlanır: long'da yukarı, short'ta aşağı (risk asla artmaz)."""
    return yukari(stop, k.tick) if yon == 1 else asagi(stop, k.tick)


def hedef_yuvarla(hedef: Decimal, yon: int, k: SembolKurali) -> Decimal:
    """Hedef tick'e girişe doğru (kolay dolum yönü): long'da aşağı, short'ta yukarı."""
    return asagi(hedef, k.tick) if yon == 1 else yukari(hedef, k.tick)


@dataclass(frozen=True)
class Boyut:
    qty: Decimal                 # 0: işlem yok
    neden: Optional[str]         # None: tamam; aksi halde atlama nedeni ('min_tutar_alti', 'gecersiz_stop', ...)
    ayrinti: str = ""
    risk_yuzde: float = 0.0      # nihai miktarın maliyet dahil stopta kaybı (% kasa)
    brut_kat: float = 0.0        # emir SONRASI brüt / kasa
    kaldirac: int = 0            # girişten önce sembole ayarlanacak kaldıraç
    baglayan: str = ""           # miktarı sınırlayan kural (kayip | nominal | marj | toplam_risk | brut)


def boyutlandir(*, ozsermaye: Decimal, tahsis: Decimal, yon: int, giris: Decimal, stop: Decimal, kural: SembolKurali,
                stop_kayma: Decimal, taker: Decimal, diger_brut: Decimal = D(0), diger_stop_riski: Decimal = D(0), kaldirac_ust=None,
                limitler=cl.CANLI_LIMITLER) -> Boyut:
    """kasa = min(borsa özsermayesi, tahsis). Miktar `canli_limitler.miktar_hesapla` ile; borsa filtreleri (MARKET_LOT_SIZE adımı/üst sınırı,
    min miktar, min tutar) burada verilir. Sonra yuvarlanmış miktar `limit_ihlalleri` ile doğrulanır."""
    kasa = min(D(ozsermaye), D(tahsis))
    s = cl.miktar_hesapla(kasa=kasa, yon=yon, giris=giris, stop=stop, stop_kayma=stop_kayma, taker=taker, adim=kural.market_step,
                          min_qty=kural.market_min, min_tutar=kural.min_notional, max_qty=kural.market_max, diger_brut=diger_brut,
                          diger_stop_riski=diger_stop_riski, kaldirac_ust=kaldirac_ust, limitler=limitler)
    if s.neden is not None:
        return Boyut(D(0), s.neden, s.ayrinti, kaldirac=s.kaldirac, baglayan=s.baglayan)
    ihlal = cl.limit_ihlalleri(qty=s.qty, giris=giris, stop=stop, kasa=kasa, stop_kayma=stop_kayma, taker=taker, kaldirac=s.kaldirac,
                               diger_brut=diger_brut, diger_stop_riski=diger_stop_riski, limitler=limitler)
    if ihlal:
        return Boyut(D(0), "sert_limit", "; ".join(ihlal), kaldirac=s.kaldirac, baglayan=s.baglayan)
    risk = float(s.qty * (abs(giris - stop) + cl.birim_maliyet(giris, stop, stop_kayma, taker)) / kasa * 100)
    return Boyut(s.qty, None, "", risk, float((diger_brut + s.qty * giris) / kasa), s.kaldirac, s.baglayan)
