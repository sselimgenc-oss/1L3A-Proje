"""Kaldıraç senaryoları: swing sistemi (S1+S2+S3) aynı işlemlerle, farklı kaldıraç kullanımıyla.

İki kullanım biçimi:
  A) Aynı risk (%1/işlem), kaldıraç yalnız teminatı azaltır  -> sonuç aynı, yalnız fonlama maliyeti ve tasfiye riski eklenir.
  B) Kaldıraçla büyütme: işlem riski ve pozisyon büyüklüğü L katı (risk = L x %1, toplam maruziyet <= L).
Her iki biçimde: kripto vadelide fonlama maliyeti (günlük %0,03 nominal üzerinden, ~yıllık %11) ve
izole teminatta tasfiye: tasfiye mesafesi (1/L - %0,5) stop mesafesinden kısaysa ve işlem içinde fiyat o kadar
düştüyse pozisyon tasfiye edilir (getiri = -1/L - maliyet). Hisse/emtia: fonlama yıllık %6 (günlük %0,016).
"""
import sys
from copy import copy
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from swing.ayarlar import S1, S2, S3, SINIFLAR  # noqa: E402
from swing.calistir import OOS_BASLANGIC, islemler, veriler  # noqa: E402
from swing.motor import portfoy  # noqa: E402

FON = {"kripto": 0.0003, "mag7": 0.00016, "emtia": 0.00016, "bist": 0.0004}


def mae_ekle(tr):
    V = veriler()
    for t in tr:
        df = V[t.varlik][0]
        p = df.loc[t.giris_tarih:t.cikis_tarih]
        t.mae = max(0.0, 1 - p["Low"].min() / t.giris) if len(p) else 0.0
        t.stop_mes = abs(t.giris - t.stop0) / t.giris
    return tr


def uyarla(tr, L, fonlama=True, tasfiye=True):
    out, tasf, kazanan_tasf = [], 0, 0
    for t in tr:
        u = copy(t)
        if fonlama and L > 1:
            u.getiri -= FON[t.sinif] * t.gun * (1 - 1 / L)  # borçlanılan kısım üzerinden
        liq = 1 / L - 0.005
        if tasfiye and L > 1 and liq < t.stop_mes and t.mae >= liq:
            tasf += 1
            kazanan_tasf += t.getiri > 0
            u.getiri = -1 / L - 0.002
        out.append(u)
    return out, tasf, kazanan_tasf


def ozet(tr, risk, ag, top):
    p = portfoy(tr, risk=risk, max_agirlik=ag, max_toplam=top)
    o = portfoy([t for t in tr if t.giris_tarih >= OOS_BASLANGIC], risk=risk, max_agirlik=ag, max_toplam=top)
    y22 = portfoy([t for t in tr if t.giris_tarih.year == 2022], risk=risk, max_agirlik=ag, max_toplam=top)
    return p, o, y22


if __name__ == "__main__":
    tr = []
    for s, prm in (("S1_geri_cekilme", S1), ("S2_kirilim", S2), ("S3_asiri_satim", S3)):
        tr += islemler(s, prm, SINIFLAR[s])
    tr = mae_ekle(tr)
    kr = [t for t in tr if t.sinif == "kripto"]
    print(f"Kripto işlemlerinde stop mesafesi: medyan %{np.median([t.stop_mes for t in kr])*100:.1f}, "
          f"%75'lik %{np.percentile([t.stop_mes for t in kr], 75)*100:.1f}")
    for L in (2, 3, 5, 10, 20):
        pay = np.mean([t.stop_mes > 1 / L - 0.005 for t in tr])
        print(f"  {L:>2}x: tasfiye mesafesi %{(1/L-0.005)*100:.1f} -> işlemlerin %{pay*100:.0f}'inde stop tasfiyeden uzakta")
    print("\nA) Aynı risk %1, kaldıraç yalnız teminatı azaltır (pozisyonlar aynı)")
    for L in (1, 3, 5, 10, 20):
        u, n, k = uyarla(tr, L)
        p, o, y = ozet(u, 0.01, 0.20, 1.0)
        print(f"  {L:>2}x  yıllık %{p['yillik_getiri']*100:5.1f}  maks.düşüş %{p['max_dusus']*100:6.1f}  Sharpe {p['sharpe_aylik']:.2f} | "
              f"2023+ yıllık %{o['yillik_getiri']*100:5.1f} | tasfiye {n} işlem ({k}'i aslında kârlı kapanacaktı)")
    print("\nB) Kaldıraçla büyütme: risk L x %1, pozisyon ve toplam maruziyet L katı")
    for L in (1, 2, 3, 5, 10):
        u, n, k = uyarla(tr, L)
        p, o, y = ozet(u, 0.01 * L, 0.20 * L, 1.0 * L)
        print(f"  {L:>2}x  yıllık %{p['yillik_getiri']*100:6.1f}  maks.düşüş %{max(p['max_dusus'],-1)*100:6.1f}  Sharpe {p['sharpe_aylik']:.2f} | "
              f"2023+ yıllık %{o['yillik_getiri']*100:6.1f} düşüş %{max(o['max_dusus'],-1)*100:6.1f} | 2022 %{y['toplam_getiri']*100:6.1f} | tasfiye {n}")
