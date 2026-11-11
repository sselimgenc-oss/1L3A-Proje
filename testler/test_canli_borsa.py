"""Canlı Binance yürütücü testleri (motor/canli/borsa). TÜM HTTP SAHTE: ağ yok, gerçek anahtar yok.

Not: `DOKUMAN_*` sabitleri Binance dokümantasyonunun HERKESE AÇIK örnek değerleridir (gerçek anahtar değil); imza algoritmasını
Binance'in yayımladığı beklenen çıktıyla doğrulamak için kullanılır. Diğer testlerdeki 'gizli' değerler uydurmadır.
"""
import inspect
import logging
from decimal import Decimal as D

import pandas as pd
import pytest

from motor.canli.borsa import canli_ayar as ca
from motor.canli.borsa import canli_limitler as cl
from motor.canli.borsa import kurallar as kr
from motor.canli.borsa.binance_futures import (BinanceFutures, BorsaHata, BorsaYasagi, EmirReddi, duz, imzala, temizle)
from motor.canli.borsa.canli_yurutucu import Ayar, MotorGorunumu, Niyet, PozGorunum, Yurutucu, client_id
from motor.canli.borsa.kuru import KuruBorsa
from motor.risk.limitler import SERT_LIMITLER, maliyetli_risk_birim

DOKUMAN_GIZLI = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"
DOKUMAN_SORGU = "symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559"
DOKUMAN_IMZA = "c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71"
UYDURMA_ANAHTAR, UYDURMA_GIZLI = "test-anahtar-0123456789", "test-gizli-ABCDEFGHIJ9876543210"


# ============================================================================================= sahte HTTP
class Yanit:
    def __init__(self, kod=200, govde=None, basliklar=None):
        self.status_code, self._g, self.headers = kod, govde if govde is not None else {}, basliklar or {}
        self.text = str(govde)

    def json(self):
        if isinstance(self._g, Exception):
            raise self._g
        return self._g


class SahteOturum:
    def __init__(self, yanitlar):
        self.yanitlar, self.istekler = list(yanitlar), []

    def request(self, yontem, url, headers=None, timeout=None):
        self.istekler.append((yontem, url, headers or {}))
        y = self.yanitlar.pop(0)
        if isinstance(y, Exception):
            raise y
        return y


def istemci(yanitlar, **kw):
    o = SahteOturum(yanitlar)
    uykular = []
    c = BinanceFutures("testnet", UYDURMA_ANAHTAR, UYDURMA_GIZLI, oturum=o, uyku=uykular.append, saat=lambda: 1_700_000_000.0, **kw)
    c.uykular = uykular
    return c, o


ZAMAN = Yanit(200, {"serverTime": 1_700_000_000_000})


# ============================================================================================= imza ve istemci
def test_imza_dokuman_ornegi():
    assert imzala(DOKUMAN_SORGU, DOKUMAN_GIZLI) == DOKUMAN_IMZA


def test_imzali_istek_biçimi_ve_gizli_sızmaz():
    c, o = istemci([ZAMAN, Yanit(200, {"totalMarginBalance": "1000", "availableBalance": "900", "totalWalletBalance": "1000"})])
    b = c.bakiye()
    assert b["ozsermaye"] == D("1000")
    yontem, url, h = o.istekler[1]
    assert url.startswith("https://testnet.binancefuture.com/fapi/v2/account?")
    assert "recvWindow=5000" in url and "timestamp=" in url and "&signature=" in url
    sorgu, imza = url.split("?")[1].rsplit("&signature=", 1)
    assert imzala(sorgu, UYDURMA_GIZLI) == imza
    assert h["X-MBX-APIKEY"] == UYDURMA_ANAHTAR
    assert UYDURMA_GIZLI not in url and UYDURMA_GIZLI not in repr(c)


def test_varsayilan_testnet_ve_canli_taban():
    assert BinanceFutures().taban == "https://testnet.binancefuture.com"
    assert BinanceFutures("canli").taban == "https://fapi.binance.com"
    with pytest.raises(ValueError):
        BinanceFutures("baska")


def test_5xx_tekrar_denenir_ve_basarili():
    c, o = istemci([ZAMAN, Yanit(503, {}), Yanit(200, {"totalMarginBalance": "5", "availableBalance": "5", "totalWalletBalance": "5"})])
    assert c.bakiye()["ozsermaye"] == D(5)
    assert len(o.istekler) == 3 and c.uykular == [2]


def test_ag_hatasi_tekrar_denenir_hata_metni_url_icermez():
    sizinti = ConnectionError(f"https://x/fapi/v2/account?timestamp=1&signature={'a' * 64}")
    c, o = istemci([ZAMAN, sizinti, sizinti, sizinti, sizinti], max_deneme=4)
    with pytest.raises(BorsaHata) as e:
        c.bakiye()
    assert "a" * 64 not in str(e.value) and "ConnectionError" in str(e.value)
    assert len(o.istekler) == 1 + 4


def test_emir_reddinde_tekrar_yok():
    c, o = istemci([ZAMAN, Yanit(400, {"code": -2019, "msg": "Margin is insufficient."})])
    with pytest.raises(EmirReddi) as e:
        c.piyasa("BTCUSDT", "BUY", D("0.01"), "1l3a-G-x")
    assert e.value.kod == -2019 and len(o.istekler) == 2 and c.uykular == []


def test_1021_zaman_esitler_ve_tekrar_dener():
    c, o = istemci([ZAMAN, Yanit(400, {"code": -1021, "msg": "Timestamp ahead"}), ZAMAN,
                    Yanit(200, {"totalMarginBalance": "1", "availableBalance": "1", "totalWalletBalance": "1"})])
    assert c.bakiye()["ozsermaye"] == D(1)
    assert [x[1].split("?")[0].rsplit("/", 1)[1] for x in o.istekler] == ["time", "account", "time", "account"]


def test_429_yasak_sonraki_istek_bloklanir():
    c, o = istemci([ZAMAN, Yanit(429, {}, {"Retry-After": "30"})])
    with pytest.raises(BorsaYasagi):
        c.bakiye()
    n = len(o.istekler)
    with pytest.raises(BorsaYasagi):
        c.bakiye()
    assert len(o.istekler) == n                            # yasak sürerken hiç istek gitmez


def test_agirlik_esigi_bekletir():
    c, o = istemci([ZAMAN, Yanit(200, {"totalMarginBalance": "1", "availableBalance": "1", "totalWalletBalance": "1"},
                                 {"X-MBX-USED-WEIGHT-1M": "1900"}),
                    Yanit(200, {"totalMarginBalance": "1", "availableBalance": "1", "totalWalletBalance": "1"})])
    c.bakiye()
    c.bakiye()
    assert c.uykular and c.uykular[0] >= 1


def test_koşullu_emir_algo_ve_klasik_parametreleri():
    c, o = istemci([ZAMAN, Yanit(200, {"algoId": 7, "clientAlgoId": "1l3a-S-1", "symbol": "BTCUSDT", "side": "SELL", "orderType": "STOP_MARKET",
                                       "quantity": "0.009", "triggerPrice": "49000", "reduceOnly": True, "algoStatus": "NEW"})])
    o1 = c.kosullu("BTCUSDT", "STOP_MARKET", "SELL", D("0.009"), D("49000"), "1l3a-S-1", "CONTRACT_PRICE")
    url = o.istekler[1][1]
    assert "/fapi/v1/algoOrder?" in url and "algoType=CONDITIONAL" in url and "reduceOnly=true" in url and "workingType=CONTRACT_PRICE" in url
    assert "triggerPrice=49000" in url and "clientAlgoId=1l3a-S-1" in url and o1["tetik"] == D("49000")
    k, o2 = istemci([ZAMAN, Yanit(200, {"orderId": 9, "clientOrderId": "x", "symbol": "BTCUSDT", "side": "SELL", "type": "STOP_MARKET", "origQty": "0.009",
                                        "stopPrice": "49000", "status": "NEW", "reduceOnly": True})], kosullu_modu="klasik")
    k.kosullu("BTCUSDT", "STOP_MARKET", "SELL", D("0.009"), D("49000"), "x")
    u2 = o2.istekler[1][1]
    assert "/fapi/v1/order?" in u2 and "stopPrice=49000" in u2 and "reduceOnly=true" in u2 and "workingType=MARK_PRICE" in u2
    with pytest.raises(ValueError):
        c.kosullu("BTCUSDT", "LIMIT", "SELL", D(1), D(1), "x")


