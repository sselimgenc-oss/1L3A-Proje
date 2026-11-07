"""Final seçim hazırlığı: ajan başına ~3 strateji önerisi (kanıt üretir; SEÇİMİ KULLANICI ONAYLAR).

YALNIZ OOS (walk-forward test pencereleri) verisi kullanılır; yeni parametre seçimi yok, kilitli döneme dokunulmaz.
Girdi: sonuclar/final_aday_havuzu_tek_grafik.csv (51 satır) + sonuclar/wf/islemler/<etiket>/<strateji>--<sembol>--<tf>.parquet
(etiket: USDT'li semboller k3_kripto, DK_ semboller k3_dk_v2) + portföy sağlamları (sonuclar/saglamlik_portfoy/*.csv,
günlük getiriler sonuclar/wf_portfoy/gunluk/).

YÖNTEM VE YAKLAŞIKLIKLAR (hepsi bilinçli, raporda da yazılı)
  1. Günlük getiri (işlem listesinden): işlem başı %1 risk, R x %1. İki sürüm:
       'cikis' : R x %1 çıkış gününe yazılır (ilkel; wf_tarama sharpe'ı ile aynı mantık, bileşiksiz toplama).
       'yay'   : aynı R x %1 işlemin açık kaldığı günlere süre payıyla yayılır (günlük MTM yoksa en yakın yaklaşık:
                 pozisyon içi yol DOĞRUSAL varsayılır; gerçek yol bilinmez). Korelasyon bu sürümle (seyrek 'cikis'
                 serisi korelasyonu olduğundan düşük gösterir).
  2. Korelasyon: iki adayın OOS aralıklarının KESİŞİMİ üzerinde (>= MIN_ORTAK_GUN gün, yoksa NaN = ölçülemedi).
     OOS dışı günler bilgi içermediğinden dışarıda; aralık içindeki işlemsiz günler 0'dır (seri 0 şişkin).
  3. Yönlü örtüşme: aynı sembol + aynı yön pozisyonlarının zaman kesişimi / min(iki adayın toplam açık kalma süresi).
     Farklı sembolde 0. Korelasyon sembol arası ortak sürücüyü (ör. TSLA-NVDA) zaten yakalar.
  4. Skor = OOS Sharpe (wf_tarama, günlük, yıllıklandırılmış) x (1 - rastgele giriş p). Basit, parametresiz.
  5. Açgözlü seçim: skora göre sırala, en iyiden başla; aday, o ana kadar seçilenlerle korelasyonu <= ESIK_KORR
     ve yönlü örtüşmesi <= ESIK_ORTUSME ise eklenir; ilk 3 SEÇİM, sonraki 5 YEDEK (aynı kurallar). Aynı strateji farklı
     sembol = ayrı kol sayılır (kural yasaklamaz; raporda işaretlenir).
  6. Yeniden oynatıcı (yeniden_oyna): seçilen setin OOS işlemlerini OLAY SIRASIYLA tek hesapta oynatır:
       - işlem başı risk %1 (giriş anındaki MTM özsermayenin), bileşik; risk_i = ölçek x %1 x MTM.
       - toplam açık risk <= %5 MTM: aşan giriş kalan bütçeye KIRPILIR (ölçek < MIN_OLCEK ise reddedilir).
       - brüt maruziyet <= 3x: her işlemin 1x-risk kaldıracı kayıtlı işlemden türetilir (nominal / (risk$ x 100));
         tavan aşılacaksa ölçek kırpılır (yine MIN_OLCEK altı reddedilir).
       - günlük kayıp %3: UTC gününde MTM, gün başı MTM'ye göre <= -%3 olursa açık pozisyonlar o andaki MTM'den kapanır,
         o gün yeni giriş reddedilir. Kill switch: MTM zirveden %20 düşerse hepsi kapanır, bir daha işlem yok.
       - AÇIK pozisyonun MTM'si bilinmediğinden limit/boyutlandırma değerlemesi MUHAFAZAKÂR: gerçekleşmiş nakit + açık
         pozisyonların yalnız zararı (R'nin süre payıyla doğrusal; kâr çıkışta sayılır). Gerçek yol bilinmediğinden ve
         doğrusal yol gelecek bilgisini (nihai R) kullandığından limit olayları yaklaşıktır. Raporlanan Sharpe/düşüş
         GERÇEKLEŞMİŞ özsermaye (çıkış günü) üzerindendir -> wf_tarama metrikleriyle aynı mantık ('yay' serisi
         yumuşattığı için Sharpe şişirir; Sharpe için KULLANILMAZ, yalnız korelasyon içindir).
         Limit kontrolleri yalnız olay anlarında (giriş/çıkış/gece yarısı) yapılır; gün içi zirve/dip görülmez.
         Zorla kapatmada ek kayma/komisyon yok.
       - Aynı sembolde zıt yönlü kollar netleşmez (birlesik.py ile aynı muhafazakâr varsayım).
     Alternatif (kıyas) motor/portfoy/birlesik.py ile yeniden koşu bu araçta YAPILMAZ (en sık seçilen ayar OOS'a
     bakılarak seçilmiş sayılır = in-sample'a kayar; yeniden oynatıcı OOS işlemlerinin kendisini kullanır).
  7. Portföy ajanı (hedef ağırlık stratejileri): günlük OOS getirileri hazır (kendi motorunda limitleri uygulanmış);
     set = eşit ağırlıklı günlük ortalama (yeniden oynatılamaz; limit sayıları yok).
  8. Tüm ajanlar tek kasa: tek-grafik kolları (swing + daytrade) birlikte yeniden oynatılır; portföy ajanı seti ayrı
     kol (sleeve) olarak %50/%50 sermaye payıyla günlük getiri düzeyinde harmanlanır (iki sleeve'in ORTAK limit
     kontrolü yok; her biri kendi içinde uygulanmış). Harman, iki serinin ortak tarih aralığında.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[2]
HAVUZ = KOK / "sonuclar" / "final_aday_havuzu_tek_grafik.csv"
WF_DIZIN = KOK / "sonuclar" / "wf"
PF_GUNLUK = KOK / "sonuclar" / "wf_portfoy" / "gunluk"
PF_SAGLAMLIK = KOK / "sonuclar" / "saglamlik_portfoy"
CIKTI = KOK / "sonuclar" / "secim"

RISK = 0.01
ESIK_KORR = 0.5
ESIK_ORTUSME = 0.3
MIN_ORTAK_GUN = 250
N_SECIM = 3
N_YEDEK = 5
MIN_OLCEK = 0.1
KUME_ESIGI = 0.5          # kümeleme: ortalama bağlantıda korelasyon > 0.5 aynı küme


# ============================================================================ okuma
def etiket_sembol(sembol: str) -> str:
    return "k3_kripto" if sembol.endswith("USDT") else "k3_dk_v2"


def kimlik(strateji: str, sembol: str, tf: str) -> str:
    return f"{strateji}|{sembol}|{tf}"


def islem_oku(strateji: str, sembol: str, tf: str, kok: Path = WF_DIZIN) -> pd.DataFrame:
    p = kok / "islemler" / etiket_sembol(sembol) / f"{strateji}--{sembol}--{tf}.parquet"
    return pd.read_parquet(p)


def wf_ozet_oku(kok: Path = WF_DIZIN) -> pd.DataFrame:
    d = pd.concat([pd.read_csv(kok / f"{e}.csv") for e in ("k3_kripto", "k3_dk_v2")], ignore_index=True)
    return d.drop_duplicates(["strateji", "sembol", "tf"], keep="last")


# ============================================================================ günlük getiri
def gunluk_getiri(islemler: pd.DataFrame, mod: str = "yay", risk: float = RISK,
                  bas=None, bit=None) -> pd.Series:
    """İşlem başı R x risk'ten UTC günlük getiri (toplamsal, bileşiksiz). mod 'cikis' | 'yay' (modül belgesi)."""
    g = pd.DatetimeIndex(islemler["giris_zamani"])
    c = pd.DatetimeIndex(islemler["cikis_zamani"])
    r = islemler["r"].to_numpy(dtype=float) * risk
    bas = (g.min() if bas is None else pd.Timestamp(bas)).floor("D")
    bit = (c.max() if bit is None else pd.Timestamp(bit)).floor("D")
    gunler = pd.date_range(bas, bit, freq="D")
    out = np.zeros(len(gunler))
    if mod == "cikis":
        idx = gunler.get_indexer(c.floor("D"))
        for i, v in zip(idx, r):
            if i >= 0:
                out[i] += v
    elif mod == "yay":
        for gi, ci, v in zip(g, c, r):
            sure = (ci - gi).total_seconds()
            g0, c0 = gi.floor("D"), ci.floor("D")
            if sure <= 0 or g0 == c0:
                i = gunler.get_indexer([c0])[0]
                if i >= 0:
                    out[i] += v
                continue
            for gun in pd.date_range(g0, c0, freq="D"):
                pay = (min(ci, gun + pd.Timedelta(days=1)) - max(gi, gun)).total_seconds() / sure
                i = gunler.get_indexer([gun])[0]
                if i >= 0 and pay > 0:
                    out[i] += v * pay
    else:
        raise ValueError("mod 'cikis' ya da 'yay' olmalı")
    return pd.Series(out, index=gunler)


