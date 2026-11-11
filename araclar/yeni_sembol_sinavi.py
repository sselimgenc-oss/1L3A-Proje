"""Yeni sembol sınavı — ON_KAYIT_YENI_SEMBOL.md'nin birebir uygulaması (KEŞİF testi; canlı planı değiştirmez).

Canlıya gidecek 4 strateji (dis__e0v1en, dis__ewo-ema-ofset 15m; dis__hma-atr-rider, dis__lube 1d), VARSAYILAN ayarlarıyla,
hiç görmedikleri Binance USDⓈ-M perpetual paritelerinde koşulur. Izgara/optimizasyon YOK. Tüm kurallar aşağıda sabit ve ön
kayıtlıdır; koşudan sonra değişmez. Okunan en büyük tarih 2026-10-31 23:59 UTC'yi aşarsa betik DURUR (sert doğrulama;
sessiz try/except yok). Tek koşu.

Alt komutlar:
  liste  : arşivden (data.binance.vision) S anındaki adayları süzer -> semboller.csv + adaylar_tum.csv   (koşudan ÖNCE, bir kez)
  kos    : kilitli semboller.csv + eski evren ile tek koşu -> islemler/, sonuc_strateji.csv, sonuc_sembol.csv, ozet.json
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

CIKTI = KOK / "sonuclar" / "evren" / "yeni_sembol"

# ============================================================================ ön kayıtlı sabitler (ON_KAYIT_YENI_SEMBOL.md)
SECIM_TARIHI = pd.Timestamp("2023-11-01", tz="UTC")           # S
OLCUM_BAS = SECIM_TARIHI                                      # ölçüm dönemi başı (bu andan önce AÇILAN işlem sayılmaz)
OLCUM_BIT_SINIR = pd.Timestamp("2026-11-01", tz="UTC")        # HARİÇ sınır = 2026-10-31 23:59:59 UTC'nin hemen sonrası
EN_BUYUK_MUM_ACILISI = pd.Timestamp("2026-10-31 23:59", tz="UTC")   # sert doğrulama: okunan en büyük zaman <= bu
OKUMA_BAS = pd.Timestamp("2021-11-01", tz="UTC")              # ısınma: S - 730 gün; iki evren için aynı
MIN_GECMIS_GUN = 730
HACIM_PENCERE_GUN = 30
ILK_N = 40
BOOT_N = 10000
BOOT_TOHUM = 20261111
GA_DUZEY = 0.90
EN_IYI_CIKAR = 3
GENEL_ESIK_SEMBOL_PAY = 0.50
DELIST_TOLERANS_GUN = 7        # son mum, arşivdeki en yeni mumdan bu kadar gün eskiyse "delist"

STRATEJILER = {"dis__e0v1en": "15m", "dis__ewo-ema-ofset": "15m", "dis__hma-atr-rider": "1d", "dis__lube": "1d"}
ESKI_EVREN = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "LINKUSDT", "BCHUSDT",
              "TRXUSDT", "XLMUSDT")
CARPANLAR = (1.0, 2.0)
ANA_CARPAN = 2.0

# Hariç tutma (taban adı: "USDT" soneki ve 1000/1000000/1M öneki atılmış)
HARIC_TABAN = frozenset({"ADA", "BCH", "BNB", "BTC", "DOGE", "ETH", "HYPE", "LINK", "SOL", "TRX", "XLM", "XRP", "ZEC",
                         "XAU", "NVDA", "TSLA"})
STABLE_TABAN = frozenset({"USDC", "BUSD", "TUSD", "FDUSD", "DAI", "USDP", "USDD", "UST", "USTC", "EUR", "AEUR", "EURS",
                          "GUSD", "PAX", "SUSD", "USDE", "USD1", "RLUSD", "USDS", "PYUSD", "FRAX", "LUSD"})
ENDEKS_TABAN = frozenset({"DEFI", "BTCDOM", "FOOTBALL", "BLUEBIRD", "ALL", "ALT", "ALTCOIN", "ETHDOM"})

KILIT_GEREKCE = "yeni sembol sınavı: KEŞİF testi, ölçüm dönemi 2023-11-01→2026-10-31 (ON_KAYIT_YENI_SEMBOL; canlı planı değiştirmez)"
os.environ.setdefault("L3A_KILIT_LOG", str(CIKTI / "kilit_acilis.jsonl"))   # açılışlar bu çalışmanın kendi günlüğüne


class TarihSiniriIhlali(RuntimeError):
    """Okunan/üretilen veri ölçüm dönemi sınırını (2026-10-31 23:59 UTC) aştı. ASLA yutulmaz."""


# ============================================================================ saf yardımcılar (testli)
def utc(x) -> pd.Timestamp:
    t = pd.Timestamp(x)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def tarih_siniri_dogrula(zamanlar, ad: str) -> pd.Timestamp | None:
    """Zaman indeksi ölçüm sınırını aşarsa TarihSiniriIhlali. En büyük zamanı döndürür (boşsa None)."""
    idx = pd.DatetimeIndex(zamanlar)
    if not len(idx):
        return None
    mx = utc(idx.max())
    if mx > EN_BUYUK_MUM_ACILISI:
        raise TarihSiniriIhlali(f"{ad}: en büyük zaman {mx} > {EN_BUYUK_MUM_ACILISI}")
    return mx


def taban_ad(sembol: str) -> str:
    """'1000SHIBUSDT' -> 'SHIB'; 'BTCUSDT' -> 'BTC' (USDT soneki ve 1000000/1000/1M öneki atılır)."""
    t = sembol[:-4] if sembol.endswith("USDT") else sembol
    for onek in ("1000000", "1000", "1M"):
        if t.startswith(onek) and len(t) > len(onek):
            return t[len(onek):]
    return t


def usdt_surekli_mi(sembol: str) -> bool:
    """Quote USDT, USDⓈ-M PERPETUAL: 'XUSDT' biçimi. Teslimli ('BTCUSDT_250328'), SETTLED kopyaları ve USDT dışı quote değil."""
    return bool(re.fullmatch(r"[A-Z0-9]+USDT", sembol)) and not sembol.endswith("SETTLEDUSDT") and "SETTLED" not in sembol


def kural_turet(medyan_fiyat: float) -> tuple:
    """Tick/step TÜRETİMİ (exchangeInfo erişilemiyor; VARSAYIM, yalnız adet/fiyat yuvarlaması): tick = 10^(floor(log10 p)-4),
    step = 10^floor(log10(1/p)) (1 adımın değeri ~0.1–1 USD)."""
    if not (medyan_fiyat > 0 and math.isfinite(medyan_fiyat)):
        raise ValueError(f"geçersiz medyan fiyat: {medyan_fiyat}")
    tick = 10.0 ** (math.floor(math.log10(medyan_fiyat)) - 4)
    step = 10.0 ** math.floor(math.log10(1.0 / medyan_fiyat))
    return float(f"{tick:.12g}"), float(f"{step:.12g}")


def aday_sec(bilgi: pd.DataFrame, secim=SECIM_TARIHI, ilk_n: int = ILK_N, min_gecmis_gun: int = MIN_GECMIS_GUN) -> pd.DataFrame:
    """Ön kayıtlı seçim kuralı. Girdi sütunları: sembol, ilk_mum, son_mum, hacim_30g (+ istenirse diğerleri).
    Çıktı: girdi + 'neden' (boş = elenmedi) + 'sira' (ilk_n içinde 1..n, değilse 0). Sıra kuralı:
      1 usdt_surekli_degil | 2 gecmis<730g (ilk mum > S-730g) | 3 S'de islem yok (son mum < S ya da S öncesi 30g hacim yok)
      4 haric/stable/endeks (taban adına göre) | 5 ikinci_kontrat (aynı taban adında hacmi yüksek olan kalır) | 6 ilk_n dışı.
    Sıralama: 30g quote hacmi azalan (eşitlikte sembol adı artan)."""
    d = bilgi.copy().reset_index(drop=True)
    for c in ("ilk_mum", "son_mum"):
        d[c] = pd.to_datetime(d[c], utc=True)
    secim = utc(secim)
    esik_ilk = secim - pd.Timedelta(days=min_gecmis_gun)
    neden = pd.Series("", index=d.index, dtype=object)
    taban = d["sembol"].map(taban_ad)

    def isaretle(maske, ad):
        m = maske & (neden == "")
        neden[m] = ad
    isaretle(~d["sembol"].map(usdt_surekli_mi), "usdt_surekli_degil")
    isaretle(d["ilk_mum"] > esik_ilk, "gecmis_730g_yok")
    isaretle((d["son_mum"] < secim) | ~(d["hacim_30g"] > 0), "S_de_islem_yok")
    isaretle(taban.isin(HARIC_TABAN), "haric_liste")
    isaretle(taban.isin(STABLE_TABAN), "stablecoin")
    isaretle(taban.isin(ENDEKS_TABAN), "endeks_kontrat")
    kal = d[neden == ""].assign(_taban=taban[neden == ""])
    kal = kal.sort_values(["hacim_30g", "sembol"], ascending=[False, True], kind="mergesort")
    ilk = kal.drop_duplicates("_taban", keep="first").index
    ikinci = kal.index.difference(ilk)
    neden[ikinci] = "ikinci_kontrat"
    kal2 = d.loc[ilk].sort_values(["hacim_30g", "sembol"], ascending=[False, True], kind="mergesort")
    sira = pd.Series(0, index=d.index, dtype=int)
    for i, ix in enumerate(kal2.index[:ilk_n], 1):
        sira[ix] = i
    neden[kal2.index[ilk_n:]] = "ilk_n_disi"
    d["neden"] = neden
    d["sira"] = sira
    return d


# ---- ölçüler
def r_olculeri(r) -> dict:
    """Bir R dizisi için: n, ΣR, ortalama R, PF, kazanma oranı, ort. kazanç, ort. kayıp (mutlak), kazanç/kayıp."""
    r = np.asarray(r, dtype=float)
    n = int(len(r))
    if n == 0:
        return {"n": 0, "sum_r": 0.0, "ort_r": float("nan"), "pf": float("nan"), "kazanma": float("nan"),
                "ort_kazanc": float("nan"), "ort_kayip": float("nan"), "kazanc_kayip": float("nan")}
    kaz, kay = r[r > 0], r[r < 0]
    brut_kaz, brut_kay = float(kaz.sum()), float(-kay.sum())
    ort_kaz = float(kaz.mean()) if len(kaz) else float("nan")
    ort_kay = float(-kay.mean()) if len(kay) else float("nan")
    return {"n": n, "sum_r": float(r.sum()), "ort_r": float(r.mean()),
            "pf": (brut_kaz / brut_kay) if brut_kay > 0 else (float("inf") if brut_kaz > 0 else float("nan")),
            "kazanma": float(len(kaz) / n), "ort_kazanc": ort_kaz, "ort_kayip": ort_kay,
            "kazanc_kayip": (ort_kaz / ort_kay) if (len(kaz) and len(kay)) else float("nan")}


def bootstrap_ga(sembol_toplam, sembol_n, n_boot: int = BOOT_N, tohum: int = BOOT_TOHUM, ga: float = GA_DUZEY) -> dict:
    """Sembol düzeyinde bootstrap: semboller yeniden örneklenir (iadeli), işlemleri birlikte taşınır; her çekilişte
    ortalama R = örneklenen sembollerin ΣR toplamı / işlem sayısı toplamı. Çekilişte hiç işlem yoksa o çekiliş atılır (sayılır).
    Yüzdelik GA: ((1-ga)/2, (1+ga)/2). Tohumlu numpy Generator(PCG64) -> tekrarlanabilir."""
    s = np.asarray(sembol_toplam, dtype=float)
    n = np.asarray(sembol_n, dtype=float)
    k = len(s)
    if k == 0 or n.sum() == 0:
        return {"alt": float("nan"), "ust": float("nan"), "n_gecerli": 0, "n_atilan": n_boot}
    rng = np.random.default_rng(tohum)
    idx = rng.integers(0, k, size=(n_boot, k))
    pay, payda = s[idx].sum(axis=1), n[idx].sum(axis=1)
    gecerli = payda > 0
    ort = pay[gecerli] / payda[gecerli]
    alt, ust = np.percentile(ort, [100 * (1 - ga) / 2, 100 * (1 + ga) / 2])
    return {"alt": float(alt), "ust": float(ust), "n_gecerli": int(gecerli.sum()), "n_atilan": int((~gecerli).sum())}


def en_iyi_k_cikar(sembol_toplam: dict, k: int = EN_IYI_CIKAR) -> tuple:
    """ΣR'ye göre en iyi k sembol çıkarılınca kalan ΣR. (kalan toplam, çıkarılan sembol listesi). Eşitlikte sembol adı artan."""
    sirali = sorted(sembol_toplam.items(), key=lambda kv: (-kv[1], kv[0]))
    cikan = [a for a, _ in sirali[:k]]
    return float(sum(v for a, v in sirali[k:])), cikan


