"""Canlı yol (CanliKaynak + Paper) sahte Binance istemcisiyle: başlangıç, REST ile devam, yeniden başlatma + kaçan mumları tamamlama."""
import pandas as pd

from motor.canli import paper as pp
from motor.canli import paper_canli as pc
from motor.canli import paper_veri as pv
from testler.test_paper_motor import TAN, kural, sentetik


class SahteIstemci:
    """Sentetik serileri 'borsa' gibi sunar: yalnız kapanmış mumlar, simdi'ye göre."""

    def __init__(self, seri, funding=None):
        self.seri, self.fund, self.cagri = seri, funding or {}, 0

    def klines(self, sembol, aralik, bas=None, bit=None, simdi=None):
        self.cagri += 1
        df = self.seri[(sembol, aralik)]
        from motor.veri.depo import aralik_suresi
        df = df[df.index + aralik_suresi(aralik) <= simdi]
        return df[df.index >= pd.Timestamp(bas)] if bas is not None else df

    def funding(self, sembol, bas=None):
        return self.fund.get(sembol, pd.DataFrame({"oran": []}, index=pd.DatetimeIndex([], tz="UTC")))


def _kur(tmp_path, m):
    t = TAN["swing__cci-esik|SOLUSDT|1d"]
    ist = SahteIstemci({("SOLUSDT", "1d"): m})
    return t, ist


def test_canli_baslat_devam_ve_yeniden_baslatma_kacan_mumlari_tamamlar(tmp_path):
    m = sentetik(520, "1d", 11, vol=0.03)
    t, ist = _kur(tmp_path, m)
    kur = {"SOLUSDT": kural("SOLUSDT")}
    t0 = m.index[400] + pd.Timedelta(days=1, seconds=10)
    k1 = pc.CanliKaynak(ist, [t], {"1d": 300}, None)
    k1.baslat(t0)
    p1 = pp.Paper([t], k1, kur, durum_yolu=tmp_path / "s.json", her_satir_kaydet=True)
    p1.baslat(t0)
    # 20 gün normal akış (her gün bir tur)
    simdi = t0
    for _ in range(20):
        simdi += pd.Timedelta(days=1)
        k1.guncelle(simdi)
        p1.adim(simdi)
    # servis 30 gün KAPALI kalır; yeniden başlar -> kaçan mumlar REST'ten tamamlanır
    simdi2 = simdi + pd.Timedelta(days=30)
    k2 = pc.CanliKaynak(ist, [t], {"1d": 300}, None)
    k2.baslat(simdi2)
    p2 = pp.Paper([t], k2, kur, durum_yolu=tmp_path / "s.json")
    assert p2.yukle()
    n = p2.adim(simdi2)
    assert n == 30                                    # 30 kaçan mum sırayla işlendi
    # kesintisiz referans
    k3 = pc.CanliKaynak(ist, [t], {"1d": 300}, None)
    k3.baslat(t0)
    p3 = pp.Paper([t], k3, kur)
    p3.baslat(t0)
    k3.guncelle(simdi2)
    p3.adim(simdi2)
    assert [x["giris_zamani"] for x in p2.motor.islemler] == [x["giris_zamani"] for x in p3.motor.islemler]
    assert p2.motor.nakit == p3.motor.nakit


def test_canli_kaynak_bosluk_olayi():
    m = sentetik(100, "1d", 1)
    ist = SahteIstemci({("SOLUSDT", "1d"): m.drop(m.index[80:83])})        # 3 günlük delik
    t = TAN["swing__cci-esik|SOLUSDT|1d"]
    olaylar = []
    k = pc.CanliKaynak(ist, [t], {"1d": 50}, None, lambda tur, msg: olaylar.append(tur))
    k.baslat(m.index[78] + pd.Timedelta(days=1, seconds=5))
    k.guncelle(m.index[90])
    assert "veri_bosluk" in olaylar