def sharpe_gunluk(getiri) -> float:
    x = np.asarray(getiri, dtype=float)
    if len(x) < 2:
        return float("nan")
    s = x.std(ddof=1)
    return float(x.mean() / s * np.sqrt(365)) if s > 0 else float("nan")


def max_dusus(ozsermaye) -> float:
    e = np.asarray(ozsermaye, dtype=float)
    if len(e) == 0:
        return float("nan")
    zirve = np.maximum.accumulate(e)
    return float(((zirve - e) / zirve).max())


def seri_ozeti(getiri: pd.Series, bilesik: bool = True) -> dict:
    """Günlük getiri serisinden toplam getiri / Sharpe / max düşüş."""
    x = getiri.to_numpy(dtype=float)
    e = np.r_[1.0, np.cumprod(1 + x)] if bilesik else np.r_[1.0, 1 + np.cumsum(x)]
    return {"getiri": float(e[-1] - 1), "sharpe": sharpe_gunluk(x), "max_dusus": max_dusus(e), "gun": int(len(x))}


# ============================================================================ korelasyon / örtüşme
def korelasyon_cifti(a: pd.Series, b: pd.Series, aralik_a: tuple, aralik_b: tuple,
                     min_gun: int = MIN_ORTAK_GUN) -> tuple:
    """İki günlük serinin OOS aralıklarının kesişiminde Pearson korelasyonu. -> (korelasyon, ortak_gün).
    Ölçülemezse (kesişim < min_gun ya da sabit seri) NaN."""
    bas = max(aralik_a[0], aralik_b[0])
    bit = min(aralik_a[1], aralik_b[1])
    if bit < bas:
        return float("nan"), 0
    gun = pd.date_range(bas.floor("D"), bit.floor("D"), freq="D")
    n = len(gun)
    if n < min_gun:
        return float("nan"), n
    x = a.reindex(gun).fillna(0.0).to_numpy()
    y = b.reindex(gun).fillna(0.0).to_numpy()
    if x.std() == 0 or y.std() == 0:
        return float("nan"), n
    return float(np.corrcoef(x, y)[0, 1]), n


def _birlestir(aralar: list) -> np.ndarray:
    """[(bas_ns, bit_ns)] -> birleşik, sıralı, kesişmeyen aralıklar (n,2)."""
    if not aralar:
        return np.zeros((0, 2), dtype=np.int64)
    a = np.array(sorted(aralar), dtype=np.int64)
    out = [list(a[0])]
    for s, e in a[1:]:
        if s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return np.array(out, dtype=np.int64)