def evren_olculeri(islem_x1: dict, islem_x2: dict, semboller) -> dict:
    """Bir (evren, strateji) için ön kayıtlı ölçülerin tümü. islem_xN: {sembol: R dizisi}; semboller: evrendeki TÜM semboller
    (işlemi olmayanlar dahil; 'ΣR>0 sembol yüzdesi' paydası = bu liste)."""
    semboller = list(semboller)
    out = {"n_sembol": len(semboller)}
    for ad, islem in (("x1", islem_x1), ("x2", islem_x2)):
        tum = np.concatenate([np.asarray(islem.get(s, []), dtype=float) for s in semboller]) if semboller else np.array([])
        for kx, v in r_olculeri(tum).items():
            out[f"{kx}_{ad}"] = v
    toplam2 = {s: float(np.sum(np.asarray(islem_x2.get(s, []), dtype=float))) for s in semboller}
    n2 = {s: int(len(islem_x2.get(s, []))) for s in semboller}
    out["n_sembol_islemli_x2"] = int(sum(1 for v in n2.values() if v > 0))
    out["pozitif_sembol_pct_x2"] = float(100.0 * sum(1 for v in toplam2.values() if v > 0) / len(semboller)) if semboller else float("nan")
    out["sembol_medyan_sumr_x2"] = float(np.median(list(toplam2.values()))) if semboller else float("nan")
    ga = bootstrap_ga([toplam2[s] for s in semboller], [n2[s] for s in semboller])
    out["boot_ga_alt_x2"], out["boot_ga_ust_x2"] = ga["alt"], ga["ust"]
    out["boot_gecerli"], out["boot_atilan"] = ga["n_gecerli"], ga["n_atilan"]
    kalan, cikan = en_iyi_k_cikar(toplam2)
    out["en_iyi3_cikinca_sumr_x2"] = kalan
    out["en_iyi3_semboller"] = ",".join(cikan)
    return out


