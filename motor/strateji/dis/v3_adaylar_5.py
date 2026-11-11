"""v3 parti 5: FOMC öncesi sürüklenme (Lucca-Moench 2015).

Kaynak: Lucca & Moench, "The Pre-FOMC Announcement Drift", NY Fed Staff Report 512 / J. Finance 2015.
Kart: swing__pre-fomc-surunme__delphic (Delphic Alpha yazısı açılamadı; kural Lucca-Moench'ten).
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.seans_takvimi import NY, _abd_tatilleri
from motor.strateji.temel import Strateji

KOK = Path(__file__).resolve().parents[3]
FOMC_YOLU = KOK / "veri" / "takvim" / "fomc.csv"
_GEREKLI_SUTUNLAR = {"tarih", "aciklama_utc", "planli", "tip"}


def fomc_takvimi_yukle(yol: Path | str | None = None) -> list[pd.Timestamp]:
    """veri/takvim/fomc.csv -> planlı FOMC açıklama anları (UTC, sıralı).

    Süzgeç: planli == "evet", tip == "planli" (plansız, yazılı oylama ve planli_gelecek satırları dışarıda),
    aciklama_utc "bilinmiyor" olmayan satırlar (2013-2015: saat yok, tahmin edilmez).
    """
    yol = Path(yol) if yol is not None else FOMC_YOLU
    if not yol.is_file():
        raise FileNotFoundError(f"FOMC takvim dosyası yok: {yol} (veri/takvim/fomc.csv bekleniyor)")
    df = pd.read_csv(yol, dtype=str, keep_default_na=False)
    eksik = _GEREKLI_SUTUNLAR - set(df.columns)
    if eksik:
        raise ValueError(f"FOMC takvimi sütun eksik: {sorted(eksik)} ({yol})")
    uygun = df[(df["planli"] == "evet") & (df["tip"] == "planli") & (df["aciklama_utc"] != "bilinmiyor")]
    return sorted(pd.to_datetime(uygun["aciklama_utc"], utc=True).tolist())


def onceki_islem_gunu(d: date) -> date:
    """d'den önceki NYSE işlem günü (hafta sonu ve ABD borsa tatilleri atlanır)."""
    x = d - timedelta(days=1)
    while x.weekday() >= 5 or x in _abd_tatilleri(x.year):
        x -= timedelta(days=1)
    return x


class PreFomcSurunme(Strateji):
    """Planlı FOMC açıklamasından 15 dk önce biten 24 saatlik pencerede long (Lucca-Moench).

    Zamanlama (mum indeksi = AÇILIŞ zamanı; sinyal mum kapanışında, dolum bir sonraki mum açılışında, 15 dk mum):
      - giriş: önceki işlem günü (açıklama ET saati - 30 dk) açılışlı mumda yon=1 -> dolum açıklama saati - 15 dk
        (14:00 ET açıklamada 13:30 mumu sinyal, 13:45 dolum).
      - çıkış: açıklama günü (açıklama - 30 dk) açılışlı mumda cikis=True -> dolum açıklamadan 15 dk önce
        (14:00 ET açıklamada 13:30 mumu sinyal, 13:45 dolum).
    Açıklama saati fomc.csv'den okunur; giriş ve çıkış aynı ET saatinde (açıklama - 15 dk). Takvim yalnız önceden ilan edilen tarih/saattir; açıklama sonucu ya da
    gelecek fiyat kullanılmaz. Giriş mumu veride yoksa (ör. DK_SPX'te veri yok, erken kapanış) o olayda işlem yok.
    Stop: kapanış - 2 x ATR(14) ("bizim eklememiz"; kaynakta stop yok).
    """

    ad, stil = "v3__pre-fomc-surunme", "swing"
    varsayilan_parametreler = {"atr_n": 14, "atr_k": 2.0}
    parametre_izgarasi = {}

    def __init__(self, cikis_ayarlari=None, takvim=None, **parametreler):
        super().__init__(cikis_ayarlari=cikis_ayarlari, **parametreler)
        self._takvim_girdi = None if takvim is None else list(takvim)

    def yeni(self, **parametreler) -> "PreFomcSurunme":
        return type(self)(cikis_ayarlari=self.cikis_ayarlari, takvim=self._takvim_girdi,
                          **{**self.parametreler, **parametreler})

    def cikis_var_mi(self):
        return True

    def _olaylar(self) -> list[pd.Timestamp]:
        ham = fomc_takvimi_yukle() if self._takvim_girdi is None else self._takvim_girdi
        return sorted(pd.Timestamp(t).tz_localize("UTC") if pd.Timestamp(t).tzinfo is None
                      else pd.Timestamp(t).tz_convert("UTC") for t in ham)

    def sinyaller(self, m):
        idx = m.index
        giris_mumlari, cikis_mumlari = [], []
        for ann in self._olaylar():
            ann_ny = ann.tz_convert(NY)
            onceki = onceki_islem_gunu(ann_ny.date())
            # Kaynak penceresi: açıklamadan 15 dk önce biten 24 saat. Giriş dolumu önceki işlem günü aynı saat
            # (açıklama ET saati - 15 dk; 14:00 açıklamada 13:45), sinyal mumu bundan 15 dk önce açılan mum.
            saat = (ann_ny - pd.Timedelta(minutes=30)).strftime("%H:%M")
            giris_mumlari.append(pd.Timestamp(f"{onceki} {saat}").tz_localize(NY).tz_convert("UTC"))
            # Çıkış dolumu açıklama - 15 dk -> sinyal mumu açıklama - 30 dk açılışlı.
            cikis_mumlari.append(ann - pd.Timedelta(minutes=30))
        u = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
        long_ok = pd.Series(u.isin(giris_mumlari), index=idx)
        cikis = pd.Series(u.isin(cikis_mumlari), index=idx)
        atr = g.atr(m["yuksek"], m["dusuk"], m["kapanis"], int(self.parametreler["atr_n"]))
        k = float(self.parametreler["atr_k"])
        return cerceve(m, long_ok, False, m["kapanis"] - atr * k, m["kapanis"] + atr * k, cikis=cikis)