def pozisyon_aralari(islemler: pd.DataFrame, sembol: str) -> dict:
    """{(sembol, yon): birleşik aralıklar}."""
    g = pd.DatetimeIndex(islemler["giris_zamani"]).as_unit("ns").asi8
    c = pd.DatetimeIndex(islemler["cikis_zamani"]).as_unit("ns").asi8
    y = islemler["yon"].to_numpy()
    out = {}
    for yon in (1, -1):
        m = y == yon
        if m.any():
            out[(sembol, yon)] = _birlestir(list(zip(g[m], c[m])))
    return out


def _kesisim_suresi(a: np.ndarray, b: np.ndarray) -> int:
    i = j = 0
    top = 0
    while i < len(a) and j < len(b):
        s, e = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if e > s:
            top += int(e - s)
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return top


def yonlu_ortusme(ara_a: dict, ara_b: dict) -> float:
    """Aynı sembol + aynı yön zaman kesişimi / min(iki adayın toplam açık kalma süresi). 0..1."""
    kesisim = sum(_kesisim_suresi(v, ara_b[k]) for k, v in ara_a.items() if k in ara_b)
    ta = sum(int((v[:, 1] - v[:, 0]).sum()) for v in ara_a.values())
    tb = sum(int((v[:, 1] - v[:, 0]).sum()) for v in ara_b.values())
    payda = min(ta, tb)
    return float(kesisim / payda) if payda > 0 else 0.0


def kumeler(kor: pd.DataFrame, esik: float = KUME_ESIGI) -> dict:
    """Ortalama bağlantılı hiyerarşik kümeleme (uzaklık = 1 - korelasyon, NaN = 1). Ortalama korelasyonu > esik
    olan kümeler birleşir. -> {kimlik: küme_no} (büyük küme önce, 1'den)."""
    ids = list(kor.index)
    k = kor.to_numpy(dtype=float).copy()
    k[np.isnan(k)] = 0.0
    np.fill_diagonal(k, 1.0)
    grup = [[i] for i in range(len(ids))]
    while len(grup) > 1:
        en, en_ij = -2.0, None
        for i in range(len(grup)):
            for j in range(i + 1, len(grup)):
                o = k[np.ix_(grup[i], grup[j])].mean()
                if o > en:
                    en, en_ij = o, (i, j)
        if en <= esik:
            break
        i, j = en_ij
        grup[i] = grup[i] + grup[j]
        del grup[j]
    grup.sort(key=lambda g: (-len(g), min(g)))
    return {ids[i]: n + 1 for n, g in enumerate(grup) for i in g}


# ============================================================================ açgözlü seçim
def acgozlu_sec(sirali: list, kor: pd.DataFrame, ortusme: Optional[pd.DataFrame] = None, n_secim: int = N_SECIM,
                n_yedek: int = N_YEDEK, esik_korr: float = ESIK_KORR, esik_ortusme: float = ESIK_ORTUSME) -> dict:
    """sirali: skora göre azalan kimlikler. İlk eleman seçilir; sonrakiler seçilenlerin HEPSİYLE
    korelasyon <= esik_korr (NaN = ölçülemedi -> geçer, 'olculemedi' olarak işaretlenir) ve yönlü örtüşme <= esik_ortusme
    ise eklenir. İlk n_secim = seçim, sonraki n_yedek = yedek.
    -> {'secim': [...], 'yedek': [...], 'elenen': {kimlik: neden}, 'max_korr': {kimlik: en yüksek korelasyon (seçilenlerle)}}"""
    kabul, elenen, maxk = [], {}, {}
    hedef = n_secim + n_yedek
    for c in sirali:
        if len(kabul) >= hedef:
            break
        mk = -np.inf
        neden = None
        for s in kabul[:]:
            kv = kor.loc[c, s] if (c in kor.index and s in kor.columns) else np.nan
            ov = ortusme.loc[c, s] if (ortusme is not None and c in ortusme.index and s in ortusme.columns) else 0.0
            if not np.isnan(kv):
                mk = max(mk, kv)
            if not np.isnan(kv) and kv > esik_korr:
                neden = f"korelasyon {kv:.2f} > {esik_korr} ({s})"
                break
            if not np.isnan(ov) and ov > esik_ortusme:
                neden = f"yönlü örtüşme {ov:.2f} > {esik_ortusme} ({s})"
                break
        if neden:
            elenen[c] = neden
        else:
            kabul.append(c)
            maxk[c] = float(mk) if np.isfinite(mk) else float("nan")
    return {"secim": kabul[:n_secim], "yedek": kabul[n_secim:], "elenen": elenen, "max_korr": maxk}


# ============================================================================ yeniden oynatıcı
@dataclass
class OynatmaAyari:
    risk: float = 0.01              # işlem başı
    toplam_risk: float = 0.05       # açık toplam risk tavanı
    kaldirac: float = 3.0
    gunluk_kayip: float = 0.03
    kill: float = 0.20
    min_olcek: float = MIN_OLCEK