def yorum_etiketi(o: dict) -> str:
    """Yalnız yeni evren, ×2. GENELLEŞİYOR: GA alt > 0 VE sembollerin >= %50'si artı VE en iyi 3 çıkınca ΣR > 0.
    GENELLEŞMİYOR: ortalama R <= 0. Aksi (ortalama R > 0 ama bir koşul tutmuyor): ZAYIF / BELİRSİZ."""
    ort = o["ort_r_x2"]
    if not (ort > 0):                 # NaN (işlem yok) da genellemiyor sayılır
        return "GENELLEŞMİYOR"
    if (o["boot_ga_alt_x2"] > 0 and o["pozitif_sembol_pct_x2"] >= 100 * GENEL_ESIK_SEMBOL_PAY
            and o["en_iyi3_cikinca_sumr_x2"] > 0):
        return "GENELLEŞİYOR"
    return "ZAYIF / BELİRSİZ"


# ---- maliyet
def en_pahali_kripto_satiri(tablo: pd.DataFrame) -> pd.Series:
    """Kripto satırlarının en pahalısı: efektif komisyon + spread/kayma + stop kayması (oranlar) toplamı en büyük;
    eşitlikte sembol adı alfabetik ilk."""
    k = tablo[tablo["sinif"] == "kripto"].copy()
    if not len(k):
        raise ValueError("maliyet tablosunda kripto satırı yok")
    k["_puan"] = k["efektif_komisyon_oran"] + k["spread_kayma_oran"] + k["stop_kayma_oran"]
    k = k.sort_values(["_puan", "sembol"], ascending=[False, True], kind="mergesort")
    return k.iloc[0].drop("_puan")


