"""Sağlamlık analizi (Aşama 2, Katman 3b): walk-forward'da karar 13'ü geçenler şans eseri mi geçti?

Girdi: sonuclar/wf/<wf_etiket>.parquet (gecti == True satırları) + sonuclar/wf/islemler/<wf_etiket>/*.parquet
(seçilen adayların birleşik OOS işlemleri). Çıktı: sonuclar/saglamlik/<etiket>.csv (+ .parquet), satır başına
tüm ölçüler ve bir ÖNERİ sütunu `saglam_mi`. Bu bir öneridir; son karar kullanıcı/liderindir.

ÖNERİ KURALI (koşudan ÖNCE sabitlendi; sonuçlara bakılarak değiştirilmez) — dört kapının HEPSİ geçilmeli:
  K1  maliyet x2 stresinde OOS PF >= 1.05           (aynı aday kümesi/pencere/skor; komisyon ve kayma x2)
  K2  rastgele giriş p-değeri <= 0.05               (aşağıdaki yöntem 2)
  K3  blok bootstrap OOS PF %90 aralığının alt sınırı > 1.0
  K4  komşu parametre ayarlarının >= %60'ında sabit-ayar OOS PF > 1   (geçerli komşu yoksa kapı geçilmez)
Yalnız RAPORLANAN, kapı OLMAYAN ölçüler (ilk sürüm): deflated Sharpe (DSR), rejim kırılımı, yıl kırılımı,
komşu sembol/TF tutarlılığı. 32 aday aynı anda sınandığı için K2'nin p-değerleri de çoklu teste açıktır
(Bonferroni için 0.05/aday sayısı bakılabilir); bu da raporlanır (`rnd_p`), kapıyı değiştirmez.

YÖNTEMLER
 1. Maliyet x2: wf_tarama.gorev_calistir, wf_tarama.maliyet_ayarlari(carpan=2) ile (komisyon taker/maker, kayma_bps,
    stop_kayma_bps iki katı; funding aynı). Aynı aday kümesi, pencere ve eğitim skoru; yeni seçim yeniden yapılır
    (maliyet artınca eğitimde başka aday seçilebilir; bu gerçek bir stres senaryosudur). OOS PF ve net getiri.
 2. Rastgele giriş (Monte Carlo, N_SIM >= 200; varsayılan 500). Gerçek OOS işlemlerinin her biri için (yon, tutma
    süresi H mum, stop mesafesi / ATR(14) katı m) üçlüsü korunur; giriş ZAMANI rastgele çekilir: stratejinin
    gerçekten bir aday seçtiği test pencerelerindeki (secimler: secilen != None) mumların içinden, tekdüze.
    Rastgele işlem: sinyal mumu j-1 kapanışında stop = kapanis[j-1] -/+ m * ATR14[j-1] (yalnız kapalı mumlar:
    lookahead yok), giriş mum j AÇILIŞINDA (motorla aynı kayma), mum j..j+H-1'de stop mum içi yüksek/düşükle
    izlenir (gap'te açılıştan, stop_kayma_bps motorla aynı), stop görülmezse mum j+H açılışında zaman çıkışı (kayma).
    Komisyon motorla aynı (taker iki yön). R = net / |giriş - stop| (motorun R tanımı). Stop geçersizse (giriş
    stopun ötesinde) bu işlem için en çok 10 yeniden çekim; olmazsa o işlem atlanır (rnd_gecersiz oranı raporlanır).
    Yaklaşıklıklar: rastgele işlemler zamanda çakışabilir (R toplamında etkisiz); funding hesaba katılmaz;
    tutma süresi gerçek işlemin süresidir ve stop erken keserse daha kısa tutulur; hedef/izleyen stop yok.
    İstatistik: stratejinin OOS toplam R'si (gerçek motordan) rastgele toplam R dağılımında;
    p = (1 + #{sim >= gerçek}) / (N_SIM + 1) (tek taraflı). rnd_yuzdelik = gerçeğin altında kalan sim oranı.
 3. DSR (Bailey & López de Prado 2014). OOS günlük getiri serisi (R x %1 risk, bileşik; tüm UTC günleri; wf_tarama
    ile aynı), SR_hat günlük, T gün, çarpıklık/basıklık örneklemden. SR0 = sqrt(V) * ((1-g) Z(1-1/N) + g Z(1-1/(N e))),
    g = Euler–Mascheroni, Z = normal ters CDF. V = tüm WF görevlerinin (işlem yapanların) günlük Sharpe'larının
    (k3 `sharpe` / sqrt(365)) varyansı (deneme dağılımının yaklaşığı; kaba ve muhafazakâr). N üç şekilde:
    dsr_aday (N = görevin aday sayısı), dsr_evren (N = deneme_kaydi.jsonl'daki benzersiz walk-forward görev sayısı),
    dsr_kosu (N = o görevlerin toplam backtest koşusu; en katı). DSR = PSR(SR0) = olasılık(gerçek SR > SR0).
    Blok bootstrap: OOS işlemleri çıkış sırasıyla, dairesel bloklar (20 işlem), 2000 yeniden örnekleme, PF'nin
    %5 ve %95 yüzdelikleri (pf_boot_alt/ust).
 4. Parametre duyarlılığı: görevin en sık seçilen ayarı (`en_sik_ayar`); her SAYISAL (bool olmayan) parametresi
    için ızgarada ±1 adım (değer ızgarada yoksa ±%20; int ise yuvarlanır; 0 değeri ve değişmeyen kopyalar atlanır;
    ızgara ucundaysa tek komşu). Her komşu TÜM veride koşulur, OOS aralığındaki (ilk test başı – son test sonu)
    girişlerin PF(R)'si "sabit ayar PF"dir (pencere seçimi yok). Çıkış ayarları (cikis_ayarlari) oynatılmaz.
    par_oran = PF>1 olan komşu oranı. Kurulamayan/koşulamayan komşular par_hata'da sayılır.
 5. Rejim (nedensel): sembolün günlük kapanışından 200 günlük SMA ve 20 günlük eğimi (SMA/SMA[-20] - 1).
    boğa: kapanış > SMA ve eğim > 0; ayı: kapanış < SMA ve eğim < 0; kalanı yatay; SMA hesaplanamayan ilk günler
    "belirsiz". Bir işlemin rejimi, girişin UTC gününden bir önceki TAMAMLANMIŞ günün değeriyle belirlenir.
    Her rejim için OOS işlem sayısı ve PF.
 6. Komşu sembol/TF: aynı strateji, WF tablosunda diğer (sembol, tf) görevleri: sayı, PF>1 olan, karar 13'ü geçen,
    medyan PF ve ayrıntı listesi.

Kilit (karar 20): veri yalnız wf_tarama._veri (depo.mum_oku) ile okunur; kilit_ac yok.

CLI: python -m motor.arastirma.saglamlik --wf-etiket k3_kripto [--surec 4] [--n-sim 500]
Kaldığı yerden devam: biten görevler sonuclar/saglamlik/<etiket>.parquet'ten atlanır.
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import time
import zlib
from pathlib import Path
from statistics import NormalDist
from typing import Optional

import numpy as np
import pandas as pd

from motor.arastirma import tarama, wf_tarama
from motor.backtest import deneme_kaydi
from motor.backtest.motor import backtest
from motor.strateji import gostergeler as gst

KOK = Path(__file__).resolve().parents[2]
CIKTI_DIZINI = KOK / "sonuclar" / "saglamlik"

# ---- öneri kuralı (sabit; bkz. modül başı) ----
KAPI_M2_PF = 1.05
KAPI_RASTGELE_P = 0.05
KAPI_BOOT_ALT = 1.0
KAPI_KOMSU_ORAN = 0.60

N_SIM = 500
N_BOOT = 2000
BLOK = 20
ATR_PERIYOT = 14
YENIDEN_CEKIM = 10
EULER_GAMA = 0.5772156649015329
_N = NormalDist()


# ---------------------------------------------------------------------------- saf istatistik
def pf_boot(r, blok: int = BLOK, n_boot: int = N_BOOT, rng=None, alfa: float = 0.10) -> tuple:
    """Dairesel blok bootstrap ile PF güven aralığı -> (alt, ust, medyan). r zaman sırasındadır."""
    r = np.asarray(r, dtype=float)
    n = len(r)
    if n < 2:
        return math.nan, math.nan, math.nan
    rng = rng if rng is not None else np.random.default_rng(0)
    blok = max(1, min(blok, n))
    nb = math.ceil(n / blok)
    basla = rng.integers(0, n, size=(n_boot, nb))
    idx = ((basla[:, :, None] + np.arange(blok)[None, None, :]) % n).reshape(n_boot, nb * blok)[:, :n]
    x = r[idx]
    pos, neg = np.clip(x, 0, None).sum(1), -np.clip(x, None, 0).sum(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        pf = np.where(neg > 0, pos / neg, np.where(pos > 0, np.inf, np.nan))
    if np.all(np.isnan(pf)):
        return math.nan, math.nan, math.nan
    lo, med, hi = np.nanpercentile(pf, [100 * alfa / 2, 50, 100 * (1 - alfa / 2)])
    return float(lo), float(hi), float(med)


def beklenen_maks_sr(n_deneme: float, sr_varyans: float) -> float:
    """SR0: N bağımsız denemenin en iyisinin beklenen Sharpe'ı (SR'lar N(0, V) varsayımı)."""
    if n_deneme <= 1 or not sr_varyans > 0:
        return 0.0
    g = EULER_GAMA
    return math.sqrt(sr_varyans) * ((1 - g) * _N.inv_cdf(1 - 1 / n_deneme)
                                    + g * _N.inv_cdf(1 - 1 / (n_deneme * math.e)))


def deflated_sharpe(getiri, n_deneme: float, sr_varyans: float) -> dict:
    """Bailey & López de Prado DSR. getiri: periyodik (günlük) getiri serisi; SR günlük (yıllıklaştırılmaz).
    -> {sr, sr0, dsr, T, carpiklik, basiklik}. dsr = P(gerçek SR > SR0)."""
    x = np.asarray(getiri, dtype=float)
    x = x[~np.isnan(x)]
    T = len(x)
    bos = {"sr": math.nan, "sr0": math.nan, "dsr": math.nan, "T": T, "carpiklik": math.nan, "basiklik": math.nan}
    if T < 3 or x.std(ddof=1) == 0:
        return bos
    sr = float(x.mean() / x.std(ddof=1))
    m = x - x.mean()
    s2 = (m ** 2).mean()
    skew = float((m ** 3).mean() / s2 ** 1.5)
    kurt = float((m ** 4).mean() / s2 ** 2)              # aşırı değil (normal = 3)
    sr0 = beklenen_maks_sr(n_deneme, sr_varyans)
    payda = 1 - skew * sr + (kurt - 1) / 4 * sr ** 2
    if payda <= 0:
        return {**bos, "sr": sr, "sr0": sr0}
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(payda)
    return {"sr": sr, "sr0": sr0, "dsr": float(_N.cdf(z)), "T": T, "carpiklik": skew, "basiklik": kurt}


def gunluk_getiri(oos: pd.DataFrame, oos_bas, oos_bit, risk: float = wf_tarama.RISK) -> np.ndarray:
    """wf_tarama.oos_metrikleri'ndeki günlük sharpe serisinin aynısı: OOS aralığındaki tüm UTC günleri."""
    d = oos.sort_values("cikis_zamani", kind="stable")
    r = d["r"].to_numpy(dtype=float)
    ozs = np.r_[1.0, np.cumprod(1.0 + risk * r)]
    son = max(pd.Timestamp(oos_bit), d["cikis_zamani"].max())
    gunler = pd.date_range(pd.Timestamp(oos_bas).floor("D"), son.floor("D"), freq="D")
    gs = pd.Series(ozs[1:], index=pd.DatetimeIndex(d["cikis_zamani"])).groupby(lambda t: t.floor("D")).last()
    gs = gs.reindex(gs.index.union(gunler)).ffill().fillna(1.0).reindex(gunler)
    g = np.r_[1.0, gs.to_numpy()]
    return g[1:] / g[:-1] - 1.0


