"""swing__crane-reaksiyon-swing: Crane "Reaksiyon swing" orta nokta tetiği (+ İki gün kuralı varyantı).

Kapanış pivotları (fraktal, k=pivot_k, NEDENSEL: pivot k mum sonra onaylanır) kullanılır; yüksek=düşük=kapanış.
mod="reaksiyon" (kart swing__reaksiyon-swing-tetik__crane): yükselen trendde (B > önceki tepe, C > A):
  B = son onaylı tepe kapanışı, C = ondan sonraki dip kapanışı (reaksiyon swing uzunluğu B..C >= min_gun mum, B ve C dahil),
  A = C'den önceki dip (B'den önce). Tetik = B - tetik_oran*(B - C) (tetik_oran=0.5: orta nokta). Düzeltmenin bittiği onayı
  (iki_gun_onay=True): C'den sonra iki ardışık yukarı kapanış VEYA kapanış > B. Giriş: onay + kapanış >= tetik durumu YENİ
  oluştuğunda (C'den en çok max_bekle mum içinde). Hedef: C + hedef_carpan*(B - A) (kart: A-B hareketi kadar projeksiyon, carpan=1).
  Stop: C - stop_tampon_atr*ATR. Zaman çıkışı: zaman_mum mum sonra (kart: "hedef veya zaman sınırı hangisi önce").
mod="iki_gun" (kart swing__iki-gun-kurali__crane): tepe pivotundan (H) hemen sonra iki ardışık düşüş mumu (kapanış<açılış);
  tetik = H - (H - L2)/2 (L2 ikinci düşüş gününün dibi); kapanış tetiğe ulaşınca (max_bekle içinde) long. Stop = pivottan beri
  en düşük dip - tampon; hedef = pivot tepesi H (kart reaksiyon projeksiyonuna atıf yapar; A-B bilgisi bu modda kullanılmadı, basitleştirme).
Short her iki modda ayna (düşen trend). Tetik BUY-STOP'tur (gün içi dolum); sinyaller yalnız kapanışta üretildiği için burada
"kapanış >= tetik" ile yaklaşıldı (motor bir sonraki açılışta girer) — kartın intrabar dolumundan farklıdır.
Çıkış: hedef veya zaman_mum (`zaman_cikisi_mum` sütunu); `cikis` sütunu kullanılmaz. Hedef girişin doğru tarafında değilse sinyal düşer.
Kaynak kartlar: swing__reaksiyon-swing-tetik__crane, swing__iki-gun-kurali__crane, swing__reversal-date-stop__crane
(Reversal date: ters/ileri gün SAYIMI belirsiz ve takvim bağımlı; KODLANMADI).
Varsayımlar: Crane'in pivot tanımı = kapanış pivotu; fraktal k ile modellendi; piyasa trendi HH/HL ile; tick değil ATR tamponu.
Negatif kanıt: aile kaydında yok; arşivde Fibonacci/ölçülü hareket (OOS PF ~0.85) ve geri çekilme denemeleri başarısız (arsiv/OZET.md §3) — bu aile
ölçülü hareket hedefi kullandığı için aynı riski taşır. Tek yazar.
"""
import numpy as np
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji import gostergeler_b2 as b
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.pivotlar import fraktal_pivotlar
from motor.strateji.temel import Strateji