def test_marj_tipi_zaten_isolated_hata_sayilmaz():
    c, o = istemci([ZAMAN, Yanit(400, {"code": -4059, "msg": "No need to change position side."}),
                    Yanit(400, {"code": -4046, "msg": "No need to change margin type."}), Yanit(200, {"leverage": 3})])
    c.hazirla("BTCUSDT", 3)
    urller = [x[1] for x in o.istekler]
    assert any("marginType=ISOLATED" in u for u in urller) and any("dualSidePosition=false" in u for u in urller) and any("leverage=3" in u for u in urller)


def test_temizle_ve_duz():
    assert "deadbeef" not in temizle("x?a=1&signature=deadbeef")
    assert duz(D("0.0090")) == "0.009" and duz(D("1E+2")) == "100" and duz(0.1) == "0.1"


# ============================================================================================= kurallar
def bilgi(tick="0.10", step="0.001", min_notional="100", mstep=None, mmin=None):
    f = [{"filterType": "PRICE_FILTER", "tickSize": tick}, {"filterType": "LOT_SIZE", "stepSize": step, "minQty": "0.001", "maxQty": "1000"},
         {"filterType": "MIN_NOTIONAL", "notional": min_notional}]
    if mstep:
        f.append({"filterType": "MARKET_LOT_SIZE", "stepSize": mstep, "minQty": mmin or mstep, "maxQty": "100"})
    return {"symbols": [{"symbol": "BTCUSDT", "filters": f}]}


def test_kural_cikar_ve_yuvarlama():
    k = kr.kural_cikar(bilgi(mstep="0.01", mmin="0.01"), "BTCUSDT")
    assert (k.tick, k.step, k.market_step, k.min_notional, k.market_max) == (D("0.10"), D("0.001"), D("0.01"), D(100), D(100))
    assert kr.miktar_yuvarla(D("0.0199"), k) == D("0.01")                       # MARKET_LOT_SIZE adımı, aşağı
    assert kr.miktar_yuvarla(D("500"), k) == D(100)                            # üst sınıra kırpılır
    assert kr.stop_yuvarla(D("49000.07"), 1, k) == D("49000.1")                 # long stop sıkı: yukarı
    assert kr.stop_yuvarla(D("51000.07"), -1, k) == D("51000.0")                # short stop sıkı: aşağı
    assert kr.hedef_yuvarla(D("52000.07"), 1, k) == D("52000.0")
    with pytest.raises(kr.KuralHatasi):
        kr.kural_cikar(bilgi(), "YOKUSDT")


COST = dict(stop_kayma=D("0.0005"), taker=D("0.0005"))
Q = D("0.027")        # varsayılan senaryo: kasa 1000, BTC 50000, stop 49000 (%2): kayıp tavanı 30/1075 = 0.0279 -> 0.027 (nominal tavanı 0.03 daha gevşek)


def boyut(E=D(1000), **kw):
    k = kr.kural_cikar(bilgi(), "BTCUSDT")
    a = dict(ozsermaye=E, tahsis=D(1000), yon=1, giris=D(50000), stop=D(49000), kural=k, **COST)
    a.update(kw)
    return kr.boyutlandir(**a), k


def test_boyut_kayip_maliyet_dahil_ve_asagi_yuvarlanmis():
    b, k = boyut()
    assert b.neden is None and b.qty == Q and b.baglayan == "kayip" and b.kaldirac == 3   # ham 30/1075 = 0.0279 -> 0.027 (YUKARI DEĞİL)
    kayip = b.qty * (D(1000) + D(50000) * D("0.0015")) / D(1000)
    assert kayip <= D("0.03") and b.risk_yuzde == pytest.approx(float(kayip * 100))


def test_min_tutar_altinda_yukari_yuvarlanmaz_atlanir():
    b, _ = boyut(E=D(50), tahsis=D(50))                                         # ham 0.0014 -> 0.001, tutar 50 < min 100: atla (yukarı yuvarlanmaz)
    assert b.qty == 0 and b.neden == "min_tutar_alti" and "YUKARI YUVARLANMAZ" in b.ayrinti
    b2, _ = boyut(E=D(500), tahsis=D(500))                                      # ham 0.0139 -> 0.013 -> tutar 650 >= 100
    assert b2.neden is None and b2.qty == D("0.013")
    k = kr.kural_cikar(bilgi(min_notional="2000"), "BTCUSDT")                   # min tutar 2000: 0.027 x 50000 = 1350 < 2000 -> atla
    b3 = kr.boyutlandir(ozsermaye=D(1000), tahsis=D(1000), yon=1, giris=D(50000), stop=D(49000), kural=k, **COST)
    assert b3.neden == "min_tutar_alti" and b3.qty == 0


def test_boyut_tahsis_tavani_ve_nominal_tavani():
    b, _ = boyut(E=D(100000), tahsis=D(1000))
    assert b.qty == Q                                                           # tahsis 1000 ile sınırlı
    b2, _ = boyut(stop=D(49900))                                                # sıkı stop (%0.2): nominal tavanı (1.5x) bağlar, kayıp tavanı değil
    assert b2.qty == D("0.03") and b2.baglayan in ("nominal", "marj")


def test_boyut_toplam_stop_riski_ve_brut_tavani():
    b, _ = boyut(diger_stop_riski=D(55))                                        # %6 = 60 USD; 55 dolu -> kalan 5 USD / 1075 = 0.0046 -> 0.004
    assert b.qty == D("0.004") and b.baglayan == "toplam_risk"
    b2, _ = boyut(diger_stop_riski=D(60))
    assert b2.neden == "risk_butcesi_dolu"
    b3, _ = boyut(diger_brut=D(1400))                                           # brüt 1.5x = 1500; kalan 100 USD / 50000 = 0.002
    assert b3.qty == D("0.002") and b3.baglayan == "brut"
    b4, _ = boyut(diger_brut=D(1500))
    assert b4.neden == "risk_butcesi_dolu"


def test_boyut_gecersiz_ve_uzak_stop():
    assert boyut(stop=D(51000))[0].neden == "gecersiz_stop"
    assert boyut(stop=D(30000))[0].neden == "stop_cok_uzak"
    assert boyut(E=D(0))[0].neden == "kasa_yok"


def test_limit_ihlalleri_yuvarlanmis_miktarla():
    ok = cl.limit_ihlalleri(qty=Q, giris=D(50000), stop=D(49000), kasa=D(1000), kaldirac=3, **COST)
    assert ok == []
    kotu = cl.limit_ihlalleri(qty=D("0.0285"), giris=D(50000), stop=D(49000), kasa=D(1000), kaldirac=3, **COST)   # yukarı yuvarlama %3'ü aşar
    assert any("islem_basi_kayip" in x for x in kotu)
    assert any("nominal" in x or "brut" in x for x in cl.limit_ihlalleri(qty=D("0.04"), giris=D(50000), stop=D(49900), kasa=D(1000), kaldirac=3, **COST))
    assert any("toplam_stop" in x for x in cl.limit_ihlalleri(qty=D("0.001"), giris=D(50000), stop=D(49000), kasa=D(1000), kaldirac=3,
                                                              diger_stop_riski=D(60), **COST))


