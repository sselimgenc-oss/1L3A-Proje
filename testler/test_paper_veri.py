"""Binance istemcisi / exchangeInfo / WS / Telegram: ağ YOK (hepsi mock). Gerçek ağ testi: PAPER_AG_TESTI=1 ile isteğe bağlı."""
import asyncio
import os

import pandas as pd
import pytest

from motor.canli import paper_canli as pc
from motor.canli import paper_veri as pv
from motor.canli import telegram as tg


class Yanit:
    def __init__(self, kod=200, js=None, baslik=None, metin=""):
        self.status_code, self._js, self.headers, self.text = kod, js, baslik or {}, metin

    def json(self):
        return self._js


class Oturum:
    def __init__(self, yanitlar):
        self.yanitlar, self.cagrilar = list(yanitlar), []

    def get(self, url, params=None, timeout=None):
        self.cagrilar.append((url, params))
        y = self.yanitlar.pop(0)
        if isinstance(y, Exception):
            raise y
        return y

    def post(self, url, data=None, timeout=None):
        self.cagrilar.append((url, data))
        return self.yanitlar.pop(0)


def ist(yanitlar, uykular=None):
    uykular = uykular if uykular is not None else []
    return pv.FapiIstemci(oturum=Oturum(yanitlar), uyku=uykular.append, saat=lambda: 1000.0, max_deneme=3), uykular


def test_429_retry_after_beklenir_ve_tekrar_denenir():
    c, uyku = ist([Yanit(429, baslik={"Retry-After": "7"}), Yanit(200, {"serverTime": 1_700_000_000_000})])
    assert c.sunucu_zamani() == pd.Timestamp(1_700_000_000_000, unit="ms", tz="UTC")
    assert uyku == [7]


def test_418_ve_451_otomatik_tekrar_yok():
    c, _ = ist([Yanit(418, baslik={"Retry-After": "300"})])
    with pytest.raises(pv.BinanceHata, match="418"):
        c.get("/x")
    c, _ = ist([Yanit(451, metin="restricted location")])
    with pytest.raises(pv.BinanceHata, match="451"):
        c.get("/x")


def test_ag_hatasi_ustel_geri_cekilme_sonunda_yukselir():
    c, uyku = ist([ConnectionError("x")] * 3)
    with pytest.raises(pv.BinanceHata, match="3 denemede"):
        c.get("/x")
    assert uyku == [2, 4, 8]


def test_agirlik_esigi_asilinca_dakika_sonuna_kadar_bekler():
    c, uyku = ist([Yanit(200, {}, {"X-MBX-USED-WEIGHT-1M": "1900"}), Yanit(200, {})])
    c.get("/a")
    c.get("/b")
    assert uyku and 1 <= uyku[0] <= 60


def _kl(t_ms, kapanis_ms, o=1.0):
    return [t_ms, str(o), str(o + 1), str(o - 1), str(o + 0.5), "10", kapanis_ms, "100", 5, "0", "0", "0"]