# ---------------------------------------------------------------------------- rastgele giriş
def islem_tanimlari(mumlar: pd.DataFrame, oos: pd.DataFrame, atr: np.ndarray) -> pd.DataFrame:
    """Gerçek OOS işlemlerinden (yon, H mum, stop_atr) üçlüleri. stop mesafesi = (net_pnl/r)/miktar (motorun R
    paydası), sinyal mumunun (giriş mumundan bir önceki) ATR'sine bölünür. Hesaplanamayanlara medyan yazılır."""
    idx = mumlar.index
    aralik = pd.Series(idx).diff().median()
    j = idx.get_indexer(pd.DatetimeIndex(oos["giris_zamani"]))
    if (j < 0).any():
        raise ValueError(f"OOS giriş zamanı mum indeksinde yok ({int((j < 0).sum())}/{len(j)}): WF işlemleri şimdiki "
                         "mum verisinden farklı veriyle üretilmiş (veri sonradan değişti); WF'yi yeniden koşun")
    h = np.maximum(1, np.rint((pd.DatetimeIndex(oos["cikis_zamani"]) - pd.DatetimeIndex(oos["giris_zamani"]))
                              / aralik)).astype(int)
    with np.errstate(divide="ignore", invalid="ignore"):
        mesafe = np.abs(oos["net_pnl"].to_numpy(float) / oos["r"].to_numpy(float) / oos["miktar"].to_numpy(float))
        a = atr[np.maximum(j - 1, 0)]
        m = mesafe / a
    gecerli = np.isfinite(m) & (m > 0) & (j >= 1)
    if not gecerli.any():
        raise ValueError("stop mesafesi hiçbir işlemde hesaplanamadı")
    m = np.where(gecerli, m, np.median(m[gecerli]))
    return pd.DataFrame({"yon": oos["yon"].to_numpy(int), "h": h, "stop_atr": m})


