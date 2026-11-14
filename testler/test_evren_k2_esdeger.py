"""K2 rastgele giriş simülatörü (evren_k2._genis) == gerçek motor (backtest): aynı giriş mumunda tek işlem, aynı R ve çıkış mumu.

Sentetik rastgele yürüyüş; her çıkış modülü ayrı + kombinasyonlar + `pozisyon_cikisi` kancası. Motor ayarı: kayma/komisyon gerçekçi,
tick/step/min_qty ihmal edilebilir (simülatör fiyat/miktar yuvarlamasız çalışır), funding yok."""
import math
import time

import numpy as np
import pandas as pd
import pytest

from motor.arastirma import evren_k2
from motor.backtest.motor import MotorAyarlari, SembolKurallari, backtest
from motor.strateji import gostergeler as gst
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.temel import Strateji

KAYMA, SKAYMA, TAKER = 2e-4, 5e-4, 5e-4
HM, MULT = 40, 1.5


def seri(n=420, seed=11):
    rng = np.random.default_rng(seed)
    kap = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, n)))
    ac = np.r_[kap[0], kap[:-1]] * (1 + rng.normal(0, 0.003, n))          # küçük gap'ler
    yu = np.maximum(ac, kap) * (1 + rng.uniform(0, 0.006, n))
    du = np.minimum(ac, kap) * (1 - rng.uniform(0, 0.006, n))
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": yu, "dusuk": du, "kapanis": kap, "hacim": 1.0}, index=idx)


class Deneme(Strateji):
    ad = "deneme"

    def __init__(self, sig, ca, kanca=None):
        super().__init__(cikis_ayarlari=ca)
        self._s = sig
        if kanca is not None:
            self.pozisyon_cikisi = kanca

    def cikis_var_mi(self):
        return True

    def sinyaller(self, mumlar):
        return self._s


def cikis_sinyalleri(n, seed=5, oran=0.06):
    rng = np.random.default_rng(seed)
    return rng.random(n) < oran


def kos(df, ca, yon, j, kanca=None, sinyalli=True):
    n = len(df)
    o, h, l, c = (df[k].to_numpy(float) for k in ("acilis", "yuksek", "dusuk", "kapanis"))
    atr = gst.atr(df["yuksek"], df["dusuk"], df["kapanis"], 14).to_numpy(float)
    ex = cikis_sinyalleri(n) if sinyalli else np.zeros(n, dtype=bool)
    sig = pd.DataFrame({"yon": 0, "stop": np.nan, "hedef": np.nan, "cikis": ex}, index=df.index)
    # motor: sinyal j-1 kapanışında, giriş j açılışında; stop simülatörle aynı formül
    sig.iloc[j - 1, sig.columns.get_loc("yon")] = yon
    sig.iloc[j - 1, sig.columns.get_loc("stop")] = c[j - 1] - yon * MULT * atr[j - 1]
    ca2 = CikisAyarlari(**{**ca.__dict__, "zaman_cikisi_mum": HM})
    ay = MotorAyarlari(baslangic_sermaye=1e9, komisyon_taker_yuzde=TAKER * 100, kayma_bps=KAYMA * 1e4,
                       stop_kayma_bps=SKAYMA * 1e4, limit_modu="olc",
                       kurallar=SembolKurallari(tick_size=1e-9, step_size=1e-4, min_qty=1e-3, min_notional=0.0))
    r = backtest(df, Deneme(sig, ca2, kanca), ay)
    # simülatör (ex dizisi sinyalsiz çıkış stratejisinden gelir: giriş sinyali olmayan aynı çıkış sütunları)
    sig0 = sig.copy()
    sig0["yon"] = 0
    sig0["stop"] = np.nan
    ci = evren_k2.cikis_bilgisi(Deneme(sig0, ca2, kanca), df)
    b = {}
    rs = evren_k2.tek_islem_r(o, h, l, c, atr, j, yon, HM, MULT, KAYMA, SKAYMA, TAKER,
                              ex=ci["ex_long"] if yon == 1 else ci["ex_short"], hedef_r=ci["hedef_r"], iz_k=ci["iz_k"],
                              iz_atr=(gst.atr(df["yuksek"], df["dusuk"], df["kapanis"], ca2.atr_periyot).to_numpy(float)
                                      if ci["iz_k"] else None), be_r=ci["be_r"], ek=ci["ek"], bilgi=b)
    return r, rs, b, ci


