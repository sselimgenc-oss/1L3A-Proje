"""Strateji arayüzü.

sinyaller(mumlar) vektörel çalışır ve mumlarla AYNI indeksli bir DataFrame döner:
  yon               1 long, -1 short, 0 yok
  stop              fiyat; yon != 0 ise zorunlu
  hedef             fiyat veya NaN
  cikis             bool: açık pozisyonu kapat
  zaman_cikisi_mum  (opsiyonel) int/NaN
Sinyal mum KAPANIŞINDA hesaplanır; motor bir sonraki mumun açılışında işlem yapar.
Gelecek verisine bakmak (lookahead) yasaktır.
"""
from abc import ABC, abstractmethod

import pandas as pd

from motor.strateji.cikislar import CikisAyarlari

SINYAL_SUTUNLARI = ["yon", "stop", "hedef", "cikis"]


class Strateji(ABC):
    ad: str = ""
    stil: str = ""
    varsayilan_parametreler: dict = {}
    parametre_izgarasi: dict = {}   # {parametre: [değerler]} — walk-forward için
    cikis_ayarlari: CikisAyarlari = CikisAyarlari()

    def __init__(self, cikis_ayarlari: CikisAyarlari = None, **parametreler):
        bilinmeyen = set(parametreler) - set(self.varsayilan_parametreler)
        if bilinmeyen:
            raise ValueError(f"Bilinmeyen parametre: {sorted(bilinmeyen)}")
        self.parametreler = {**self.varsayilan_parametreler, **parametreler}
        if cikis_ayarlari is not None:
            self.cikis_ayarlari = cikis_ayarlari

    def yeni(self, **parametreler) -> "Strateji":
        """Aynı yapılandırmada, bazı parametreleri değişmiş kopya (walk-forward için)."""
        return type(self)(cikis_ayarlari=self.cikis_ayarlari, **{**self.parametreler, **parametreler})

    def cikis_var_mi(self) -> bool:
        """Strateji mevcut parametreleriyle kendi hedefini veya `cikis` sinyalini üretiyor mu?
        Üretmiyorsa (False) ve CikisAyarlari'nda da çıkış yoksa backtest() ValueError verir."""
        return False

    @abstractmethod
    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        ...