def uygun_giris_mumlari(mumlar: pd.DataFrame, secimler: list, atr: np.ndarray) -> np.ndarray:
    """Stratejinin gerçekten aday seçtiği test pencerelerindeki, ATR'si hazır mumların indeksleri (giriş mumu j)."""
    idx = mumlar.index
    maske = np.zeros(len(idx), dtype=bool)
    for s in secimler:
        if s.get("secilen") is None:
            continue
        maske |= (idx >= pd.Timestamp(s["test_bas"])) & (idx < pd.Timestamp(s["test_bit"]))
    j = np.nonzero(maske)[0]
    return j[(j >= 1) & np.isfinite(atr[np.maximum(j - 1, 0)])]


def _tek_islem_r(o, h, l, c, atr, j, yon, hm, mult, kayma, stop_kayma, taker):
    """Tek rastgele işlem R'si; stop geçersizse None. Ayrıntı için modül başı yöntem 2."""
    giris = o[j] * (1 + yon * kayma)
    stop = c[j - 1] - yon * mult * atr[j - 1]
    risk = (giris - stop) * yon
    if not risk > 0:
        return None
    son = j + hm
    if yon == 1:
        vur = l[j:son] <= stop
    else:
        vur = h[j:son] >= stop
    if vur.any():
        b = int(np.argmax(vur))
        gap = o[j + b] <= stop if yon == 1 else o[j + b] >= stop
        ham = o[j + b] if gap else stop
        cikis = ham * (1 - yon * stop_kayma)
    else:
        cikis = o[son] * (1 - yon * kayma)
    net = yon * (cikis - giris) - taker * (giris + cikis)
    return net / risk


