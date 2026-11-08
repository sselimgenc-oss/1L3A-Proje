"""Bağımsız denetim (2026-11-08) paper/canlı düzeltmeleri: O8 hata koruması, O9 askıda kol, O10 çok sembollü satır bekletme,
O11 TradFi 1d eşiği (araştırma = paper), O12 --ayar-guncelle sütunları, O13 token maskeleme, O15 günlük özet, O17 BTC kıyas dosyası,
kill/günlük limitte tetikleyen birimin aynı adımda kapanması, deploy birimleri. Ağ yok."""
import dataclasses
import logging
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import SembolKurallari
from motor.canli import paper as pp
from motor.canli import paper_canli as pc
from motor.canli import paper_sinyal as psg
from motor.canli import paper_veri as pv
from motor.canli import telegram as tg
from motor.canli.paper_motor import Birim
from motor.portfoy.temel import PortfoyStratejisi
from testler.test_paper_canli import SahteIstemci
from testler.test_paper_motor import _iki_birimli, duz, tanim

KOK = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------- O8: tur hata koruması
def _paper_kayitli(tmp_path):
    p, tans = _iki_birimli()
    p.durum_yolu = tmp_path / "s.json"
    p.kaydet()
    return p, tans


def test_motor_hatasi_kaydedilir_bildirilir_durum_geri_yuklenir(tmp_path):
    p, _ = _paper_kayitli(tmp_path)
    bildirim = []
    p.bildirim = lambda tur, mesaj: bildirim.append((tur, mesaj))
    nakit0, acik0 = p.motor.nakit, set(p.motor.acik)

    def tur():                                    # satırın yarısında patlayan tur: bellek tutarsız kalır
        p.motor.nakit -= Decimal("123")
        p.motor.acik.clear()
        raise KeyError("bozuk_satir")

    k = pp.TurKoruyucu(p, lambda: p.yukle(ayar_guncelle=True, olay_yaz=False), p.kaydet, sinir=5)
    assert k.calistir(tur) is True                # ilk hata: devam
    assert p.motor.nakit == nakit0 and set(p.motor.acik) == acik0      # son tutarlı kayda dönüldü
    o = [x for x in p.olaylar if x["tur"] == "motor_hatasi"]
    assert len(o) == 1 and "KeyError" in o[0]["mesaj"] and "1/5" in o[0]["mesaj"]
    assert bildirim and bildirim[-1][0] == "motor_hatasi"              # Telegram yolu (Bildirimci) çağrıldı
    assert k.cikis_kodu == 0


def test_ayni_hata_n_kez_kontrollu_durur_farkli_hata_ve_basari_sayaci_sifirlar(tmp_path):
    p, _ = _paper_kayitli(tmp_path)

    def hata(msg):
        def f():
            raise ValueError(msg)
        return f
    k = pp.TurKoruyucu(p, lambda: None, None, sinir=3)
    assert k.calistir(hata("a")) and k.calistir(hata("a"))
    assert k.calistir(hata("b"))                  # farklı hata: sayaç 1'den
    assert k.calistir(lambda: None) and k.sayi == 0                   # başarılı tur sıfırlar
    assert k.calistir(hata("a")) and k.calistir(hata("a"))
    assert k.calistir(hata("a")) is False and k.cikis_kodu == 1       # 3. kez art arda: kontrollü dur
    assert p.olaylar[-1]["tur"] == "motor_durdu"


def test_geri_yukleme_basarisizsa_hemen_durur_ve_tutarsiz_isaretlenir(tmp_path):
    p, _ = _paper_kayitli(tmp_path)

    def bozuk_geri():
        raise RuntimeError("disk okunamadı")
    k = pp.TurKoruyucu(p, bozuk_geri, None, sinir=5)
    assert k.calistir(lambda: 1 / 0) is False
    assert not k.tutarli and k.cikis_kodu == 1


def test_binance_hatasi_gecici_sayilir(tmp_path):
    p, _ = _paper_kayitli(tmp_path)
    k = pp.TurKoruyucu(p, lambda: None, None, sinir=1, binance_hata=pv.BinanceHata)

    def f():
        raise pv.BinanceHata("HTTP 503")
    assert k.calistir(f) and k.calistir(f) and k.cikis_kodu == 0
    assert p.olaylar[-1]["tur"] == "binance_hata"