def islem_tablosu_hazirla(parcalar: dict) -> pd.DataFrame:
    """parcalar: {kol_kimligi: (islemler DataFrame, sembol)} -> birleşik tablo
    (kol, sembol, yon, giris, cikis, r, sf). sf = stop uzaklığı oranı (risk$/nominal): 1x-risk kaldıracı = RISK/sf.
    Risk$ = net_pnl/r (r küçükken gürültülü: |r| < 0.05 satırları komşudan doldurulur)."""
    out = []
    for kol, (d, sembol) in parcalar.items():
        d = d.sort_values("giris_zamani", kind="stable").reset_index(drop=True)
        r = d["r"].to_numpy(dtype=float)
        nominal = (d["miktar"] * d["giris_fiyati"]).to_numpy(dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            risk_usd = np.where(np.abs(r) >= 0.05, d["net_pnl"].to_numpy(dtype=float) / r, np.nan)
            sf = risk_usd / nominal
        sf = pd.Series(sf).ffill().bfill().fillna(0.05).clip(lower=1e-4).to_numpy()
        out.append(pd.DataFrame({"kol": kol, "sembol": sembol, "yon": d["yon"].to_numpy(),
                                 "giris": pd.DatetimeIndex(d["giris_zamani"]), "cikis": pd.DatetimeIndex(d["cikis_zamani"]),
                                 "r": r, "sf": sf}))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(
        columns=["kol", "sembol", "yon", "giris", "cikis", "r", "sf"])


def yeniden_oyna(tablo: pd.DataFrame, ayar: OynatmaAyari = None, bas=None, bit=None) -> dict:
    """tablo: islem_tablosu_hazirla çıktısı (kol, sembol, yon, giris, cikis, r, sf). Tek hesapta olay sırasıyla oynatır
    (modül belgesi madde 6). -> {'gunluk': Series(günlük MTM özsermaye, başlangıç 1.0), 'getiri': günlük getiri,
    'olaylar': [dict], 'sayac': {...}, 'kabul': kabul edilen satır dizinleri}."""
    ay = ayar or OynatmaAyari()
    if len(tablo) == 0:
        raise ValueError("boş işlem tablosu")
    T = tablo.reset_index(drop=True)
    g_ns = pd.DatetimeIndex(T["giris"]).as_unit("ns").asi8
    c_ns = pd.DatetimeIndex(T["cikis"]).as_unit("ns").asi8
    r = T["r"].to_numpy(dtype=float)
    sf = T["sf"].to_numpy(dtype=float)
    bas_ts = (pd.DatetimeIndex(T["giris"]).min() if bas is None else pd.Timestamp(bas)).floor("D")
    bit_ts = (pd.DatetimeIndex(T["cikis"]).max() if bit is None else pd.Timestamp(bit)).floor("D") + pd.Timedelta(days=1)
    geceler = pd.date_range(bas_ts, bit_ts, freq="D")
    # olay: (zaman_ns, tür, indeks); tür -1 gece yarısı, 0 çıkış, 1 giriş
    olay = [(t.as_unit('ns').value, -1, -1) for t in geceler]
    olay += [(int(c_ns[i]), 0, i) for i in range(len(T))]
    olay += [(int(g_ns[i]), 1, i) for i in range(len(T))]
    olay.sort()

    nakit, zirve = 1.0, 1.0
    gun_basi, gun_kilit, olu = None, False, False
    acik = {}          # i -> (risk_usd, kaldirac_nominal)
    sayac = {"giris_kabul": 0, "reddedilen": 0, "kirpilan": 0, "red_toplam_risk": 0, "red_kaldirac": 0,
             "red_gunluk": 0, "red_kill": 0, "gunluk_limit_olayi": 0, "kill_olayi": 0, "zorla_kapanan": 0}
    olaylar, gunluk_ozs = [], {}
    kabul = []
    islem_pnl = {}     # i -> (gerçekleşme zamanı ns, kâr/zarar; başlangıç özsermayesi = 1.0 birimi); zorla kapanışlar dahil (Aşama 3 pano için)

    def mtm(t):
        # MUHAFAZAKÂR değerleme: gerçekleşmiş nakit + açık pozisyonların yalnız ZARARI (doğrusal yol); kâr çıkışta sayılır
        top = nakit
        for i, (rk, _) in acik.items():
            d = c_ns[i] - g_ns[i]
            f = 1.0 if d <= 0 else min(max((t - g_ns[i]) / d, 0.0), 1.0)
            top += min(0.0, rk * r[i] * f)
        return top

    def hepsini_kapat(t, neden):
        nonlocal nakit
        for i, (rk, _) in list(acik.items()):
            d = c_ns[i] - g_ns[i]
            f = 1.0 if d <= 0 else min(max((t - g_ns[i]) / d, 0.0), 1.0)
            nakit += rk * r[i] * f
            islem_pnl[i] = (int(t), rk * r[i] * f)
            sayac["zorla_kapanan"] += 1
        acik.clear()
        olaylar.append({"zaman": str(pd.Timestamp(t, tz="UTC")), "olay": neden})

    for t, tur, i in olay:
        if tur == -1:
            gun_basi, gun_kilit = mtm(t), False
            gunluk_ozs[pd.Timestamp(t, tz="UTC")] = nakit      # seri = GERÇEKLEŞMİŞ özsermaye (wf_tarama ile aynı mantık)
            continue
        m = mtm(t)
        zirve = max(zirve, m)
        if not olu and m <= zirve * (1 - ay.kill):
            hepsini_kapat(t, "kill_switch")
            sayac["kill_olayi"] += 1
            olu = True
            m = mtm(t)
        elif not olu and not gun_kilit and gun_basi and m / gun_basi - 1 <= -ay.gunluk_kayip:
            hepsini_kapat(t, "gunluk_limit")
            sayac["gunluk_limit_olayi"] += 1
            gun_kilit = True
            m = mtm(t)
        if tur == 0:
            if i in acik:
                rk, _ = acik.pop(i)
                nakit += rk * r[i]
                islem_pnl[i] = (int(t), rk * r[i])
            continue
        # giriş
        if olu:
            sayac["reddedilen"] += 1; sayac["red_kill"] += 1; continue
        if gun_kilit:
            sayac["reddedilen"] += 1; sayac["red_gunluk"] += 1; continue
        hedef_risk = ay.risk * m
        oda = ay.toplam_risk * m - sum(rk for rk, _ in acik.values())
        olcek = min(1.0, oda / hedef_risk) if hedef_risk > 0 else 0.0
        neden_red = "red_toplam_risk"
        brut = sum(n for _, n in acik.values())
        nominal_1 = hedef_risk / sf[i]
        if olcek >= ay.min_olcek:
            oda_k = ay.kaldirac * m - brut
            if oda_k < nominal_1 * olcek:
                olcek = min(olcek, oda_k / nominal_1) if nominal_1 > 0 else 0.0
                neden_red = "red_kaldirac"
        if olcek < ay.min_olcek:
            sayac["reddedilen"] += 1; sayac[neden_red] += 1; continue
        if olcek < 1.0:
            sayac["kirpilan"] += 1
        acik[i] = (hedef_risk * olcek, nominal_1 * olcek)
        sayac["giris_kabul"] += 1
        kabul.append(i)
    ozs = pd.Series(gunluk_ozs).sort_index()
    getiri = ozs.pct_change().dropna()
    return {"gunluk": ozs, "getiri": getiri, "olaylar": olaylar, "sayac": sayac, "kabul": kabul,
            "nakit_son": nakit, "islem_pnl": islem_pnl}


# ============================================================================ aday tablosu
def aday_hazirla(havuz: pd.DataFrame, wf: pd.DataFrame) -> tuple:
    """Her havuz satırı için işlemler, günlük serileri, aralık ve ölçüler. -> (adaylar DataFrame, veri dict)."""
    veri, satirlar = {}, []
    for _, h in havuz.iterrows():
        cid = kimlik(h.strateji, h.sembol, h.tf)
        d = islem_oku(h.strateji, h.sembol, h.tf)
        w = wf[(wf.strateji == h.strateji) & (wf.sembol == h.sembol) & (wf.tf == h.tf)].iloc[0]
        aralik = (pd.Timestamp(w.oos_bas), pd.Timestamp(w.oos_bit))
        yay = gunluk_getiri(d, "yay", bas=aralik[0], bit=aralik[1])
        cik = gunluk_getiri(d, "cikis", bas=aralik[0], bit=aralik[1])
        veri[cid] = {"islem": d, "yay": yay, "cikis": cik, "aralik": aralik,
                     "pozisyon": pozisyon_aralari(d, h.sembol), "tur": "tek", "sembol": h.sembol}
        skor = float(w.sharpe) * (1 - float(h.rnd_p))
        satir = {"kimlik": cid, "tur": "tek", "ajan": h.stil, "strateji": h.strateji, "sembol": h.sembol, "tf": h.tf,
                 "skor": skor, "oos_sharpe": float(w.sharpe), "rnd_p": float(h.rnd_p), "pf": float(w.profit_factor),
                 "pf_ex5": float(w.en_iyi_yuzde5_haric_pf), "max_dusus": float(w.max_dusus),
                 "islem": int(w.islem_sayisi), "oos_bas": str(aralik[0].date()), "oos_bit": str(aralik[1].date()),
                 "net_getiri": float(w.net_getiri), "m2_pf": float(h.m2_pf), "pf_boot_alt": float(h.pf_boot_alt),
                 "bh_sharpe": float(w.bh_sharpe)}
        for y in range(2020, 2026):
            satir[f"net_{y}"] = float(w[f"net_{y}"]) if pd.notna(w[f"net_{y}"]) else np.nan
            satir[f"n_{y}"] = int(w[f"n_{y}"])
        satirlar.append(satir)
    return pd.DataFrame(satirlar), veri


def portfoy_adaylari() -> tuple:
    """Sağlam portföy stratejileri (saglam_mi=True) ve OOS günlük getirileri."""
    satirlar, veri = [], {}
    for csv in sorted(PF_SAGLAMLIK.glob("p3_*_v3.csv")) + [PF_SAGLAMLIK / "p3_kripto_v2.csv"]:
        etiket = csv.stem
        d = pd.read_csv(csv)
        for _, r in d[d["saglam_mi"].astype(bool)].iterrows():
            yol = PF_GUNLUK / etiket / f"{r.strateji}--{r.evren}--{r.tf}.parquet"
            g = pd.read_parquet(yol)["oos_getiri"].astype(float)
            cid = f"{r.strateji}|{r.evren}|{r.tf}"
            aralik = (g.index.min(), g.index.max())
            veri[cid] = {"gunluk": g, "yay": g, "cikis": g, "aralik": aralik, "pozisyon": {}, "tur": "portfoy",
                         "sembol": r.evren}
            satirlar.append({"kimlik": cid, "tur": "portfoy", "ajan": "portfoy", "strateji": r.strateji,
                             "sembol": r.evren, "tf": r.tf, "skor": float(r.sharpe) * (1 - float(r.rnd_p)),
                             "oos_sharpe": float(r.sharpe), "rnd_p": float(r.rnd_p), "pf": np.nan, "pf_ex5": np.nan,
                             "max_dusus": float(r.max_dusus), "islem": np.nan, "oos_bas": str(aralik[0].date()),
                             "oos_bit": str(aralik[1].date()), "net_getiri": float(r.net_getiri),
                             "m2_pf": np.nan, "pf_boot_alt": np.nan, "bh_sharpe": float(r.bh_sharpe),
                             "boot_alt_sharpe": float(r.boot_alt)})
    return pd.DataFrame(satirlar), veri


def korelasyon_matrisleri(veri: dict) -> tuple:
    """-> (kor_yay, kor_cikis, ortusme, ortak_gun) DataFrame'leri (kimlik x kimlik)."""
    ids = list(veri)
    n = len(ids)
    ky, kc, ort, og = (np.full((n, n), np.nan) for _ in range(4))
    for i in range(n):
        for j in range(i, n):
            a, b = veri[ids[i]], veri[ids[j]]
            if i == j:
                ky[i, j] = kc[i, j] = 1.0
                ort[i, j] = 1.0
                og[i, j] = len(pd.date_range(a["aralik"][0].floor("D"), a["aralik"][1].floor("D"), freq="D"))
                continue
            for mat, mod in ((ky, "yay"), (kc, "cikis")):
                v, ng = korelasyon_cifti(a[mod], b[mod], a["aralik"], b["aralik"])
                mat[i, j] = mat[j, i] = v
                og[i, j] = og[j, i] = ng
            o = yonlu_ortusme(a["pozisyon"], b["pozisyon"]) if a["pozisyon"] and b["pozisyon"] else 0.0
            ort[i, j] = ort[j, i] = o
    f = lambda m: pd.DataFrame(m, index=ids, columns=ids)  # noqa: E731
    return f(ky), f(kc), f(ort), f(og)


# ============================================================================ set simülasyonu
def set_simule(ids: list, veri: dict, ayar: OynatmaAyari = None) -> dict:
    """Tek-grafik kollar için: yeniden oynatım + tek tek toplam kıyası."""
    parcalar = {c: (veri[c]["islem"], veri[c]["sembol"]) for c in ids}
    tablo = islem_tablosu_hazirla(parcalar)
    sonuc = yeniden_oyna(tablo, ayar)
    o = sonuc["getiri"]
    ozet = seri_ozeti(o)
    bas, bit = o.index.min(), o.index.max()
    gun = pd.date_range(bas, bit, freq="D")
    toplam = sum(veri[c]["cikis"].reindex(gun).fillna(0.0) for c in ids)
    tt = seri_ozeti(toplam, bilesik=True)
    sonuc.update({"kol": len(ids), "ozet": ozet, "tek_tek_toplam": tt, "n_islem_toplam": int(len(tablo)),
                  "yillik": yillik_getiri(o), "toplam_seri": toplam})
    return sonuc


def yillik_getiri(getiri: pd.Series) -> dict:
    return {int(y): float(np.prod(1 + g.to_numpy()) - 1) for y, g in getiri.groupby(getiri.index.year)}


def portfoy_set(ids: list, veri: dict) -> dict:
    """Portföy ajanı: eşit ağırlıklı günlük ortalama (ortak aralık)."""
    bas = max(veri[c]["aralik"][0] for c in ids)
    bit = min(veri[c]["aralik"][1] for c in ids)
    gun = pd.date_range(bas.floor("D"), bit.floor("D"), freq="D")
    df = pd.concat([veri[c]["gunluk"].reindex(gun).fillna(0.0) for c in ids], axis=1)
    ort = df.mean(axis=1)
    return {"getiri": ort, "ozet": seri_ozeti(ort), "yillik": yillik_getiri(ort), "tek": {c: seri_ozeti(df.iloc[:, k]) for k, c in enumerate(ids)}}


def harmanla(a: pd.Series, b: pd.Series, pay_a: float = 0.5) -> dict:
    """İki sleeve günlük getirisini ortak aralıkta pay_a/(1-pay_a) ile günlük yeniden dengeli harmanlar."""
    bas, bit = max(a.index.min(), b.index.min()), min(a.index.max(), b.index.max())
    gun = pd.date_range(bas, bit, freq="D")
    h = pay_a * a.reindex(gun).fillna(0.0) + (1 - pay_a) * b.reindex(gun).fillna(0.0)
    return {"getiri": h, "ozet": seri_ozeti(h), "yillik": yillik_getiri(h)}


# ============================================================================ rapor
def _p(x, d=1):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:.{d}f}%"