def maliyet_tablosu_uret(v2_tablo: pd.DataFrame, yeni_semboller) -> pd.DataFrame:
    """v2 tablosu AYNEN + yeni semboller için en pahalı kripto satırının kopyası (sembol adı değişir, kaynak notu eklenir)."""
    pahali = en_pahali_kripto_satiri(v2_tablo)
    kopya = []
    for s in yeni_semboller:
        r = pahali.copy()
        r["sembol"] = s
        r["kaynak"] = f"YENİ SEMBOL SINAVI: v2 tablosunun en pahalı kripto satırı ({pahali['sembol']}) kopyası. " + str(pahali["kaynak"])
        kopya.append(r)
    yeni = pd.DataFrame(kopya, columns=v2_tablo.columns) if kopya else v2_tablo.iloc[0:0]
    out = pd.concat([v2_tablo, yeni], ignore_index=True)
    if out["sembol"].duplicated().any():
        raise ValueError("yeni semboller v2 tablosunda zaten var")
    return out


def veri_ozeti(*cerceveler) -> str:
    h = hashlib.sha256()
    for df in cerceveler:
        if df is None or not len(df):
            h.update(b"-")
            continue
        h.update(pd.util.hash_pandas_object(df, index=True).to_numpy().tobytes())
        h.update("|".join(map(str, df.columns)).encode())
    return h.hexdigest()


def sha256_dosya(yol) -> str:
    return hashlib.sha256(Path(yol).read_bytes()).hexdigest()


def git_commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=KOK, capture_output=True, text=True, check=True).stdout.strip()


# ============================================================================ liste (ağ)
def _s3_liste(onek: str):
    from motor.veri import indir
    import xml.etree.ElementTree as ET
    keys, prefs, marker = [], [], ""
    while True:
        p = {"delimiter": "/", "prefix": onek, "max-keys": "1000"}
        if marker:
            p["marker"] = marker
        r = indir._get(indir.S3_LISTE, params=p)
        r.raise_for_status()
        k = ET.fromstring(r.content)
        ns = {"s": k.tag.split("}")[0].strip("{")}
        keys += [e.text for e in k.findall("s:Contents/s:Key", ns)]
        prefs += [e.text for e in k.findall("s:CommonPrefixes/s:Prefix", ns)]
        if k.findtext("s:IsTruncated", namespaces=ns) == "true":
            marker = k.findtext("s:NextMarker", namespaces=ns) or (keys[-1] if keys else prefs[-1])
        else:
            return keys, prefs


