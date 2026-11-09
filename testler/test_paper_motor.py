"""Paper motoru: tekrar modu = backtest (sentetik veri, ağ yok), ortak hesap limitleri, kalıcılık, Decimal/step."""
import dataclasses
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import tarama
from motor.backtest.motor import SembolKurallari
from motor.canli import paper as pp
from motor.canli import paper_esleme as es
from motor.canli import paper_sinyal as psg
from motor.canli.paper_motor import PaperMotor, PKol, Birim
from motor.portfoy.motor import PortfoyAyarlari
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.temel import Strateji


def sentetik(n, tf, seed, bas="2024-01-01", p0=100.0, vol=0.012, hafta_ici=False):
    rng = np.random.default_rng(seed)
    frek = {"30m": "30min", "4h": "4h", "1d": "D"}[tf]
    idx = pd.date_range(bas, periods=n * (2 if hafta_ici else 1), freq=frek, tz="UTC", name="zaman")
    if hafta_ici:
        idx = idx[idx.dayofweek < 5][:n]
    r = rng.normal(0.0002, vol, len(idx))
    c = p0 * np.exp(np.cumsum(r))
    o = np.r_[p0, c[:-1]] * (1 + rng.normal(0, vol / 6, len(idx)))
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, vol / 3, len(idx))))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, vol / 3, len(idx))))
    return pd.DataFrame({"acilis": o, "yuksek": h, "dusuk": l, "kapanis": c, "hacim": 1000.0, "quote_hacim": 1e5,
                         "islem_sayisi": 10}, index=idx)


TAN = {t.kimlik: t for t in psg.tanimlari_yukle(ayar_kaynagi="kilit")}


def kural(s):
    return tarama.SEMBOL_KURALLARI.get(s, tarama.VARSAYILAN_KURAL)


@pytest.mark.parametrize("kimlik,tf,n,bas_i,seed", [
    ("swing__cci-esik|SOLUSDT|1d", "1d", 500, 300, 1),
    ("swing__konsolidasyon-kirilim|SOLUSDT|4h", "4h", 1500, 1000, 2),
    ("dis__fraktal-alligator-sky|DK_NVDA|4h", "4h", 1500, 1000, 3),
    ("dis__dual-thrust|ETHUSDT|30m", "30m", 1200, 600, 4),
])
def test_tek_grafik_tekrar_modu_backtest_ile_ayni(kimlik, tf, n, bas_i, seed):
    t = TAN[kimlik]
    m = sentetik(n, tf, seed=seed, p0=100.0, vol=0.02 if tf != "30m" else 0.006)
    r = es.tek_esle(t, m, None, {t.sembol: kural(t.sembol)}, m.index[bas_i])
    assert r["n_backtest"] == r["n_paper"] and r["n_backtest"] >= 1, "sentetik veride işlem üretmeli"
    assert r["tam_esit_zaman_haric"], r["farklar"][:3]
    assert r["max_mutlak_fark"] <= 1e-9


def _pf_veri(t, n=520, seed=7):
    out = {}
    for k, s in enumerate(t.evren):
        out[s] = sentetik(n, "1d", seed + k, p0=50 + 10 * k, vol=0.025, hafta_ici=s.startswith("DK_"))
    return out


@pytest.mark.parametrize("kimlik", ["pf__kesit_ls|kripto|1d", "pf__rotasyon|hepsi|1d"])
def test_portfoy_tekrar_modu_backtest_ile_ayni(kimlik):
    t = TAN[kimlik]
    ver = _pf_veri(t)
    bas = ver[t.evren[0]].index[430]
    r = es.pf_esle(t, ver, {}, {s: kural(s) for s in t.evren}, bas)
    assert r["n_backtest"] == r["n_paper"] and r["n_backtest"] > 0
    assert r["tam_esit_zaman_haric"], r["farklar"][:3]
    assert r["max_mutlak_fark"] <= 1e-9