# ============================================================================================= sahte borsa + yürütücü
class Sahte:
    """Bellekte borsa. Hata enjeksiyonu: stop_hatasi, kapat_hatasi."""

    def __init__(self, ozsermaye="1000", mark=50000):
        self.ozs, self.mark = D(ozsermaye), {"BTCUSDT": D(mark)}
        self.poz, self.acik, self.dolu, self.cagrilar = {}, {}, {}, []
        self.stop_hatasi = self.kapat_hatasi = False
        self.fill_px = None            # dolum fiyatı (kayma enjeksiyonu)
        self.piyasa_mod = None         # None | belirsiz_dolar | belirsiz_dolmaz  (giriş POST'u ağ hatasıyla biter)
        self.sorgu_bozuk = False       # sorgula BorsaHata atar
        self.iptal_hatasi = False
        self.stop_belirsiz_durum = None   # kosullu STOP belirsiz hata atar; sorgula bu durumda kayıt döner

    def bakiye(self): return {"ozsermaye": self.ozs, "kullanilabilir": self.ozs, "cuzdan": self.ozs}
    def mark_fiyat(self, s): return self.mark[s]
    def hazirla(self, s, k): self.cagrilar.append(("hazirla", s, k))

    def pozisyonlar(self):
        return [{"sembol": s, "miktar": q, "giris": self.mark[s], "mark": self.mark[s], "marj_tipi": "ISOLATED"} for s, q in self.poz.items()]

    def emirler(self, s=None): return [o for o in self.acik.values() if s in (None, o["sembol"])]

    def piyasa(self, s, yon, q, cid, reduce_only=False):
        self.cagrilar.append(("piyasa", s, yon, q, cid, reduce_only))
        if reduce_only and self.kapat_hatasi:
            raise EmirReddi("kapat reddedildi", kod=-2022)
        if not reduce_only and self.piyasa_mod and self.piyasa_mod.startswith("belirsiz"):
            mod, self.piyasa_mod = self.piyasa_mod, None
            if mod == "belirsiz_dolar":
                self.piyasa(s, yon, q, cid, reduce_only)
                self.cagrilar.pop()
            raise BorsaHata("ağ hatası", belirsiz=True)
        isaret = 1 if yon == "BUY" else -1
        yeni = self.poz.get(s, D(0)) + isaret * q
        if yeni == 0:
            self.poz.pop(s, None)
        else:
            self.poz[s] = yeni
        o = {"id": str(len(self.dolu)), "client_id": cid, "sembol": s, "tur": "MARKET", "yon": yon, "miktar": q, "tetik": D(0), "reduce_only": reduce_only,
             "durum": "FILLED", "kosullu": False, "dolan": q, "ort_fiyat": self.fill_px or self.mark[s]}
        self.dolu[cid] = o
        return o

    def kosullu(self, s, tur, yon, q, tetik, cid, wt="MARK_PRICE"):
        self.cagrilar.append(("kosullu", s, tur, yon, q, tetik, cid, wt))
        if self.stop_hatasi and tur == "STOP_MARKET":
            raise EmirReddi("Order would immediately trigger.", kod=-2021)
        if self.stop_belirsiz_durum and tur == "STOP_MARKET":
            raise BorsaHata("ağ hatası", belirsiz=True)
        o = {"id": cid, "client_id": cid, "sembol": s, "tur": tur, "yon": yon, "miktar": q, "tetik": tetik, "reduce_only": True, "durum": "NEW", "kosullu": True}
        self.acik[cid] = o
        return o

    def sorgula(self, s, cid):
        if self.sorgu_bozuk:
            raise BorsaHata("sorgu hatası", belirsiz=True)
        if self.stop_belirsiz_durum and cid.startswith("1l3a-S-"):
            return {"client_id": cid, "sembol": s, "tur": "STOP_MARKET", "durum": self.stop_belirsiz_durum, "reduce_only": True, "miktar": D(0), "tetik": D(0)}
        return self.dolu.get(cid) or self.acik.get(cid)

    def iptal(self, s, cid, kosullu=True):
        self.cagrilar.append(("iptal", cid))
        if self.iptal_hatasi:
            raise BorsaHata("iptal hatası", belirsiz=True)
        self.acik.pop(cid, None)

    def hepsini_iptal(self, s):
        self.cagrilar.append(("hepsini_iptal", s))
        if self.iptal_hatasi:
            raise BorsaHata("iptal hatası", belirsiz=True)
        for k in [k for k, o in self.acik.items() if o["sembol"] == s]:
            self.acik.pop(k)

    def adlar(self): return [c[0] for c in self.cagrilar]


T0 = pd.Timestamp("2026-11-11 08:00", tz="UTC")
ARALIK = pd.Timedelta(hours=1)


class Ortam:
    def __init__(self, tmp_path, ozs="1000", tahsis=1000, borsa=None, mod="testnet"):
        self.borsa = borsa or Sahte(ozs)
        self.olaylar, self.bildirimler = [], []
        self.zaman = [T0 + ARALIK + pd.Timedelta(seconds=60)]
        self.yol = tmp_path / "yurutucu.json"
        self.ayar = Ayar(mod, D(tahsis))
        self.y = self.yeni()

    def yeni(self):
        return Yurutucu("S1", self.borsa, bilgi(), self.ayar, self.yol, olay=lambda t, m: self.olaylar.append((t, m)),
                        bildir=self.bildirimler.append, saat=lambda: self.zaman[0], sembol_esle=lambda s: s)

    def turler(self): return [t for t, _ in self.olaylar]


def ac_niyeti(stop="49000", hedef=None, t=T0, kol="K1", sabit_r=None):
    return Niyet("ac", kol, "BTCUSDT", 1, stop=D(stop), hedef=D(hedef) if hedef else None, sinyal_zamani=t, aralik=ARALIK,
                 risk_oran=D("0.01"), stop_kayma=D("0.0005"), taker=D("0.0005"), sabit_r=sabit_r)


def gor(niyetler=(), pozlar=None, son=T0):
    return MotorGorunumu(list(niyetler), pozlar or {}, {"K1": "BTCUSDT"}, {"K1": son}, {"K1": ARALIK})


def test_giris_hemen_ardindan_borsa_stopu(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti(hedef="52000")]))
    c = [x for x in e.borsa.cagrilar if x[0] in ("piyasa", "kosullu")]
    assert [x[0] for x in c] == ["piyasa", "kosullu", "kosullu"]
    piyasa, stop, hedef = c
    assert piyasa[2:4] == ("BUY", Q) and piyasa[5] is False
    assert stop[2:5] == ("STOP_MARKET", "SELL", Q) and stop[5] == D("49000") and stop[7] == "MARK_PRICE"
    assert hedef[2] == "TAKE_PROFIT_MARKET" and hedef[5] == D("52000")
    assert e.borsa.poz == {"BTCUSDT": Q}
    assert {"canli_emir_doldu", "canli_stop_kuruldu"} <= set(e.turler())
    assert any("canli_stop_kuruldu" in b for b in e.bildirimler) and any("canli_emir_doldu" in b for b in e.bildirimler)
    assert ("hazirla", "BTCUSDT", 3) in e.borsa.cagrilar


