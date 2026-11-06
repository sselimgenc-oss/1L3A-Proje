"""swing__donchian-kirilim: Donchian kanalı (N mumun en yüksek/en düşüğü) kırılımında trend yönünde giriş (4h/1d).

Kural: kapanış önceki `giris_n` mumun en yükseğini (kırılım yüzdesi kirilim_pct kadar aşarak) İLK kez aşarsa long;
önceki `giris_n` mumun en düşüğünün altına inerse short. Opsiyonel filtreler: kapanış > SMA(trend_ma) (long; short
ayna) ve hacim > hacim_k*20 mum ortalama hacim. Stop (zorunlu): stop_modu "atr" -> kapanış -/+ stop_atr*ATR;
"kanal" -> karşı çıkış kanalı (önceki cikis_n mumun düşüğü/zirvesi); "bar" -> kırılım mumunun dibi/zirvesi -/+
stop_tampon_atr*ATR. Hedef: hedef_r*R (0: yok). Çıkış: pozisyon yönüne göre karşı `cikis_n` mum kanalının kırılması
(long için önceki cikis_n mumun en düşüğünün altında kapanış; short ayna) -> `cikis`. Çıkış YÖNLÜDÜR
(`cikis_long` / `cikis_short` sütunları; hangi pozisyonun açık olduğunu motor bilir).
Kaynak kartlar: swing__aralik-kirilimi__ladha (1G; 10/20 günlük zirveyi %3-5 aşarak kapanış, stop kırılma günü dibinin
  %1 altı, çıkış 10/20 günlük EMA altı kapanış; hisse/endeks filtreleri -> kirilim_pct=3, stop_modu="bar"),
  swing__gann-cift-tepe-kirilim__razaq (çift tepe formasyonu: KODLANMADI), daytrade kartları (fraktal+SMA50 ve Donchian
  geri çekilme-kırılımı: KODLANMADI, fraktal/üst-banda-iki-temas tetiği sınıfta yok).
Kodlanmayan: Ladha'nın ciro/fiyat/endeks filtreleri ve 2.5-5 gün sonra yarı çıkış (kısmi çıkış CikisAyarlari.kismi ile verilebilir).
Varsayımlar: kapanış bazlı kırılım ve kapanış bazlı kanal çıkışı; kanal mevcut mum HARİÇ (lookahead yok); Turtle tarzı
  giris_n 10-55, cikis_n 5-20 ızgarada.
Negatif kanıt: arşivde 1S Donchian başarısız (arsiv/OZET.md §3, kısa TF + maliyet); Scheier/Bulkowski: kırılımların
  çoğu başarısız. Trend takip: az kazanç oranı, büyük kazançlar; kâr yoğunlaşması beklenir.
"""
import pandas as pd

from motor.strateji import gostergeler as g
from motor.strateji.daytrade._ortak import cerceve
from motor.strateji.gostergeler_b1 import donchian_kanal
from motor.strateji.temel import Strateji


class DonchianKirilim(Strateji):
    ad = "swing__donchian-kirilim"
    stil = "swing"
    varsayilan_parametreler = {
        "giris_n": 20, "cikis_n": 10, "kirilim_pct": 0.0, "trend_ma": 0, "hacim_k": 0.0,
        "stop_modu": "atr", "stop_atr": 2.0, "stop_tampon_atr": 0.25, "hedef_r": 0.0,
        "atr_periyot": 14, "short": True,
    }
    parametre_izgarasi = {
        "giris_n": [10, 20, 55],
        "cikis_n": [5, 10, 20],
        "stop_atr": [2.0, 3.0],
    }

    def cikis_var_mi(self) -> bool:
        return self.parametreler["cikis_n"] > 0 or self.parametreler["hedef_r"] > 0

    def _cekirdek(self, mumlar: pd.DataFrame, gun_sonu: bool = False, seans_saat: float = 0.0) -> pd.DataFrame:
        p = self.parametreler
        y, d, k = mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"]
        atr = g.atr(y, d, k, p["atr_periyot"])
        gk = donchian_kanal(y, d, p["giris_n"])
        ust = gk["ust"] * (1.0 + p["kirilim_pct"] / 100.0)
        alt = gk["alt"] * (1.0 - p["kirilim_pct"] / 100.0)
        long_ok = (k > ust) & (k.shift(1) <= ust.shift(1)) & atr.notna()
        short_ok = (k < alt) & (k.shift(1) >= alt.shift(1)) & atr.notna() & bool(p["short"])
        if p["trend_ma"]:
            tr = g.sma(k, int(p["trend_ma"]))
            long_ok &= k > tr
            short_ok &= k < tr
        if p["hacim_k"] > 0:
            ok = mumlar["hacim"] > p["hacim_k"] * mumlar["hacim"].shift(1).rolling(20, min_periods=20).mean()
            long_ok &= ok
            short_ok &= ok
        cn = max(int(p["cikis_n"]), 1)
        ck = donchian_kanal(y, d, cn)
        if p["stop_modu"] == "atr":
            stop_l, stop_s = k - p["stop_atr"] * atr, k + p["stop_atr"] * atr
        elif p["stop_modu"] == "kanal":
            stop_l, stop_s = ck["alt"], ck["ust"]
        else:
            stop_l, stop_s = d - p["stop_tampon_atr"] * atr, y + p["stop_tampon_atr"] * atr
        if p["hedef_r"]:
            h_l = k + p["hedef_r"] * (k - stop_l)
            h_s = k - p["hedef_r"] * (stop_s - k)
        else:
            h_l = h_s = None
        sig = cerceve(mumlar, long_ok, short_ok, stop_l, stop_s, h_l, h_s, None,
                      gun_sonu=gun_sonu, seans_saat=seans_saat)
        sig["cikis_long"] = False
        sig["cikis_short"] = False
        if p["cikis_n"] > 0:
            # Yönlü çıkış: long -> kapanış < karşı kanal altı; short -> kapanış > karşı kanal üstü. Pozisyonun
            # hangi yönde olduğunu motor bilir (sanal pozisyon izlenmez).
            sig["cikis_long"] = (k < ck["alt"]).fillna(False).astype(bool)
            sig["cikis_short"] = (k > ck["ust"]).fillna(False).astype(bool)
        return sig

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        return self._cekirdek(mumlar)
