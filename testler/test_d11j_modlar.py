"""d11j: mevcut sınıflara eklenen yeni gösterge/mod/filtre seçenekleri.

Kontroller:
  1. Her yeni mod sentetik veride çalışır, sinyal üretir (ya da en azından hatasız boş döner), stoplar doğru tarafta, ÇIKIŞ vardır.
  2. Lookahead yok: veriyi kesince geçmiş sinyaller değişmez (rekürsif göstergeler dahil).
  3. VARSAYILAN DAVRANIŞ DEĞİŞMEZ: dokunulan sınıfların (ve alt sınıflarının) varsayılan + ızgara sinyalleri, değişiklikten ÖNCE kaydedilen
     özetle (d11j_varsayilan_ozet.json) birebir aynıdır. Portföy sınıfları için aynısı (d11j_varsayilan_pf_ozet.json).
  4. Ek ayar kayıtları (stratejiler/ayarlar_d11j_ek.json: funding ve portföy ayarları) kurulur ve çalışır.
  5. Yardımcı göstergelerin (motor/strateji/_gosterge_d11j.py) sınır/nedensellik özellikleri.
Not: özet dosyaları pandas'ın hash_pandas_object çıktısına dayanır; pandas sürümü değişirse yeniden üretilmelidir.
"""
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pandas.testing as pdt
import pytest

from motor.strateji import _gosterge_d11j as j
from motor.strateji import kayit

DIZIN = Path(__file__).resolve().parent
KOK = DIZIN.parent


def _veri(seed, n, freq):
    rng = np.random.default_rng(seed)
    kap = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, n) + 0.0004 * np.sin(np.arange(n) / 50)))
    ac = np.r_[kap[0], kap[:-1]] * (1 + rng.normal(0, 0.002, n))
    yu = np.maximum(ac, kap) * (1 + rng.uniform(0, 0.006, n))
    du = np.minimum(ac, kap) * (1 - rng.uniform(0, 0.006, n))
    hac = rng.uniform(50, 500, n) * (1 + 3 * (rng.uniform(size=n) > 0.97))
    idx = pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC", name="zaman")
    df = pd.DataFrame({"acilis": ac, "yuksek": yu, "dusuk": du, "kapanis": kap, "hacim": hac}, index=idx)
    df["funding_orani"] = rng.normal(0.0001, 0.0003, n)
    return df


MUM = _veri(1, 1500, "1h")
MUM15 = _veri(2, 1500, "15min")


def _yuvarla(x):
    """İşlemciye bağlı son-bit kayan nokta farkları (SIMD/BLAS) hash'i bozmasın: 9 anlamlı ondalığa göreli yuvarlama.
    (CI'da aynı commit bir koşuda geçip diğerinde düştü — davranış değişikliği değil, makine farkı.)"""
    return x.map(lambda v: float(f"{v:.9g}") if pd.notna(v) else v)


def _ozet(sig):
    h = hashlib.sha256()
    for c in sorted(sig.columns):
        h.update(c.encode())
        h.update(pd.util.hash_pandas_object(_yuvarla(sig[c].astype(float)) if sig[c].dtype != object else sig[c].astype(str),
                                            index=False).values.tobytes())
    return h.hexdigest()[:16] + f":{int((sig['yon'] != 0).sum())}"


