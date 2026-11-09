"""D12b: Kakushadze & Serur "151 Trading Strategies" taramasından tek-grafik stratejiler.

Kaynak: arXiv 1912.04492 (İspanyolca baskı). Kitap metni repoda yok; burada yalnız kural özeti ve tarih tablosu var.
  dis__hp-filtre-ma    §8.1  HP filtreli MA kesişimi (NEDENSEL HP: bkz. _gosterge_d12b)
  dis__fomc-gunu-long  §19.5 FOMC duyuru günü long, gün sonu çıkış
"""
import numpy as np
import pandas as pd

from motor.strateji.dis._gosterge_d3 import ORTAK, D3Taban
from motor.strateji.dis._gosterge_d12b import hp_nedensel
from motor.strateji.gostergeler_b2 import gecis

# FOMC KARAR (açıklama) günleri, planlı toplantıların 2. günü. Kaynak: Federal Reserve "FOMC Meeting calendars and
# information" sayfası (federalreserve.gov/monetarypolicy/fomccalendars.htm) yayımlanmış takvimleri; hafızadan yazıldı.
# NOT: 2020-03-03 ve 2020-03-15 acil (planlı olmayan) kesintilerdir, tabloda YOK. 2026 satırı Fed'in önceden yayımladığı
# takvimdir (gerçekleşme teyidi yapılmadı); herhangi bir tarihten emin olunmazsa tablo dışı bırakılır, eksik tarih strateji
# için "o gün işlem yok" demektir. Tablo 2020-2026 dışını KAPSAMAZ.
FOMC_GUNLERI = (
    "2020-01-29", "2020-04-29", "2020-06-10", "2020-07-29", "2020-09-16", "2020-11-05", "2020-12-16",
    "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16", "2021-07-28", "2021-09-22", "2021-11-03", "2021-12-15",
    "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15", "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14", "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
)


class HpFiltreMa(D3Taban):
    """dis__hp-filtre-ma — HP trend bileşeni üzerinde hızlı/yavaş SMA kesişimi (long/short).
    Kaynak: 151 §8.1. Kural: kapanışın nedensel HP trendi (her bar yalnız son `hp_pencere` barı görür, klasik HP çözümünün pencere
    sonu noktası; lambda = `hp_lambda`); trendin `hizli` ve `yavas` SMA'sı. hizli > yavas ise long durumu, hizli < yavas short
    durumu; durum değişiminde giriş, ters duruma geçince çıkış (yonler="long": short yok). Stop ATR (orijinalde yok -> varsayım).
    Sapma: kitap iki taraflı HP'yi anar (lookahead) -> tek taraflı sürüm; lambda/pencere/MA uzunlukları kitapta sabit değil (varsayım)."""
    ad = "dis__hp-filtre-ma"
    stil = "swing"
    varsayilan_parametreler = {**ORTAK, "yonler": "ls", "hp_lambda": 1600.0, "hp_pencere": 100, "hizli": 5, "yavas": 21,
                               "stop_atr_k": 3.0}
    parametre_izgarasi = {"hp_lambda": [400.0, 1600.0, 6400.0], "hizli": [3, 5, 8], "yavas": [13, 21, 34]}

    def kosullar(self, m):
        p = self.parametreler
        h, y = int(p["hizli"]), int(p["yavas"])
        if h >= y:
            raise ValueError("hizli < yavas olmalı")
        tr = hp_nedensel(m["kapanis"], p["hp_lambda"], int(p["hp_pencere"]))
        hz, yv = tr.rolling(h, min_periods=h).mean(), tr.rolling(y, min_periods=y).mean()
        ok = hz.notna() & yv.notna()
        yukari, asagi = (hz > yv) & ok, (hz < yv) & ok
        return {"long": gecis(yukari), "short": gecis(asagi), "cikis_long": asagi, "cikis_short": yukari}


class FomcGunuLong(D3Taban):
    """dis__fomc-gunu-long — FOMC karar gününün ilk barının kapanışında long, ABD seansı sonunda çık (gün içi, 1h/30m).
    Kaynak: 151 §19.5 (kitap: FOMC günü hisse, diğer günler nakit/tahvil; burada yalnız o gün long, diğer günler işlemsiz).
    Kural: UTC takvim günü FOMC_GUNLERI tablosundaysa o günün ilk barının kapanışında long (motor sonraki açılışta girer);
    çıkış: barın kapanış anı >= `cikis_saat` (UTC; 20.0 = yaz saatinde ABD kapanışı, kışın 1 saat erken) ya da UTC gün sonu
    (gun_sonu; 24 saat işlem gören DK_SPX için güvence). Yalnız long. Stop ATR (orijinalde yok -> varsayım).
    Yalnız DK_SPX ve ABD hisseleri için anlamlıdır (diğer enstrümanlarda çalıştırmak bir anlam taşımaz); 1 günden uzun
    mumlarda ValueError. Tablo 2020-2026 dışını kapsamaz (bkz. FOMC_GUNLERI). Tek enstrüman başına yılda ~8 işlem: istatistiksel güç düşük."""
    ad = "dis__fomc-gunu-long"
    stil = "daytrade"
    _gun_sonu = True
    varsayilan_parametreler = {**ORTAK, "stop_atr_k": 2.0, "cikis_saat": 20.0}
    parametre_izgarasi = {"cikis_saat": [18.0, 20.0, 21.0], "stop_atr_k": [1.5, 2.0, 3.0]}

    def kosullar(self, m):
        idx = m.index
        if len(idx) < 2:
            return {}
        fark = ((idx[1:] - idx[:-1]) / pd.Timedelta(seconds=1)).to_numpy()
        sure = np.r_[np.nan, np.minimum.accumulate(fark)]          # nedensel (yalnız geçmiş aralıklar)
        if np.nanmin(sure) >= 86400:
            raise ValueError("dis__fomc-gunu-long gün içi (< 1d) mum ister")
        gun = idx.normalize()
        fomc = pd.Series(gun.isin(pd.to_datetime(list(FOMC_GUNLERI), utc=True)), index=idx)
        ilk = pd.Series(gun != gun.to_series().shift(1).to_numpy(), index=idx)
        kapanis_zamani = idx + pd.to_timedelta(np.where(np.isnan(sure), 0.0, sure), unit="s")
        saat = pd.Series(kapanis_zamani.hour + kapanis_zamani.minute / 60.0, index=idx)
        # kapanış anı ertesi güne taşan bar (saat ~0) gun_sonu ile kapatılır
        return {"long": fomc & ilk, "cikis_long": (saat >= float(self.parametreler["cikis_saat"])) & (kapanis_zamani.normalize() == gun)}
