"""Denetim bulguları B05-B11 (2026-11-10): limit uygulaması (açılış MTM, askıda pozisyon), funding imleci, sembol bazlı maliyet,
geç gelen bar, kaldıraç tavanında kayma payı. Ağ yok."""
import dataclasses
import json
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import SembolKurallari, kaldirac_tavani_miktar
from motor.canli import paper as pp
from motor.canli import paper_canli as pc
from motor.canli.paper_motor import Birim, PaperMotor, _dec, _enc
from motor.portfoy.motor import PortfoyAyarlari, portfoy_backtest
from testler.test_paper_canli import SahteIstemci
from testler.test_paper_motor import _iki_birimli, duz, tanim
from testler.test_portfoy_motor import KURAL, Elle, ayar, mumlar, tablo

GUN = pd.Timedelta(days=1)


# ---------------------------------------------------------------------------- B09: açılış MTM ile limit (portföy çekirdeği = referans)
def test_b09_portfoy_acilis_boslugu_gunluk_limiti_girislerden_once_kurar():
    n = 8
    # A: 5. satırda (index 4) -%4 açılış boşluğu (stop 95'in üstünde), kapanışta toparlanır -> eski kod yalnız kapanışta baktığı için limit hiç tetiklenmezdi
    A = mumlar([(100, 100.5, 99.5, 100)] * 4 + [(96, 100.6, 95.5, 100)] + [(100, 100.5, 99.5, 100)] * 3, frekans="1D")
    B = mumlar([(50, 50.5, 49.5, 50)] * n, frekans="1D")
    h, s = tablo(A.index, ["A", "B"]), tablo(A.index, ["A", "B"])
    h.iloc[0, 0], s.iloc[0, 0] = 1.0, 95.0           # A: satır 1 açılışında 1x long
    h.iloc[3, 1], s.iloc[3, 1] = 0.5, 40.0           # B: giriş emri tam boşluk satırının (4) açılışında yürütülür
    r = portfoy_backtest({"A": A, "B": B}, Elle(h, s), ayar())
    olaylar = [o for o in r.limit_olaylari if o["tur"] == "gunluk_kayip"]
    assert olaylar and olaylar[0]["zaman"] == A.index[4] and olaylar[0]["evre"] == "acilis"
    assert (r.islemler.sembol == "B").sum() == 0, "boşluk günü limit aşıkken yeni giriş açılmamalı"
    assert any(x["sembol"] == "B" and x["neden"] == "gunluk_kayip_limiti" for x in r.reddedilenler)
    a = r.islemler[r.islemler.sembol == "A"].iloc[0]
    assert a.cikis_nedeni == "gunluk_limit" and a.cikis_zamani == A.index[4]


def test_b09_paper_acilis_boslugu_baska_birimin_girisini_engeller_ve_acigi_kapatir():
    tans = [tanim("a|AUSDT|1d", "AUSDT", grup="g1", pay="1", stop_yuzde=1.0), tanim("b|BUSDT|1d", "BUSDT", grup="g2", pay="1", stop_yuzde=1.0)]
    mum = {(t.sembol, "1d"): duz(12, 100.0) for t in tans}
    kur = {t.sembol: SembolKurallari(0.01, 0.001, 0.001, 5.0) for t in tans}
    p = pp.tekrar_calistir(tans, mum, {}, kur, mum[("AUSDT", "1d")].index[3], kapat=False)
    m = p.motor
    b_a, b_b = p.birimler
    kid_a, kid_b = [k for k in m.acik if k.startswith("a|")][0], [k for k in m.acik if k.startswith("b|")][0]
    m.acik.pop(kid_b)                                      # B düz; giriş emri bekliyor (HepsiLong her barda long ister)
    assert m.tum_kollar[1].giris_emri is not None
    qa = m.acik[kid_a].miktar
    t = b_b.son_t + GUN
    bar_b = (100.0, 100.1, 99.9, 100.0)
    bar_a_bosluk = (96.0, 100.1, 95.9, 100.0)               # A -%4 boşluk (stop 99 hemen altı: A'nın kendi satırı daha işlenmedi)
    m.acilis_fazi(b_b, t, {"BUSDT": bar_b, "AUSDT": bar_a_bosluk})
    assert m.gunluk_blok and m.limit_olaylari[-1]["evre"] == "acilis" and m.limit_olaylari[-1]["tur"] == "gunluk_kayip"
    assert not any(q.kol.birim == b_b.ad for q in m.acik.values()), "limit aşıkken B girişi açılmamalı"
    assert any(r["neden"] == "gunluk_kayip_limiti" and r["sembol"] == "BUSDT" for r in m.reddedilenler)
    # A açık pozisyonu aynı adımda, boşluk (açılış) fiyatından stop kaymasıyla kapandı (eski kapanış fiyatından değil)
    x = next(i for i in m.islemler if i["sembol"] == "AUSDT" and i["cikis_nedeni"] == "gunluk_limit")
    assert x["cikis_fiyati"] == pytest.approx(96.0 * (1 - 0.0005), abs=0.011) and x["miktar"] == float(qa)
    assert not m.acik