# ---------------------------------------------------------------- 1-2. yeni modlar: sinyal + stop tarafı + lookahead
S = "swing__"
YENI = [
    # (strateji, parametreler, en az giriş sayısı)
    (S + "macd-sinyal", dict(gosterge="trix", osc_n=14, sinyal=9, sinyal_tipi="sma"), 1),
    (S + "macd-sinyal", dict(gosterge="trix", osc_n=30, mod="sifir"), 1),
    (S + "macd-sinyal", dict(gosterge="tsi", osc_uzun=25, osc_kisa=13, sinyal=13), 1),
    (S + "macd-sinyal", dict(gosterge="kvo", osc_kisa=34, osc_uzun=55, sinyal=13), 1),
    (S + "macd-sinyal", dict(gosterge="obv", sinyal=21, sinyal_tipi="sma"), 1),
    (S + "macd-sinyal", dict(gosterge="ad", sinyal=21, sinyal_tipi="sma"), 1),
    (S + "macd-sinyal", dict(gosterge="pvt", sinyal=21, sinyal_tipi="sma"), 1),
    (S + "macd-sinyal", dict(gosterge="mfi", osc_n=14, sinyal=9), 1),
    (S + "macd-sinyal", dict(gosterge="uo", mod="esik", esik=65.0), 1),
    (S + "macd-sinyal", dict(gosterge="emv", osc_n=14, mod="sifir"), 1),
    (S + "macd-sinyal", dict(gosterge="decycler", mod="sifir"), 1),
    (S + "macd-sinyal", dict(gosterge="adx_di"), 1),
    (S + "macd-sinyal", dict(gosterge="adx_di", kaydirma=10), 1),
    (S + "macd-sinyal", dict(gosterge="macd", sinyal_tipi="sma"), 1),
    (S + "rsi-asiri-donus", dict(gosterge="uo", rsi_periyot=7, alt=30.0, mod="bolgede"), 1),
    (S + "rsi-asiri-donus", dict(gosterge="tsi", rsi_periyot=25, osc_kisa=13, alt=37.5, mod="bolgede"), 1),
    (S + "rsi-asiri-donus", dict(gosterge="stc", rsi_periyot=10, osc_kisa=23, osc_uzun=50, alt=25.0), 1),
    (S + "rsi-asiri-donus", dict(gosterge="mfi", rsi_periyot=22, alt=30.0), 1),
    (S + "rsi-asiri-donus", dict(gosterge="wpr", rsi_periyot=18, alt=10.0), 1),
    (S + "rsi-asiri-donus", dict(gosterge="arsi"), 1),
    (S + "rsi-asiri-donus", dict(esik_modu="uyarlanir"), 1),
    (S + "rsi-asiri-donus", dict(esik_modu="atr_oran", mod="bolgede"), 1),
    (S + "rsi-asiri-donus", dict(esik_modu="dinamik_medyan"), 1),
    (S + "supertrend-psar", dict(gosterge="chandelier"), 1),
    (S + "supertrend-psar", dict(gosterge="nrtr"), 1),
    (S + "supertrend-psar", dict(gosterge="ha_atr"), 1),
    (S + "ma-kesisim", dict(ma_tipi="wma"), 1),
    (S + "ma-kesisim", dict(ma_tipi="hma"), 1),
    (S + "ma-kesisim", dict(ma_tipi="alma"), 1),
    (S + "ma-kesisim", dict(ma_tipi="cma", hizli=10, yavas=35), 1),
    (S + "ma-kesisim", dict(ma_tipi="mama", kaynak="ha_ohlc4"), 1),
    (S + "ma-kesisim", dict(ma_tipi="itrend"), 1),
    (S + "bant-donus", dict(bant_tipi="envelope", adx_esik=0.0), 1),
    (S + "bant-donus", dict(bant_tipi="tma", adx_esik=0.0), 1),
    (S + "bant-donus", dict(onay_osc="stokastik", adx_esik=0.0), 1),
    (S + "bant-donus", dict(onay_osc="stochrsi", adx_esik=0.0, onay_esik=40.0), 1),
    (S + "bant-donus", dict(orta_egim_n=3, adx_esik=0.0), 1),
    (S + "ichimoku", dict(mod="skor", skor_esik=30.0, skor_cikis=20.0), 1),
    (S + "ardisik-bar-tukenme", dict(seri_n_short=2, tetik="seri_sonu"), 1),
    (S + "heikin-ashi-donus", dict(aralik_yuzde=0.5), 1),
    (S + "mum-yutan-donus", dict(mod="devam", desen="ikisi", devam_ma=50), 1),
    (S + "mum-yutan-donus", dict(mod="devam", desen="marubozu", maru_oran=0.5, maru_govde=0.3, devam_ma=50), 1),
    (S + "ma-geri-cekilme", dict(mod="uclu_hiza", hiza1=20, hiza2=50, hiza3=100, hedef_r=1.5), 1),
    ("dis__sqz-donus", dict(ema_oran=0.99, ewo_esik=0.1, wr_esik=48.0), 1),
    ("dis__sqz-donus", dict(sqz_sart=True, guc=0.0), 0),
    ("dis__min10-dip", dict(cikis_modu="pencere_zirve", pencere=15, zaman_cikisi=0), 1),
    ("onceki__kapitulasyon", dict(esik=0.05, pencere=24, hacim_k=1.3, rsi_esik=15.0, donus_teyit=True), 1),
    ("onceki__kapitulasyon", dict(esik=0.03, pencere=24, dip_n=48, sma_n=200), 1),
    ("dis__hacim-patlama-kirilimi", dict(kirilim_ref="n_mum_zirve", hacim_k=2.0), 1),
    ("dis__ilk-yarim-saat-son-yarim-saat", dict(r1_ref="onceki_kapanis", sinyal="r12"), 1),
    ("dis__ilk-yarim-saat-son-yarim-saat", dict(sinyal="r1_r12"), 0),
    ("dis__pivot-ters-stop", dict(giris="olusum", sol=4, sag=2, stop_yuzde=5.0, hedef_yuzde=4.0), 1),
    ("dis__bant-kirilim-trend", dict(mod="bollinger", n=18, k=3.4, cci_n=10), 0),
    ("daytrade__pivot-seviye", dict(mod="camarilla", cam_bolge=1), 1),
    ("daytrade__pivot-seviye", dict(mod="camarilla", cam_bolge=2, hedef_modu="r"), 1),
    ("dis__funding-carry", dict(giris_modu="esik", short=True, long=False, rejim=False), 1),
]


