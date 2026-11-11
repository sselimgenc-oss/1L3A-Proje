"""Parti 5 (pre-FOMC sürüklenme) sinyal kuralları; piyasa sonucu veya backtest çalıştırmaz."""
import numpy as np
import pandas as pd
import pytest

from motor.strateji import kayit
from motor.strateji.dis.v3_adaylar_5 import (FOMC_YOLU, PreFomcSurunme, fomc_takvimi_yukle,
                                             onceki_islem_gunu)

NY = "America/New_York"


def _mum(bas, bitis, tz=NY):
    # 15 dk mumlar, 7/24 (kripto benzeri), açılış zamanlı indeks
    idx = pd.date_range(bas, bitis, freq="15min", tz=tz).tz_convert("UTC")
    rng = np.random.default_rng(1)
    k = pd.Series(100 + np.cumsum(rng.normal(0, 0.1, len(idx))), index=idx)
    return pd.DataFrame({"acilis": k.shift(1).fillna(k.iloc[0]), "yuksek": k + 0.3,
                         "dusuk": k - 0.3, "kapanis": k, "hacim": 10.0}, index=idx)


def _ny(s):
    return pd.Timestamp(s).tz_localize(NY)


def test_kayit_ve_stil():
    assert kayit.al("v3__pre-fomc-surunme") is PreFomcSurunme
    assert PreFomcSurunme.stil == "swing" and PreFomcSurunme().cikis_var_mi()


def test_yaz_ve_kis_giris_cikis_dogru_mumlarda():
    # 2024-07-31 (yaz, EDT) ve 2024-12-18 (kış, EST) 14:00 ET açıklamaları.
    takvim = [_ny("2024-07-31 14:00"), _ny("2024-12-18 14:00")]
    m = _mum("2024-07-20", "2025-01-05")
    s = PreFomcSurunme(takvim=takvim).sinyaller(m)
    ny = m.index.tz_convert(NY)
    giris = m.index[s.yon == 1].tz_convert(NY)
    cikis = m.index[s.cikis].tz_convert(NY)
    assert list(giris) == [_ny("2024-07-30 13:30"), _ny("2024-12-17 13:30")]
    assert list(cikis) == [_ny("2024-07-31 13:30"), _ny("2024-12-18 13:30")]
    # UTC saatleri DST'ye göre kayar: yaz 17:45Z, kış 18:45Z (giriş sinyal mumu).
    assert [t.tz_convert("UTC").hour for t in giris] == [17, 18]
    # Dolum: sinyal mumunun bir sonraki açılışı = 13:45 ET (önceki gün) / 13:45 ET (açıklama günü).
    pos = np.where(s.yon == 1)[0]
    assert m.index[pos[0] + 1].tz_convert(NY) == _ny("2024-07-30 13:45")
    pos = np.where(s.cikis)[0]
    assert m.index[pos[0] + 1].tz_convert(NY) == _ny("2024-07-31 13:45")
    # Stop var ve long için fiyatın altında.
    assert (s.stop[s.yon == 1] < m.kapanis[s.yon == 1]).all()
    assert s.stop[s.yon == 1].notna().all()


def test_fomc_olmayan_gunde_sinyal_yok():
    takvim = [_ny("2024-07-31 14:00")]
    m = _mum("2024-07-01", "2024-09-01")
    s = PreFomcSurunme(takvim=takvim).sinyaller(m)
    assert (s.yon != 0).sum() == 1 and s.cikis.sum() == 1
    bos = PreFomcSurunme(takvim=[]).sinyaller(m)
    assert (bos.yon == 0).all() and not bos.cikis.any()


def test_tatil_sonrasi_onceki_islem_gunu_tatili_atlar():
    # 2024-06-19 Çarşamba Juneteenth (tatil): 2024-06-20 Perşembe açıklaması -> önceki işlem günü 18 Haziran Salı.
    assert onceki_islem_gunu(pd.Timestamp("2024-06-20").date()) == pd.Timestamp("2024-06-18").date()
    # Pazartesi açıklaması -> önceki Cuma.
    assert onceki_islem_gunu(pd.Timestamp("2024-07-08").date()) == pd.Timestamp("2024-07-05").date()
    takvim = [_ny("2024-06-20 14:00")]
    m = _mum("2024-06-10", "2024-06-25")
    s = PreFomcSurunme(takvim=takvim).sinyaller(m)
    assert list(m.index[s.yon == 1].tz_convert(NY)) == [_ny("2024-06-18 13:30")]


def test_acikalama_saati_14_degilse_cikis_ann_eksi_15():
    takvim = [_ny("2024-07-31 14:15")]
    m = _mum("2024-07-25", "2024-08-03")
    s = PreFomcSurunme(takvim=takvim).sinyaller(m)
    assert list(m.index[s.yon == 1].tz_convert(NY)) == [_ny("2024-07-30 13:45")]  # 24 saat pencere: aynı ET saati
    assert list(m.index[s.cikis].tz_convert(NY)) == [_ny("2024-07-31 13:45")]


def test_giris_mumu_yoksa_islem_yok():
    takvim = [_ny("2024-07-31 14:00")]
    m = _mum("2024-07-25", "2024-08-03")
    m = m.drop(index=_ny("2024-07-30 13:30").tz_convert("UTC"))
    s = PreFomcSurunme(takvim=takvim).sinyaller(m)
    assert (s.yon == 0).all()


def test_naif_indeks_utc_sayilir_ve_yeni_takvimi_korur():
    takvim = [_ny("2024-07-31 14:00")]
    m = _mum("2024-07-25", "2024-08-03")
    n = m.copy()
    n.index = n.index.tz_localize(None)
    a = PreFomcSurunme(takvim=takvim).yeni(atr_k=3.0)
    s = a.sinyaller(n)
    assert (s.yon == 1).sum() == 1 and a.parametreler["atr_k"] == 3.0


def test_gercek_takvim_yukleyici():
    t = fomc_takvimi_yukle()
    df = pd.read_csv(FOMC_YOLU, dtype=str, keep_default_na=False)
    beklenen = ((df.planli == "evet") & (df.tip == "planli") & (df.aciklama_utc != "bilinmiyor")).sum()
    assert len(t) == beklenen > 80
    assert all(x.tzinfo is not None for x in t) and t == sorted(t)
    assert pd.Timestamp("2026-12-09", tz="UTC") not in t
    with pytest.raises(FileNotFoundError):
        fomc_takvimi_yukle("/yok/fomc.csv")
