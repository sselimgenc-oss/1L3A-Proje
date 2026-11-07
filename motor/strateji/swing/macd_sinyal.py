"""swing__macd-sinyal: MACD sinyal çizgisi / sıfır çizgisi kesişimi.

Kaynak kartlar: boxer, make, razaq, hogan, graham, johnson, kratter (sıfır geçişi);
impuls-sistemi (kratter) kodlanmadı (EMA13 + histogram rengi ayrı bir sistem).
Ortak çekirdek (kartlar): MACD(12,26,9) çizgisi sinyal çizgisini yukarı keserse long, aşağı keserse short;
alternatif tetik: MACD çizgisinin sıfırı geçmesi (mod="sifir"). Johnson: ters kesişimde çık.
Kanonik kural ile kart çelişkisi yok.

Varsayımlar (kitapta yok): kartların hiçbiri stop vermiyor -> stop = kapanış -/+ atr_k*ATR;
hedef yok (NaN), çıkış = ters kesişim (`cikis`). Boxer'ın "3 gün tutma" filtresi uygulanmadı.
sifir_filtre=True: sinyal kesişimi long için MACD>0, short için MACD<0 iken (Johnson s.66, "daha güçlü").

d11j EK SEÇENEKLER (varsayılanlar eskisiyle birebir aynı; ızgaraya girmez, ayar kaydıyla denenir):
  gosterge: "macd" (varsayılan) | trix, tsi, kvo, obv, ad, pvt, mfi, uo, emv, decycler (motor/strateji/_gosterge_d11j.py;
  periyotlar osc_n/osc_kisa/osc_uzun, 0 = göstergenin kendi varsayılanı) | "adx_di" (hat=+DI, sinyal=-DI, periyot osc_n=14).
  Hat için sinyal çizgisi = EMA/SMA(`sinyal`; `sinyal_tipi`); kaydirma>0 ise sinyal çizgisi yerine hattın kaydirma bar
  ÖNCEKİ değeri (kaydırılmış kopyayla kesişim). mod="esik": hat `esik` seviyesini yukarı/aşağı keser (mod="sifir" esik=0'dır).
  Kaynak ailelerin kural özeti: gosterge-sinyal-sifir-kesisimi (PVT/SMA21, MFI/EMA9, TRIX/SMA9, TSI/EMA13, KVO/EMA13,
  OBV/SMA21, A/D/SMA21, UO eşik, Decycler osilatörü) ve osilator-cizgi-kesisimi-genel (ADX +DI/-DI, kaydırılmış kopya).
  Farklı zaman diliminden osilatör kesişimi (H6) ve RVI KODLANMADI. EMV kaynakta H+L/H-L tutarsız: ölçekten bağımsız
  sinyal çizgisi kesişiminde kullanılır. Hacim tabanlı göstergeler (obv/ad/pvt/mfi/kvo/emv) hacim sütununu ister.
"""
import pandas as pd

from motor.strateji import _gosterge_d11j as j
from motor.strateji import gostergeler as g
from motor.strateji.swing._ortak import sinyal_cercevesi
from motor.strateji.temel import Strateji


class MacdSinyal(Strateji):
    ad = "swing__macd-sinyal"
    stil = "swing"
    varsayilan_parametreler = {
        "hizli": 12, "yavas": 26, "sinyal": 9,
        "mod": "sinyal",          # "sinyal": MACD x sinyal çizgisi | "sifir": MACD x 0 | "esik": hat x esik
        "sifir_filtre": False,
        "gosterge": "macd", "sinyal_tipi": "ema", "esik": 0.0, "kaydirma": 0,
        "osc_n": 0, "osc_kisa": 0, "osc_uzun": 0,
        "atr_periyot": 14, "atr_k": 2.0,
        "short": True,
    }
    parametre_izgarasi = {
        "mod": ["sinyal", "sifir"],
        "sinyal": [5, 9, 12],
        "atr_k": [1.5, 2.0, 3.0],
    }

    def sinyaller(self, mumlar: pd.DataFrame) -> pd.DataFrame:
        p = self.parametreler
        kap = mumlar["kapanis"]
        atr = g.atr(mumlar["yuksek"], mumlar["dusuk"], kap, p["atr_periyot"])
        hat, sin = self._hat_sinyal(mumlar)
        if p["mod"] == "esik":
            yukari = (hat > p["esik"]) & (hat.shift(1) <= p["esik"])
            asagi = (hat < p["esik"]) & (hat.shift(1) >= p["esik"])
        elif p["mod"] == "sifir":
            yukari = (hat > 0) & (hat.shift(1) <= 0)
            asagi = (hat < 0) & (hat.shift(1) >= 0)
        else:
            yukari = (hat > sin) & (hat.shift(1) <= sin.shift(1))
            asagi = (hat < sin) & (hat.shift(1) >= sin.shift(1))
            if p["sifir_filtre"]:
                yukari, asagi = yukari & (hat > 0), asagi & (hat < 0)
        gecerli = atr.notna() & hat.notna()
        long_ok = yukari & gecerli
        short_ok = asagi & gecerli & bool(p["short"])
        return sinyal_cercevesi(
            mumlar.index, long_ok, short_ok,
            kap - p["atr_k"] * atr, kap + p["atr_k"] * atr,
            cikis=(yukari | asagi) & gecerli)

    def _hat_sinyal(self, mumlar: pd.DataFrame):
        """(hat, sinyal çizgisi). Varsayılan (gosterge="macd", sinyal_tipi="ema", kaydirma=0) eski MACD hesabıdır."""
        p = self.parametreler
        kap = mumlar["kapanis"]
        if p["gosterge"] == "macd" and p["sinyal_tipi"] == "ema" and not p["kaydirma"]:
            m = g.macd(kap, p["hizli"], p["yavas"], p["sinyal"])
            return m["macd"], m["sinyal"]
        if p["gosterge"] == "macd":
            hat = g.ema(kap, p["hizli"]) - g.ema(kap, p["yavas"])
        elif p["gosterge"] == "adx_di":
            ax = g.adx(mumlar["yuksek"], mumlar["dusuk"], kap, int(p["osc_n"] or 14))
            hat, sin = ax["arti_di"], ax["eksi_di"]
            return hat, (hat.shift(int(p["kaydirma"])) if p["kaydirma"] else sin)
        else:
            hat = j.ozel_osc(p["gosterge"], mumlar, int(p["osc_n"]), int(p["osc_kisa"]), int(p["osc_uzun"]))
        if p["kaydirma"]:
            return hat, hat.shift(int(p["kaydirma"]))
        ma = g.ema if p["sinyal_tipi"] == "ema" else g.sma
        return hat, ma(hat, int(p["sinyal"]))

    def cikis_var_mi(self) -> bool:
        """Ters kesişim `cikis` üretir (her zaman)."""
        return True