def _kimlik(x):
    ad, par, _ = x
    return ad + ":" + ",".join(f"{k}={v}" for k, v in par.items())


@pytest.mark.parametrize("ad,par,en_az", YENI, ids=[_kimlik(x) for x in YENI])
def test_yeni_mod_sinyal_stop_cikis(ad, par, en_az):
    s = kayit.al(ad)(**par)
    sig = s.sinyaller(MUM)
    assert sig.index.equals(MUM.index)
    assert {"yon", "stop", "hedef", "cikis"} <= set(sig.columns)
    gi = sig[sig["yon"] != 0]
    assert len(gi) >= en_az, f"{ad} {par}: sinyal yok"
    kap = MUM["kapanis"].reindex(gi.index)
    assert gi["stop"].notna().all()
    assert (gi.loc[gi["yon"] == 1, "stop"] < kap[gi["yon"] == 1]).all()
    assert (gi.loc[gi["yon"] == -1, "stop"] > kap[gi["yon"] == -1]).all()
    ayarda = s.cikis_ayarlari
    assert s.cikis_var_mi() or any(getattr(ayarda, a) not in (None, ()) for a in
                                   ("atr_iz_suren_k", "zaman_cikisi_mum", "sabit_r_hedefi")) or "zaman_cikisi_mum" in sig.columns


@pytest.mark.parametrize("ad,par,en_az", YENI, ids=[_kimlik(x) for x in YENI])
def test_yeni_mod_lookahead_yok(ad, par, en_az):
    s = kayit.al(ad)(**par)
    tam = s.sinyaller(MUM)
    for n in (700, 1100):
        parca = s.sinyaller(MUM.iloc[:n])
        pdt.assert_frame_equal(parca, tam.iloc[:n], check_exact=False, rtol=1e-9, atol=1e-9)


