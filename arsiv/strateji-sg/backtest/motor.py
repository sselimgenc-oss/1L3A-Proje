"""Bar bazlı backtest motoru.

Kurallar (muhafazakâr varsayımlar):
  * Sinyal i. barın KAPANIŞINDA üretilir, işlem i+1. barın AÇILIŞINDA açılır.
  * Stop / hedef bar içi high/low ile kontrol edilir; aynı barda ikisi de
    değerse önce STOP'un tetiklendiği varsayılır.
  * Fiyat açılışta stop/hedefin ötesine boşluk yaparsa açılış fiyatından çıkılır.
  * Aynı anda tek pozisyon. Masraflar (spread + komisyon + kayma) her işlemden düşülür.
"""
import numpy as np
from numba import njit


@njit(cache=True)
def _calistir(o, h, l, c, sinyal, stop_mesafe, hedef_mesafe, cikis_sinyal,
              zorla_kapat, max_bar, be_tetik, iz_mesafe):
    n = len(c)
    # çıktı: giriş idx, çıkış idx, yön, giriş fiyatı, çıkış fiyatı, risk(fiyat), sebep
    out = np.zeros((n, 7))
    k = 0
    i = 0
    while i < n - 1:
        s = sinyal[i]
        if s == 0 or np.isnan(stop_mesafe[i]) or stop_mesafe[i] <= 0:
            i += 1
            continue
        yon = s
        j = i + 1
        giris = o[j]
        risk = stop_mesafe[i]
        stop = giris - yon * risk
        hedef = giris + yon * hedef_mesafe[i] if hedef_mesafe[i] > 0 else np.nan
        be_yapildi = False
        en_iyi = giris
        sebep = 0
        cikis = np.nan
        while True:
            # açılış boşluğu kontrolü (giriş barı hariç)
            if j > i + 1:
                if (yon > 0 and o[j] <= stop) or (yon < 0 and o[j] >= stop):
                    cikis = o[j]; sebep = 1; break
                if not np.isnan(hedef) and ((yon > 0 and o[j] >= hedef) or (yon < 0 and o[j] <= hedef)):
                    cikis = o[j]; sebep = 2; break
            # bar içi: önce stop
            if (yon > 0 and l[j] <= stop) or (yon < 0 and h[j] >= stop):
                cikis = stop; sebep = 1; break
            if not np.isnan(hedef) and ((yon > 0 and h[j] >= hedef) or (yon < 0 and l[j] <= hedef)):
                cikis = hedef; sebep = 2; break
            # bar kapanışında yönetim
            if yon > 0:
                en_iyi = max(en_iyi, h[j])
            else:
                en_iyi = min(en_iyi, l[j])
            if be_tetik > 0 and not be_yapildi and yon * (en_iyi - giris) >= be_tetik * risk:
                be_yapildi = True
                if yon * (giris - stop) > 0:
                    stop = giris
            if iz_mesafe > 0:
                yeni = en_iyi - yon * iz_mesafe * risk
                if yon * (yeni - stop) > 0:
                    stop = yeni
            if cikis_sinyal[j] == -yon or cikis_sinyal[j] == 2:
                cikis = c[j]; sebep = 3; break
            if zorla_kapat[j]:
                cikis = c[j]; sebep = 4; break
            if max_bar > 0 and j - i >= max_bar:
                cikis = c[j]; sebep = 5; break
            if j >= n - 1:
                cikis = c[j]; sebep = 6; break
            j += 1
        out[k, 0] = i + 1; out[k, 1] = j; out[k, 2] = yon
        out[k, 3] = giris; out[k, 4] = cikis; out[k, 5] = risk; out[k, 6] = sebep
        k += 1
        i = j  # çıkış barının kapanışında yeni sinyal değerlendirilebilir
    return out[:k]


SEBEP = {1: "stop", 2: "hedef", 3: "sinyal", 4: "seans", 5: "süre", 6: "veri sonu"}


def backtest(df, sinyal, stop_mesafe, hedef_mesafe, maliyet, cikis_sinyal=None,
             zorla_kapat=None, max_bar=0, be_tetik=0.0, iz_mesafe=0.0):
    """maliyet: dict(sabit=fiyat birimi gidiş-dönüş, oran=fiyatın oranı olarak gidiş-dönüş)."""
    import pandas as pd
    n = len(df)
    o, h, l, c = (df[k].to_numpy(np.float64) for k in ("open", "high", "low", "close"))
    sinyal = np.asarray(sinyal, np.float64)
    stop_mesafe = np.asarray(stop_mesafe, np.float64)
    hedef_mesafe = np.asarray(hedef_mesafe, np.float64)
    cs = np.zeros(n) if cikis_sinyal is None else np.asarray(cikis_sinyal, np.float64)
    zk = np.zeros(n, np.bool_) if zorla_kapat is None else np.asarray(zorla_kapat, np.bool_)
    r = _calistir(o, h, l, c, sinyal, stop_mesafe, hedef_mesafe, cs, zk,
                  int(max_bar), float(be_tetik), float(iz_mesafe))
    t = pd.DataFrame(r, columns=["gi", "ci", "yon", "giris", "cikis", "risk", "sebep"])
    t["gi"] = t.gi.astype(int); t["ci"] = t.ci.astype(int)
    t["giris_zaman"] = df.index[t.gi]
    t["cikis_zaman"] = df.index[t.ci]
    brut = t.yon * (t.cikis - t.giris)
    masraf = maliyet.get("sabit", 0.0) + maliyet.get("oran", 0.0) * t.giris
    t["pnl"] = brut - masraf                       # fiyat birimi
    t["pnl_pct"] = 100 * t.pnl / t.giris            # kaldıraçsız % getiri
    t["R"] = t.pnl / t.risk                          # risk birimi cinsinden
    t["sebep"] = t.sebep.map(SEBEP)
    return t


def ozet(t, risk_pct=1.0):
    """risk_pct: her işlemde sermayenin % kaçı riske ediliyor (R bazlı bileşik eğri)."""
    if len(t) == 0:
        return dict(islem=0, kazanma=np.nan, pf=np.nan, ortR=np.nan, toplamR=0.0,
                    getiri_pct=0.0, maxdd_pct=0.0, toplam_pct=0.0)
    kaz = t.R[t.R > 0].sum()
    kay = -t.R[t.R <= 0].sum()
    egri = np.cumprod(1 + risk_pct / 100 * t.R.to_numpy())
    tepe = np.maximum.accumulate(egri)
    dd = (1 - egri / tepe).max() * 100
    return dict(
        islem=len(t),
        kazanma=100 * (t.pnl > 0).mean(),
        pf=kaz / kay if kay > 0 else np.inf,
        ortR=t.R.mean(),
        toplamR=t.R.sum(),
        getiri_pct=100 * (egri[-1] - 1),
        maxdd_pct=dd,
        toplam_pct=t.pnl_pct.sum(),
    )