GIRISLER = [(j, y) for j in (30, 55, 80, 110, 140, 170, 200, 240, 280, 320, 350, 365) for y in (1, -1)]

MODULLER = {
    "kismi_R": (dict(kismi=((1.0, 0.25), (2.0, 0.25)), sabit_r_hedefi=4.0), {"hedef", "stop", "stop_gap", "sinyal", "zaman"}),
    "kismi_yuzde": (dict(kismi_yuzde=((0.8, 0.3), (1.6, 0.2)), sabit_r_hedefi=5.0), None),
    "kismi_tam": (dict(kismi=((1.0, 0.5), (1.5, 0.5)), sabit_r_hedefi=6.0), None),
    "stop_basamaklari": (dict(stop_basamaklari=((1.0, 0.0), (2.0, 1.0))), None),
    "azalan_roi": (dict(azalan_roi=((0, 3.0), (10, 1.0), (20, 0.3))), "roi"),
    "geri_cekilme": (dict(geri_cekilme_yuzde=1.5, geri_cekilme_min_kar_yuzde=1.0), "geri_cekilme"),
    "kar_rsi": (dict(kar_rsi_esikleri=((0.5, 60.0), (2.0, 55.0))), "kar_rsi"),
    "yalniz_karda": (dict(yalniz_karda_cikis=True, yalniz_karda_min_kar_yuzde=0.3), None),
    "min_tutma": (dict(min_tutma_mum=6), None),
    "yasa_zarar": (dict(yasa_bagli_zarar_cikisi=((8, 1.0),)), "yasa_zarar"),
    "chandelier": (dict(kapanis_chandelier_k=1.5), "kapanis_chandelier"),
    "elder": (dict(elder_guvenli_bolge_k=1.5), None),
    "agresif_iz": (dict(atr_iz_suren_k=3.0, agresif_iz_esigi=0.5, agresif_iz_atr_k=1.0, sabit_r_hedefi=3.0), None),
    "iz_basabas_hedef": (dict(atr_iz_suren_k=2.5, basabas_r_esigi=1.0, sabit_r_hedefi=3.0), None),
    "kombo_1": (dict(kismi=((1.0, 0.25),), stop_basamaklari=((1.5, 0.5),), azalan_roi=((0, 4.0), (15, 0.5)),
                     geri_cekilme_yuzde=2.0, yasa_bagli_zarar_cikisi=((12, 1.5),), sabit_r_hedefi=3.0), None),
    "kombo_2": (dict(kar_rsi_esikleri=((0.5, 65.0),), kapanis_chandelier_k=2.0, elder_guvenli_bolge_k=2.0,
                     yalniz_karda_cikis=True, min_tutma_mum=3, kismi_yuzde=((1.0, 0.4),), atr_iz_suren_k=3.0), None),
}


def _karsilastir(df, ca, kanca=None, beklenen_neden=None, sinyalli=True):
    nedenler, karsilastirilan = set(), 0
    for j, y in GIRISLER:
        r, rs, b, _ = kos(df, ca, y, j, kanca, sinyalli)
        if rs is None or len(r.islemler) == 0:
            assert rs is None and len(r.islemler) == 0, (j, y, rs, len(r.islemler))
            continue
        t = r.islemler.iloc[0]
        assert rs == pytest.approx(t.r, rel=1e-6, abs=1e-6), (j, y, t.cikis_nedeni)
        if b:                                           # eski (ek=None) yol çıkış mumunu bildirmez; yalnız R karşılaştırılır
            assert b["cikis_idx"] == int(df.index.get_loc(t.cikis_zamani)), (j, y, t.cikis_nedeni, b)
        nedenler.add(t.cikis_nedeni)
        karsilastirilan += 1
    assert karsilastirilan >= len(GIRISLER) // 2
    if isinstance(beklenen_neden, str):
        assert beklenen_neden in nedenler, nedenler       # modül gerçekten tetiklendi
    return nedenler


