"""D10-A (kuyruktaki yeni_aile satırları, a grubu) için göstergeler. Hepsi nedensel: t. satır yalnız t. mum kapanışına kadar
olan veriyi kullanır. Paylaşılan dosyalara dokunulmaz.

  connors_rsi, yuzde_b, stoch_yavas, risk_siniri_l/s, pivot_olaylari, nokta_sekil_sinyalleri, swing_trendi
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.dis._gosterge_d9 import ardisik_say
from motor.strateji.gostergeler_b2 import yuzdelik_sira


def connors_rsi(kapanis: pd.Series, rsi_n: int = 3, seri_n: int = 2, sira_n: int = 100) -> pd.Series:
    """ConnorsRSI (standart tanım): [RSI(kapanış, rsi_n) + RSI(seri uzunluğu, seri_n) + yüzdelik sıra(1 mumluk getiri, sira_n)] / 3.
    Seri uzunluğu: art arda yükselen kapanış sayısı (+), düşen (-). Kitapta tanım verilmemiş: standart varsayıldı."""
    yuk = ardisik_say(kapanis > kapanis.shift(1))
    dus = ardisik_say(kapanis < kapanis.shift(1))
    seri = (yuk - dus).astype(float)
    sira = 100.0 * yuzdelik_sira(kapanis.pct_change(), sira_n)
    return (g.rsi(kapanis, rsi_n) + g.rsi(seri, seri_n) + sira) / 3.0


def yuzde_b(kapanis: pd.Series, n: int = 20, k: float = 2.0) -> pd.Series:
    """Bollinger %B: (kapanış - alt) / (üst - alt)."""
    b = g.bollinger(kapanis, n, k)
    ust, alt = b["ust"], b["alt"]
    return (kapanis - alt) / (ust - alt).where(ust != alt)


def stoch_yavas(yuksek, dusuk, kapanis, k_n: int = 8, k_yav: int = 3, d_n: int = 3) -> pd.DataFrame:
    """Yavaş stokastik (k_n, k_yav, d_n): ham %K'nın k_yav SMA'sı = K; K'nın d_n SMA'sı = D."""
    hh = yuksek.rolling(k_n, min_periods=k_n).max()
    ll = dusuk.rolling(k_n, min_periods=k_n).min()
    ham = 100.0 * (kapanis - ll) / (hh - ll).where(hh != ll)
    k = ham.rolling(k_yav, min_periods=k_yav).mean()
    return pd.DataFrame({"k": k, "d": k.rolling(d_n, min_periods=d_n).mean()})


def risk_siniri_l(stop, kapanis, atr, maks):
    """Long stopunu en çok `maks` x ATR uzağa çeker (maks <= 0: sınırsız)."""
    return stop if not maks or maks <= 0 else np.maximum(stop, kapanis - maks * atr)


def risk_siniri_s(stop, kapanis, atr, maks):
    return stop if not maks or maks <= 0 else np.minimum(stop, kapanis + maks * atr)


def pivot_olaylari(tablo: pd.DataFrame):
    """pivotlar.py tablosundan ONAY sırasıyla pivot olayları: (onay_idx, tur(+1 tepe/-1 dip), pivot_idx, fiyat) dizileri."""
    yt = np.flatnonzero(tablo["yeni_tepe"].to_numpy())
    yd = np.flatnonzero(tablo["yeni_dip"].to_numpy())
    st_i, st_f = tablo["son_tepe_idx"].to_numpy(), tablo["son_tepe_fiyat"].to_numpy()
    sd_i, sd_f = tablo["son_dip_idx"].to_numpy(), tablo["son_dip_fiyat"].to_numpy()
    olay = [(int(b), 1, int(st_i[b]), float(st_f[b])) for b in yt] + \
           [(int(b), -1, int(sd_i[b]), float(sd_f[b])) for b in yd]
    olay.sort()
    if not olay:
        z = np.array([], dtype=int)
        return z, z, z, np.array([])
    o, t, p, f = zip(*olay)
    return np.array(o), np.array(t), np.array(p), np.array(f)


def swing_trendi(tablo: pd.DataFrame) -> pd.Series:
    """Onaylı pivotlardan trend: son iki tepe VE son iki dip yükseliyorsa +1, ikisi de alçalıyorsa -1; karışıksa önceki durum."""
    st, ot = tablo["son_tepe_fiyat"], tablo["onceki_tepe_fiyat"]
    sd, od = tablo["son_dip_fiyat"], tablo["onceki_dip_fiyat"]
    ham = pd.Series(np.nan, index=tablo.index)
    ham[(st > ot) & (sd > od)] = 1.0
    ham[(st < ot) & (sd < od)] = -1.0
    return ham.ffill()


def nokta_sekil_sinyalleri(yuksek: pd.Series, dusuk: pd.Series, kutu: float, ters: int = 3, tol: int = 0,
                           stop_ek: int = 4, ucle: bool = True, sarsinti: bool = True) -> pd.DataFrame:
    """Nokta & Şekil (yüzde kutulu, log ölçek: kutu = fiyatın `kutu` oranı; seviye = floor(ln(fiyat)/ln(1+kutu))).
    Sütunlar mum yüksek/düşük ile kurulur: yükselen sütunda yeni kutu varsa uzar, yoksa `ters` kutu geri dönüş sütunu açar
    (önce devam, sonra dönüş). Tek ileri geçiş = nedensel.
      long/short: üçlü tepe (dip) kırılımı ve boğa (ayı) sarsıntısı sinyalleri; stop_l/stop_s: formasyon stop fiyatı.
      cikis_l: ayı sinyali (O sütunu önceki O dibinin altına iner), cikis_s: boğa sinyali (X sütunu önceki X tepesini aşar).
    tol: iki tepe/dip eşit sayılır (kutu farkı <= tol)."""
    n = len(yuksek)
    lb = float(np.log1p(kutu))
    hi = np.floor(np.log(yuksek.to_numpy(float)) / lb).astype(np.int64)
    lo = np.floor(np.log(dusuk.to_numpy(float)) / lb).astype(np.int64)
    long_ = np.zeros(n, bool); short_ = np.zeros(n, bool)
    cikis_l = np.zeros(n, bool); cikis_s = np.zeros(n, bool)
    stop_l = np.full(n, np.nan); stop_s = np.full(n, np.nan)
    cols = [[1, int(hi[0]), int(lo[0])]]            # [yon(+1 X / -1 O), ust, alt]

    def fiyat(seviye):
        return float(np.exp(lb * seviye))
    for t in range(1, n):
        c = cols[-1]
        ust0, alt0 = c[1], c[2]
        yeni = False
        if c[0] == 1:
            if hi[t] >= c[1] + 1:
                c[1] = int(hi[t])
            elif lo[t] <= c[1] - ters:
                cols.append([-1, c[1] - 1, int(lo[t])]); yeni = True
        else:
            if lo[t] <= c[2] - 1:
                c[2] = int(lo[t])
            elif hi[t] >= c[2] + ters:
                cols.append([1, int(hi[t]), c[2] + 1]); yeni = True
        k = len(cols)
        cur = cols[-1]
        if k >= 3 and cur[0] == 1:
            ref = cols[-3][1]
            if cur[1] > ref and (yeni or ust0 <= ref):
                cikis_s[t] = True
        if k >= 3 and cur[0] == -1:
            ref = cols[-3][2]
            if cur[2] < ref and (yeni or alt0 >= ref):
                cikis_l[t] = True
        if ucle and k >= 5 and cur[0] == 1:
            a, b = cols[-3], cols[-5]
            tep = max(a[1], b[1])
            if abs(a[1] - b[1]) <= tol and cur[1] > tep and (yeni or ust0 <= tep) and cols[-2][2] > cols[-4][2]:
                long_[t] = True; stop_l[t] = fiyat(cols[-2][2])
        if ucle and k >= 5 and cur[0] == -1:
            a, b = cols[-3], cols[-5]
            dip = min(a[2], b[2])
            if abs(a[2] - b[2]) <= tol and cur[2] < dip and (yeni or alt0 >= dip) and cols[-2][1] < cols[-4][1]:
                short_[t] = True; stop_s[t] = fiyat(cols[-2][1] + 1)
        if sarsinti and yeni and k >= 7:
            if cur[0] == 1:
                b1, b0, b00 = cols[-2][2], cols[-4][2], cols[-6][2]
                if abs(b0 - b00) <= tol and 1 <= b0 - b1 <= 3 and cols[-3][1] > cols[-5][1]:
                    long_[t] = True; stop_l[t] = fiyat(b1 - stop_ek)
            else:
                t1, t0, t00 = cols[-2][1], cols[-4][1], cols[-6][1]
                if abs(t0 - t00) <= tol and 1 <= t1 - t0 <= 3 and cols[-3][2] < cols[-5][2]:
                    short_[t] = True; stop_s[t] = fiyat(t1 + 1 + stop_ek)
    return pd.DataFrame({"long": long_, "short": short_, "stop_l": stop_l, "stop_s": stop_s,
                         "cikis_l": cikis_l, "cikis_s": cikis_s}, index=yuksek.index)
