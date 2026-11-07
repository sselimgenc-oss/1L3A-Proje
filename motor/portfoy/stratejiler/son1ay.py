"""Son 1 ay açık kaynak adayları — portföy kolu (stratejiler/ek_kaynaklar/son1ay_2026-11.md). KOD KOPYALANMADI.

pf__son1ay_trendrider — hassannazir2536/TrendRider (lisans belirtilmemiş), "günlük 50 MA coin rotasyonu"
  Kural (kaynak strateji dosyası + README): coin'in günlük kapanışı SMA(sma_gun=50) üstündeyse o coinin dilimini tut, değilse nakit
  (USDT). Sinyal günlük, yeniden dengeleme günlük. Kaynakta 'rotasyon' yok: her coin kendi trend filtresinin açık/kapalı durumudur;
  dilimler sabittir (nakit diğer coinlere AKTARILMAZ). Ağırlıklar: "kademeli" = kaynağın varsayılan config'i (BTC %30, ETH %20, diğer
  coinler %12.5; toplam azami maruziyet 3 coinde %62.5); "esit" = 1/n. Kaynak -%15 felaket stopu (borsada) -> iz_stop_yuzde=0.15.
  Fark: kaynak evreni BTC/ETH/XRP/SOL/DOGE/TRX (6 coin); bizde karar 22 evreni BTC/ETH/SOL. Kaynakta reddedilen (2 gün onay, 20 gün
  çıkış, iz süren stop, vol boyutlama) eklenmedi. Not: `pf__trend_sepet` (sma_gun, takvim=D, nakitli) "esit" kolunun aynısıdır;
  buradaki katkı kademeli ağırlık + %15 stop + 20/50/100 komşuluğu.

pf__son1ay_e014 — Bederf/leah-freqtrade-strategies (MIT), "E014 makro rotasyon SPY/TLT/GLD"
  Kaynakta KOD YOK; yalnız README: "SPY / TLT / GLD 25 haftalık momentum", haftalık, üç varlıktan BİRİ seçilir. Mutlak momentum
  filtresi, yeniden dengeleme günü, ücret, pencere yöntemi YAZILMAMIŞ. Bu sınıf yalnız belgelenen kuralı uygular: haftalık (W)
  yeniden dengeleme, skor = 25 hafta (175 takvim günü) getirisi, en iyi k=1 varlık %100. `mutlak` (en iyi skor <= 0 ise nakit)
  kaynakta belirtilmediği için ızgarada False/True ikisi de denenir (varsayılan False = "üçünden biri her zaman").
  Vekiller (Dukascopy): SPY -> DK_SPX (S&P 500 endeks CFD'si, USA500IDXUSD), TLT -> DK_UST (ABD T-Bond CFD'si, USTBONDTRUSD),
  GLD -> DK_XAU. CFD/endeks serisi ETF toplam getirisi (temettü/faiz) içermez; DK_UST tahvil vadeli CFD'sidir (TLT'den farklı vade ve
  taşıma).
"""
from __future__ import annotations

import numpy as np

from motor.portfoy.stratejiler.ortak import KRIPTO, ORTAK_PARAMETRELER, PfTemel, dongusel_hedef, sma_gun, tetik_satirlari
from motor.portfoy.stratejiler.rotasyon import Rotasyon

MAKRO = ("DK_SPX", "DK_UST", "DK_XAU")
KADEMELI = {"BTCUSDT": 0.30, "ETHUSDT": 0.20, "SOLUSDT": 0.125}


class SonBirAyTrendRider(PfTemel):
    ad = "pf__son1ay_trendrider"
    min_sembol = 1
    varsayilan_parametreler = {**ORTAK_PARAMETRELER, "atr_k": 3.0, "iz_stop_yuzde": 0.15, "semboller": KRIPTO,
                               "sma_gun": 50, "agirlik": "kademeli", "takvim": "D"}
    parametre_izgarasi = {"sma_gun": [20, 50, 100], "agirlik": ["esit", "kademeli"], "iz_stop_yuzde": [0.15, 0.25]}

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        kap = tk.kap[kolon]
        sm = sma_gun(kap, int(p["sma_gun"]))
        ust = tk.eksene(kap > sm).fillna(False).to_numpy(dtype=bool)
        hazir = tk.eksene(sm.notna()).fillna(False).to_numpy(dtype=bool)
        tetik = tetik_satirlari(tk.eksen, p["takvim"], hazir.any(axis=1))
        if p["agirlik"] not in ("esit", "kademeli"):
            raise ValueError("agirlik 'esit' ya da 'kademeli' olmalı")

        def agirlik(i):
            n = max(len(kolon), 1)
            w = {}
            for j, c in enumerate(kolon):
                if ust[i, j] and hazir[i, j]:
                    w[c] = (1.0 / n) if p["agirlik"] == "esit" else KADEMELI.get(c, 0.125)
            return w

        return dongusel_hedef(tk.eksen, kolon, tetik, agirlik)


class SonBirAyE014(Rotasyon):
    ad = "pf__son1ay_e014"
    min_sembol = 2
    varsayilan_parametreler = {**Rotasyon.varsayilan_parametreler, "semboller": MAKRO, "skor": "getiri",
                               "lookback_gun": 175, "k": 1, "takvim": "W", "mutlak": False}
    parametre_izgarasi = {"lookback_gun": [126, 175, 252], "mutlak": [False, True], "k": [1, 2]}