def _gun_zip(anahtar: str) -> pd.DataFrame:
    from motor.veri import indir
    return indir.mum_csv_ayristir(indir.zip_icinden_csv(indir.zip_getir(anahtar)))


def arsiv_bilgi(sembol: str, secim=SECIM_TARIHI) -> dict:
    """Bir sembolün 1d arşivinden: ilk_mum, son_mum, hacim_30g (S öncesi son 30 gün toplam quote hacmi), medyan_kapanis."""
    from motor.veri import indir
    taban = indir.TABAN
    secim = utc(secim)
    aylik = {re.search(r"(\d{4}-\d{2})\.zip$", k).group(1): k
             for k in _s3_liste(f"{taban}/monthly/klines/{sembol}/1d/{sembol}-1d-")[0] if k.endswith(".zip")}
    b = {"sembol": sembol, "ilk_ay": min(aylik) if aylik else "", "son_ay": max(aylik) if aylik else "",
         "ilk_mum": pd.NaT, "son_mum": pd.NaT, "hacim_30g": float("nan"), "medyan_kapanis": float("nan"), "n_mum_30g": 0}
    if not aylik:
        return b
    ay_s = secim.strftime("%Y-%m")
    # ön süzgeç (yalnız ay düzeyinde, kesin): ilk ay > S-730g ayı ya da son ay < S ayı -> ayrıntı gerekmez
    if b["ilk_ay"] > (secim - pd.Timedelta(days=MIN_GECMIS_GUN)).strftime("%Y-%m") or b["son_ay"] < ay_s:
        return b
    b["ilk_mum"] = _gun_zip(aylik[b["ilk_ay"]]).index.min()
    son = _gun_zip(aylik[b["son_ay"]]).index.max()
    gunluk = [k for k in _s3_liste(f"{taban}/daily/klines/{sembol}/1d/{sembol}-1d-")[0] if k.endswith(".zip")]
    for k in gunluk:
        g = utc(re.search(r"(\d{4}-\d{2}-\d{2})\.zip$", k).group(1))
        son = max(son, g)
    b["son_mum"] = son
    pencere_bas = secim - pd.Timedelta(days=HACIM_PENCERE_GUN)
    parcalar = []
    for ay in sorted({pencere_bas.strftime("%Y-%m"), (secim - pd.Timedelta(days=1)).strftime("%Y-%m")}):
        if ay in aylik:
            parcalar.append(_gun_zip(aylik[ay]))
    if parcalar:
        d = pd.concat(parcalar)
        d = d[(d.index >= pencere_bas) & (d.index < secim)]
        b["hacim_30g"] = float(d["quote_hacim"].sum()) if len(d) else float("nan")
        b["n_mum_30g"] = int(len(d))
        b["medyan_kapanis"] = float(d["kapanis"].median()) if len(d) else float("nan")
    return b


def liste_uret(cikti: Path = CIKTI, is_parcacigi: int = 8) -> pd.DataFrame:
    from motor.veri import indir
    _, prefs = _s3_liste(f"{indir.TABAN}/monthly/klines/")
    semboller = sorted(p.rstrip("/").split("/")[-1] for p in prefs)
    adaylar = [s for s in semboller if usdt_surekli_mi(s)]
    print(f"arşivde {len(semboller)} sembol; USDT sürekli biçimli {len(adaylar)}", flush=True)
    with ThreadPoolExecutor(is_parcacigi) as ex:
        satirlar = list(ex.map(arsiv_bilgi, adaylar))
    bilgi = pd.DataFrame(satirlar)
    diger = pd.DataFrame({"sembol": [s for s in semboller if not usdt_surekli_mi(s)]})
    d = aday_sec(pd.concat([bilgi, diger], ignore_index=True)) if len(diger) else aday_sec(bilgi)
    # eleme nedeni ay-düzeyi süzgeçten gelenler için ayrıntı: ilk mum/son mum NaT olanlar zaten 'gecmis'/'S_de_islem_yok' görünür
    arsiv_son = pd.to_datetime(bilgi["son_mum"], utc=True).max()
    d["arsiv_son_mum"] = arsiv_son
    d["delist"] = pd.to_datetime(d["son_mum"], utc=True) < (arsiv_son - pd.Timedelta(days=DELIST_TOLERANS_GUN))
    kural = d["medyan_kapanis"].map(lambda p: kural_turet(p) if (p == p and p > 0) else (float("nan"), float("nan")))
    d["tick"] = [k[0] for k in kural]
    d["step"] = [k[1] for k in kural]
    cikti.mkdir(parents=True, exist_ok=True)
    tum_sut = ["sembol", "neden", "sira", "hacim_30g", "ilk_mum", "son_mum", "delist", "medyan_kapanis", "tick", "step", "ilk_ay", "son_ay"]
    d[tum_sut].sort_values(["sira", "hacim_30g"], ascending=[True, False]).to_csv(cikti / "adaylar_tum.csv", index=False)
    s = d[d["sira"] > 0].sort_values("sira")
    ciktis = pd.DataFrame({"sira": s["sira"], "sembol": s["sembol"], "hacim_30g_quote": s["hacim_30g"].round(2),
                           "ilk_mum": s["ilk_mum"], "son_mum": s["son_mum"], "delist": s["delist"],
                           "medyan_kapanis_S": s["medyan_kapanis"], "tick": s["tick"], "step": s["step"]})
    ciktis.to_csv(cikti / "semboller.csv", index=False)
    print(f"semboller.csv: {len(ciktis)} sembol, delist {int(ciktis['delist'].sum())}", flush=True)
    return ciktis


