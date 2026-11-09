"""Portföy stratejileri için ortak altyapı (karar 23).

Takvim günü ilkesi
  Tüm geri bakış pencereleri TAKVİM GÜNÜ cinsindendir ("365" = 12 ay). Hesaplar, mum eksenindeki 1d mumlardan kurulan
  GÜNLÜK TAKVİM IZGARASINDA yapılır (kapanış: ileri doldurulmuş = yalnız geçmiş; yüksek/düşük/açılış: ileri
  doldurulmaz). Hisse/emtia hafta sonu gün sayısı kripto ile aynı olur; "300 günlük SMA" her sembolde aynı süredir.
  Sonuç, motorun ortak zaman eksenindeki satırlara (aynı UTC günü) taşınır. Eksen mumları 00:00 UTC'de olmalıdır
  (yalnız 1d); aksi halde ValueError.

Yeniden dengeleme takvimi
  `takvim`: "D" günlük, "W" haftalık (Pazartesi başlangıçlı), "M" aylık, "Q" çeyreklik, "Y" yıllık ya da bir tam sayı
  N (N günde bir; dönem kimliği = epoch_gün // N -> veri başlangıcından BAĞIMSIZ). Yeniden dengeleme satırı = yeni
  dönemin eksendeki İLK satırı (dönem değişimi önceki satırdan bilinir -> nedensel). İlk geçerli satır da bir
  yeniden dengelemedir.

Stoplar (zorunlu): varsayılan ATR felaket stopu = kapanış -/+ atr_k * ATR(atr_periyot) (long/short), iz süren
(motor yalnız sıkılaştırır). `iz_stop_yuzde` > 0 ise stop = kapanış * (1 -/+ yüzde). Hedefi sıfırdan farklı olan
her satırda ATR hazır olmalıdır; hazır değilse o sembolün hedefi 0'a çekilir (stopsuz pozisyon açılmaz).

NOT (motor etkisi): motor işlem başı riski %1 ile sınırlar; stop mesafesi geniş oldukça ağırlık küçülür
(w <= %1 / stop_mesafesi). Bu sert limitin doğal sonucudur, strateji bunu aşamaz.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from motor.portfoy.temel import PortfoyStratejisi, atr_tablosu, ortak_eksen

# Test evreni (karar 22)
KRIPTO = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
HISSE = ("DK_AAPL", "DK_MSFT", "DK_GOOGL", "DK_AMZN", "DK_NVDA", "DK_META", "DK_TSLA")
EMTIA = ("DK_XAU", "DK_WTI", "DK_COPPER")
HEPSI = KRIPTO + HISSE + EMTIA

ORTAK_PARAMETRELER = {"atr_k": 3.0, "atr_periyot": 14, "iz_stop_yuzde": 0.0}


# ------------------------------------------------------------------ takvim ızgarası
class Takvim:
    """Günlük takvim ızgarası üzerinde panel hesapları (bkz. modül docstring'i)."""

    def __init__(self, veriler: dict, baslangic: dict | None = None):
        """baslangic: {sembol: ilk kullanılabilir zaman}; bu zamandan önceki satırlar tüm panellerde NaN (ör. ATR'nin
        hazır olduğu ilk bar: stopsuz pozisyon açılamayacağından sembol o zamana dek 'veri yok' sayılır)."""
        self.veriler = veriler
        self.baslangic = baslangic or {}
        self.eksen = ortak_eksen(veriler)
        if not (self.eksen == self.eksen.floor("D")).all():
            raise ValueError("portföy stratejileri yalnız 1d mumlarla (00:00 UTC) çalışır")
        self.gun = pd.date_range(self.eksen[0], self.eksen[-1], freq="D", tz="UTC", name="zaman")
        self._onbellek: dict = {}

    def panel(self, alan: str = "kapanis", doldur: bool | None = None) -> pd.DataFrame:
        """Izgara üzerinde sembol sütunlu tablo. doldur=None: kapanış ileri doldurulur, diğer alanlar doldurulmaz."""
        doldur = (alan == "kapanis") if doldur is None else doldur
        k = (alan, doldur)
        if k not in self._onbellek:
            t = pd.DataFrame({s: df[alan].reindex(self.gun) for s, df in self.veriler.items()})
            for s, b in self.baslangic.items():
                if s in t.columns:
                    t[s] = t[s].where(t.index >= b) if b is not None else np.nan
            self._onbellek[k] = t.ffill() if doldur else t
        return self._onbellek[k]

    @property
    def kap(self) -> pd.DataFrame:
        return self.panel("kapanis")

    def getiri(self) -> pd.DataFrame:
        """Günlük (takvim) getiri; veri yoksa NaN."""
        return self.kap.pct_change(fill_method=None)

    def mom(self, gun: int, atla: int = 0) -> pd.DataFrame:
        """kap[t-atla] / kap[t-gun] - 1 (takvim günü)."""
        return self.kap.shift(atla) / self.kap.shift(gun) - 1.0

    def vol(self, gun: int) -> pd.DataFrame:
        return self.getiri().rolling(gun, min_periods=max(5, int(gun * 0.7))).std()

    def eksene(self, df: pd.DataFrame | pd.Series):
        """Izgara tablosunu motor eksenine taşı (aynı UTC günü)."""
        return df.reindex(self.eksen)


# ------------------------------------------------------------------ yeniden dengeleme takvimi
def donem_kimligi(eksen: pd.DatetimeIndex, takvim) -> np.ndarray:
    t = str(takvim)
    gun = (eksen.floor("D") - pd.Timestamp("1970-01-01", tz="UTC")).days.to_numpy().astype(np.int64)
    if t.isdigit():
        n = int(t)
        if n < 1:
            raise ValueError("takvim gün sayısı >= 1 olmalı")
        return gun // n
    if t == "D":
        return gun
    if t == "W":
        return (gun + 3) // 7                       # 1970-01-01 Perşembe -> +3 ile Pazartesi başlangıçlı hafta
    yil, ay = eksen.year.to_numpy().astype(np.int64), eksen.month.to_numpy().astype(np.int64)
    if t == "M":
        return yil * 12 + ay
    if t == "Q":
        return yil * 4 + (ay - 1) // 3
    if t == "Y":
        return yil
    raise ValueError("takvim D, W, M, Q, Y ya da gün sayısı olmalı")


def tetik_satirlari(eksen: pd.DatetimeIndex, takvim, gecerli: np.ndarray) -> np.ndarray:
    """Yeniden dengeleme satırları (bool dizi): dönem değişimi VEYA ilk geçerli satır. gecerli: satır başına bool
    (stratejinin karar verebildiği satırlar). Dönem değişimi gecerli olmayan bir satıra denk gelirse, ilk geçerli
    satır dönem içindeyken de tetiklenir."""
    kimlik = donem_kimligi(eksen, takvim)
    degisim = np.r_[False, kimlik[1:] != kimlik[:-1]]
    gecerli = np.asarray(gecerli, dtype=bool)
    ilk = np.zeros(len(eksen), dtype=bool)
    if gecerli.any():
        ilk[int(np.argmax(gecerli))] = True
    return (degisim | ilk) & gecerli


def en_iyi_k(skor: pd.Series, k: int, buyuk_iyi: bool = True) -> list:
    """Geçerli (NaN olmayan) skorlardan en iyi k etiket; eşitlikte sütun sırası (kararlı)."""
    s = skor.dropna()
    if s.empty or k <= 0:
        return []
    s = s.iloc[np.argsort(-s.to_numpy() if buyuk_iyi else s.to_numpy(), kind="stable")]
    return list(s.index[:k])


def sma_gun(kap: pd.DataFrame, gun: int) -> pd.DataFrame:
    return kap.rolling(gun, min_periods=gun).mean()


def ema_gun(kap: pd.DataFrame, gun: int) -> pd.DataFrame:
    return kap.ewm(span=gun, adjust=False, min_periods=gun).mean()


# ------------------------------------------------------------------ taban sınıf
class PfTemel(PortfoyStratejisi):
    """Portföy stratejileri tabanı. Alt sınıf `_hedef(ev, takvim)` yazar: ortak_eksen(ev) indeksli, sembol sütunlu
    hedef ağırlık tablosu (NaN = değişiklik yok). Alt evren `semboller` parametresiyle seçilir; alt sınıfın
    `min_sembol` değerinden az sembol varsa ValueError."""

    ad = ""
    kaynak = ""
    min_sembol = 1
    varsayilan_parametreler: dict = {}
    parametre_izgarasi: dict = {}

    # --- alt evren
    def ek_semboller(self) -> tuple:
        """Alım-satım evreni DIŞINDA ama veri olarak gereken semboller (rejim/referans). Alt sınıf geçersiz kılar."""
        return ()

    def evren(self, veriler: dict) -> dict:
        sec = [s for s in self.parametreler["semboller"] if s in veriler]
        if len(sec) < self.min_sembol:
            raise ValueError(f"{self.ad}: en az {self.min_sembol} sembol gerekli, evrende {len(sec)} var "
                             f"(istenen: {list(self.parametreler['semboller'])})")
        return {s: veriler[s] for s in sec}

    def _tum(self, veriler: dict) -> tuple:
        """-> (ev, tum): ev = alım-satım evreni, tum = ev + ek semboller (rejim/referans verisi)."""
        ev = self.evren(veriler)
        eksik = [s for s in self.ek_semboller() if s and s not in veriler]
        if eksik:
            raise ValueError(f"{self.ad}: gerekli ek semboller veride yok: {eksik}")
        tum = dict(ev)
        for s in self.ek_semboller():
            if s and s not in tum:
                tum[s] = veriler[s]
        return ev, tum

    def etkin_semboller(self, mevcut) -> tuple:
        return tuple(s for s in self.parametreler["semboller"] if s in set(mevcut))

    def uygun_mu(self, mevcut) -> bool:
        mevcut = set(mevcut)
        return (len(self.etkin_semboller(mevcut)) >= self.min_sembol
                and all((not s) or s in mevcut for s in self.ek_semboller()))

    # --- hedefler / stoplar
    def hedefler(self, veriler: dict) -> pd.DataFrame:
        ev, tum = self._tum(veriler)
        atr_tum = atr_tablosu(tum, self.parametreler["atr_periyot"])
        tk = Takvim(tum, {s: atr_tum[s].first_valid_index() for s in tum})        # ATR hazır olana dek sembol yok sayılır
        h = self._hedef(ev, tk)
        h = h.reindex(index=tk.eksen, columns=list(ev))
        atr = atr_tum[list(ev)].reindex(tk.eksen).ffill()
        acik = h.notna() & (h != 0)
        h = h.mask(acik & atr.isna(), 0.0)
        return h

    def _hedef(self, ev: dict, tk: Takvim) -> pd.DataFrame:  # pragma: no cover
        raise NotImplementedError

    def stoplar(self, veriler: dict, hedefler: pd.DataFrame) -> pd.DataFrame:
        ev, tum = self._tum(veriler)
        p = self.parametreler
        eksen = ortak_eksen(tum)
        kap = pd.DataFrame({s: df["kapanis"].reindex(eksen) for s, df in ev.items()}).ffill()
        atr = atr_tablosu(ev, p["atr_periyot"]).reindex(eksen).ffill()
        # nedensel: yalnız o satıra kadar verilmiş hedefler
        yon = np.sign(hedefler.reindex(index=eksen, columns=list(ev)).ffill().fillna(0.0))
        if p["iz_stop_yuzde"] > 0:
            stop = kap * (1.0 - yon * p["iz_stop_yuzde"])
        else:
            stop = kap - yon * p["atr_k"] * atr
        stop = stop.where(yon != 0)
        return stop.reindex(hedefler.index)


def dongusel_hedef(eksen, kolonlar, tetik: np.ndarray, agirlik_fn) -> pd.DataFrame:
    """Tetik satırlarında agirlik_fn(i) -> Series(kolon -> ağırlık, eksik = 0) çağırıp hedef tablosunu kurar."""
    h = np.full((len(eksen), len(kolonlar)), np.nan)
    for i in np.flatnonzero(tetik):
        w = agirlik_fn(i)
        satir = np.zeros(len(kolonlar))
        for j, c in enumerate(kolonlar):
            satir[j] = float(w.get(c, 0.0))
        h[i] = satir
    return pd.DataFrame(h, index=eksen, columns=list(kolonlar))


def degisim_satirlari(w: pd.DataFrame, esik: float = 1e-9) -> pd.DataFrame:
    """Durum tablosu (her satır hedef ağırlık) -> yalnız değişen satırlarda dolu emir tablosu (diğerleri NaN).
    Satır, herhangi bir sembolün hedefi bir önceki satıra göre değiştiyse tamamen yazılır (ilk satır dahil, sıfırdan
    farklıysa)."""
    onceki = w.shift(1).fillna(0.0)
    degisti = ((w.fillna(0.0) - onceki).abs() > esik).any(axis=1)
    maske = pd.DataFrame(np.repeat(degisti.to_numpy()[:, None], w.shape[1], axis=1), index=w.index, columns=w.columns)
    return w.where(maske)
