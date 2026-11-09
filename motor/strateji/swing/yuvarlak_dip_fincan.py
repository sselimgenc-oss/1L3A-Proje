"""swing__yuvarlak-dip-fincan — fincan-sap / yuvarlak dip kırılımı (4h/1d).

Kural (çekirdek `formasyon_b4.YuvarlakDipFincanTaban`):
  Zigzag pivotlarından (zigzag_esik_k*ATR) sol kenar (tepe), taban (dip), sağ kenar (tepe) ve sap dibi (dip); sıra: sol < taban <
  sağ < sap. Fincan derinliği D = sol - taban >= min_derinlik_atr*ATR; genişlik (sol->sağ) min_genislik..maks_genislik mum;
  iki kenar kenar_tol*D içinde; sap sığ (0 < sağ - sap <= sap_maks*D); kapanışlar sol-sağ arasında yukarı açık paraboliğe
  R2 >= yuvarlaklik ile uyar (V şeklini eler). Tetik: sap dibi onaylandıktan sonra gecerlilik mum içinde kapanış sağ kenarın
  üstüne çıkar (sap dibi altında kapanış iptal). Stop = sap dibi - tampon_atr*ATR; hedef = sağ kenar + hedef_olcu*D (Bulkowski:
  yükseklik x %60; Jordan ~2R). Short: ayna (yuvarlak tepe, 'kaş çatma').
Stil (swing): 4h/1d; zigzag pivot (alternasyon için).
Kaynak kartlar: swing__fincan-sap-kirilim__jordan, daytrade__gulumseme-kasini-catma__bulkowski (C noktası alımı kodlanmadı; fincan kırılımına dahil), daytrade__ters-yukselen-tarak__bulkowski (geri çekilme %40-62 aralığı kenar/sap oranıyla yaklaşıldı).
Varsayımlar / ölçülebilir yaklaşık tanım: Formasyon 'sezgisel': pivot + parabol R2 + kenar/sap oran eşikleri tarafımızdan. Hacim, 50 SMA 25 gün kaydırılmış görselleştirme ve 'alt SMA altında çıkış' kodlanmadı.
Çelişkiler: Bulkowski hedefi yükseklik x %60, Jordan 2xrisk; hedef_olcu ızgarası 0.6-1.5. Bulkowski 'smile' girişi C noktasında (kırılımdan önce), Jordan sap kırılımında; kırılım seçildi.
Negatif kanıt: Bulkowski: teyitli deniz tarağı %75 hedefe ulaşır ama 'kas çatma'da alım ort. -%5, kazanma %31; satış tarafı zayıf kanıt.
"""
from motor.strateji.formasyon_b4 import YuvarlakDipFincanTaban


class YuvarlakDipFincan(YuvarlakDipFincanTaban):
    ad = "swing__yuvarlak-dip-fincan"
    stil = "swing"
    varsayilan_parametreler = {**YuvarlakDipFincanTaban.varsayilan_parametreler,
                               "yuvarlaklik": 0.6,
                               }
    parametre_izgarasi = {
        "yuvarlaklik": [0.4, 0.6, 0.8],
        "sap_maks": [0.33, 0.5],
        "hedef_olcu": [0.6, 1.0, 1.5],
    }