def _f(x, d=2):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}"


def _tablo_md(df: pd.DataFrame) -> str:
    satir = ["| yıl | " + " | ".join(map(str, df.columns)) + " |", "|---|" + "---|" * len(df.columns)]
    for y, r in df.iterrows():
        satir.append(f"| {y} | " + " | ".join(_p(v) for v in r) + " |")
    return "\n".join(satir)


def calistir(cikti: Path = CIKTI) -> dict:
    cikti.mkdir(parents=True, exist_ok=True)
    havuz = pd.read_csv(HAVUZ)
    wf = wf_ozet_oku()
    tek, veri = aday_hazirla(havuz, wf)
    pf, veri_pf = portfoy_adaylari()
    veri.update(veri_pf)
    adaylar = pd.concat([tek, pf], ignore_index=True)
    ky, kc, ort, og = korelasyon_matrisleri(veri)
    kume = kumeler(ky)
    adaylar["kume"] = adaylar["kimlik"].map(kume)

    # --- ajanlar
    ajanlar = {}
    for ajan in ("swing", "daytrade", "scalp", "portfoy"):
        alt = adaylar[adaylar.ajan == ajan].sort_values("skor", ascending=False)
        sirali = [c for c in alt.kimlik if alt.set_index("kimlik").loc[c, "skor"] > 0]
        ajanlar[ajan] = acgozlu_sec(sirali, ky, ort) if sirali else {"secim": [], "yedek": [], "elenen": {}, "max_korr": {}}

    # --- oneri.csv
    ai = adaylar.set_index("kimlik")
    satir = []
    for ajan, s in ajanlar.items():
        for rol, lst in (("secim", s["secim"]), ("yedek", s["yedek"])):
            for k, c in enumerate(lst, 1):
                a = ai.loc[c]
                ayni = [x for x in s["secim"] + s["yedek"] if x != c and ai.loc[x, "strateji"] == a.strateji]
                not_ = "aynı strateji, farklı enstrüman" if ayni else ""
                satir.append({"ajan": ajan, "rol": rol, "sira": k, "kimlik": c, "strateji": a.strateji, "sembol": a.sembol,
                              "tf": a.tf, "skor": a.skor, "oos_sharpe": a.oos_sharpe, "rnd_p": a.rnd_p, "pf": a.pf,
                              "max_dusus": a.max_dusus, "islem": a.islem, "net_2022": a.get("net_2022", np.nan),
                              "kume": a.kume, "secilenlerle_max_korr": s["max_korr"].get(c, np.nan), "not": not_})
    oneri = pd.DataFrame(satir)
    oneri.to_csv(cikti / "oneri.csv", index=False)
    adaylar.to_csv(cikti / "adaylar.csv", index=False)

    # --- korelasyon.csv (uzun biçim)
    ids = list(ky.index)
    kr = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            kr.append({"a": ids[i], "b": ids[j], "korr_yay": ky.iloc[i, j], "korr_cikis": kc.iloc[i, j],
                       "yonlu_ortusme": ort.iloc[i, j], "ortak_gun": og.iloc[i, j]})
    pd.DataFrame(kr).to_csv(cikti / "korelasyon.csv", index=False)

    # --- simülasyonlar
    sim_satir, sim_detay = [], {}
    tek_ajanlar = [a for a in ("swing", "daytrade") if ajanlar[a]["secim"]]
    for ajan in tek_ajanlar:
        sim_detay[ajan] = set_simule(ajanlar[ajan]["secim"], veri)
    tum_tek = [c for a in tek_ajanlar for c in ajanlar[a]["secim"]]
    if tum_tek:
        sim_detay["tek_grafik_tum"] = set_simule(tum_tek, veri)
    # stres: havuzdaki TÜM tek-grafik kollar (limitlerin gerçekten devreye girdiği durum; öneri değil)
    sim_detay["stres_tum_havuz"] = set_simule(list(tek.kimlik), veri)
    pf_ids = ajanlar["portfoy"]["secim"]
    if pf_ids:
        sim_detay["portfoy"] = portfoy_set(pf_ids, veri)
    if tum_tek and pf_ids:
        sim_detay["tum_kasa"] = harmanla(sim_detay["tek_grafik_tum"]["getiri"], sim_detay["portfoy"]["getiri"])
    for ad, s in sim_detay.items():
        o = s["ozet"]
        sc = s.get("sayac", {})
        t = s.get("tek_tek_toplam", {})
        sim_satir.append({"set": ad, "kol_sayisi": s.get("kol", len(pf_ids) if ad == "portfoy" else len(tum_tek) + len(pf_ids)),
                          "getiri": o["getiri"], "sharpe": o["sharpe"], "max_dusus": o["max_dusus"], "gun": o["gun"],
                          "gunluk_limit_olayi": sc.get("gunluk_limit_olayi", np.nan), "kill_olayi": sc.get("kill_olayi", np.nan),
                          "reddedilen": sc.get("reddedilen", np.nan), "kirpilan": sc.get("kirpilan", np.nan),
                          "giris_kabul": sc.get("giris_kabul", np.nan), "islem_toplam": s.get("n_islem_toplam", np.nan),
                          "tek_tek_toplam_getiri": np.nan if ad.startswith("stres") else t.get("getiri", np.nan), "tek_tek_toplam_sharpe": t.get("sharpe", np.nan),
                          "tek_tek_toplam_max_dusus": t.get("max_dusus", np.nan)})
    pd.DataFrame(sim_satir).to_csv(cikti / "birlesik.csv", index=False)
    yil = pd.DataFrame({ad: pd.Series(s["yillik"]) for ad, s in sim_detay.items()}).sort_index()
    yil.to_csv(cikti / "birlesik_yillik.csv")

    md = ozet_yaz(adaylar, ajanlar, ky, ort, kume, sim_detay, pd.DataFrame(sim_satir), yil, veri)
    (cikti / "ozet.md").write_text(md, encoding="utf-8")
    return {"adaylar": adaylar, "ajanlar": ajanlar, "oneri": oneri, "sim": sim_detay, "ky": ky, "kume": kume, "ort": ort}


