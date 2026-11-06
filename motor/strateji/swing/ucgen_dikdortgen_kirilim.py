"""swing__ucgen-dikdortgen-kirilim — üçgen / dikdörtgen sınırı kırılımı (4h/1d).

Kural (çekirdek `formasyon_b4.UcgenDikdortgenTaban`):
  Son iki onaylı tepe ve iki dip pivotundan (pivotlar.py, nedensel; pencere mum içinde) sınır çizgileri: iki tepe
  yatay_tol_atr*ATR içinde ise yatay direnç, belirgin alçalıyorsa alçalan çizgi; iki dip belirgin yükseliyorsa yükselen alt
  çizgi. Tip: yükselen üçgen (yatay üst + yükselen alt), simetrik (alçalan üst + yükselen alt), dikdörtgen (ikisi yatay);
  tipler `ucgen/simetrik/dikdortgen` ile açılıp kapanır. Long: kapanış üst çizgi + tampon_atr*ATR üstünde ve önceki kapanış
  içerideydi (ilk kırılım), hacim > hacim_k * ort. hacim (hacim_k=0: kapalı). Stop = karşı uç (alt çizgi, stop_modu='orta'
  = orta) - stop_tampon_atr*ATR, en az min_risk_atr*ATR uzakta; hedef = üst çizgi + hedef_olcu*(formasyon başlangıç
  yüksekliği) (Bulkowski ölçü kuralı; hedef-giriş >= min_rr*risk). Short: ayna (alçalan üçgen, simetrik, dikdörtgen alt sınır).
Stil (swing): 4h/1d; pencere 30-60 mum (kart: 20-60), pivot_k=3.
Kaynak kartlar: daytrade__ucgen-kirilim-hacim__singhal, daytrade__yukselen-ucgen-3-gun-kapanis__bulkowski, daytrade__alcalan-ucgen-asagi-kirilim-satis__bulkowski, daytrade__simetrik-ucgen-satis__bulkowski, daytrade__dikdortgen-ust-21sma-3gun__bulkowski, daytrade__dikdortgen-alt-kirilim-3gun__bulkowski.
Varsayımlar / ölçülebilir yaklaşık tanım: Varsayılan stop_modu='orta': stop karşı uçta iken ölçü hedefi (1x yükseklik) risk/ödülü ~<1 yapıp min_rr süzgecinde çoğu işlemi eler (karsi_uc ızgarada). Kartlarda üçgen tespiti 'çizim': iki tepe + iki dip pivotundan çizgi (iki nokta). Bulkowski 3. gün çıkışı, 1 kuruş üstü alım stopu, 21 SMA filtresi, bozulmuş (başarısız) üçgen girişi, iz süren stop ve retest KODLANMADI (zaman çıkışı CikisAyarlari ile verilebilir). Düşen hacim (konsolidasyonda) şartı yok, yalnız kırılım hacmi.
Çelişkiler: Simetrik üçgende Bulkowski kişisel olarak %77 satışın zararla bittiğini söyler, Kratter simetrik için kural vermez; simetrik tip açık ama kapatılabilir (simetrik=False).
Negatif kanıt: Bulkowski: simetrik üçgen satışlarında %77 zararla çıkış (Vivus örneği); gün içi simetrik üçgen ölçü kuralı yalnız %46 işler (825 günlük üçgen, aşağı kırılım). Olumlu: dikdörtgen üst %75 kazanma, 4-5 gün ort. tutma (günlük hisse, 1991-2011).
"""
from motor.strateji.formasyon_b4 import UcgenDikdortgenTaban


class UcgenDikdortgenKirilim(UcgenDikdortgenTaban):
    ad = "swing__ucgen-dikdortgen-kirilim"
    stil = "swing"
    varsayilan_parametreler = {**UcgenDikdortgenTaban.varsayilan_parametreler,
                               "pencere": 45,
                               "pivot_k": 3,
                               "hedef_olcu": 1.0,
                               "stop_modu": 'orta',
                               }
    parametre_izgarasi = {
        "pencere": [30, 45, 60],
        "hacim_k": [0.0, 1.5],
        "stop_modu": ["karsi_uc", "orta"],
        "hedef_olcu": [1.0, 1.5],
    }