@pytest.mark.parametrize("ad", list(MODULLER))
def test_modul_motorla_esdeger(ad):
    kw, beklenen = MODULLER[ad]
    _karsilastir(seri(), CikisAyarlari(**kw), beklenen_neden=beklenen)


def test_kismi_ve_kismi_yuzde_gercekten_kismi_alir():
    df = seri()
    toplam = 0
    for ad in ("kismi_R", "kismi_yuzde"):
        for j, y in GIRISLER:
            r, rs, b, _ = kos(df, CikisAyarlari(**MODULLER[ad][0]), y, j)
            if len(r.islemler):
                toplam += int(r.islemler.iloc[0].kismi_sayisi)
    assert toplam > 0


def test_kanca_motorla_esdeger():
    df = seri()

    def kanca(d):
        return (d.tutulan_mum >= 4 and d.kar_yuzde < -0.4) or d.kar_yuzde > 2.5 or (d.en_yuksek - d.en_dusuk) / d.giris_fiyati > 0.07
    nedenler = _karsilastir(df, CikisAyarlari(sabit_r_hedefi=4.0), kanca=kanca)
    assert "kanca" in nedenler


def test_kanca_durum_alanlari_motorla_ayni():
    df = seri()
    motor_g, sim_g = [], []

    def kanca_m(d):
        motor_g.append(d)
        return False
    for kancasi, hedef in ((kanca_m, motor_g),):
        r, rs, b, _ = kos(df, CikisAyarlari(), 1, 60, kancasi)
    # simülatör için aynı kanca
    def kanca_s(d):
        sim_g.append(d)
        return False
    kos(df, CikisAyarlari(), 1, 60, kanca_s)
    # kos her çağrıda motoru da koşar: sim_g = motor çağrıları + sim çağrıları; ilk yarı motor, ikinci yarı simülatör
    assert len(sim_g) % 2 == 0 and len(sim_g) > 0
    yarim = len(sim_g) // 2
    for a, c_ in zip(sim_g[:yarim], sim_g[yarim:]):
        assert (a.yon, a.giris_mum_indeksi, a.mum_indeksi, a.tutulan_mum) == (c_.yon, c_.giris_mum_indeksi, c_.mum_indeksi, c_.tutulan_mum)
        for ad in ("en_yuksek", "en_dusuk", "kapanis", "kar_yuzde"):
            assert getattr(a, ad) == pytest.approx(getattr(c_, ad), rel=1e-7)
    assert a.giris_fiyati == pytest.approx(c_.giris_fiyati, rel=1e-7)


def test_kapali_yeni_alan_ek_yok_ve_desteklenmeyen_bos():
    sig = pd.DataFrame({"yon": 0, "stop": np.nan, "hedef": np.nan, "cikis": False}, index=seri().index)
    ci = evren_k2.cikis_bilgisi(Deneme(sig, CikisAyarlari(atr_iz_suren_k=2.0, basabas_r_esigi=1.0)), seri())
    assert ci["ek"] is None and ci["desteklenmeyen"] == []
    tum = CikisAyarlari(kismi=((1.0, 0.25),), kismi_yuzde=((1.0, 0.2),), stop_basamaklari=((1.0, 0.0),), azalan_roi=((0, 3.0),),
                        geri_cekilme_yuzde=2.0, kar_rsi_esikleri=((1.0, 60.0),), yalniz_karda_cikis=True, min_tutma_mum=3,
                        yasa_bagli_zarar_cikisi=((8, 1.0),), kapanis_chandelier_k=2.0, elder_guvenli_bolge_k=2.0,
                        agresif_iz_esigi=0.5, agresif_iz_atr_k=1.0)
    assert evren_k2.desteklenmeyen(tum) == []
    assert evren_k2.desteklenmeyen(CikisAyarlari(stop_sonrasi_bekleme_mum=3)) == ["stop_sonrasi_bekleme_mum"]