def test_sert_limit_gercek_miktar_ve_borsa_ozsermayesiyle(tmp_path):
    e = Ortam(tmp_path, ozs="800", tahsis=5000)                                   # tahsis büyük ama borsa özsermayesi 800: 800 üzerinden
    e.y.adim(gor([ac_niyeti()]))
    q = e.borsa.poz["BTCUSDT"]
    kayip = q * (D(1000) + D(50000) * D("0.0015")) / D(800)
    assert 0 < kayip <= D(str(cl.CANLI_LIMITLER.islem_basi_max_kayip_oran))
    assert q * 50000 / 800 <= D(str(cl.CANLI_LIMITLER.islem_basi_max_nominal_kat))
    assert q * 50000 / 3 / 800 <= D(str(cl.CANLI_LIMITLER.islem_basi_max_marj_oran))
    assert q * 1000 / 800 <= D(str(cl.CANLI_LIMITLER.toplam_stop_riski_oran))


def test_stop_basarisiz_pozisyon_hemen_kapanir(tmp_path):
    e = Ortam(tmp_path)
    e.borsa.stop_hatasi = True
    e.y.adim(gor([ac_niyeti()]))
    assert e.borsa.poz == {}                                                       # çıplak pozisyon yok
    p = [c for c in e.borsa.cagrilar if c[0] == "piyasa"]
    assert len(p) == 2 and p[1][2] == "SELL" and p[1][5] is True                   # reduceOnly kapatma
    assert "canli_stop_basarisiz" in e.turler() and any("canli_stop_basarisiz" in b for b in e.bildirimler)
    assert "S1" not in e.y.durum["pozlar"] and "K1" not in e.y.durum["pozlar"]


def test_stop_ve_kapatma_ikisi_de_basarisiz_alarm_ve_tekrar(tmp_path):
    e = Ortam(tmp_path)
    e.borsa.stop_hatasi = e.borsa.kapat_hatasi = True
    e.y.adim(gor([ac_niyeti()]))
    assert e.borsa.poz and any("KAPATMA DA BAŞARISIZ" in m for _, m in e.olaylar)
    e.borsa.stop_hatasi = e.borsa.kapat_hatasi = False                             # sorun giderildi: mutabakat stopu kurar
    e.y.adim(gor([]))
    assert any(o["tur"] == "STOP_MARKET" for o in e.borsa.acik.values())


def test_min_tutar_alti_atlanir_olay_ve_telegram(tmp_path):
    e = Ortam(tmp_path, ozs="50", tahsis=50)
    e.y.adim(gor([ac_niyeti()]))
    assert e.borsa.poz == {} and "piyasa" not in e.borsa.adlar()
    assert "min_tutar_alti" in e.turler() and any("min_tutar_alti" in b for b in e.bildirimler)
    e.y.adim(gor([ac_niyeti()]))                                                   # aynı sinyal bir daha denenmez
    assert e.turler().count("min_tutar_alti") == 1


def test_eski_sinyal_atlanir(tmp_path):
    e = Ortam(tmp_path)
    e.zaman[0] = T0 + ARALIK + pd.Timedelta(hours=2)
    e.y.adim(gor([ac_niyeti()]))
    assert e.borsa.poz == {} and "canli_giris_atlandi" in e.turler()


def test_idempotent_yeniden_baslatma_cift_emir_yok(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti()]))
    n = len([c for c in e.borsa.cagrilar if c[0] == "piyasa"])
    e.y = e.yeni()                                                                 # servis yeniden başladı (durum dosyasından)
    e.y.adim(gor([ac_niyeti()]))
    assert len([c for c in e.borsa.cagrilar if c[0] == "piyasa"]) == n == 1
    assert client_id("G", "S1", "K1", T0) == client_id("G", "S1", "K1", T0) != client_id("G", "S1", "K1", T0 + ARALIK)
    assert len(client_id("S", "S" * 50, "K" * 50, T0, "9" * 50)) <= 36


def test_cokme_giris_sonrasi_stop_kurulmadan_yeniden_baslatma(tmp_path):
    e = Ortam(tmp_path)
    e.borsa.stop_hatasi = True
    # giriş yapıldı, stop kurulamadan çökme simülasyonu: durum 'gonderildi' kaydı + borsada dolu emir/pozisyon, stop yok
    gid = client_id("G", "S1", "K1", T0)
    e.borsa.piyasa("BTCUSDT", "BUY", D("0.009"), gid)
    e.y.durum["pozlar"]["K1"] = {"sembol": "BTCUSDT", "bsembol": "BTCUSDT", "yon": 1, "qty": "0.009", "stop": "49000", "hedef": None,
                                "giris_bar": str(T0), "aralik_sn": 3600, "durum": "gonderildi", "giris_id": gid, "stop_id": None, "hedef_id": None}
    e.y._kaydet()
    e.borsa.stop_hatasi = False
    e.y = e.yeni()
    e.y.adim(gor([ac_niyeti()]))
    assert len([c for c in e.borsa.cagrilar if c[0] == "piyasa"]) == 1            # ikinci giriş YOK
    stoplar = [o for o in e.borsa.acik.values() if o["tur"] == "STOP_MARKET"]
    assert len(stoplar) == 1 and stoplar[0]["tetik"] == D(49000) and stoplar[0]["miktar"] == D("0.009")


def test_mutabakat_stopsuz_pozisyona_stop_kurar(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti()]))
    e.borsa.acik.clear()                                                           # stop borsadan silindi (elle/hata)
    e.y.adim(gor([], {"K1": PozGorunum("BTCUSDT", 1, D(49000))}))
    assert any(o["tur"] == "STOP_MARKET" and o["tetik"] == D(49000) for o in e.borsa.acik.values())
    assert "canli_uyusmazlik" in e.turler()


def test_mutabakat_bilinmeyen_pozisyon_yalniz_uyari(tmp_path):
    e = Ortam(tmp_path)
    e.borsa.mark["ETHUSDT"] = D(3000)
    e.borsa.poz["ETHUSDT"] = D("0.5")
    e.borsa.poz["BTCUSDT"] = D("-0.01")                                            # motorun beklemediği yön/kayıtsız
    before = len(e.borsa.cagrilar)
    e.y.adim(gor([]))
    assert len(e.borsa.cagrilar) == before                                         # HİÇ emir/iptal yok
    assert sum(1 for t in e.turler() if t == "canli_uyusmazlik") == 2 and any("BİLİNMEYEN" in b for b in e.bildirimler)
    e.y.adim(gor([]))
    assert sum(1 for t in e.turler() if t == "canli_uyusmazlik") == 2              # tekrar tekrar yağmaz


def test_mutabakat_kayip_pozisyon_kayit_temizlenir_emirler_iptal(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti(hedef="52000")]))
    e.borsa.poz.clear()                                                            # stop çalıştı
    e.y.adim(gor([]))
    assert "K1" not in e.y.durum["pozlar"] and e.borsa.acik == {}
    assert any("borsada pozisyon yok" in m for _, m in e.olaylar)
    e.y.adim(gor([ac_niyeti(hedef="52000")]))                                      # aynı sinyalle yeniden girilmez
    assert e.borsa.poz == {}


def test_motor_kapattiysa_borsada_da_kapanir(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti()]))
    e.zaman[0] += ARALIK
    e.y.adim(gor([], {}, son=T0 + ARALIK))                                         # motor dolum satırını işledi, pozisyon yok (stop/limit)
    assert e.borsa.poz == {} and e.borsa.acik == {}
    # henüz dolum satırı işlenmediyse (son=T0) kapatılmaz
    e2 = Ortam(tmp_path / "b")
    e2.y.adim(gor([ac_niyeti()]))
    e2.y.adim(gor([], {}, son=T0))
    assert e2.borsa.poz


def test_kapat_niyeti_piyasa_kapatir_ve_stopu_iptal_eder(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti(hedef="52000")]))
    e.y.adim(gor([Niyet("kapat", "K1", "BTCUSDT", 1, neden="sinyal", aralik=ARALIK)], {"K1": PozGorunum("BTCUSDT", 1, D(49000))}))
    assert e.borsa.poz == {} and e.borsa.acik == {}
    assert [c for c in e.borsa.cagrilar if c[0] == "piyasa"][-1][2:6:3] == ("SELL", True)