def test_pencere_kesilmesi_yalniz_sonlu_bellekli_gostergelerde_etki_eder():
    """Pencereli (son N bar) girdi ile tam geçmiş sonuçları: cci-esik için işlemler aynı (raporlanır, gizlenmez)."""
    t = TAN["swing__cci-esik|SOLUSDT|1d"]
    m = sentetik(700, "1d", 5, vol=0.03)
    tam = es.tek_esle(t, m, None, {t.sembol: kural(t.sembol)}, m.index[500])
    pen = es.tek_esle(t, m, None, {t.sembol: kural(t.sembol)}, m.index[500], pencere={"1d": 200})
    assert tam["tam_esit_zaman_haric"] and pen["n_paper"] >= 0
    assert pen["n_backtest"] == tam["n_backtest"]


# ---------------------------------------------------------------------------- yardımcı strateji (limit testleri)
class HepsiLong(Strateji):
    ad = "test__hepsi_long"
    stil = "swing"
    varsayilan_parametreler = {"stop_yuzde": 1.0}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=1000)

    def cikis_var_mi(self):
        return True

    def sinyaller(self, mumlar):
        c = mumlar["kapanis"]
        sig = pd.DataFrame({"yon": 1, "stop": c * (1 - self.parametreler["stop_yuzde"] / 100), "hedef": np.nan,
                            "cikis": False}, index=mumlar.index)
        return sig


def tanim(kimlik, sembol, grup="g", pay="1", tf="1d", stop_yuzde=1.0):
    return psg.StratejiTanim(kimlik, "swing", "tek_grafik", "test__hepsi_long", sembol, tf, "x",
                             HepsiLong(stop_yuzde=stop_yuzde), grup, Decimal(pay))


def duz(n, p, tf="1d", dalga=0.001):
    idx = pd.date_range("2025-01-01", periods=n, freq="D", tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": p, "yuksek": p * (1 + dalga), "dusuk": p * (1 - dalga), "kapanis": p, "hacim": 1.0, "quote_hacim": 1.0,
                         "islem_sayisi": 1}, index=idx)


def test_tek_hesapta_kaldirac_ve_toplam_risk_tavani():
    """Çok dar stoplu 4 strateji aynı anda girer: brüt <= 3x ve toplam stop riski <= %5 (hesap düzeyinde) kalır."""
    tans = [tanim(f"k{i}|S{i}USDT|1d", f"S{i}USDT", grup="tek", pay="0.5", stop_yuzde=0.05) for i in range(4)]
    mum = {(t.sembol, "1d"): duz(10, 100.0, dalga=0.0) for t in tans}
    kur = {t.sembol: SembolKurallari(0.01, 0.001, 0.001, 5.0) for t in tans}
    p = pp.tekrar_calistir(tans, mum, {}, kur, mum[("S0USDT", "1d")].index[3], kapat=False)
    m = p.motor
    assert len(m.acik) > 0
    assert m.brut_kaldirac() <= 3.0 + 1e-9
    assert m.acik_stop_riski() <= 0.05 + 1e-9
    # grup (tek-grafik kolu payı 0.5): grup stop riski <= %5 x grup payı
    E = m.ozsermaye()
    risk_grup = sum((max((Decimal(m.son_kap[q.sembol]) - q.stop) * q.miktar * q.yon, Decimal(0)) for q in m.acik.values()), Decimal(0))
    assert risk_grup <= Decimal("0.05") * E * Decimal("0.5") * Decimal("1.0001")


def test_miktar_asagi_yuvarlanir_ve_step_filtresi_uygulanir():
    t = tanim("a|XUSDT|1d", "XUSDT", pay="1", stop_yuzde=3.0)
    mum = {("XUSDT", "1d"): duz(8, 123.45)}
    kur = {"XUSDT": SembolKurallari(0.01, 0.1, 0.1, 5.0)}
    p = pp.tekrar_calistir([t], mum, {}, kur, mum[("XUSDT", "1d")].index[2], kapat=False)
    q = next(iter(p.motor.acik.values()))
    assert q.miktar % Decimal("0.1") == 0 and q.miktar > 0
    # maliyet dahil işlem başı risk (2026-11-09): birim risk = |giriş-stop| + max(giriş, stop)·(stop_kayma + 2·taker) (paper varsayılanları)
    from motor.risk.limitler import maliyetli_risk_birim
    ay = p.ayarlar
    ham = Decimal("10000") * Decimal("0.01") / maliyetli_risk_birim(q.giris, q.stop, Decimal(repr(ay.stop_kayma_bps)) / 10000,
                                                                   Decimal(repr(ay.komisyon_taker_yuzde)) / 100)
    assert q.miktar <= ham                        # aşağı yuvarlama (yukarı değil)
    assert ham - q.miktar < Decimal("0.1")


