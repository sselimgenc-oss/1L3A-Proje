"""Kullanıcı kararı 2026-11-09:
(1) İşlem başı %1 risk MALİYET DAHİL (fiyat riski + stop kayması + giriş/çıkış komisyonu) — backtest, portföy (sinyal kolu), paper motoru ve
    secim.yeniden_oyna aynı kuralı uygular; r tanımı (fiyat riski cinsinden net) değişmez.
(2) Paper TradFi funding'i öder ama ayrı alanda tutar; backtest beklentisi kıyasları TradFi funding HARİÇ yapılır.
"""
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import evren_maliyet as em
from motor.arastirma import secim as sec
from motor.arastirma import wf_evren as we
from motor.backtest.motor import MotorAyarlari, SembolKurallari, backtest
from motor.canli import dersler as ders
from motor.canli import karne as kr_
from motor.canli import koc as kc
from motor.canli import paper as pp
from motor.canli import paper_durum as pdr
from motor.canli import paper_veri as pv
from motor.canli import pano as pn
from motor.canli.paper_motor import PaperMotor
from motor.portfoy.birlesik import birlesik_backtest
from motor.portfoy.motor import PortfoyAyarlari
from motor.risk.limitler import SERT_LIMITLER, maliyetli_risk_birim
from testler.test_bt_motor import Hazir, mumlar_yap, sinyal_yap
from testler.test_paper_motor import TAN, kural, sentetik, tanim

KASA = 10000.0
LIMIT = KASA * SERT_LIMITLER.islem_basi_max_risk_yuzde / 100          # 100 USD
PAY = 0.02                                                              # yuvarlama payı (tick/step): 2 sent
INCE = SembolKurallari(tick_size=0.01, step_size=1e-6, min_qty=1e-6, min_notional=1.0)
# evren maliyet tablosundan: kripto ve hisse örneği
SEMBOLLER = ["BTCUSDT", "DK_AAPL"]


def _ay_bt(sembol: str) -> MotorAyarlari:
    return em.maliyet_ayarlari(sembol, INCE, 1.0)


def _stop_senaryosu(yon: int):
    """Mum 0 kapanışında sinyal (stop 2% uzakta), mum 1 açılışında giriş, mum 1 içinde stop değer (gap yok)."""
    if yon == 1:
        df = mumlar_yap([(100, 100, 100, 100), (100, 100.2, 97.0, 97.5), (97.5, 97.5, 97.5, 97.5)])
        return df, sinyal_yap(df, {0: (1, 98.0, np.nan)})
    df = mumlar_yap([(100, 100, 100, 100), (100, 103.0, 99.8, 102.5), (102.5, 102.5, 102.5, 102.5)])
    return df, sinyal_yap(df, {0: (-1, 102.0, np.nan)})


# ---------------------------------------------------------------------------- (1) backtest motoru
@pytest.mark.parametrize("sembol", SEMBOLLER)
@pytest.mark.parametrize("yon", [1, -1])
def test_backtest_stop_toplam_kaybi_yuzde1i_asmaz(sembol, yon):
    df, sig = _stop_senaryosu(yon)
    r = backtest(df, Hazir(sig), _ay_bt(sembol))
    t = r.islemler.iloc[0]
    assert t.cikis_nedeni == "stop"
    kayip = KASA - float(r.ozsermaye.iloc[-1])
    assert kayip == pytest.approx(-t.net_pnl)
    assert kayip <= LIMIT + PAY                     # maliyet dahil <= %1
    assert kayip >= LIMIT - 0.5                     # ve neredeyse tam %1 (boyut gereksiz küçülmedi)
    # r tanımı değişmedi: net / (miktar·|giriş − ilk stop|) -> tam stop kaybında |r| > 1 (maliyetler fiyat riskinin üstünde)
    stop = 98.0 if yon == 1 else 102.0
    assert t.r == pytest.approx(t.net_pnl / (t.miktar * abs(t.giris_fiyati - stop)), rel=1e-9)
    assert t.r < -1.0