def rastgele_giris(mumlar: pd.DataFrame, tanim: pd.DataFrame, uygun: np.ndarray, ayar, n_sim: int = N_SIM,
                   seed: int = 0, atr_periyot: int = ATR_PERIYOT) -> dict:
    """-> {toplam_r: dizi(n_sim), n_gecersiz: int, n_islem: int}. `ayar`: MotorAyarlari (maliyetler motorunkiyle aynı)."""
    rng = np.random.default_rng(seed)
    o, h = mumlar["acilis"].to_numpy(float), mumlar["yuksek"].to_numpy(float)
    l, c = mumlar["dusuk"].to_numpy(float), mumlar["kapanis"].to_numpy(float)
    atr = gst.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], atr_periyot).to_numpy(float)
    n = len(mumlar)
    kayma, skayma = ayar.kayma_bps / 1e4, ayar.stop_kayma_bps / 1e4
    taker = ayar.komisyon_taker_yuzde / 100
    uygun = np.sort(uygun)
    yon, hm, mult = tanim["yon"].to_numpy(int), tanim["h"].to_numpy(int), tanim["stop_atr"].to_numpy(float)
    m = len(tanim)
    # her işlem için j + H <= n-1 olan uygun mumların önek uzunluğu
    kullan = np.searchsorted(uygun, n - 1 - hm, side="right")
    if (kullan == 0).any():
        raise ValueError("uygun giriş mumu yok (pencere/tutma süresi)")
    toplam = np.zeros(n_sim)
    gecersiz = 0
    u = rng.random((n_sim, m, YENIDEN_CEKIM))
    for s in range(n_sim):
        top = 0.0
        for k in range(m):
            for d in range(YENIDEN_CEKIM):
                j = int(uygun[int(u[s, k, d] * kullan[k])])
                r = _tek_islem_r(o, h, l, c, atr, j, int(yon[k]), int(hm[k]), float(mult[k]), kayma, skayma, taker)
                if r is not None:
                    top += r
                    break
            else:
                gecersiz += 1
        toplam[s] = top
    return {"toplam_r": toplam, "n_gecersiz": gecersiz, "n_islem": m * n_sim}


def rastgele_p(gercek_toplam_r: float, sim_toplam_r) -> tuple:
    """(p, yüzdelik): p = (1 + #{sim >= gerçek}) / (N+1) tek taraflı; yüzdelik = sim'in gerçeğin altında kalan oranı."""
    s = np.asarray(sim_toplam_r, dtype=float)
    return float((1 + (s >= gercek_toplam_r).sum()) / (len(s) + 1)), float((s < gercek_toplam_r).mean())


# ---------------------------------------------------------------------------- parametre duyarlılığı
def komsu_parametreler(par: dict, izgara: dict) -> list:
    """[(parametre, yon, yeni_deger)] — yöntem 4. Sayısal (bool olmayan) parametreler; ızgarada ±1 adım,
    ızgarada yoksa ±%20 (int ise yuvarlanır; 0 ve değişmeyen kopyalar atlanır)."""
    cikti = []
    for ad, v in par.items():
        if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)):
            continue
        degerler = sorted({x for x in (izgara.get(ad) or []) if isinstance(x, (int, float, np.integer, np.floating))
                           and not isinstance(x, bool)})
        if v in degerler:
            i = degerler.index(v)
            if i > 0:
                cikti.append((ad, -1, degerler[i - 1]))
            if i < len(degerler) - 1:
                cikti.append((ad, 1, degerler[i + 1]))
            continue
        if v == 0:
            continue
        for yon, c in ((-1, 0.8), (1, 1.2)):
            y = v * c
            if isinstance(v, (int, np.integer)):
                y = int(round(y))
                if y == v:
                    continue
            cikti.append((ad, yon, y))
    return cikti


