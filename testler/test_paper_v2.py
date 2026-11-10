"""Paper v2 seti: 10 strateji, her biri kendi sanal kasasında (motor/canli/paper_v2.py). Sentetik veri; ağ/gerçek veri gerekmez
(set/tanım testleri yalnız depodaki dosyaları okur)."""
import copy
import dataclasses
import json
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from motor.backtest.motor import D, SembolKurallari
from motor.canli import paper as pp
from motor.canli import paper_sinyal as psg
from motor.canli import paper_takvim as tk
from motor.canli import paper_v2 as v2
from motor.canli import paper_veri as pv
from motor.canli.paper_kaynak import TekrarKaynagi
from motor.canli.paper_motor import PaperDesteklemiyorHatasi
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.temel import Strateji

KOK = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------- yardımcılar
class OrtalamaTrend(Strateji):
    """close > SMA(n) iken long (nedensel), altında çıkış; stop %3. Test stratejisi."""
    ad = "test__ortalama_trend"
    stil = "swing"
    varsayilan_parametreler = {"n": 10}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=1000)

    def cikis_var_mi(self):
        return True

    def sinyaller(self, mumlar):
        c = mumlar["kapanis"]
        ma = c.rolling(self.parametreler["n"]).mean()
        yon = (c > ma).astype(int)
        return pd.DataFrame({"yon": yon, "stop": c * 0.97, "hedef": np.nan, "cikis": (c < ma).fillna(False)}, index=mumlar.index)


class HepsiYon(Strateji):
    ad = "test__hepsi_yon"
    stil = "swing"
    varsayilan_parametreler = {"yon": 1, "stop_yuzde": 1.0}
    cikis_ayarlari = CikisAyarlari(zaman_cikisi_mum=1000)

    def cikis_var_mi(self):
        return True

    def sinyaller(self, mumlar):
        c = mumlar["kapanis"]
        y = self.parametreler["yon"]
        stop = c * (1 - y * self.parametreler["stop_yuzde"] / 100)
        return pd.DataFrame({"yon": y, "stop": stop, "hedef": np.nan, "cikis": False}, index=mumlar.index)


def sentetik(n, seed, p0=100.0, vol=0.02, bas="2025-01-01"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(bas, periods=n, freq="D", tz="UTC", name="zaman")
    r = rng.normal(0.0003, vol, n)
    c = p0 * np.exp(np.cumsum(r))
    o = np.r_[p0, c[:-1]] * (1 + rng.normal(0, vol / 6, n))
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, vol / 3, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, vol / 3, n)))
    return pd.DataFrame({"acilis": o, "yuksek": h, "dusuk": l, "kapanis": c, "hacim": 1000.0, "quote_hacim": 1e5, "islem_sayisi": 10}, index=idx)


def tanim(kimlik, semboller, nesne=None, etiket="iyi_gorundu", tf="1d", kol="tek_evren", pay="1"):
    nesne = nesne or OrtalamaTrend()
    return psg.StratejiTanim(kimlik, "swing", kol, nesne.ad, "", tf, "varsayilan", nesne, kimlik, Decimal(pay), tuple(semboller), etiket=etiket)


def set_(*kimlikler, s=0.5):
    return {"surum": 1, "ad": v2.SET_ADI, "s": s, "baslangic_sermaye": 10000,
            "stratejiler": [{"strateji": k, "tf": "1d", "evren": "genel", "tur": "tek", "etiket": "iyi_gorundu"} for k in kimlikler]}


SEM = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def veri(semboller=SEM, n=260):
    return {(s, "1d"): sentetik(n, seed=11 + i, p0=50 + 40 * i, vol=0.025) for i, s in enumerate(semboller)}


def kos(tanimlar, mumlar, fund=None, ayar_set=None, bas_i=120, kapat=True, onbellek=None, tradfi=True):
    ix = next(iter(mumlar.values())).index
    p = v2.kasalar_kur(tanimlar, mumlar, fund or {}, ayar_set or set_(*[t.kimlik for t in tanimlar]), pencere={"1d": 300},
                       onbellek=onbellek, tradfi_varsayim=tradfi)
    return v2.kos(p, ix[bas_i], ix[-1] + pd.Timedelta(days=1), kapat=kapat)


