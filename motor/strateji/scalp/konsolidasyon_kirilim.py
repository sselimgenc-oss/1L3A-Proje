"""scalp__konsolidasyon-kirilim: dar blok / aralık kırılımı (15m), hacim ve trend filtreli.

Çekirdek swing `KonsolidasyonKirilim` ile aynıdır; bu sınıf ondan türer, scalp'e özgü değişenler:
  stop varsayılanı kutu ORTASI (kartlar: "karşı uç / blok ortası"), kutu uzunluğu 10, hedef = 1.5 x kutu
  yüksekliği (kart: min 2R / aralık yüksekliği), trend EMA(20 -> 50 ızgarasız; Volman/Hogan: trend yönünde).
Kural: önceki `uzunluk` mumun kutusu dar (yükseklik <= maks_genislik_atr*ATR); kapanış kutu dışında (+tampon);
  hacim > hacim_k x kutu ortalama hacmi; trend_ema yönünde. Stop kutu ucu/ortası, hedef kapanıştan kutu yüksekliği.
Kaynak kartlar: daytrade__1dk-konsolidasyon-kirilim-scalp__singhal (1m, 4-5 mumluk aralık, min 1:3),
  scalp__blok-kirma__volman, scalp__yuvarlak-sayi-aralik-kirilimi__volman, scalp__ic-aralik-kirilimi__volman,
  scalp__devrilme-noktasi-arb__volman (hepsi 1m-5m; yuvarlak sayı ve iç-aralık/ARB varyantları kodlanmadı).
PİP -> ATR: Volman kartlarının pip stop/hedefleri (5m EURUSD) kutu yüksekliği ve ATR katlarıyla ifade edilir
  (dar kutu <= 3 ATR; hedef 1.5x kutu).
Negatif kanıt (aile kaydı): Scheier — kırılımların çoğu başarısız olur, duraklama/retest filtresi gerekir;
  Bulkowski — destek kırılımı satışlarının %70'i zararla bitmiş. Retest/duraklama kodlanmadı.
Varsayımlar: dar-kutu eşiği tarafımızdan; swing/day trade konsolidasyon ailesiyle yüksek korelasyon beklenir.
"""
from motor.strateji.swing.konsolidasyon_kirilim import KonsolidasyonKirilim as _Swing


class KonsolidasyonKirilim(_Swing):
    ad = "scalp__konsolidasyon-kirilim"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler,
                               "uzunluk": 10, "maks_genislik_atr": 3.0, "stop_modu": "orta",
                               "hedef_olcu": 1.5, "trend_ema": 50}
    parametre_izgarasi = {
        "uzunluk": [8, 12, 20],
        "hacim_k": [0.0, 1.5, 2.0],
        "stop_modu": ["uc", "orta"],
    }

    def cikis_var_mi(self) -> bool:
        return True   # hedef = ölçülü hareket