# ============================================================================ koşu
def _kurallar(sembol: str, semboller_df: pd.DataFrame):
    from motor.arastirma import wf_evren as we      # kurallari_tamamla() import'ta çalışır (eski evren kuralları)
    from motor.backtest.motor import SembolKurallari
    if sembol in ESKI_EVREN:
        return we.tarama.SEMBOL_KURALLARI.get(sembol, we.tarama.VARSAYILAN_KURAL)
    r = semboller_df.set_index("sembol").loc[sembol]
    return SembolKurallari(tick_size=float(r["tick"]), step_size=float(r["step"]), min_qty=float(r["step"]), min_notional=5.0)


def son_islem_kes(df: pd.DataFrame, son_islem) -> pd.DataFrame:
    """Delist sonrası arşiv, sıfır hacimli DÜZ mumlarla dolar (kapanış sabit). Son GERÇEK işlem mumunu (quote hacmi > 0) içeren
    mumdan sonrası atılır; açık işlem bu mumun kapanışından kapanır ("veri_sonu"). Girdi/çıktı indeksi: açılış zamanı."""
    return df[df.index <= utc(son_islem)]


def veri_oku(sembol: str, tf: str) -> tuple:
    """(mumlar, funding, en büyük mum zamanı, en büyük funding zamanı, son gerçek işlem 5m mumu): [OKUMA_BAS, 2026-11-01), son gerçek
    işlem mumunda kesilir. Sınır SERT doğrulanır."""
    from motor.veri import depo
    from motor.veri.yeniden_ornekle import tf_mumlari
    ham5 = depo.mum_oku(sembol, "5m", OKUMA_BAS, OLCUM_BIT_SINIR, kilit_ac=True, gerekce=KILIT_GEREKCE)
    tarih_siniri_dogrula(ham5.index, f"{sembol} 5m ham")
    gercek = ham5.index[(ham5["quote_hacim"] > 0).to_numpy()]
    if not len(gercek):
        raise RuntimeError(f"{sembol}: ölçüm aralığında işlem hacmi olan mum yok")
    son_islem = gercek.max()
    mumlar = son_islem_kes(tf_mumlari(sembol, tf, OKUMA_BAS, OLCUM_BIT_SINIR, kilit_ac=True, gerekce=KILIT_GEREKCE), son_islem)
    fund = son_islem_kes(depo.funding_oku(sembol, OKUMA_BAS, OLCUM_BIT_SINIR, kilit_ac=True, gerekce=KILIT_GEREKCE), son_islem)
    mx_m = tarih_siniri_dogrula(mumlar.index, f"{sembol} {tf} mum")
    mx_f = tarih_siniri_dogrula(fund.index, f"{sembol} funding")
    if mx_m is None:
        raise RuntimeError(f"{sembol} {tf}: ölçüm aralığında mum yok")
    return mumlar, fund, mx_m, mx_f, son_islem