def test_stop_yukselir_once_yeni_sonra_eski_iptal_gevsetme_yok(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti()]))
    eski = list(e.borsa.acik)[0]
    e.y.adim(gor([], {"K1": PozGorunum("BTCUSDT", 1, D("49500"))}))
    assert list(e.borsa.acik.values())[0]["tetik"] == D("49500") and eski not in e.borsa.acik and len(e.borsa.acik) == 1
    sira = [c[0] for c in e.borsa.cagrilar][-2:]
    assert sira == ["kosullu", "iptal"]                                            # önce yeni, sonra eski
    e.y.adim(gor([], {"K1": PozGorunum("BTCUSDT", 1, D("49000"))}))                # düşürme/gevşetme yok
    assert list(e.borsa.acik.values())[0]["tetik"] == D("49500")


def test_kill_switch_toplam_dusus_hepsini_kapatir_ve_bloklar(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti()]))
    e.borsa.ozs = D("690")                                                         # zirve 1000 -> -%31 (strateji kill -%30)
    e.y.adim(gor([]))
    assert e.borsa.poz == {} and e.borsa.acik == {} and e.y.durum["kill"] is True
    assert "canli_kill_switch" in e.turler() and any("KILL" in b for b in e.bildirimler)
    n = len([c for c in e.borsa.cagrilar if c[0] == "piyasa"])
    e.zaman[0] += pd.Timedelta(days=3)
    e.y.adim(gor([ac_niyeti(t=T0 + pd.Timedelta(days=3) - ARALIK - pd.Timedelta(seconds=1))]))
    assert len([c for c in e.borsa.cagrilar if c[0] == "piyasa"]) == n             # yeni giriş yok (kalıcı)
    e.y = e.yeni()
    assert e.y.durum["kill"] is True                                                # yeniden başlatma kaldırmaz


def test_gunluk_limit_yeni_giris_yok_kapatmaz_ertesi_gun_acilir(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([]))                                                               # gün başı 1000
    e.borsa.poz["BTCUSDT"] = Q
    e.borsa.ozs = D("935")                                                          # -%6,5 (günlük limit -%6)
    e.y.adim(gor([ac_niyeti(kol="K2")]))
    assert e.borsa.poz == {"BTCUSDT": Q} and e.y.durum["gun_blok"] and not e.y.durum["kill"]   # açık pozisyon KAPATILMAZ
    assert piyasa_sayisi(e.borsa) == 0 and piyasa_sayisi(e.borsa, reduce=True) == 0             # yeni giriş de yok, kapatma da
    assert "canli_giris_atlandi" in e.turler()
    e.zaman[0] += pd.Timedelta(days=1)
    e.borsa.poz.clear()
    t1 = e.zaman[0] - ARALIK - pd.Timedelta(seconds=30)
    e.y.adim(gor([ac_niyeti(t=t1)]))
    assert not e.y.durum["gun_blok"] and e.borsa.poz                                # ertesi UTC günü yeniden girişe izin


def test_hata_yutulmaz_ama_turu_dusurmez_ve_blok(tmp_path):
    class Bozuk(Sahte):
        def bakiye(self): raise BorsaHata("sunucu 503")
    e = Ortam(tmp_path, borsa=Bozuk())
    for _ in range(3):
        e.y.adim(gor([ac_niyeti()]))
    assert e.turler().count("canli_yurutucu_hatasi") == 3 and e.y._ardisik_hata == 3


# ============================================================================================= kuru mod, ayar, köprü
def test_kuru_borsa_emir_gondermeden_ayni_akis(tmp_path):
    kb = KuruBorsa(lambda s: D(50000), D(1000))
    e = Ortam(tmp_path, borsa=kb, mod="kuru")
    e.y.adim(gor([ac_niyeti()]))
    assert [x[0] for x in kb.gonderilen] == ["piyasa", "STOP_MARKET"] and kb.poz["BTCUSDT"]["miktar"] == Q
    e.y.adim(gor([Niyet("kapat", "K1", "BTCUSDT", 1, neden="sinyal", aralik=ARALIK)], {"K1": PozGorunum("BTCUSDT", 1, D(49000))}))
    assert kb.poz == {} and kb.acik == {}


def test_canli_mod_onay_olmadan_baslamaz():
    h = {"mod": "canli", "stratejiler": [{"id": "A", "api_key_env": "K", "api_secret_env": "S", "tahsis_usd": 1000}]}
    with pytest.raises(ca.CanliOnayHatasi):
        ca.coz(h, {})
    with pytest.raises(ca.CanliOnayHatasi):
        ca.coz(h, {"CANLI_ONAY": "hayir"})
    assert ca.coz(h, {"CANLI_ONAY": "evet"}).mod == "canli"
    assert ca.coz({**h, "mod": "testnet"}, {}).mod == "testnet"
    assert ca.coz({"stratejiler": h["stratejiler"]}, {}).mod == "testnet"          # varsayılan testnet


def test_ayar_dogrulama_bir_hesap_bir_strateji_ve_anahtar_adi_hatasi():
    s = {"id": "A", "api_key_env": "K1", "api_secret_env": "S1", "tahsis_usd": 100}
    with pytest.raises(ca.CanliAyarHatasi):
        ca.coz({"stratejiler": [s, {**s, "id": "B"}]}, {})                         # aynı anahtar iki strateji
    with pytest.raises(ca.CanliAyarHatasi):
        ca.coz({"mod": "xx", "stratejiler": [s]}, {})
    a = ca.coz({"stratejiler": [s]}, {})
    with pytest.raises(ca.CanliAyarHatasi) as e:
        ca.anahtarlar(a.stratejiler[0], {})
    assert "K1" in str(e.value)                                                     # yalnız ad, değer yok
    assert ca.anahtarlar(a.stratejiler[0], {"K1": "a", "S1": "b"}) == ("a", "b")


def test_ornek_ayar_ve_deploy_dosyalarinda_gizli_yok():
    from pathlib import Path
    kok = Path(__file__).resolve().parents[1]
    for yol in ("stratejiler/canli_ayar.ornek.json", "deploy/1l3a-canli.env.ornek", "deploy/1l3a-canli.service"):
        m = (kok / yol).read_text(encoding="utf-8")
        for satir in m.splitlines():
            if "=" in satir and not satir.lstrip().startswith("#") and satir.split("=")[0].strip().startswith(("BINANCE", "CANLI_ONAY", "TELEGRAM")):
                assert satir.split("=", 1)[1].strip() == "", satir
    assert ca.yukle(kok / "stratejiler/canli_ayar.ornek.json", {}).mod == "testnet"