# ---------------------------------------------------------------- 3. varsayılan davranış değişmez
_OZET = json.loads((DIZIN / "d11j_varsayilan_ozet.json").read_text(encoding="utf-8"))


def test_varsayilan_ve_izgara_sinyalleri_degismedi():
    kayitli = kayit.tum_stratejiler()
    bozuk = []
    n = 0
    for ad in _OZET["_adlar"]:
        s = kayitli[ad]
        adlar = list(s.parametre_izgarasi)
        for par in [{}] + [dict(zip(adlar, d)) for d in itertools.product(*s.parametre_izgarasi.values())]:
            anahtar = f"{ad}|{json.dumps(par, sort_keys=True)}|0"
            beklenen = _OZET["ozet"][anahtar]
            try:
                sonuc = _ozet(s(**par).sinyaller(MUM.copy()))
            except Exception as e:  # noqa: BLE001 - özet dosyasında hata da kayıtlı olabilir
                sonuc = "HATA:" + type(e).__name__
            n += 1
            if sonuc != beklenen:
                bozuk.append((anahtar, beklenen, sonuc))
    assert n > 500
    assert not bozuk, bozuk[:5]


def test_yeni_parametreler_varsayilanda_etkisiz():
    """Yeni parametrelerin varsayılan değerleri nötrdür (mod anahtarları eski davranışı seçer)."""
    kayitli = kayit.tum_stratejiler()
    beklenen = {
        "swing__macd-sinyal": dict(gosterge="macd", sinyal_tipi="ema", kaydirma=0),
        "swing__rsi-asiri-donus": dict(esik_modu="sabit"),
        "scalp__supertrend-psar": dict(gosterge="supertrend"),
        "swing__ma-kesisim": dict(kaynak="kapanis"),
        "swing__bant-donus": dict(bant_tipi="bollinger", orta_egim_n=0, onay_osc=""),
        "swing__ichimoku": dict(mod="kijun_bulut"),
        "swing__mum-yutan-donus": dict(mod="donus"),
        "swing__ma-geri-cekilme": dict(mod="klasik"),
        "dis__pivot-ters-stop": dict(giris="kirilim", stop_yuzde=0.0, hedef_yuzde=0.0),
    }
    for ad, kv in beklenen.items():
        v = kayitli[ad].varsayilan_parametreler
        for k, x in kv.items():
            assert v[k] == x, (ad, k)
    # yeni modlar ızgaraya girmedi
    assert "esik_modu" not in kayitli["swing__rsi-asiri-donus"].parametre_izgarasi
    assert "gosterge" not in kayitli["swing__macd-sinyal"].parametre_izgarasi
    assert "ma_tipi" not in kayitli["swing__ma-kesisim"].parametre_izgarasi
    assert "bant_tipi" not in kayitli["swing__bant-donus"].parametre_izgarasi


# ---------------------------------------------------------------- 4. portföy sınıfları
def _pf_gunluk(seed, n=900):
    rng = np.random.default_rng(seed)
    kap = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.02, n)))
    ac = np.r_[kap[0], kap[:-1]] * (1 + rng.normal(0, 0.003, n))
    yu = np.maximum(ac, kap) * (1 + rng.uniform(0, 0.01, n))
    du = np.minimum(ac, kap) * (1 - rng.uniform(0, 0.01, n))
    hac = rng.uniform(50, 500, n)
    idx = pd.date_range("2022-01-01", periods=n, freq="1D", tz="UTC", name="zaman")
    return pd.DataFrame({"acilis": ac, "yuksek": yu, "dusuk": du, "kapanis": kap, "hacim": hac}, index=idx)


def _pf_veri():
    from motor.portfoy.stratejiler.ortak import HEPSI
    veriler = {s: _pf_gunluk(i + 1) for i, s in enumerate(HEPSI)}
    veriler["DK_SPX"] = _pf_gunluk(99)
    return veriler