def islem_kos(strateji_ad: str, tf: str, sembol: str, carpan: float, mumlar, fund, kurallar, tablo_yolu) -> pd.DataFrame:
    """Tek koşu: varsayılan ayar, funding dahil net R. Yalnız S sonrası AÇILAN işlemler (motor islem_baslangic)."""
    from motor.arastirma import evren_maliyet
    from motor.arastirma.v2 import ham
    from motor.backtest.motor import backtest
    from motor.strateji import funding
    etiket, st = ham.varsayilan_strateji(strateji_ad)
    if etiket != "varsayilan":
        raise RuntimeError(f"{strateji_ad}: varsayılan ayar bekleniyordu, bulunan: {etiket}")
    ay = evren_maliyet.maliyet_ayarlari(sembol, kurallar, carpan, tablo_yolu)
    hazir = funding.stratejiye_hazirla(st, mumlar, fund, sembol, tf)
    res = backtest(hazir, st, ay, fund, islem_baslangic=OLCUM_BAS)
    d = res.islemler.sort_values("giris_zamani", kind="stable").reset_index(drop=True)
    r = d["r"].to_numpy(dtype=float)
    if not np.isfinite(r).all():
        raise ValueError(f"{strateji_ad}/{sembol}: işlem R'si NaN/sonsuz")
    if len(d):
        g = pd.DatetimeIndex(d["giris_zamani"])
        c = pd.DatetimeIndex(d["cikis_zamani"])
        g = g.tz_localize("UTC") if g.tz is None else g
        c = c.tz_localize("UTC") if c.tz is None else c
        if (g < OLCUM_BAS).any():
            raise TarihSiniriIhlali(f"{strateji_ad}/{sembol}: S öncesi açılan işlem var")
        if c.max() > OLCUM_BIT_SINIR or g.max() > EN_BUYUK_MUM_ACILISI:
            raise TarihSiniriIhlali(f"{strateji_ad}/{sembol}: işlem ölçüm sınırını aşıyor ({g.max()}, {c.max()})")
    return pd.DataFrame({"giris_zamani": pd.DatetimeIndex(d["giris_zamani"]).as_unit("ns"),
                         "cikis_zamani": pd.DatetimeIndex(d["cikis_zamani"]).as_unit("ns"),
                         "yon": d["yon"].to_numpy(dtype=np.int8), "r": r, "cikis_nedeni": d["cikis_nedeni"].astype(str).to_numpy()})


_AYAR: dict = {}


def _isci(gorev: tuple) -> dict:
    sembol, evren, tf = gorev
    a = _AYAR
    mumlar, fund, mx_m, mx_f, son_islem = veri_oku(sembol, tf)
    kurallar = _kurallar(sembol, a["semboller_df"])
    sonuc = {"sembol": sembol, "evren": evren, "tf": tf, "max_mum": str(mx_m), "max_fund": str(mx_f) if mx_f is not None else "", "son_islem": str(son_islem),
             "veri_sha256": veri_ozeti(mumlar, fund), "islemler": {}}
    for ad, stf in STRATEJILER.items():
        if stf != tf:
            continue
        for carpan in CARPANLAR:
            sonuc["islemler"][(ad, carpan)] = islem_kos(ad, tf, sembol, carpan, mumlar, fund, kurallar, a["tablo_yolu"])
    return sonuc


def _baslat(ayar: dict):
    _AYAR.clear()
    _AYAR.update(ayar)