def test_gizli_ve_imza_hicbir_logda_gorunmez(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    sizinti = ConnectionError(f"https://testnet.binancefuture.com/fapi/v1/order?x=1&signature={'b' * 64} {UYDURMA_GIZLI}")
    c, o = istemci([ZAMAN, Yanit(503, {}), sizinti, Yanit(400, {"code": -2019, "msg": "Margin is insufficient."}),
                    Yanit(400, {"code": -1021, "msg": "x"}), ZAMAN, Yanit(500, {})], max_deneme=2)
    for _ in range(3):
        try:
            c.piyasa("BTCUSDT", "BUY", D("0.01"), "1l3a-G-x")
        except BorsaHata as e:
            hata = str(e)
            assert UYDURMA_GIZLI not in hata and "b" * 64 not in hata
    class Bozuk(Sahte):
        def bakiye(self): return c.bakiye()
    e = Ortam(tmp_path, borsa=Bozuk())
    e.y.adim(gor([ac_niyeti()]))
    metin = "\n".join(r.getMessage() for r in caplog.records) + "\n".join(m for _, m in e.olaylar) + "\n".join(e.bildirimler)
    for yasak in (UYDURMA_GIZLI, UYDURMA_ANAHTAR, "b" * 64):
        assert yasak not in metin
    import re
    assert not re.search(r"signature=[0-9a-f]{16,}", metin)
    assert UYDURMA_GIZLI not in repr(c) and UYDURMA_GIZLI not in repr(vars(c).get("oturum", ""))


def test_kopru_niyet_uretir_ve_desteklenmeyeni_reddeder():
    from types import SimpleNamespace as NS
    import numpy as np
    from motor.canli.borsa import motor_kopru as mk
    from motor.strateji import cikislar as cks
    kol = NS(kimlik="K1", sembol="BTCUSDT", mod="sinyal", cikis_ayarlari=cks.CikisAyarlari(), giris_emri=(1, 49000.0, np.nan, 5),
             cikis_emri=None, grup_payi=D(1))
    birim = NS(kollar=[kol], son_t=T0, aralik=ARALIK)
    motor = NS(kill=False, gunluk_blok=False, acik={}, risk_oran=D("0.005"), _sk=lambda s: D("0.0005"), _tk=lambda s: D("0.0004"))
    g = mk.gorunum(motor, [birim])
    n = g.niyetler[0]
    assert (n.tur, n.yon, n.stop, n.hedef, n.sinyal_zamani, n.risk_oran, n.taker) == ("ac", 1, D("49000.0"), None, T0, D("0.005"), D("0.0004"))
    motor.kill = True
    assert mk.gorunum(motor, [birim]).niyetler == []                                # paper kill: giriş yok
    motor.kill = False
    kol.cikis_emri = "sinyal"
    motor.acik = {"K1": NS(sembol="BTCUSDT", yon=1, stop=D(49000), hedef=None)}
    g = mk.gorunum(motor, [birim])
    assert [x.tur for x in g.niyetler] == ["kapat"] and g.pozlar["K1"].stop == D(49000)
    mk.uygunluk_kontrol(motor, [birim])
    kol.mod = "agirlik"
    with pytest.raises(mk.CanliDesteklemiyorHatasi):
        mk.uygunluk_kontrol(motor, [birim])


def test_paper_servisi_davranisi_degismedi_kanca_varsayilan_none():
    from motor.canli import paper
    p = inspect.signature(paper.canli_calistir).parameters
    assert p["tur_kancasi"].default is None and p["strateji_filtre"].default is None


def test_gercek_paper_motoruyla_kanca_filtre_ve_kopru(tmp_path, monkeypatch):
    """Gerçek PaperKasalar + sahte Binance (paper testlerinin düzeneği): kanca her turda çağrılır, filtre yalnız seçili stratejiyi kurar,
    köprü gerçek PaperMotor nesnelerini okur ve yürütücü sahte borsada çalışır."""
    from testler.test_paper_canli import SahteFapi
    from testler.test_paper_v2 import OrtalamaTrend, set_, tanim
    from motor.canli import paper as pp, paper_veri as pv, paper_v2 as v2
    from motor.canli.borsa import motor_kopru as mk
    monkeypatch.setattr(pv, "FapiIstemci", SahteFapi)
    monkeypatch.setitem(pp.PENCERE, "1d", 120)
    a = tanim("a", ["BTCUSDT"], OrtalamaTrend(n=10))
    b = tanim("b", ["SOLUSDT"], OrtalamaTrend(n=15))
    ayar = set_("a", "b")
    monkeypatch.setattr(v2, "set_yukle", lambda *x, **k: ayar)
    monkeypatch.setattr(v2, "tanimlari_yukle", lambda *x, **k: [a, b])
    goruldu = []

    def kanca(p, simdi):
        assert set(p.hesaplar) == {"a"}                                               # filtre: yalnız canlıya alınan strateji
        h = p.hesaplar["a"]
        mk.uygunluk_kontrol(h.motor, h.birimler)
        g = mk.gorunum(h.motor, h.birimler)
        goruldu.append(g)
        assert g.kollar and all(n.tur in ("ac", "kapat") for n in g.niyetler)
        for n in g.niyetler:
            if n.tur == "ac":
                assert n.stop is not None and n.sinyal_zamani is not None and 0 < n.risk_oran <= D("0.01")
    assert pp.canli_calistir(tmp_path, None, False, tek_sefer=True, tur_kancasi=kanca, strateji_filtre=["a"]) == 0
    assert len(goruldu) == 1
    with pytest.raises(ValueError, match="sette olmayan"):
        pp.canli_calistir(tmp_path / "x", None, False, tek_sefer=True, strateji_filtre=["yok"])


# ============================================================================================= bağımsız inceleme düzeltmeleri (regresyon)
def piyasa_sayisi(b, reduce=False):
    return len([c for c in b.cagrilar if c[0] == "piyasa" and c[5] is reduce])


def test_r1_emir_post_agda_tekrar_edilmez_okuma_edilir():
    ag = ConnectionError("x")
    c, o = istemci([ZAMAN, ag, Yanit(200, {})])
    with pytest.raises(BorsaHata) as e:
        c.piyasa("BTCUSDT", "BUY", D("0.01"), "1l3a-G-x")
    assert e.value.belirsiz and len(o.istekler) == 2 and c.uykular == []           # tek POST
    c, o = istemci([ZAMAN, Yanit(503, {}), Yanit(200, {})])
    with pytest.raises(BorsaHata) as e:
        c.piyasa("BTCUSDT", "BUY", D("0.01"), "1l3a-G-x")
    assert e.value.belirsiz and len(o.istekler) == 2
    c, o = istemci([ZAMAN, Yanit(502, {}), Yanit(200, {})])                           # algo (koşullu) emir de aynı
    with pytest.raises(BorsaHata) as e:
        c.kosullu("BTCUSDT", "STOP_MARKET", "SELL", D("0.01"), D(49000), "1l3a-S-x")
    assert e.value.belirsiz and len(o.istekler) == 2
    c, o = istemci([ZAMAN, ag, Yanit(200, [])])                                        # okuma (GET) hâlâ tekrar edilir
    assert c.pozisyonlar() == [] and len(o.istekler) == 3


def test_r1_belirsiz_giris_emir_dolduysa_tekrar_gonderilmez(tmp_path):
    e = Ortam(tmp_path)
    e.borsa.piyasa_mod = "belirsiz_dolar"                                              # POST ağ hatasıyla bitti ama borsada doldu
    e.y.adim(gor([ac_niyeti()]))
    assert piyasa_sayisi(e.borsa) == 1 and e.borsa.poz == {"BTCUSDT": Q}
    assert any(o["tur"] == "STOP_MARKET" for o in e.borsa.acik.values())


def test_r1_belirsiz_giris_emir_yoksa_bir_kez_yeniden_gonderilir(tmp_path):
    e = Ortam(tmp_path)
    e.borsa.piyasa_mod = "belirsiz_dolmaz"
    e.y.adim(gor([ac_niyeti()]))
    assert piyasa_sayisi(e.borsa) == 2 and e.borsa.poz == {"BTCUSDT": Q}      # ikincisi: borsa 'emir yok' dedi
    assert piyasa_sayisi(e.borsa) == 2


def test_r2_iptal_edilmis_eski_stop_kuruldu_sayilmaz(tmp_path):
    e = Ortam(tmp_path)
    e.borsa.stop_belirsiz_durum = "CANCELED"                                            # POST belirsiz; sorgu: aynı kimlikli kayıt İPTAL edilmiş
    e.y.adim(gor([ac_niyeti()]))
    assert e.borsa.poz == {} and "canli_stop_basarisiz" in e.turler() and "canli_stop_kuruldu" not in e.turler()
    e2 = Ortam(tmp_path / "b")
    e2.borsa.stop_belirsiz_durum = "NEW"                                                # aktifse başarı
    e2.y.adim(gor([ac_niyeti()]))
    assert e2.borsa.poz and "canli_stop_kuruldu" in e2.turler()


def test_r2_yeniden_kurulumda_kimlik_deneme_sayaciyla_degisir(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti()]))
    ilk = e.y.durum["pozlar"]["K1"]["stop_id"]
    e.borsa.acik.clear()                                                                 # stop iptal edildi/düştü
    e.y.adim(gor([], {"K1": PozGorunum("BTCUSDT", 1, D(49000))}))
    ikinci = e.y.durum["pozlar"]["K1"]["stop_id"]
    assert ilk != ikinci and e.y.durum["pozlar"]["K1"]["stop_deneme"] == 2 and ikinci in e.borsa.acik