def test_b09_kill_acilis_boslugunda_da_kurulur():
    p, _ = _iki_birimli()
    m = p.motor
    b_a, _ = p.birimler
    m.nakit -= Decimal("2100")                            # zirveden ~ -%21, kapanış fazı daha çalışmadan
    t = b_a.son_t + GUN
    m.acilis_fazi(b_a, t, {"AUSDT": (100.0, 100.1, 99.9, 100.0)})
    assert m.kill and not m.acik
    assert any(o["tur"] == "kill_switch" and o["evre"] == "acilis" for o in m.limit_olaylari)


# ---------------------------------------------------------------------------- B11: askıdaki pozisyon limitte kapanır
def _askili(tmp_path):
    p, tans = _iki_birimli()
    p.durum_yolu = tmp_path / "s.json"
    p.kaydet()
    mum = {(t.sembol, "1d"): duz(12, 100.0) for t in tans}
    kur = {t.sembol: SembolKurallari(0.01, 0.001, 0.001, 5.0) for t in tans}
    tans2 = [tans[0], dataclasses.replace(tans[1], veri_yok="BUSDT durumu SETTLING (TRADING değil)")]
    q = pp.Paper(tans2, pp.TekrarKaynagi(mum, {}), kur, durum_yolu=tmp_path / "s.json")
    olay = []
    q.bildirim = lambda tur, mesaj: olay.append(tur)
    assert q.yukle()
    assert len(q.motor.acik) == 1 and len(q.motor.askida["acik"]) == 1
    return q, olay


def test_b11_gunluk_limitte_askida_pozisyon_da_kapanir_ve_alarm_yazar(tmp_path):
    q, olay = _askili(tmp_path)
    m = q.motor
    b_a = q.birimler[0]
    brut0 = m.brut_kaldirac()
    askida_nominal = m._askida_katki()[1]
    assert askida_nominal > 0 and brut0 > 0
    t = b_a.son_t + GUN
    m.acilis_fazi(b_a, t, {"AUSDT": (100.0, 100.1, 99.9, 100.0)})
    m.nakit -= Decimal("350")                              # ~ -%3.5 gün içi
    m.kapanis_fazi(b_a, t, None)
    assert m.gunluk_blok and not m.acik
    assert not m.askida["acik"], "askıdaki pozisyon limitte açık kalmamalı"
    assert len(m.askida_kapanislar) == 1 and m.askida_kapanislar[0]["sembol"] == "BUSDT" and m.askida_kapanislar[0]["cikis_nedeni"] == "gunluk_limit"
    assert m.brut_kaldirac() == 0
    q._satir_sonrasi(b_a, t)
    assert "askida_kapatma" in olay and any(o["tur"] == "askida_kapatma" for o in q.olaylar)
    # kayıt/yükleme: kapanış kaydı korunur, askıda pozisyon geri gelmez
    d = _dec(json.loads(json.dumps(_enc(m.durum_al()))))
    assert d["askida_kapanislar"] and not any(v["kol"].startswith("b|") for v in d["acik"].values())


def test_b11_kill_acilis_fazinda_askida_pozisyonu_kapatir(tmp_path):
    q, _ = _askili(tmp_path)
    m = q.motor
    b_a = q.birimler[0]
    m.nakit -= Decimal("2100")
    m.acilis_fazi(b_a, b_a.son_t + GUN, {"AUSDT": (100.0, 100.1, 99.9, 100.0)})
    assert m.kill and not m.acik and not m.askida["acik"]