@pytest.fixture(scope="module")
def pf_veri():
    return _pf_veri()


def _pf_ozet(h):
    # Zaman indeksi çözünürlüğü pandas 2.x (ns) / 3.x (us) arasında değişir; hash'in değerleri etkilenmesin diye
    # indeks sabit "us" çözünürlüğüne çekilir (değerler ve zaman damgaları aynı, yalnız iç dtype normalize).
    h = h.copy()
    h.index = h.index.as_unit("us")
    h = h.apply(_yuvarla)
    return hashlib.sha256(pd.util.hash_pandas_object(h.fillna(-999.0), index=True).values.tobytes()).hexdigest()[:16] \
        + f":{int(h.notna().sum().sum())}"


def test_pf_varsayilan_hedefler_degismedi(pf_veri):
    from motor.portfoy.stratejiler import tum_portfoy_stratejileri
    beklenen = json.loads((DIZIN / "d11j_varsayilan_pf_ozet.json").read_text(encoding="utf-8"))
    kayitli = tum_portfoy_stratejileri()
    bozuk = []
    for anahtar, deger in beklenen.items():
        ad, par = anahtar.split("|", 1)
        sonuc = _pf_ozet(kayitli[ad](**json.loads(par)).hedefler(pf_veri))
        if sonuc != deger:
            bozuk.append((anahtar, deger, sonuc))
    assert len(beklenen) > 50
    assert not bozuk, bozuk[:5]


_EK = json.loads((KOK / "stratejiler" / "ayarlar_d11j_ek.json").read_text(encoding="utf-8"))
_EK_PF = [x for x in _EK if x["hedef"].startswith("pf__")]
_EK_DIS = [x for x in _EK if not x["hedef"].startswith("pf__")]


def _par(x):
    return {k: (tuple(v) if isinstance(v, list) else v) for k, v in x["parametreler"].items()}


@pytest.mark.parametrize("x", _EK_PF, ids=[x["ayar_id"] for x in _EK_PF])
def test_pf_yeni_modlar_calisir(x, pf_veri):
    from motor.portfoy.stratejiler import tum_portfoy_stratejileri
    s = tum_portfoy_stratejileri()[x["hedef"]](**_par(x))
    h = s.hedefler(pf_veri)
    assert h.shape[0] > 0 and h.notna().sum().sum() > 0, x["ayar_id"]
    assert (h.abs().fillna(0.0) <= 1.0 + 1e-9).all().all()
    # nedensellik: son 200 günü silince önceki hedefler aynı kalmalı
    kisa = {k: v.iloc[:-200] for k, v in pf_veri.items()}
    h2 = s.hedefler(kisa)
    ortak = h2.index
    pdt.assert_frame_equal(h.loc[ortak], h2, check_exact=False, rtol=1e-9, atol=1e-9)


@pytest.mark.parametrize("x", _EK_DIS, ids=[x["ayar_id"] for x in _EK_DIS])
def test_ek_dis_ayar_calisir(x):
    s = kayit.al(x["hedef"])(**_par(x))
    sig = s.sinyaller(MUM)
    assert (sig["yon"] != 0).sum() > 0


def test_ek_ayar_bilinmeyen_parametre_yok(pf_veri):
    from motor.portfoy.stratejiler import tum_portfoy_stratejileri
    for x in _EK:
        sinif = tum_portfoy_stratejileri()[x["hedef"]] if x["hedef"].startswith("pf__") else kayit.al(x["hedef"])
        assert set(x["parametreler"]) <= set(sinif.varsayilan_parametreler), x["ayar_id"]