class CraneReaksiyonSwing(Strateji):
    ad = "swing__crane-reaksiyon-swing"
    stil = "swing"
    varsayilan_parametreler = {
        "mod": "reaksiyon", "pivot_k": 3, "min_gun": 3, "tetik_oran": 0.5, "iki_gun_onay": True,
        "hedef_carpan": 1.0, "max_bekle": 20, "zaman_mum": 20, "stop_tampon_atr": 0.1, "stop_max_atr": 4.0,
        "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "pivot_k": [2, 3, 4],
        "min_gun": [3, 5],
        "hedef_carpan": [0.75, 1.0, 1.5],
    }

    def cikis_var_mi(self) -> bool:
        return True   # hedef + zaman çıkışı

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        a, y, d, k = mumlar["acilis"], mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        n = len(k)
        kn, an, yn, dn = k.to_numpy(), a.to_numpy(), y.to_numpy(), d.to_numpy()
        atr = g.atr(y, d, k, p["atr_periyot"]).to_numpy()
        if p["mod"] not in ("reaksiyon", "iki_gun"):
            raise ValueError(f"Bilinmeyen mod: {p['mod']}")
        kk = int(p["pivot_k"])
        if p["mod"] == "iki_gun" and kk < 2:
            raise ValueError("iki_gun modu için pivot_k >= 2 gerekir")
        pv = fraktal_pivotlar(k, k, kk)
        st, si = pv["son_tepe_fiyat"].to_numpy(), pv["son_tepe_idx"].to_numpy()
        ot = pv["onceki_tepe_fiyat"].to_numpy()
        sd, sdi = pv["son_dip_fiyat"].to_numpy(), pv["son_dip_idx"].to_numpy()
        od, odi = pv["onceki_dip_fiyat"].to_numpy(), pv["onceki_dip_idx"].to_numpy()
        mg, bekle, ora = int(p["min_gun"]), int(p["max_bekle"]), p["tetik_oran"]
        durum_l = np.zeros(n, dtype=bool)
        durum_s = np.zeros(n, dtype=bool)
        stop_l = np.full(n, np.nan)
        stop_s = np.full(n, np.nan)
        hedef_l = np.full(n, np.nan)
        hedef_s = np.full(n, np.nan)
        for t in range(2, n):
            if np.isnan(atr[t]):
                continue
            tampon = p["stop_tampon_atr"] * atr[t]
            if p["mod"] == "reaksiyon":
                # --- long: B=son tepe, C=ondan sonraki dip, A=C'den önceki dip (B'den önce)
                if not (np.isnan(si[t]) or np.isnan(sdi[t]) or np.isnan(odi[t]) or np.isnan(ot[t])):
                    B, C, A = st[t], sd[t], od[t]
                    if (sdi[t] > si[t] and odi[t] < si[t] and B > ot[t] and C > A
                            and sdi[t] - si[t] + 1 >= mg and t - sdi[t] <= bekle):
                        onay = (kn[t] > kn[t - 1] > kn[t - 2] and t - 2 >= sdi[t]) or kn[t] > B
                        if not p["iki_gun_onay"]:
                            onay = True
                        tetik = B - ora * (B - C)
                        if onay and kn[t] >= tetik:
                            durum_l[t] = True
                            stop_l[t] = C - tampon
                            hedef_l[t] = C + p["hedef_carpan"] * (B - A)
                # --- short: B=son dip, C=ondan sonraki tepe, A=C'den önceki tepe
                if not (np.isnan(si[t]) or np.isnan(sdi[t]) or np.isnan(od[t])) and not np.isnan(pv["onceki_tepe_idx"].to_numpy()[t]):
                    B, C, A = sd[t], st[t], ot[t]
                    oti = pv["onceki_tepe_idx"].to_numpy()[t]
                    if (si[t] > sdi[t] and oti < sdi[t] and B < od[t] and C < A
                            and si[t] - sdi[t] + 1 >= mg and t - si[t] <= bekle):
                        onay = (kn[t] < kn[t - 1] < kn[t - 2] and t - 2 >= si[t]) or kn[t] < B
                        if not p["iki_gun_onay"]:
                            onay = True
                        tetik = B + ora * (C - B)
                        if onay and kn[t] <= tetik:
                            durum_s[t] = True
                            stop_s[t] = C + tampon
                            hedef_s[t] = C - p["hedef_carpan"] * (A - B)
            else:
                # iki gün kuralı: tepe H'den sonra iki ardışık düşüş mumu; tetik H - (H-L2)/2
                if not np.isnan(si[t]) and not np.isnan(ot[t]):
                    i0 = int(si[t])
                    if i0 + 2 <= t and t - i0 <= bekle and st[t] > ot[t] and kn[i0 + 1] < an[i0 + 1] and kn[i0 + 2] < an[i0 + 2]:
                        H, L2 = st[t], dn[i0 + 2]
                        tetik = H - (H - L2) / 2.0
                        dibi = dn[i0 + 1:t + 1].min()
                        if kn[t] >= tetik:
                            durum_l[t] = True
                            stop_l[t] = dibi - tampon
                            hedef_l[t] = H
                if not np.isnan(sdi[t]) and not np.isnan(od[t]):
                    i0 = int(sdi[t])
                    if i0 + 2 <= t and t - i0 <= bekle and sd[t] < od[t] and kn[i0 + 1] > an[i0 + 1] and kn[i0 + 2] > an[i0 + 2]:
                        Lw, H2 = sd[t], yn[i0 + 2]
                        tetik = Lw + (H2 - Lw) / 2.0
                        zirve = yn[i0 + 1:t + 1].max()
                        if kn[t] <= tetik:
                            durum_s[t] = True
                            stop_s[t] = zirve + tampon
                            hedef_s[t] = Lw
        idx = k.index
        atr_s = pd.Series(atr, index=idx)
        long_ok = b.gecis(pd.Series(durum_l, index=idx))
        short_ok = b.gecis(pd.Series(durum_s, index=idx)) & bool(p["short"])
        sl = np.maximum(pd.Series(stop_l, index=idx), k - p["stop_max_atr"] * atr_s)
        ss = np.minimum(pd.Series(stop_s, index=idx), k + p["stop_max_atr"] * atr_s)
        hl, hs = pd.Series(hedef_l, index=idx), pd.Series(hedef_s, index=idx)
        long_ok &= hl > k
        short_ok &= hs < k
        sig = cerceve(mumlar, long_ok, short_ok, sl, ss, hl, hs)
        if p["zaman_mum"]:
            sig["zaman_cikisi_mum"] = pd.Series(float(p["zaman_mum"]), index=idx).where(sig["yon"] != 0)
        return sig
