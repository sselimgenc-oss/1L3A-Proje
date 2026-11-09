"""v2 YENİ ADAYLARI (ON_KAYIT_V2 2.8): varlık sınıfı İÇİ kesitsel long/short (momentum ve kısa vadeli dönüş).

ÖN TANIM (hiçbir backtest görülmeden yazıldı; varsayılan ayar tek ana deneme, ızgara yalnız S2 komşu kontrolü):

pf__sinif_kesit_mom  — kesitsel 12-1 ay momentum.
  Fikir (genel literatür): Jegadeesh-Titman (1993) kesitsel momentum; Asness-Moskowitz-Pedersen (2013) "Value and
  Momentum Everywhere" (momentum varlık sınıfları İÇİNDE sıralanır). Skor = kapanış[t-30g] / kapanış[t-365g] - 1 (son ay atlanır).
  Aylık ("M") yeniden dengeleme.
pf__sinif_kesit_donus — kesitsel 1 hafta kısa vadeli dönüş.
  Fikir: Jegadeesh (1990), Lehmann (1990) haftalık/aylık kısa vadeli dönüş. Skor = -(kapanış[t] / kapanış[t-7g] - 1);
  kaybedenler long, kazananlar short. Haftalık ("W") yeniden dengeleme.

Ortak kural: sınıflar (kripto 3, ABD hisse 7, emtia 3; ortak.KRIPTO/HISSE/EMTIA) AYRI AYRI sıralanır; sınıf başına en iyi
k long, en kötü k short, k = max(1, floor(n * kuyruk)) (<= n//2; kuyruk=1/3: 3 sembolde 1, 7 sembolde 2). Her sınıfta
long ve short toplamı eşit (dolar-nötr); bacak başı brüt `brut`/2, geçerli (>= 2 sembollü) sınıflara eşit bölünür. Sınıf
içi ağırlık eşit. SHORT AÇAR. Stop: ortak ATR felaket stopu (PfTemel: kapanış -/+ atr_k x ATR(14), motor yalnız
sıkılaştırır); işlem riski/brüt/günlük/kill motorda sert limitlerle uygulanır (karar 24/25 bütçe kuralları aynen).
Nedensellik: skor satır t'nin kapanışına kadar olan mumlardan; yeniden dengeleme dönem değişimi satırında (ortak.tetik_satirlari).
Evren küçük (3-13 sembol); sonuçlar gürültülüdür (KesitLS ile aynı uyarı). Kod başka bir depodan kopyalanmadı.
"""
from __future__ import annotations

import numpy as np

from motor.portfoy.stratejiler.ortak import (EMTIA, HEPSI, HISSE, KRIPTO, ORTAK_PARAMETRELER, PfTemel,
                                             dongusel_hedef, tetik_satirlari)

SINIFLAR_VARLIK = (KRIPTO, HISSE, EMTIA)


class _SinifIciKesit(PfTemel):
    min_sembol = 2

    def _skor(self, tk):
        """DataFrame (takvim ızgarası): yüksek skor = long. Alt sınıf yazar."""
        raise NotImplementedError

    def _hedef(self, ev, tk):
        p = self.parametreler
        kolon = list(ev)
        S = tk.eksene(self._skor(tk)[kolon]).to_numpy(dtype=float)
        gruplar = [[j for j, c in enumerate(kolon) if c in sinif] for sinif in SINIFLAR_VARLIK]
        gruplar = [g for g in gruplar if len(g) >= 2]
        gecerli = np.zeros(len(S), dtype=bool)
        for g in gruplar:
            gecerli |= np.isfinite(S[:, g]).sum(axis=1) >= 2
        tetik = tetik_satirlari(tk.eksen, p["takvim"], gecerli)

        def agirlik(i):
            uyeler = [[j for j in g if np.isfinite(S[i, j])] for g in gruplar]
            uyeler = [u for u in uyeler if len(u) >= 2]
            w = {}
            for u in uyeler:
                n = len(u)
                k = max(1, min(int(np.floor(n * p["kuyruk"] + 1e-9)), n // 2))
                sirali = sorted(u, key=lambda j: (-S[i, j], j))          # eşitlikte sütun sırası (kararlı)
                pay = p["brut"] / 2.0 / len(uyeler) / k
                for j in sirali[:k]:
                    w[kolon[j]] = pay
                for j in sirali[-k:]:
                    w[kolon[j]] = -pay
            return w

        return dongusel_hedef(tk.eksen, kolon, tetik, agirlik)


class SinifIciKesitMom(_SinifIciKesit):
    """Sınıf içi kesitsel momentum L/S (varsayılan 12-1 ay, aylık). Ayrıntı: modül açıklaması."""

    ad = "pf__sinif_kesit_mom"
    varsayilan_parametreler = {**ORTAK_PARAMETRELER, "semboller": HEPSI, "lookback_gun": 365, "atla_gun": 30,
                               "kuyruk": 1.0 / 3.0, "takvim": "M", "brut": 1.0}
    parametre_izgarasi = {"lookback_gun": [180, 270, 365], "atla_gun": [0, 30]}

    def _skor(self, tk):
        p = self.parametreler
        return tk.mom(int(p["lookback_gun"]), int(p["atla_gun"]))


class SinifIciKesitDonus(_SinifIciKesit):
    """Sınıf içi kesitsel kısa vadeli dönüş L/S (varsayılan 7 gün, haftalık). Ayrıntı: modül açıklaması."""

    ad = "pf__sinif_kesit_donus"
    varsayilan_parametreler = {**ORTAK_PARAMETRELER, "semboller": HEPSI, "lookback_gun": 7,
                               "kuyruk": 1.0 / 3.0, "takvim": "W", "brut": 1.0}
    parametre_izgarasi = {"lookback_gun": [3, 7, 14], "takvim": ["D", "W"]}

    def _skor(self, tk):
        return -tk.mom(int(self.parametreler["lookback_gun"]))
