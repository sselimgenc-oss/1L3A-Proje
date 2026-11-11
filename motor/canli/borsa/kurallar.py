"""Borsa filtreleri (exchangeInfo) ve SERT_LIMITLER'e uyumlu emir boyutlandırma.

KURAL: miktar HER ZAMAN aşağı yuvarlanır. Risk bazlı miktar minimumun altında kalırsa YUKARI YUVARLANMAZ (1% risk sınırı
aşılırdı): işlem atlanır (neden `min_tutar_alti`). Nihai emir, YUVARLANMIŞ miktarla ve borsadaki güncel özsermayeyle tekrar
doğrulanır (`sert_limit_ihlalleri`): işlem başı risk (maliyet dahil) <= %1, toplam açık stop riski <= %5, brüt <= 3x.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Optional

from motor.risk.limitler import SERT_LIMITLER, maliyetli_risk_birim

D = Decimal
STOP_UZAKLIK_MAKS = D("0.25")        # |giriş-stop|/giriş bunu aşarsa atla (3x izole kaldıraçta tasfiye ~%33'te; stop ondan önce olmalı)


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
    neden: Optional[str]         # None: tamam; aksi halde atlama nedeni ('min_tutar_alti', 'risk_yok', ...)
    ayrinti: str = ""
    risk_yuzde: float = 0.0      # nihai miktarın maliyet dahil işlem başı riski (% özsermaye)
    brut_kat: float = 0.0        # emir SONRASI brüt / özsermaye


def sert_limit_ihlalleri(*, qty: Decimal, giris: Decimal, stop: Decimal, ozsermaye: Decimal, stop_kayma: Decimal, taker: Decimal,
                         grup_payi: Decimal = D(1), diger_brut: Decimal = D(0), diger_stop_riski: Decimal = D(0), limitler=SERT_LIMITLER) -> list:
    """Nihai (yuvarlanmış) miktarın SERT_LIMITLER ihlalleri; boş liste = uyumlu. Aşırı küçük toleransla (1e-9) karşılaştırır."""
    out = []
    if ozsermaye <= 0:
        return ["ozsermaye_yok"]
    tol = D("1e-9")
    risk = qty * maliyetli_risk_birim(giris, stop, stop_kayma, taker) / ozsermaye * 100
    if risk > D(limitler.islem_basi_max_risk_yuzde) + tol:
        out.append(f"islem_basi_risk %{risk:.4f} > %{limitler.islem_basi_max_risk_yuzde}")
    toplam = (diger_stop_riski + qty * abs(giris - stop)) / ozsermaye * 100
    if toplam > D(limitler.portfoy_toplam_risk_yuzde) + tol:
        out.append(f"toplam_stop_riski %{toplam:.4f} > %{limitler.portfoy_toplam_risk_yuzde}")
    brut = (diger_brut + qty * giris) / ozsermaye
    if brut > D(str(limitler.max_kaldirac)) + tol:
        out.append(f"brut_kaldirac {brut:.4f}x > {limitler.max_kaldirac}x")
    return out


def boyutlandir(*, ozsermaye: Decimal, tahsis: Decimal, yon: int, giris: Decimal, stop: Decimal, kural: SembolKurali,
                risk_oran: Decimal, grup_payi: Decimal = D(1), stop_kayma: Decimal, taker: Decimal,
                diger_brut: Decimal = D(0), diger_stop_riski: Decimal = D(0), limitler=SERT_LIMITLER) -> Boyut:
    """Paper motorunun sinyal kolu formülü (`PaperMotor._istenen_qty`): qty = E·pay·risk_oran / (|giriş-stop| + max(giriş,stop)·(stop_kayma+2·taker)),
    E = min(borsa özsermayesi, tahsis edilen sermaye). Üstüne toplam stop riski (%5) ve brüt (3x) tavanları, sonra borsa filtreleri."""
    E = min(D(ozsermaye), D(tahsis))
    if E <= 0:
        return Boyut(D(0), "ozsermaye_yok", f"özsermaye {ozsermaye}")
    if (yon == 1 and stop >= giris) or (yon == -1 and stop <= giris) or yon not in (1, -1):
        return Boyut(D(0), "gecersiz_stop", f"yon={yon} giris={giris} stop={stop}")
    if abs(giris - stop) / giris > STOP_UZAKLIK_MAKS:
        return Boyut(D(0), "stop_cok_uzak", f"|giris-stop|/giris > {STOP_UZAKLIK_MAKS}")
    r_oran = min(D(risk_oran), D(limitler.islem_basi_max_risk_yuzde) / 100)
    qty_r = E * grup_payi * r_oran / maliyetli_risk_birim(giris, stop, stop_kayma, taker)
    qty_t = (D(limitler.portfoy_toplam_risk_yuzde) / 100 * E - diger_stop_riski) / abs(giris - stop)
    qty_g = (D(str(limitler.max_kaldirac)) * E - diger_brut) / giris
    ham = min(qty_r, qty_t, qty_g)
    if ham <= 0:
        return Boyut(D(0), "risk_butcesi_dolu", f"toplam stop riski/brüt tavanı dolu (qty_t={qty_t:.8f}, qty_g={qty_g:.8f})")
    qty = miktar_yuvarla(ham, kural)
    if qty < kural.market_min or qty <= 0 or qty * giris < kural.min_notional:
        return Boyut(D(0), "min_tutar_alti", f"risk bazlı miktar {ham:.8f} -> yuvarlanmış {qty} (min miktar {kural.market_min}, "
                                              f"min tutar {kural.min_notional}, tutar {qty * giris:.4f}); YUKARI YUVARLANMAZ")
    ihlal = sert_limit_ihlalleri(qty=qty, giris=giris, stop=stop, ozsermaye=E, stop_kayma=stop_kayma, taker=taker, grup_payi=grup_payi,
                                 diger_brut=diger_brut, diger_stop_riski=diger_stop_riski, limitler=limitler)
    # işlem başı risk grup payına göre E·pay üzerinden hesaplandı; ihlal kontrolü tam E üzerinden (daha sıkı değil, eşit/gevşek olamaz): pay<=1
    if ihlal:
        return Boyut(D(0), "sert_limit", "; ".join(ihlal))
    risk = float(qty * maliyetli_risk_birim(giris, stop, stop_kayma, taker) / E * 100)
    return Boyut(qty, None, "", risk, float((diger_brut + qty * giris) / E))