def islem_ozeti(h):
    return [(x["kol"], str(x["giris_zamani"]), str(x["cikis_zamani"]), x["miktar"], x["net_pnl"], x["cikis_nedeni"]) for x in h.motor.islemler]


# ---------------------------------------------------------------------------- set tanımı
def test_set_10_strateji_etiketler_holdout_dosyalariyla_tutarli():
    s = v2.set_yukle()
    assert len(s["stratejiler"]) == 10 and s["s"] == 0.5 and s["baslangic_sermaye"] == 10000
    et = {k["strateji"]: k["etiket"] for k in s["stratejiler"]}
    dogrulandi = {a for a, e in et.items() if e == "dogrulandi"}
    girdi = json.loads((KOK / "sonuclar/evren/v2/holdout/paper_girdisi.json").read_text())
    assert dogrulandi == {x["strateji"] for x in girdi["set"]} and len(dogrulandi) == 2
    assert girdi["s"] == s["s"]
    kesif = pd.read_csv(KOK / "sonuclar/evren/v2/holdout_kesif/holdout_kesif.csv").set_index("strateji")
    for a, e in et.items():
        if e == "iyi_gorundu":
            assert a in kesif.index and kesif.loc[a, "net"] > 0 and kesif.loc[a, "k2_p"] <= 0.05, a
    assert sum(1 for e in et.values() if e == "iyi_gorundu") == 8


def test_set_havuzla_uyusmazlik_acik_hata(tmp_path):
    s = v2.set_yukle()
    s2 = copy.deepcopy(s)
    s2["stratejiler"][0]["tf"] = "4h"
    yol = tmp_path / "set.json"
    yol.write_text(json.dumps(s2))
    with pytest.raises(v2.PaperV2Hatasi, match="havuzla"):
        v2.set_yukle(yol)
    s3 = copy.deepcopy(s)
    s3["stratejiler"][0]["etiket"] = "harika"
    yol.write_text(json.dumps(s3))
    with pytest.raises(v2.PaperV2Hatasi, match="etiket"):
        v2.set_yukle(yol)
    s4 = copy.deepcopy(s)
    s4["stratejiler"].append(dict(s4["stratejiler"][0]))
    yol.write_text(json.dumps(s4))
    with pytest.raises(v2.PaperV2Hatasi, match="tekrarlı"):
        v2.set_yukle(yol)


