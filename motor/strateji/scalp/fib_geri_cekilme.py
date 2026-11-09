"""scalp__fib-geri-cekilme: SMA/EMA200 trend yönünde Fibonacci geri çekilmesinde tepki mumu (15m).

Çekirdek swing `FibGeriCekilme` ile aynıdır (türetildi); scalp'e özgü: pivot_k=3, trend_ema=200 (kart: 200 SMA
yönü; burada EMA(200) kapanış konumu), bölge ızgarası 0.236-0.786, hedef önceki swing (1.0) veya uzatma.
Kural: bacak T (son tepe) - D (arası en düşük dip); fiyat Fib bölgesine iner, yükseliş mumu kapanır -> long
(kapanış > EMA200); stop Fib 1.0 (bacak başı) - tampon*ATR; hedef T. Short ayna.
Kaynak kartlar: daytrade__ma200-fibonacci-5dk__singhal (5dk; 200 SMA eğimi + Fib seviyesinde yükseliş mumu;
  stop alt Fib seviyesinin altı; hedef %0 Fib veya 1:2), daytrade__pivot-fibonacci-cift-destek-direnc__backus
  (2dk; S1 pivot + %23.6 Fib çift destek + Stokastik: KODLANMADI, pivot+Fib çakışması sınıfta yok).
Kodlanmayan: 200 SMA EĞİMİ (yalnız kapanış>EMA200), short'ta ayı yutan mum şartı (basit düşüş mumu), Backus kartı.
5dk -> 15m: pivot_k ve bölge aynı kalır; sayılar ATR'ye göre ölçeklenir (tampon_atr).
Negatif kanıt: arşiv (arsiv/OZET.md §3): Fibonacci denemesi OOS PF ≈ 0.85; 5 dk geri çekilme başarısız.
"""
from motor.strateji.swing.fib_geri_cekilme import FibGeriCekilme as _Swing


class FibGeriCekilme(_Swing):
    ad = "scalp__fib-geri-cekilme"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "pivot_k": 3, "trend_ema": 200}
    parametre_izgarasi = {
        "giris_alt": [0.236, 0.382, 0.5],
        "giris_ust": [0.618, 0.786],
        "hedef_uzatma": [1.0, 1.272, 1.618],
    }