def ayar_coz(ad: str, etiket: str):
    """wf_tarama ayar etiketinden ('varsayilan' | 'kart:<id>' | 'dis:<id>' | 'izgara:<json>') strateji nesnesi."""
    tur, _, arg = etiket.partition(":")
    if tur == "izgara":
        return tarama._strateji_kur(ad, "izgara", json.loads(arg))
    if tur == "varsayilan":
        return tarama._strateji_kur(ad, "varsayilan", None)
    return tarama._strateji_kur(ad, tur, arg)


# ---------------------------------------------------------------------------- rejim
def gunluk_rejim(mumlar: pd.DataFrame) -> pd.Series:
    """Gün (UTC) -> 'boga'|'ayi'|'yatay'|'belirsiz'; değer o günün BAŞINDA bilinen (önceki tamamlanmış gün) bilgidir."""
    kap = mumlar["kapanis"].resample("1D").last().dropna()
    sma = kap.rolling(200).mean()
    egim = sma / sma.shift(20) - 1.0
    rej = pd.Series("yatay", index=kap.index, dtype=object)
    rej[(kap > sma) & (egim > 0)] = "boga"
    rej[(kap < sma) & (egim < 0)] = "ayi"
    rej[egim.isna()] = "belirsiz"
    return rej.shift(1).fillna("belirsiz")


def rejim_etiketle(rejim: pd.Series, giris_zamanlari) -> np.ndarray:
    gun = pd.DatetimeIndex(giris_zamanlari).floor("D")
    # giriş gününe en yakın önceki (dahil) gün kaydı; shift(1) sayesinde o günün değeri nedenseldir
    pos = rejim.index.searchsorted(gun, side="right") - 1
    v = rejim.to_numpy(dtype=object)
    return np.where(pos >= 0, v[np.maximum(pos, 0)], "belirsiz")


# ---------------------------------------------------------------------------- görev
_S: dict = {}


def oneri(satir: dict) -> tuple:
    """-> (saglam_mi: bool, basarisiz kapılar: str). Kural modül başında; NaN = geçmez."""
    def gec(v, ok):
        return v is not None and not (isinstance(v, float) and math.isnan(v)) and ok(v)
    k = {"K1_maliyet2_pf": gec(satir.get("m2_pf"), lambda v: v >= KAPI_M2_PF),
         "K2_rastgele_p": gec(satir.get("rnd_p"), lambda v: v <= KAPI_RASTGELE_P),
         "K3_boot_alt": gec(satir.get("pf_boot_alt"), lambda v: v > KAPI_BOOT_ALT),
         "K4_komsu_param": gec(satir.get("par_oran"), lambda v: v >= KAPI_KOMSU_ORAN)}
    kaybeden = [a for a, ok in k.items() if not ok]
    return (not kaybeden), ";".join(kaybeden)


def _isci_baslat(ayar: dict):
    _S.clear()
    _S.update(ayar)
    wf_tarama._isci_baslat(ayar["wf_ayar"])


def gorev_calistir(g: dict) -> dict:
    t0 = time.perf_counter()
    satir = {"strateji": g["strateji"], "stil": g["stil"], "sembol": g["sembol"], "tf": g["tf"], "hata": ""}
    try:
        _icerik(g, satir)
    except Exception as e:  # noqa: BLE001  (satıra yazılır; saglam_mi False olur, koşu durmaz)
        satir["hata"] = f"{type(e).__name__}: {e}"
    satir["saglam_mi"], satir["kapi_basarisiz"] = oneri(satir) if satir["hata"] == "" else (False, "hata")
    satir["sure_sn"] = time.perf_counter() - t0
    return satir