def test_backtest_eski_formul_yuzde1i_asardi():
    """Kontrol: yalnız fiyat riskiyle boyutlansaydı aynı stop %1'i aşardı (değişikliğin nedeni, denetim O7)."""
    df, sig = _stop_senaryosu(1)
    ay = _ay_bt("DK_AAPL")
    fiyat = 100 * (1 + ay.kayma_bps / 1e4)
    eski_miktar = LIMIT / (fiyat - 98.0)
    yeni_miktar = backtest(df, Hazir(sig), ay).islemler.iloc[0].miktar
    assert yeni_miktar < eski_miktar
    assert yeni_miktar == pytest.approx(LIMIT / float(maliyetli_risk_birim(fiyat, 98.0, ay.stop_kayma_bps / 1e4,
                                                                             ay.komisyon_taker_yuzde / 100)), rel=1e-5)


# ---------------------------------------------------------------------------- (1) portföy motoru (sinyal kolu)
class _Bir(Hazir):
    def __init__(self, yon):
        self.yon = yon
        super().__init__(None)

    def sinyaller(self, mumlar):
        return _stop_senaryosu(self.yon)[1].set_axis(mumlar.index)


@pytest.mark.parametrize("sembol", SEMBOLLER)
@pytest.mark.parametrize("yon", [1, -1])
def test_portfoy_sinyal_kolu_stop_kaybi_yuzde1i_asmaz(sembol, yon):
    df, _ = _stop_senaryosu(yon)
    ms = {sembol: em.sembol_maliyeti(sembol, 1.0)}
    ay = PortfoyAyarlari(limit_modu="olc", maliyet_sembol=ms, kurallar={sembol: INCE})
    r = birlesik_backtest({sembol: df}, [(_Bir(yon), sembol)], ay, toplam_risk_tavani_yuzde=5.0)
    t = r.islemler.iloc[0]
    assert t.cikis_nedeni == "stop"
    assert -t.net_pnl <= LIMIT + PAY and -t.net_pnl >= LIMIT - 0.5
    # tek-grafik motoruyla aynı boyut (aynı maliyet)
    bt = backtest(df, Hazir(_stop_senaryosu(yon)[1]), _ay_bt(sembol)).islemler.iloc[0]
    assert t.miktar == pytest.approx(bt.miktar, rel=1e-6)


# ---------------------------------------------------------------------------- (1) paper motoru
def _duz_stop(n_once=4, n_sonra=3, p=100.0):
    idx = pd.date_range("2025-01-01", periods=n_once + 1 + n_sonra, freq="D", tz="UTC", name="zaman")
    sat = [(p, p, p, p)] * n_once + [(p, p * 1.001, p * 0.97, p * 0.975)] + [(p * 0.975,) * 4] * n_sonra
    df = pd.DataFrame(sat, columns=["acilis", "yuksek", "dusuk", "kapanis"], index=idx)
    df["hacim"], df["quote_hacim"], df["islem_sayisi"] = 1.0, 1.0, 1
    return df


@pytest.mark.parametrize("sembol", ["XUSDT", "DK_AAPL"])
def test_paper_stop_kaybi_yuzde1i_asmaz(sembol):
    t = tanim(f"a|{sembol}|1d", sembol, pay="1", stop_yuzde=2.0)
    mum = {(sembol, "1d"): _duz_stop()}
    mal = em.sembol_maliyeti("BTCUSDT" if sembol == "XUSDT" else sembol, 1.0)
    ay = PortfoyAyarlari(baslangic_sermaye=KASA, limit_modu="uygula", maliyet_sembol={sembol: mal})
    ix = mum[(sembol, "1d")].index
    p = pp.tekrar_calistir([t], mum, {}, {sembol: INCE}, ix[3], kapat=False, ayarlar=ay)
    ilk = p.motor.islemler[0]
    assert ilk["cikis_nedeni"] == "stop"
    assert -ilk["net_pnl"] <= LIMIT + PAY and -ilk["net_pnl"] >= LIMIT - 0.5


# ---------------------------------------------------------------------------- (1) yeniden_oyna + eşdeğerlik
T0 = pd.Timestamp("2022-01-03", tz="UTC")


@pytest.mark.parametrize("sembol", SEMBOLLER)
@pytest.mark.parametrize("yon", [1, -1])
def test_yeniden_oyna_tam_stop_kaybi_yuzde1(sembol, yon):
    """r = tam stop kaybı (fiyat riski + maliyet, fiyat riski cinsinden) -> kasa kaybı tam %1."""
    taker_y, _, _, stop_bps = em.sembol_maliyeti(sembol, 1.0)
    sf = 0.02
    mp = float(sec.maliyet_payi(sf, yon, stop_bps / 1e4, taker_y / 100))
    r = -(sf + mp) / sf
    tablo = pd.DataFrame({"kol": ["k"], "sembol": [sembol], "yon": [yon], "giris": [T0], "cikis": [T0 + pd.Timedelta(hours=5)],
                          "r": [r], "sf": [sf], "maliyet_payi": [mp]})
    s = sec.yeniden_oyna(tablo)
    assert s["islem_pnl"][0][1] == pytest.approx(-0.01, rel=1e-12)
    eski = sec.yeniden_oyna(tablo.assign(maliyet_payi=0.0))                 # yalnız fiyat riski: %1'i aşardı
    assert eski["islem_pnl"][0][1] < -0.01