# ---------------------------------------------------------------------------- O9: veri yok olan kol askıda taşınır
def test_veri_yok_kol_askida_tasinir_digerleri_yuklenir_ve_geri_gelir(tmp_path):
    p, tans = _paper_kayitli(tmp_path)
    E0 = p.motor.ozsermaye()
    assert len(p.motor.acik) == 2
    mum = {(t.sembol, "1d"): duz(12, 100.0) for t in tans}
    kur = {t.sembol: SembolKurallari(0.01, 0.001, 0.001, 5.0) for t in tans}
    tans2 = [tans[0], dataclasses.replace(tans[1], veri_yok="BUSDT durumu SETTLING (TRADING değil)")]
    q = pp.Paper(tans2, pp.TekrarKaynagi(mum, {}), kur, durum_yolu=tmp_path / "s.json")
    olay = []
    q.bildirim = lambda tur, mesaj: olay.append(tur)
    assert q.yukle()                                                   # eskiden: KeyError / 'bilinmeyen kol'
    assert len(q.motor.acik) == 1 and len(q.motor.askida["acik"]) == 1
    assert q.motor.ozsermaye() == E0                                   # askıdaki pozisyon donmuş fiyatla değerlenir
    assert "askida" in olay and any("ASKIDA" in u for u in q.uyarilar)
    assert q.motor.brut_kaldirac() == pytest.approx(p.motor.brut_kaldirac())   # hesap düzeyi kaldıraca dahil
    q.kaydet()
    # sembol geri gelince: askıdaki kol aynen geri yüklenir
    r = pp.Paper(tans, pp.TekrarKaynagi(mum, {}), kur, durum_yolu=tmp_path / "s.json")
    assert r.yukle()
    assert set(r.motor.acik) == set(p.motor.acik) and not r.motor.askida["acik"]
    assert r.motor.ozsermaye() == E0


# ---------------------------------------------------------------------------- O10: çok sembollü birim satırı beklenir
def _gun_df(gunler, p=100.0):
    idx = pd.DatetimeIndex(pd.to_datetime(gunler, utc=True), name="zaman")
    return pd.DataFrame({"acilis": p, "yuksek": p + 1, "dusuk": p - 1, "kapanis": p, "hacim": 1.0, "quote_hacim": 1.0,
                         "islem_sayisi": 1}, index=idx)


def test_cok_sembollu_birim_eksik_sembolu_bekler_zaman_asiminda_veri_bosluk():
    olaylar = []
    k = pc.CanliKaynak(SahteIstemci({}), [], {}, None, lambda tur, msg: olaylar.append((tur, msg)))
    # Cuma 2024-03-08 .. Pazartesi 2024-03-11: BTC her gün, NVDA (hisse) yalnız Cuma
    k.mumlar = {("BTCUSDT", "1d"): _gun_df(["2024-03-08", "2024-03-09", "2024-03-10", "2024-03-11"]),
                ("DK_NVDA", "1d"): _gun_df(["2024-03-08"])}
    b = Birim("pf", "1d", pd.Timedelta(days=1), [], ["BTCUSDT", "DK_NVDA"])
    son_t = pd.Timestamp("2024-03-07", tz="UTC")
    pzt_kap = pd.Timestamp("2024-03-12", tz="UTC")
    r = k.satirlar(b, son_t, pzt_kap + pd.Timedelta(seconds=60))
    # Cuma + hafta sonu (hisse beklenmez, uyarı yok) yayımlanır; Pazartesi NVDA gelene kadar BEKLER
    assert [str(t.date()) for t, _ in r] == ["2024-03-08", "2024-03-09", "2024-03-10"]
    assert not olaylar
    # NVDA Pazartesi mumu gelince satır tam yayımlanır
    k.mumlar[("DK_NVDA", "1d")] = _gun_df(["2024-03-08", "2024-03-11"])
    r = k.satirlar(b, pd.Timestamp("2024-03-10", tz="UTC"), pzt_kap + pd.Timedelta(seconds=400))
    assert len(r) == 1 and r[0][1]["DK_NVDA"] is not None and not olaylar
    # hiç gelmezse: zaman aşımından sonra eksik sembolle yayımlanır + veri_bosluk
    k.mumlar[("DK_NVDA", "1d")] = _gun_df(["2024-03-08"])
    assert not k.satirlar(b, pd.Timestamp("2024-03-10", tz="UTC"), pzt_kap + pd.Timedelta(seconds=pc.BIRIM_BEKLEME_SN - 1))
    r = k.satirlar(b, pd.Timestamp("2024-03-10", tz="UTC"), pzt_kap + pd.Timedelta(seconds=pc.BIRIM_BEKLEME_SN))
    assert len(r) == 1 and r[0][1]["DK_NVDA"] is None
    assert [t for t, _ in olaylar] == ["veri_bosluk"] and "DK_NVDA" in olaylar[0][1]