def ozet_yaz(adaylar, ajanlar, ky, ort, kume, sim, sim_tablo, yil, veri) -> str:
    ai = adaylar.set_index("kimlik")
    L = ["# Final seçim önerisi (ajan başına ~3 strateji)", "",
         "_Bu bir ÖNERİDİR; seçimi kullanıcı onaylar. Yalnız OOS (walk-forward test pencereleri) verisi kullanıldı; yeni "
         "parametre seçilmedi, kilitli döneme dokunulmadı._", "",
         "## Yöntem (sade)",
         "- **Aday havuzu:** 51 tek-grafik satırı (34 strateji; kripto + Mag7 hisseleri) + sağlamlık testini geçen 4 portföy stratejisi.",
         "- **Skor:** OOS Sharpe x (1 - rastgele giriş p). Sharpe yüksek ve rastgele girişten ayırt edilebilir olan öne geçer.",
         f"- **Çeşitlendirme:** En iyi skorla başla; sonraki aday, seçilenlerle günlük getiri korelasyonu <= {ESIK_KORR} ve aynı "
         f"sembol + aynı yönde zaman örtüşmesi <= {int(ESIK_ORTUSME * 100)}% ise eklenir. İlk 3 = öneri, sonraki 5 = yedek.",
         "- **Aynı strateji, farklı enstrüman** ayrı kol sayıldı (aşağıda 'not' sütununda işaretli).",
         "- **Günlük getiri:** işlem başı %1 risk, R x %1; günlük MTM yok, bu yüzden işlem getirisi açık kaldığı günlere "
         "doğrusal yayıldı (yaklaşık). Korelasyon bu seriyle hesaplandı.",
         "- **Birleşik simülasyon:** seçilen setin OOS işlemleri tek hesapta olay sırasıyla yeniden oynatıldı; sert limitler: "
         "işlem başı %1, toplam açık risk %5, 3x, günlük %3 (açık pozisyonlar kapanır, gün boyu giriş yok), %20 kill. "
         "Açık pozisyonların anlık değeri bilinmediğinden limit olayları yaklaşıktır.", ""]
    for ajan, baslik in (("swing", "Swing ajanı"), ("daytrade", "Day trade ajanı"), ("scalp", "Scalp ajanı"),
                         ("portfoy", "Portföy ajanı")):
        s = ajanlar[ajan]
        L += [f"## {baslik}", ""]
        if not s["secim"]:
            L += ["Aday yok (hiçbir aday karar 13 / sağlamlık kapısını geçmedi) -> ajan kapalı kalır (karar 11).", ""]
            continue
        L += ["| rol | strateji | sembol/evren | tf | skor | OOS Sharpe | rastgele p | PF | max düşüş | işlem | 2022 net | küme | seçilenlerle max korr | not |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for rol, lst in (("ÖNERİ", s["secim"]), ("yedek", s["yedek"])):
            for c in lst:
                a = ai.loc[c]
                ayni = [x for x in s["secim"] + s["yedek"] if x != c and ai.loc[x, "strateji"] == a.strateji]
                L.append(f"| {rol} | {a.strateji} | {a.sembol} | {a.tf} | {_f(a.skor)} | {_f(a.oos_sharpe)} | {_f(a.rnd_p, 3)} | "
                         f"{_f(a.pf)} | {_p(a.max_dusus)} | {'-' if pd.isna(a.islem) else int(a.islem)} | "
                         f"{_p(a.get('net_2022', np.nan))} | {int(a.kume)} | {_f(s['max_korr'].get(c, np.nan))} | "
                         f"{'aynı strateji, farklı enstrüman' if ayni else ''} |")
        ne = {k: v for k, v in s["elenen"].items()}
        if ne:
            L += ["", f"Çeşitlendirme nedeniyle atlanan aday sayısı: {len(ne)} (ör. " +
                  "; ".join(f"{ai.loc[k, 'strateji']}/{ai.loc[k, 'sembol']}: {v}" for k, v in list(ne.items())[:3]) + ")."]
        L.append("")
    kn = pd.Series(kume).value_counts()
    L += [f"**Korelasyon kümeleri:** {len(kn)} küme (ortalama korelasyon > {KUME_ESIGI} aynı küme); en büyük 3 küme "
          f"{', '.join(str(x) for x in kn.head(3).tolist())} adaylık. Ayrıntı: korelasyon.csv, adaylar.csv ('kume').", ""]
    # birleşik
    L += ["## Birleşik OOS sonucu (seçilen setler)", "",
          "| set | kol | birleşik getiri | Sharpe | max düşüş | günlük limit | kill | reddedilen | kırpılan | tek tek toplam getiri | tek tek toplam Sharpe | tek tek toplam düşüş |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in sim_tablo.iterrows():
        L.append(f"| {r['set']} | {'-' if pd.isna(r.kol_sayisi) else int(r.kol_sayisi)} | {_p(r.getiri)} | {_f(r.sharpe)} | {_p(r.max_dusus)} | "
                 f"{'-' if pd.isna(r.gunluk_limit_olayi) else int(r.gunluk_limit_olayi)} | "
                 f"{'-' if pd.isna(r.kill_olayi) else int(r.kill_olayi)} | "
                 f"{'-' if pd.isna(r.reddedilen) else int(r.reddedilen)} | {'-' if pd.isna(r.kirpilan) else int(r.kirpilan)} | "
                 f"{_p(r.tek_tek_toplam_getiri)} | {_f(r.tek_tek_toplam_sharpe)} | {_p(r.tek_tek_toplam_max_dusus)} |")
    L += ["",
          "- 'Tek tek toplam': kolların çıkış-günü getirileri her biri aynı kasada %1 riskle, limitsiz ve kırpmasız toplanıp bileşiklenir. Fark = limitlerin ve ortak kasanın etkisi.",
          "- 'tum_kasa' = tek-grafik kollar (swing+daytrade, ortak limitli yeniden oynatım) %50 + portföy ajanı seti %50 (günlük getiri "
          "düzeyinde harman, ortak limit kontrolü yok), yalnız iki serinin ortak tarih aralığında.",
          "- 'stres_tum_havuz': 51 kolun hepsi tek kasada (öneri değil; sert limitlerin gerçekten devreye girdiğini göstermek için).",
          "- Portföy seti: kendi motorunda limitler uygulanmış günlük getirilerin eşit ağırlıklı ortalaması (limit sayıları yok).", "",
          "### Yıl bazında birleşik getiri", "", _tablo_md(yil), ""]
    L += ["## Riskler ve dikkat edilecekler", "",
          "- **Boğa dönemi:** OOS'un büyük kısmı 2019–2025 boğa (kripto 2020–21, Mag7 hisseleri). Kazancın hangi yıllarda toplandığı "
          "yukarıdaki yıl tablosunda; 2022 (ayı) sonuçları aday tablosunda 'net_2022' sütununda. Boğaya bağımlı seçimler ayıda zayıf kalabilir.",
          "- **Yoğunlaşma:** kümeler aşağıdaki sayıda; swing adaylarının çoğu aynı birkaç hisse (TSLA, NVDA, AAPL) üzerinde. Farklı strateji olsa da "
          "ortak sürücü (Mag7 boğası) aynıdır; korelasyon <= 0.5 koşulu bunu ancak kısmen sınırlar.",
          "- **Tek sembole bağımlılık:** day trade tarafında yalnız ETH (dual-thrust 1h ve 30m aynı strateji, neredeyse aynı işlemler).",
          "- **Emtiada aday yok:** altın/petrol/bakırda tek-grafik sağlam strateji çıkmadı; emtia yalnız portföy ajanında (kanarya) dolaylı.",
          "- **Scalp yok:** kriptoda 0 geçen, TradFi dakikalık veri bekleniyor -> scalp ajanı şimdilik kapalı (karar 11).",
          "- **Çoklu test:** Bonferroni'yi hiçbiri geçmiyor, DSR ~ 0 (DURUM.md). Skor ve seçim OOS'a bakılarak yapıldığından "
          "bu sayılar iyimserdir; asıl bağımsız sınav kilitli dönemdir (karar 20; yalnız kullanıcı onayıyla ve bir kez).",
          "- **Yaklaşıklıklar:** günlük MTM yok (doğrusal yay), limit kontrolleri olay anlarında, zorla kapatmada kayma yok, "
          "ardışık pencerelerde seçilen adaylar zamanda çakışabilir.", ""]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cikti", default=str(CIKTI))
    a = ap.parse_args(argv)
    calistir(Path(a.cikti))


if __name__ == "__main__":
    main()
