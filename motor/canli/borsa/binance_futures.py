"""Minimal imzalı Binance USDⓈ-M vadeli REST istemcisi (HMAC-SHA256).

GÜVENLİK: API anahtarı/gizli yalnız ortam değişkeninden okunur (bkz. canli_ayar). Bu modül gizliyi ASLA loga yazmaz; imzalı
sorgu dizgisi (signature=...) hiçbir log/hata metninde görünmez (`temizle`). Ağ hata metinleri (URL taşıyabilir) loglanmaz,
yalnız istisna türü adı loglanır.

YENİDEN DENEME POLİTİKASI: okuma/iptal/ayar istekleri yalnız ağ hatası, HTTP 5xx ve -1021 için (üstel geri çekilme) tekrar denenir.
EMİR VEREN POST'LAR (/fapi/v1/order, /fapi/v1/algoOrder) ağ hatası/zaman aşımı/5xx'te ASLA OTOMATİK TEKRAR EDİLMEZ: newClientOrderId yalnız
AÇIK emirler arasında benzersizdir, dolmuş bir piyasa emri aynı kimlikle yeniden gönderilirse ikinci kez dolar (çift pozisyon). Belirsiz sonuç
`belirsiz=True` BorsaHata olarak yükselir; çağıran (yürütücü) emri kimlikle SORGULAR ve yalnız borsa "böyle emir yok" derse yeniden gönderir.
Yalnız -1021 (reddedildi, işlenmedi) emir POST'unda da güvenle tekrar denenir. Emir reddi / diğer 4xx kodlarında tekrar yok.

KOŞULLU EMİRLER (STOP_MARKET / TAKE_PROFIT_MARKET): Binance 2025-12'den itibaren USDⓈ-M'de bunları "Algo Order" uçlarına taşıdı
(/fapi/v1/algoOrder). `kosullu_modu="algo"` (varsayılan) o uçları, "klasik" eski /fapi/v1/order ucunu kullanır. Uç/parametre adları
TESTNET'te doğrulanmalıdır (bu geliştirme ortamından Binance'e erişim yoktur; testler sahte HTTP ile yazıldı).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import time
from decimal import Decimal
from typing import Callable, Optional
from urllib.parse import urlencode

log = logging.getLogger("canli.borsa")

TESTNET = "https://testnet.binancefuture.com"
CANLI = "https://fapi.binance.com"
TABANLAR = {"testnet": TESTNET, "canli": CANLI}
AGIRLIK_ESIGI = 1800                 # dakikalık ağırlık 2400; %75'te bekle
ISTEK_ZAMAN_ASIMI = 20
IDEMPOTENT_KODLAR = {-4046, -4059}   # "değiştirmeye gerek yok" (marj tipi / pozisyon modu zaten istenen)
YOK_KODLARI = {-2013, -2011}         # emir yok / iptal edilecek emir yok

_IMZA = re.compile(r"signature=[0-9a-fA-F]+", re.I)


def temizle(metin) -> str:
    """Log/hata metninden imzayı (ve varsa anahtar başlığını) siler."""
    return _IMZA.sub("signature=***", str(metin))


def imzala(sorgu: str, gizli: str) -> str:
    """HMAC-SHA256(gizli, sorgu) onaltılık. Binance dokümantasyon örneğiyle test edilir."""
    return hmac.new(gizli.encode(), sorgu.encode(), hashlib.sha256).hexdigest()


def duz(x) -> str:
    """Sayıyı bilimsel gösterimsiz metne çevirir (Decimal / float / int)."""
    if isinstance(x, Decimal):
        return format(x.normalize(), "f") if x != 0 else "0"
    if isinstance(x, float):
        return format(Decimal(repr(x)).normalize(), "f")
    return str(x)


class BorsaHata(Exception):
    """Borsa isteği başarısız. `kod`: Binance hata kodu (varsa), `http`: HTTP durumu, `belirsiz`: emir borsada oluşmuş olabilir."""

    def __init__(self, mesaj: str, kod: Optional[int] = None, http: Optional[int] = None, belirsiz: bool = False):
        super().__init__(temizle(mesaj))
        self.kod, self.http, self.belirsiz = kod, http, belirsiz


class EmirReddi(BorsaHata):
    """Borsa isteği açıkça reddetti (tekrar YOK)."""


class BorsaYasagi(BorsaHata):
    """429/418: rate limit ya da IP yasağı."""


class BinanceFutures:
    def __init__(self, ortam: str = "testnet", anahtar: str = "", gizli: str = "", oturum=None, uyku: Callable = time.sleep,
                 saat: Callable = time.time, recv_window: int = 5000, max_deneme: int = 4, kosullu_modu: str = "algo",
                 taban: Optional[str] = None):
        if ortam not in TABANLAR and taban is None:
            raise ValueError(f"ortam testnet|canli olmalı: {ortam!r}")
        if kosullu_modu not in ("algo", "klasik"):
            raise ValueError("kosullu_modu algo|klasik")
        self.ortam = ortam
        self.taban = taban or TABANLAR[ortam]
        self._anahtar, self._gizli = anahtar, gizli
        if oturum is None:
            import requests
            oturum = requests.Session()
        self.oturum, self.uyku, self.saat = oturum, uyku, saat
        self.recv_window, self.max_deneme, self.kosullu_modu = recv_window, max_deneme, kosullu_modu
        self.zaman_farki_ms: Optional[int] = None
        self.kullanilan_agirlik, self.agirlik_zamani = 0, 0.0
        self.yasak_bitis = 0.0

    def __repr__(self) -> str:                      # anahtar/gizli asla gösterilmez
        return f"BinanceFutures(ortam={self.ortam!r}, taban={self.taban!r})"

    # ------------------------------------------------------------------ çekirdek
    def zaman_esitle(self) -> int:
        r = self._ham("GET", "/fapi/v1/time", {}, imzali=False)
        self.zaman_farki_ms = int(r["serverTime"]) - int(self.saat() * 1000)
        return self.zaman_farki_ms

    def _agirlik_bekle(self) -> None:
        simdi = self.saat()
        if simdi < self.yasak_bitis:
            raise BorsaYasagi(f"IP yasağı/rate limit sürüyor ({self.yasak_bitis - simdi:.0f} sn)", http=418)
        if simdi - self.agirlik_zamani >= 60:
            self.kullanilan_agirlik = 0
        if self.kullanilan_agirlik >= AGIRLIK_ESIGI:
            bekle = max(1.0, 60 - (simdi - self.agirlik_zamani))
            log.warning("rate limit: ağırlık %d >= %d; %.0f sn bekleniyor", self.kullanilan_agirlik, AGIRLIK_ESIGI, bekle)
            self.uyku(bekle)
            self.kullanilan_agirlik = 0

    def _ham(self, yontem: str, yol: str, params: dict, imzali: bool = True, tekrar_guvenli: bool = True):
        """tekrar_guvenli=False (emir veren POST): ağ hatası/5xx tek denemede `belirsiz` hata olarak yükselir."""
        son = None
        for deneme in range(1, self.max_deneme + 1):
            self._agirlik_bekle()
            p = dict(params)
            basliklar = {}
            if imzali:
                if not self._anahtar or not self._gizli:
                    raise BorsaHata("API anahtarı/gizli tanımlı değil (ortam değişkeni)")
                if self.zaman_farki_ms is None:
                    self.zaman_esitle()
                p["recvWindow"] = self.recv_window
                p["timestamp"] = int(self.saat() * 1000) + (self.zaman_farki_ms or 0)
                sorgu = urlencode(p)
                sorgu += "&signature=" + imzala(sorgu, self._gizli)
                basliklar["X-MBX-APIKEY"] = self._anahtar
            else:
                sorgu = urlencode(p)
            url = self.taban + yol + ("?" + sorgu if sorgu else "")
            try:
                r = self.oturum.request(yontem, url, headers=basliklar, timeout=ISTEK_ZAMAN_ASIMI)
            except Exception as e:  # noqa: BLE001  (ağ hatası: yalnız tür adı loglanır — metin URL/imza taşıyabilir; tekrar denenir)
                son = BorsaHata(f"{yontem} {yol} ağ hatası: {type(e).__name__}", belirsiz=True)
                if not tekrar_guvenli:
                    raise son from None
                bekle = min(2 ** deneme, 30)
                log.warning("%s %s ağ hatası %s (%d/%d); %d sn sonra tekrar", yontem, yol, type(e).__name__, deneme, self.max_deneme, bekle)
                self.uyku(bekle)
                continue
            w = r.headers.get("X-MBX-USED-WEIGHT-1M") if getattr(r, "headers", None) else None
            if w is not None:
                self.kullanilan_agirlik, self.agirlik_zamani = int(w), self.saat()
            if r.status_code == 200:
                return r.json()
            kod, mesaj = None, ""
            try:
                j = r.json()
                kod, mesaj = j.get("code"), str(j.get("msg", ""))[:200]
            except Exception:  # noqa: BLE001  (gövde JSON değil: durum kodu yeter)
                mesaj = ""
            if r.status_code in (429, 418):
                bekle = int(r.headers.get("Retry-After", 60))
                self.yasak_bitis = self.saat() + bekle
                raise BorsaYasagi(f"{r.status_code} {yol} rate limit/yasak; Retry-After={bekle} sn", kod, r.status_code)
            if kod == -1021 and deneme < self.max_deneme:            # zaman damgası penceresi dışında: saati eşitle, tekrar dene
                log.warning("%s %s: -1021 zaman damgası; sunucu saatiyle eşitleniyor", yontem, yol)
                self.zaman_esitle()
                continue
            if 500 <= r.status_code < 600:
                son = BorsaHata(f"{yontem} {yol} sunucu hatası {r.status_code}", kod, r.status_code, belirsiz=True)
                if not tekrar_guvenli:
                    raise son
                bekle = min(2 ** deneme, 30)
                log.warning("%s %s HTTP %d (%d/%d); %d sn sonra tekrar", yontem, yol, r.status_code, deneme, self.max_deneme, bekle)
                self.uyku(bekle)
                continue
            raise EmirReddi(f"{yontem} {yol} reddedildi: HTTP {r.status_code} kod={kod} {mesaj}", kod, r.status_code)
        raise BorsaHata(f"{yontem} {yol}: {self.max_deneme} denemede başarısız: {son}", belirsiz=True)

    def _get(self, yol, params=None, imzali=True):
        return self._ham("GET", yol, params or {}, imzali)

    # ------------------------------------------------------------------ herkese açık
    def sunucu_zamani(self) -> int:
        return int(self._get("/fapi/v1/time", imzali=False)["serverTime"])

    def exchange_info(self) -> dict:
        return self._get("/fapi/v1/exchangeInfo", imzali=False)

    def mark_fiyat(self, sembol: str) -> Decimal:
        return Decimal(str(self._get("/fapi/v1/premiumIndex", {"symbol": sembol}, imzali=False)["markPrice"]))

    # ------------------------------------------------------------------ hesap
    def bakiye(self) -> dict:
        """-> {'ozsermaye': marj bakiyesi (cüzdan + gerçekleşmemiş K/Z), 'kullanilabilir', 'cuzdan'} (USDT, Decimal)."""
        a = self._get("/fapi/v2/account")
        return {"ozsermaye": Decimal(str(a["totalMarginBalance"])), "kullanilabilir": Decimal(str(a["availableBalance"])),
                "cuzdan": Decimal(str(a["totalWalletBalance"]))}

    def pozisyonlar(self) -> list:
        """Açık pozisyonlar: [{'sembol', 'miktar' (işaretli), 'giris', 'mark', 'marj_tipi'}]."""
        out = []
        for x in self._get("/fapi/v2/positionRisk"):
            q = Decimal(str(x["positionAmt"]))
            if q != 0:
                out.append({"sembol": x["symbol"], "miktar": q, "giris": Decimal(str(x["entryPrice"])),
                            "mark": Decimal(str(x["markPrice"])), "marj_tipi": str(x.get("marginType", "")).upper()})
        return out

    @staticmethod
    def _norm(x: dict, kosullu: bool) -> dict:
        if kosullu and "algoId" in x:
            return {"id": str(x["algoId"]), "client_id": x.get("clientAlgoId", ""), "sembol": x["symbol"], "tur": x.get("orderType", x.get("type", "")),
                    "yon": x["side"], "miktar": Decimal(str(x.get("quantity", "0"))), "tetik": Decimal(str(x.get("triggerPrice", "0"))),
                    "reduce_only": bool(x.get("reduceOnly", False)) or bool(x.get("closePosition", False)),
                    "durum": x.get("algoStatus", x.get("status", "")), "kosullu": True}
        return {"id": str(x["orderId"]), "client_id": x.get("clientOrderId", ""), "sembol": x["symbol"], "tur": x.get("origType", x.get("type", "")),
                "yon": x["side"], "miktar": Decimal(str(x.get("origQty", "0"))), "tetik": Decimal(str(x.get("stopPrice", "0"))),
                "reduce_only": bool(x.get("reduceOnly", False)) or bool(x.get("closePosition", False)),
                "durum": x.get("status", ""), "kosullu": kosullu, "dolan": Decimal(str(x.get("executedQty", "0"))),
                "ort_fiyat": Decimal(str(x.get("avgPrice", "0")))}

    def emirler(self, sembol: Optional[str] = None) -> list:
        """Açık emirler (normal + koşullu), normalize."""
        p = {"symbol": sembol} if sembol else {}
        out = [self._norm(x, False) for x in self._get("/fapi/v1/openOrders", p)]
        if self.kosullu_modu == "algo":
            out += [self._norm(x, True) for x in self._get("/fapi/v1/openAlgoOrders", p)]
        return out

    # ------------------------------------------------------------------ hazırlık
    def hazirla(self, sembol: str, kaldirac: int) -> None:
        """Tek yönlü (one-way) mod, ISOLATED marj, kaldıraç. 'zaten öyle' hataları (-4046/-4059) sorun değildir."""
        for yol, p in (("/fapi/v1/positionSide/dual", {"dualSidePosition": "false"}),
                       ("/fapi/v1/marginType", {"symbol": sembol, "marginType": "ISOLATED"})):
            try:
                self._ham("POST", yol, p)
            except EmirReddi as e:
                if e.kod not in IDEMPOTENT_KODLAR:
                    raise
        self._ham("POST", "/fapi/v1/leverage", {"symbol": sembol, "leverage": int(kaldirac)})

    # ------------------------------------------------------------------ emirler
    def piyasa(self, sembol: str, yon: str, miktar: Decimal, client_id: str, reduce_only: bool = False) -> dict:
        p = {"symbol": sembol, "side": yon, "type": "MARKET", "quantity": duz(miktar), "newClientOrderId": client_id,
             "newOrderRespType": "RESULT"}
        if reduce_only:
            p["reduceOnly"] = "true"
        return self._norm(self._ham("POST", "/fapi/v1/order", p, tekrar_guvenli=False), False)

    def kosullu(self, sembol: str, tur: str, yon: str, miktar: Decimal, tetik: Decimal, client_id: str,
                working_type: str = "MARK_PRICE") -> dict:
        """STOP_MARKET / TAKE_PROFIT_MARKET, her zaman reduceOnly. `yon`: kapatan taraf (long pozisyon için SELL)."""
        if tur not in ("STOP_MARKET", "TAKE_PROFIT_MARKET"):
            raise ValueError(tur)
        if working_type not in ("MARK_PRICE", "CONTRACT_PRICE"):
            raise ValueError(working_type)
        if self.kosullu_modu == "algo":
            p = {"algoType": "CONDITIONAL", "symbol": sembol, "side": yon, "type": tur, "quantity": duz(miktar),
                 "triggerPrice": duz(tetik), "workingType": working_type, "reduceOnly": "true", "clientAlgoId": client_id}
            return self._norm(self._ham("POST", "/fapi/v1/algoOrder", p, tekrar_guvenli=False), True)
        p = {"symbol": sembol, "side": yon, "type": tur, "quantity": duz(miktar), "stopPrice": duz(tetik),
             "workingType": working_type, "reduceOnly": "true", "newClientOrderId": client_id}
        return self._norm(self._ham("POST", "/fapi/v1/order", p, tekrar_guvenli=False), False)

    def sorgula(self, sembol: str, client_id: str) -> Optional[dict]:
        """clientOrderId ile emir; yoksa None. Normal ve koşullu uçlara bakar."""
        try:
            return self._norm(self._get("/fapi/v1/order", {"symbol": sembol, "origClientOrderId": client_id}), False)
        except EmirReddi as e:
            if e.kod not in YOK_KODLARI:
                raise
        if self.kosullu_modu == "algo":
            try:
                return self._norm(self._get("/fapi/v1/algoOrder", {"clientAlgoId": client_id}), True)
            except EmirReddi as e:
                if e.kod not in YOK_KODLARI:
                    raise
        return None

    def iptal(self, sembol: str, client_id: str, kosullu: bool = True) -> None:
        try:
            if kosullu and self.kosullu_modu == "algo":
                self._ham("DELETE", "/fapi/v1/algoOrder", {"clientAlgoId": client_id})
            else:
                self._ham("DELETE", "/fapi/v1/order", {"symbol": sembol, "origClientOrderId": client_id})
        except EmirReddi as e:
            if e.kod not in YOK_KODLARI:
                raise

    def hepsini_iptal(self, sembol: str) -> None:
        self._ham("DELETE", "/fapi/v1/allOpenOrders", {"symbol": sembol})
        if self.kosullu_modu == "algo":
            self._ham("DELETE", "/fapi/v1/algoOpenOrders", {"symbol": sembol})