def test_tek_sembollu_birim_ve_tekrar_kaynagi_degismez():
    k = pc.CanliKaynak(SahteIstemci({}), [], {}, None)
    k.mumlar = {("BTCUSDT", "1d"): _gun_df(["2024-03-08", "2024-03-09"])}
    b = Birim("x", "1d", pd.Timedelta(days=1), [], ["BTCUSDT"])
    assert len(k.satirlar(b, None, pd.Timestamp("2024-03-10", tz="UTC"))) == 2


# ---------------------------------------------------------------------------- O11: TradFi 1d/4h — araştırma yolu == paper yolu
def _ham_5m(bas, bit, seed):
    idx = pd.date_range(bas, bit, freq="5min", tz="UTC", inclusive="left", name="zaman")
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.001, len(idx))))
    o = np.r_[100.0, c[:-1]]
    return pd.DataFrame({"acilis": o, "yuksek": np.maximum(o, c) * 1.0005, "dusuk": np.minimum(o, c) * 0.9995, "kapanis": c,
                         "hacim": 1.0, "quote_hacim": 2.0, "islem_sayisi": np.full(len(idx), 3, dtype="int64")}, index=idx)


class _Ham5m:
    """Binance TradFi perp gibi 7/24 5m mum sunar (yalnız kapanmış mumlar)."""

    def __init__(self, df):
        self.df = df

    def klines(self, sembol, aralik, bas=None, bit=None, simdi=None):
        assert aralik == "5m"
        d = self.df[(self.df.index >= pd.Timestamp(bas)) & (self.df.index + pd.Timedelta(minutes=5) <= simdi)]
        return d.copy()


@pytest.mark.parametrize("sembol,tf", [("DK_XAU", "1d"), ("DK_WTI", "1d"), ("DK_NVDA", "1d"), ("DK_NVDA", "4h")])
def test_tradfi_paper_yeniden_ornekleme_arastirma_ile_ayni(tmp_path, sembol, tf):
    from motor.canli import paper_takvim as tk
    from motor.veri.depo import mum_yolu
    from motor.veri.yeniden_ornekle import tf_mumlari, yeniden_ornekle, _seans_ayari
    ham = _ham_5m("2024-02-26", "2024-04-08", 5)                       # 6 hafta; ABD DST geçişi (10 Mart) dahil
    seansli = ham[tk.seans_maskesi(sembol, ham.index)]                 # araştırma verisi (Dukascopy: yalnız seans mumları)
    yol = mum_yolu(sembol, "5m", tmp_path)
    yol.parent.mkdir(parents=True)
    seansli.to_parquet(yol)
    arastirma = tf_mumlari(sembol, tf, dizin=tmp_path)
    # paper: her gün kapanıştan sonra kısa pencere (canlı CanliKaynak.guncelle gibi)
    ist, parca = _Ham5m(ham), []
    for gun in pd.date_range("2024-02-26", "2024-04-07", freq="D", tz="UTC"):
        parca.append(pv.mumlar(ist, sembol, tf, gun, gun + pd.Timedelta(days=1, seconds=5)))
    paper = pd.concat(parca)
    paper = paper[~paper.index.duplicated()]
    kol = ["acilis", "yuksek", "dusuk", "kapanis", "hacim", "quote_hacim", "islem_sayisi"]
    pd.testing.assert_frame_equal(paper[kol], arastirma[kol], check_freq=False)
    if sembol in ("DK_XAU", "DK_WTI"):
        pazar = pd.Timestamp("2024-03-10", tz="UTC")
        assert pazar not in paper.index                                # Pazar emtia barı yok (araştırmada da yok)
        # eski davranış (pencere medyanı) Pazar barını üretiyordu: test hatayı yakalar
        pencere = ham[(ham.index >= pazar) & (ham.index < pazar + pd.Timedelta(days=1))]
        pencere = pencere[tk.seans_maskesi(sembol, pencere.index)]
        assert pazar in yeniden_ornekle(pencere, tf, kaynak="5m", eksikleri_at=True, **_seans_ayari(sembol)).index