def test_yeniden_oyna_maliyet_payi_zorunlu():
    tablo = pd.DataFrame({"kol": ["k"], "sembol": ["A"], "yon": [1], "giris": [T0], "cikis": [T0 + pd.Timedelta(hours=5)],
                          "r": [1.0], "sf": [0.02]})
    with pytest.raises(ValueError, match="maliyet_payi"):
        sec.yeniden_oyna(tablo)


@pytest.mark.parametrize("sembol", SEMBOLLER)
@pytest.mark.parametrize("yon", [1, -1])
def test_yeniden_oyna_backtest_ile_ayni_riski_hesaplar(sembol, yon):
    """Aynı işlem: backtest motorunun boyutu (net_pnl / kasa) = yeniden_oyna'nın ham r'den hesapladığı K/Z; fiyat riski de aynı."""
    df, sig = _stop_senaryosu(yon)
    ay = _ay_bt(sembol)
    isl = backtest(df, Hazir(sig), ay).islemler
    t = isl.iloc[0]
    tablo = sec.islem_tablosu_hazirla({"k": (isl, sembol)}, (ay.stop_kayma_bps / 1e4, ay.komisyon_taker_yuzde / 100))
    s = sec.yeniden_oyna(tablo)
    assert s["islem_pnl"][0][1] == pytest.approx(t.net_pnl / KASA, rel=1e-6)
    stop = 98.0 if yon == 1 else 102.0
    fiyat_riski_bt = t.miktar * abs(t.giris_fiyati - stop) / KASA
    fiyat_riski_oy = s["islem_pnl"][0][1] / t.r
    assert fiyat_riski_oy == pytest.approx(fiyat_riski_bt, rel=1e-6)


def test_wf_evren_oynatma_tablosu_sembol_maliyeti_ve_carpan():
    oos = pd.DataFrame({"sembol": ["BTCUSDT", "DK_AAPL", "BTCUSDT"], "yon": [1, 1, -1], "giris_zamani": [T0] * 3,
                        "cikis_zamani": [T0 + pd.Timedelta(hours=1)] * 3, "r": [1.0] * 3, "sf": [0.02] * 3, "stop_mesafe": [1.0] * 3})
    t1 = we.oynatma_tablosu(oos, ("BTCUSDT", "DK_AAPL"), carpan=1.0).set_index(["sembol", "yon"])["maliyet_payi"]
    assert t1[("BTCUSDT", 1)] == pytest.approx(0.0005 + 2 * 0.0005)            # stop 5 bps + 2 x taker %0.05
    assert t1[("DK_AAPL", 1)] == pytest.approx(0.0010 + 2 * 0.0005)            # stop 10 bps
    assert t1[("BTCUSDT", -1)] == pytest.approx(1.02 * 0.0015)                 # short: max(giriş, stop) = giriş·(1+sf)
    t2 = we.oynatma_tablosu(oos, ("BTCUSDT", "DK_AAPL"), carpan=2.0).set_index(["sembol", "yon"])["maliyet_payi"]
    assert t2[("BTCUSDT", 1)] == pytest.approx(2 * 0.0015)                     # K1 maliyet x2
    with pytest.raises(ValueError, match="carpan"):
        we.oynatma_tablosu(oos, ("BTCUSDT", "DK_AAPL"))


# ---------------------------------------------------------------------------- (2) TradFi funding ayrımı
def test_tradfi_siniflama_ve_exchangeinfo_uyusmazligi():
    assert pv.tradfi_mi("DK_NVDA") and not pv.tradfi_mi("SOLUSDT")
    bilgi = {"symbols": [{"symbol": "NVDAUSDT", "contractType": "TRADIFI_PERPETUAL", "status": "TRADING"},
                         {"symbol": "SOLUSDT", "contractType": "PERPETUAL", "status": "TRADING"},
                         {"symbol": "AAPLUSDT", "contractType": "PERPETUAL", "status": "TRADING"}]}
    u = pv.tradfi_sinif_uyusmazliklari(bilgi, ["DK_NVDA", "SOLUSDT", "DK_AAPL"])
    assert len(u) == 1 and u[0].startswith("DK_AAPL")


