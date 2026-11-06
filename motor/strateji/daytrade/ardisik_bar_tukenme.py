"""daytrade__ardisik-bar-tukenme: ardışık mum serisi / Woods yavaşlama ve doruğa-karşı sonrası ters yönde giriş; gün sonunda kapanır (1h).

Çekirdek swing `ArdisikBarTukenme` ile aynıdır (türetildi): desen "renk" (3-5 ardışık aynı renkli mum; zincir=lower high/low), "yavaslama"
(ardışık dipler düşer, adımlar AZALIR -> long; Woods Yavaşlama), "doruk" (adımlar ARTAR -> long; Woods Doruğa Karşı); short ayna.
Tetik: serinin ardından gelen mumun, serinin son mumunun zirvesi (short: dibi) üstünde (altında) kapanışı ("kirilim") veya serinin
son mumunun kapanışı ("seri_sonu", yalnız desen="renk"). Stop = seri uç noktası -/+ tampon*ATR (risk <= max_risk_atr*ATR); hedef hedef_r*R.
Day trade'e özgü: 1h varsayılanları (tetik "kirilim", hedef 2R, trend_ma 0) ve UTC gün sonu zorunlu çıkışı (seansın son mumunda giriş yok).
Kaynak kartlar: daytrade__yavaslama__woods ve daytrade__doruga-karsi__woods (5-30 dk vadeli, 3 çubuk; kurulum çubuğunun 1 tik ötesine stop emir;
  stop kurulum çubuğunun 1 tik ötesi; kâr alma kuralı yok; piyasa önyargısına karşı işlem yok -> trend_ma ile yaklaşık).
Kodlanmayan: "kurulum çubuğu yükseliş değilse bir sonraki yükseliş çubuğu" kuralı, Woods'un yapısal pivot filtresi (s.97), sıkışıklık/destek
  birleşimi tercihi, ters-yönlü Doruk Karşıtı'nın açık pozisyon çıkışı olarak kullanımı.
Varsayımlar: tik tamponu ATR tamponuna çevrildi; hedef kitapta yok (2R varsayım); doruk için "boğa doruk karşıtı" tanımı kitapta yok, düşüş yönü
  aynası alındı (kart belirsizliği).
Negatif kanıt: yok; Woods: trend yönüne karşı (ters) kullanım yeni başlayanlara önerilmez. Arşivde ortalamaya dönüş / kısa TF başarısız (arsiv/OZET.md §3).
"""
from motor.strateji.gostergeler_b1 import GunSonu
from motor.strateji.swing.ardisik_bar_tukenme import ArdisikBarTukenme as _Swing


class ArdisikBarTukenme(GunSonu, _Swing):
    ad = "daytrade__ardisik-bar-tukenme"
    stil = "daytrade"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "seri_n": 3, "tetik": "kirilim", "hedef_r": 2.0,
                               "seans_saat": 0.0}
    parametre_izgarasi = {
        "desen": ["renk", "yavaslama", "doruk"],
        "seri_n": [3, 4],
        "hedef_r": [1.5, 2.0, 3.0],
    }

    def sinyaller(self, mumlar):
        return self._cekirdek(mumlar, gun_sonu=True, seans_saat=self.parametreler["seans_saat"])
