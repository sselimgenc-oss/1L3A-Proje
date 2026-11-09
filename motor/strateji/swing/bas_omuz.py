"""swing__bas-omuz — baş-omuz (tepe) ve ters baş-omuz (dip), boyun çizgisi kırılımı.

Kural (çekirdek: formasyon_b3.bas_omuz_cekirdek): nedensel zigzag pivotlarından ardışık 3 onaylı dip (ters baş-omuz)
  — ortadaki (baş) iki yandakinden en az min_bas_atr*ATR düşük, iki omuz farkı <= sim_tol*yükseklik, boyun çizgisi
  = dipler arası iki tepeden geçen doğru (eğim <= egim_tol*yükseklik; "düz veya biraz eğimli", Penn/Kratter),
  sol/sağ zaman oranı <= zaman_oran. Tetik: kapanış boyun çizgisini yukarı kırar (teyitsiz erken giriş yok;
  Bulkowski: onaylanmadan satma). Pivot ancak onay mumunda bilinir; kırılım, D3 onayından sonra aranır ve en fazla
  maks_asim_atr*ATR kadar boyun üstündeyse alınır (kovalamak yok). Baş-omuz tepe = aynadaki aynı kural (short).
  Stop: sağ omuz (stop_modu="omuz") veya baş ("bas") ucunun tampon_atr*ATR ötesi. Hedef: boyun + hedef_olcu * (boyun -
  baş) (ölçü kuralı; Bulkowski ölçü kuralı yaklaşık tam yükseklik).
  Opsiyonel Scheier sağ omuz filtresi (sag_omuz_filtre=1): sağ omuz, başa sol omuzdan DAHA YAKIN olmamalı.
Kaynak kartlar: bas-omuz__sharpe, bas-omuz-boyun-kirilim__penn, bas-omuz-boyun-cizgisi__kratter,
  bas-omuz-sag-omuz-filtre__scheier, bas-omuz-ust-satis__bulkowski, karmasik-bas-omuz-ust-satis__bulkowski.
Varsayımlar: "formasyon görme" -> zigzag (ATR eşikli) pivotları; omuz simetrisi/eğim eşikleri kartlarda sayısal
  değil (optimize edilecek). Hacim ve "açığa satış için zayıf sektör" filtreleri yok. Karmaşık (çok omuzlu) baş-omuz
  ayrı ele alınmadı (ardışık 3 pivot kuralı onu kısmen yakalar).
Çelişkiler: Scheier sağ omuz kuralı "ters yön" önerir (kural ihlalinde trend devamı); biz yalnız kuralı sağlayan
  formasyonu işleriz. Bulkowski kısa için "yeni yıl zirvesinde açığa satma" der — uygulanmadı.
Negatif kanıt: Bulkowski istatistikleri GÜNLÜK hisse; yazarın kendi kaydı: görülen vakaların %30'unda kayıp.
  Başarısızlık/pullback sıktır (kırılım sonrası boyuna geri dönüş ~%50+). arsiv/OZET.md §3'te benzer klasik formasyon
  (çift dip/tepe vb.) için olumlu kanıt yok; ölçülü hareket hedefleri mekanik testte zayıf.
"""
import pandas as pd

from motor.strateji.formasyon_b3 import FormasyonTaban, bas_omuz_cekirdek


class BasOmuz(FormasyonTaban):
    ad = "swing__bas-omuz"
    stil = "swing"
    varsayilan_parametreler = {
        "pivot_yontemi": "zigzag", "pivot_k": 3, "zigzag_esik_k": 2.0, "atr_periyot": 14,
        "sim_tol": 0.4, "egim_tol": 0.5, "zaman_oran": 3.0, "min_bas_atr": 0.5, "min_yuk_atr": 2.0,
        "sag_omuz_filtre": 0, "gecerlilik": 40, "maks_asim_atr": 1.5, "tampon_atr": 0.25,
        "stop_modu": "omuz", "hedef_olcu": 1.0, "min_rr": 1.0, "long": True, "short": True,
    }
    parametre_izgarasi = {
        "sim_tol": [0.25, 0.4, 0.6],
        "hedef_olcu": [0.75, 1.0, 1.5],
        "zigzag_esik_k": [1.5, 2.0, 3.0],
    }

    def cekirdek(self, m: pd.DataFrame):
        return bas_omuz_cekirdek(m, self.parametreler)

    def cikis_var_mi(self) -> bool:
        """Ölçü hedefi (hedef_olcu > 0)."""
        return self.parametreler["hedef_olcu"] > 0
