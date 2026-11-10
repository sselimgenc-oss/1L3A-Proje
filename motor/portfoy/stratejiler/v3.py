"""v3 adayları, parti 1: kesitsel funding ve FIP stratejileri."""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.portfoy.temel import PortfoyStratejisi, atr_tablosu, ortak_eksen
from motor.portfoy.stratejiler.ortak import (
    KRIPTO, ORTAK_PARAMETRELER, PfTemel, Takvim, dongusel_hedef, tetik_satirlari,
)


class _FundingKesit(PortfoyStratejisi):
    """Funding sütunlarını aynı anda sıralayan ortak çekirdek.

    Her sembol DataFrame'inde ``funding_orani`` mum kapanışında bilinen son
    settlement olmalıdır. Eksik sütun sıfır varsayılmaz, açık hata verir.
    """

    funding_gerekli = True
    min_sembol = 2
    varsayilan_parametreler = {
        "semboller": KRIPTO, "dilim": 0.1, "takvim": "D", "bakis_gun": 0,
        "gecikme_gun": 0, "devam": False, "atr_k": 3.0, "atr_periyot": 14,
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
        eksik = [s for s in adlar if "funding_orani" not in veriler[s]]
        if eksik:
            raise ValueError(f"{self.ad}: funding_orani eksik: {eksik}")
        return {s: veriler[s] for s in adlar}

    def _skor(self, panel):
        p = self.parametreler
        skor = panel
        if p["bakis_gun"]:
            skor = panel.rolling(f"{int(p['bakis_gun'])}D", min_periods=2).mean()
        if p["gecikme_gun"]:
            hedef_idx = skor.index - pd.Timedelta(days=int(p["gecikme_gun"]))
            skor = skor.reindex(skor.index.union(hedef_idx)).sort_index().ffill().reindex(hedef_idx)
            skor.index = panel.index
        return skor

    def hedefler(self, veriler):
        ev = self._evren(veriler)
        eksen = ortak_eksen(ev)
        panel = pd.DataFrame({s: d["funding_orani"].reindex(eksen) for s, d in ev.items()}).ffill()
        skor = self._skor(panel)
        p = self.parametreler
        if p["takvim"] == "D":
            tetik = (eksen.hour == 0) & (eksen.minute == 0)
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
    """Bir gün gecikmeli 7 günlük funding ortalamasıyla haftalık tercil L/S.

    Kaynak: https://bryanvine.github.io/alpha-research/paper2.html.
    """

    ad = "pf__v3-funding-7g-haftalik-tercil"
    varsayilan_parametreler = {
        **_FundingKesit.varsayilan_parametreler, "dilim": 1.0 / 3.0,
        "takvim": "W", "bakis_gun": 7, "gecikme_gun": 1,
    }


class FipKesitsel(PfTemel):
    """90 günlük FIP skoruyla haftalık üst %20 long/alt %20 short.

    Kaynak: https://github.com/baptoudur/claudetest. Skor karttaki kesin
    tanımdır: işaret(90g getiri) * (pozitif gün - negatif gün) / 90.
    """

    ad = "pf__v3-fip-kesitsel-momentum"
    min_sembol = 2
    varsayilan_parametreler = {
        **ORTAK_PARAMETRELER, "semboller": KRIPTO, "lookback_gun": 90,
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
        gecerli = np.isfinite(S).sum(axis=1) >= 2
        tetik = tetik_satirlari(ax, p["takvim"], gecerli)

        def agirlik(i):
            s = pd.Series(S[i], index=kolon).dropna().sort_values(kind="stable")
            k = min(max(1, int(np.ceil(len(s) * p["dilim"]))), len(s) // 2)
            if k < 1:
                return {}
            w = {c: -p["brut"] / (2 * k) for c in s.index[:k]}
            w.update({c: p["brut"] / (2 * k) for c in s.index[-k:]})
            return w

        return dongusel_hedef(ax, kolon, tetik, agirlik)


V3_SINIFLAR = (Funding1sDevam, FundingKesitCarry, Funding7gTercil, FipKesitsel)