# ---------------------------------------------------------------------------- mevcut durum dosyası yüklenir (eski biçim: yeni anahtarlar yok)
def test_eski_durum_dosyasi_yeni_alanlar_olmadan_yuklenir(tmp_path):
    p, tans = _iki_birimli()
    d = json.loads(json.dumps(_enc(p.durum_sozlugu())))
    for k in ("askida_kapanislar", "gec_bar_olaylari"):
        d["motor"].pop(k, None)
    yol = tmp_path / "eski.json"
    yol.write_text(json.dumps(d))
    mum = {(t.sembol, "1d"): duz(12, 100.0) for t in tans}
    kur = {t.sembol: SembolKurallari(0.01, 0.001, 0.001, 5.0) for t in tans}
    q = pp.Paper(tans, pp.TekrarKaynagi(mum, {}), kur, durum_yolu=yol)
    assert q.yukle()
    assert q.motor.askida_kapanislar == [] and q.motor.gec_bar_olaylari == []
    assert set(q.motor.acik) == set(p.motor.acik) and q.motor.nakit == p.motor.nakit
    q.adim(mum[("AUSDT", "1d")].index[-1] + GUN)               # yüklenen durumla devam edilebilir


# ---------------------------------------------------------------------------- B05: funding imleci
def _funding_motoru():
    p, _ = _iki_birimli()
    m = p.motor
    pos = next(q for q in m.acik.values() if q.sembol == "AUSDT")
    idx = pd.date_range("2025-01-01", periods=400, freq="h", tz="UTC")
    m.fiyat_serisi("AUSDT", idx, np.full(len(idx), 100.0))
    pos.son_f = pd.Timestamp("2025-01-05 00:00", tz="UTC")
    return m, pos


def test_b05_gec_gelen_funding_kaydi_bir_kez_odenir():
    m, pos = _funding_motoru()
    r1, r2, r3 = (pd.Timestamp(x, tz="UTC") for x in ("2025-01-05 08:00", "2025-01-05 16:00", "2025-01-06 00:00"))
    qty = pos.miktar * pos.yon
    # tur 1: yalnız r1 geldi (r2 henüz yayımlanmadı), satır 2025-01-05 20:00 açılışında işleniyor
    m.funding_serisi("AUSDT", pd.DatetimeIndex([r1]), np.array([0.001]))
    o1 = m._funding_ode(pos, pd.Timestamp("2025-01-05 20:00", tz="UTC"), True)
    assert o1 == qty * Decimal("100.0") * Decimal("0.001")
    # tur 2: r2 GEÇ geldi (zamanı son satırdan önce); sonraki satırda ödenmeli (eskiden imleç bitis'e atlayıp sonsuza dek atlanıyordu)
    m.funding_serisi("AUSDT", pd.DatetimeIndex([r1, r2]), np.array([0.001, 0.002]))
    o2 = m._funding_ode(pos, pd.Timestamp("2025-01-05 21:00", tz="UTC"), True)
    assert o2 == qty * Decimal("100.0") * Decimal("0.002")
    # tekrar çağrı: çift ödeme yok
    assert m._funding_ode(pos, pd.Timestamp("2025-01-05 22:00", tz="UTC"), True) == 0
    m.funding_serisi("AUSDT", pd.DatetimeIndex([r1, r2, r3]), np.array([0.001, 0.002, 0.003]))
    assert m._funding_ode(pos, pd.Timestamp("2025-01-06 00:00", tz="UTC"), True) == qty * Decimal("100.0") * Decimal("0.003")
    assert pos.funding == qty * Decimal("100.0") * Decimal("0.006")


def test_b05_backtest_funding_toplami_degismez():
    """Tüm kayıtlar baştan varken (backtest) imleç değişikliği sonucu etkilemez: her kayıt tam bir kez ödenir."""
    m, pos = _funding_motoru()
    zam = pd.date_range("2025-01-05 08:00", periods=6, freq="8h", tz="UTC")
    m.funding_serisi("AUSDT", zam, np.full(6, 0.001))
    top = Decimal(0)
    for h in range(1, 60):
        top += m._funding_ode(pos, pd.Timestamp("2025-01-05 00:00", tz="UTC") + pd.Timedelta(hours=h), True)
    assert top == pos.miktar * pos.yon * Decimal("100.0") * Decimal("0.001") * 6