def test_min_notional_reddi():
    t = tanim("a|XUSDT|1d", "XUSDT", pay="1", stop_yuzde=3.0)
    mum = {("XUSDT", "1d"): duz(8, 123.45)}
    kur = {"XUSDT": SembolKurallari(0.01, 0.1, 0.1, 1e9)}
    p = pp.tekrar_calistir([t], mum, {}, kur, mum[("XUSDT", "1d")].index[2], kapat=False)
    assert not p.motor.acik and any(r["neden"] == "min_notional" for r in p.motor.reddedilenler)


def _iki_birimli():
    tans = [tanim("a|AUSDT|1d", "AUSDT", grup="g1", pay="0.5"), tanim("b|BUSDT|1d", "BUSDT", grup="g2", pay="0.5")]
    mum = {(t.sembol, "1d"): duz(12, 100.0) for t in tans}
    kur = {t.sembol: SembolKurallari(0.01, 0.001, 0.001, 5.0) for t in tans}
    p = pp.tekrar_calistir(tans, mum, {}, kur, mum[("AUSDT", "1d")].index[3], kapat=False)
    assert len(p.motor.acik) == 2
    return p, tans


def test_gunluk_limit_ortak_hesap_diger_birimi_hemen_kapatir_ve_giris_durdurur():
    p, tans = _iki_birimli()
    m = p.motor
    b_a, b_b = p.birimler
    # A birimi satırında hesap -%3'ün altına iner (nakitten zarar yazılır): limit tetiklenmeli
    t = b_a.son_t + pd.Timedelta(days=1)
    bar = (100.0, 100.1, 99.9, 100.0)
    m.acilis_fazi(b_a, t, {"AUSDT": bar})
    m.nakit -= Decimal("350")                    # ~ -%3.5 gün içi
    m.kapanis_fazi(b_a, t, None)
    assert m.gunluk_blok and m.gunluk_limit_sayisi == 1
    assert [o["tur"] for o in m.limit_olaylari] == ["gunluk_kayip"]
    # diğer birimin (B) pozisyonu beklemeden kapandı
    assert all(q.kol.birim != b_b.ad for q in m.acik.values())
    assert any(x["cikis_nedeni"] == "gunluk_limit" and x["sembol"] == "BUSDT" for x in m.islemler)
    # A'nın (tetikleyen birim) kendi pozisyonu da AYNI ADIMDA kapandı (bir bar beklenmez)
    assert not m.acik
    assert any(x["cikis_nedeni"] == "gunluk_limit" and x["sembol"] == "AUSDT" for x in m.islemler)
    # yeni giriş yok: ertesi gün açılışında (aynı UTC günü değil) ama bugün içinde B satırı giriş yapamaz
    t2 = t
    m.acilis_fazi(b_b, t2, {"BUSDT": bar})
    assert not any(q.kol.birim == b_b.ad for q in m.acik.values())


def test_kill_switch_kalici_ve_hepsini_durdurur():
    p, tans = _iki_birimli()
    m = p.motor
    b_a, b_b = p.birimler
    t = b_a.son_t + pd.Timedelta(days=1)
    bar = (100.0, 100.1, 99.9, 100.0)
    m.acilis_fazi(b_a, t, {"AUSDT": bar})
    m.nakit -= Decimal("2100")                   # zirveden ~ -%21
    m.kapanis_fazi(b_a, t, None)
    assert m.kill and not m.acik                     # tetikleyen birim (A) dahil hepsi aynı adımda kapandı
    assert {x["sembol"] for x in m.islemler if x["cikis_nedeni"] == "kill_switch"} == {"AUSDT", "BUSDT"}
    # kalıcılık: kill durumu diske yazılıp geri yüklenince korunur
    import json
    from motor.canli.paper_motor import _dec, _enc
    d = _dec(json.loads(json.dumps(_enc(m.durum_al()))))
    p2, _ = _iki_birimli()
    p2.motor.durum_yukle(d)
    assert p2.motor.kill