def test_tradfi_alanlari_islem_satiri():
    x = {"sembol": "DK_NVDA", "funding": 5.0, "net_pnl": -50.0, "r": -0.5}
    a = PaperMotor.tradfi_alanlari(x, Decimal("100"))
    assert a["funding_tradfi"] == 5.0 and a["r_kiyas"] == pytest.approx(-0.45)
    assert PaperMotor.tradfi_alanlari(x) == a                                  # eski kayıt: risk net/r'den
    k = PaperMotor.tradfi_alanlari({"sembol": "SOLUSDT", "funding": 5.0, "net_pnl": -50.0, "r": -0.5})
    assert k == {"funding_tradfi": 0.0, "r_kiyas": -0.5}                         # kripto funding kıyasa dahil kalır


class _Kol:
    def __init__(self, sk, sembol):
        self.sk, self.sembol = sk, sembol


class _M:
    def __init__(self, log):
        self.maliyet_log = log
        self.tum_kollar = [_Kol("tek_nvda", "DK_NVDA"), _Kol("tek_sol", "SOLUSDT"), _Kol("pf_hepsi", "DK_XAU"), _Kol("pf_hepsi", "BTCUSDT")]


def test_tradfi_kumulatif_gunluk_ve_eski_kayit():
    z = lambda g: pd.Timestamp(g, tz="UTC")  # noqa: E731
    log = [{"zaman": z("2026-11-10 08:00"), "sk": "tek_nvda", "tur": "funding", "tutar": Decimal("1.5"), "sembol": "DK_NVDA"},
           {"zaman": z("2026-11-10 16:00"), "sk": "tek_sol", "tur": "funding", "tutar": Decimal("9"), "sembol": "SOLUSDT"},
           {"zaman": z("2026-11-11 00:00"), "sk": "pf_hepsi", "tur": "funding", "tutar": Decimal("2"), "sembol": "DK_XAU"},
           {"zaman": z("2026-11-11 08:00"), "sk": "tek_nvda", "tur": "funding", "tutar": Decimal("0.5")},              # eski: sembolsüz, sk tek TradFi
           {"zaman": z("2026-11-11 08:00"), "sk": "pf_hepsi", "tur": "funding", "tutar": Decimal("7")},                # eski: karışık -> belirsiz
           {"zaman": z("2026-11-11 08:00"), "sk": "tek_nvda", "tur": "ucret", "tutar": Decimal("3"), "sembol": "DK_NVDA"}]
    kayit, bel = pdr.tradfi_funding_kayitlari(_M(log))
    assert bel == {"adet": 1, "tutar": Decimal("7")}
    g = pdr.tradfi_kumulatif(kayit, ["2026-11-09", "2026-11-10", "2026-11-11"])
    assert g == {"2026-11-09": Decimal(0), "2026-11-10": Decimal("1.5"), "2026-11-11": Decimal("4.0")}
    assert pdr.tradfi_kumulatif(kayit, ["2026-11-11"], "tek_nvda") == {"2026-11-11": Decimal("2.0")}


def _satir(kimlik, r, rk, neden="stop"):
    return {"kimlik": kimlik, "r": r, "r_kiyas": rk, "cikis_nedeni": neden, "zaman": "2026-11-10T00:00:00Z",
            "giris_zamani": "2026-11-09T00:00:00Z", "cikis_zamani": "2026-11-10T00:00:00Z", "sembol": "DK_NVDA",
            "net_pnl_yerel": "1.00", "set_katki_usd": "1.00"}


def test_dersler_karne_koc_tradfi_funding_haric_r_kullanir():
    # r (funding dahil) hep <= 0, r_kiyas (TradFi funding hariç) hep > 0: kıyaslar r_kiyas'ı kullanmalı
    sat = [_satir("s", -0.01, 0.2) for _ in range(40)]
    ref = {"n": 100, "isabet": 0.5, "ort_r": 0.1, "std_r": 1.0, "pf_r": 1.3, "cikis_paylari": {"stop": 1.0}}
    o = ders.degerlendir("s", sat, ref)
    assert o["isabet"] == 1.0 and o["ort_r"] == pytest.approx(0.2)
    assert "zarar eden işlem yok" in str(kr_.kalite(sat))                    # r ile PF = 0 olurdu; r_kiyas ile zarar yok
    assert kc._kazanmadi(sat[0]) is False
    assert kc._kazanmadi({"r": -0.01}) is True                                  # r_kiyas alanı yok (backtest): r


