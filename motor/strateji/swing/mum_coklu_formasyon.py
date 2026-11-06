"""swing__mum-coklu-formasyon — Japon mum dönüş desenleri (3 mum ve üzeri), desen tamamlanınca ters yönde giriş.

Desenler (formasyon_b3.mum_*; `desenler` parametresi virgüllü liste veya "hepsi"):
  uc_cizgi      boğa üç çizgi vuruşu (LONG; aynada ayı üç çizgi vuruşu SHORT): 3 kırmızı mum, her biri öncekinden düşük
                dip/kapanış, kapanış kendi dibine yakın (<= yakin*aralık); 4. boğa mumu 3.'nün kapanışında/altında açılır,
                1. kırmızının yükseğinin üstünde kapanır.
  terk_bebek    boğa terk edilmiş bebek (LONG; aynada SHORT): kırmızı, aşağı boşluklu doji (gövde <= doji_oran*aralık),
                yukarı boşluklu boğa mumu.
  harami_capraz boğa harami çaprazı (LONG; aynada ayı SHORT): güçlü kırmızı (gövde >= guclu_atr*ATR), gövdesi içinde doji,
                doji'de hacim düşüşü (hacim_filtre), yutan boğa mumu (kapanış > kırmızının açılışı).
  uc_kara_karga yükseliş sonrası 3 kırmızı mum, her biri daha düşük dip, kapanış dibe yakın (yalnız SHORT).
  iki_bosluk    yükseliş sonrası aralarında aşağı boşluk olan iki kırmızı mum (yalnız SHORT).
Hepsi desenden önce `trend_n` mumda net >= trend_min_atr*ATR ters hareket ister (düşüş sonrası long, yükseliş sonrası short).
Giriş: desen tamamlandığı mumun kapanışı. Stop: desenin ucu (min düşük) - tampon_atr*ATR (en az min_risk_atr*ATR risk).
Hedef (kartta YOK; varsayım): giriş + hedef_r * risk.
Kaynak kartlar: uc-cizgi-vurus__graham, terk-edilmis-bebek__graham, iki-bosluk-deseni__graham, uc-kara-karga__graham,
  harami-capraz__graham.
Varsayımlar: "yakın kapanış", doji, güçlü mum eşikleri kartta sayısal değil (yakin=0.3, doji_oran=0.1, guclu_atr=1.0).
  BOŞLUK desenleri (terk_bebek, iki_bosluk): 7/24 kriptoda açılış ≈ önceki kapanış, gerçek boşluk neredeyse yok ->
  gevşek tanım: komşu mumların aralıkları en çok bosluk_tol_atr*ATR örtüşür; bu desenler kriptoda çok seyrek tetiklenir
  (kartta da "boşluklu desenler kriptoda tanımsız"). Hisse/emtia (TradFi) verisinde anlamlıdır.
Çelişkiler: üç çizgi vuruşunda 4. mumun açılışı için kart iki farklı ifade veriyor; "kapanışta veya altında açılır" alındı.
Negatif kanıt: kartlardaki %68-%84 doğruluk iddiaları Bulkowski'den ikinci el aktarım (Graham), kanıtsız; Bulkowski kendi
  mum istatistiklerinde bu desenlerin çoğunun tahmin gücünün zayıf olduğunu raporlar. Tek yazar. Stop/hedef kartlarda yok.
"""
import numpy as np
import pandas as pd

from motor.strateji.formasyon_b3 import (FormasyonTaban, MUM_DESENLERI, iki_yon, mum_cekirdek_tek)


class MumCokluFormasyon(FormasyonTaban):
    ad = "swing__mum-coklu-formasyon"
    stil = "swing"
    varsayilan_parametreler = {
        "desenler": "hepsi", "trend_n": 5, "trend_min_atr": 1.0, "yakin": 0.3, "doji_oran": 0.1,
        "guclu_atr": 1.0, "bosluk_tol_atr": 0.3, "hacim_filtre": 1, "tampon_atr": 0.5, "min_risk_atr": 0.5,
        "hedef_r": 2.0, "atr_periyot": 14, "long": True, "short": True,
    }
    parametre_izgarasi = {
        "trend_n": [3, 5, 8],
        "tampon_atr": [0.25, 0.5, 1.0],
        "hedef_r": [1.5, 2.0, 3.0],
    }

    def _secili(self):
        d = str(self.parametreler["desenler"]).strip()
        if d == "hepsi":
            return list(MUM_DESENLERI)
        adlar = [x.strip() for x in d.split(",") if x.strip()]
        bilinmeyen = set(adlar) - set(MUM_DESENLERI)
        if bilinmeyen:
            raise ValueError(f"Bilinmeyen desen: {sorted(bilinmeyen)}")
        return adlar

    def _hesapla(self, m, long_acik, short_acik):
        p = self.parametreler
        n = len(m)
        yon = np.zeros(n, dtype="int64")
        stop = np.full(n, np.nan)
        hedef = np.full(n, np.nan)
        for ad in self._secili():
            fonk, l_ok, s_ok = MUM_DESENLERI[ad]
            cek = mum_cekirdek_tek(fonk)
            y, s, h = iki_yon(m, lambda df, _c=cek: _c(df, p), long_acik and l_ok, short_acik and s_ok)
            yeni = (y != 0) & (yon == 0)
            yon[yeni], stop[yeni], hedef[yeni] = y[yeni], s[yeni], h[yeni]
        return yon, stop, hedef

    def cikis_var_mi(self) -> bool:
        return self.parametreler["hedef_r"] > 0