# ---------------------------------------------------------------------------- B06: sembol bazlı maliyet (hesap geneli en yüksek değil)
def test_b06_paper_kill_cikisi_sembolun_kendi_maliyetini_kullanir():
    tans = [tanim("a|AUSDT|1d", "AUSDT", grup="g1", pay="0.5"), tanim("b|BUSDT|1d", "BUSDT", grup="g2", pay="0.5")]
    mum = {(t.sembol, "1d"): duz(12, 100.0) for t in tans}
    kur = {t.sembol: SembolKurallari(0.01, 0.001, 0.001, 5.0) for t in tans}
    ms = {"AUSDT": (0.05, 0.02, 2.0, 5.0), "BUSDT": (0.10, 0.02, 4.0, 30.0)}
    ay = PortfoyAyarlari(komisyon_taker_yuzde=0.10, komisyon_maker_yuzde=0.02, kayma_bps=4.0, stop_kayma_bps=30.0, maliyet_sembol=ms, limit_modu="uygula")
    p = pp.tekrar_calistir(tans, mum, {}, kur, mum[("AUSDT", "1d")].index[3], ayarlar=ay, kapat=False)
    m = p.motor
    assert len(m.acik) == 2
    b_a, _ = p.birimler
    t = b_a.son_t + GUN
    m.acilis_fazi(b_a, t, {"AUSDT": (100.0, 100.1, 99.9, 100.0)})
    m.nakit -= Decimal("2100")
    m.kapanis_fazi(b_a, t, None)
    cik = {x["sembol"]: x for x in m.islemler if x["cikis_nedeni"] == "kill_switch"}
    assert cik["AUSDT"]["cikis_fiyati"] == pytest.approx(100.0 * (1 - 0.0005), abs=0.011)      # A'nın stop kayması 5 bps (hesap geneli 30 değil)
    assert cik["BUSDT"]["cikis_fiyati"] == pytest.approx(100.0 * (1 - 0.0030), abs=0.011)
    ucret_a = next(x for x in m.maliyet_log if x["tur"] == "ucret" and x["sembol"] == "AUSDT" and x["zaman"] == t + GUN)
    assert ucret_a["tutar"] == Decimal(str(cik["AUSDT"]["cikis_fiyati"])) * Decimal(str(cik["AUSDT"]["miktar"])) * Decimal("0.0005")


# ---------------------------------------------------------------------------- B07: geç gelen bar
def _gun_df(gunler, p=100.0, **kw):
    idx = pd.DatetimeIndex(pd.to_datetime(gunler, utc=True), name="zaman")
    d = {"acilis": p, "yuksek": p + 1, "dusuk": p - 1, "kapanis": p, "hacim": 1.0, "quote_hacim": 1.0, "islem_sayisi": 1}
    d.update(kw)
    return pd.DataFrame(d, index=idx)


def test_b07_kaynak_gec_gelen_mumu_bir_kez_verir():
    k = pc.CanliKaynak(SahteIstemci({}), [], {}, None, lambda tur, msg: None)
    k.mumlar = {("BTCUSDT", "1d"): _gun_df(["2024-03-08", "2024-03-09", "2024-03-10", "2024-03-11"]),
                ("DK_NVDA", "1d"): _gun_df(["2024-03-08"])}
    b = Birim("pf", "1d", pd.Timedelta(days=1), [], ["BTCUSDT", "DK_NVDA"])
    pzt = pd.Timestamp("2024-03-11", tz="UTC")
    r = k.satirlar(b, pd.Timestamp("2024-03-10", tz="UTC"), pzt + GUN + pd.Timedelta(seconds=pc.BIRIM_BEKLEME_SN))
    assert len(r) == 1 and r[0][1]["DK_NVDA"] is None
    b.son_t = pzt
    assert k.gec_barlar(b) == []                                       # mum henüz yok
    k.mumlar[("DK_NVDA", "1d")] = _gun_df(["2024-03-08", "2024-03-11"], dusuk=94.0)
    g = k.gec_barlar(b)
    assert len(g) == 1 and g[0][0] == pzt and g[0][1] == "DK_NVDA" and g[0][2][2] == 94.0
    assert k.gec_barlar(b) == []                                       # bir kez


def test_b07_gec_gelen_barda_kacirilan_stop_kontrol_edilir():
    p, tans = _iki_birimli()
    m = p.motor
    b_a, _ = p.birimler
    kid = [k for k in m.acik if k.startswith("a|")][0]
    pos = m.acik[kid]
    stop = pos.stop
    # satır: A'nın mumu yokmuş gibi işlenir (zaman aşımı)
    t = b_a.son_t + GUN
    m.acilis_fazi(b_a, t, {"AUSDT": None})
    m.kapanis_fazi(b_a, t, None)
    b_a.son_t = t
    assert kid in m.acik
    # mum SONRADAN gelir: düşük stopun altında -> kaçırılan stop kontrolü çalışır (yalnız bu barın OHLC'si)
    ol = m.gec_bar_isle(b_a, t, "AUSDT", (100.0, 100.2, float(stop) - 1.0, 100.0))
    assert ol["sonuc"] == "stop" and kid not in m.acik
    x = m.islemler[-1]
    assert x["cikis_nedeni"] == "stop" and x["cikis_zamani"] == t + GUN and x["sembol"] == "AUSDT"
    assert m.gec_bar_olaylari[-1] is ol
    # yuva durumu geri yüklendi (sonraki satırları bozmaz)
    assert m.VAR["AUSDT"][0] is False