def test_paper_limit_modu_olc_reddedilir():
    with pytest.raises(ValueError):
        PaperMotor(PortfoyAyarlari(limit_modu="olc"), {})


def test_yeniden_baslatma_ayni_sonuc(tmp_path):
    """Yarıda kaydet -> yeni nesneye yükle -> devam: kesintisiz koşuyla işlemler birebir aynı."""
    t = TAN["swing__cci-esik|SOLUSDT|1d"]
    m = sentetik(520, "1d", 11, vol=0.03)
    kur = {t.sembol: kural(t.sembol)}
    mumlar = {(t.sembol, t.tf): m}
    bas, ara, bit = m.index[400], m.index[460], m.index[-1] + pd.Timedelta(days=1)
    tam = pp.tekrar_calistir([pp.psg.StratejiTanim(**{**dataclasses.asdict(t), "nesne": t.nesne})], mumlar, {}, kur, bas, bit, kapat=False)
    # kesintili
    kay = pp.TekrarKaynagi(mumlar, {})
    a = pp.Paper([t], kay, kur, durum_yolu=tmp_path / "s.json")
    a.baslat(bas)
    a.adim(ara)
    a.kaydet()
    b = pp.Paper([t], pp.TekrarKaynagi(mumlar, {}), kur, durum_yolu=tmp_path / "s.json")
    assert b.yukle()
    b.adim(bit)
    assert [x["giris_zamani"] for x in b.motor.islemler] == [x["giris_zamani"] for x in tam.motor.islemler]
    assert [x["net_pnl"] for x in b.motor.islemler] == [x["net_pnl"] for x in tam.motor.islemler]
    assert b.motor.nakit == tam.motor.nakit and len(b.motor.acik) == len(tam.motor.acik)


def test_durum_ayar_farki_acik_hata(tmp_path):
    t = TAN["swing__cci-esik|SOLUSDT|1d"]
    m = sentetik(520, "1d", 11)
    kur = {t.sembol: kural(t.sembol)}
    a = pp.Paper([t], pp.TekrarKaynagi({(t.sembol, t.tf): m}, {}), kur, durum_yolu=tmp_path / "s.json")
    a.baslat(m.index[400])
    a.kaydet()
    t2 = dataclasses.replace(t, ayar="baska")
    b = pp.Paper([t2], pp.TekrarKaynagi({(t.sembol, t.tf): m}, {}), kur, durum_yolu=tmp_path / "s.json")
    with pytest.raises(RuntimeError, match="ayar"):
        b.yukle()
    assert b.yukle(ayar_guncelle=True)


def test_set_tek_hesapta_calisir_ve_toplamlar_tutar():
    """7 strateji tek hesapta (sentetik): çalışır; strateji katkıları toplamı = özsermaye - başlangıç (kuruşuna)."""
    from motor.canli import paper_durum as pdr
    tans = list(psg.tanimlari_yukle(ayar_kaynagi="kilit"))
    mum, fund = {}, {}
    for k, t in enumerate(tans):
        for j, s in enumerate(t.veri_semboller):
            if (s, t.tf) not in mum:
                mum[(s, t.tf)] = sentetik({"30m": 700, "4h": 600, "1d": 600}[t.tf], t.tf, 100 + k * 13 + j, vol=0.02,
                                          hafta_ici=s.startswith("DK_") and t.tf == "1d")
    kur = {s: kural(s) for t in tans for s in t.veri_semboller}
    ilk = mum[("ETHUSDT", "30m")].index[650]
    p = pp.tekrar_calistir(tans, mum, fund, kur, mum[("SOLUSDT", "1d")].index[500], None, pencere={"30m": 400, "4h": 400, "1d": 400}, kapat=False)
    m = p.motor
    toplam = sum((pdr.strateji_pnl(p, t.kimlik)["toplam"] for t in tans), Decimal(0))
    assert abs((m.ozsermaye() - Decimal(10000)) - toplam) < Decimal("0.0001")
    assert m.brut_kaldirac() <= 3.0 + 1e-9 and m.acik_stop_riski() <= 0.05 + 1e-6
