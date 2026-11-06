"""scalp__cift-dip-tepe: çift dip / çift tepe boyun çizgisi kırılımı (15m).

Çekirdek swing `CiftDipTepe` ile aynıdır (türetildi): nedensel fraktal pivotlarla iki eşit dip (tolerans_yuzde),
aralarında min/maks mum, boyun = arasındaki zirve; kapanış boynu geçince long (çift tepe aynası short);
stop = iki dipten düşüğün tampon*ATR altı; hedef boyun + hedef_olcu*(boyun-dip). Scalp'e özgü: 15m varsayılanları
(tolerans %0.5, min_arasi 4, maks_arasi 40, gecerlilik 20) ve ızgara.
Kaynak kartlar: daytrade__gun-ici-cift-tepe-kisa__bulkowski (5m; vadi kırılınca short, hedef formasyon boyu),
  daytrade__gun-ici-cift-dip-uzun__bulkowski (5m; zirve üstü, hedef formasyon boyu). Bu iki kart çekirdektir.
KODLANMAYAN: gun-ici-ucl-tepe-kisa / ucl-dip-uzun (üçlü formasyon: sınıf iki pivotla çalışır),
  yanal-momentum-cift-dip-tepe__maza ve geri-cekilme-cift-dip-tepe__maza (1m mum eşit tepe/dip + destek/direnç
  seviyesi + gün tipi/ana trend filtreleri; farklı mekanik).
Varsayımlar: Bulkowski'nin "1 kuruş" tamponu ATR tamponuna çevrildi; "kapanışa 1-2 saat kala" zaman filtresi yok
  (scalp'te gün sonu zorunlu değil); RSI teyidi kapalı. 5m -> 15m.
Kanıt/negatif: Bulkowski çift dip %67 hedefe ulaşma günlük ölçekli; gün içi doğrulama yok.
"""
from motor.strateji.swing.cift_dip_tepe import CiftDipTepe as _Swing


class CiftDipTepe(_Swing):
    ad = "scalp__cift-dip-tepe"
    stil = "scalp"
    varsayilan_parametreler = {**_Swing.varsayilan_parametreler, "tolerans_yuzde": 0.5, "min_arasi": 4,
                               "maks_arasi": 40, "gecerlilik": 20}
    parametre_izgarasi = {
        "tolerans_yuzde": [0.3, 0.5, 1.0],
        "min_arasi": [4, 8, 12],
        "hedef_olcu": [0.75, 1.0, 1.5],
    }