def test_r3_kill_once_kapat_sonra_iptal_kapatma_basarisizsa_stop_kalir(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti()]))
    e.borsa.kapat_hatasi = True
    e.borsa.ozs = D("690")
    e.y.adim(gor([], {"K1": PozGorunum("BTCUSDT", 1, D(49000))}))
    assert e.borsa.poz and any(o["tur"] == "STOP_MARKET" for o in e.borsa.acik.values())   # stop yerinde
    assert "hepsini_iptal" not in e.borsa.adlar() and "canli_kill_hatasi" in e.turler()
    n = e.turler().count("canli_kill_hatasi")
    e.y.adim(gor([], {"K1": PozGorunum("BTCUSDT", 1, D(49000))}))
    assert e.turler().count("canli_kill_hatasi") == n                                     # uyarı tekrar tekrar yağmaz
    e.borsa.kapat_hatasi = False                                                           # kapatma yeniden denenir
    e.y.adim(gor([], {"K1": PozGorunum("BTCUSDT", 1, D(49000))}))
    assert e.borsa.poz == {} and e.borsa.acik == {}
    ad = e.borsa.adlar()
    assert ad.index("hepsini_iptal") > max(i for i, c in enumerate(e.borsa.cagrilar) if c[0] == "piyasa" and c[5])   # iptal, kapatmadan SONRA


def test_r3_kill_kapatma_basarisizken_stopsuz_pozisyona_stop_kurulur(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti()]))
    e.borsa.acik.clear()
    e.borsa.kapat_hatasi = True
    e.borsa.ozs = D("690")
    e.y.adim(gor([], {"K1": PozGorunum("BTCUSDT", 1, D(49000))}))
    assert any(o["tur"] == "STOP_MARKET" for o in e.borsa.acik.values())                   # kill sırasında da mutabakat stopu korur


def test_r4_r5_belirsiz_giris_sonra_pozisyon_gorunce_hemen_stop_ve_acik(tmp_path):
    e = Ortam(tmp_path)
    e.borsa.piyasa_mod = "belirsiz_dolmaz"
    e.borsa.sorgu_bozuk = True                                                              # ne gönderim ne sorgu doğrulanabiliyor
    e.y.adim(gor([ac_niyeti()]))
    assert e.y.durum["pozlar"]["K1"]["durum"] == "gonderildi" and "canli_giris_belirsiz" in e.turler() and piyasa_sayisi(e.borsa) <= 1
    e.borsa.sorgu_bozuk = False
    e.borsa.poz["BTCUSDT"] = D("0.009")                                                    # emir sonradan doldu
    e.y.adim(gor([]))                                                                       # paper henüz pozisyonu bilmiyor
    r = e.y.durum["pozlar"]["K1"]
    assert r["durum"] == "acik" and r["qty"] == "0.009" and r["giris"] == "50000"
    assert any(o["tur"] == "STOP_MARKET" and o["tetik"] == D(49000) for o in e.borsa.acik.values())
    assert not any("BİLİNMEYEN" in m for _, m in e.olaylar)
    e.y.adim(gor([], {"K1": PozGorunum("BTCUSDT", 1, D("49500"))}))                          # 'acik' olduğu için iz süren stop artık çalışır
    assert list(o["tetik"] for o in e.borsa.acik.values() if o["tur"] == "STOP_MARKET") == [D("49500")]


def test_r4_dolmadi_iptal_basarisiz_kayit_korunur(tmp_path):
    class DolmayanSahte(Sahte):
        def piyasa(self, s, yon, q, cid, reduce_only=False):
            self.cagrilar.append(("piyasa", s, yon, q, cid, reduce_only))
            return {"id": "1", "client_id": cid, "sembol": s, "tur": "MARKET", "yon": yon, "miktar": q, "tetik": D(0), "reduce_only": False,
                    "durum": "NEW", "kosullu": False, "dolan": D(0), "ort_fiyat": D(0)}
    b = DolmayanSahte()
    b.iptal_hatasi = True
    e = Ortam(tmp_path, borsa=b)
    e.y.adim(gor([ac_niyeti()]))
    assert e.y.durum["pozlar"]["K1"]["durum"] == "gonderildi"                               # iptal edilemedi: emir sonradan dolabilir, kayıt şart


def test_r6_dolum_kaymasi_riski_asarsa_reduceonly_kucultulur(tmp_path):
    e = Ortam(tmp_path)
    e.borsa.fill_px = D(50800)                                                              # mark 50000, gerçek dolum %1,6 kötü: stop mesafesi 1800 > 1000
    e.y.adim(gor([ac_niyeti()]))
    q = e.borsa.poz["BTCUSDT"]
    assert q < Q and "canli_risk_asimi" in e.turler()
    assert piyasa_sayisi(e.borsa, reduce=True) == 1
    kayip = q * (D(1800) + D(50800) * D("0.0015")) / D(1000)
    assert kayip <= D(str(cl.CANLI_LIMITLER.islem_basi_max_kayip_oran))                               # GERÇEK dolumla uyumlu
    assert [o["miktar"] for o in e.borsa.acik.values() if o["tur"] == "STOP_MARKET"] == [q]  # stop kalan miktar için


def test_r6_kill_ve_gunluk_tahsis_tabanli(tmp_path):
    e = Ortam(tmp_path, ozs="5000", tahsis=1000)                                            # hesap tahsisten büyük
    e.y.adim(gor([]))
    e.borsa.ozs = D("4000")                                                                  # hesap -%20 ama tahsis tabanı hâlâ 1000: kill YOK
    e.y.adim(gor([]))
    assert not e.y.durum["kill"] and not e.y.durum["gun_blok"]
    e.borsa.ozs = D("690")                                                                   # tahsisin altına indi: min(690,1000) -> -%31
    e.y.adim(gor([]))
    assert e.y.durum["kill"]


def test_r7_paper_stopu_fiyatin_otesinde_piyasada_kapatir(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti()]))
    e.y.adim(gor([], {"K1": PozGorunum("BTCUSDT", 1, D("50500"))}))                          # mark 50000 < yeni stop 50500
    assert e.borsa.poz == {} and e.borsa.acik == {} and "K1" not in e.y.durum["pozlar"]


def test_r7_paper_yonu_farkliysa_kapatir_ve_uyari_tekrarlanmaz(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti()]))
    e.y.adim(gor([], {"K1": PozGorunum("BTCUSDT", -1, D(51000))}))
    assert e.borsa.poz == {}
    e2 = Ortam(tmp_path / "b")
    e2.y.adim(gor([ac_niyeti()]))
    e2.borsa.stop_hatasi = True                                                               # yeni stop sürekli reddedilir
    for _ in range(4):
        e2.y.adim(gor([], {"K1": PozGorunum("BTCUSDT", 1, D("49500"))}))
    assert e2.turler().count("canli_stop_hatasi") == 1                                        # aynı koşul bir kez
    assert [o["tetik"] for o in e2.borsa.acik.values()] == [D(49000)]                          # eski stop yerinde


