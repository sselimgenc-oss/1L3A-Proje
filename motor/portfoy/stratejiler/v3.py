"""v3 adayları, parti 1: kesitsel funding ve FIP stratejileri."""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.portfoy.temel import PortfoyStratejisi, atr_tablosu, ortak_eksen
from motor.strateji.funding import GUNLUK_TOPLAM_SUTUN, SUTUN as FUNDING_SUTUNU
from motor.portfoy.stratejiler.ortak import (
    HEPSI, KRIPTO, ORTAK_PARAMETRELER, PfTemel, Takvim, dongusel_hedef, tetik_satirlari,
)


V3_KRIPTO = (
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT", "TRXUSDT", "ZECUSDT",
    "HYPEUSDT", "DOGEUSDT", "LINKUSDT", "ADAUSDT", "XLMUSDT", "BCHUSDT",
)


class _FundingKesit(PortfoyStratejisi):
    """Funding sütunlarını aynı anda sıralayan ortak çekirdek.

    Alt sınıf ``funding_sutunu`` ile son settlement oranını ya da mum aralığı
    toplamını seçer. Eksik sütun sıfır varsayılmaz, açık hata verir.
    """

    funding_gerekli = True
    funding_sutunu = FUNDING_SUTUNU
    min_sembol = 2
    varsayilan_parametreler = {
        "semboller": KRIPTO, "dilim": 0.1, "takvim": "D", "bakis_gun": 0,
        "gecikme_gun": 0, "bakis_min": 2, "devam": False, "atr_k": 3.0, "atr_periyot": 14,
        "iz_stop_yuzde": 0.0,
    }
    parametre_izgarasi = {}

    def etkin_semboller(self, mevcut):
        return tuple(s for s in self.parametreler["semboller"] if s in set(mevcut))

    def ek_semboller(self):
        return ()

    def uygun_mu(self, mevcut):
        return len(self.etkin_semboller(mevcut)) >= self.min_sembol

    def _evren(self, veriler):
        adlar = self.etkin_semboller(veriler)
        if len(adlar) < self.min_sembol:
            raise ValueError(f"{self.ad}: en az iki sembol gerekli")
        eksik = [s for s in adlar if self.funding_sutunu not in veriler[s]]
        if eksik:
            raise ValueError(f"{self.ad}: {self.funding_sutunu} eksik: {eksik}")
        return {s: veriler[s] for s in adlar}

    def _skor(self, panel):
        p = self.parametreler
        skor = panel
        if p["bakis_gun"]:
            skor = panel.rolling(f"{int(p['bakis_gun'])}D", min_periods=int(p["bakis_min"])).mean()
        if p["gecikme_gun"]:
            hedef_idx = skor.index - pd.Timedelta(days=int(p["gecikme_gun"]))
            skor = skor.reindex(skor.index.union(hedef_idx)).sort_index().ffill().reindex(hedef_idx)
            skor.index = panel.index
        return skor

    def hedefler(self, veriler):
        ev = self._evren(veriler)
        eksen = ortak_eksen(ev)
        panel = pd.DataFrame({s: d[self.funding_sutunu].reindex(eksen) for s, d in ev.items()}).ffill()
        skor = self._skor(panel)
        p = self.parametreler
        if p["takvim"] == "D":
            tetik = (eksen.hour == 0) & (eksen.minute == 0)
        elif p["takvim"] == "3D":
            gun = (eksen.floor("D") - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(days=1)
            tetik = (gun % 3 == 0) & (eksen.hour == 0) & (eksen.minute == 0)
        elif p["takvim"] == "W":
            tetik = (eksen.day_of_week == 0) & (eksen.hour == 0) & (eksen.minute == 0)
        else:
            raise ValueError("takvim D veya W olmalı")
        h = pd.DataFrame(np.nan, index=eksen, columns=list(ev))
        for i in np.flatnonzero(tetik):
            s = skor.iloc[i].dropna().sort_values(kind="stable")
            if len(s) < 2:
                continue
            n = max(1, int(np.ceil(len(s) * float(p["dilim"]))))
            n = min(n, len(s) // 2)
            dusuk, yuksek = list(s.index[:n]), list(s.index[-n:])
            longlar, shortlar = (yuksek, dusuk) if p["devam"] else (dusuk, yuksek)
            h.iloc[i] = 0.0
            h.loc[eksen[i], longlar] = 0.5 / n
            h.loc[eksen[i], shortlar] = -0.5 / n
        # Portföy sözleşmesi: stopsuz hedef açılamaz. ATR ısınmadan gelen ilk
        # takvim tetikleri açıkça sıfıra çekilir; sonraki tetikte yeniden seçilir.
        atr = atr_tablosu(ev, int(p["atr_periyot"])).reindex(eksen).ffill()
        h = h.mask(h.notna() & h.ne(0.0) & atr.isna(), 0.0)
        return h

    def stoplar(self, veriler, hedefler):
        ev = self._evren(veriler)
        eksen = hedefler.index
        kap = pd.DataFrame({s: d["kapanis"].reindex(eksen) for s, d in ev.items()}).ffill()
        atr = atr_tablosu(ev, int(self.parametreler["atr_periyot"])).reindex(eksen).ffill()
        yon = np.sign(hedefler.ffill().fillna(0.0))
        stop = kap - yon * float(self.parametreler["atr_k"]) * atr
        return stop.where(yon != 0)


class Funding1sDevam(_FundingKesit):
    """00:00 UTC funding kesitinde yüksek long/düşük short, bir sonraki saatte yeniden sıfırla.

    Kaynak: https://github.com/OctopusTakopi/funding-rate-alpha. Portföy motoru
    hedefi bir sonraki bar açılışında doldurduğundan saatlik veri kullanılmalıdır.
    """

    ad = "pf__v3-funding-1s-devam"
    varsayilan_parametreler = {**_FundingKesit.varsayilan_parametreler, "devam": True}

    def hedefler(self, veriler):
        h = super().hedefler(veriler)
        acilis = h.notna().any(axis=1) & h.fillna(0.0).ne(0.0).any(axis=1)
        for i in np.flatnonzero(acilis):
            if i + 1 < len(h):
                h.iloc[i + 1] = 0.0
        return h


class FundingKesitCarry(_FundingKesit):
    """Günlük düşük funding long/yüksek funding short decil carry.

    Kaynak: https://github.com/OctopusTakopi/funding-rate-alpha.
    """

    ad = "pf__v3-funding-kesit-decil-carry"


class Funding7gTercil(_FundingKesit):
    """Bir gün gecikmeli 7 günlük toplam-funding ortalamasıyla haftalık tercil L/S.

    Günlük toplam, o günlük mumun aralığındaki tüm settlement oranlarının
    toplamıdır; son settlement oranı değildir. Kaynak:
    https://bryanvine.github.io/alpha-research/paper2.html.
    """

    ad = "pf__v3-funding-7g-haftalik-tercil"
    funding_sutunu = GUNLUK_TOPLAM_SUTUN
    varsayilan_parametreler = {
        **_FundingKesit.varsayilan_parametreler, "dilim": 1.0 / 3.0,
        "semboller": V3_KRIPTO, "takvim": "W", "bakis_gun": 7,
        "bakis_min": 7, "gecikme_gun": 1,
    }


class FundingZ90UcGun(_FundingKesit):
    """90 günlük kendi-tarihçe funding z-skoruyla üç günde bir decil L/S.

    Kaynak: https://github.com/OctopusTakopi/funding-rate-alpha. Üst üste
    binen kohort kaynakta belirsiz olduğundan tek kohort üç günde bir yenilenir.
    """

    ad = "pf__v3-funding-z90-3gun"
    varsayilan_parametreler = {
        **_FundingKesit.varsayilan_parametreler, "takvim": "3D", "z_gun": 90,
    }

    def _skor(self, panel):
        n = int(self.parametreler["z_gun"])
        ort = panel.rolling(f"{n}D", min_periods=n).mean()
        sapma = panel.rolling(f"{n}D", min_periods=n).std(ddof=0).replace(0.0, np.nan)
        return (panel - ort) / sapma


class FipKesitsel(PfTemel):
    """90 günlük FIP skoruyla haftalık üst %20 long/alt %20 short.

    Kaynak: https://github.com/baptoudur/claudetest. Skor karttaki kesin
    tanımdır: işaret(90g getiri) * (pozitif gün - negatif gün) / 90.
    """

    ad = "pf__v3-fip-kesitsel-momentum"
    min_sembol = 5
    varsayilan_parametreler = {
        **ORTAK_PARAMETRELER, "semboller": V3_KRIPTO, "lookback_gun": 90,
        "dilim": 0.2, "takvim": "W", "brut": 1.0,
    }
    parametre_izgarasi = {}

    def _hedef(self, ev, tk: Takvim):
        p, kolon, ax = self.parametreler, list(ev), tk.eksen
        n = int(p["lookback_gun"])
        r = tk.getiri()[kolon]
        duzgunluk = ((r > 0).astype(float) - (r < 0).astype(float)).rolling(n, min_periods=n).sum() / n
        skor = np.sign(tk.mom(n)[kolon]) * duzgunluk
        S = tk.eksene(skor).to_numpy(dtype=float)
        gecerli = np.isfinite(S).sum(axis=1) >= self.min_sembol
        tetik = tetik_satirlari(ax, p["takvim"], gecerli)

        def agirlik(i):
            s = pd.Series(S[i], index=kolon).dropna().sort_values(kind="stable")
            if len(s) < self.min_sembol:
                return {}
            k = min(max(1, int(np.ceil(len(s) * p["dilim"]))), len(s) // 2)
            if k < 1:
                return {}
            w = {c: -p["brut"] / (2 * k) for c in s.index[:k]}
            w.update({c: p["brut"] / (2 * k) for c in s.index[-k:]})
            return w

        return dongusel_hedef(ax, kolon, tetik, agirlik)


class KriptoMaxPiyango(PfTemel):
    """MAX (piyango) kesiti: son 28 günün en yüksek günlük getirisine göre haftalık üst %20 long / alt %20 short.

    Kaynak: Özdamar, Akdeniz, Şensoy, Financial Innovation 2021, Eq.(1), dipnot 9, Tablo 2
    (https://link.springer.com/article/10.1186/s40854-021-00291-9). Kriptoda 7/24 olduğundan "ay" = 28 gün kayan
    pencere, her hafta yeniden hesaplanır (kaynak dipnot 9). MAX(N=1) = penceredeki en yüksek günlük getiri.
    YÖN kaynağın bulduğu gibi: yüksek MAX long, düşük MAX short (hisse literatürünün tersi; kriptoda 10-1 pozitif).
    Satır t'nin skoru t günlük çubuğunun kapanışına kadar olan 28 günlük getiriyi kullanır (t dahil, tamamlanmış çubuk);
    emir bir sonraki barın açılışında dolar (FIP ile aynı zamanlama), gelecek veri yoktur.
    Bizim uyarlamalarımız: sabit 13 coinlik evren (hayatta kalma yanlılığı), decil yerine üst/alt %20 (en az 1,
    en çok n/2 sembol), eşit ağırlık, brüt 1,0 (bacak başına 0,5), haftalık Pazartesi tetik. Kaynakta stop yok:
    ortak ATR(14) x 3 stop "bizim eklememiz".
    """

    ad = "pf__v3-kripto-max-piyango"
    min_sembol = 5
    varsayilan_parametreler = {
        **ORTAK_PARAMETRELER, "semboller": V3_KRIPTO, "pencere_gun": 28, "max_n": 1,
        "dilim": 0.2, "takvim": "W", "brut": 1.0,
    }
    parametre_izgarasi = {}

    def _hedef(self, ev, tk: Takvim):
        p, kolon, ax = self.parametreler, list(ev), tk.eksen
        n, mn = int(p["pencere_gun"]), int(p["max_n"])
        r = tk.getiri()[kolon]
        if mn == 1:
            skor = r.rolling(n, min_periods=n).max()
        else:
            skor = r.rolling(n, min_periods=n).apply(lambda x: np.sort(x)[-mn:].mean(), raw=True)
        S = tk.eksene(skor).to_numpy(dtype=float)
        gecerli = np.isfinite(S).sum(axis=1) >= self.min_sembol
        tetik = tetik_satirlari(ax, p["takvim"], gecerli)

        def agirlik(i):
            s = pd.Series(S[i], index=kolon).dropna().sort_values(kind="stable")
            if len(s) < self.min_sembol:
                return {}
            k = min(max(1, int(np.ceil(len(s) * p["dilim"]))), len(s) // 2)
            if k < 1:
                return {}
            w = {c: -p["brut"] / (2 * k) for c in s.index[:k]}
            w.update({c: p["brut"] / (2 * k) for c in s.index[-k:]})
            return w

        return dongusel_hedef(ax, kolon, tetik, agirlik)


class DonchianAnsambl(PfTemel):
    """Dokuz kapanış kanalının eşit ortalamasıyla long-only kripto ansamblı.

    Kaynak: Zarattini vd., ``A Century of Evidence on Trend-Following
    Investing`` revize kripto uygulaması; Tur 4 doğrulama tablosundaki Bölüm
    4.1--5.1. Her model kendi orta-kanal iz stop durumunu taşır. Model ağırlığı
    yıllık %25 / 90 günlük yıllık volatilite, en çok %200'dür. Semboller eşit
    sermaye bütçesi (1/B) alır. Volatilitenin tek başına yarattığı %20'den küçük
    göreli hedef değişimleri emir üretmez; model sinyali değişince emir anında
    üretilir. Motorun zorunlu fiyat stopu ayrıca ATR(14) x 3'tür.
    """

    ad = "pf__v3-donchian-ansambl"
    min_sembol = 2
    varsayilan_parametreler = {
        **ORTAK_PARAMETRELER, "semboller": V3_KRIPTO,
        "pencereler": (5, 10, 20, 30, 60, 90, 150, 250, 360),
        "vol_gun": 90, "hedef_vol": 0.25, "model_tavan": 2.0,
        "vol_islem_esigi": 0.20,
    }
    parametre_izgarasi = {}

    @staticmethod
    def _model_durumu(kap: pd.Series, pencere: int) -> pd.Series:
        up = kap.rolling(pencere, min_periods=pencere).max()
        down = kap.rolling(pencere, min_periods=pencere).min()
        mid = (up + down) / 2.0
        sonuc = np.zeros(len(kap), dtype=bool)
        aktif, ts = False, np.nan
        for i in range(len(kap)):
            c, u, m = kap.iloc[i], up.iloc[i], mid.iloc[i]
            if not (np.isfinite(c) and np.isfinite(u) and np.isfinite(m)):
                continue
            cikti = False
            if aktif:
                if c <= ts:
                    aktif, ts, cikti = False, np.nan, True
                else:
                    ts = max(ts, m)
            if not aktif and not cikti and c == u:
                aktif, ts = True, m
            sonuc[i] = aktif
        return pd.Series(sonuc, index=kap.index)

    def _hedef(self, ev, tk: Takvim):
        p, kolon, ax = self.parametreler, list(ev), tk.eksen
        modeller = []
        for n in p["pencereler"]:
            modeller.append(pd.DataFrame({s: self._model_durumu(tk.kap[s], int(n)) for s in kolon}))
        durum = np.stack([x.to_numpy(dtype=bool) for x in modeller], axis=2)
        degisim = np.any(durum != np.roll(durum, 1, axis=0), axis=2)
        degisim[0] = durum[0].any(axis=1)

        vol = tk.getiri()[kolon].rolling(int(p["vol_gun"]), min_periods=int(p["vol_gun"])).std() * np.sqrt(365.0)
        model_w = (float(p["hedef_vol"]) / vol).clip(upper=float(p["model_tavan"]))
        model_w_np = np.nan_to_num(model_w.to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0)
        istek = durum.astype(float) * model_w_np[:, :, None]
        hedef = np.mean(istek, axis=2) / len(kolon)

        emir = np.full_like(hedef, np.nan, dtype=float)
        mevcut = np.zeros(len(kolon), dtype=float)
        kap = tk.kap[kolon].to_numpy(dtype=float)
        esik = float(p["vol_islem_esigi"])
        for i in range(len(tk.gun)):
            if i > 0:
                oran = np.divide(kap[i], kap[i - 1], out=np.ones(len(kolon)),
                                 where=np.isfinite(kap[i]) & np.isfinite(kap[i - 1]) & (kap[i - 1] != 0))
                nakit = 1.0 - mevcut.sum()
                nominal = mevcut * oran
                toplam = nakit + nominal.sum()
                mevcut = nominal / toplam if toplam > 0 else mevcut
            fark = np.abs(hedef[i] - mevcut)
            vol_degisti = (fark > 0.0) & (fark >= esik * np.abs(mevcut))
            vol_degisti |= (mevcut == 0.0) & (fark > 0.0)
            yaz = degisim[i] | vol_degisti
            emir[i, yaz] = hedef[i, yaz]
            mevcut[yaz] = hedef[i, yaz]
        return pd.DataFrame(emir, index=tk.gun, columns=kolon).reindex(ax)


class VolYonetimliLong(PfTemel):
    """Önceki tam takvim ayının gerçekleşen voluna göre aylık long ağırlık.

    Kaynak: Moreira ve Muir (2017), NBER w22208. Tüm örneklemden seçilen
    ileriye bakan ``c`` yerine önceden sabit yıllık %20 hedef kullanılır;
    ağırlık 1,0 ile sınırlıdır; semboller eşit sermaye (1/n) alır. Kaynakta stop yoktur; motor sözleşmesi için
    ATR(14) x 2 felaket stopu bizim eklememizdir.
    """

    ad = "pf__v3-vol-yonetimli-long"
    min_sembol = 1
    varsayilan_parametreler = {
        **ORTAK_PARAMETRELER, "semboller": HEPSI, "hedef_vol": 0.20,
        "agirlik_tavan": 1.0, "yillik_gun": 252, "atr_k": 2.0,
    }
    parametre_izgarasi = {}

    def _hedef(self, ev, tk: Takvim):
        p, kolon, ax = self.parametreler, list(ev), tk.eksen
        aylik_vol = {}
        for s in kolon:
            r = ev[s]["kapanis"].pct_change(fill_method=None)
            ay = r.index.tz_localize(None).to_period("M")
            aylik_vol[s] = r.groupby(ay).std() * np.sqrt(float(p["yillik_gun"]))
        tetik = tetik_satirlari(ax, "M", np.ones(len(ax), dtype=bool))

        def agirlik(i):
            # Semboller eşit sermaye (1/n) alır; her sembolün kendi payı içinde ağırlık en çok agirlik_tavan.
            onceki_ay = (ax[i].tz_localize(None).to_period("M") - 1)
            sonuc = {}
            for s in kolon:
                v = aylik_vol[s].get(onceki_ay, np.nan)
                sonuc[s] = (min(float(p["hedef_vol"]) / v, float(p["agirlik_tavan"])) / len(kolon)
                              if np.isfinite(v) and v > 0 else 0.0)
            return sonuc

        return dongusel_hedef(ax, kolon, tetik, agirlik)


V3_SINIFLAR = (
    Funding1sDevam, FundingKesitCarry, Funding7gTercil, FundingZ90UcGun,
    FipKesitsel, DonchianAnsambl, VolYonetimliLong, KriptoMaxPiyango,
)
