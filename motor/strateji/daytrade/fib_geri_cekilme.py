"""daytrade__fib-geri-cekilme: trendde Fibonacci geri çekilme bölgesinde tepki mumu; gün sonunda kapanır (1h).

Çekirdek swing `FibGeriCekilme` ile aynıdır (türetildi): nedensel pivotlarla bacak (son tepe T, aradaki en düşük
dip D; R=T-D), mum dibi [T-giris_ust*R, T-giris_alt*R] bölgesinde ve yükseliş mumu kapanışında long (short ayna),
stop = Fib stop_seviyesi (1.0 = bacak başı) ötesi - tampon*ATR, hedef T + (hedef_uzatma-1)*R. Day trade'e özgü:
1h varsayılanları (pivot_k=4) ve UTC gün sonu zorunlu çıkışı (seansın son mumunda giriş yok).
Kaynak kart: daytrade__macd-fibonacci-geri-cekilme__singhal (30dk; yükselişte swing tepesi sonrası Fib
  seviyesinde yeşil mum + MACD>sinyal; stop önceki swing dibi; hedef Fib %0 üstü veya 1:2).
Kodlanmayan: MACD>sinyal onayı (sınıfta yok); kitap yalnız long tarif eder, short ayna eklenmiştir (short=False ile kapat).
Varsayımlar: "yükselen trend" = yapı (T > önceki tepe); giriş mum kapanışı (kitap: yeşil mumun kapanışı üstü stop-buy).
Negatif kanıt: arşiv (arsiv/OZET.md §3): Fibonacci / ölçülü hareket denemesi OOS PF ≈ 0.85.
"""
from motor.strateji.gostergeler_b1 import GunSonu
from motor.strateji.swing.fib_geri_cekilme import FibGeriCekilme as _Swing


class FibGeriCekilme(GunSonu, _Swing):
    ad = "daytrade__fib-geri-cekilme"
    stil = "daytrade"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "pivot_k": 4, "trend_ema": 0, "seans_saat": 0.0}
    parametre_izgarasi = {
        "giris_alt": [0.382, 0.5, 0.618],
        "giris_ust": [0.618, 0.786],
        "hedef_uzatma": [1.0, 1.272, 1.618],
    }