def test_b07_gec_gelen_bar_stopa_degmezse_pozisyon_ve_deger_degismez():
    p, _ = _iki_birimli()
    m = p.motor
    b_a, _ = p.birimler
    kid = [k for k in m.acik if k.startswith("a|")][0]
    t = b_a.son_t + GUN
    m.acilis_fazi(b_a, t, {"AUSDT": None})
    m.kapanis_fazi(b_a, t, None)
    b_a.son_t = t
    nakit0, son_kap0 = m.nakit, m.son_kap["AUSDT"]
    ol = m.gec_bar_isle(b_a, t, "AUSDT", (100.0, 100.5, 99.9, 100.2))
    assert ol["sonuc"] == "temiz" and kid in m.acik and m.nakit == nakit0 and m.son_kap["AUSDT"] == son_kap0


def test_b07_paper_adim_gec_barlari_isler_ve_olay_yazar():
    """Uçtan uca: iki sembollü birim, B mumu zaman aşımından sonra gelir; Paper.adim bar için stop kontrolünü çalıştırır ve olay yazar."""
    p, _ = _iki_birimli()
    b_a = p.birimler[0]
    t = b_a.son_t + GUN
    calls = []

    class K:
        def gec_barlar(self, b):
            return [(t, "AUSDT", (100.0, 100.2, 50.0, 100.0))] if (b is b_a and not calls) else []

        def satirlar(self, *a):
            return []

    kid = [k for k in p.motor.acik if k.startswith("a|")][0]
    b_a.son_t = t
    p.kaynak = K()
    calls.append(1)
    p.kaynak = K()
    calls.clear()
    olay = []
    p.bildirim = lambda tur, mesaj: olay.append(tur)
    n = p.adim(t + GUN)
    assert n == 0 and p._son_gec == 1 and "gec_bar" in olay
    assert kid not in p.motor.acik and p.motor.islemler[-1]["cikis_nedeni"] == "stop"


# ---------------------------------------------------------------------------- B10: kaldıraç tavanı kaymayı da taşır
def test_b10_kaldirac_tavani_kayma_payi_dahil_dolumda_3x_asilmaz():
    # tek-grafik fonksiyonu: çağıran taker + kayma verir; dolum fiyatındaki nominal + komisyon + kayma kaybı <= K·E
    E, K, taker, kayma, ham = Decimal("10000"), Decimal(3), Decimal("0.0005"), Decimal("0.0002"), Decimal("100")
    fiyat = ham * (1 + kayma)
    q = kaldirac_tavani_miktar(E, K, taker + kayma, fiyat)
    nominal = q * fiyat
    ozs_sonra = E - nominal * taker - q * (fiyat - ham)
    assert float(K) * (1 - 1e-5) <= float(nominal / ozs_sonra) <= float(K)
    eski = kaldirac_tavani_miktar(E, K, taker, fiyat) * fiyat
    assert eski / (E - eski * taker - eski / fiyat * (fiyat - ham)) > K          # eski tavan: 3x'in üstünde


def test_b10_portfoy_motoru_dolum_sonrasi_kaldirac_3x_asilmaz():
    n = 6
    ad = ["A", "B", "C", "D"]
    veri = {k: mumlar([(100, 100.5, 99.5, 100)] * n, frekans="1D") for k in ad}
    ix = veri["A"].index
    h, s = tablo(ix, ad), tablo(ix, ad)
    h.iloc[0, :], s.iloc[0, :] = 1.0, 99.5                          # 4 x 1x istenir -> orantılı olarak 3x tavana kırpılır
    r = portfoy_backtest(veri, Elle(h, s), ayar(komisyon_taker_yuzde=0.05, kayma_bps=20.0))
    px = round(100 * 1.002, 2)
    assert len(r.islemler) == 4
    nominal = sum(x.miktar * px for x in r.islemler.itertuples())
    ozs_sonra = 10000.0 - nominal * 0.0005 - sum(x.miktar * (px - 100.0) for x in r.islemler.itertuples())
    assert nominal / ozs_sonra <= 3.0 + 2e-3
    assert nominal / ozs_sonra > 2.9