def test_yeni_yol_temel_ayarlarla_eski_yolla_ayni():
    """ek açık ama yeni modül yok (yalnız kanca=False) -> eski vektörel/mum-mum yolla aynı R (eşdeğerlik çapraz kontrolü)."""
    df = seri()
    ca = CikisAyarlari(atr_iz_suren_k=2.5, basabas_r_esigi=1.0, sabit_r_hedefi=3.0)
    for j, y in GIRISLER:
        n = len(df)
        o, h, l, c = (df[k].to_numpy(float) for k in ("acilis", "yuksek", "dusuk", "kapanis"))
        atr = gst.atr(df["yuksek"], df["dusuk"], df["kapanis"], 14).to_numpy(float)
        ex = cikis_sinyalleri(n)
        sig = pd.DataFrame({"yon": 0, "stop": np.nan, "hedef": np.nan, "cikis": ex}, index=df.index)
        ci_e = evren_k2.cikis_bilgisi(Deneme(sig, ca), df)
        ci_y = evren_k2.cikis_bilgisi(Deneme(sig, ca, kanca=lambda d: False), df)
        assert ci_e["ek"] is None and ci_y["ek"] is not None
        kw = dict(ex=ci_e["ex_long"] if y == 1 else ci_e["ex_short"], hedef_r=ci_e["hedef_r"], iz_k=ci_e["iz_k"], iz_atr=atr, be_r=ci_e["be_r"])
        a = evren_k2.tek_islem_r(o, h, l, c, atr, j, y, HM, MULT, KAYMA, SKAYMA, TAKER, **kw)
        b = evren_k2.tek_islem_r(o, h, l, c, atr, j, y, HM, MULT, KAYMA, SKAYMA, TAKER, ek=ci_y["ek"], **kw)
        assert (a is None) == (b is None)
        if a is not None:
            assert b == pytest.approx(a, rel=1e-9, abs=1e-9)


def test_performans_olcumu_bilgi(capsys):
    """Tek simülasyon maliyeti (bilgi amaçlı; üst sınır gevşek)."""
    df = seri(3000)
    n = len(df)
    o, h, l, c = (df[k].to_numpy(float) for k in ("acilis", "yuksek", "dusuk", "kapanis"))
    atr = gst.atr(df["yuksek"], df["dusuk"], df["kapanis"], 14).to_numpy(float)
    sig = pd.DataFrame({"yon": 0, "stop": np.nan, "hedef": np.nan, "cikis": cikis_sinyalleri(n)}, index=df.index)
    ca = CikisAyarlari(kismi=((1.0, 0.25),), stop_basamaklari=((1.0, 0.0),), azalan_roi=((0, 4.0), (30, 1.0)), geri_cekilme_yuzde=2.0,
                       kar_rsi_esikleri=((1.0, 70.0),), kapanis_chandelier_k=3.0, atr_iz_suren_k=3.0, sabit_r_hedefi=3.0)
    ci = evren_k2.cikis_bilgisi(Deneme(sig, ca), df)
    rng = np.random.default_rng(1)
    js = rng.integers(30, n - 100, 3000)
    t0 = time.perf_counter()
    for j in js:
        evren_k2.tek_islem_r(o, h, l, c, atr, int(j), 1, 60, MULT, KAYMA, SKAYMA, TAKER, ex=ci["ex_long"], hedef_r=ci["hedef_r"],
                             iz_k=ci["iz_k"], iz_atr=atr, be_r=ci["be_r"], ek=ci["ek"])
    dt = (time.perf_counter() - t0) / len(js)
    with capsys.disabled():
        print(f"\n[perf] tek_islem_r (genis, hm=60, tum modullar): {dt * 1e6:.0f} us/islem")
    assert dt < 5e-3