def _icerik(g: dict, satir: dict):
    S = _S
    ad, sembol, tf = g["strateji"], g["sembol"], g["tf"]
    oos_bas, oos_bit = pd.Timestamp(g["oos_bas"]), pd.Timestamp(g["oos_bit"])
    satir.update({"n_aday": int(g["n_aday"]), "en_sik_ayar": g["en_sik_ayar"], "wf_islem": int(g["islem_sayisi"]),
                  "wf_pf": float(g["profit_factor"]), "wf_net": float(g["net_getiri"]),
                  "wf_toplam_r": float(g["toplam_r"])})
    oos = pd.read_parquet(wf_tarama.islem_yolu(S["wf_dizini"], S["wf_etiket"], ad, sembol, tf))
    oos = oos.sort_values("cikis_zamani", kind="stable").reset_index(drop=True)
    if len(oos) != satir["wf_islem"]:
        raise RuntimeError(f"işlem dosyası ({len(oos)}) ile WF özeti ({satir['wf_islem']}) uyuşmuyor")
    if abs(wf_tarama.pf_hesapla(oos["r"]) - satir["wf_pf"]) > 1e-6:
        raise RuntimeError("işlem dosyasından PF, WF özetiyle uyuşmuyor")
    mumlar, fund = wf_tarama._veri(sembol, tf)
    kurallar = tarama.SEMBOL_KURALLARI.get(sembol, tarama.VARSAYILAN_KURAL)
    ay1 = wf_tarama.maliyet_ayarlari(kurallar, 1.0)
    rng_tohum = zlib.crc32(f"{ad}|{sembol}|{tf}".encode()) ^ S["tohum"]

    # 1) maliyet x2 — aynı walk-forward (aday kümesi, pencere, skor) iki katı maliyetle
    m2 = _m2_calistir(g)
    satir.update({"m2_islem": m2.get("islem_sayisi", 0), "m2_pf": m2.get("profit_factor", math.nan),
                  "m2_net": m2.get("net_getiri", math.nan), "m2_hata": m2.get("hata", "")})
    if m2.get("hata"):
        raise RuntimeError(f"maliyet x2 walk-forward hatası: {m2['hata']}")

    # 2) rastgele giriş
    secimler = json.loads(g["secimler"])
    atr = gst.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], ATR_PERIYOT).to_numpy(float)
    tanim = islem_tanimlari(mumlar, oos, atr)
    uygun = uygun_giris_mumlari(mumlar, secimler, atr)
    rs = rastgele_giris(mumlar, tanim, uygun, ay1, S["n_sim"], seed=rng_tohum)
    p, yuz = rastgele_p(satir["wf_toplam_r"], rs["toplam_r"])
    satir.update({"rnd_n_sim": S["n_sim"], "rnd_p": p, "rnd_yuzdelik": yuz,
                  "rnd_ort_r": float(rs["toplam_r"].mean()), "rnd_std_r": float(rs["toplam_r"].std(ddof=1)),
                  "rnd_p95_r": float(np.percentile(rs["toplam_r"], 95)),
                  "rnd_gecersiz": rs["n_gecersiz"] / rs["n_islem"], "rnd_uygun_mum": int(len(uygun))})

    # 3) DSR + bootstrap
    gg = gunluk_getiri(oos, oos_bas, oos_bit)
    for ad_, n in (("aday", g["n_aday"]), ("evren", S["n_evren"]), ("kosu", S["n_kosu"])):
        d = deflated_sharpe(gg, n, S["sr_varyans"])
        satir[f"dsr_{ad_}"] = d["dsr"]
        satir[f"sr0_{ad_}_yillik"] = d["sr0"] * math.sqrt(365)
    satir.update({"sr_yillik": d["sr"] * math.sqrt(365), "gun_sayisi": d["T"], "carpiklik": d["carpiklik"],
                  "basiklik": d["basiklik"], "dsr_n_aday": int(g["n_aday"]), "dsr_n_evren": S["n_evren"],
                  "dsr_n_kosu": S["n_kosu"], "sr_varyans": S["sr_varyans"]})
    lo, hi, med = pf_boot(oos["r"].to_numpy(float), BLOK, N_BOOT, np.random.default_rng(rng_tohum + 1))
    satir.update({"pf_boot_alt": lo, "pf_boot_ust": hi, "pf_boot_medyan": med})

    # 4) parametre duyarlılığı (sabit ayar, tüm OOS dönemi)
    satir.update(_parametre_duyarlilik(ad, g["en_sik_ayar"], mumlar, fund, ay1, oos_bas, oos_bit))

    # 5) rejim
    rej = rejim_etiketle(gunluk_rejim(mumlar), oos["giris_zamani"])
    rpf = 0
    for kod in ("boga", "ayi", "yatay", "belirsiz"):
        x = oos.loc[rej == kod, "r"].to_numpy(float)
        satir[f"rejim_{kod}_n"] = int(len(x))
        if kod != "belirsiz":
            pf = wf_tarama.pf_hesapla(x) if len(x) else math.nan
            satir[f"rejim_{kod}_pf"] = pf
            rpf += int(pf > 1) if not math.isnan(pf) else 0
    satir["rejim_pf_gt1_sayi"] = rpf
    satir["yil_detay"] = " ".join(f"{y}:{g[f'pf_{y}']:.2f}({int(g[f'n_{y}'])})" for y in wf_tarama.YILLAR
                                  if g.get(f"n_{y}", 0) and g[f"n_{y}"] > 0 and not pd.isna(g[f"pf_{y}"]))

    # 6) komşu sembol/TF
    satir.update(_komsu_gorevler(g, S["wf_tablo"]))


def _m2_calistir(g: dict) -> dict:
    """wf_tarama._AYAR'ı geçici olarak maliyet x2 + ayrı çıktı dizini ile kurup aynı görevi koşar."""
    eski = dict(wf_tarama._AYAR)
    try:
        wf_tarama._AYAR.update(maliyet_carpani=2.0, cikti_dizini=_S["cikti_dizini"] / "m2_islemler",
                               etiket=_S["wf_etiket"])
        return wf_tarama.gorev_calistir({k: g[k] for k in ("strateji", "stil", "sembol", "tf")})
    finally:
        wf_tarama._AYAR.clear()
        wf_tarama._AYAR.update(eski)