def test_yeniden_ornekle_beklenen_sayi_verilmezse_davranis_ayni():
    from motor.veri.yeniden_ornekle import yeniden_ornekle
    df = _ham_5m("2024-03-04", "2024-03-06", 1)
    df = df.drop(df.index[5:250])
    a = yeniden_ornekle(df, "1d", esik_orani=0.25)
    b = yeniden_ornekle(df, "1d", esik_orani=0.25, beklenen_sayi=None)
    pd.testing.assert_frame_equal(a, b)
    c = yeniden_ornekle(df, "1d", esik_orani=0.25, beklenen_sayi=288)
    assert bool(c["eksik"].iloc[0]) and not bool(a["eksik"].iloc[0])  # 43/288 < 0.25 (sabit); pencere medyanıyla 'tam' sayılırdı


# ---------------------------------------------------------------------------- O12: --ayar-guncelle portföy sütunları
class _SahtePf(PortfoyStratejisi):
    ad = "test__pf"
    varsayilan_parametreler = {"semboller": ("AUSDT", "BUSDT", "CUSDT"), "w": 0.0}

    def hedefler(self, veriler):
        from motor.portfoy.temel import ortak_eksen
        eks = ortak_eksen(veriler)
        return pd.DataFrame({s: self.parametreler["w"] for s in self.parametreler["semboller"]}, index=eks)

    def stoplar(self, veriler, hedefler):
        return pd.DataFrame({s: veriler[s]["kapanis"].reindex(hedefler.index) * 0.9 for s in hedefler.columns}, index=hedefler.index)


def _pf_tanim(semboller, w, ayar):
    return psg.StratejiTanim("pf__test|x|1d", "portfoy", "portfoy", "test__pf", "", "1d", ayar,
                             _SahtePf(semboller=tuple(semboller), w=w), "pf__test|x|1d", Decimal("1"), evren=("AUSDT", "BUSDT", "CUSDT"))


def _pf_kur(tmp_path, w):
    mum = {(s, "1d"): duz(20, 100.0 + k) for k, s in enumerate(("AUSDT", "BUSDT", "CUSDT"))}
    kur = {s: SembolKurallari(0.01, 0.001, 0.001, 5.0) for s in ("AUSDT", "BUSDT", "CUSDT")}
    t = _pf_tanim(("AUSDT", "BUSDT", "CUSDT"), w, "eski")
    p = pp.Paper([t], pp.TekrarKaynagi(mum, {}), kur, durum_yolu=tmp_path / "s.json")
    p.baslat(mum[("AUSDT", "1d")].index[5])
    p.adim(mum[("AUSDT", "1d")].index[8])
    p.kaydet()
    return mum, kur, p


def test_ayar_guncelle_yeni_sembol_kumesini_kullanir(tmp_path):
    mum, kur, p = _pf_kur(tmp_path, 0.0)
    assert p.pf_sutunlar["pf__test|x|1d"] == ["AUSDT", "BUSDT", "CUSDT"] and not p.motor.acik
    yeni = _pf_tanim(("AUSDT", "BUSDT"), 0.2, "yeni")
    q = pp.Paper([yeni], pp.TekrarKaynagi(mum, {}), kur, durum_yolu=tmp_path / "s.json")
    assert q.yukle(ayar_guncelle=True)
    assert q.pf_sutunlar["pf__test|x|1d"] == ["AUSDT", "BUSDT"]
    assert [k.sembol for k in q.birimler[0].kollar] == ["AUSDT", "BUSDT"]
    assert not q.motor.askida["kol"]                                   # bilerek çıkarılan kol askıda sayılmaz
    assert any(o["tur"] == "ayar_guncelle" and "CUSDT" in o["mesaj"] for o in q.olaylar)


