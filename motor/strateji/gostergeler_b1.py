"""B1 ailelerine özgü yardımcılar (paylaşılan gostergeler.py'ye dokunulmaz). Hepsi nedensel.

  GunSonu           day trade karışımı: sinyallere UTC gün sonu zorunlu çıkışını ekler.
  donchian_kanal    önceki n mumun en yüksek/en düşüğü (mevcut mum HARİÇ).
  seans_gap         seans (UTC gün) açılış boşluğu: önceki seans kapanışına göre fark, ATR'si, seans içi mum no.
  gunluk_sma        alt TF mumlardan günlük SMA (htf.ust_zaman ile; değer ertesi gün 00:00'dan itibaren).
  ardisik_sayac     ardışık aynı yönlü mum sayısı (koşu uzunluğu).
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import gun_sonu_uygula, seans_kimligi
from motor.strateji.htf import ust_zaman


class GunSonu:
    """Day trade karışımı. Sınıf `varsayilan_parametreler`ine "seans_saat" koymalı.
    MRO'da parent'tan ÖNCE yazılır: class X(GunSonu, ParentStrateji)."""

    def cikis_var_mi(self) -> bool:
        return True   # seansın son mumunda zorunlu çıkış

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        return gun_sonu_uygula(super().sinyaller(mumlar), self.parametreler["seans_saat"])


def donchian_kanal(yuksek: pd.Series, dusuk: pd.Series, n: int) -> pd.DataFrame:
    """ust/alt: t. satırda mum t'den ÖNCEKİ n mumun en yüksek/en düşüğü."""
    n = int(n)
    return pd.DataFrame({"ust": yuksek.shift(1).rolling(n, min_periods=n).max(),
                         "alt": dusuk.shift(1).rolling(n, min_periods=n).min()})


def seans_gap(mumlar: pd.DataFrame, atr: pd.Series, seans_saat: float = 0.0,
              olcum: str = "acilis") -> pd.DataFrame:
    """Seans açılış boşluğu. Sütunlar (mumlarla aynı indeks):
      seans      seans kimliği (tam sayı gün no)
      mum_no     seansın kaçıncı mumu (1'den)
      onc_kap    bir önceki seansın son kapanışı (ilk seansta NaN)
      acilis     seansın ilk mumunun açılışı
      gap        referans - onc_kap; referans: olcum="acilis" -> seans açılışı,
                 "ilk_bar" -> seansın ilk mumunun KAPANIŞI (ilk mum kapandıktan sonra bilinir; mum_no=1 satırı dahil)
      ref        gap'in referans fiyatı (acilis veya ilk mum kapanışı)
      atr0       seansın ilk mumundaki ATR (seans boyunca sabit; ölçek)
      dusuk_kor / yuksek_kor   "boşluk korunuyor mu" testi için seans içi kümülatif en düşük / en yüksek.
                 olcum="ilk_bar" ise BİRİNCİ MUM HARİÇ (ilk mumun kendisi boşluğu oluşturan hareket; düşüğü açılışın
                 altına, zirvesi üstüne iner ve testi her zaman bozardı); ilk mumda +inf / -inf.
    Kripto 7/24'te bir mumun açılışı önceki mumun kapanışına ~eşit olduğundan olcum="acilis" boşluğu ~0'dır
    (anlamı zayıf); "ilk_bar" ilk mumun hareketini boşluk sayar. Satır t yalnız seans başından t'ye kadar
    (ve bir önceki, tamamen kapanmış seans) bilgisini kullanır."""
    seans = seans_kimligi(mumlar.index, seans_saat)
    gr = mumlar.groupby(seans)
    mum_no = pd.Series(gr.cumcount().to_numpy() + 1, index=mumlar.index)
    acilis = gr["acilis"].transform("first")
    ilk_kap = gr["kapanis"].transform("first")
    onc = gr["kapanis"].last().shift(1).reindex(seans).to_numpy()
    onc = pd.Series(onc, index=mumlar.index)
    ref = acilis if olcum == "acilis" else ilk_kap
    atr0 = atr.where(mum_no == 1).groupby(seans).transform("max")
    maske = (mum_no > 1) if olcum == "ilk_bar" else pd.Series(True, index=mumlar.index)
    dusuk_kor = mumlar["dusuk"].where(maske).groupby(seans).cummin().fillna(np.inf)
    yuksek_kor = mumlar["yuksek"].where(maske).groupby(seans).cummax().fillna(-np.inf)
    return pd.DataFrame({"seans": seans, "mum_no": mum_no, "onc_kap": onc, "acilis": acilis,
                         "ref": ref, "gap": ref - onc, "atr0": atr0, "dusuk_kor": dusuk_kor, "yuksek_kor": yuksek_kor},
                        index=mumlar.index)


def gunluk_sma(mumlar: pd.DataFrame, periyot: int) -> pd.Series:
    """Günlük kapanışların SMA'sı, alt TF indeksine lookahead'siz hizalı (htf.ust_zaman)."""
    s = ust_zaman(mumlar, "1d", lambda u: pd.DataFrame({"sma": g.sma(u["kapanis"], int(periyot))}))
    return s["sma"]


def ardisik_sayac(kosul: pd.Series) -> pd.Series:
    """kosul True olan ardışık mum sayısı (False'ta 0'a döner)."""
    k = kosul.fillna(False).astype(bool)
    grup = (~k).cumsum()
    return k.astype(int).groupby(grup).cumsum()