def _parametre_duyarlilik(ad, en_sik_ayar, mumlar, fund, ayar, oos_bas, oos_bit) -> dict:
    s0 = ayar_coz(ad, en_sik_ayar)
    izgara = s0.parametre_izgarasi or {}
    komsular = komsu_parametreler(s0.parametreler, izgara)

    def sabit_pf(s):
        r = backtest(mumlar, s, ayar, fund).islemler
        if not len(r):                  # işlemsiz ayar: boş sütun naive dtype olur, Timestamp (UTC) ile kıyaslanamaz
            return math.nan, 0
        gz = pd.DatetimeIndex(r["giris_zamani"])
        r = r[(gz >= oos_bas) & (gz < oos_bit)]
        return wf_tarama.pf_hesapla(r["r"].to_numpy(float)) if len(r) else math.nan, len(r)

    merkez, merkez_n = sabit_pf(s0)
    pfler, detay, hatalar = [], [], []
    for p, yon, v in komsular:
        try:
            pf, n = sabit_pf(s0.yeni(**{p: v}))
        except ValueError as e:         # geçersiz kombinasyon (ör. hızlı >= yavaş) / çıkış yok: sayılır, raporlanır
            hatalar.append(f"{p}={v}: {type(e).__name__}: {e}"[:100])
            continue
        detay.append(f"{p}{'+' if yon > 0 else '-'}={v}:{pf:.2f}({n})")
        pfler.append(pf)
    a = np.array(pfler, dtype=float)
    iyi = int((a > 1).sum()) if len(a) else 0                # NaN (işlemsiz komşu) > 1 değildir
    return {"par_merkez_pf": merkez, "par_merkez_islem": merkez_n, "par_n_komsu": len(komsular),
            "par_n_gecerli": len(pfler), "par_n_pf_gt1": iyi,
            "par_oran": iyi / len(pfler) if pfler else math.nan,
            "par_min_pf": float(np.nanmin(a)) if len(a) and not np.all(np.isnan(a)) else math.nan,
            "par_medyan_pf": float(np.nanmedian(a)) if len(a) and not np.all(np.isnan(a)) else math.nan,
            "par_hata": len(hatalar), "par_hata_ornek": hatalar[0] if hatalar else "",
            "par_detay": " | ".join(detay)}


def _komsu_gorevler(g: dict, tablo: pd.DataFrame) -> dict:
    d = tablo[(tablo["strateji"] == g["strateji"]) & (tablo["hata"] == "")
              & ~((tablo["sembol"] == g["sembol"]) & (tablo["tf"] == g["tf"]))]
    pf = pd.to_numeric(d["profit_factor"], errors="coerce")
    isl = pd.to_numeric(d["islem_sayisi"], errors="coerce").fillna(0)
    iyi = (pf > 1) & (isl > 0)
    return {"komsu_n": int(len(d)), "komsu_pf_gt1": int(iyi.sum()), "komsu_gecti": int(d["gecti"].sum()),
            "komsu_medyan_pf": float(pf[isl > 0].median()) if (isl > 0).any() else math.nan,
            "komsu_detay": " ".join(f"{s}/{t}:{('%.2f' % p) if not pd.isna(p) else '-'}({int(n)})"
                                    for s, t, p, n in zip(d["sembol"], d["tf"], pf, isl))}


# ---------------------------------------------------------------------------- ana akış
def deneme_sayilari(wf_tablo: pd.DataFrame, yol=None) -> tuple:
    """(n_evren, n_kosu): deneme_kaydi.jsonl'daki walk-forward girdileri (pencere_sayisi > 0) üzerinden benzersiz
    görev sayısı ve toplam backtest koşusu. Kayıt yoksa WF tablosundaki hatasız görev/koşu sayısı."""
    kayitlar = [k for k in deneme_kaydi.oku(yol) if k.get("pencere_sayisi", 0) > 0]
    if kayitlar:
        gorev = {(k["strateji"], k["sembol"], k["aralik"]) for k in kayitlar}
        return len(gorev), sum(k["toplam_kosu"] for k in kayitlar)
    ok = wf_tablo[wf_tablo["hata"] == ""]
    return len(ok), int(ok["n_kosu"].sum())


def sr_varyansi(wf_tablo: pd.DataFrame) -> float:
    """İşlem yapan tüm WF görevlerinin günlük Sharpe'ının (yıllık sharpe / sqrt(365)) varyansı."""
    s = pd.to_numeric(wf_tablo["sharpe"], errors="coerce").dropna() / math.sqrt(365)
    return float(s.var(ddof=1)) if len(s) > 1 else math.nan


