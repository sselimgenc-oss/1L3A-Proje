"""CTA / zaman serisi momentumu (volatilite hedefli, çok enstrümanlı)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.portfoy.stratejiler.ortak import HEPSI, ORTAK_PARAMETRELER, PfTemel, dongusel_hedef, tetik_satirlari


class Cta(PfTemel):
    """TinyCTA / zaman serisi momentumu (TSMOM), volatilite hedefli.

    Kaynaklar: TinyCTA / 10 satırlık CTA (Markowitz risk uzayında birleştirme; kaynak kod repoda yok, kural özü
    kullanıcı listesinden), awesome: Zaman serisi momentumu (vol hedefli; Moskowitz-Ooi-Pedersen).
    Kural: her enstrümanda sinyal s_i in [-1,1]:
      ewmac : tanh((EMA_hizli - EMA_yavas) / (kapanış * σ_gün * sqrt(yavas)))  (volatiliteye bölünmüş EWM farkı)
      tsmom : işaret(tsmom_gun günlük getiri)
      sma   : işaret(kapanış - SMA(yavas))
    yon="long": negatif sinyaller 0'lanır. Birleştirme:
      bagimsiz : w_i = s_i * (hedef_vol/sqrt(365)) / σ_gün_i / n   (n = geçerli enstrüman; portföy volatilitesi <= hedef)
      kovaryans: Markowitz risk uzayı: w ∝ Σ^-1 (s_i σ_i) ; Σ = kayan (vol_gun) kovaryans, köşegene %50 büzülmüş; toplam
                 volatilite hedef_vol'e (yıllık) ölçeklenir.
    w +-1'e kırpılır (motor ayrıca %1 işlem riski ve 3x brüt uygular). Yeniden dengeleme `takvim`'de.
    Uyarlama: kaynaklar çok geniş vadeli işlem evreni (~60) kullanır; burada 13 enstrüman (3 kripto, 7 hisse, 3 emtia).
    TSMOM'da kaynak long/short bacakları ayrı ters-vol ağırlıklar ve bacak başı vol hedefi + 4x kaldıraç sınırı kullanır;
    burada tek ortak vol hedefi (motor 3x tavanı zaten uygular) -> sade uyarlama.
    """

    ad = "pf__cta"
    min_sembol = 2
    varsayilan_parametreler = {**ORTAK_PARAMETRELER, "semboller": HEPSI, "sinyal": "ewmac", "hizli": 16, "yavas": 64,
                               "tsmom_gun": 365, "vol_gun": 60, "hedef_vol": 0.10, "birlesim": "bagimsiz",
                               "yon": "ls", "takvim": "W", "buzulme": 0.5}
    parametre_izgarasi = {"sinyal": ["ewmac", "tsmom", "sma"], "birlesim": ["bagimsiz", "kovaryans"],
                          "hedef_vol": [0.05, 0.10, 0.20]}

    def _sinyal(self, tk, kolon):
        p = self.parametreler
        kap = tk.kap[kolon]
        sd = tk.vol(p["vol_gun"])[kolon]
        if p["sinyal"] == "ewmac":
            f = kap.ewm(span=p["hizli"], adjust=False, min_periods=p["hizli"]).mean()
            s = kap.ewm(span=p["yavas"], adjust=False, min_periods=p["yavas"]).mean()
            return np.tanh((f - s) / (kap * sd * np.sqrt(p["yavas"])))
        if p["sinyal"] == "tsmom":
            return np.sign(tk.mom(p["tsmom_gun"])[kolon])
        if p["sinyal"] == "sma":
            return np.sign(kap - kap.rolling(p["yavas"], min_periods=p["yavas"]).mean())
        raise ValueError("sinyal ewmac, tsmom ya da sma olmalı")

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        ax = tk.eksen
        sg = self._sinyal(tk, kolon)
        if p["yon"] == "long":
            sg = sg.clip(lower=0.0)
        S = tk.eksene(sg).to_numpy(dtype=float)
        sd = tk.vol(p["vol_gun"])[kolon]
        SD = tk.eksene(sd).to_numpy(dtype=float)
        gecerli = (np.isfinite(S) & np.isfinite(SD)).sum(axis=1) >= 1
        tetik = tetik_satirlari(ax, p["takvim"], gecerli)
        gunluk_hedef = p["hedef_vol"] / np.sqrt(365.0)
        grid_no = tk.gun.get_indexer(ax)
        R = tk.getiri()[kolon].to_numpy(dtype=float)

        def agirlik(i):
            ok = np.isfinite(S[i]) & np.isfinite(SD[i]) & (SD[i] > 0)
            if not ok.any():
                return {}
            if p["birlesim"] == "bagimsiz":
                n = ok.sum()
                w = np.where(ok, S[i] / np.where(SD[i] > 0, SD[i], np.inf) * gunluk_hedef / n, 0.0)
            else:
                j = np.flatnonzero(ok)
                pencere = R[max(0, grid_no[i] - p["vol_gun"] + 1):grid_no[i] + 1][:, j]
                kov = pd.DataFrame(pencere).cov().to_numpy()
                if not np.isfinite(kov).all():
                    return {}
                kov = (1.0 - p["buzulme"]) * kov + p["buzulme"] * np.diag(np.diag(kov))
                mu = S[i][j] * SD[i][j]
                try:
                    ham = np.linalg.solve(kov + 1e-12 * np.eye(len(j)), mu)
                except np.linalg.LinAlgError:
                    return {}
                pv = float(np.sqrt(max(ham @ kov @ ham, 0.0)))
                if pv <= 0:
                    return {}
                w = np.zeros(len(kolon))
                w[j] = ham * gunluk_hedef / pv
            w = np.clip(w, -1.0, 1.0)
            return dict(zip(kolon, w))

        return dongusel_hedef(ax, kolon, tetik, agirlik)