def test_tanimlar_v2_varsayilan_ayar_ve_evren():
    from motor.arastirma.v2 import sabit
    tans = {t.kimlik: t for t in v2.tanimlari_yukle()}
    assert len(tans) == 10
    assert all(t.ayar == "varsayilan" for t in tans.values())
    assert tans["dis__ewo-ema-ofset"].tf == "15m" and tans["dis__e0v1en"].tf == "15m"
    assert tuple(tans["dis__ewo-ema-ofset"].evren) == sabit.evren_listesi("kripto") and len(tans["dis__ewo-ema-ofset"].evren) == 13
    assert tuple(tans["dis__lube"].evren) == sabit.evren_listesi("genel") and len(tans["dis__lube"].evren) == 35
    pf = tans["pf__sabit_sepet"]
    assert pf.kol == "portfoy" and pf.grup_payi == Decimal("0.5") and set(pf.evren) == {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
    assert tans["dis__hma-atr-rider"].nesne.cikis_ayarlari.atr_iz_suren_k == 2.0       # desteklenen gelişmiş çıkış alanı
    assert {t.etiket for t in tans.values()} == {"dogrulandi", "iyi_gorundu"}


def test_hesap_ayarlari_risk_yarim_yuzde_ve_sembol_maliyeti():
    from motor.risk.limitler import SERT_LIMITLER
    tans = {t.kimlik: t for t in v2.tanimlari_yukle()}
    s = v2.set_yukle()
    ay = v2.hesap_ayarlari(tans["dis__lube"], s)
    assert ay.risk_yuzde == pytest.approx(0.5) and ay.risk_yuzde < SERT_LIMITLER.islem_basi_max_risk_yuzde
    assert ay.baslangic_sermaye == 10000 and ay.limit_modu == "uygula"
    assert set(ay.maliyet_sembol) == set(tans["dis__lube"].evren)
    assert ay.maliyet_sembol["DK_NATGAS"][2] > ay.maliyet_sembol["BTCUSDT"][2]             # sembol bazlı kayma (v2 tablosu)
    # hesap motoru sert limiti aşamaz
    from motor.canli.paper_motor import PaperMotor
    m = PaperMotor(dataclasses.replace(ay, risk_yuzde=5.0, kaldirac=50.0), {})
    assert m.risk_oran == Decimal("0.01") and m.kal == SERT_LIMITLER.max_kaldirac


def test_fail_closed_desteklenmeyen_cikis_alani_adiyla_hata():
    kotu = OrtalamaTrend(cikis_ayarlari=CikisAyarlari(zaman_cikisi_mum=1000, stop_basamaklari=((1.0, 0.0),)))
    t = tanim("kotu|strateji", SEM, kotu)
    with pytest.raises(PaperDesteklemiyorHatasi, match=r"kotu\|strateji: stop_basamaklari"):
        v2.fail_closed_kontrol([t])
    # servis yolu: set yükleme sırasında da durur (v2 varsayılan ayarı desteklenmeyen alan taşıyorsa hiçbir hesap kurulmaz)
    import motor.arastirma.v2.ham as hm
    orijinal = hm.varsayilan_strateji
    try:
        hm.varsayilan_strateji = lambda ad: ("varsayilan", kotu)
        with pytest.raises(PaperDesteklemiyorHatasi, match="BAŞLAMAZ"):
            v2.tanimlari_yukle()
    finally:
        hm.varsayilan_strateji = orijinal
    # motor da ayrıca reddeder (ikinci savunma)
    with pytest.raises(PaperDesteklemiyorHatasi):
        v2.kasalar_kur([t], veri(), {}, set_("kotu|strateji"))


# ---------------------------------------------------------------------------- hesaplar
def test_tek_evren_tek_sembol_tek_grafik_ile_ayni_islemler():
    """Yeni çok sembollü yol, tek sembolde eski tek_grafik yoluyla birebir aynı işlemleri üretir."""
    mum = veri(["BTCUSDT"])
    ix = mum[("BTCUSDT", "1d")].index
    ay = v2.hesap_ayarlari(tanim("a", ["BTCUSDT"]), set_("a"))
    kurallar = v2.kurallar_tekrar([tanim("a", ["BTCUSDT"])])
    eski = psg.StratejiTanim("a|BTCUSDT|1d", "swing", "tek_grafik", "test__ortalama_trend", "BTCUSDT", "1d", "varsayilan", OrtalamaTrend(),
                             "g", Decimal(1))
    pe = pp.tekrar_calistir([eski], mum, {}, kurallar, ix[120], ix[-1] + pd.Timedelta(days=1), ay, {"1d": 300})
    yeni = kos([tanim("a", ["BTCUSDT"])], mum)
    h = yeni.hesaplar["a"]
    assert len(pe.motor.islemler) >= 3
    assert [(str(x["giris_zamani"]), str(x["cikis_zamani"]), x["miktar"], x["net_pnl"]) for x in pe.motor.islemler] == \
           [(str(x["giris_zamani"]), str(x["cikis_zamani"]), x["miktar"], x["net_pnl"]) for x in h.motor.islemler]


def test_hesaplar_birbirinden_bagimsiz_ve_toplam_toplamdir():
    mum = veri()
    a = tanim("a", ["BTCUSDT", "ETHUSDT"], OrtalamaTrend(n=10))
    b = tanim("b", ["ETHUSDT", "SOLUSDT"], OrtalamaTrend(n=20))
    birlikte = kos([a, b], mum)
    yalniz_a = kos([a], mum).hesaplar["a"]
    yalniz_b = kos([b], mum).hesaplar["b"]
    assert islem_ozeti(birlikte.hesaplar["a"]) == islem_ozeti(yalniz_a) and len(islem_ozeti(yalniz_a)) >= 3
    assert islem_ozeti(birlikte.hesaplar["b"]) == islem_ozeti(yalniz_b)
    assert birlikte.hesaplar["a"].motor is not birlikte.hesaplar["b"].motor
    assert birlikte.motor.ozsermaye() == birlikte.hesaplar["a"].motor.ozsermaye() + birlikte.hesaplar["b"].motor.ozsermaye()
    assert birlikte.baslangic_hesap == 20000
    assert len(birlikte.motor.islemler) == len(yalniz_a.motor.islemler) + len(yalniz_b.motor.islemler)
    for h in birlikte.hesaplar.values():                                   # her kasa kendi başlangıç sermayesinden: 10.000
        assert h.ayarlar.baslangic_sermaye == 10000


def test_sert_limitler_hesap_basina_uygulanir():
    """Çok dar stoplu ve çok sembollü iki hesap: HER hesapta açık stop riski <= %5, brüt <= 3x, işlem başı risk <= %0.5 (maliyet dahil)."""
    from motor.arastirma.v2 import sabit
    sem = list(sabit.evren_listesi("kripto"))                                        # 13 sembol: 13 x %0.5 = %6.5 > %5 tavan -> kırpılmalı
    mum = {(s, "1d"): sentetik(30, seed=i, p0=100.0, vol=0.0005) for i, s in enumerate(sem)}
    ix = mum[(sem[0], "1d")].index
    tans = [tanim(f"h{j}", sem, HepsiYon(stop_yuzde=0.05)) for j in range(2)]
    ayar = set_("h0", "h1")
    kaynak = TekrarKaynagi(mum, {}, {"1d": 300})
    kur = {s: SembolKurallari(0.01, 0.001, 0.001, 5.0) for s in sem}
    p = v2.PaperKasalar(tans, kaynak, kur, ayar)
    p.baslat(ix[3])
    p.adim(ix[10], son_satir_bayragi=False)
    for h in p.hesaplar.values():
        m = h.motor
        assert len(m.acik) > 0
        E = m.ozsermaye()
        assert m.acik_stop_riski() <= 0.05 + 1e-9
        assert m.brut_kaldirac() <= 3.0 + 1e-9
        for pos in m.acik.values():
            assert pos.risk_tutar / E <= Decimal("0.0050001")                    # s x %1
    assert p.hesaplar["h0"].motor.kill is False


def test_kill_bir_hesapta_digerini_durdurmaz():
    mum = veri()
    a, b = tanim("a", ["BTCUSDT"]), tanim("b", ["ETHUSDT"])
    p = v2.kasalar_kur([a, b], mum, {}, set_("a", "b"), pencere={"1d": 300})
    p.baslat(mum[("BTCUSDT", "1d")].index[120])
    p.hesaplar["a"].motor.kill = True                                          # a hesabı durdu (kalıcı)
    p.adim(mum[("BTCUSDT", "1d")].index[-1] + pd.Timedelta(days=1), son_satir_bayragi=True)
    assert len(p.hesaplar["a"].motor.islemler) == 0 and len(p.hesaplar["b"].motor.islemler) >= 2
    p.motor.yenile()
    assert p.motor.kill is True                                                # toplam görünüm kritik durumu gizlemez


def test_karar_onbellegi_ayni_sonucu_verir(tmp_path):
    mum = veri()
    tans = [tanim("a", SEM, OrtalamaTrend(n=7))]
    ix = mum[("BTCUSDT", "1d")].index
    bas, bit = ix[120], ix[-1] + pd.Timedelta(days=1)
    onb = v2.karar_onbellegi_olustur(tans, mum, {}, bas, bit, tmp_path, surec=1, pencere={"1d": 300}, geri_bildirim=lambda *a: None)
    assert len(onb) > 300
    # yeniden çağrı dosyadan okur (aynı sonuç)
    onb2 = v2.karar_onbellegi_olustur(tans, mum, {}, bas, bit, tmp_path, surec=1, pencere={"1d": 300}, geri_bildirim=lambda *a: None)
    assert onb2.keys() == onb.keys()
    onbsiz = kos(tans, mum)
    onbli = kos(tans, mum, onbellek=onb)
    assert islem_ozeti(onbsiz.hesaplar["a"]) == islem_ozeti(onbli.hesaplar["a"]) and len(onbsiz.hesaplar["a"].motor.islemler) >= 5


def test_baslangicta_her_sembol_kendi_son_barinin_kararini_alir():
    """Ortak eksenin son satırında mumu olmayan sembol (hafta sonu satırında hisse gibi) bekleyen emrini kaybetmez."""
    mum = veri(["BTCUSDT", "DK_AAPL"])
    ix = mum[("BTCUSDT", "1d")].index
    mum[("DK_AAPL", "1d")] = mum[("DK_AAPL", "1d")].drop(ix[119])                  # son satırda AAPL mumu yok
    t = tanim("a", ["BTCUSDT", "DK_AAPL"], HepsiYon(stop_yuzde=2.0))
    p = v2.kasalar_kur([t], mum, {}, set_("a"), pencere={"1d": 300}, tradfi_varsayim=False)
    p.baslat(ix[120])                                                              # son kapanmış satır = ix[119]
    h = p.hesaplar["a"]
    emirli = {k.sembol for k in h.motor.tum_kollar if k.giris_emri is not None}
    assert emirli == {"BTCUSDT", "DK_AAPL"}


# ---------------------------------------------------------------------------- kalıcılık
def test_durum_kaydet_yukle_devam_ayni_sonuc(tmp_path):
    mum = veri()
    tans = [tanim("a", SEM, OrtalamaTrend(n=10)), tanim("b", SEM[:2], OrtalamaTrend(n=20))]
    ix = mum[("BTCUSDT", "1d")].index
    ayar = set_("a", "b")
    tam = kos(tans, mum, ayar_set=ayar, kapat=False)
    p1 = v2.kasalar_kur(tans, mum, {}, ayar, pencere={"1d": 300})
    p1.baslat(ix[120])
    p1.adim(ix[200])
    yol = tmp_path / "paper_state.json"
    p1.kaydet(yol)
    p2 = v2.kasalar_kur(tans, mum, {}, ayar, pencere={"1d": 300})
    assert p2.yukle(yol) is True
    p2.adim(ix[-1] + pd.Timedelta(days=1))
    for k in ("a", "b"):
        assert islem_ozeti(p2.hesaplar[k]) == islem_ozeti(tam.hesaplar[k])
        assert p2.hesaplar[k].motor.ozsermaye() == tam.hesaplar[k].motor.ozsermaye()


def test_eski_7li_set_durumu_acik_hatayla_reddedilir_ve_silinmez(tmp_path):
    mum = veri()
    p = v2.kasalar_kur([tanim("a", SEM)], mum, {}, set_("a"), pencere={"1d": 300})
    yol = tmp_path / "paper_state.json"
    yol.write_text(json.dumps({"surum": 1, "baslangic_sermaye": 10000.0, "ayarlar": {}, "pf_sutunlar": {}, "motor": {}}))
    with pytest.raises(v2.PaperV2Hatasi, match="eski 7'li set"):
        p.yukle(yol)
    assert yol.exists()                                                        # eski durum asla silinmez
    # farklı set imzası
    p.baslat(mum[("BTCUSDT", "1d")].index[120])
    p.kaydet(yol)
    d = json.loads(yol.read_text())
    d["set_imza"] = "baska"
    yol.write_text(json.dumps(d))
    with pytest.raises(v2.PaperV2Hatasi, match="set imzası"):
        p.yukle(yol)


# ---------------------------------------------------------------------------- durum dosyaları ve pano
def test_durum_dosyalari_etiket_hesap_ve_toplam(tmp_path):
    mum = veri()
    a = tanim("a", SEM, OrtalamaTrend(n=10), etiket="dogrulandi")
    b = tanim("b", SEM[:2], OrtalamaTrend(n=20), etiket="iyi_gorundu")
    p = kos([a, b], mum, kapat=False)
    simdi = mum[("BTCUSDT", "1d")].index[-1] + pd.Timedelta(days=1)
    v2.durum_yaz(p, p.kaynak, tmp_path, simdi, kaynak_adi="backtest", veri_dizini=tmp_path)
    st = json.loads((tmp_path / "stratejiler.json").read_text())
    by = {x["kimlik"]: x for x in st["stratejiler"]}
    assert by["a"]["etiket"] == "dogrulandi" and by["b"]["etiket"] == "iyi_gorundu"
    assert by["a"]["hesap"]["baslangic"] == "10000.00" and by["a"]["hesap"]["risk_yuzde"] == pytest.approx(0.5)
    oz = json.loads((tmp_path / "ozet.json").read_text())
    ha = json.loads((tmp_path / "hesaplar" / "a" / "ozet.json").read_text())
    hb = json.loads((tmp_path / "hesaplar" / "b" / "ozet.json").read_text())
    assert Decimal(oz["ozsermaye"]) == Decimal(ha["ozsermaye"]) + Decimal(hb["ozsermaye"])
    assert oz["baslangic_ozsermaye"] == "20000.00" and ha["baslangic_ozsermaye"] == "10000.00"
    assert Decimal(by["a"]["hesap"]["ozsermaye"]) == Decimal(ha["ozsermaye"])
    assert any("KANIT DEĞİL" in n for n in oz["notlar"])
    # pano: etiket çipi + kasa satırı
    from motor.canli import pano
    pano.uret(tmp_path, tmp_path / "pano.html")
    sayfa = (tmp_path / "pano.html").read_text(encoding="utf-8")
    assert "doğrulandı" in sayfa and "iyi göründü" in sayfa and "Kasa (kendi sanal hesabı)" in sayfa


def test_pano_etiket_cipi_alan_yoksa_bos():
    from motor.canli import pano
    assert pano._etiket_cipi(None) == "" and pano._etiket_cipi("") == ""
    assert "doğrulandı" in pano._etiket_cipi("dogrulandi") and "iyi göründü" in pano._etiket_cipi("iyi_gorundu")


# ---------------------------------------------------------------------------- TradFi (tekrar varsayımı, takvim, eşleme)
def test_tradfi_funding_varsayimi_long_oder_short_gelir_yazilmaz():
    mum = veri(["DK_AAPL"], n=200)
    ix = mum[("DK_AAPL", "1d")].index
    tl = tanim("long", ["DK_AAPL"], HepsiYon(yon=1, stop_yuzde=50.0))
    ts = tanim("short", ["DK_AAPL"], HepsiYon(yon=-1, stop_yuzde=50.0))
    p = kos([tl, ts], mum, bas_i=50)
    fl = sum(x["funding"] for x in p.hesaplar["long"].motor.islemler)
    fs = sum(x["funding"] for x in p.hesaplar["short"].motor.islemler)
    assert fl > 0 and fs == 0
    p2 = kos([tl, ts], mum, bas_i=50, tradfi=False)                              # varsayım kapalı: tekrarda TradFi funding yok
    assert sum(x["funding"] for x in p2.hesaplar["long"].motor.islemler) == 0
    # kaynak: stratejiye verilen funding_df DEĞİŞMEZ (varsayım yalnız motora gider)
    k = v2.TekrarKaynagiV2(mum, {})
    assert k.funding_df("DK_AAPL") is None and len(k.funding_dizisi("DK_AAPL")[0]) > 0
    assert set(pd.Series(k.funding_dizisi("DK_AAPL")[0]).diff().dropna()) == {pd.Timedelta(hours=8)}


def test_yeni_tradfi_semboller_takvim_ve_esleme():
    for s in ("DK_AVGO", "DK_LLY", "DK_WMT", "DK_JPM", "DK_V", "DK_MU", "DK_AMD", "DK_XOM", "DK_JNJ", "DK_MA"):
        assert tk.tur(s) == "hisse", s
    assert tk.tur("DK_XAG") == "emtia" and tk.tur("DK_NATGAS") == "emtia" and tk.tur("BTCUSDT") == "kripto"
    assert pv.binance_sembol("DK_AVGO") == "AVGOUSDT" and pv.binance_sembol("DK_XAG") == "XAGUSDT"
    assert "DK_JNJ" not in pv.ESLEME and "DK_MA" not in pv.ESLEME            # Binance TradFi karşılığı envanterde yok -> veri yok


def test_canli_eslemesi_olmayan_sembol_evrenden_duser_strateji_calisir():
    t = tanim("a", ["BTCUSDT", "DK_JNJ", "DK_AAPL"])
    esl = {"BTCUSDT": ("BTCUSDT", None), "DK_AAPL": ("AAPLUSDT", None), "DK_JNJ": (None, "DK_JNJ Binance USDⓈ-M exchangeInfo'da yok")}
    pp._tanimlara_veri_yok_isle([t], esl)
    assert t.veri_yok == "" and t.evren == ("BTCUSDT", "DK_AAPL") and "DK_JNJ" in t.disarida
    t2 = tanim("b", ["DK_JNJ", "DK_MA"])
    pp._tanimlara_veri_yok_isle([t2], {"DK_JNJ": (None, "yok"), "DK_MA": (None, "yok")})
    assert t2.veri_yok                                                           # hiç sembol kalmadı: strateji 'veri yok'
    pf = tanim("c", ["BTCUSDT", "DK_JNJ"], kol="portfoy")
    pp._tanimlara_veri_yok_isle([pf], {"BTCUSDT": ("BTCUSDT", None), "DK_JNJ": (None, "yok")})
    assert pf.veri_yok                                                           # portföyde evren bütünlüğü: tamamı 'veri yok'


def test_varsayilan_set_v2_ve_eski_yol_secenegi():
    import inspect
    assert inspect.signature(pp.canli_calistir).parameters["set_modu"].default == "v2"
    src = inspect.getsource(pp.main)
    assert 'default="v2"' in src and '"eski"' in src


# ---------------------------------------------------------------------------- canlı servis (sahte Binance; ağ yok)
def test_canli_calistir_v2_sahte_binance_evrenden_dusme_durum_ve_eski_durum_reddi(tmp_path, monkeypatch):
    from motor.canli import durum as d
    from testler.test_paper_canli import SahteFapi
    monkeypatch.setattr(pv, "FapiIstemci", SahteFapi)
    monkeypatch.setitem(pp.PENCERE, "1d", 120)
    a = tanim("a", ["BTCUSDT", "DK_JNJ", "ETHUSDT"], OrtalamaTrend(n=10), etiket="dogrulandi")
    b = tanim("b", ["SOLUSDT"], OrtalamaTrend(n=15), etiket="iyi_gorundu")
    ayar = set_("a", "b")
    monkeypatch.setattr(v2, "set_yukle", lambda *x, **k: ayar)
    monkeypatch.setattr(v2, "tanimlari_yukle", lambda *x, **k: [a, b])
    assert pp.canli_calistir(tmp_path, None, False, tek_sefer=True) == 0                       # varsayılan = v2
    veri, sorun = d.oku_hepsi(tmp_path)
    assert not sorun
    s = {x["kimlik"]: x for x in veri["stratejiler"]["stratejiler"]}
    assert s["a"]["etiket"] == "dogrulandi" and s["b"]["etiket"] == "iyi_gorundu" and s["a"]["durum"] == "calisiyor"
    assert a.evren == ("BTCUSDT", "ETHUSDT") and "DK_JNJ" in a.disarida                          # eşlemesi olmayan sembol evrenden düştü
    assert any("DK_JNJ" in u for u in veri["saglik"]["uyarilar"]) or any("DK_JNJ" in n for n in veri["ozet"]["notlar"])
    assert (tmp_path / "paper_state.json").exists() and (tmp_path / "hesaplar" / "a" / "ozet.json").exists()
    st = json.loads((tmp_path / "paper_state.json").read_text())
    assert st["set"] == "paper_v2" and set(st["hesaplar"]) == {"a", "b"}
    # yeniden başlatma durumu yükler
    assert pp.canli_calistir(tmp_path, None, False, tek_sefer=True) == 0
    assert any(o["tur"] == "yeniden_baslatma" for o in d.ek_oku(tmp_path, "olaylar"))
    # eski 7'li set durumu: v2 başlamaz (açık hata), dosya silinmez
    eski = tmp_path / "eski"
    eski.mkdir()
    (eski / "paper_state.json").write_text(json.dumps({"surum": 1, "baslangic_sermaye": 10000.0, "ayarlar": {}, "pf_sutunlar": {}, "motor": {}}))
    with pytest.raises(v2.PaperV2Hatasi, match="eski 7'li set"):
        pp.canli_calistir(eski, None, False, tek_sefer=True)
    assert (eski / "paper_state.json").exists()


# ---------------------------------------------------------------------------- kabul testi aracı (saf işlevler)
def test_uyum_araci_eslestirme_ve_referans():
    import importlib.util
    spec = importlib.util.spec_from_file_location("paper_v2_uyum", KOK / "araclar" / "paper_v2_uyum.py")
    u = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(u)
    g = pd.Timestamp("2026-01-05", tz="UTC")
    oos = pd.DataFrame({"sembol": ["A", "B", "C"], "giris_zamani": [g, g, g + pd.Timedelta(days=1)], "r": [1.0, -0.5, 2.0],
                        "pnl_h": [0.01, -0.005, 0.02], "kabul": [True, True, False]})
    paper = [{"sembol": "A", "giris_zamani": g, "r": 1.01, "net_pnl": 100.0}, {"sembol": "D", "giris_zamani": g, "r": 0.3, "net_pnl": 30.0}]
    e = u.eslestir(oos, paper)
    assert (e["holdout_kabul"], e["paper"], e["ortak"], e["sadece_holdout"], e["sadece_paper"]) == (2, 2, 1, 1, 1)
    assert e["ortak_medyan_abs_dR"] == pytest.approx(0.01) and e["sadece_paper_pnl"] == 30.0
    r = u.referans("dis__gauss-stoch-eth")
    assert r["kaynak"] == "holdout.csv" and r["net"] == pytest.approx(0.1037, abs=1e-3)
    assert u.referans("dis__lube")["kaynak"] == "holdout_kesif.csv"


def test_veri_yok_strateji_bos_kasada_bekler_digerleri_calisir(tmp_path):
    mum = veri(["BTCUSDT"])
    a = tanim("a", ["BTCUSDT"])
    b = tanim("b", ["DK_JNJ", "DK_MA"])
    pp._tanimlara_veri_yok_isle([b], {"DK_JNJ": (None, "yok"), "DK_MA": (None, "yok")})
    assert b.veri_yok
    p = v2.PaperKasalar([a, b], TekrarKaynagi(mum, {}, {"1d": 300}), {"BTCUSDT": SembolKurallari(0.1, 0.001, 0.001, 5.0)}, set_("a", "b"))
    ix = mum[("BTCUSDT", "1d")].index
    p.baslat(ix[120])
    p.adim(ix[-1] + pd.Timedelta(days=1), son_satir_bayragi=True)
    assert len(p.hesaplar["a"].motor.islemler) >= 2 and not p.hesaplar["b"].motor.islemler
    v2.durum_yaz(p, p.kaynak, tmp_path, ix[-1] + pd.Timedelta(days=1), kaynak_adi="backtest", veri_dizini=tmp_path)
    st = {x["kimlik"]: x for x in json.loads((tmp_path / "stratejiler.json").read_text())["stratejiler"]}
    assert st["b"]["durum"].startswith("veri yok") and st["a"]["durum"] == "calisiyor"
