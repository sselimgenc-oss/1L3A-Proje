"""Kağıt al-sat motorları: backtest motorunun (backtest/kripto_motor._portfoy) kurallarını saat saat, artımlı uygular.

KGTAltPortfoy: tek bir gün başlangıcının (gun_bas) KGT alt portföyü. Her saat için `bar(...)` çağrılır:
  1) önceki kapanışta oluşan girişler bu mumun açılışında (öncelik: hacim sırası, maks. pozisyon / tek pozisyon /
     brüt sınırları, risk = özsermaye x risk_oran / stop yüzdesi),
  2) açık pozisyon yönetimi: bekleyen çıkış -> açılıştan; açılış stopun altındaysa açılıştan; mum içinde stop;
     yoksa 1R'de kısmi kâr + başabaş stop (aynı mumda başabaş: çözücü fonksiyon, yoksa OHLC yolu varsayımı),
     fonlama, 4S trend çıkış sinyali -> bir sonraki açılışta,
  3) bu mumun kapanışındaki yeni sinyaller -> bir sonraki açılışta giriş.
KMNDefter: piyasa nötr kesitsel momentum defteri. Dengeleme gününde hedef ağırlıklara gider (devir masrafı),
  aradaki saatlerde adetler sabit (pozisyon değerleri fiyatla değişir), fonlama damgalarında fonlama ödenir/alınır.
Tüm durum JSON'a yazılabilir sözlüklerdir.
"""
import math


class KGTAltPortfoy:
    def __init__(self, ad, sermaye, p, durum=None):
        self.ad = ad
        self.p = p
        d = durum or {}
        self.ozs = d.get("ozs", sermaye)              # gerçekleşmiş özsermaye (backtest motoru gibi)
        self.poz = d.get("poz", {})                   # sembol -> pozisyon sözlüğü
        self.bekleyen = d.get("bekleyen", {})         # sembol -> stop mesafesi (bir sonraki açılışta giriş)
        self.son_kapanis = d.get("son_kapanis", {})   # sembol -> son kapanış (brüt hesabı için)

    def durum(self):
        return dict(ad=self.ad, ozs=self.ozs, poz=self.poz, bekleyen=self.bekleyen, son_kapanis=self.son_kapanis)

    def bar(self, zaman, mumlar, sinyaller, cikislar, oncelik, fonlama, be_coz=None):
        """zaman: mumun açılış zamanı (str). mumlar: sembol -> (o, h, l, c). sinyaller: sembol -> stop mesafesi
        (bu mumun kapanışında giriş sinyali). cikislar: sembol -> -1 (long çıkış sinyali) / 0 / 1.
        oncelik: sembol -> hacim sırası (küçük önce). fonlama: sembol -> oran (bu mum bir fonlama damgasıysa).
        be_coz(sembol, giris, tp1) -> True/False/None: aynı mumda kısmi kârdan sonra başabaş vuruldu mu (1 dk veri).
        Döndürür: işlem kayıtları listesi. tur="kismi": 1R kısmi kâr satışı (pnl = o satışın kâr/zararı, R boş);
        tur="kapanis": pozisyonun kapanışı (pnl = kalan kısmın kâr/zararı, giriş masrafı ve fonlama dahil; R ve
        pnl_islem işlemin tamamı). Satırların pnl toplamı gerçekleşen toplam kâr/zarardır."""
        p = self.p; islemler = []
        # 1) bekleyen girişler (açılışta)
        if self.bekleyen:
            nacik = len(self.poz)
            brut = sum(x["miktar"] * self.son_kapanis.get(s, x["giris"]) for s, x in self.poz.items())
            for s in sorted(self.bekleyen, key=lambda s: oncelik.get(s, 999)):
                if s in self.poz or s not in mumlar:
                    continue
                if nacik >= p["max_poz"]:
                    break
                px = mumlar[s][0]; sd = self.bekleyen[s]
                if not (sd > 0) or not (px > 0):
                    continue
                notional = p["risk"] * self.ozs / (sd / px)
                notional = min(notional, p["max_pay"] * self.ozs, p["max_brut"] * self.ozs - brut)
                if notional <= 0.0005 * self.ozs:
                    continue
                m = notional / px
                masraf = notional * p["maliyet"]
                self.ozs -= masraf
                self.poz[s] = dict(yon=1, giris=px, miktar=m, q0=m, stop=px - sd, risk=sd, tp1=px + p["tp1_r"] * sd,
                                   tp1_yapildi=False, giris_zaman=zaman, ozs0=self.ozs + masraf, r_toplam=-masraf,
                                   fon=0.0, cikis_bekliyor=False)
                nacik += 1; brut += notional
        self.bekleyen = {}
        # 2) açık pozisyon yönetimi
        for s in list(self.poz):
            x = self.poz[s]
            if s not in mumlar:          # veri yok (geçici boşluk): pozisyon korunur
                continue
            o, h, l, c = mumlar[s]
            cik, sebep = None, None
            if x["cikis_bekliyor"]:
                cik, sebep = o, "sinyal"
            elif o <= x["stop"]:
                cik, sebep = o, "stop"
            elif l <= x["stop"]:
                cik, sebep = x["stop"], "stop"
            if sebep is None and p["tp1_r"] > 0 and not x["tp1_yapildi"] and h >= x["tp1"]:
                px = max(o, x["tp1"]); q = x["miktar"] * p["tp1_pay"]
                pnl = (px - x["giris"]) * q - q * px * p["maliyet"]
                self.ozs += pnl; x["r_toplam"] += pnl; x["miktar"] -= q; x["tp1_yapildi"] = True
                x["kismi_pnl"] = x.get("kismi_pnl", 0.0) + pnl
                islemler.append(dict(portfoy=self.ad, sembol=s, yon=x.get("yon", 1), tur="kismi",
                                     giris_zaman=x["giris_zaman"], cikis_zaman=zaman, giris=x["giris"], cikis=px,
                                     miktar=q, R=None, pnl=pnl, pnl_islem=None, sebep="tp1", tp1=True, fonlama=0.0))
                if p["be_tp1"] and x["giris"] > x["stop"]:
                    x["stop"] = x["giris"]
                vur = be_coz(s, x["giris"], x["tp1"]) if be_coz else None
                if vur is None:                                  # OHLC yolu varsayımı (backtest ici_sira=1)
                    vur = (c < o and l <= x["stop"]) or c <= x["stop"]
                if vur:
                    cik, sebep = x["stop"], "stop"
            if sebep is not None:
                q = x["miktar"]
                pnl = (cik - x["giris"]) * q - q * cik * p["maliyet"]
                self.ozs += pnl; x["r_toplam"] += pnl
                islemler.append(dict(portfoy=self.ad, sembol=s, yon=x.get("yon", 1), tur="kapanis",
                                     giris_zaman=x["giris_zaman"], cikis_zaman=zaman, giris=x["giris"], cikis=cik,
                                     miktar=q, R=x["r_toplam"] / (x["q0"] * x["risk"]),
                                     pnl=x["r_toplam"] - x.get("kismi_pnl", 0.0), pnl_islem=x["r_toplam"],
                                     sebep=sebep, tp1=x["tp1_yapildi"], fonlama=x["fon"]))
                del self.poz[s]
                continue
            f = fonlama.get(s, 0.0)
            if f:
                od = -x["miktar"] * c * f
                self.ozs += od; x["fon"] += od; x["r_toplam"] += od
            if cikislar.get(s, 0) == -1:
                x["cikis_bekliyor"] = True
        # 3) yeni sinyaller (kapanışta)
        for s, sd in sinyaller.items():
            if s not in self.poz and sd and sd > 0:
                self.bekleyen[s] = sd
        for s, m in mumlar.items():
            self.son_kapanis[s] = m[3]
        return islemler

    def deger(self, fiyat):
        """Piyasa değeriyle özsermaye (backtest eğrisi gibi: gerçekleşmiş + açık kâr/zarar)."""
        return self.ozs + sum((fiyat.get(s, x["giris"]) - x["giris"]) * x["miktar"] for s, x in self.poz.items())