def test_ayar_guncelle_cikan_sembolde_acik_pozisyon_varsa_acik_hata(tmp_path):
    mum, kur, p = _pf_kur(tmp_path, 0.2)
    assert any(q.sembol == "CUSDT" for q in p.motor.acik.values())
    yeni = _pf_tanim(("AUSDT", "BUSDT"), 0.2, "yeni")
    q = pp.Paper([yeni], pp.TekrarKaynagi(mum, {}), kur, durum_yolu=tmp_path / "s.json")
    with pytest.raises(RuntimeError, match="AÇIK POZİSYON"):
        q.yukle(ayar_guncelle=True)


# ---------------------------------------------------------------------------- O13: token loga sızmaz
TOKEN = "123456789:AAH-gizliTokenDegeri_abcdefghijk1234"


def test_telegram_ag_hatasinda_token_loga_sizmaz(caplog):
    class Oturum:
        def post(self, url, **kw):
            raise ConnectionError(f"HTTPSConnectionPool: Max retries exceeded with url: {url}")
    env = {tg.TOKEN_ENV: TOKEN, tg.CHAT_ENV: "42"}
    with caplog.at_level(logging.DEBUG):
        assert tg.gonder("x", env=env, oturum=Oturum(), uyku=lambda s: None) is False
    assert TOKEN not in caplog.text and "AAH-gizli" not in caplog.text
    assert "ConnectionError" in caplog.text and "***" in caplog.text


def test_maskele_kalip():
    assert TOKEN not in tg.maskele(f"https://api.telegram.org/bot{TOKEN}/sendMessage")
    assert tg.maskele("sıradan metin 12:30") == "sıradan metin 12:30"


# ---------------------------------------------------------------------------- O15: günlük özet TSİ 00:10, dün tam gün, restartta tekrar yok
def test_gunluk_ozet_zamani_tsi_ve_state(tmp_path):
    p, _ = _paper_kayitli(tmp_path)
    once = pd.Timestamp("2026-11-08 21:09", tz="UTC")              # 00:09 TSİ (9 Kasım)
    sonra = pd.Timestamp("2026-11-08 21:10", tz="UTC")             # 00:10 TSİ
    assert pp.dun_tsi(sonra) == "2026-11-08"
    p.son_ozet = "2026-11-07"
    assert not pp.ozet_zamani(p, once) and pp.ozet_zamani(p, sonra)
    assert not pp.ozet_zamani(p, pd.Timestamp("2026-11-08 20:00", tz="UTC"))   # 23:00 TSİ: dün=7 Kasım zaten gönderildi
    p.son_ozet = pp.dun_tsi(sonra)
    p.kaydet()
    q, tans = _iki_birimli()
    q.durum_yolu = tmp_path / "s.json"
    assert q.yukle() and q.son_ozet == "2026-11-08"
    assert not pp.ozet_zamani(q, sonra + pd.Timedelta(hours=5))     # yeniden başlatma: aynı gün tekrar gitmez


def test_dun_ozeti_tam_gun_kz_ve_metin():
    p, _ = _iki_birimli()
    p.motor.gun_kapanis_tsi = {"2026-11-06": Decimal("10000"), "2026-11-07": Decimal("10050"), "2026-11-08": Decimal("10020")}
    d = pp.dun_ozeti(p, "2026-11-07")
    assert d["pnl"] == Decimal("50") and d["getiri"] == pytest.approx(0.005) and d["not"] is None
    from testler.test_telegram import html_gecerli, ozet
    m = tg.ozet_metni(ozet(), dun=d)
    assert "Dün (TSİ tam gün): +50,00 $" in m and "7 Kasım 2026" in m and "Bugün" not in m and html_gecerli(m)
    assert pp.dun_ozeti(p, "2026-11-10")["pnl"] == 0                 # işlenen mum yok: 0 + not


# ---------------------------------------------------------------------------- O17: BTC kıyas 1h dosyası atomik güncellenir
class _BtcIst:
    def __init__(self):
        self.cagri = []

    def klines(self, sembol, aralik, bas, bit, simdi):
        self.cagri.append((sembol, aralik, bas))
        idx = pd.date_range(pd.Timestamp(bas).ceil("h"), simdi - pd.Timedelta(hours=1), freq="h", name="zaman")
        idx = idx[idx + pd.Timedelta(hours=1) <= simdi]
        return pd.DataFrame({"acilis": 1.0, "yuksek": 1.0, "dusuk": 1.0, "kapanis": np.arange(len(idx), dtype=float) + 50000,
                             "hacim": 1.0, "quote_hacim": 1.0, "islem_sayisi": np.ones(len(idx), dtype="int64")}, index=idx)