def test_pano_tradfi_funding_ayri_satir():
    blok = {"ucret": "1.00", "kayma": "0.50", "funding": "2.00", "toplam": "3.50"}
    ml = {"toplam": {"son24s": blok, "tum": blok},
          "funding_tradfi": {"toplam": "1.25", "kapanan": "1.00", "acik": "0.25", "son24s": "0.10", "belirsiz_adet": 0, "belirsiz_tutar": "0.00"}}
    h = pn._maliyet_toplam(ml)
    assert "TradFi funding" in h and "1.25" in h
    assert "motor bu alanı yazmıyor" in pn._maliyet_toplam({"toplam": {"son24s": blok, "tum": blok}})


def test_paper_tradfi_funding_ayri_tutulur_ve_kiyas_haric():
    """Gerçek paper akışı: TradFi (DK_NVDA) ve kripto (SOLUSDT) funding'i ödenir; işlem satırında funding_tradfi yalnız TradFi'de,
    ozet/maliyet funding_tradfi toplamı = TradFi işlemlerinin funding'i + açık TradFi pozisyonu; r_kiyas = r + funding_tradfi/risk."""
    tans = [TAN["dis__fraktal-alligator-sky|DK_NVDA|4h"], TAN["swing__cci-esik|SOLUSDT|1d"]]
    nv = sentetik(1500, "4h", 3, p0=100.0, vol=0.02)
    sol = sentetik(500, "1d", 1, p0=100.0, vol=0.02, bas=str(nv.index[0].date()))
    mum = {("DK_NVDA", "4h"): nv, ("SOLUSDT", "1d"): sol}
    fz = pd.date_range(nv.index[0], nv.index[-1], freq="8h", tz="UTC")
    fund = {"DK_NVDA": pd.DataFrame({"oran": 0.0003}, index=fz), "SOLUSDT": pd.DataFrame({"oran": 0.0002}, index=fz)}
    kur = {"DK_NVDA": kural("DK_NVDA"), "SOLUSDT": kural("SOLUSDT")}
    p = pp.tekrar_calistir(tans, mum, fund, kur, nv.index[1000], kapat=False)
    simdi = nv.index[-1] + pd.Timedelta(hours=4, minutes=5)
    o = pdr.olustur(p, simdi, beklenti_csv=pdr.BEKLENTI_CSV)
    m = p.motor
    nv_isl = [x for x in m.islemler if x["sembol"] == "DK_NVDA"]
    sol_isl = [x for x in m.islemler if x["sembol"] == "SOLUSDT"]
    assert nv_isl and sol_isl, "sentetik veride iki sembolde de işlem olmalı"
    assert any(x["funding"] != 0 for x in nv_isl)
    for x in nv_isl:
        assert x["funding_tradfi"] == x["funding"]
        risk = x["net_pnl"] / x["r"]
        assert x["r_kiyas"] == pytest.approx((x["net_pnl"] + x["funding"]) / risk, rel=1e-9)
    for x in sol_isl:
        assert x["funding_tradfi"] == 0.0 and x["r_kiyas"] == x["r"]
    assert any(x["funding"] != 0 for x in sol_isl)                            # kripto funding ödendi ama ayrı alana girmedi
    beklenen = sum(Decimal(repr(x["funding"])) for x in nv_isl) + sum((q.funding for q in m.acik.values() if q.sembol == "DK_NVDA"), Decimal(0))
    tf = o["ozet"]["funding_tradfi"]
    assert abs(Decimal(tf["toplam"]) - beklenen) <= Decimal("0.01")
    assert o["ekstra"]["maliyet"]["funding_tradfi"] == tf
    satirlar = [s for s in o["islemler"] if s["sembol"] == "DK_NVDA"]
    assert all(Decimal(s["funding_tradfi"]) == Decimal(pdr.d.para(x["funding"])) for s, x in zip(satirlar, sorted(nv_isl, key=lambda x: x["cikis_zamani"])))
    assert any(s["r_kiyas"] != s["r"] for s in satirlar)