class KMNDefter:
    def __init__(self, ad, sermaye, maliyet, durum=None):
        self.ad = ad; self.maliyet = maliyet
        d = durum or {}
        self.deger_ = d.get("deger", sermaye)      # defter değeri
        self.maruz = d.get("maruz", {})            # sembol -> işaretli pozisyon değeri ($, long > 0)
        self.fiyat = d.get("fiyat", {})            # sembol -> son fiyat

    def durum(self):
        return dict(deger=self.deger_, maruz=self.maruz, fiyat=self.fiyat)

    def fiyatla(self, fiyat):
        """Yeni fiyatlarla pozisyon değerlerini ve defteri güncelle (adetler sabit)."""
        for s in list(self.maruz):
            if s in fiyat and s in self.fiyat and self.fiyat[s] > 0:
                r = fiyat[s] / self.fiyat[s] - 1
                self.deger_ += self.maruz[s] * r
                self.maruz[s] *= (1 + r)
        for s, v in fiyat.items():
            self.fiyat[s] = v

    def fonla(self, fonlama):
        od = -sum(self.maruz[s] * f for s, f in fonlama.items() if s in self.maruz)
        self.deger_ += od
        return od

    def dengele(self, hedef, fiyat):
        """hedef: sembol -> ağırlık. Devir masrafı düşülür. Döndürür: (devir $, masraf $)."""
        yeni = {s: w * self.deger_ for s, w in hedef.items() if s in fiyat}
        tum = set(yeni) | set(self.maruz)
        devir = sum(abs(yeni.get(s, 0.0) - self.maruz.get(s, 0.0)) for s in tum)
        masraf = devir * self.maliyet
        self.deger_ -= masraf
        self.maruz = {s: v for s, v in yeni.items() if v != 0}
        for s in yeni:
            self.fiyat[s] = fiyat[s]
        return devir, masraf