def kos(cikti: Path = CIKTI, surec: int = 4) -> dict:
    import multiprocessing as mp
    semboller_df = pd.read_csv(cikti / "semboller.csv")
    yeni = list(semboller_df["sembol"])
    if len(yeni) != len(set(yeni)) or set(yeni) & set(ESKI_EVREN):
        raise ValueError("semboller.csv: tekrarlı sembol ya da eski evrenle kesişim")
    from motor.arastirma import evren_maliyet
    v2_yol = KOK / "sonuclar" / "evren" / "v2" / "maliyet_tablosu_v2.csv"
    beklenen = v2_yol.with_suffix(".sha256").read_text().strip()
    if sha256_dosya(v2_yol) != beklenen:
        raise RuntimeError("v2 maliyet tablosu .sha256 ile uyuşmuyor")
    tablo = maliyet_tablosu_uret(pd.read_csv(v2_yol), yeni)
    tablo_yolu = cikti / "maliyet_tablosu_yeni_sembol.csv"
    tablo.to_csv(tablo_yolu, index=False)
    for s in ESKI_EVREN:                                    # eski evren kendi satırlarıyla: tabloda var olmalı
        evren_maliyet.satir(s, tablo_yolu)
    gorevler = [(s, "yeni", tf) for s in yeni for tf in sorted(set(STRATEJILER.values()))] + \
               [(s, "eski", tf) for s in ESKI_EVREN for tf in sorted(set(STRATEJILER.values()))]
    _baslat({"semboller_df": semboller_df, "tablo_yolu": tablo_yolu})
    (cikti / "islemler").mkdir(parents=True, exist_ok=True)
    sonuclar = []
    with mp.get_context("fork").Pool(surec) as havuz:
        for i, s in enumerate(havuz.imap_unordered(_isci, gorevler, chunksize=1), 1):
            sonuclar.append(s)
            print(f"[{i}/{len(gorevler)}] {s['evren']} {s['sembol']} {s['tf']} max_mum={s['max_mum']}", flush=True)
    # --- topla
    islem = {}                         # (evren, strateji, carpan) -> {sembol: r dizisi}
    sembol_satirlari = []
    for s in sorted(sonuclar, key=lambda x: (x["evren"], x["sembol"], x["tf"])):
        for (ad, carpan), df in s["islemler"].items():
            islem.setdefault((s["evren"], ad, carpan), {})[s["sembol"]] = df["r"].to_numpy()
            yol_d = cikti / "islemler" / f"x{carpan:g}"
            yol_d.mkdir(parents=True, exist_ok=True)
            df.to_parquet(yol_d / f"{ad}--{s['sembol']}.parquet")
    satirlar = []
    for evren, lst in (("yeni", yeni), ("eski", list(ESKI_EVREN))):
        for ad in STRATEJILER:
            x1, x2 = islem[(evren, ad, 1.0)], islem[(evren, ad, 2.0)]
            o = evren_olculeri(x1, x2, lst)
            o = {"evren": evren, "strateji": ad, "tf": STRATEJILER[ad], **o}
            o["yorum_x2"] = yorum_etiketi(o) if evren == "yeni" else ""
            satirlar.append(o)
            for sm in lst:
                r1, r2 = np.asarray(x1.get(sm, [])), np.asarray(x2.get(sm, []))
                m2 = r_olculeri(r2)
                sembol_satirlari.append({"evren": evren, "strateji": ad, "sembol": sm, "n_islem_x1": len(r1), "sum_r_x1": float(r1.sum()),
                                         "n_islem_x2": len(r2), "sum_r_x2": float(r2.sum()), "ort_r_x2": m2["ort_r"], "pf_x2": m2["pf"]})
    son_islem = {}
    for s in sonuclar:
        son_islem[(s["evren"], s["sembol"])] = s["son_islem"]
    ref = max(pd.Timestamp(v) for v in son_islem.values())
    pd.DataFrame([{"evren": e, "sembol": sm, "son_islem_mumu": v,
                   "delist": bool(pd.Timestamp(v) < ref - pd.Timedelta(days=DELIST_TOLERANS_GUN))}
                  for (e, sm), v in sorted(son_islem.items())]).to_csv(cikti / "delist_duzeltme.csv", index=False)
    pd.DataFrame(satirlar).to_csv(cikti / "sonuc_strateji.csv", index=False)
    pd.DataFrame(sembol_satirlari).to_csv(cikti / "sonuc_sembol.csv", index=False)
    mx = max(pd.Timestamp(s["max_mum"]) for s in sonuclar)
    tarih_siniri_dogrula([mx], "koşu sonu en büyük mum")
    ozet = {"betik_sha256": sha256_dosya(Path(__file__)), "semboller_csv_sha256": sha256_dosya(cikti / "semboller.csv"),
            "maliyet_tablosu_sha256": sha256_dosya(tablo_yolu), "v2_maliyet_tablosu_sha256": beklenen, "commit": git_commit(),
            "en_buyuk_okunan_mum": str(mx), "en_buyuk_okunan_funding": max((s["max_fund"] for s in sonuclar if s["max_fund"]), default=""),
            "girdi_veri_sha256": {f"{s['evren']}:{s['sembol']}:{s['tf']}": s["veri_sha256"] for s in sorted(sonuclar, key=lambda x: (x["evren"], x["sembol"], x["tf"]))},
            "olcum_bas": str(OLCUM_BAS), "olcum_bit_sinir_haric": str(OLCUM_BIT_SINIR), "okuma_bas": str(OKUMA_BAS),
            "boot": {"n": BOOT_N, "tohum": BOOT_TOHUM, "ga": GA_DUZEY}, "ana_carpan": ANA_CARPAN,
            "yeni_evren_sembol_sayisi": len(yeni), "eski_evren": list(ESKI_EVREN),
            "yorumlar_yeni_evren_x2": {r["strateji"]: r["yorum_x2"] for r in satirlar if r["evren"] == "yeni"},
            "islem_dosyalari_sha256": {str(p.relative_to(cikti)): sha256_dosya(p) for p in sorted((cikti / "islemler").rglob("*.parquet"))}}
    (cikti / "ozet.json").write_text(json.dumps(ozet, indent=1, ensure_ascii=False, default=str))
    return ozet


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("komut", choices=("liste", "kos"))
    p.add_argument("--surec", type=int, default=4)
    a = p.parse_args(argv)
    if a.komut == "liste":
        liste_uret()
    else:
        kos(surec=a.surec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
