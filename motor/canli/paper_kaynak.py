"""Paper motoru veri kaynağı arayüzü ve bellek-içi kaynak (tekrar modu + canlı önbellek tabanı).

`TekrarKaynagi`: {(sembol, tf): mum DataFrame} ve {sembol: funding DataFrame} tutar. Tekrar modunda geçmiş mumlar sırayla
"canlıymış gibi" verilir (satırlar: kapanışı `simdi`den önce/eşit olanlar). Canlı kaynak (paper_canli.CanliKaynak) aynı sınıfı
genişletir: çerçeveler REST ile büyütülür, satır mantığı AYNIDIR (tekrar modu gerçek yolu sınar).
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from motor.veri.depo import aralik_suresi

MUM_SUTUNLARI = ("acilis", "yuksek", "dusuk", "kapanis")


class TekrarKaynagi:
    def __init__(self, mumlar: dict, fundingler: Optional[dict] = None, pencere: Optional[dict] = None):
        """mumlar: {(sembol, tf): DataFrame (UTC açılış indeksi, acilis/yuksek/dusuk/kapanis/...)}.
        pencere: {tf: son N bar} (None: tüm geçmiş; tekrar-modu eşleşme testi tüm geçmişle koşar)."""
        self.mumlar = {k: v for k, v in mumlar.items()}
        self.fundingler = dict(fundingler or {})
        self.pencere = pencere or {}

    # ------------------------------------------------------------------ satırlar
    def _eksen(self, birim, son_t, simdi) -> pd.DatetimeIndex:
        idx = None
        for s in birim.semboller:
            df = self.mumlar[(s, birim.tf)]
            ix = df.index
            idx = ix if idx is None else idx.union(ix)
        idx = idx.sort_values()
        k = idx[(idx + birim.aralik) <= simdi]
        if son_t is not None:
            k = k[k > son_t]
        return k

    def satirlar(self, birim, son_t, simdi) -> list:
        """Birimin işlenmemiş, KAPANMIŞ satırları: [(t_acilis, {sembol: (o,h,l,c) | None})]."""
        out = []
        eks = self._eksen(birim, son_t, simdi)
        if not len(eks):
            return out
        tablo = {}
        for s in birim.semboller:
            df = self.mumlar[(s, birim.tf)]
            alt = df.loc[df.index.isin(eks), list(MUM_SUTUNLARI)]
            tablo[s] = {t: tuple(r) for t, r in zip(alt.index, alt.to_numpy(dtype=float))}
        for t in eks:
            out.append((t, {s: tablo[s].get(t) for s in birim.semboller}))
        return out

    def gec_barlar(self, birim) -> list:
        """Satırı bekleme süresi dolduktan sonra gelen mumlar: [(t_acilis, sembol, (o,h,l,c))]. Tekrar modunda tüm veri baştan var: boş."""
        return []

    def son_satir(self, birim, simdi) -> Optional[tuple]:
        """Kapanışı <= simdi olan en son satır (başlangıç kararı için)."""
        idx = None
        for s in birim.semboller:
            ix = self.mumlar[(s, birim.tf)].index
            idx = ix if idx is None else idx.union(ix)
        idx = idx.sort_values()
        k = idx[(idx + birim.aralik) <= simdi]
        if not len(k):
            return None
        t = k[-1]
        row = {}
        for s in birim.semboller:
            df = self.mumlar[(s, birim.tf)]
            row[s] = tuple(df.loc[t, list(MUM_SUTUNLARI)].to_numpy(dtype=float)) if t in df.index else None
        return t, row

    # ------------------------------------------------------------------ strateji girdisi
    def gecmis(self, sembol: str, tf: str, t) -> pd.DataFrame:
        """Mumlar <= t (t dahil: kapanmış bar). Pencere varsa son N bar."""
        df = self.mumlar[(sembol, tf)]
        j = df.index.searchsorted(t, side="right")
        n = self.pencere.get(tf)
        i = max(0, j - n) if n else 0
        return df.iloc[i:j]

    def funding_df(self, sembol: str) -> Optional[pd.DataFrame]:
        return self.fundingler.get(sembol)

    # ------------------------------------------------------------------ motor besleme
    def en_ince_tf(self, sembol: str) -> Optional[str]:
        tfler = [tf for (s, tf) in self.mumlar if s == sembol]
        return min(tfler, key=aralik_suresi) if tfler else None

    def fiyat_dizisi(self, sembol: str):
        tf = self.en_ince_tf(sembol)
        df = self.mumlar[(sembol, tf)]
        return df.index, df["acilis"].to_numpy(dtype=float)

    def funding_dizisi(self, sembol: str):
        f = self.fundingler.get(sembol)
        if f is None or not len(f):
            return pd.DatetimeIndex([], tz="UTC"), np.array([], dtype=float)
        return f.index, f["oran"].to_numpy(dtype=float)

    def son_mum_zamani(self, sembol: str, tf: str) -> Optional[pd.Timestamp]:
        df = self.mumlar.get((sembol, tf))
        return df.index[-1] if df is not None and len(df) else None