def test_r8_stop_miktar_uyusmazligi_yeni_stopu_iptal_etmez_tolerans_step(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti()]))
    eski = list(e.borsa.acik.values())[0]
    eski["miktar"] = D("0.0275")                                                              # fark 0.0005 < step 0.001: eşleşme sayılır
    e.y.adim(gor([], {"K1": PozGorunum("BTCUSDT", 1, D(49000))}))
    assert list(e.borsa.acik) == [eski["client_id"]] and "canli_uyusmazlik" not in [t for t in e.turler() if t == "canli_uyusmazlik"]
    eski["miktar"] = D("0.004")                                                               # gerçek uyuşmazlık
    e.y.adim(gor([], {"K1": PozGorunum("BTCUSDT", 1, D(49000))}))
    stoplar = list(e.borsa.acik.values())
    assert len(stoplar) == 1 and stoplar[0]["miktar"] == Q and stoplar[0]["client_id"] == e.y.durum["pozlar"]["K1"]["stop_id"]


def test_r9_iptal_basarisizsa_kayit_silinmez_yetim_emirler_temizlenir(tmp_path):
    e = Ortam(tmp_path)
    e.y.adim(gor([ac_niyeti(hedef="52000")]))
    e.borsa.iptal_hatasi = True
    e.y.adim(gor([Niyet("kapat", "K1", "BTCUSDT", 1, neden="sinyal", aralik=ARALIK)], {"K1": PozGorunum("BTCUSDT", 1, D(49000))}))
    assert e.borsa.poz == {} and "K1" in e.y.durum["pozlar"] and len(e.borsa.acik) == 2        # kayıt tutuldu, emirler hâlâ orada
    e.borsa.iptal_hatasi = False
    e.y.adim(gor([]))
    assert "K1" not in e.y.durum["pozlar"] and e.borsa.acik == {}
    # kayıtsız yetim reduceOnly emir (örn. durum dosyası kaybı) pozisyon yokken iptal edilir
    e2 = Ortam(tmp_path / "b")
    e2.borsa.kosullu("BTCUSDT", "STOP_MARKET", "SELL", D("0.009"), D(49000), "1l3a-S-yetim")
    e2.y.adim(gor([]))
    assert e2.borsa.acik == {}


def test_r10_eski_sinyal_mumsuz_satirda_taze_gorunmez():
    from types import SimpleNamespace as NS
    import numpy as np
    from motor.canli.borsa import motor_kopru as mk
    from motor.strateji import cikislar as cks
    kol = NS(kimlik="K1", sembol="BTCUSDT", mod="sinyal", cikis_ayarlari=cks.CikisAyarlari(), giris_emri=(1, 49000.0, np.nan, 5), cikis_emri=None, grup_payi=D(1))
    son = T0 + 3 * ARALIK                                                                      # motor son satırı işledi ama sembolün mumu T0'da kalmış
    birim = NS(kollar=[kol], son_t=son, aralik=ARALIK, tf="1h")
    motor = NS(kill=False, gunluk_blok=False, acik={}, risk_oran=D("0.01"), _sk=lambda s: D("0.0005"), _tk=lambda s: D("0.0005"))
    n = mk.gorunum(motor, [birim], son_mum=lambda s, tf, t: T0).niyetler[0]
    assert n.sinyal_zamani == T0 and client_id("G", "S", "K1", n.sinyal_zamani) == client_id("G", "S", "K1", T0)
    ayni = mk.gorunum(motor, [NS(**{**vars(birim), "son_t": son + ARALIK})], son_mum=lambda s, tf, t: T0).niyetler[0]
    assert client_id("G", "S", "K1", ayni.sinyal_zamani) == client_id("G", "S", "K1", n.sinyal_zamani)   # her satırda yeni kimlik DEĞİL
    from motor.canli.borsa.canli_yurutucu import Ayar as _A
    assert n.sinyal_zamani + n.aralik + pd.Timedelta(seconds=_A().giris_gecikme_max_sn) < son                # bayat: yürütücü atlar


def test_r10_bayat_sinyal_yurutucuda_giris_yapmaz(tmp_path):
    e = Ortam(tmp_path)
    e.zaman[0] = T0 + 3 * ARALIK
    e.y.adim(gor([ac_niyeti(t=T0)]))
    assert e.borsa.poz == {} and "canli_giris_atlandi" in e.turler()


def test_r11_sabit_r_hedefi_gercek_dolumdan_tp_olarak_kurulur(tmp_path):
    from motor.strateji import cikislar as cks
    e = Ortam(tmp_path)
    e.borsa.fill_px = D(50010)
    e.y.adim(gor([ac_niyeti(sabit_r=2.0)]))
    beklenen = D(repr(cks.r_hedef_fiyati(1, 50010.0, float(D(50010) - D(49000)), 2.0)))
    tp = [o for o in e.borsa.acik.values() if o["tur"] == "TAKE_PROFIT_MARKET"]
    assert len(tp) == 1 and abs(tp[0]["tetik"] - beklenen) <= D("0.1") and tp[0]["tetik"] > D(50010)


def test_r12_sifir_ozsermaye_sifira_bolme_yok(tmp_path):
    e = Ortam(tmp_path, ozs="0")
    e.y.adim(gor([ac_niyeti()]))
    assert "canli_yurutucu_hatasi" not in e.turler() and e.borsa.poz == {}


def test_r12_benimsenen_kayit_bar_araligini_tasir_motor_kapali_calisir(tmp_path):
    e = Ortam(tmp_path)
    e.borsa.poz["BTCUSDT"] = D("0.009")                                                       # durum dosyası kayıp; motor pozisyonu biliyor
    e.y.adim(gor([], {"K1": PozGorunum("BTCUSDT", 1, D(49000))}))
    assert e.y.durum["pozlar"]["K1"]["aralik_sn"] == 3600
    e.y.adim(gor([], {}, son=T0 + ARALIK))                                                    # motor pozisyonu kapattı
    assert e.borsa.poz == {}


def test_r12_calistir_uygunluk_kontrolu_cagirir_ve_paper_telegrami_susar():
    from motor.canli.borsa import calistir
    src = inspect.getsource(calistir.main)
    assert "uygunluk_kontrol(" in src and "telegram_sessiz=True" in src


def test_a_telegram_sessiz_paper_bildirimleri_gitmez(tmp_path, monkeypatch):
    from testler.test_paper_canli import SahteFapi
    from testler.test_paper_v2 import OrtalamaTrend, set_, tanim
    from motor.canli import paper as pp, paper_veri as pv, paper_v2 as v2, telegram as tg
    monkeypatch.setattr(pv, "FapiIstemci", SahteFapi)
    monkeypatch.setitem(pp.PENCERE, "1d", 120)
    a = tanim("a", ["BTCUSDT"], OrtalamaTrend(n=10))
    monkeypatch.setattr(v2, "set_yukle", lambda *x, **k: set_("a"))
    monkeypatch.setattr(v2, "tanimlari_yukle", lambda *x, **k: [a])
    gonderilen = []
    monkeypatch.setattr(tg, "gonder", lambda m, *x, **k: gonderilen.append(m) or True)
    assert pp.canli_calistir(tmp_path / "s", None, False, tek_sefer=True, telegram_sessiz=True) == 0
    assert gonderilen == []
    assert pp.canli_calistir(tmp_path / "n", None, False, tek_sefer=True) == 0                 # varsayılan: paper bildirimleri eskisi gibi gider
    assert gonderilen
