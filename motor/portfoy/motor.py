"""Çok enstrümanlı portföy backtest motoru (karar 23). Ortak hesap, ortak sert limitler.

Mimari
  - `portfoy_backtest(veriler, strateji, ayarlar, fundingler)`: PortfoyStratejisi'nin hedef ağırlıkları.
  - `birlesik.birlesik_backtest(...)`: tek-grafik stratejileri "kol" olarak aynı hesapta.
  İkisi de aynı çekirdeği (`_Motor`) kullanır: her "kol" bir (strateji, sembol) çiftidir, kendi pozisyonu vardır.
  Ağırlık kolları (mod="agirlik") sembol başına bir kol; sinyal kolları (mod="sinyal") tek-grafik Strateji sinyalleriyle
  çalışır (stop/hedef/iz süren stop/kısmi/zaman çıkışı tek-grafik motoruyla aynı kurallar).

Ortak zaman ekseni ve farklı işlem saatleri
  - Eksen = tüm sembol indekslerinin birleşimi. Tüm semboller AYNI mum süresinde olmalı (yoksa ValueError).
  - Bir sembolün mumu olmayan satırda: o sembolde dolum/stop kontrolü yapılmaz, bekleyen emir ilk açık bara kayar
    (hedef ağırlık emirlerinde en son emir geçerlidir). Pozisyon son bilinen KAPANIŞ ile DEĞERLENİR (ileri doldurma
    yalnız değerleme içindir; sinyal hesabı stratejinin kendi verisiyle yapılır, motor sinyale fiyat vermez).
  - Funding'de fiyat: funding zamanından önceki son mumun açılışı (tek-grafik motoruyla aynı).
  - Hisse seansı gibi kısmi günlük mumlarda "gün" = UTC takvim günü; günlük kayıp özsermaye (MTM) üzerinden hesaplanır.

Dolum (tek-grafik motoruyla aynı): sinyal t kapanışında, dolum o sembolün sonraki mumunun AÇILIŞINDA.
  Alış: açılış*(1+kayma_bps), satış: açılış*(1-kayma_bps) (tick'e yuvarlanır); taker komisyon; stop çıkışı/gap/
  kill/günlük limit çıkışı `stop_kayma_bps`; miktar step_size'a AŞAĞI yuvarlanır; min_qty/min_notional altı reddedilir.
  Sembol kuralları `motor.arastirma.tarama.SEMBOL_KURALLARI` (yoksa VARSAYILAN_KURAL) — ayarlar.kurallar ile ezilebilir.
  Funding: pozisyon açıkken nominal * oran * yön; fundingler[sembol] DataFrame (VERI_SOZLESMESI), yoksa 0.
  Stop: mum içi; aynı mumda stop görülürse stop kazanır; açılış stopun ötesindeyse dolum açılıştan ("stop_gap").
  Veri sonunda açık pozisyonlar son bilinen kapanıştan kapanır ("veri_sonu").

SERT LİMİTLER (motor.risk.limitler.SERT_LIMITLER; ayarlar aşarsa tavana kırpılır, uyarilar'a yazılır)
  1. İşlem başı risk: bir pozisyonun dolum fiyatından stopuna kadar kaybı <= risk_yuzde * özsermaye (özsermaye
     dolum anındaki MTM). Hedef ağırlık bunu aşıyorsa miktar KÜÇÜLTÜLÜR ve `kirpmalar`a "risk" olarak yazılır.
     SİNYAL kollarında bu kayıp MALİYET DAHİLDİR (2026-11-09): |px − stop| + max(px, stop)·(stop_kayma + 2·taker), sembolün
     maliyetiyle (limitler.maliyetli_risk_birim). Ağırlık kolları (karar 25) fiyat riskiyle ölçülür.
  2. Toplam brüt maruziyet <= kaldirac(3x) * özsermaye (dolum anında, komisyon payı dahil):
     (a) emirler arası ORANTILI küçültme: sabit kalan pozisyonlar + istenen hedefler tavanı aşıyorsa tüm hedef
         pozisyon büyüklükleri aynı oranda küçültülür ("kaldirac_orantili");
     (b) dolum sırasında SERT kontrol (azaltmalar önce, artışlar sonra): tavan aşılacaksa miktar kısılır;
     (c) fiyat kayması yüzünden kapanışta brüt > tavan çıkarsa ertesi açılışta tüm pozisyonlar oranla küçültülür
         ("kaldirac_azalt"). Kapanış maruziyeti bu yüzden bir bar boyunca geçici olarak tavanı aşabilir.
  3. Günlük kayıp: UTC günü içinde portföy MTM'si gün başına göre <= -%3 olursa (bar kapanışında) tüm pozisyonlar
     sonraki açılışta kapanır ("gunluk_limit") ve o UTC günü yeni giriş/büyütme olmaz.
  4. Kill switch: özsermaye zirveden %20 düşerse tüm pozisyonlar kapanır ("kill_switch"), bir daha işlem açılmaz.
  limit_modu="olc": 3 ve 4 işlemi durdurmaz, yalnız `limit_olaylari`na yazar (SADECE araştırma). 1 ve 2 her iki
  modda uygulanır.
  5. Portföy toplam riski (karar 25, kullanıcı onaylı 2026-11-07): AĞIRLIK kollarında pozisyon başına %1 yerine açık +
     yeni pozisyonların stopa kadar TOPLAM riski <= portfoy_toplam_risk_yuzde (%5) x MTM özsermaye; tek pozisyon da en
     fazla %5 taşıyabilir. Aşılırsa yeni/artan hedefler ORANTILI küçültülür ("portfoy_risk"). SİNYAL kollarında işlem
     başı %1 (1. madde) aynen geçerlidir. Ayar (toplam_risk_tavani_yuzde) bu değeri aşamaz (kırpılır, uyarı yazılır).
  Ek (ayarla): toplam_risk_tavani_yuzde (sert değerin altına inebilir) ve max_pozisyon.
ZARARDAKİ POZİSYON BÜYÜTÜLEMEZ (ortalama düşürme yasağı): ağırlık kolunda, mevcut pozisyon dolum anında zarardaysa
  (açılış fiyatı < ortalama giriş, long için) hedef büyüklük mevcudu AŞAMAZ; yalnız küçültme/kapatma yapılır
  ("zarar_buyutme" kirpmalar'a yazılır). Kârdaki pozisyona ekleme ve yeniden dengelemede küçültme serbesttir.

Çıktı: SonucPortfoy (bkz. sınıf). Muhasebe Decimal; tablolar float.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

import numpy as np
import pandas as pd

from motor.backtest import metrikler as mtr
from motor.backtest.motor import D, SembolKurallari, _step_asagi, _tick
from motor.risk.limitler import SERT_LIMITLER, maliyetli_risk_birim
from motor.strateji import cikislar as cks
from motor.strateji.cikislar import CikisAyarlari
from motor.strateji.seans_takvimi import mum_suresi
from motor.portfoy.temel import PortfoyStratejisi, ortak_eksen

ISLEM_KOLONLARI = ["sembol", "kol", "yon", "giris_zamani", "giris_fiyati", "cikis_zamani", "cikis_fiyati", "miktar",
                   "brut_pnl", "komisyon", "funding", "net_pnl", "r", "cikis_nedeni", "kismi_sayisi", "kismi_pnl"]


@dataclass
class PortfoyAyarlari:
    baslangic_sermaye: float = 10000.0
    risk_yuzde: float = 1.0                  # SİNYAL kollarında işlem başına stopa kadar risk (%); sert limitle kırpılır
    kaldirac: float = 3.0                    # toplam brüt maruziyet tavanı (özsermaye katı); sert limitle kırpılır
    komisyon_taker_yuzde: float = 0.05
    komisyon_maker_yuzde: float = 0.02
    hedef_limit_emri: bool = False
    kayma_bps: float = 2.0
    stop_kayma_bps: float = 5.0
    limit_modu: str = "uygula"               # "uygula" | "olc" (yalnız araştırma)
    toplam_risk_tavani_yuzde: Optional[float] = None   # açık pozisyonların stopa kadar toplam riski; None: sert değer (%5); sert değeri aşamaz
    max_pozisyon: Optional[int] = None                 # aynı anda açık kol sayısı; None: yok
    kurallar: Optional[dict] = None                    # {sembol: SembolKurallari}; yoksa tarama.SEMBOL_KURALLARI
    # Sembol başına maliyet (araştırma; evren maliyet tablosu): {sembol: (taker_yuzde, maker_yuzde, kayma_bps, stop_kayma_bps)}.
    # Listede olmayan sembol yukarıdaki tek değerleri kullanır. None: tek değer (varsayılan, eski davranış).
    maliyet_sembol: Optional[dict] = None


def sembol_kurali(sembol: str, ayarlar: PortfoyAyarlari) -> SembolKurallari:
    if ayarlar.kurallar and sembol in ayarlar.kurallar:
        return ayarlar.kurallar[sembol]
    from motor.arastirma import tarama     # yerel içe aktarma: ağır modül, döngü riski
    return tarama.SEMBOL_KURALLARI.get(sembol, tarama.VARSAYILAN_KURAL)


@dataclass
class Kol:
    """Bir (strateji, sembol) çifti. Diziler ortak eksen uzunluğundadır."""
    kimlik: str
    sembol: str
    mod: str                                   # "agirlik" | "sinyal"
    strateji_ad: str = ""
    # agirlik modu
    w: Optional[np.ndarray] = None             # hedef ağırlık (NaN: değişiklik yok)
    stop: Optional[np.ndarray] = None          # stop fiyatı (NaN: yok)
    # sinyal modu
    s_yon: Optional[np.ndarray] = None
    s_stop: Optional[np.ndarray] = None
    s_hedef: Optional[np.ndarray] = None
    s_cikis_l: Optional[np.ndarray] = None
    s_cikis_s: Optional[np.ndarray] = None
    s_zc: Optional[np.ndarray] = None
    atr: Optional[np.ndarray] = None
    s_gsk: Optional[np.ndarray] = None         # gün sonu kapanış bayrağı (seanslı veri; None: yok). Bkz. _gun_sonu_kapat
    cikis_ayarlari: CikisAyarlari = field(default_factory=CikisAyarlari)
    # çalışma durumu
    hedef_emri: Optional[tuple] = None         # agirlik: (yon, w_abs, stop_ham)
    giris_emri: Optional[tuple] = None         # sinyal: (yon, stop, hedef, zc)
    cikis_emri: Optional[str] = None
    kucult_emri: Optional[float] = None


@dataclass
class SonucPortfoy:
    islemler: pd.DataFrame
    ozsermaye: pd.Series                       # her ortak-eksen satırının kapanışında MTM özsermaye
    gunluk_ozsermaye: pd.Series                # UTC gün sonu MTM
    agirlik_gecmisi: pd.DataFrame              # sembol başına (net nominal / özsermaye), satır kapanışı
    pozisyon_gecmisi: pd.DataFrame             # sembol başına net miktar (işaretli)
    maruziyet: pd.DataFrame                    # brut, net (özsermaye oranı), pozisyon_sayisi
    maruziyet_dolum: pd.Series                 # dolumlardan hemen sonra brüt/özsermaye (sert limit testi için)
    reddedilenler: list
    kirpmalar: list                            # {zaman, kol, sembol, tur, istenen_agirlik, uygulanan_agirlik}
    uyarilar: list
    baslangic_sermaye: float
    limit_olaylari: list = field(default_factory=list)
    toplam_notional: float = 0.0               # tüm dolumların mutlak nominal toplamı (devir için)

    def devir(self) -> dict:
        ort = float(self.ozsermaye.mean())
        yil = max((self.ozsermaye.index[-1] - self.ozsermaye.index[0]).total_seconds() / mtr.YIL_SANIYE, 1e-9)
        return {"toplam_notional": self.toplam_notional,
                "devir_katsayisi": self.toplam_notional / ort if ort else np.nan,    # ortalama özsermaye katı
                "devir_yillik": self.toplam_notional / ort / yil if ort else np.nan}

    def metrikler(self) -> dict:
        m = mtr.hesapla(self.islemler, self.ozsermaye, self.baslangic_sermaye)
        d = self.devir()
        m["ort_pozisyon_sayisi"] = float(self.maruziyet["pozisyon_sayisi"].mean())
        m["ort_brut_maruziyet"] = float(self.maruziyet["brut"].mean())
        m["max_brut_maruziyet"] = float(self.maruziyet["brut"].max())
        m["ort_net_maruziyet"] = float(self.maruziyet["net"].mean())
        m["devir_katsayisi"] = d["devir_katsayisi"]
        m["devir_yillik"] = d["devir_yillik"]
        m["kirpma_sayisi"] = len(self.kirpmalar)
        m["reddedilen_sayisi"] = len(self.reddedilenler)
        return m


@dataclass
class _P:
    kol: Kol
    sembol: str
    yon: int
    miktar: Decimal
    giris: Decimal                  # ortalama giriş
    zaman: pd.Timestamp
    stop: Decimal
    ilk_stop: Decimal
    hedef: Optional[Decimal]
    giris_kom: Decimal
    son_f: pd.Timestamp
    ekstrem: float
    zaman_limit: Optional[int]
    risk_tutar: Decimal
    tepe_miktar: Decimal
    funding: Decimal = Decimal(0)
    tutulan: int = 0
    brut_toplam: Decimal = Decimal(0)
    cikis_kom: Decimal = Decimal(0)
    cikis_qty: Decimal = Decimal(0)
    cikis_notional: Decimal = Decimal(0)
    kismi_sayisi: int = 0
    kismi_net: Decimal = Decimal(0)
    kismi_bekleyen: tuple = ()
    ilk_miktar: Decimal = Decimal(0)


@dataclass
class _Emir:
    kol: Kol
    yon: int                        # hedef yön (-1, 0, +1)
    w_abs: Decimal
    stop: Optional[Decimal]
    hedef: Optional[Decimal] = None
    zc: Optional[int] = None
    sinyal: bool = False
    px: Optional[Decimal] = None    # hedef yöndeki dolum fiyatı
    qty: Decimal = Decimal(0)       # sınırlandırılmış hedef büyüklük (mutlak)
    ham: Decimal = Decimal(0)


class _Motor:
    def __init__(self, veriler, kollar, ayarlar, fundingler, eksen, islem_baslangic=None):
        self.ay = ayarlar
        L = SERT_LIMITLER
        self.uyarilar = []
        self.risk_yuzde = min(ayarlar.risk_yuzde, L.islem_basi_max_risk_yuzde)
        self.kal = min(ayarlar.kaldirac, L.max_kaldirac)
        if self.risk_yuzde < ayarlar.risk_yuzde:
            self.uyarilar.append(f"risk_yuzde {ayarlar.risk_yuzde} -> {self.risk_yuzde} (sert limit)")
        if self.kal < ayarlar.kaldirac:
            self.uyarilar.append(f"kaldirac {ayarlar.kaldirac} -> {self.kal} (sert limit)")
        if ayarlar.limit_modu not in ("uygula", "olc"):
            raise ValueError("limit_modu 'uygula' veya 'olc' olmalı")
        self.olc = ayarlar.limit_modu == "olc"
        self.risk_oran = D(self.risk_yuzde) / 100
        self.taker, self.maker = D(ayarlar.komisyon_taker_yuzde) / 100, D(ayarlar.komisyon_maker_yuzde) / 100
        self.kayma = D(ayarlar.kayma_bps) / 10000
        self.stop_kayma = D(ayarlar.stop_kayma_bps) / 10000
        # semboller arası farklı maliyet (opsiyonel): {sembol: (taker_yuzde, maker_yuzde, kayma_bps, stop_kayma_bps)}; yoksa tek değer
        self.mal = {s: (D(a) / 100, D(b) / 100, D(c) / 10000, D(d) / 10000)
                    for s, (a, b, c, d) in (ayarlar.maliyet_sembol or {}).items()}
        self.taker_en_yuksek = max([self.taker] + [v[0] for v in self.mal.values()])
        self.kayma_en_yuksek = max([self.kayma] + [v[2] for v in self.mal.values()])
        # brüt tavan paydasındaki birim maliyet: dolum fiyatı (kayma dahil) üzerinden nominal + komisyon + kayma kaybı özsermayeden düşer
        # (B10, 2026-11-10: kayma payda dışındaydı -> dolumdan sonra kaldıraç ~%0.2 üstte kalıyordu)
        self.kap_maliyet = self.taker_en_yuksek + self.kayma_en_yuksek
        top_sert = L.portfoy_toplam_risk_yuzde
        top = top_sert if ayarlar.toplam_risk_tavani_yuzde is None else min(ayarlar.toplam_risk_tavani_yuzde, top_sert)
        if ayarlar.toplam_risk_tavani_yuzde is not None and ayarlar.toplam_risk_tavani_yuzde > top_sert:
            self.uyarilar.append(f"toplam_risk_tavani_yuzde {ayarlar.toplam_risk_tavani_yuzde} -> {top_sert} (sert limit)")
        self.top_risk = D(top) / 100          # her zaman var: portföy toplam stop riski tavanı (karar 25)
        self.max_poz = ayarlar.max_pozisyon
        self.islem_baslangic = islem_baslangic
        self.kollar = kollar
        self.eksen = eksen
        self.Z = list(eksen)
        n = self.n = len(eksen)

        self.semboller = list(veriler)
        self.sem_i = {s: k for k, s in enumerate(self.semboller)}
        self.A, self.Hh, self.Ll, self.C, self.VAR = {}, {}, {}, {}, {}
        self.own_idx, self.own_open, self.tick, self.step, self.min_qty, self.min_notional = {}, {}, {}, {}, {}, {}
        self.fund = {}
        araliklar = {}
        for s, df in veriler.items():
            self.A[s] = df["acilis"].reindex(eksen).to_numpy(dtype=float)
            self.Hh[s] = df["yuksek"].reindex(eksen).to_numpy(dtype=float)
            self.Ll[s] = df["dusuk"].reindex(eksen).to_numpy(dtype=float)
            self.C[s] = df["kapanis"].reindex(eksen).to_numpy(dtype=float)
            self.VAR[s] = eksen.isin(df.index)
            self.own_idx[s] = df.index
            self.own_open[s] = df["acilis"].to_numpy(dtype=float)
            k = sembol_kurali(s, ayarlar)
            self.tick[s], self.step[s] = D(k.tick_size), D(k.step_size)
            self.min_qty[s], self.min_notional[s] = D(k.min_qty), D(k.min_notional)
            f = (fundingler or {}).get(s)
            self.fund[s] = ((f.index, f["oran"].to_numpy(dtype=float)) if f is not None and len(f) else None)
            if len(df) > 1:
                araliklar[s] = mum_suresi(df.index)   # mod: seans/gece boşluklarından etkilenmez
        if len(set(araliklar.values())) > 1:
            raise ValueError(f"Semboller farklı mum süresinde: {araliklar}")
        self.aralik = next(iter(araliklar.values())) if araliklar else pd.Timedelta(0)

        self.nakit = D(ayarlar.baslangic_sermaye)
        self.acik: dict[str, _P] = {}
        self.islemler, self.reddedilenler, self.kirpmalar, self.limit_olaylari = [], [], [], []
        self.son_kap = {s: np.nan for s in self.semboller}
        self.toplam_notional = Decimal(0)
        self.kill, self.gunluk_blok = False, False

    # ------------------------------------------------------------------ yardımcılar
    def _fiyat_ham(self, s, i, acilista: bool) -> float:
        """Değerleme fiyatı: mumu varsa açılış/kapanış, yoksa son bilinen kapanış."""
        if self.VAR[s][i]:
            return self.A[s][i] if acilista else self.C[s][i]
        return self.son_kap[s]

    def _ozs(self, i, acilista: bool) -> Decimal:
        top = self.nakit
        for p in self.acik.values():
            top += (D(self._fiyat_ham(p.sembol, i, acilista)) - p.giris) * p.miktar * p.yon
        return top

    def _brut(self, i, acilista: bool, haric: Optional[str] = None) -> Decimal:
        top = Decimal(0)
        for k, p in self.acik.items():
            if k != haric:
                top += abs(D(self._fiyat_ham(p.sembol, i, acilista)) * p.miktar)
        return top

    def _acik_risk(self, i, acilista: bool, haric: Optional[str] = None) -> Decimal:
        top = Decimal(0)
        for k, p in self.acik.items():
            if k != haric:
                r = (D(self._fiyat_ham(p.sembol, i, acilista)) - p.stop) * p.miktar * p.yon
                if r > 0:
                    top += r
        return top

    def _tk(self, s):
        return self.mal[s][0] if s in self.mal else self.taker

    def _mk(self, s):
        return self.mal[s][1] if s in self.mal else self.maker

    def _ky(self, s):
        return self.mal[s][2] if s in self.mal else self.kayma

    def _sk(self, s):
        return self.mal[s][3] if s in self.mal else self.stop_kayma

    def _piyasa(self, s, yon_pozisyon: int, ham, k: Decimal) -> Decimal:
        """Pozisyon yönünün tersine işlem: long satar -> düşük, short alır -> yüksek."""
        return _tick(D(ham) * (1 - yon_pozisyon * k), self.tick[s])

    def _funding_ode(self, p: _P, bitis, dahil: bool) -> Decimal:
        fz = self.fund[p.sembol]
        if fz is None:
            return Decimal(0)
        zamanlar, oranlar = fz
        a = zamanlar.searchsorted(p.son_f, side="right")
        b = zamanlar.searchsorted(bitis, side="right" if dahil else "left")
        toplam = Decimal(0)
        oi, oo = self.own_idx[p.sembol], self.own_open[p.sembol]
        for k in range(a, b):
            j = max(oi.searchsorted(zamanlar[k], side="right") - 1, 0)
            toplam += p.miktar * D(oo[j]) * D(oranlar[k]) * p.yon
        p.funding += toplam
        if dahil and b > a:
            # imleç ÖDENEN son funding kaydına ilerler (bitis'e değil): bitis'ten önceki ama henüz gelmemiş (geç gelen, paper funding'i 30 dk'da
            # bir yeniler) kayıt sonraki çağrıda bir kez ödenir; ödenen kayıt tekrar ödenmez (B05). Backtest'te tüm kayıtlar baştan var,
            # (son ödenen, bitis] aralığında kayıt olmadığı için sonuç eskisiyle birebir aynıdır.
            p.son_f = max(p.son_f, zamanlar[b - 1])
        return toplam

    def _kirp(self, t, kol, tur, istenen, uygulanan):
        self.kirpmalar.append({"zaman": t, "kol": kol.kimlik, "sembol": kol.sembol, "tur": tur,
                               "istenen_agirlik": float(istenen), "uygulanan_agirlik": float(uygulanan)})

    def _red(self, t, kol, yon, neden):
        self.reddedilenler.append({"zaman": t, "kol": kol.kimlik, "sembol": kol.sembol, "yon": yon, "neden": neden})

    # ------------------------------------------------------------------ dolum işlemleri
    def _azalt(self, p: _P, fiyat: Decimal, qty: Decimal, t, kom_orani: Decimal, neden: str, kismi: bool) -> None:
        """Pozisyonun bir kısmını (ya da tamamını: qty >= miktar) kapatır; tamamıysa işlem satırı yazılır."""
        qty = min(qty, p.miktar)
        brut = (fiyat - p.giris) * qty * p.yon
        kom = fiyat * qty * kom_orani
        self.nakit += brut - kom
        self.toplam_notional += fiyat * qty
        p.brut_toplam += brut
        p.cikis_kom += kom
        p.cikis_qty += qty
        p.cikis_notional += fiyat * qty
        p.miktar -= qty
        if p.miktar > 0:
            p.kismi_sayisi += 1
            p.kismi_net += brut - kom
            return
        net = p.brut_toplam - p.giris_kom - p.cikis_kom - p.funding
        ort_cikis = p.cikis_notional / p.cikis_qty
        self.islemler.append({
            "sembol": p.sembol, "kol": p.kol.kimlik, "yon": p.yon, "giris_zamani": p.zaman,
            "giris_fiyati": float(p.giris), "cikis_zamani": t, "cikis_fiyati": float(ort_cikis),
            "miktar": float(p.tepe_miktar), "brut_pnl": float(p.brut_toplam),
            "komisyon": float(p.giris_kom + p.cikis_kom), "funding": float(p.funding), "net_pnl": float(net),
            "r": float(net / p.risk_tutar) if p.risk_tutar else np.nan, "cikis_nedeni": neden,
            "kismi_sayisi": p.kismi_sayisi, "kismi_pnl": float(p.kismi_net)})
        del self.acik[p.kol.kimlik]

    def _giris(self, kol: Kol, yon: int, qty: Decimal, px: Decimal, stop: Decimal, t, i,
               hedef=None, zc=None) -> None:
        """Yeni pozisyon aç ya da mevcut pozisyona ekle (aynı yön)."""
        kom = qty * px * self._tk(kol.sembol)
        self.nakit -= kom
        self.toplam_notional += qty * px
        risk = qty * abs(px - stop)
        p = self.acik.get(kol.kimlik)
        if p is None:
            kis = ()
            if kol.mod == "sinyal":
                rb = abs(px - stop)
                kis = tuple((_tick(D(cks.r_hedef_fiyati(yon, float(px), float(rb), r_k)), self.tick[kol.sembol]), D(oran))
                            for r_k, oran in sorted(kol.cikis_ayarlari.kismi))
            self.acik[kol.kimlik] = _P(kol, kol.sembol, yon, qty, px, t, stop, stop, hedef, kom, t, float(px), zc,
                                       risk, qty, ilk_miktar=qty, kismi_bekleyen=kis)
        else:
            p.giris = (p.giris * p.miktar + px * qty) / (p.miktar + qty)
            p.miktar += qty
            p.tepe_miktar = max(p.tepe_miktar, p.miktar)
            p.giris_kom += kom
            p.risk_tutar += risk
            if (stop - p.stop) * p.yon > 0:
                p.stop = stop

    # ------------------------------------------------------------------ boyutlandırma
    def _istenen_qty(self, kol, E, px, stop, w_abs, i) -> Decimal:
        """w ve işlem başı risk sınırlı hedef büyüklük (adım yuvarlaması YOK)."""
        qty_w = w_abs * E / px
        rb = abs(px - stop)
        if rb == 0:
            return Decimal(0)
        # sinyal kolu: işlem başı %1 MALİYET DAHİL (2026-11-09, limitler.maliyetli_risk_birim); ağırlık kolu: tek pozisyon en fazla
        # toplam tavan kadar (karar 25; fiyat riski)
        qty_r = E * (self.risk_oran if kol.mod == "sinyal" else self.top_risk) / self._risk_birim(kol, px, stop)
        return min(qty_w, qty_r)

    def _risk_birim(self, kol, px, stop) -> Decimal:
        """Boyutlandırmadaki birim risk. Sinyal kolu: maliyet dahil (sembolün stop kayması + 2 x taker); ağırlık kolu: |px - stop|."""
        if kol.mod == "sinyal":
            return maliyetli_risk_birim(px, stop, self._sk(kol.sembol), self._tk(kol.sembol))
        return abs(px - stop)

    def _hedef_emirleri_topla(self, i, t, E):
        """Bu satırda yürütülecek emirler (+ ölçekleme için bekleyen ağırlık emirlerinin tahmini büyüklüğü)."""
        emirler, bekleyen_tahmin = [], Decimal(0)
        for kol in self.kollar:
            s = kol.sembol
            var = bool(self.VAR[s][i])
            if kol.mod == "agirlik":
                if kol.hedef_emri is None:
                    continue
                yon, w_abs, stop_ham = kol.hedef_emri
                p = self.acik.get(kol.kimlik)
                if not var:
                    # ölçekleme tahmini: son kapanıştan
                    if yon != 0 and not np.isnan(self.son_kap[s]) and not np.isnan(stop_ham):
                        px = D(self.son_kap[s])
                        sp = D(stop_ham)
                        if abs(px - sp) > 0:
                            bekleyen_tahmin += self._istenen_qty(kol, E, px, sp, w_abs, i) * px
                    continue
                px = None
                stop = None
                if yon != 0:
                    px = _tick(D(self.A[s][i]) * (1 + yon * self._ky(s)), self.tick[s])
                    stop = _tick(D(stop_ham), self.tick[s]) if not np.isnan(stop_ham) else None
                    if p is not None and p.yon == yon:
                        stop = p.stop if stop is None or (stop - p.stop) * yon <= 0 else stop
                    if stop is None:
                        raise ValueError(f"{s} {t}: hedef ağırlık sıfırdan farklı ama stop yok (stop zorunlu)")
                emirler.append(_Emir(kol, yon, w_abs, stop, px=px))
                kol.hedef_emri = None
            else:
                if kol.giris_emri is None or not var:
                    continue
                yon, stop_ham, hedef_ham, zc = kol.giris_emri
                kol.giris_emri = None
                if kol.kimlik in self.acik:
                    continue                      # tek-grafik kuralı: açık pozisyon varken giriş yok
                px = _tick(D(self.A[s][i]) * (1 + yon * self._ky(s)), self.tick[s])
                emirler.append(_Emir(kol, yon, D(self.kal), _tick(D(stop_ham), self.tick[s]),
                                     hedef=(D(hedef_ham) if not np.isnan(hedef_ham) else None),
                                     zc=zc, sinyal=True, px=px))
        return emirler, bekleyen_tahmin

    def _risk_orantili(self, emirler, E, i, t) -> None:
        """Toplam stop riski <= top_risk * E. Sabit kalan pozisyonların (emri olmayanlar, azalan/aynı kalan hedefler,
        artan hedeflerin mevcut kısmı) riski düşüldükten sonra kalan bütçe, ağırlık kollarının ARTIŞLARINA aynı oranda
        paylaştırılır. Sinyal emirleri sıralı kontrole (Faz B) bırakılır; riskleri sabit sayılır."""
        butce = self.top_risk * E
        sabit = Decimal(0)
        artanlar = []                                  # (emir, mevcut_qty, artis_riski)
        hedefli = {e.kol.kimlik for e in emirler}
        for k, p in self.acik.items():
            if k not in hedefli:
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

    def _emirleri_yurut(self, i, t) -> None:
        E = self._ozs(i, True)
        emirler, bekleyen_tahmin = self._hedef_emirleri_topla(i, t, E)
        if not emirler:
            return
        # geçersiz stop / engeller -> hedef büyüklük
        for e in emirler:
            e.ham = Decimal(0)
            if e.yon == 0:
                continue
            kol, s = e.kol, e.kol.sembol
            if (e.yon == 1 and e.stop >= e.px) or (e.yon == -1 and e.stop <= e.px):
                self._red(t, kol, e.yon, "gecersiz_stop")
                e.ham = None                      # emir iptal; mevcut pozisyona dokunulmaz
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
        # ham None: emir iptal (pozisyona dokunma)
        emirler = [e for e in emirler if not (e.ham is None)]
        # --- 2(a) orantılı kaldıraç ölçeklemesi
        kap = Decimal(self.kal) * E / (1 + Decimal(self.kal) * self.kap_maliyet)
        hedefli = {e.kol.kimlik for e in emirler}
        sabit = Decimal(0)
        for k, p in self.acik.items():
            if k not in hedefli:
                sabit += abs(D(self._fiyat_ham(p.sembol, i, True)) * p.miktar)
        istek = bekleyen_tahmin + sum((e.ham * e.px for e in emirler if e.yon != 0), Decimal(0))
        f = Decimal(1)
        if istek > 0 and sabit + istek > kap:
            f = max(Decimal(0), (kap - sabit) / istek)
        for e in emirler:
            q = e.ham * f if e.yon != 0 else Decimal(0)
            e.qty = _step_asagi(q, self.step[e.kol.sembol]) if e.yon != 0 else Decimal(0)
            if f < 1 and e.yon != 0:
                self._kirp(t, e.kol, "kaldirac_orantili", e.w_abs, e.qty * e.px / E)
        # --- 5) portföy toplam stop riski (karar 25): ağırlık kollarının ARTAN hedefleri orantılı küçültülür
        self._risk_orantili(emirler, E, i, t)
        # --- engeller (kill / günlük limit / ısınma): artış ve yeni giriş yasak
        for e in emirler:
            kol = e.kol
            p = self.acik.get(kol.kimlik)
            if e.yon == 0:
                continue
            neden = None
            if self.kill:
                neden = "kill_switch"
            elif self.gunluk_blok and not self.olc:
                neden = "gunluk_kayip_limiti"
            elif self.islem_baslangic is not None and t < self.islem_baslangic and p is None:
                neden = "isinma"
            if neden is not None:
                artis = p is None or p.yon != e.yon or e.qty > p.miktar
                if artis:
                    self._red(t, kol, e.yon, neden)
                    if p is not None and p.yon == e.yon:
                        e.qty = min(e.qty, p.miktar)          # büyütme yok, mevcut korunur (kill'de zaten kapanmış)
                    else:
                        e.yon, e.qty = 0, Decimal(0)
        # --- Faz A: azaltma / kapatma
        for e in emirler:
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
            fiyat = self._piyasa(s, p.yon, self.A[s][i], self._ky(s))
            self._azalt(p, fiyat, red_q, t, self._tk(s), neden, True)
        # --- Faz B: açma / ekleme
        for e in emirler:
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
            # zararda büyütme yasağı
            if p is not None and (D(self.A[s][i]) - p.giris) * p.yon < 0:
                self._kirp(t, kol, "zarar_buyutme", e.w_abs, cur * e.px / E)
                continue
            if p is None and self.max_poz is not None and len(self.acik) >= self.max_poz:
                self._red(t, kol, e.yon, "max_pozisyon")
                continue
            rb = abs(e.px - e.stop)
            # toplam risk tavanı (sıralı)
            if self.top_risk is not None:
                butce = self.top_risk * E - self._acik_risk(i, True, haric=kol.kimlik)
                kisit = max(butce, Decimal(0)) / rb
                if kisit < hedef_q:
                    self._kirp(t, kol, "toplam_risk", e.w_abs, kisit * e.px / E)
                    hedef_q = _step_asagi(kisit, self.step[s])
                    if hedef_q <= cur:
                        self._red(t, kol, e.yon, "toplam_risk_tavani")
                        continue
            # sert brüt tavan (sıralı)
            oda = kap - self._brut(i, True, haric=kol.kimlik)
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
            # risk kırpması raporu (ağırlık kolu): w_abs'ı risk sınırı kısıtladıysa
            if kol.mod == "agirlik" and e.ham < e.w_abs * E / e.px - Decimal("1e-12"):
                self._kirp(t, kol, "risk", e.w_abs, e.ham * e.px / E)
            self._giris(kol, e.yon, ekle, e.px, e.stop, t, i, hedef=e.hedef, zc=e.zc)

    # ------------------------------------------------------------------ ana döngü
    def calistir(self) -> SonucPortfoy:
        n, Z = self.n, self.Z
        m = len(self.semboller)
        ozs_l, ozs_i = [], None
        ag = np.zeros((n, m))
        qh = np.zeros((n, m))
        brut_s, net_s, npoz = np.zeros(n), np.zeros(n), np.zeros(n)
        dolum_brut = np.zeros(n)
        L = SERT_LIMITLER
        self.kill, self.gunluk_blok = False, False
        gun, gun_basi = None, self.nakit
        onceki_ozs = zirve = self.nakit
        kill_asildi = gunluk_kaydedildi = False
        sinyal_kollari = [k for k in self.kollar if k.mod == "sinyal"]

        for i in range(n):
            t = Z[i]
            if t.date() != gun:
                gun, gun_basi, self.gunluk_blok, gunluk_kaydedildi = t.date(), onceki_ozs, False, False

            # 1) açılışta funding
            for p in list(self.acik.values()):
                if self.VAR[p.sembol][i]:
                    self.nakit -= self._funding_ode(p, t, True)

            # 1b) açılış MTM ile limit kontrolü (B09): açılış boşluğu günlük -%3 / kill -%20'yi aşıyorsa bayraklar BU satırda, girişlerden
            #     (adım 3) ÖNCE kurulur; açık pozisyonlar bu açılışta (adım 2) stop kaymasıyla kapanır. Kapanış kontrolü (adım 6) aynen sürer.
            if not self.olc:
                E_ac = self._ozs(i, True)
                kill_y = (not self.kill) and (zirve - E_ac) / zirve * 100 >= D(L.kill_switch_dusus_yuzde)
                gun_pct_ac = (E_ac - gun_basi) / gun_basi * 100
                gunluk_y = gun_pct_ac <= -D(L.gunluk_max_kayip_yuzde)
                if kill_y:
                    self.kill = True
                    self.limit_olaylari.append({"tur": "kill_switch", "zaman": t, "ozsermaye": float(E_ac),
                                                "dusus_yuzde": float((zirve - E_ac) / zirve * 100), "mod": "uygula", "evre": "acilis"})
                if gunluk_y:
                    if not gunluk_kaydedildi:
                        gunluk_kaydedildi = True
                        self.limit_olaylari.append({"tur": "gunluk_kayip", "zaman": t, "ozsermaye": float(E_ac),
                                                    "dusus_yuzde": float(-gun_pct_ac), "mod": "uygula", "evre": "acilis"})
                    self.gunluk_blok = True
                if kill_y or gunluk_y:
                    neden_l = "kill_switch" if self.kill else "gunluk_limit"
                    for kol in self.kollar:
                        if kol.kimlik in self.acik:
                            kol.cikis_emri = neden_l
                    if self.kill:
                        for kol in self.kollar:
                            kol.hedef_emri = None
                            kol.giris_emri = None

            # 2) açılışta bekleyen çıkışlar (kill / günlük limit / sinyal / zaman / kaldıraç azaltma)
            for kol in self.kollar:
                p = self.acik.get(kol.kimlik)
                s = kol.sembol
                if p is None:
                    kol.cikis_emri = kol.kucult_emri = None
                    continue
                if not self.VAR[s][i]:
                    continue
                if kol.cikis_emri:
                    neden = kol.cikis_emri
                    k = self._sk(s) if neden in ("kill_switch", "gunluk_limit") else self._ky(s)
                    self._azalt(p, self._piyasa(s, p.yon, self.A[s][i], k), p.miktar, t, self._tk(s), neden, False)
                    kol.hedef_emri = None
                elif kol.kucult_emri is not None:
                    f = D(kol.kucult_emri)
                    q = _step_asagi(p.miktar * f, self.step[s])
                    red_q = p.miktar - q
                    if q < self.min_qty[s]:
                        red_q = p.miktar
                    if red_q > 0:
                        self._kirp(t, kol, "kaldirac_azalt", 1.0, float(f))
                        self._azalt(p, self._piyasa(s, p.yon, self.A[s][i], self._ky(s)), red_q, t, self._tk(s),
                                    "kaldirac_azalt", True)
                kol.cikis_emri = None
                kol.kucult_emri = None

            # 3) açılışta bekleyen girişler / hedef ağırlıklar
            self._emirleri_yurut(i, t)
            E_acilis = self._ozs(i, True)
            dolum_brut[i] = float(self._brut(i, True) / E_acilis) if E_acilis > 0 else 0.0

            # 4) mum içi stop / hedef / kısmi
            for kol in self.kollar:
                p = self.acik.get(kol.kimlik)
                s = kol.sembol
                if p is None or not self.VAR[s][i]:
                    continue
                self._mum_ici(p, kol, i, t)

            # 4b) gün sonu kapanış dolumu (backtest.motor adım 3b ile aynı): stop/hedef değmediyse mumun KAPANIŞINDAN
            for kol in self.kollar:
                if kol.s_gsk is not None and kol.s_gsk[i] and kol.kimlik in self.acik and self.VAR[kol.sembol][i]:
                    self._gun_sonu_kapat(self.acik[kol.kimlik], i, t)

            # 5) veri sonu
            if i == n - 1:
                for p in list(self.acik.values()):
                    s = p.sembol
                    ham = self._fiyat_ham(s, i, False)
                    self.nakit -= self._funding_ode(p, t + self.aralik, False)
                    self._azalt(p, _tick(D(ham), self.tick[s]), p.miktar, t + self.aralik, self._tk(s), "veri_sonu", False)

            # 6) kapanış: özsermaye, limitler
            for s in self.semboller:
                if self.VAR[s][i]:
                    self.son_kap[s] = self.C[s][i]
            E = self._ozs(i, False)
            ozs_l.append(E)
            onceki_ozs = E
            zirve = max(zirve, E)
            dusus = (zirve - E) / zirve * 100
            if self.olc:
                if dusus >= D(L.kill_switch_dusus_yuzde):
                    if not kill_asildi:
                        kill_asildi = True
                        self.limit_olaylari.append({"tur": "kill_switch", "zaman": t, "ozsermaye": float(E),
                                                    "dusus_yuzde": float(dusus), "mod": "olc"})
                else:
                    kill_asildi = False
            elif not self.kill and dusus >= D(L.kill_switch_dusus_yuzde):
                self.kill = True
                self.limit_olaylari.append({"tur": "kill_switch", "zaman": t, "ozsermaye": float(E),
                                            "dusus_yuzde": float(dusus), "mod": "uygula"})
            gunluk_pct = (E - gun_basi) / gun_basi * 100
            if gunluk_pct <= -D(L.gunluk_max_kayip_yuzde):
                if not gunluk_kaydedildi:
                    gunluk_kaydedildi = True
                    self.limit_olaylari.append({"tur": "gunluk_kayip", "zaman": t, "ozsermaye": float(E),
                                                "dusus_yuzde": float(-gunluk_pct), "mod": "olc" if self.olc else "uygula"})
                if not self.olc:
                    self.gunluk_blok = True

            # geçmiş kayıtları
            brut = Decimal(0)
            net = Decimal(0)
            for p in self.acik.values():
                k = self.sem_i[p.sembol]
                mk = D(self._fiyat_ham(p.sembol, i, False))
                nom = p.yon * p.miktar * mk
                qh[i, k] += float(p.yon * p.miktar)
                ag[i, k] += float(nom / E) if E > 0 else 0.0
                brut += abs(nom)
                net += nom
            brut_s[i] = float(brut / E) if E > 0 else 0.0
            net_s[i] = float(net / E) if E > 0 else 0.0
            npoz[i] = len(self.acik)

            # 7) sonraki açılış için kararlar
            if self.kill:
                for kol in self.kollar:
                    kol.hedef_emri = None
                    kol.giris_emri = None
                    if kol.kimlik in self.acik:
                        kol.cikis_emri = "kill_switch"
            elif self.gunluk_blok and not self.olc:
                for kol in self.kollar:
                    if kol.kimlik in self.acik:
                        kol.cikis_emri = "gunluk_limit"
            else:
                if E > 0 and brut / E > D(self.kal):
                    f = D(self.kal) / (brut / E) * Decimal("0.9999")
                    for kol in self.kollar:
                        if kol.kimlik in self.acik and kol.cikis_emri is None:
                            kol.kucult_emri = float(f)
            for kol in self.kollar:
                if kol.mod == "agirlik":
                    self._karar_agirlik(kol, i, t)
                elif self.VAR[kol.sembol][i]:
                    self._karar_sinyal(kol, i, t)

        ozs = pd.Series([float(x) for x in ozs_l], index=self.eksen, name="ozsermaye")
        df = pd.DataFrame(self.islemler, columns=ISLEM_KOLONLARI)
        gun_ozs = ozs.groupby(ozs.index.floor("D")).last()
        return SonucPortfoy(
            df, ozs, gun_ozs,
            pd.DataFrame(ag, index=self.eksen, columns=self.semboller),
            pd.DataFrame(qh, index=self.eksen, columns=self.semboller),
            pd.DataFrame({"brut": brut_s, "net": net_s, "pozisyon_sayisi": npoz}, index=self.eksen),
            pd.Series(dolum_brut, index=self.eksen, name="brut_dolum"),
            self.reddedilenler, self.kirpmalar, self.uyarilar, float(self.ay.baslangic_sermaye),
            self.limit_olaylari, float(self.toplam_notional))

    # ------------------------------------------------------------------ mum içi
    def _mum_ici(self, p: _P, kol: Kol, i, t) -> None:
        s = p.sembol
        o, h, l = self.A[s][i], self.Hh[s][i], self.Ll[s][i]
        tick = self.tick[s]
        if p.yon == 1:
            stop_gap, stop_vur = o <= p.stop, l <= p.stop
            hedef_gap = p.hedef is not None and o >= p.hedef
            hedef_vur = p.hedef is not None and h >= p.hedef
        else:
            stop_gap, stop_vur = o >= p.stop, h >= p.stop
            hedef_gap = p.hedef is not None and o <= p.hedef
            hedef_vur = p.hedef is not None and l <= p.hedef
        maker_mi = self.ay.hedef_limit_emri
        cikis = None
        if stop_gap:
            cikis = (self._piyasa(s, p.yon, o, self._sk(s)), "stop_gap", t, self._tk(s))
        elif hedef_gap:
            cikis = (_tick(D(o), tick), "hedef", t, self._mk(s) if maker_mi else self._tk(s))
        elif stop_vur:
            cikis = (self._piyasa(s, p.yon, float(p.stop), self._sk(s)), "stop", t + self.aralik, self._tk(s))
        elif hedef_vur:
            cikis = (p.hedef, "hedef", t + self.aralik, self._mk(s) if maker_mi else self._tk(s))
        if p.kismi_bekleyen and (cikis is None or (cikis[1] == "hedef" and not hedef_gap)):
            kom_k = self._mk(s) if maker_mi else self._tk(s)
            kalan = []
            step = self.step[s]
            for seviye, oran in p.kismi_bekleyen:
                if p.hedef is not None and (seviye - p.hedef) * p.yon >= 0:
                    continue
                gorulen = (o >= seviye) if p.yon == 1 else (o <= seviye)
                vurdu = (h >= seviye) if p.yon == 1 else (l <= seviye)
                if not (gorulen or vurdu):
                    kalan.append((seviye, oran))
                    continue
                fiyat_k = _tick(D(o), tick) if gorulen else seviye
                t_k = t if gorulen else t + self.aralik
                qty = min(_step_asagi(p.ilk_miktar * oran, step), p.miktar)
                if qty <= 0:
                    continue
                if t_k != t:
                    self.nakit -= self._funding_ode(p, t_k, False)
                    fz = self.fund[s]
                    if fz is not None:
                        b_ = fz[0].searchsorted(t_k, side="left")
                        if b_ > 0 and fz[0][b_ - 1] > p.son_f:
                            p.son_f = fz[0][b_ - 1]
                if p.miktar - qty < self.min_qty[s]:
                    cikis = (fiyat_k, "kismi_tam", t_k, kom_k)
                    break
                self._azalt(p, fiyat_k, qty, t_k, kom_k, "kismi", True)
            p.kismi_bekleyen = tuple(kalan)
        if cikis is not None:
            fiyat_c, neden, t_c, kom_o = cikis
            if t_c != t:
                self.nakit -= self._funding_ode(p, t_c, False)
            self._azalt(p, fiyat_c, p.miktar, t_c, kom_o, neden, False)

    def _gun_sonu_kapat(self, p: _P, i, t, aralik=None) -> None:
        """Gün sonu kapanışı (`gun_sonu_kapanis` bayraklı mum; seanslı veri): mum içi stop/hedef bu mumda pozisyonu
        kapatmadıysa pozisyon mumun KAPANIŞ fiyatından, sinyal çıkışıyla aynı kayma ve taker komisyonuyla kapanır
        (neden "gun_sonu", zaman = mum kapanışı). backtest.motor adım 3b ile birebir aynı sıra/fiyat/öncelik."""
        s = p.sembol
        t_c = t + (self.aralik if aralik is None else aralik)
        self.nakit -= self._funding_ode(p, t_c, False)
        self._azalt(p, self._piyasa(s, p.yon, self.C[s][i], self._ky(s)), p.miktar, t_c, self._tk(s), "gun_sonu", False)

    # ------------------------------------------------------------------ kararlar (bar kapanışı)
    def _karar_agirlik(self, kol: Kol, i, t) -> None:
        w, sp = kol.w[i], kol.stop[i]
        p = self.acik.get(kol.kimlik)
        tick = self.tick[kol.sembol]
        if not np.isnan(w):
            yon = 0 if w == 0 else (1 if w > 0 else -1)
            if self.kill:
                if yon != 0:
                    self._red(t, kol, yon, "kill_switch")
                return
            stop_ham = sp
            if yon != 0 and np.isnan(sp):
                if kol.hedef_emri is not None and not np.isnan(kol.hedef_emri[2]):
                    stop_ham = kol.hedef_emri[2]
                elif p is None or p.yon != yon:
                    raise ValueError(f"{kol.sembol} {t}: hedef ağırlık sıfırdan farklı ama stop yok (stop zorunlu)")
            kol.hedef_emri = (yon, D(abs(w)), stop_ham if yon != 0 else np.nan)
        elif not np.isnan(sp):
            if p is not None:
                yeni = _tick(D(sp), tick)
                if (yeni - p.stop) * p.yon > 0:
                    p.stop = yeni
            if kol.hedef_emri is not None:
                yon, w_abs, _ = kol.hedef_emri
                kol.hedef_emri = (yon, w_abs, sp)

    def _karar_sinyal(self, kol: Kol, i, t) -> None:
        p = self.acik.get(kol.kimlik)
        s = kol.sembol
        ca = kol.cikis_ayarlari
        if p is not None:
            p.tutulan += 1
            h, l = self.Hh[s][i], self.Ll[s][i]
            p.ekstrem = max(p.ekstrem, h) if p.yon == 1 else min(p.ekstrem, l)
            risk_birim_f = float(abs(p.giris - p.ilk_stop))
            yeni = float(p.stop)
            if ca.basabas_r_esigi:
                yeni = cks.basabasa_cek(p.yon, yeni, float(p.giris), p.ekstrem, risk_birim_f, ca.basabas_r_esigi)
            if ca.atr_iz_suren_k:
                yeni = cks.iz_suren_stop(p.yon, yeni, p.ekstrem, kol.atr[i], ca.atr_iz_suren_k)
            yeni_d = _tick(D(yeni), self.tick[s])
            if (yeni_d - p.stop) * p.yon > 0:
                p.stop = yeni_d
            if kol.cikis_emri is None:
                if self.kill:
                    kol.cikis_emri = "kill_switch"
                elif self.gunluk_blok and not self.olc:
                    kol.cikis_emri = "gunluk_limit"
                elif (kol.s_cikis_l[i] if p.yon == 1 else kol.s_cikis_s[i]):
                    kol.cikis_emri = "sinyal"
                elif cks.zaman_doldu(p.tutulan, p.zaman_limit):
                    kol.cikis_emri = "zaman"
        if kol.s_yon[i] != 0:
            zc = kol.s_zc[i]
            kol.giris_emri = (int(kol.s_yon[i]), kol.s_stop[i], kol.s_hedef[i],
                              int(zc) if not np.isnan(zc) else ca.zaman_cikisi_mum)
        else:
            kol.giris_emri = None


def agirlik_kollari(veriler: dict, strateji: PortfoyStratejisi, eksen) -> list:
    h, s = strateji.sinyaller(veriler)
    kollar = []
    for sembol in h.columns:
        w = h[sembol].to_numpy(dtype=float)
        st = s[sembol].to_numpy(dtype=float) if sembol in s.columns else np.full(len(eksen), np.nan)
        kollar.append(Kol(kimlik=f"{strateji.ad or 'portfoy'}|{sembol}", sembol=sembol, mod="agirlik",
                          strateji_ad=strateji.ad, w=w, stop=st))
    return kollar


def portfoy_backtest(veriler: dict, strateji: PortfoyStratejisi, ayarlar: PortfoyAyarlari = None,
                     fundingler: Optional[dict] = None,
                     islem_baslangic: Optional[pd.Timestamp] = None) -> SonucPortfoy:
    """veriler: {sembol: mum DataFrame}; fundingler: {sembol: funding DataFrame} (opsiyonel).
    islem_baslangic: bu zamandan önceki satırlarda yeni pozisyon açılmaz (ısınma payı)."""
    ayarlar = ayarlar or PortfoyAyarlari()
    eksen = ortak_eksen(veriler)
    kollar = agirlik_kollari(veriler, strateji, eksen)
    return _Motor(veriler, kollar, ayarlar, fundingler, eksen, islem_baslangic).calistir()
