"""Paper trading hesap motoru (Aşama 4): TEK hesap, artımlı (mum mum) çalışır, durumu diske yazılabilir.

KURAL: backtest motorunun muhasebe/dolum mantığı ile AYNI kod kullanılır. `motor.portfoy.motor._Motor`
(birleşik backtest çekirdeği: Decimal muhasebe, step aşağı yuvarlama, tick, taker komisyon, kayma, stop kayması, funding,
stop/hedef/kısmi/iz süren stop, zararda büyütme yasağı, sert limitler) alt sınıflanır; vektör dizileri yerine "o anki satır"
yuvaları (`_Yuva`) verilir. Var olan modüllerde tek satır değişmedi.

Bu sınıfın EKLEDİKLERİ (backtest çekirdeğinde olmayanlar)
  1. ARTIMLI ÇALIŞMA: `bar_isle(birim, t, mumlar, karar_fn)` = çekirdeğin ana döngüsündeki bir satır
     (1 funding, 2 bekleyen çıkış, 3 bekleyen giriş/hedef ağırlık, 4 mum içi stop/hedef, 6 kapanış değerleme + limitler,
     7 sonraki açılış için kararlar). Sinyal/ağırlık kararlarını `karar_fn(bar_sonrası)` üretir (strateji geçmişi <= t ile).
  2. ÇOK ZAMAN DİLİMLİ BİRİMLER: her "birim" (bir tek-grafik stratejisi ya da bir portföy stratejisi) kendi mum süresiyle
     kendi satırlarında işlenir; hesap ortaktır. Pozisyonlar sembolün SON BİLİNEN fiyatıyla değerlenir (en ince seri).
  3. KOL PAYLARI (sleeve): kilit testindeki set oynatmasıyla aynı ağırlıklar. Her kolun bir `grup`u ve `grup_payi`
     vardır: tek-grafik kolu (4 strateji) payı 0.5, portföy stratejileri 0.5/3 her biri. Boyutlandırma, işlem başı %1 risk ve
     toplam stop riski bütçesi (%5) GRUP özsermayesi (= hesap özsermayesi x grup payı) üzerindendir. Üstüne HESAP düzeyinde
     (pay 1) sert limitler ayrıca uygulanır: toplam stop riski <= %5, brüt <= 3x. Tek grup ve pay 1 ise (izole) bu, çekirdekle
     birebir aynıdır (iki kapsam aynı sayıları verir).
  4. ORTAK LİMİT KONTROLÜ: günlük kayıp (-%3) ve kill switch (%20) HESAP özsermayesi üzerindendir. Tetiklenince tetikleyen
     birimin pozisyonları çekirdek kuralıyla (sonraki açılışta, stop kayması) kapanır; DİĞER birimlerin pozisyonları
     BEKLEMEDEN son bilinen fiyattan (stop kayması) kapatılır (neden: kill_switch / gunluk_limit); yeni giriş/büyütme hiçbir
     birimde yapılmaz. Kill switch kalıcıdır (yeniden başlatma kaldırmaz).
  5. DURUM: `durum_al()` / `durum_yukle()` JSON-uyumlu anlık görüntü (Decimal metin, Timestamp ISO).
Paper'da limit_modu yalnız "uygula"dır ("olc" reddedilir).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Callable, Optional

import numpy as np
import pandas as pd

from motor.backtest.motor import D, SembolKurallari, _step_asagi, _tick
from motor.portfoy.motor import Kol, PortfoyAyarlari, _Emir, _Motor, _P
from motor.risk.limitler import SERT_LIMITLER
from motor.strateji import cikislar as cks

NAN = float("nan")


class _Yuva:
    """`dizi[i]` çağrısına i'yi yok sayıp o anki değeri döner (vektör dizisi yerine)."""
    __slots__ = ("v",)

    def __init__(self, v=NAN):
        self.v = v

    def __getitem__(self, i):
        return self.v


@dataclass
class PKol(Kol):
    grup: str = ""
    grup_payi: Decimal = Decimal(1)
    birim: str = ""
    sk: str = ""            # final_set strateji kimliği (raporlama)


@dataclass
class Birim:
    """Bir stratejinin satır akışı. `semboller`: bu birimin mumlarını okuduğu semboller (strateji sembolleri)."""
    ad: str
    tf: str
    aralik: pd.Timedelta
    kollar: list
    semboller: list
    son_t: Optional[pd.Timestamp] = None      # son işlenen satırın açılış zamanı