def saglamlik_tara(wf_etiket: str, etiket: Optional[str] = None, surec: int = 4, n_sim: int = N_SIM,
                   wf_dizini: Optional[Path] = None, cikti_dizini: Optional[Path] = None, veri_dizini=None,
                   baslangic=None, bitis=None, tohum: int = 0, ilerleme: bool = True,
                   deneme_kaydi_yolu=None, hatalari_yeniden: bool = False) -> pd.DataFrame:
    if n_sim < 200:
        raise ValueError("n_sim >= 200 olmalı")
    etiket = etiket or wf_etiket
    wf_dizini = Path(wf_dizini) if wf_dizini is not None else wf_tarama.CIKTI_DIZINI
    cikti_dizini = Path(cikti_dizini) if cikti_dizini is not None else CIKTI_DIZINI
    cikti_dizini.mkdir(parents=True, exist_ok=True)
    tablo = pd.read_parquet(wf_dizini / f"{wf_etiket}.parquet")
    aday = tablo[(tablo["gecti"]) & (tablo["hata"] == "")].copy()
    n_evren, n_kosu = deneme_sayilari(tablo, deneme_kaydi_yolu)
    yol_pq = cikti_dizini / f"{etiket}.parquet"
    onceki = pd.read_parquet(yol_pq) if yol_pq.exists() else pd.DataFrame()
    if hatalari_yeniden and len(onceki):      # hatalı satırlar atılır, yeniden koşulur; sağlıklı satırlara dokunulmaz
        onceki = onceki[onceki["hata"].fillna("") == ""].reset_index(drop=True)
    bitmis = set(zip(onceki["strateji"], onceki["sembol"], onceki["tf"])) if len(onceki) else set()
    gorevler = [r for r in aday.to_dict("records") if (r["strateji"], r["sembol"], r["tf"]) not in bitmis]
    gorevler.sort(key=lambda g: (g["sembol"], g["tf"]))
    if ilerleme:
        print(f"[sag] {etiket}: geçen {len(aday)}, bitmiş {len(aday) - len(gorevler)}, kalan {len(gorevler)}; "
              f"N_evren={n_evren} N_kosu={n_kosu}", flush=True)
    wf_ayar = {"veri_dizini": veri_dizini, "baslangic": baslangic, "bitis": bitis, "izgara": True,
               "pencere_gun": wf_tarama.PENCERE_GUN, "min_islem": wf_tarama.MIN_ISLEM,
               "cikti_dizini": cikti_dizini, "etiket": wf_etiket, "maliyet_carpani": 1.0}
    ayar = {"wf_ayar": wf_ayar, "wf_dizini": wf_dizini, "wf_etiket": wf_etiket, "cikti_dizini": cikti_dizini,
            "n_sim": n_sim, "tohum": tohum, "n_evren": n_evren, "n_kosu": n_kosu,
            "sr_varyans": sr_varyansi(tablo), "wf_tablo": tablo}
    yeni = []
    t0 = time.perf_counter()

    def ekle(satir):
        yeni.append(satir)
        wf_tarama._yaz(pd.concat([onceki, pd.DataFrame(yeni)], ignore_index=True), yol_pq)
        if ilerleme:
            print(f"[sag] {len(yeni)}/{len(gorevler)}  {satir['strateji']} {satir['sembol']} {satir['tf']}  "
                  f"saglam={satir['saglam_mi']}  {satir.get('hata', '')[:80]}  ({time.perf_counter() - t0:.0f} sn)",
                  flush=True)

    if gorevler:
        if surec <= 1:
            _isci_baslat(ayar)
            for g in gorevler:
                ekle(gorev_calistir(g))
        else:
            with mp.get_context("fork").Pool(surec, _isci_baslat, (ayar,)) as havuz:
                for satir in havuz.imap_unordered(gorev_calistir, gorevler, chunksize=1):
                    ekle(satir)
    sonuc = pd.read_parquet(yol_pq) if yol_pq.exists() else pd.DataFrame()
    if len(sonuc):
        sonuc.to_csv(cikti_dizini / f"{etiket}.csv", index=False)
    if ilerleme:
        print(f"[sag] bitti: {len(yeni)} yeni görev, {time.perf_counter() - t0:.1f} sn -> {yol_pq}", flush=True)
    return sonuc


def main(argv=None):
    ap = argparse.ArgumentParser(description="Sağlamlık analizi (Aşama 2 Katman 3b)")
    ap.add_argument("--wf-etiket", required=True)
    ap.add_argument("--etiket", default=None, help="çıktı etiketi (varsayılan: wf etiketi)")
    ap.add_argument("--surec", type=int, default=4)
    ap.add_argument("--hatalari-yeniden", action="store_true", help="hata satırlarını sil ve yeniden koş")
    ap.add_argument("--n-sim", type=int, default=N_SIM)
    a = ap.parse_args(argv)
    s = saglamlik_tara(a.wf_etiket, a.etiket, a.surec, a.n_sim, hatalari_yeniden=a.hatalari_yeniden)
    if len(s):
        print(f"sağlam önerilen: {int(s['saglam_mi'].sum())}/{len(s)}  hatalı: {int((s['hata'] != '').sum())}")


if __name__ == "__main__":
    main()
