"""CANLI (gerçek para / testnet) yürütücüsünün risk kuralı: TEK KAYNAK. Kullanıcı kararı 2026-11-11.

KAPSAM: YALNIZ canlı yürütücü (`motor/canli/borsa/`). Paper, backtest ve araştırma `motor/risk/limitler.py::SERT_LIMITLER`'i kullanmaya
DEVAM EDER; o dosya bu karardan etkilenmez (testler değerlerin değişmediğini kontrol eder). Bu dosya dışında canlı risk SAYISI yoktur.

Kural (strateji hesabı başına; kasa = min(borsa özsermayesi, tahsis edilen sermaye)):
  - işlem başı stopta kayıp (maliyet dahil) <= kasa x %3; işlem başı marj <= kasa x %50; işlem başı nominal <= kasa x 1.5
  - miktar = min(1.5·kasa/fiyat, 0.03·kasa/(stop mesafesi + birim maliyet)) [+ marj tavanı, toplam risk/brüt bütçesi], stepSize'a AŞAĞI;
    min tutar/min miktarın altında kalırsa işlem ATLANIR (asla yukarı yuvarlanmaz; olay `min_tutar_alti`)
  - toplam açık stop riski <= kasa x %6; brüt nominal <= kasa x 1.5
  - günlük kayıp -%6 (UTC günü, gün başı kasadan): ertesi UTC gününe kadar yeni giriş yok (açık pozisyonlar KAPATILMAZ: borsa stopu + strateji çıkışı sürer)
  - strateji kill: zirve kasadan -%30 -> hepsini kapat + kalıcı dur (yeniden başlatmada da)
  - hesap kill: TÜM canlı stratejilerin kasa TOPLAMI, ortak zirveden -%20 -> hepsini kapat + hepsi kalıcı dur
  - izole marj; kaldıraç: stop mesafesi <= %15 -> 3x, > %15 -> 2x (girişten önce sembole ayarlanır). Kaldıraç = izinli azami; marj tavanı
    (kasa x %50) bu kaldıraçla birlikte nominal tavanını belirler: 3x -> 1.5x kasa, 2x -> 1.0x kasa.
Fonksiyonlar saftır (Decimal); borsa filtreleri (adım, min tutar) parametre olarak gelir.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal
from typing import Optional

D = Decimal


@dataclass(frozen=True)
class CanliLimitleri:
    islem_basi_max_kayip_oran: float = 0.03      # stopta (maliyet dahil) kasanın en fazla %3'ü
    islem_basi_max_marj_oran: float = 0.50       # işlem başı marj / kasa
    islem_basi_max_nominal_kat: float = 1.5      # işlem başı nominal / kasa
    toplam_stop_riski_oran: float = 0.06         # tüm açık pozisyonların stopa kadar toplam riski / kasa
    brut_nominal_kat: float = 1.5                # brüt nominal / kasa
    gunluk_max_kayip_oran: float = 0.06          # UTC günü, gün başı kasadan
    strateji_kill_oran: float = 0.30             # strateji kasasının zirveden düşüşü
    hesap_kill_oran: float = 0.20                # tüm stratejilerin kasa toplamının ortak zirveden düşüşü
    stop_yakin_siniri_oran: float = 0.15         # stop mesafesi (fiyatın oranı) <= bu: yakın stop
    kaldirac_yakin: int = 3                      # yakın stopta azami kaldıraç
    kaldirac_uzak: int = 2                       # uzak stopta (> sınır) azami kaldıraç
    stop_uzaklik_maks_oran: float = 0.25         # |giriş-stop|/giriş bunu aşarsa işlem atlanır


CANLI_LIMITLER = CanliLimitleri()
TOL = D("1e-9")


def _d(x) -> Decimal:
    return x if isinstance(x, Decimal) else D(str(x))


def birim_maliyet(giris: Decimal, stop: Decimal, stop_kayma: Decimal, taker: Decimal) -> Decimal:
    """Birim başına stop kayması + giriş ve çıkış komisyonu (çıkış stop fiyatı üzerinden; short'ta stop > giriş: max)."""
    return max(giris, stop) * (stop_kayma + 2 * taker)


def kaldirac_sec(stop_uzaklik_oran, limitler: CanliLimitleri = CANLI_LIMITLER) -> int:
    """Stop mesafesi (|giriş-stop|/giriş) <= %15 -> 3x; üstü -> 2x. Sınırın kendisi 3x."""
    return limitler.kaldirac_yakin if _d(stop_uzaklik_oran) <= _d(limitler.stop_yakin_siniri_oran) else limitler.kaldirac_uzak


def asagi(x: Decimal, adim: Decimal) -> Decimal:
    return (_d(x) / adim).to_integral_value(rounding=ROUND_FLOOR) * adim


@dataclass(frozen=True)
class MiktarSonucu:
    qty: Decimal                       # 0: işlem yok
    neden: Optional[str]               # None | gecersiz_stop | stop_cok_uzak | kasa_yok | risk_butcesi_dolu | min_tutar_alti
    ayrinti: str = ""
    kaldirac: int = 0
    baglayan: str = ""                 # miktarı sınırlayan kural: kayip | nominal | marj | toplam_risk | brut
    ham: Decimal = D(0)                # yuvarlama öncesi


def miktar_hesapla(*, kasa, yon: int, giris, stop, stop_kayma, taker, adim, min_qty=D(0), min_tutar=D(0), max_qty=None,
                   diger_brut=D(0), diger_stop_riski=D(0), kaldirac_ust: Optional[int] = None,
                   limitler: CanliLimitleri = CANLI_LIMITLER) -> MiktarSonucu:
    """qty = min(nominal tavanı, marj tavanı, kayıp tavanı, toplam risk bütçesi, brüt bütçesi), `adim`a AŞAĞI. min miktar / min tutar
    altı -> atla (yukarı yuvarlama YOK). `diger_stop_riski`: diğer açık pozisyonların fiyat riski; `diger_brut`: diğerlerinin nominali."""
    L = limitler
    kasa, giris, stop = _d(kasa), _d(giris), _d(stop)
    if kasa <= 0:
        return MiktarSonucu(D(0), "kasa_yok", f"kasa {kasa}")
    if yon not in (1, -1) or (yon == 1 and stop >= giris) or (yon == -1 and stop <= giris):
        return MiktarSonucu(D(0), "gecersiz_stop", f"yon={yon} giris={giris} stop={stop}")
    uzaklik = abs(giris - stop)
    oran = uzaklik / giris
    if oran > _d(L.stop_uzaklik_maks_oran):
        return MiktarSonucu(D(0), "stop_cok_uzak", f"|giris-stop|/giris {oran:.4f} > {L.stop_uzaklik_maks_oran}")
    kald = kaldirac_sec(oran, L)
    if kaldirac_ust is not None:                          # dolum sonrası yeniden boyut: borsada ZATEN ayarlı kaldıraç aşılamaz
        kald = min(kald, int(kaldirac_ust))
    birim_risk = uzaklik + birim_maliyet(giris, stop, _d(stop_kayma), _d(taker))
    aday = {
        "nominal": _d(L.islem_basi_max_nominal_kat) * kasa / giris,
        "marj": _d(L.islem_basi_max_marj_oran) * kald * kasa / giris,
        "kayip": _d(L.islem_basi_max_kayip_oran) * kasa / birim_risk,
        "toplam_risk": (_d(L.toplam_stop_riski_oran) * kasa - _d(diger_stop_riski)) / (birim_risk),
        "brut": (_d(L.brut_nominal_kat) * kasa - _d(diger_brut)) / giris,
    }
    baglayan = min(aday, key=lambda k: aday[k])           # eşitlikte sözlük sırası (nominal, marj, kayip, ...)
    ham = aday[baglayan]
    if ham <= 0:
        return MiktarSonucu(D(0), "risk_butcesi_dolu", f"toplam risk/brüt bütçesi dolu ({baglayan})", kald, baglayan, ham)
    qty = asagi(min(ham, _d(max_qty)) if max_qty is not None else ham, _d(adim))
    if qty <= 0 or qty < _d(min_qty) or qty * giris < _d(min_tutar):
        return MiktarSonucu(D(0), "min_tutar_alti", f"hesaplanan miktar {ham:.8f} -> yuvarlanmış {qty} (min miktar {min_qty}, min tutar {min_tutar}, "
                            f"tutar {qty * giris:.4f}); YUKARI YUVARLANMAZ", kald, baglayan, ham)
    return MiktarSonucu(qty, None, "", kald, baglayan, ham)


def limit_ihlalleri(*, qty, giris, stop, kasa, stop_kayma, taker, kaldirac: int, diger_brut=D(0), diger_stop_riski=D(0),
                    limitler: CanliLimitleri = CANLI_LIMITLER) -> list:
    """Nihai (yuvarlanmış / gerçek dolumlu) miktarın ihlalleri; boş liste = uyumlu."""
    L = limitler
    qty, giris, stop, kasa = _d(qty), _d(giris), _d(stop), _d(kasa)
    if kasa <= 0:
        return ["kasa_yok"]
    out = []
    kayip = qty * (abs(giris - stop) + birim_maliyet(giris, stop, _d(stop_kayma), _d(taker))) / kasa
    if kayip > _d(L.islem_basi_max_kayip_oran) + TOL:
        out.append(f"islem_basi_kayip %{kayip * 100:.4f} > %{L.islem_basi_max_kayip_oran * 100:g}")
    nominal = qty * giris / kasa
    if nominal > _d(L.islem_basi_max_nominal_kat) + TOL:
        out.append(f"islem_nominal {nominal:.4f}x > {L.islem_basi_max_nominal_kat}x")
    marj = nominal / max(int(kaldirac), 1)
    if marj > _d(L.islem_basi_max_marj_oran) + TOL:
        out.append(f"islem_marj %{marj * 100:.4f} > %{L.islem_basi_max_marj_oran * 100:g}")
    toplam = (_d(diger_stop_riski) + qty * abs(giris - stop)) / kasa
    if toplam > _d(L.toplam_stop_riski_oran) + TOL:
        out.append(f"toplam_stop_riski %{toplam * 100:.4f} > %{L.toplam_stop_riski_oran * 100:g}")
    brut = (_d(diger_brut) + qty * giris) / kasa
    if brut > _d(L.brut_nominal_kat) + TOL:
        out.append(f"brut_nominal {brut:.4f}x > {L.brut_nominal_kat}x")
    return out


# ---------------------------------------------------------------------------- günlük / kill durumu (saf; durum sözlüğü yerinde güncellenir)
def gunluk_kill_guncelle(d: dict, kasa, gun: str, limitler: CanliLimitleri = CANLI_LIMITLER) -> list:
    """Strateji durumu `d` (anahtarlar: zirve, gun, gun_basi, kill, kill_neden, gun_blok) yerinde güncellenir.
    -> [(olay_turu, mesaj)]. Yeni UTC gününde gün başı kasa sıfırlanır ve günlük blok kalkar; kill ASLA kalkmaz."""
    L, kasa, olaylar = limitler, _d(kasa), []
    if d.get("gun") != gun:
        d["gun"], d["gun_basi"], d["gun_blok"] = gun, str(kasa), False
    zirve = max(_d(d["zirve"]) if d.get("zirve") else kasa, kasa)
    d["zirve"] = str(zirve)
    gb = _d(d["gun_basi"])
    if not d.get("kill") and zirve > 0 and (zirve - kasa) / zirve >= _d(L.strateji_kill_oran) - TOL:
        d["kill"], d["kill_neden"] = True, "kill_switch"
        olaylar.append(("canli_kill_switch", f"STRATEJİ KILL: kasa {kasa:.2f}, zirve {zirve:.2f} (düşüş >= %{L.strateji_kill_oran * 100:g}); "
                                             "tüm pozisyonlar kapatılıyor, sonra emirler iptal; kalıcı durdu, elle sıfırlama gerekir."))
    if not d.get("kill") and not d.get("gun_blok") and gb > 0 and (gb - kasa) / gb >= _d(L.gunluk_max_kayip_oran) - TOL:
        d["gun_blok"] = True
        olaylar.append(("canli_kill_switch", f"GÜNLÜK LİMİT: gün başı {gb:.2f} -> {kasa:.2f} (>= %{L.gunluk_max_kayip_oran * 100:g} kayıp); "
                                             "bugün yeni giriş yok (açık pozisyonlar kapatılmaz)."))
    return olaylar


def hesap_kill_guncelle(h: dict, kasalar: dict, limitler: CanliLimitleri = CANLI_LIMITLER) -> Optional[str]:
    """Hesap düzeyi durum `h` (anahtarlar: kimlikler, zirve, kill, kill_neden) yerinde güncellenir. `kasalar` = {strateji_kimligi: kasa}
    TÜM canlı stratejiler için. Strateji kümesi değişirse ortak zirve yeni toplamdan başlar. Tetiklenirse mesaj döner, aksi halde None;
    kill kalıcıdır (h['kill'] bir kez True olunca elle sıfırlanana kadar True)."""
    L = limitler
    toplam = sum((_d(v) for v in kasalar.values()), D(0))
    kimlikler = sorted(kasalar)
    if h.get("kimlikler") != kimlikler:
        h["kimlikler"], h["zirve"] = kimlikler, None
    zirve = max(_d(h["zirve"]) if h.get("zirve") else toplam, toplam)
    h["zirve"], h["toplam"] = str(zirve), str(toplam)
    if not h.get("kill") and zirve > 0 and (zirve - toplam) / zirve >= _d(L.hesap_kill_oran) - TOL:
        h["kill"], h["kill_neden"] = True, "hesap_kill"
        return (f"HESAP KILL: tüm stratejilerin kasa toplamı {toplam:.2f}, ortak zirve {zirve:.2f} (düşüş >= %{L.hesap_kill_oran * 100:g}); "
                "TÜM stratejiler kapatılıyor ve kalıcı durduruluyor.")
    return None