# ---------------------------------------------------------------- 5. yardımcı göstergeler
def test_osilator_sinirlari():
    y, d, k, h = MUM["yuksek"], MUM["dusuk"], MUM["kapanis"], MUM["hacim"]
    for s, alt, ust in ((j.ultimate_osc(y, d, k), 0, 100), (j.stc(k), 0, 100), (j.mfi(y, d, k, h), 0, 100),
                        (j.williams_r(y, d, k), -100, 0), (j.tsi(k), -100, 100)):
        v = s.dropna()
        assert len(v) > 1000 and v.min() >= alt - 1e-9 and v.max() <= ust + 1e-9


def test_chandelier_cizgi_trend_icinde_tek_yonlu():
    df = j.chandelier(MUM["yuksek"], MUM["dusuk"], MUM["kapanis"])
    yon, ls = df["yon"], df["cizgi_l"]
    # önceki kapanış çizginin üstündeyken (Chandelier kuralı) uzun çizgi azalmaz
    kap = MUM["kapanis"]
    devam = (yon == 1) & (yon.shift(1) == 1) & ls.notna() & ls.shift(1).notna() & (kap.shift(1) > ls.shift(1))
    assert (ls[devam] >= ls.shift(1)[devam] - 1e-12).all()


def test_nrtr_yon_ve_cizgi_tarafi():
    k = MUM["kapanis"]
    df = j.nrtr(k, 0.02)
    ok = df["yon"] == 1
    assert (df.loc[ok & (k.index > k.index[25]), "cizgi_l"] < k[ok & (k.index > k.index[25])]).mean() > 0.95


def test_ayar_agirlik_fonksiyonlari():
    rng = np.random.default_rng(3)
    a = rng.normal(0, 0.01, (400, 6))
    a[:, 1] += 0.8 * a[:, 0]
    cov = np.cov(a.T)
    for w in (j.hrp_agirlik(cov), j.min_varyans_agirlik(cov)):
        assert abs(w.sum() - 1.0) < 1e-9 and (w >= -1e-12).all()
    w = j.maks_sharpe_agirlik(cov, a.mean(0))
    assert w.sum() == 0 or abs(w.sum() - 1.0) < 1e-9
    assert j.maks_sharpe_agirlik(cov, -np.abs(a.mean(0))).sum() == 0     # beklenen getiri yoksa nakit
    # HRP: iki özdeş varlık eşit ağırlık alır
    c2 = np.array([[1.0, 0.9, 0.1], [0.9, 1.0, 0.1], [0.1, 0.1, 1.0]]) * 1e-4
    w2 = j.hrp_agirlik(c2)
    assert abs(w2[0] - w2[1]) < 1e-9


def test_rejim_ftd_ve_dagitim():
    r = np.r_[np.full(60, 0.004), np.full(8, -0.006), [0.002, 0.003, 0.004, 0.002, 0.02], np.full(10, 0.003)]
    kap = pd.Series(100 * np.cumprod(1 + r), index=pd.date_range("2020-01-01", periods=len(r)))
    hac = pd.Series(np.r_[np.full(68, 1.0), [1, 1, 1, 1, 2], np.full(10, 2)], index=kap.index)
    on = j.rejim_ftd(kap, hac)
    assert not on.iloc[:72].any() and on.iloc[-1]           # FTD öncesi kapalı, 5. rally gününde açılır
    dag = j.rejim_dagitim(kap, hac, esik=3)
    assert dag.dtype == bool and dag.iloc[0]


def test_triple_rsi_ve_mama_nedensel():
    kap = pd.DataFrame({"a": MUM["kapanis"], "b": MUM15["kapanis"].to_numpy()}, index=MUM.index)
    tr = j.triple_rsi_ok(kap)
    assert tr.dtypes.eq(bool).all()
    tam = j.mama_fama(MUM["kapanis"])
    kes = j.mama_fama(MUM["kapanis"].iloc[:800])
    pdt.assert_series_equal(tam[0].iloc[:800], kes[0], check_exact=False)
    pdt.assert_series_equal(tam[1].iloc[:800], kes[1], check_exact=False)
