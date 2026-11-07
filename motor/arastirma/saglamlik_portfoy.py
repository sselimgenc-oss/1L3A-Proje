"""Portföy sağlamlık paketi (Aşama 2, karar 23/24): karar 24'ü geçen portföy stratejileri şans eseri mi geçti?

Girdi: sonuclar/wf_portfoy/<wf_etiket>.parquet (gecti == True satırları) + sonuclar/wf_portfoy/gunluk/<wf_etiket>/
<strateji>--<evren>--<tf>.parquet (birleşik OOS günlük getirisi). Çıktı: sonuclar/saglamlik_portfoy/<wf_etiket>.csv
(+ .parquet): satır başına tüm ölçüler ve bir ÖNERİ sütunu `saglam_mi` (+ `saglam_nedenler`). Bu bir öneridir;
son karar kullanıcı/liderindir (karar 26).

ÖNERİ KURALI (koşudan ÖNCE sabitlendi; sonuçlara bakılarak DEĞİŞTİRİLMEZ) — beş kapının HEPSİ geçilmeli:
  K1  maliyet x2: aynı wf_portfoy (komisyon taker/maker + kayma + stop kayması x2) -> OOS Sharpe >= 0.4 VE net > 0
  K2  rastgele kıyas: p <= 0.05 (yöntem 2)
  K3  blok bootstrap OOS Sharpe %90 aralığının alt ucu (5. yüzdelik) > 0 (yöntem 3)
  K4  parametre komşuluğu: en sık seçilen ayarın komşularının >= %60'ında OOS Sharpe > 0; en az 2 geçerli komşu
      yoksa kapı geçilmez (yöntem 4)
  (K5 yok: yoğunlaşma, rejim ve yıl bazında sonuç yalnız RAPORLANIR, kapı değildir.)

YÖNTEMLER
 1. Maliyet x2: `wf_portfoy.wf_portfoy(..., maliyet_carpani=2)`; aynı aday kümesi, pencereler ve eğitim skoru. Maliyet
    artınca eğitimde başka aday seçilebilir (gerçek bir stres senaryosu). m2_sharpe, m2_net_getiri. Bu koşular ayrı bir
    deneme kaydına (`sonuclar/saglamlik_portfoy/deneme_kaydi_m2.jsonl`) yazılır; ana kaydı şişirmez.
 2. Rastgele kıyas (Monte Carlo, N_SIM = 200 simülasyon). Stratejinin her test penceresinde seçilmiş adayı için
    (walk-forward seçimi `secimler` sütunundan), aynı adayın "rastgele ağırlıklı" kopyası aynı motorla (aynı veri,
    aynı maliyet, aynı limit modu, AYNI STOP KURALI: adayın kendi `stoplar` işlevi) koşulur:
      - Yeniden dengeleme takvimi: adayın pozisyon durumunun (hedeflerin ileri doldurulmuş hali) DEĞİŞTİĞİ satırlar.
        Rastgele kopya yalnız bu satırlarda emir verir.
      - Pozisyon sayısı ve ağırlık: o satırdaki sıfırdan farklı ağırlıkların (işaretli) KÜMESİ aynen korunur, ama
        hangi sembole gideceği rastgeledir (ATR'si hazır olan semboller arasından, yerine koymadan). Böylece her satırda
        long/short sayısı, brüt ve net ağırlık stratejiyle birebir aynıdır (ortalama maruziyet eşleşir).
      - Devir eşleşmesi: tam yeniden çekim, stratejinin korumadığı pozisyonları da değiştirip maliyeti şişirir (kıyası
        stratejiye ADAYSIZ lehine eğer). Bu yüzden stratejinin iki ardışık satır arasında KORUDUĞU sembol sayısı kadar
        pozisyon, önceki rastgele pozisyonlardan (işaretini koruyarak) korunur; kalanı yeniden çekilir.
    Her simülasyon: seçilen her adayın rastgele kopyası TAM veride koşulur (tek tohum), gerçek stratejideki gibi
    test pencerelerine dikilir (seçimsiz pencereler 0), OOS günlük Sharpe'ı hesaplanır. Stratejinin gerçek OOS Sharpe'ı bu
    dağılımda: rnd_yuzdelik = sim Sharpe < gerçek oranı; p = (1 + #{sim >= gerçek}) / (N + 1) (tek taraflı).
    Not: rastgele kopya eğitimde SEÇİLMEZ (seçim kenarı yoktur); gerçek strateji seçim kenarı OOS'ta görülür -> kıyas adil.
    Yaklaşıklık: pairs gibi hedef oranı olan stratejilerde rastgele kopya bacak ilişkisini korumaz (yalnız ağırlık kümesi).
 3. Blok bootstrap: OOS günlük getirileri (seçimsiz pencereler dahil tüm OOS günleri), dairesel bloklar 20 gün,
    2000 yeniden örnekleme, yıllık Sharpe (sqrt(365)); %5 ve %95 yüzdelikleri boot_alt / boot_ust. Tohum sabit.
 4. Parametre komşuluğu: en sık seçilen ayar (`en_sik_ayar`; etkin parametreleri `aday_listesi`nden). Sayısal parametre
    (bool/str hariç; ızgarada tam sayı-dizgeli değerler, ör. takvim "14", sıralı sayısal sayılır) için ızgarada ±1 adım;
    ızgarada olmayan / ızgarada bulunmayan sayısal parametre için ±%20 (int ise yuvarlanır, en az ±1). 0 değerleri,
    `semboller` ve kategorik parametreler oynatılmaz; aynı etkin parametreler tek komşu. Her komşu TAM veride sabit ayarla
    koşulur (pencere seçimi yok); OOS aralığındaki (ilk test başı - son test sonu) günlük Sharpe > 0 ise "olumlu".
    komsu_oran = olumlu / geçerli komşu; kurulamayan/koşulamayan komşular komsu_hata'da sayılır, paydaya girmez.
    sabit_sharpe = en sık ayarın kendisinin sabit-ayar OOS Sharpe'ı (bilgi).
 5. Yoğunlaşma (yalnız rapor): en iyi %1 ve %5 gün (en az 1) çıkarılınca bileşik net (net_ex1, net_ex5); en iyi ayın
    ve en iyi yılın payı = o dönemin log-getirisi / toplam log-getiri (toplam <= 0 ise NaN; 1'i aşabilir).
 6. Rejim ve yıl (yalnız rapor): rejim, BTCUSDT günlük kapanışından nedensel (bir önceki tamamlanmış gün):
    boğa: kapanış > SMA200 ve SMA200 eğimi (20 gün) > 0; ayı: kapanış < SMA200 ve eğim < 0; kalanı yatay; BTC verisi ya da
    SMA yoksa "belirsiz". Her rejim için gün sayısı, bileşik net, günlük Sharpe (rej_<ad>_gun/net/sharpe). Yıl bazında
    net ve Sharpe `yil_json` sütununda; yil_pozitif_oran = net > 0 yıl oranı.

Kilit (karar 20): veri yalnız `motor.portfoy.veri.veri_yukle` (depo.mum_oku) ile okunur; kilit_ac yok.
Paralel: bileşen başına bir görev (m2, analiz, komşu, rastgele dilimleri); kaldığı yerden devam: biten bileşenler
`sonuclar/saglamlik_portfoy/<etiket>_parcalar/*.json` olarak saklanır ve atlanır.

CLI: python -m motor.arastirma.saglamlik_portfoy --wf-etiket p3_kripto_v2 [--surec 4] [--n-sim 200]
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import time
import zlib
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from motor.arastirma import wf_portfoy as wp
from motor.portfoy import veri as pveri
from motor.portfoy.motor import portfoy_backtest
from motor.portfoy.stratejiler import tum_portfoy_stratejileri
from motor.portfoy.temel import PortfoyStratejisi, atr_tablosu

KOK = Path(__file__).resolve().parents[2]
CIKTI_DIZINI = KOK / "sonuclar" / "saglamlik_portfoy"

# ---- öneri kapıları (sabit; bkz. modül başı) ----
M2_SHARPE_MIN = 0.4
M2_NET_MIN = 0.0            # net > 0
RND_P_MAX = 0.05
BOOT_ALT_MIN = 0.0          # alt uç > 0
KOMSU_ORAN_MIN = 0.60
KOMSU_MIN_GECERLI = 2
# ---- yöntem sabitleri ----
N_SIM = 200
SIM_DILIM = 20
BOOT_BLOK = 20
BOOT_TEKRAR = 2000
BOOT_TOHUM = 20261107
KOMSU_ORANI = 0.20
SMA_REJIM = 200
EGIM_GUN = 20
REJIM_SEMBOL = "BTCUSDT"
GUN = pd.Timedelta(days=1)


# ---------------------------------------------------------------------------- saf istatistik yardımcıları
def sharpe(r) -> float:
    return wp.sharpe_gunluk(r)


def blok_bootstrap_sharpe(r, blok: int = BOOT_BLOK, tekrar: int = BOOT_TEKRAR, tohum: int = BOOT_TOHUM,
                          yuzdelikler=(5, 95)) -> dict:
    """Dairesel blok bootstrap ile yıllık Sharpe dağılımı. -> {boot_alt, boot_ust, boot_ort, boot_sharpe}"""
    r = np.asarray(r, dtype=float)
    T = len(r)
    if T < 2 * blok:
        return {"boot_alt": math.nan, "boot_ust": math.nan, "boot_ort": math.nan, "boot_sharpe": sharpe(r)}
    rng = np.random.default_rng(tohum)
    nb = math.ceil(T / blok)
    bas = rng.integers(0, T, size=(tekrar, nb))
    idx = ((bas[:, :, None] + np.arange(blok)[None, None, :]) % T).reshape(tekrar, nb * blok)[:, :T]
    x = r[idx]
    sd = x.std(axis=1, ddof=1)
    sh = np.where(sd > 0, x.mean(axis=1) / np.where(sd > 0, sd, 1.0) * math.sqrt(365), np.nan)
    lo, hi = np.nanpercentile(sh, yuzdelikler)
    return {"boot_alt": float(lo), "boot_ust": float(hi), "boot_ort": float(np.nanmean(sh)), "boot_sharpe": sharpe(r)}


def rastgele_p(gercek: float, sim) -> dict:
    """p = (1 + #{sim >= gerçek}) / (N + 1) (tek taraflı); yüzdelik = sim < gerçek oranı. NaN simülasyonlar atılır."""
    s = np.asarray(sim, dtype=float)
    s = s[np.isfinite(s)]
    if not np.isfinite(gercek) or len(s) == 0:
        return {"rnd_n": int(len(s)), "rnd_p": math.nan, "rnd_yuzdelik": math.nan, "rnd_ort": math.nan, "rnd_std": math.nan}
    return {"rnd_n": int(len(s)), "rnd_p": float((1 + (s >= gercek).sum()) / (len(s) + 1)),
            "rnd_yuzdelik": float((s < gercek).mean()), "rnd_ort": float(s.mean()), "rnd_std": float(s.std(ddof=1)) if len(s) > 1 else math.nan}


def yogunlasma(r: pd.Series) -> dict:
    """Yoğunlaşma (rapor): en iyi %1/%5 gün hariç net, en iyi ay/yıl payı (log-getiri)."""
    v = r.to_numpy(dtype=float)
    m = {"net_ex1": math.nan, "net_ex5": math.nan, "en_iyi_ay_pay": math.nan, "en_iyi_yil_pay": math.nan}
    if len(v) == 0:
        return m
    s = np.sort(v)[::-1]
    for ad, oran in (("net_ex1", 0.01), ("net_ex5", 0.05)):
        m[ad] = float(np.prod(1.0 + s[max(1, math.ceil(oran * len(s))):]) - 1.0)
    lg = pd.Series(np.log1p(v), index=r.index)
    toplam = float(lg.sum())
    if toplam > 0:
        m["en_iyi_ay_pay"] = float(lg.groupby([lg.index.year, lg.index.month]).sum().max() / toplam)
        m["en_iyi_yil_pay"] = float(lg.groupby(lg.index.year).sum().max() / toplam)
    return m


def rejim_etiketleri(kapanis: pd.Series, gunler: pd.DatetimeIndex) -> pd.Series:
    """Her gün için rejim (bir önceki TAMAMLANMIŞ günün değeriyle; nedensel)."""
    k = kapanis.groupby(kapanis.index.floor("D")).last()
    sma = k.rolling(SMA_REJIM, min_periods=SMA_REJIM).mean()
    egim = sma / sma.shift(EGIM_GUN) - 1.0
    et = pd.Series("belirsiz", index=k.index, dtype=object)
    ok = sma.notna() & egim.notna()
    et[ok & (k > sma) & (egim > 0)] = "boga"
    et[ok & (k < sma) & (egim < 0)] = "ayi"
    et[ok & (et == "belirsiz")] = "yatay"
    return et.shift(1).reindex(gunler).fillna("belirsiz")


def rejim_ve_yil(r: pd.Series, kapanis: Optional[pd.Series]) -> dict:
    m: dict = {}
    et = rejim_etiketleri(kapanis, r.index) if kapanis is not None and len(kapanis) else \
        pd.Series("belirsiz", index=r.index, dtype=object)
    for ad in ("boga", "ayi", "yatay", "belirsiz"):
        x = r[et.to_numpy() == ad].to_numpy(dtype=float)
        m[f"rej_{ad}_gun"] = int(len(x))
        m[f"rej_{ad}_net"] = float(np.prod(1.0 + x) - 1.0) if len(x) else math.nan
        m[f"rej_{ad}_sharpe"] = sharpe(x) if len(x) > 1 else math.nan
    yil = {}
    for y in sorted(set(r.index.year)):
        x = r[r.index.year == y].to_numpy(dtype=float)
        yil[int(y)] = {"net": float(np.prod(1.0 + x) - 1.0), "sharpe": sharpe(x), "gun": int(len(x))}
    m["yil_json"] = json.dumps(yil)
    m["yil_pozitif_oran"] = float(np.mean([v["net"] > 0 for v in yil.values()])) if yil else math.nan
    return m


# ---------------------------------------------------------------------------- rastgele ağırlıklı kopya
def rastgele_hedef(durum: np.ndarray, degisim: np.ndarray, uygun: np.ndarray, kolonlar, index, rng) -> pd.DataFrame:
    """Rastgele hedef tablosu (NaN = değişiklik yok). durum: (T, n) adayın ileri doldurulmuş hedef durumu; degisim: (T,)
    durumun değiştiği satırlar; uygun: (T, n) sembol o satırda pozisyon alabilir mi. Modül başı yöntem 2."""
    T, n = durum.shape
    out = np.full((T, n), np.nan)
    onceki_gercek = np.zeros(n)
    onceki_rnd = np.zeros(n)
    for i in np.flatnonzero(degisim):
        cur = durum[i]
        agirlik = [float(w) for w in cur[cur != 0]]
        pos = [w for w in agirlik if w > 0]
        neg = [w for w in agirlik if w < 0]
        korunan_n = int(((np.sign(onceki_gercek) == np.sign(cur)) & (cur != 0)).sum())
        yeni = np.zeros(n)
        adaylar = [j for j in np.flatnonzero(onceki_rnd != 0) if uygun[i, j]]
        rng.shuffle(adaylar)
        kalan = 0
        for j in adaylar:
            if kalan >= korunan_n:
                break
            havuz = pos if onceki_rnd[j] > 0 else neg
            if not havuz:
                continue
            yeni[j] = havuz.pop(int(rng.integers(len(havuz))))
            kalan += 1
        artan = pos + neg
        rng.shuffle(artan)
        bos = [j for j in np.flatnonzero(uygun[i]) if yeni[j] == 0]
        rng.shuffle(bos)
        for w, j in zip(artan, bos):
            yeni[j] = w
        out[i] = yeni
        onceki_gercek, onceki_rnd = cur, yeni
    return pd.DataFrame(out, index=index, columns=list(kolonlar))


class RastgeleHazirlik:
    """Bir adayın rastgele kopyası için sabit parçalar (hedef durum, değişim satırları, uygunluk)."""

    def __init__(self, st, veriler: dict):
        h = st.hedefler(veriler)
        self.kolonlar = list(h.columns)
        self.index = h.index
        durum = h.ffill().fillna(0.0)
        self.durum = durum.to_numpy(dtype=float)
        onceki = durum.shift(1).fillna(0.0)
        self.degisim = ((durum - onceki).abs() > 1e-9).any(axis=1).to_numpy()
        atr = atr_tablosu({s: veriler[s] for s in self.kolonlar}, st.parametreler["atr_periyot"])
        self.uygun = atr.reindex(h.index).ffill().notna().to_numpy()
        self.n_degisim = int(self.degisim.sum())


class RastgeleAgirlik(PortfoyStratejisi):
    """Aday stratejinin rastgele ağırlıklı kopyası: takvim, ağırlık kümesi ve stop kuralı adayın kendisidir."""
    ad = "pf__rastgele"

    def __init__(self, taban, hazirlik: RastgeleHazirlik, tohum):
        self.parametreler = {}
        self.taban, self.hazirlik, self.tohum = taban, hazirlik, tohum

    def hedefler(self, veriler: dict) -> pd.DataFrame:
        hz = self.hazirlik
        return rastgele_hedef(hz.durum, hz.degisim, hz.uygun, hz.kolonlar, hz.index, np.random.default_rng(self.tohum))

    def stoplar(self, veriler: dict, hedefler: pd.DataFrame) -> pd.DataFrame:
        return self.taban.stoplar(veriler, hedefler)


# ---------------------------------------------------------------------------- komşu ayarlar
def _sayi_mi(x) -> bool:
    return (isinstance(x, (int, float)) and not isinstance(x, bool)) or (isinstance(x, str) and x.isdigit())


def komsu_ayarlari(sinif, parametreler: dict) -> list:
    """-> [{parametre: yeni_deger}] (tek parametre oynayan komşular). Modül başı yöntem 4."""
    izgara = getattr(sinif, "parametre_izgarasi", {}) or {}
    komsular = []
    for ad, deger in parametreler.items():
        if ad == "semboller" or deger is None or isinstance(deger, (bool, tuple, list, dict)):
            continue
        if isinstance(deger, str) and not (ad in izgara and deger.isdigit()):
            continue
        yeniler = []
        g = list(izgara.get(ad, []))
        if g and all(_sayi_mi(x) for x in g) and deger in g:
            gs = sorted(g, key=float)
            i = gs.index(deger)
            yeniler = [gs[j] for j in (i - 1, i + 1) if 0 <= j < len(gs)]
        elif isinstance(deger, (int, float)) and deger != 0:
            if isinstance(deger, int):
                lo, hi = round(deger * (1 - KOMSU_ORANI)), round(deger * (1 + KOMSU_ORANI))
                lo, hi = min(lo, deger - 1), max(hi, deger + 1)
                yeniler = [x for x in (lo, hi) if x >= 1]
            else:
                yeniler = [deger * (1 - KOMSU_ORANI), deger * (1 + KOMSU_ORANI)]
        for y in yeniler:
            if y != deger:
                komsular.append({ad: y})
    return komsular


# ---------------------------------------------------------------------------- görev altyapısı
_VERI: dict = {}
_HAZIR: dict = {}


def _veri(evren_ad: str, tf: str):
    k = (evren_ad, tf)
    if k not in _VERI:
        _VERI.clear()
        _VERI[k] = pveri.veri_yukle(tuple(wp.EVRENLER[evren_ad]), tf)
    return _VERI[k]


def anahtar(satir) -> str:
    return f"{satir['strateji']}--{satir['evren']}--{satir['tf']}"


def _gunluk(r) -> pd.Series:
    g = r.gunluk_ozsermaye.pct_change().fillna(0.0)
    g.index = pd.DatetimeIndex(g.index).floor("D")
    return g.groupby(level=0).last().astype(float)


def _kos(st, evren_ad: str, tf: str, ay=None) -> pd.Series:
    veriler, fundingler = _veri(evren_ad, tf)
    evren = tuple(wp.EVRENLER[evren_ad])
    sec = wp.gerekli_semboller(st, evren)
    return _gunluk(portfoy_backtest({s: veriler[s] for s in sec}, st, ay or wp.maliyet_ayarlari(1.0),
                                    {s: fundingler[s] for s in sec if s in fundingler}))


def secim_pencereleri(secimler: list) -> list:
    return [(s["secilen"], pd.Timestamp(s["test_bas"]), pd.Timestamp(s["test_bit"])) for s in secimler
            if s["secilen"] is not None]


def dik(gunluk_by_aday: dict, pencereler: list, oos_gunleri: pd.DatetimeIndex) -> pd.Series:
    """Seçilen adayların test penceresi getirilerini OOS günlerine dikler (seçimsiz günler 0)."""
    out = pd.Series(0.0, index=oos_gunleri)
    for etiket, t0, t1 in pencereler:
        g = gunluk_by_aday[etiket]
        g = g[(g.index >= t0) & (g.index < t1)]
        ort = out.index.intersection(g.index)
        out.loc[ort] = g.reindex(ort).to_numpy()
    return out


def _satir_ayar(satir, aday_etiket):
    adaylar, _ = wp.aday_listesi(satir["strateji"], wp.EVRENLER[satir["evren"]], True)
    d = dict(adaylar)
    if aday_etiket not in d:
        raise KeyError(f"aday bulunamadı: {aday_etiket}")
    return d[aday_etiket]


def oos_getiri_oku(wf_dizin: Path, wf_etiket: str, satir) -> pd.Series:
    yol = wp.islem_yolu(wf_dizin, wf_etiket, satir["strateji"], satir["evren"], satir["tf"], "gunluk")
    return pd.read_parquet(yol)["oos_getiri"].astype(float)


# ---- bileşenler
def bilesen_m2(satir, g) -> dict:
    yol = Path(g["cikti_dizini"]) / "m2_wf" / anahtar(satir)
    df = wp.wf_portfoy(g["wf_etiket"], [satir["strateji"]], satir["evren"], tf=satir["tf"], surec=1, cikti_dizini=yol,
                       deneme_kaydi_yolu=Path(g["cikti_dizini"]) / "deneme_kaydi_m2.jsonl", ilerleme=False,
                       maliyet_carpani=2.0)
    r = df.iloc[0]
    if r["hata"]:
        return {"m2_hata": str(r["hata"])}
    return {"m2_sharpe": float(r["sharpe"]), "m2_net_getiri": float(r["net_getiri"]), "m2_max_dusus": float(r["max_dusus"]),
            "m2_hata": ""}


def bilesen_analiz(satir, g) -> dict:
    r = oos_getiri_oku(g["wf_dizin"], g["wf_etiket"], satir)
    m = {"gercek_sharpe": sharpe(r.to_numpy()), **blok_bootstrap_sharpe(r.to_numpy()), **yogunlasma(r)}
    kap = None
    try:
        v, _ = pveri.veri_yukle((REJIM_SEMBOL,), "1d")
        kap = v[REJIM_SEMBOL]["kapanis"]
    except Exception:  # noqa: BLE001  (BTC verisi yoksa rejimler 'belirsiz')
        pass
    m.update(rejim_ve_yil(r, kap))
    return m


def bilesen_komsu(satir, g) -> dict:
    sinif = tum_portfoy_stratejileri()[satir["strateji"]]
    taban = _satir_ayar(satir, satir["en_sik_ayar"])
    oos_bas, oos_bit = pd.Timestamp(satir["oos_bas"]), pd.Timestamp(satir["oos_bit"])

    def oos_sharpe(st):
        gl = _kos(st, satir["evren"], satir["tf"])
        return sharpe(gl[(gl.index >= oos_bas) & (gl.index < oos_bit)].to_numpy())

    out = {"sabit_sharpe": math.nan}
    try:
        out["sabit_sharpe"] = oos_sharpe(taban)
    except Exception as e:  # noqa: BLE001
        out["sabit_hata"] = f"{type(e).__name__}: {e}"[:160]
    gecerli, olumlu, hata, ayrinti, gorulen = 0, 0, 0, [], set()
    for oyna in komsu_ayarlari(sinif, taban.parametreler):
        try:
            st = taban.yeni(**oyna)
            kimlik = wp._json(st.parametreler)
            if kimlik in gorulen:
                continue
            gorulen.add(kimlik)
            evren = tuple(wp.EVRENLER[satir["evren"]])
            if not st.uygun_mu(evren):
                raise ValueError("evrende uygun değil")
            sh = oos_sharpe(st)
            if not np.isfinite(sh):
                raise ValueError("Sharpe hesaplanamadı")
        except Exception as e:  # noqa: BLE001  (kurulamayan komşu paydaya girmez)
            hata += 1
            ayrinti.append({"ayar": oyna, "hata": f"{type(e).__name__}: {e}"[:100]})
            continue
        gecerli += 1
        olumlu += int(sh > 0)
        ayrinti.append({"ayar": oyna, "sharpe": sh})
    out.update({"komsu_n": gecerli, "komsu_olumlu": olumlu, "komsu_hata": hata,
                "komsu_oran": olumlu / gecerli if gecerli else math.nan,
                "komsu_ayrinti": json.dumps(ayrinti, default=str, ensure_ascii=False)})
    return out


def _hazir(satir, etiket):
    k = (satir["strateji"], satir["evren"], satir["tf"], etiket)
    if k not in _HAZIR:
        st = _satir_ayar(satir, etiket)
        veriler, fundingler = _veri(satir["evren"], satir["tf"])
        sec = wp.gerekli_semboller(st, tuple(wp.EVRENLER[satir["evren"]]))
        v = {s: veriler[s] for s in sec}
        f = {s: fundingler[s] for s in sec if s in fundingler}
        _HAZIR[k] = (st, v, f, RastgeleHazirlik(st, v))
    return _HAZIR[k]


def bilesen_rastgele(satir, g, dilim: int) -> dict:
    secimler = json.loads(satir["secimler"])
    pencere = secim_pencereleri(secimler)
    etiketler = sorted({p[0] for p in pencere})
    oos_gunleri = oos_getiri_oku(g["wf_dizin"], g["wf_etiket"], satir).index
    ay = wp.maliyet_ayarlari(1.0)
    temel_tohum = zlib.crc32(anahtar(satir).encode())
    sharpeler = []
    for sim in range(dilim * g["dilim"], min((dilim + 1) * g["dilim"], g["n_sim"])):
        gl = {}
        for k, etiket in enumerate(etiketler):
            st, v, f, hz = _hazir(satir, etiket)
            tohum = [temel_tohum, sim, k]
            gl[etiket] = _gunluk(portfoy_backtest(v, RastgeleAgirlik(st, hz, tohum), ay, f))
        sharpeler.append(sharpe(dik(gl, pencere, oos_gunleri).to_numpy()))
    return {"sharpe": sharpeler}


def gorev_calistir(gorev: dict) -> dict:
    t0 = time.perf_counter()
    g, satir, tur = gorev["ortak"], gorev["satir"], gorev["tur"]
    try:
        if tur == "m2":
            sonuc = bilesen_m2(satir, g)
        elif tur == "analiz":
            sonuc = bilesen_analiz(satir, g)
        elif tur == "komsu":
            sonuc = bilesen_komsu(satir, g)
        else:
            sonuc = bilesen_rastgele(satir, g, int(tur.split("_")[1]))
        sonuc["_hata"] = ""
    except Exception as e:  # noqa: BLE001  (bileşen hatası kaydedilir; bu bileşen kapıyı geçmez)
        sonuc = {"_hata": f"{type(e).__name__}: {e}"[:300]}
    sonuc["_sure_sn"] = time.perf_counter() - t0
    return {"anahtar": gorev["anahtar"], "tur": tur, "sonuc": sonuc}


# ---------------------------------------------------------------------------- birleştirme
def kapilar(m: dict) -> tuple:
    """Satırdaki ölçülerden K1-K4 ve öneri. -> (saglam_mi, [geçilemeyen kapılar])"""
    def ok(v):
        return v is not None and not (isinstance(v, float) and math.isnan(v))
    ned = []
    if not (ok(m.get("m2_sharpe")) and m["m2_sharpe"] >= M2_SHARPE_MIN and ok(m.get("m2_net_getiri")) and m["m2_net_getiri"] > M2_NET_MIN):
        ned.append(f"K1 maliyet x2 (Sharpe {m.get('m2_sharpe')}, net {m.get('m2_net_getiri')})")
    if not (ok(m.get("rnd_p")) and m["rnd_p"] <= RND_P_MAX):
        ned.append(f"K2 rastgele p {m.get('rnd_p')}")
    if not (ok(m.get("boot_alt")) and m["boot_alt"] > BOOT_ALT_MIN):
        ned.append(f"K3 bootstrap alt {m.get('boot_alt')}")
    if not (ok(m.get("komsu_oran")) and m.get("komsu_n", 0) >= KOMSU_MIN_GECERLI and m["komsu_oran"] >= KOMSU_ORAN_MIN):
        ned.append(f"K4 komşu oranı {m.get('komsu_oran')} (n={m.get('komsu_n')})")
    return (not ned), ned


def satir_birlestir(satir, parcalar: dict, n_sim: int) -> dict:
    out = {"strateji": satir["strateji"], "evren": satir["evren"], "tf": satir["tf"], "en_sik_ayar": satir["en_sik_ayar"],
           "sharpe": float(satir["sharpe"]), "net_getiri": float(satir["net_getiri"]), "max_dusus": float(satir["max_dusus"]),
           "bh_sharpe": float(satir.get("bh_sharpe", math.nan)), "hatalar": ""}
    hatalar = []
    sims = []
    for tur, p in parcalar.items():
        if p.get("_hata"):
            hatalar.append(f"{tur}: {p['_hata']}")
            continue
        if tur.startswith("rnd_"):
            sims += p["sharpe"]
        else:
            out.update({k: v for k, v in p.items() if not k.startswith("_")})
    if sims:
        out.update(rastgele_p(float(satir["sharpe"]), sims))
    out["hatalar"] = " | ".join(hatalar)
    ok, ned = kapilar(out)
    out["saglam_mi"] = bool(ok)
    out["saglam_nedenler"] = "; ".join(ned)
    return out


def _parca_yolu(dizin: Path, anah: str, tur: str) -> Path:
    return dizin / f"{anah}--{tur}.json"


def saglamlik_portfoy(wf_etiket: str, surec: int = 4, n_sim: int = N_SIM, dilim: int = SIM_DILIM,
                      wf_dizin: Optional[Path] = None, cikti_dizini: Optional[Path] = None, etiket: Optional[str] = None,
                      stratejiler: Optional[list] = None, ilerleme: bool = True) -> pd.DataFrame:
    wf_dizin = Path(wf_dizin) if wf_dizin is not None else wp.CIKTI_DIZINI
    cikti_dizini = Path(cikti_dizini) if cikti_dizini is not None else CIKTI_DIZINI
    etiket = etiket or wf_etiket
    cikti_dizini.mkdir(parents=True, exist_ok=True)
    wf = pd.read_parquet(wf_dizin / f"{wf_etiket}.parquet")
    hedef = wf[(wf["gecti"]) & (wf["hata"] == "")]
    if stratejiler is not None:
        hedef = hedef[hedef["strateji"].isin(stratejiler)]
    satirlar = {anahtar(r): r.to_dict() for _, r in hedef.iterrows()}
    parca_dizin = cikti_dizini / f"{etiket}_parcalar"
    parca_dizin.mkdir(parents=True, exist_ok=True)
    ortak = {"wf_etiket": wf_etiket, "wf_dizin": wf_dizin, "cikti_dizini": cikti_dizini, "n_sim": n_sim, "dilim": dilim}
    n_dilim = math.ceil(n_sim / dilim)
    turler = ["m2", "analiz", "komsu"] + [f"rnd_{i}" for i in range(n_dilim)]
    tum, kalan = 0, []
    for anah, s in satirlar.items():
        for tur in turler:
            tum += 1
            if not _parca_yolu(parca_dizin, anah, tur).exists():
                kalan.append({"anahtar": anah, "tur": tur, "satir": s, "ortak": ortak})
    # uzun görevler (rastgele dilimleri) önce
    kalan.sort(key=lambda x: (not x["tur"].startswith("rnd_"), x["anahtar"], x["tur"]))
    if ilerleme:
        print(f"[sgp] {etiket}: {len(satirlar)} strateji, {tum} görev, kalan {len(kalan)}", flush=True)
    t0 = time.perf_counter()

    def bitir(r, n):
        yol = _parca_yolu(parca_dizin, r["anahtar"], r["tur"])
        if not r["sonuc"].get("_hata"):                 # hatalı bileşen kaydedilmez: yeniden koşulunca tekrar denenir
            yol.write_text(json.dumps(r["sonuc"], default=str))
        else:
            (parca_dizin / f"{r['anahtar']}--{r['tur']}.hata").write_text(json.dumps(r["sonuc"], default=str))
        if ilerleme:
            print(f"[sgp] {n}/{len(kalan)} {r['anahtar']} {r['tur']} {r['sonuc'].get('_hata') or 'ok'} "
                  f"({time.perf_counter() - t0:.0f} sn)", flush=True)

    if kalan:
        if surec <= 1:
            for n, g in enumerate(kalan, 1):
                bitir(gorev_calistir(g), n)
        else:
            with mp.get_context("fork").Pool(min(surec, len(kalan))) as havuz:
                for n, r in enumerate(havuz.imap_unordered(gorev_calistir, kalan, chunksize=1), 1):
                    bitir(r, n)
    satirlar_out = []
    for anah, s in satirlar.items():
        parcalar = {}
        for tur in turler:
            yol = _parca_yolu(parca_dizin, anah, tur)
            if yol.exists():
                parcalar[tur] = json.loads(yol.read_text())
            else:
                hy = parca_dizin / f"{anah}--{tur}.hata"
                parcalar[tur] = json.loads(hy.read_text()) if hy.exists() else {"_hata": "bileşen yok"}
        satirlar_out.append(satir_birlestir(s, parcalar, n_sim))
    df = pd.DataFrame(satirlar_out)
    if len(df):
        df.to_parquet(cikti_dizini / f"{etiket}.parquet", index=False)
        df.to_csv(cikti_dizini / f"{etiket}.csv", index=False)
    if ilerleme:
        print(f"[sgp] bitti: {time.perf_counter() - t0:.0f} sn -> {cikti_dizini / (etiket + '.csv')}", flush=True)
    return df


def main(argv=None):
    ap = argparse.ArgumentParser(description="Portföy sağlamlık paketi (karar 24'ü geçenler için)")
    ap.add_argument("--wf-etiket", required=True)
    ap.add_argument("--etiket", default=None, help="çıktı etiketi (varsayılan: wf etiketi)")
    ap.add_argument("--stratejiler", nargs="*", default=None)
    ap.add_argument("--surec", type=int, default=4)
    ap.add_argument("--n-sim", type=int, default=N_SIM)
    a = ap.parse_args(argv)
    df = saglamlik_portfoy(a.wf_etiket, a.surec, a.n_sim, etiket=a.etiket, stratejiler=a.stratejiler)
    if len(df):
        print(f"önerilen sağlam: {int(df['saglam_mi'].sum())}/{len(df)}")


if __name__ == "__main__":
    main()
