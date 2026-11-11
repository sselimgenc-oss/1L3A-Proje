"""`kuru` modu: hiçbir şey borsaya gönderilmez. Aynı arayüzü (BinanceFutures ile) bellekte taklit eder; emirler loglanır.

Veri (mark fiyat) ve exchangeInfo dışarıdan verilir (herkese açık uçlar; imzalı uç / anahtar GEREKMEZ). Dolum = verilen mark fiyat.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Callable

from motor.canli.borsa.binance_futures import BorsaHata

log = logging.getLogger("canli.kuru")
D = Decimal


class KuruBorsa:
    def __init__(self, mark_fn: Callable[[str], Decimal], tahsis: Decimal):
        self.mark_fn, self.cuzdan = mark_fn, D(tahsis)
        self.poz: dict = {}               # sembol -> {"miktar": işaretli, "giris": Decimal}
        self.acik: dict = {}              # client_id -> normalize emir
        self.gonderilen: list = []        # (kuru) log: gönderilecek olan emirler
        self.no = 0

    def __repr__(self) -> str:
        return "KuruBorsa()"

    def mark_fiyat(self, sembol): return D(self.mark_fn(sembol))

    def bakiye(self) -> dict:
        kz = sum(((self.mark_fiyat(s) - p["giris"]) * p["miktar"] for s, p in self.poz.items()), D(0))
        return {"ozsermaye": self.cuzdan + kz, "kullanilabilir": self.cuzdan, "cuzdan": self.cuzdan}

    def pozisyonlar(self) -> list:
        return [{"sembol": s, "miktar": p["miktar"], "giris": p["giris"], "mark": self.mark_fiyat(s), "marj_tipi": "ISOLATED"} for s, p in self.poz.items()]

    def emirler(self, sembol=None) -> list:
        return [o for o in self.acik.values() if sembol in (None, o["sembol"])]

    def hazirla(self, sembol, kaldirac) -> None:
        log.info("KURU hazırla %s ISOLATED one-way x%s", sembol, kaldirac)

    def _id(self) -> str:
        self.no += 1
        return str(self.no)

    def piyasa(self, sembol, yon, miktar, client_id, reduce_only=False) -> dict:
        log.info("KURU piyasa %s %s %s reduceOnly=%s", sembol, yon, miktar, reduce_only)
        self.gonderilen.append(("piyasa", sembol, yon, miktar, client_id))
        px, isaret = self.mark_fiyat(sembol), (1 if yon == "BUY" else -1)
        p = self.poz.get(sembol)
        if reduce_only:
            if p is None:
                raise BorsaHata("kuru: kapatılacak pozisyon yok", kod=-2022)
            miktar = min(miktar, abs(p["miktar"]))
        yeni = (p["miktar"] if p else D(0)) + isaret * miktar
        if p is not None and reduce_only:                 # gerçekleşen K/Z cüzdana yazılır
            self.cuzdan += (px - p["giris"]) * miktar * (1 if p["miktar"] > 0 else -1)
        if yeni == 0:
            self.poz.pop(sembol, None)
            for k in [k for k, o in self.acik.items() if o["sembol"] == sembol]:
                self.acik.pop(k)
        else:
            self.poz[sembol] = {"miktar": yeni, "giris": px if p is None else p["giris"]}
        return {"id": self._id(), "client_id": client_id, "sembol": sembol, "tur": "MARKET", "yon": yon, "miktar": miktar, "tetik": D(0),
                "reduce_only": reduce_only, "durum": "FILLED", "kosullu": False, "dolan": miktar, "ort_fiyat": px}

    def kosullu(self, sembol, tur, yon, miktar, tetik, client_id, working_type="MARK_PRICE") -> dict:
        log.info("KURU %s %s %s %s @ %s reduceOnly", tur, sembol, yon, miktar, tetik)
        self.gonderilen.append((tur, sembol, yon, miktar, tetik, client_id))
        o = {"id": self._id(), "client_id": client_id, "sembol": sembol, "tur": tur, "yon": yon, "miktar": miktar, "tetik": tetik,
             "reduce_only": True, "durum": "NEW", "kosullu": True}
        self.acik[client_id] = o
        return o

    def sorgula(self, sembol, client_id):
        return self.acik.get(client_id)

    def iptal(self, sembol, client_id, kosullu=True) -> None:
        self.acik.pop(client_id, None)

    def hepsini_iptal(self, sembol) -> None:
        for k in [k for k, o in self.acik.items() if o["sembol"] == sembol]:
            self.acik.pop(k)