class PaperMotor(_Motor):
    def __init__(self, ayarlar: PortfoyAyarlari, kurallar: dict):
        if ayarlar.limit_modu != "uygula":
            raise ValueError("paper motoru yalnız limit_modu='uygula' ile çalışır (limitler ölçülmez, uygulanır)")
        ayarlar = dataclasses.replace(ayarlar, kurallar=dict(kurallar))
        super().__init__({}, [], ayarlar, {}, pd.DatetimeIndex([], tz="UTC"), None)
        self.tum_kollar: list = []
        self.birimler: dict = {}
        self.gun = None
        self.gun_basi = D(ayarlar.baslangic_sermaye)
        self.onceki_ozs = D(ayarlar.baslangic_sermaye)
        self.zirve = D(ayarlar.baslangic_sermaye)
        self.gunluk_kaydedildi = False
        self.gunluk_limit_sayisi = 0
        self.gun_kapanis: dict = {}               # "YYYY-MM-DD" -> o günün son özsermayesi (Decimal)
        self.ozs_son = D(ayarlar.baslangic_sermaye)
        self.son_zaman: Optional[pd.Timestamp] = None
        self.kurallar_tablo = dict(kurallar)
        self.maliyet_log: list = []               # {zaman, sk, tur: ucret|kayma|funding, tutar: Decimal} (raporlama; muhasebeyi etkilemez)
        self._acil = False

    # ------------------------------------------------------------------ maliyet kaydı (çekirdek yöntemlerini sarar, davranışı değiştirmez)
    def _maliyet(self, t, kol_veya_p, tur: str, tutar: Decimal) -> None:
        if tutar != 0:
            kol = kol_veya_p.kol if hasattr(kol_veya_p, "kol") else kol_veya_p
            self.maliyet_log.append({"zaman": t, "sk": kol.sk, "tur": tur, "tutar": tutar})

    def _giris(self, kol, yon, qty, px, stop, t, i, hedef=None, zc=None) -> None:
        ham = D(self.A[kol.sembol][i])
        self._maliyet(t, kol, "ucret", qty * px * self.taker)
        self._maliyet(t, kol, "kayma", qty * abs(px - ham))
        super()._giris(kol, yon, qty, px, stop, t, i, hedef=hedef, zc=zc)

    def _azalt(self, p, fiyat, qty, t, kom_orani, neden, kismi) -> None:
        q = min(qty, p.miktar)
        self._maliyet(t, p, "ucret", fiyat * q * kom_orani)
        if neden in ("hedef", "kismi", "kismi_tam", "veri_sonu"):
            ref = fiyat
        elif neden == "stop":
            ref = p.stop
        elif self._acil or not self.VAR[p.sembol][0]:
            ref = D(self.son_kap[p.sembol])
        else:
            ref = D(self.A[p.sembol][0])
        self._maliyet(t, p, "kayma", q * abs(fiyat - ref))
        super()._azalt(p, fiyat, qty, t, kom_orani, neden, kismi)

    def _funding_ode(self, p, bitis, dahil: bool) -> Decimal:
        x = super()._funding_ode(p, bitis, dahil)
        self._maliyet(bitis, p, "funding", x)
        return x

    # ------------------------------------------------------------------ kurulum
    def sembol_ekle(self, s: str, kural: SembolKurallari):
        if s in self.A:
            return
        self.sem_i[s] = len(self.semboller)
        self.semboller.append(s)
        self.A[s], self.Hh[s], self.Ll[s], self.C[s] = _Yuva(), _Yuva(), _Yuva(), _Yuva()
        self.VAR[s] = _Yuva(False)
        self.own_idx[s] = pd.DatetimeIndex([], tz="UTC")
        self.own_open[s] = np.array([], dtype=float)
        self.tick[s], self.step[s] = D(kural.tick_size), D(kural.step_size)
        self.min_qty[s], self.min_notional[s] = D(kural.min_qty), D(kural.min_notional)
        self.fund[s] = None
        self.son_kap[s] = NAN
        self.kurallar_tablo[s] = kural

    def birim_ekle(self, b: Birim):
        if b.ad in self.birimler:
            raise ValueError(f"birim tekrarlı: {b.ad}")
        self.birimler[b.ad] = b
        for k in b.kollar:
            k.birim = b.ad
            if k.mod == "agirlik":
                k.w, k.stop = _Yuva(), _Yuva()
            else:
                k.s_yon, k.s_stop, k.s_hedef = _Yuva(0), _Yuva(), _Yuva()
                k.s_cikis_l, k.s_cikis_s, k.s_zc, k.atr = _Yuva(False), _Yuva(False), _Yuva(), _Yuva()
            self.tum_kollar.append(k)

    def fiyat_serisi(self, s: str, idx: pd.DatetimeIndex, acilislar: np.ndarray):
        """Funding fiyatı için sembolün (en ince serinin) açılış fiyatları."""
        self.own_idx[s], self.own_open[s] = idx, acilislar

    def funding_serisi(self, s: str, idx: pd.DatetimeIndex, oranlar: np.ndarray):
        self.fund[s] = (idx, oranlar) if len(idx) else None

    # ------------------------------------------------------------------ değerleme yardımcıları (grup kapsamlı)
    def _kapsam(self, p, grup) -> bool:
        return grup is None or p.kol.grup == grup

    def _brut_k(self, i, haric=None, grup=None) -> Decimal:
        top = Decimal(0)
        for k, p in self.acik.items():
            if k != haric and self._kapsam(p, grup):
                top += abs(D(self._fiyat_ham(p.sembol, i, True)) * p.miktar)
        return top

    def _acik_risk_k(self, i, haric=None, grup=None) -> Decimal:
        top = Decimal(0)
        for k, p in self.acik.items():
            if k != haric and self._kapsam(p, grup):
                r = (D(self._fiyat_ham(p.sembol, i, True)) - p.stop) * p.miktar * p.yon
                if r > 0:
                    top += r
        return top

    # ------------------------------------------------------------------ boyutlandırma (grup payı)
    def _istenen_qty(self, kol, E, px, stop, w_abs, i) -> Decimal:
        Ek = E * kol.grup_payi
        qty_w = w_abs * Ek / px
        rb = abs(px - stop)
        if rb == 0:
            return Decimal(0)
        qty_r = Ek * (self.risk_oran if kol.mod == "sinyal" else self.top_risk) / rb
        return min(qty_w, qty_r)

    def _kap_orani(self, E, i, emirler, bekleyen_tahmin, grup, pay) -> Decimal:
        kap = Decimal(self.kal) * E * pay / (1 + Decimal(self.kal) * self.taker)
        hedefli = {e.kol.kimlik for e in emirler}
        sabit = Decimal(0)
        for k, p in self.acik.items():
            if k not in hedefli and self._kapsam(p, grup):
                sabit += abs(D(self._fiyat_ham(p.sembol, i, True)) * p.miktar)
        istek = bekleyen_tahmin + sum((e.ham * e.px for e in emirler if e.yon != 0), Decimal(0))
        f = Decimal(1)
        if istek > 0 and sabit + istek > kap:
            f = max(Decimal(0), (kap - sabit) / istek)
        return f

    def _risk_orantili_k(self, emirler, E, i, t, grup, pay) -> None:
        """Çekirdekteki `_risk_orantili` ile aynı; yalnız bütçe/sabit risk `grup` kapsamında (grup None: hesap)."""
        butce = self.top_risk * E * pay
        sabit = Decimal(0)
        artanlar = []
        hedefli = {e.kol.kimlik for e in emirler}
        for k, p in self.acik.items():
            if k not in hedefli and self._kapsam(p, grup):
                sabit += max((D(self._fiyat_ham(p.sembol, i, True)) - p.stop) * p.miktar * p.yon, Decimal(0))
        for e in emirler:
            if e.yon == 0:
                continue
            p = self.acik.get(e.kol.kimlik)
            cur = p.miktar if (p is not None and p.yon == e.yon) else Decimal(0)
            mtm_risk = (max((D(self._fiyat_ham(p.sembol, i, True)) - p.stop) * p.yon, Decimal(0)) if cur > 0
                        else Decimal(0))
            if e.kol.mod != "agirlik":
                sabit += e.qty * abs(e.px - e.stop)
                continue
            if e.qty <= cur:
                sabit += e.qty * mtm_risk
                continue
            sabit += cur * mtm_risk
            artanlar.append((e, cur, (e.qty - cur) * abs(e.px - e.stop)))
        istek = sum((a[2] for a in artanlar), Decimal(0))
        if istek <= 0 or sabit + istek <= butce:
            return
        f = max(Decimal(0), (butce - sabit) / istek)
        for e, cur, _ in artanlar:
            ist = e.qty
            yeni = cur + (e.qty - cur) * f
            e.qty = max(_step_asagi(yeni, self.step[e.kol.sembol]), cur)
            self._kirp(t, e.kol, "portfoy_risk", ist * e.px / E, e.qty * e.px / E)

    def _risk_orantili(self, emirler, E, i, t) -> None:
        if not emirler:
            return
        g = emirler[0].kol
        self._risk_orantili_k(emirler, E, i, t, g.grup, g.grup_payi)
        self._risk_orantili_k(emirler, E, i, t, None, Decimal(1))

    # ------------------------------------------------------------------ açılışta emir yürütme (çekirdeğin kopyası + grup kapsamı)
    def _emirleri_yurut(self, i, t) -> None:
        E = self._ozs(i, True)
        emirler, bekleyen_tahmin = self._hedef_emirleri_topla(i, t, E)
        if not emirler:
            return
        for e in emirler:
            e.ham = Decimal(0)
            if e.yon == 0:
                continue
            kol, s = e.kol, e.kol.sembol
            if (e.yon == 1 and e.stop >= e.px) or (e.yon == -1 and e.stop <= e.px):
                self._red(t, kol, e.yon, "gecersiz_stop")
                e.ham = None
                continue
            if e.sinyal and e.hedef is not None:
                e.hedef = _tick(e.hedef, self.tick[s])
            if e.sinyal and e.hedef is None and kol.cikis_ayarlari.sabit_r_hedefi:
                e.hedef = _tick(D(cks.r_hedef_fiyati(e.yon, float(e.px), float(abs(e.px - e.stop)),
                                                     kol.cikis_ayarlari.sabit_r_hedefi)), self.tick[s])
            if e.hedef is not None and (e.hedef - e.px) * e.yon <= 0:
                self._red(t, kol, e.yon, "gecersiz_hedef")
                e.ham = None
                continue
            e.ham = self._istenen_qty(kol, E, e.px, e.stop, e.w_abs, i)
        emirler = [e for e in emirler if not (e.ham is None)]
        if not emirler:
            return
        g0 = emirler[0].kol
        f = min(self._kap_orani(E, i, emirler, bekleyen_tahmin, g0.grup, g0.grup_payi),
                self._kap_orani(E, i, emirler, bekleyen_tahmin, None, Decimal(1)))
        for e in emirler:
            q = e.ham * f if e.yon != 0 else Decimal(0)
            e.qty = _step_asagi(q, self.step[e.kol.sembol]) if e.yon != 0 else Decimal(0)
            if f < 1 and e.yon != 0:
                self._kirp(t, e.kol, "kaldirac_orantili", e.w_abs, e.qty * e.px / E)
        self._risk_orantili(emirler, E, i, t)
        for e in emirler:
            kol = e.kol
            p = self.acik.get(kol.kimlik)
            if e.yon == 0:
                continue
            neden = None
            if self.kill:
                neden = "kill_switch"
            elif self.gunluk_blok:
                neden = "gunluk_kayip_limiti"
            elif self.islem_baslangic is not None and t < self.islem_baslangic and p is None:
                neden = "isinma"
            if neden is not None:
                artis = p is None or p.yon != e.yon or e.qty > p.miktar
                if artis:
                    self._red(t, kol, e.yon, neden)
                    if p is not None and p.yon == e.yon:
                        e.qty = min(e.qty, p.miktar)
                    else:
                        e.yon, e.qty = 0, Decimal(0)
        for e in emirler:                                    # Faz A: azaltma / kapatma
            kol, s = e.kol, e.kol.sembol
            p = self.acik.get(kol.kimlik)
            if p is None or kol.mod != "agirlik":
                continue
            if e.yon == p.yon and e.qty >= p.miktar:
                continue
            if e.yon != p.yon:
                red_q, neden = p.miktar, ("hedef_sifir" if e.yon == 0 else "yon_degisim")
            else:
                red_q = _step_asagi(p.miktar - e.qty, self.step[s])
                neden = "kucultme"
                if red_q <= 0:
                    continue
                if p.miktar - red_q < self.min_qty[s]:
                    red_q = p.miktar
                    neden = "hedef_sifir"
            fiyat = self._piyasa(s, p.yon, self.A[s][i], self.kayma)
            self._azalt(p, fiyat, red_q, t, self.taker, neden, True)
        for e in emirler:                                    # Faz B: açma / ekleme
            kol, s = e.kol, e.kol.sembol
            if e.yon == 0:
                continue
            p = self.acik.get(kol.kimlik)
            cur = p.miktar if p is not None else Decimal(0)
            if p is not None and p.yon != e.yon:
                continue
            hedef_q = e.qty
            if hedef_q <= cur:
                continue
            if p is not None and (D(self.A[s][i]) - p.giris) * p.yon < 0:
                self._kirp(t, kol, "zarar_buyutme", e.w_abs, cur * e.px / E)
                continue
            if p is None and self.max_poz is not None and len(self.acik) >= self.max_poz:
                self._red(t, kol, e.yon, "max_pozisyon")
                continue
            rb = abs(e.px - e.stop)
            butce = min(self.top_risk * E * kol.grup_payi - self._acik_risk_k(i, kol.kimlik, kol.grup),
                        self.top_risk * E - self._acik_risk_k(i, kol.kimlik, None))
            kisit = max(butce, Decimal(0)) / rb
            if kisit < hedef_q:
                self._kirp(t, kol, "toplam_risk", e.w_abs, kisit * e.px / E)
                hedef_q = _step_asagi(kisit, self.step[s])
                if hedef_q <= cur:
                    self._red(t, kol, e.yon, "toplam_risk_tavani")
                    continue
            kap1 = Decimal(self.kal) * E * kol.grup_payi / (1 + Decimal(self.kal) * self.taker)
            kap2 = Decimal(self.kal) * E / (1 + Decimal(self.kal) * self.taker)
            oda = min(kap1 - self._brut_k(i, kol.kimlik, kol.grup), kap2 - self._brut_k(i, kol.kimlik, None))
            ust = max(oda, Decimal(0)) / e.px
            if ust < hedef_q:
                self._kirp(t, kol, "kaldirac", e.w_abs, ust * e.px / E)
                hedef_q = _step_asagi(ust, self.step[s])
                if hedef_q <= cur:
                    self._red(t, kol, e.yon, "kaldirac_tavani")
                    continue
            ekle = hedef_q - cur
            if p is None:
                if hedef_q < self.min_qty[s] or hedef_q <= 0:
                    self._red(t, kol, e.yon, "min_qty")
                    continue
                if hedef_q * e.px < self.min_notional[s]:
                    self._red(t, kol, e.yon, "min_notional")
                    continue
            else:
                if ekle < self.min_qty[s] or ekle * e.px < self.min_notional[s]:
                    self._red(t, kol, e.yon, "min_notional")
                    continue
            if kol.mod == "agirlik" and e.ham < e.w_abs * E * kol.grup_payi / e.px - Decimal("1e-12"):
                self._kirp(t, kol, "risk", e.w_abs, e.ham * e.px / E)
            self._giris(kol, e.yon, ekle, e.px, e.stop, t, i, hedef=e.hedef, zc=e.zc)

    # ------------------------------------------------------------------ satır akışı
    def _satir_hazirla(self, b: Birim, mumlar: dict) -> None:
        self.kollar = b.kollar
        self.aralik = b.aralik
        for s in self.semboller:
            self.VAR[s].v = False
        for s, m in mumlar.items():
            if m is None:
                continue
            o, h, l, c = m
            self.A[s].v, self.Hh[s].v, self.Ll[s].v, self.C[s].v = float(o), float(h), float(l), float(c)
            self.VAR[s].v = True

    def _gun_kontrol(self, t) -> None:
        g = t.date()
        if self.gun is None or g > self.gun:
            self.gun, self.gun_basi, self.gunluk_blok, self.gunluk_kaydedildi = g, self.onceki_ozs, False, False

    def acilis_fazi(self, b: Birim, t, mumlar: dict) -> None:
        """Çekirdek ana döngüsü adım 1-3: funding, bekleyen çıkışlar, bekleyen girişler/hedef ağırlıklar."""
        self._satir_hazirla(b, mumlar)
        self._gun_kontrol(t)
        for p in list(self.acik.values()):
            if p.kol.birim == b.ad and self.VAR[p.sembol][0]:
                self.nakit -= self._funding_ode(p, t, True)
        for kol in b.kollar:
            p = self.acik.get(kol.kimlik)
            s = kol.sembol
            if p is None:
                kol.cikis_emri = kol.kucult_emri = None
                continue
            if not self.VAR[s][0]:
                continue
            if kol.cikis_emri:
                neden = kol.cikis_emri
                k = self.stop_kayma if neden in ("kill_switch", "gunluk_limit") else self.kayma
                self._azalt(p, self._piyasa(s, p.yon, self.A[s][0], k), p.miktar, t, self.taker, neden, False)
                kol.hedef_emri = None
            elif kol.kucult_emri is not None:
                f = D(kol.kucult_emri)
                q = _step_asagi(p.miktar * f, self.step[s])
                red_q = p.miktar - q
                if q < self.min_qty[s]:
                    red_q = p.miktar
                if red_q > 0:
                    self._kirp(t, kol, "kaldirac_azalt", 1.0, float(f))
                    self._azalt(p, self._piyasa(s, p.yon, self.A[s][0], self.kayma), red_q, t, self.taker,
                                "kaldirac_azalt", True)
            kol.cikis_emri = None
            kol.kucult_emri = None
        self._emirleri_yurut(0, t)

    def _acil_kapat(self, t, neden: str, haric_birim: str) -> None:
        """Diğer birimlerin pozisyonlarını beklemeden son bilinen fiyattan kapatır (stop kayması)."""
        self._acil = True
        for p in list(self.acik.values()):
            if p.kol.birim == haric_birim:
                continue
            fiyat_ham = self.son_kap[p.sembol]
            if fiyat_ham != fiyat_ham:                      # NaN: hiç mum görülmedi (olmamalı)
                raise RuntimeError(f"acil kapatma: {p.sembol} için fiyat yok")
            self.nakit -= self._funding_ode(p, t, False)
            self._azalt(p, self._piyasa(p.sembol, p.yon, fiyat_ham, self.stop_kayma), p.miktar, t, self.taker, neden, False)
            p.kol.cikis_emri = p.kol.kucult_emri = None
        self._acil = False

    def kapanis_fazi(self, b: Birim, t, karar_fn: Optional[Callable], son_satir: bool = False) -> None:
        """Adım 4-7. `karar_fn()` sinyal/ağırlık kararlarını döner: {kol_kimligi: {alan: değer}} (adım 7)."""
        L = SERT_LIMITLER
        for kol in b.kollar:
            p = self.acik.get(kol.kimlik)
            if p is None or not self.VAR[kol.sembol][0]:
                continue
            self._mum_ici(p, kol, 0, t)
        if son_satir:
            self.veri_sonu(b, t)
        for s in self.semboller:
            if self.VAR[s][0]:
                self.son_kap[s] = self.C[s][0]
        E = self._ozs(0, False)
        self.ozs_son = E
        self.onceki_ozs = E
        self.zirve = max(self.zirve, E)
        self.son_zaman = t + b.aralik
        self.gun_kapanis[str(self.gun)] = E
        dusus = (self.zirve - E) / self.zirve * 100
        kill_yeni = gunluk_yeni = False
        if not self.kill and dusus >= D(L.kill_switch_dusus_yuzde):
            self.kill = True
            kill_yeni = True
            self.limit_olaylari.append({"tur": "kill_switch", "zaman": t, "ozsermaye": float(E),
                                        "dusus_yuzde": float(dusus), "mod": "uygula"})
        gunluk_pct = (E - self.gun_basi) / self.gun_basi * 100
        if gunluk_pct <= -D(L.gunluk_max_kayip_yuzde):
            if not self.gunluk_kaydedildi:
                self.gunluk_kaydedildi = True
                gunluk_yeni = True
                self.gunluk_limit_sayisi += 1
                self.limit_olaylari.append({"tur": "gunluk_kayip", "zaman": t, "ozsermaye": float(E),
                                            "dusus_yuzde": float(-gunluk_pct), "mod": "uygula"})
            self.gunluk_blok = True
        if kill_yeni:
            self._acil_kapat(t + b.aralik, "kill_switch", b.ad)
        elif gunluk_yeni:
            self._acil_kapat(t + b.aralik, "gunluk_limit", b.ad)
        # 7) sonraki açılış için kararlar
        brut = sum((abs(D(self._fiyat_ham(p.sembol, 0, False)) * p.miktar) for p in self.acik.values()), Decimal(0))
        if self.kill:
            for kol in self.tum_kollar:
                kol.hedef_emri = None
                kol.giris_emri = None
                if kol.kimlik in self.acik and kol.birim == b.ad:
                    kol.cikis_emri = "kill_switch"
        elif self.gunluk_blok:
            for kol in b.kollar:
                if kol.kimlik in self.acik:
                    kol.cikis_emri = "gunluk_limit"
        else:
            if E > 0 and brut / E > D(self.kal):
                f = D(self.kal) / (brut / E) * Decimal("0.9999")
                for kol in b.kollar:
                    if kol.kimlik in self.acik and kol.cikis_emri is None:
                        kol.kucult_emri = float(f)
        self._kararlari_uygula(b, t, karar_fn() if karar_fn else {})

    def _kararlari_uygula(self, b: Birim, t, kararlar: dict) -> None:
        for kol in b.kollar:
            d = kararlar.get(kol.kimlik, {})
            if kol.mod == "agirlik":
                kol.w.v, kol.stop.v = d.get("w", NAN), d.get("stop", NAN)
                self._karar_agirlik(kol, 0, t)
            else:
                kol.s_yon.v, kol.s_stop.v, kol.s_hedef.v = d.get("yon", 0), d.get("stop", NAN), d.get("hedef", NAN)
                kol.s_cikis_l.v, kol.s_cikis_s.v = d.get("cikis_l", False), d.get("cikis_s", False)
                kol.s_zc.v, kol.atr.v = d.get("zc", NAN), d.get("atr", NAN)
                if self.VAR[kol.sembol][0]:
                    self._karar_sinyal(kol, 0, t)

    def ilk_karar(self, b: Birim, t, mumlar: dict, kararlar: dict) -> None:
        """Başlangıçta: son kapanmış barın kararlarını (bekleyen emirler) kurar; dolum/PnL yok (çekirdekte 'ısınma' satırı)."""
        self._satir_hazirla(b, mumlar)
        for s, m in mumlar.items():
            if m is not None:
                self.son_kap[s] = float(m[3])
        self._kararlari_uygula(b, t, kararlar)

    def veri_sonu(self, b: Birim, t) -> None:
        """Replay sonu: açık pozisyonları son kapanıştan kapatır (backtest 'veri_sonu' ile aynı)."""
        for p in list(self.acik.values()):
            if p.kol.birim != b.ad:
                continue
            s = p.sembol
            ham = self._fiyat_ham(s, 0, False)
            self.nakit -= self._funding_ode(p, t + b.aralik, False)
            self._azalt(p, _tick(D(ham), self.tick[s]), p.miktar, t + b.aralik, self.taker, "veri_sonu", False)

    # ------------------------------------------------------------------ raporlama yardımcıları
    def ozsermaye(self, fiyatlar: Optional[dict] = None) -> Decimal:
        top = self.nakit
        for p in self.acik.values():
            fp = (fiyatlar or {}).get(p.sembol)
            fp = self.son_kap[p.sembol] if fp is None else fp
            top += (D(fp) - p.giris) * p.miktar * p.yon
        return top

    def brut_kaldirac(self) -> Optional[float]:
        E = self.ozsermaye()
        if E <= 0:
            return None
        b = sum((abs(D(self.son_kap[p.sembol]) * p.miktar) for p in self.acik.values()), Decimal(0))
        return float(b / E)

    def acik_stop_riski(self) -> float:
        E = self.ozsermaye()
        r = Decimal(0)
        for p in self.acik.values():
            x = (D(self.son_kap[p.sembol]) - p.stop) * p.miktar * p.yon
            r += max(x, Decimal(0))
        return float(r / E) if E > 0 else 0.0

    # ------------------------------------------------------------------ durum (JSON)
    def durum_al(self) -> dict:
        kol_durum = {}
        for k in self.tum_kollar:
            kol_durum[k.kimlik] = {"hedef_emri": _enc(k.hedef_emri), "giris_emri": _enc(k.giris_emri),
                                   "cikis_emri": k.cikis_emri, "kucult_emri": k.kucult_emri}
        return _enc({
            "nakit": self.nakit, "kill": self.kill, "gunluk_blok": self.gunluk_blok, "gun": str(self.gun) if self.gun else None,
            "gun_basi": self.gun_basi, "onceki_ozs": self.onceki_ozs, "zirve": self.zirve, "ozs_son": self.ozs_son,
            "gunluk_kaydedildi": self.gunluk_kaydedildi, "gunluk_limit_sayisi": self.gunluk_limit_sayisi,
            "son_zaman": self.son_zaman, "toplam_notional": self.toplam_notional,
            "son_kap": self.son_kap, "gun_kapanis": self.gun_kapanis,
            "acik": {k: {f.name: getattr(p, f.name) for f in dataclasses.fields(p) if f.name != "kol"} | {"kol": p.kol.kimlik}
                     for k, p in self.acik.items()},
            "kol": kol_durum, "islemler": self.islemler, "reddedilenler": self.reddedilenler, "kirpmalar": self.kirpmalar,
            "limit_olaylari": self.limit_olaylari, "maliyet_log": self.maliyet_log,
            "birimler": {a: b.son_t for a, b in self.birimler.items()}})

    def durum_yukle(self, d: dict) -> None:
        d = _dec(d)
        self.nakit, self.kill, self.gunluk_blok = d["nakit"], d["kill"], d["gunluk_blok"]
        self.gun = pd.Timestamp(d["gun"]).date() if d["gun"] else None
        self.gun_basi, self.onceki_ozs, self.zirve, self.ozs_son = d["gun_basi"], d["onceki_ozs"], d["zirve"], d["ozs_son"]
        self.gunluk_kaydedildi, self.gunluk_limit_sayisi = d["gunluk_kaydedildi"], d["gunluk_limit_sayisi"]
        self.son_zaman, self.toplam_notional = d["son_zaman"], d["toplam_notional"]
        for s, v in d["son_kap"].items():
            if s in self.son_kap:
                self.son_kap[s] = v
        self.gun_kapanis = dict(d["gun_kapanis"])
        kollar = {k.kimlik: k for k in self.tum_kollar}
        self.acik = {}
        for k, pd_ in d["acik"].items():
            kol = kollar[pd_["kol"]]
            alan = {f.name for f in dataclasses.fields(_P)}
            kw = {a: pd_[a] for a in alan if a != "kol"}
            kw["kol"] = kol
            kw["kismi_bekleyen"] = tuple(tuple(x) for x in kw["kismi_bekleyen"])
            self.acik[k] = _P(**kw)
        for kid, kd in d["kol"].items():
            if kid not in kollar:
                raise ValueError(f"durum dosyasında bilinmeyen kol: {kid} (final set değişmiş olabilir)")
            k = kollar[kid]
            k.hedef_emri = tuple(kd["hedef_emri"]) if kd["hedef_emri"] is not None else None
            k.giris_emri = tuple(kd["giris_emri"]) if kd["giris_emri"] is not None else None
            k.cikis_emri, k.kucult_emri = kd["cikis_emri"], kd["kucult_emri"]
        self.islemler, self.reddedilenler = list(d["islemler"]), list(d["reddedilenler"])
        self.kirpmalar, self.limit_olaylari = list(d["kirpmalar"]), list(d["limit_olaylari"])
        self.maliyet_log = list(d.get("maliyet_log", []))
        for a, t in d["birimler"].items():
            if a in self.birimler:
                self.birimler[a].son_t = t


# ---------------------------------------------------------------------------- JSON kodlama (Decimal/Timestamp/NaN güvenli)
def _enc(x):
    if isinstance(x, Decimal):
        return {"__D": str(x)}
    if isinstance(x, pd.Timestamp):
        return {"__T": x.isoformat()}
    if isinstance(x, (np.floating, float)):
        x = float(x)
        return {"__N": 1} if x != x else x
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, tuple):
        return {"__L": [_enc(i) for i in x]}
    if isinstance(x, list):
        return [_enc(i) for i in x]
    if isinstance(x, dict):
        return {str(k): _enc(v) for k, v in x.items()}
    return x


def _dec(x):
    if isinstance(x, dict):
        if "__D" in x:
            return Decimal(x["__D"])
        if "__T" in x:
            return pd.Timestamp(x["__T"])
        if "__N" in x:
            return NAN
        if "__L" in x:
            return tuple(_dec(i) for i in x["__L"])
        return {k: _dec(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_dec(i) for i in x]
    return x