def test_ws_akis_adlari():
    t = TAN["dis__dual-thrust|ETHUSDT|30m"]
    k = pc.CanliKaynak(SahteIstemci({}), [t, TAN["dis__fraktal-alligator-sky|DK_NVDA|4h"]], {}, None)
    a = pc.akislar(k)
    assert "ethusdt@kline_30m" in a and "nvdausdt@kline_5m" in a        # TradFi: 5m'den seans mumu kurulur
    assert pc.ws_url(a).startswith("wss://fstream.binance.com/market/stream?streams=")


class SahteFapi(SahteIstemci):
    """canli_calistir için: exchangeInfo + isteğe göre sentetik mum üretir (ağ yok)."""

    def __init__(self):
        super().__init__({})
        self.simdi = pd.Timestamp("2026-03-01 12:07", tz="UTC")
        self.sembol_tohum = {"BTCUSDT": 1, "ETHUSDT": 2, "SOLUSDT": 3, "NVDAUSDT": 4}

    def sunucu_zamani(self):
        return self.simdi

    def exchange_info(self):
        def s(ad, tick="0.01", step="0.001"):
            return {"symbol": ad, "contractType": "PERPETUAL", "status": "TRADING", "filters": [
                {"filterType": "PRICE_FILTER", "tickSize": tick}, {"filterType": "LOT_SIZE", "stepSize": step, "minQty": step},
                {"filterType": "MIN_NOTIONAL", "notional": "5"}]}
        return {"symbols": [s("BTCUSDT", "0.1"), s("ETHUSDT"), s("SOLUSDT", "0.01", "0.1"), s("NVDAUSDT", "0.01", "0.01")]}

    def klines(self, sembol, aralik, bas=None, bit=None, simdi=None):
        from motor.veri.depo import aralik_suresi
        a = aralik_suresi(aralik)
        bas = pd.Timestamp(bas) if bas is not None else simdi - 400 * a
        idx = pd.date_range(bas.ceil(a), simdi - a, freq=a)
        idx = idx[idx + a <= simdi]
        n = len(idx)
        base = sentetik(max(n, 2), "1d", self.sembol_tohum[sembol], p0=100.0, vol=0.01 * (a / pd.Timedelta(days=1)) ** 0.5 + 0.002)
        df = base.iloc[:n].copy()
        df.index = idx
        df.index.name = "zaman"
        return df


def test_canli_calistir_tek_sefer_sahte_binance(tmp_path, monkeypatch):
    from motor.canli import durum as d
    monkeypatch.setattr(pv, "FapiIstemci", SahteFapi)
    monkeypatch.setitem(pp.PENCERE, "1d", 120)
    monkeypatch.setitem(pp.PENCERE, "4h", 120)
    monkeypatch.setitem(pp.PENCERE, "30m", 300)
    assert pp.canli_calistir(tmp_path, None, False, tek_sefer=True) == 0
    veri, sorun = d.oku_hepsi(tmp_path)
    assert not sorun
    s = {x["kimlik"]: x for x in veri["stratejiler"]["stratejiler"]}
    # exchangeInfo'da olmayan semboller (DK_ hisse/emtia eşlemesi) -> o stratejiler VERİ YOK, uydurma yok
    assert s["pf__kanarya|hisse_emtia|1d"]["durum"].startswith("veri yok")
    assert s["pf__rotasyon|hepsi|1d"]["durum"].startswith("veri yok")
    assert s["dis__fraktal-alligator-sky|DK_NVDA|4h"]["durum"] == "calisiyor"
    assert any("VERİ YOK" in u for u in veri["saglik"]["uyarilar"])
    assert (tmp_path / "paper_state.json").exists()
    # ikinci çalıştırma durumu yükler (yeniden başlatma)
    assert pp.canli_calistir(tmp_path, None, False, tek_sefer=True) == 0
    assert any(o["tur"] == "yeniden_baslatma" for o in d.ek_oku(tmp_path, "olaylar"))
