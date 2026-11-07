"""D12b göstergeleri: nedensel (tek taraflı) Hodrick-Prescott filtresi.

Klasik HP filtresi iki taraflıdır: t anındaki trend değeri t'den SONRAKİ verilere de bağlıdır (lookahead). Burada her bar
yalnız kendisine kadar olan `pencere` kadar veriyle, o pencerede klasik HP çözülüp pencerenin SON noktası alınır
(tek taraflı / kayan pencere sürümü). HP çözümü doğrusal olduğundan pencerenin son noktası sabit bir ağırlık vektörüyle
verinin ağırlıklı toplamıdır: w = (I + lambda D'D)^-1 sütunlarının son satırı; trend[t] = w . y[t-pencere+1..t].
Böylece O(n * pencere) maliyetle hesaplanır ve her bar yalnız geçmişi görür.
"""
import numpy as np
import pandas as pd


def hp_son_nokta_agirliklari(pencere: int, lamb: float) -> np.ndarray:
    """Uzunluğu `pencere` olan HP penceresinin son noktasının trend ağırlıkları (toplam 1)."""
    if pencere < 4:
        raise ValueError("HP pencere >= 4 olmalı")
    if lamb <= 0:
        raise ValueError("HP lambda > 0 olmalı")
    d = np.zeros((pencere - 2, pencere))
    for i in range(pencere - 2):
        d[i, i:i + 3] = (1.0, -2.0, 1.0)
    a = np.eye(pencere) + lamb * d.T @ d
    e = np.zeros(pencere)
    e[-1] = 1.0
    return np.linalg.solve(a, e)          # A simetrik: son satır = son sütun


def hp_nedensel(seri: pd.Series, lamb: float = 1600.0, pencere: int = 100) -> pd.Series:
    """Nedensel HP trend bileşeni (ilk pencere-1 bar NaN; pencere içinde NaN varsa NaN)."""
    w = hp_son_nokta_agirliklari(int(pencere), float(lamb))
    y = seri.to_numpy(dtype=float)
    n = len(y)
    cikti = np.full(n, np.nan)
    if n >= pencere:
        kayan = np.lib.stride_tricks.sliding_window_view(y, int(pencere))
        cikti[pencere - 1:] = kayan @ w
    return pd.Series(cikti, index=seri.index)
