"""swing__cift-dip-tepe — çift dip / çift tepe, boyun çizgisi kırılımı.

Kural (kartların ortak çekirdeği: Sharpe, Johnson, Graham, Bulkowski):
  Çift dip: ardışık iki onaylı dip pivotu (nedensel, bkz. pivotlar.py) arasındaki fark
  <= tolerans_yuzde (ilk dibe göre %), aralarındaki mesafe [min_arasi, maks_arasi] mum,
  boyun çizgisi = iki dip arasındaki en yüksek tepe ve boyun, dibin üstünde en az
  min_derinlik_atr*ATR olmalı. Tetik: kapanış boyun çizgisinin ÜSTÜNE geçer (teyitsiz erken giriş
  yok). Formasyon, kapanış iki dipten düşüğün altına inerse veya `gecerlilik` mum içinde
  kırılım gelmezse geçersiz. Opsiyonel RSI teyidi (Johnson): formasyon boyunca RSI <= rsi_esik
  (rsi_esik=0: kapalı). Çift tepe aynası (short).
  Stop: iki dipten düşüğün tampon_atr*ATR altı ("desenin sınırlarının hemen dışı").
  Hedef: boyun + hedef_olcu * (boyun - dip) (formasyon yüksekliği; Johnson/Bulkowski).

Kaynak kartlar: eve-eve-cift-dip__bulkowski, cift-dip-tepe__sharpe, cift-dip-tepe-donus__penn,
  cift-ust-dip-kirilim__graham, cift-dip-boyun-kirilim__johnson (+ aile kartları).
Kanıt: Bulkowski çift dipte günlük ölçekte %67 hedefe ulaşma, pullback oranı ort. %55; ancak
  istatistikler GÜNLÜK ölçekli, gün içi doğrulama yok. Kitaplar teyitsiz girişi riskli sayar.
Varsayımlar: "çirkin" çift dip (Bulkowski: sağ dip sol dipten %5+ yüksek) tolerans ile elenir;
  önceki trend (düşüş) şartı koda eklenmedi (RSI filtresi isteğe bağlı vekil); ikinci dibin
  pivot onayı için pivot_k mum beklenir, boyun kırılımı o güne kadar gelmiş olabilir.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.pivotlar import pivot_tablosu, sinyal_cercevesi
from motor.strateji.temel import Strateji


class CiftDipTepe(Strateji):
    ad = "swing__cift-dip-tepe"
    stil = "swing"
    varsayilan_parametreler = {
        "pivot_yontemi": "fraktal", "pivot_k": 3, "zigzag_esik_k": 2.0,
        "tolerans_yuzde": 1.0, "min_arasi": 5, "maks_arasi": 60, "gecerlilik": 30,
        "min_derinlik_atr": 1.0, "rsi_esik": 0.0, "rsi_periyot": 14,
        "tampon_atr": 0.25, "hedef_olcu": 1.0, "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "tolerans_yuzde": [0.5, 1.0, 2.0],
        "min_arasi": [5, 10, 20],
        "hedef_olcu": [0.75, 1.0, 1.5],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        n = len(mumlar)
        yu, du, kap = (mumlar[c].to_numpy(float) for c in ("yuksek", "dusuk", "kapanis"))
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], p["atr_periyot"]).to_numpy()
        rsi = g.rsi(mumlar["kapanis"], int(p["rsi_periyot"])).to_numpy()
        pv = pivot_tablosu(mumlar, p["pivot_yontemi"], int(p["pivot_k"]),
                           int(p["atr_periyot"]), p["zigzag_esik_k"])
        yeni_dip, yeni_tepe = pv["yeni_dip"].to_numpy(), pv["yeni_tepe"].to_numpy()
        sd_f, sd_i = pv["son_dip_fiyat"].to_numpy(), pv["son_dip_idx"].to_numpy()
        od_f, od_i = pv["onceki_dip_fiyat"].to_numpy(), pv["onceki_dip_idx"].to_numpy()
        st_f, st_i = pv["son_tepe_fiyat"].to_numpy(), pv["son_tepe_idx"].to_numpy()
        ot_f, ot_i = pv["onceki_tepe_fiyat"].to_numpy(), pv["onceki_tepe_idx"].to_numpy()
        tol = p["tolerans_yuzde"] / 100.0
        rsi_e = p["rsi_esik"]

        yon = np.zeros(n, dtype="int64")
        stop = np.full(n, np.nan)
        hedef = np.full(n, np.nan)
        kur_l = None   # (boyun, dip_alt, bitis)
        kur_s = None   # (boyun, tepe_ust, bitis)

        for t in range(n):
            if np.isnan(atr[t]):
                continue
            # --- yeni formasyon kurulumu (ikinci pivotun onay mumunda)
            if yeni_dip[t] and not np.isnan(od_f[t]):
                a, b = int(od_i[t]), int(sd_i[t])
                if (p["min_arasi"] <= b - a <= p["maks_arasi"]
                        and abs(sd_f[t] - od_f[t]) <= tol * od_f[t]):
                    boyun = yu[a:b + 1].max()
                    if boyun - max(sd_f[t], od_f[t]) >= p["min_derinlik_atr"] * atr[t]:
                        ok = True
                        if rsi_e > 0:
                            ok = np.nanmin(rsi[a:t + 1]) <= rsi_e if not np.all(np.isnan(rsi[a:t + 1])) else False
                        if ok:
                            kur_l = (boyun, min(sd_f[t], od_f[t]), t + int(p["gecerlilik"]))
            if p["short"] and yeni_tepe[t] and not np.isnan(ot_f[t]):
                a, b = int(ot_i[t]), int(st_i[t])
                if (p["min_arasi"] <= b - a <= p["maks_arasi"]
                        and abs(st_f[t] - ot_f[t]) <= tol * ot_f[t]):
                    boyun = du[a:b + 1].min()
                    if min(st_f[t], ot_f[t]) - boyun >= p["min_derinlik_atr"] * atr[t]:
                        ok = True
                        if rsi_e > 0:
                            ok = np.nanmax(rsi[a:t + 1]) >= 100.0 - rsi_e if not np.all(np.isnan(rsi[a:t + 1])) else False
                        if ok:
                            kur_s = (boyun, max(st_f[t], ot_f[t]), t + int(p["gecerlilik"]))
            # --- tetik / geçersizlik
            if kur_l is not None:
                boyun, dip, bitis = kur_l
                if kap[t] < dip or t > bitis:
                    kur_l = None
                elif kap[t] > boyun:
                    h = boyun + p["hedef_olcu"] * (boyun - dip)
                    if h > kap[t]:          # hareket zaten tamamlandıysa (boşluk) işlem yok
                        yon[t] = 1
                        stop[t] = dip - p["tampon_atr"] * atr[t]
                        hedef[t] = h
                    kur_l = None
            if kur_s is not None and yon[t] == 0:
                boyun, tepe, bitis = kur_s
                if kap[t] > tepe or t > bitis:
                    kur_s = None
                elif kap[t] < boyun:
                    h = boyun - p["hedef_olcu"] * (tepe - boyun)
                    if h < kap[t]:
                        yon[t] = -1
                        stop[t] = tepe + p["tampon_atr"] * atr[t]
                        hedef[t] = h
                    kur_s = None
        return sinyal_cercevesi(mumlar.index, yon, stop, hedef)

    def cikis_var_mi(self) -> bool:
        """Hedef formasyon ölçüsü."""
        return self.parametreler["hedef_olcu"] > 0