def test_kiyas_btc_1h_dosyasi_guncellenir_ve_kiyas_okur(tmp_path):
    from motor.canli import kiyas as ky
    ist = _BtcIst()
    s1 = pd.Timestamp("2026-11-08 12:00:05", tz="UTC")
    assert pp.kiyas_btc_guncelle(ist, tmp_path, s1) > 0
    s2 = s1 + pd.Timedelta(hours=3)
    assert pp.kiyas_btc_guncelle(ist, tmp_path, s2) == 3
    assert ist.cagri[-1][2] == pd.Timestamp("2026-11-08 12:00", tz="UTC")       # artımlı: yalnız yeni mumlar istenir
    seri, tf = ky.kapanislar("BTCUSDT", tmp_path)
    assert tf == "1h" and seri.index[-1] == pd.Timestamp("2026-11-08 15:00", tz="UTC")   # kapanış zamanı = taze
    assert not list(tmp_path.rglob("*.tmp"))


def test_kiyas_btc_arastirma_dizinine_yazmaz_ve_hata_uyari(tmp_path):
    ist = _BtcIst()
    assert pp.kiyas_btc_guncelle(ist, KOK / "veri" / "mumlar", pd.Timestamp("2026-11-08", tz="UTC")) is None and not ist.cagri

    class Bozuk:
        def klines(self, *a, **k):
            raise pv.BinanceHata("HTTP 503")
    p, _ = _iki_birimli()
    assert pp.kiyas_btc_guncelle(Bozuk(), tmp_path, pd.Timestamp("2026-11-08", tz="UTC"), p) is None
    assert any("kıyas BTC" in u for u in p.uyarilar)


# ---------------------------------------------------------------------------- kill/günlük limit: eşleşme aracı çekirdek kuralını korur
def test_eslesme_modunda_tetikleyen_birim_sonraki_acilista_kapanir():
    tans = [tanim("a|AUSDT|1d", "AUSDT", grup="g1", pay="0.5"), tanim("b|BUSDT|1d", "BUSDT", grup="g2", pay="0.5")]
    mum = {(t.sembol, "1d"): duz(12, 100.0) for t in tans}
    kur = {t.sembol: SembolKurallari(0.01, 0.001, 0.001, 5.0) for t in tans}
    p = pp.tekrar_calistir(tans, mum, {}, kur, mum[("AUSDT", "1d")].index[3], kapat=False, tetikleyen_hemen_kapat=False)
    m = p.motor
    b_a = p.birimler[0]
    t = b_a.son_t + pd.Timedelta(days=1)
    m.acilis_fazi(b_a, t, {"AUSDT": (100.0, 100.1, 99.9, 100.0)})
    m.nakit -= Decimal("2100")
    m.kapanis_fazi(b_a, t, None)
    assert m.kill and b_a.kollar[0].cikis_emri == "kill_switch" and len(m.acik) == 1


# ---------------------------------------------------------------------------- deploy: OnFailure + Telegram oneshot
def test_deploy_birimleri():
    s = (KOK / "deploy" / "1l3a-paper.service").read_text(encoding="utf-8")
    assert "OnFailure=1l3a-bildirim@%n.service" in s and "TimeoutStopSec=120" in s and "Restart=on-failure" in s
    b = (KOK / "deploy" / "1l3a-bildirim@.service").read_text(encoding="utf-8")
    assert "Type=oneshot" in b and "EnvironmentFile=-/etc/1l3a-paper.env" in b and "--servis-hatasi %i" in b
    assert "TELEGRAM_BOT_TOKEN=" not in b and "api.telegram.org" not in b


def test_servis_hatasi_metni_ve_cli_yapilandirmasiz(monkeypatch):
    monkeypatch.delenv(tg.TOKEN_ENV, raising=False)
    m = tg.servis_hatasi_metni("1l3a-paper.service", {"MONITOR_SERVICE_RESULT": "exit-code", "MONITOR_EXIT_STATUS": "1"})
    assert "1l3a-paper.service" in m and "exit-code" in m and "Servis durdu" in m
    assert tg.main(["--servis-hatasi", "1l3a-paper.service"]) == 1      # yapılandırma yok: gönderilmez (loglanır), çıkış 1