def test_klines_kapanmamis_mumu_atar_ve_sayfalar():
    simdi = pd.Timestamp("2026-01-01 01:00", tz="UTC")
    t0 = int(pd.Timestamp("2026-01-01 00:00", tz="UTC").value // 10**6)
    t1 = t0 + 1_800_000
    t2 = t0 + 3_600_000           # 01:00'da açılan mum: kapanmamış
    c, _ = ist([Yanit(200, [_kl(t0, t0 + 1_799_999), _kl(t1, t1 + 1_799_999), _kl(t2, t2 + 1_799_999)])])
    df = c.klines("ETHUSDT", "30m", None, None, simdi)
    assert len(df) == 2 and df.index[-1] == pd.Timestamp("2026-01-01 00:30", tz="UTC")
    assert list(df.columns)[:4] == ["acilis", "yuksek", "dusuk", "kapanis"]


BILGI = {"symbols": [
    {"symbol": "ETHUSDT", "contractType": "PERPETUAL", "status": "TRADING", "filters": [
        {"filterType": "PRICE_FILTER", "tickSize": "0.01"}, {"filterType": "LOT_SIZE", "stepSize": "0.001", "minQty": "0.001"},
        {"filterType": "MARKET_LOT_SIZE", "stepSize": "0.01", "minQty": "0.01"}, {"filterType": "MIN_NOTIONAL", "notional": "20"}]},
    {"symbol": "NVDAUSDT", "contractType": "PERPETUAL", "status": "TRADING", "filters": [
        {"filterType": "PRICE_FILTER", "tickSize": "0.01"}, {"filterType": "LOT_SIZE", "stepSize": "0.01", "minQty": "0.01"},
        {"filterType": "MIN_NOTIONAL", "notional": "5"}]},
    {"symbol": "COPPERUSDT", "contractType": "PERPETUAL", "status": "BREAK", "filters": []},
    {"symbol": "XAUUSDT", "contractType": "TRADIFI_PERPETUAL", "status": "TRADING", "filters": []},
    {"symbol": "CLUSDT", "contractType": "CURRENT_QUARTER", "status": "TRADING", "filters": []},
]}


def test_exchange_info_filtreleri():
    k = pv.kurallar_cikar(BILGI)
    assert k["ETHUSDT"].tick_size == 0.01 and k["ETHUSDT"].step_size == 0.01 and k["ETHUSDT"].min_notional == 20.0   # MARKET_LOT_SIZE öncelikli
    assert k["NVDAUSDT"].step_size == 0.01 and "COPPERUSDT" not in k


def test_tradfi_esleme_bulunamazsa_veri_yok_uydurma_yok():
    e = pv.esleme_dogrula(BILGI, ["ETHUSDT", "DK_NVDA", "DK_COPPER", "DK_AAPL"])
    assert e["ETHUSDT"] == ("ETHUSDT", None) and e["DK_NVDA"] == ("NVDAUSDT", None)
    assert e["DK_COPPER"][0] is None and "TRADING" in e["DK_COPPER"][1]
    assert e["DK_AAPL"][0] is None and "yok" in e["DK_AAPL"][1]


def test_tradfi_perpetual_turu_kabul_vadeli_red():
    e = pv.esleme_dogrula(BILGI, ["DK_XAU", "DK_WTI"])
    assert e["DK_XAU"] == ("XAUUSDT", None)
    assert e["DK_WTI"][0] is None and "sürekli sözleşme değil" in e["DK_WTI"][1]


def test_veri_yok_isaretleme():
    from motor.canli import paper
    from motor.canli import paper_sinyal as psg
    tans = psg.tanimlari_yukle(ayar_kaynagi="kilit")
    e = pv.esleme_dogrula(BILGI, sorted({s for t in tans for s in t.veri_semboller}))
    paper._tanimlara_veri_yok_isle(tans, e)
    yok = {t.kimlik for t in tans if t.veri_yok}
    assert "dis__fraktal-alligator-sky|DK_NVDA|4h" not in yok          # NVDAUSDT var
    assert "pf__kanarya|hisse_emtia|1d" in yok and "pf__rotasyon|hepsi|1d" in yok     # çoğu sembol listede yok


def test_tradfi_mumlari_seans_suzgecinden_gecer():
    # 5m mumlar: Cuma 14:30-21:00 UTC seans içi + hafta sonu (Binance 7/24) -> hafta sonu atılmalı
    idx = pd.date_range("2026-11-06 14:30", "2026-11-08 12:00", freq="5min", tz="UTC")
    satir = [_kl(int(t.value // 10**6), int(t.value // 10**6) + 299_999) for t in idx]

    class S:
        def klines(self, sembol, aralik, bas, bit, simdi):
            return pv.klines_df(satir, pd.Timestamp("2026-11-09", tz="UTC"))
    df = pv.mumlar(S(), "DK_NVDA", "1h", None, pd.Timestamp("2026-11-09", tz="UTC"))
    assert len(df) and df.index.max() < pd.Timestamp("2026-11-06 22:00", tz="UTC")
    assert df.index.dayofweek.max() == 4


def test_ws_24_saat_proaktif_yeniden_baglanma_ve_kopma():
    olaylar, mesajlar = [], []

    class WS:
        def __init__(self, n):
            self.n = n

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def recv(self):
            self.n -= 1
            if self.n < 0:
                await asyncio.sleep(10)
            return '{"stream":"x","data":{"k":{"x":true}}}'

    baglanti = []

    def baglan(url, **kw):
        baglanti.append(url)
        if len(baglanti) == 1:
            raise ConnectionError("kopma")          # ilk bağlantı hatası
        return WS(2)

    async def kos():
        durdur = asyncio.Event()

        async def hizli(_):
            return None
        g = asyncio.create_task(pc.ws_dongu("wss://x/stream?streams=a@kline_1m", mesajlar.append,
                                            lambda t, m: olaylar.append(t), durdur, baglan=baglan, yeniden_sn=0.3,
                                            uyku=hizli))
        await asyncio.sleep(1.0)
        durdur.set()
        await asyncio.wait_for(g, 5)
    asyncio.run(kos())
    assert "ws_koptu" in olaylar and "ws_baglandi" in olaylar or "ws_yeniden_baglandi" in olaylar
    assert "ws_24sa_yenileme" in olaylar and len(baglanti) >= 3 and len(mesajlar) >= 2


def test_telegram_yapilandirma_yoksa_gondermez_ve_loglar(caplog):
    tg._yok_loglandi[0] = False
    with caplog.at_level("WARNING", logger="paper.telegram"):
        assert tg.gonder("merhaba", env={}) is False
    assert any("devre dışı" in r.message for r in caplog.records)


def test_telegram_gonderim_ve_hata():
    s = Oturum([Yanit(200), Yanit(500, metin="boom")])
    env = {"TELEGRAM_BOT_TOKEN": "T", "TELEGRAM_CHAT_ID": "C"}
    assert tg.gonder("x" * 5000, env=env, oturum=s, uyku=lambda x: None, saat=lambda: 1e9) is True
    url, data = s.cagrilar[0]
    assert "botT/sendMessage" in url and len(data["text"]) == 4096 and data["chat_id"] == "C"
    assert tg.gonder("y", env=env, oturum=s, uyku=lambda x: None, saat=lambda: 2e9) is False


def test_token_repoda_yok():
    from pathlib import Path
    for p in Path(pv.__file__).parent.glob("*.py"):
        assert "api.telegram.org/bot" not in p.read_text(encoding="utf-8") or p.name == "telegram.py"


@pytest.mark.skipif(os.environ.get("PAPER_AG_TESTI") != "1", reason="gerçek ağ testi isteğe bağlı: PAPER_AG_TESTI=1")
def test_gercek_ag_fapi_klines():
    c = pv.FapiIstemci()
    df = c.klines("ETHUSDT", "30m", pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=6), None, pd.Timestamp.now(tz="UTC"))
    assert len(df) >= 5
