"""Evren stratejileri taraması (karar 27; ön kayıt: sonuclar/evren/ON_KAYIT.md — yöntem ve ölçütler orada sabittir).

Evren stratejisi = strateji + tf + TEK ortak ayar; evrenin 13 enstrümanının hepsinde aynı anda koşar, işlemler TEK
kasada birleşir. Mevcut parçalar yeniden kullanılır: wf_tarama (aday listesi, veri, maliyet, pencereler, PF(R)),
secim.yeniden_oyna (tek kasa, sert limitler), saglamlik (bootstrap, DSR, komşu parametre, rastgele işlem), wf_portfoy
(analiz başlangıcı).

AŞAMALAR (CLI alt komutları): ham -> wf -> saglamlik -> secim -> kilit -> ozet
  1. ham: her (strateji, tf, sembol) için TÜM adaylar kilit ÖNCESİ tüm veride bir kez koşulur (kilit_ac YOK);
     işlemler sonuclar/evren/ham/<strateji>--<tf>--<sembol>.parquet (+ .json yan dosya: aday etiketleri, koşu/hata sayısı,
     veri aralığı). Yan dosya en son yazılır = "bitti" işareti; biten atlanır (devam ettirilebilir). Hatalar yan dosyada.
  2. wf: pencere başına ayar, EVREN TOPLAMI PF(R) ile (eğitim: girişi pencerede, kapanışı pencere bitişinden önce/eşit
     olan işlemler; 13 enstrümanın toplamı; asgari eğitim işlemi evren toplamında swing 30, diğer 60); eşitlikte daha
     çok işlem, sonra aday sırası. OOS = seçilen ayarın girişi test penceresinde olan tüm işlemleri. Birleştirme: aynı
     enstrümanda önceki pencerenin işlemi hâlâ açıkken başlayan işlem atılır (tek pozisyon/enstrüman; sayısı raporlanır),
     sonra secim.yeniden_oyna (işlem %1, toplam stop riski %5, 3x, günlük %3, kill %20; sıra = giriş zamanı, eşitlikte
     evren sırası).
  3. ölçütler: ON_KAYIT geçme ölçütleri 1 ve 2.
  4. saglamlik (yalnız 1 ve 2'yi geçenlere): K1 maliyet x2 (ham koşu x2 + aynı evren WF), K2 rastgele giriş, K3 blok
     bootstrap, K4 komşu ayarlar. DSR yalnız raporlanır.
  5. secim: stil başına <= 3.
  6. kilit: bilgi amaçlı; seçimde kullanılmaz.

BELİRSİZ NOKTALARDA KOŞUDAN ÖNCE VERİLEN KARARLAR (sonuca bakılarak değiştirilmez)
  K-A  Scalp zaman dilimleri ON_KAYIT'a uygun 5m/15m (karar 11'deki "yalnız >=15m" yerine ön kayıt geçerli kabul edildi).
       Daytrade 30m/1h, swing 4h/1d. wf_tarama'daki STRATEJI_TF geçersiz kılması (KGT: 30m/1h) aynen uygulanır.
  K-B  Verisi olmayan enstrüman o tf'de dışarıda kalır (WTI/COPPER'in yalnız 1h dosyası var: 30m ve altı tf'lerde
       dışarıda). Kalan enstrüman sayısı satıra yazılır.
  K-C  Analiz başlangıcı = o tf'de verisi OLAN enstrümanların >= %75'inin verisinin başladığı gün
       (wf_portfoy.analiz_baslangici, MIN_KAPSAMA). Bitiş = kilit öncesi son mum.
  K-D  Kaba eleme YAPILMADI (karar 19: erken eleme yok). Tüm (strateji, tf) kombinasyonları WF'ye girdi.
  K-E  Ölçüt 1'in PF'si, en iyi %5 hariç PF'si ve işlem sayısı tek kasada KABUL EDİLEN işlemlerin R değerlerinden
       (PF(R)); net getiri, günlük Sharpe (365 gün yıllıklama, OOS aralığındaki tüm UTC günleri, gerçekleşmiş özsermaye)
       ve max düşüş yeniden oynatmanın günlük gerçekleşmiş özsermaye eğrisinden. Kasa PF'si (pnl tabanlı) yalnız bilgi.
  K-F  Genişlik: enstrüman/sınıf neti = yeniden oynatmada KABUL edilen işlemlerin gerçekleşen pnl toplamı (özsermaye
       birimi). "Enstrümanların >= %50'si net>0" paydası = OOS'ta kabul edilmiş işlemi olan enstrüman sayısı. Tek enstrüman
       payı = en büyük enstrüman neti / toplam net (toplam net <= 0 ise ölçüt zaten başarısız). Sınıf: kripto (BTC, ETH,
       SOL), hisse (7), emtia (XAU, WTI, COPPER); "en az ikisinde net>0" = işlemi olan sınıflardan >= 2'sinin neti > 0.
  K-G  K1: maliyet x2 ile ham koşu + aynı WF + aynı yeniden oynatma; K-E'deki PF >= 1.05. K3: kabul edilen işlemlerin R
       dizisi çıkış sırasıyla, blok 20, 2000 örnek, %90 aralık alt sınırı > 1. K4: en sık seçilen ayarın (eşitlikte ilk)
       saglamlik.komsu_parametreler komşuları, her biri 13 enstrümanda tüm kilit öncesi veride koşulur, evren toplamı
       PF(R) > 1 olanların oranı >= %60 (PF OOS aralığındaki girişlerle; komşu yoksa kapı geçilmez).
  K-H  K2: her OOS işlemi için (enstrüman, yön, tutma süresi H mum, stop/ATR14 katı) korunur; giriş zamanı AYNI test
       penceresi içinden o enstrümanın mumlarından tekdüze çekilir ("zaman" korunur = pencere). Sınama istatistiği evren
       OOS toplam R (birleştirilmiş, yeniden oynatma öncesi, çakışma süzgecinden sonra). 500 simülasyon,
       p = (1 + #{sim >= gerçek}) / 501. Maliyet saglamlik.rastgele_giris ile aynı (taker + kayma).
  K-I  Skor = OOS Sharpe x (1 - K2 p). Korelasyon: kabul edilen işlemlerin R x %1'inin işlem süresince yayılmış günlük
       getirisi (secim.gunluk_getiri 'yay'), OOS aralıklarının kesişimi; < 250 ortak gün ise ölçülemedi = geçer.
       Yönlü örtüşme süzgeci ON_KAYIT'ta yok, uygulanmaz. Seçim açgözlü (secim.acgozlu_sec).
  K-J  DSR toplam deneme sayısıyla: deneme_kaydi.jsonl toplam koşu + 787 (Haiku Ar-Ge); ayrıca (strateji, tf) kombinasyon
       sayısıyla. Yalnız rapor.
  K-K  Kilitli dönem bilgisi: ayar, kilit başlangıcında biten son eğitim penceresinden (aynı evren toplamı PF(R) kuralı)
       seçilir; kilitli dönemde değiştirilmeden kilit açılarak koşulur; yalnızca kilit sonrası girişler sayılır.
  K-M  GÜNCELLEME 1 (ON_KAYIT, kullanıcı): swing/daytrade evreni 36 enstrüman (13 kripto, 18 hisse, 5 emtia; XMR/LEO
       Binance perp'i yok, dışarıda), scalp evreni 4 (DK_SPX, DK_XAU, DK_WTI, BTCUSDT). Ham koşu enstrüman bazlıdır ve
       evrenden bağımsızdır (eski 13'lükteki koşular yeniden kullanılır). Verisi henüz inmemiş (sembol, tf) için yan dosya
       YAZILMAZ (bekliyor); WF yalnız evrenin tüm ham koşuları bitince çalışır; ham --kesin ile hâlâ verisi olmayanlar
       "dışarıda" olarak mühürlenir ve raporlanır. SPX hisse sınıfı sayılır. Yeni enstrümanların sembol kuralları
       (tick/step) yaklaşık Binance/Dukascopy varsayımıdır (kurallari_tamamla).
  K-N  GÜNCELLEME 2: BIST (13 hisse) swing/daytrade evrenine, BIST_XU030 scalp evrenine eklendi (evren 49 / 5); "bist" dördüncü
       varlık sınıfı (genişlik: kripto/hisse/emtia/bist, en az ikisinde net>0). Bir enstrümanın o tf'de verisi eğitim + test
       penceresi uzunluğundan kısaysa (WF için yeterli geçmiş yok) o (strateji, tf)'de dışarıda kalır ve "kisa_gecmis"
       sütununa yazılır; analiz başlangıcı kalan enstrümanlar üzerinden hesaplanır.
  K-L  Hatalı (aday, sembol) koşusu o ayarın o sembolde işlemsiz kalması demektir (funding'li strateji DK sembolünde
       FundingYokHatasi verir); sayılar satırlara yazılır.

  K-P  GÜNCELLEME 4: değerlendirme strateji düzeyindedir (enstrüman sıralaması/seçimi yok). Sağlamlık, WF'yi geçenlere ve
       "yakın" olanlara (WF'de en çok bir ölçüt kaçıran ve kaçırdığı ölçüt PF>=1.1, Sharpe>=0.4, düşüş<=%25 içinde) koşulur.
       "İyi" = tüm WF ölçütleri + K1-K4. "İyiye yakın" = iyi değil ve (WF'de başarısız ölçüt + başarısız K kapısı) <= 1.
       İki liste de stil bazında skora (Sharpe x (1 - K2 p)) göre sıralanır: iyi_liste.csv, iyiye_yakin_liste.csv.
       Stil başına <= 3 seçim (secim.csv) yalnız "iyi"lerden, korelasyon süzgeciyle yapılır.
  K-O  GÜNCELLEME 3: dönem etiketi. "2020_bugun" (asıl koşu): veri 2020-01-01'den veri sonuna, kilit_ac=True + gerekçe
       ("karar 27 evren testi 2020→bugün (kullanıcı kararı)"; her okuma kilit_acilis.jsonl'a yazılır), kilit bilgisi aşaması
       yok. "kilit_oncesi": ilk tasarım (kilit kapalı), çıktılar sonuclar/evren/kilit_oncesi/ (yalnız ara/deneme).
       Portföy (hedef-ağırlık) stratejileri `portfoy` aşamasıyla aynı evren ve dönemde wf_portfoy yolundan, karar 24 ölçütleriyle.

Kilit (karar 20): "kilit_oncesi" döneminde ham/wf/saglamlik kilit_ac'sız okur; "2020_bugun" döneminde kilit_ac=True (K-O).
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import multiprocessing as mp
import time
import zlib
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from motor.arastirma import saglamlik, secim, tarama, wf_portfoy, wf_tarama
from motor.backtest import deneme_kaydi
from motor.backtest.motor import backtest
from motor.backtest.walk_forward import pencereler_uret
from motor.strateji import funding, kayit
from motor.strateji import gostergeler as gst
from motor.veri import depo, kilit
from motor.veri.yeniden_ornekle import tf_mumlari

KOK = Path(__file__).resolve().parents[2]
CIKTI = KOK / "sonuclar" / "evren"

# GÜNCELLEME 1 (ON_KAYIT, kullanıcı): swing/daytrade evreni 5 emtia + 18 hisse + 13 kripto; scalp evreni 4 enstrüman.
# XMR/LEO Binance USDⓈ-M perp'i olmadığı için dışarıda (raporlanır).
KRIPTO = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "SOLUSDT", "TRXUSDT", "ZECUSDT", "HYPEUSDT", "DOGEUSDT",
          "LINKUSDT", "ADAUSDT", "XLMUSDT", "BCHUSDT")
HISSE = tuple("DK_" + t for t in ("AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "LLY", "WMT", "JPM",
                                   "V", "MU", "AMD", "XOM", "JNJ", "MA", "ABBV"))
EMTIA = ("DK_XAU", "DK_XAG", "DK_WTI", "DK_COPPER", "DK_NATGAS")
BIST = tuple("BIST_" + t for t in ("AKBNK", "ASELS", "ASTOR", "BIMAS", "EKGYO", "EREGL", "FROTO", "KCHOL", "SISE",
                                    "TCELL", "THYAO", "TRALT", "TUPRS"))                  # GÜNCELLEME 2
EVREN_GENEL = KRIPTO + HISSE + EMTIA + BIST                           # swing + daytrade (49)
EVREN_SCALP = ("DK_SPX", "DK_XAU", "DK_WTI", "BTCUSDT", "BIST_XU030")
EVREN_STIL = {"swing": EVREN_GENEL, "daytrade": EVREN_GENEL, "scalp": EVREN_SCALP}
EVREN = EVREN_GENEL
DISARIDA_KRIPTO = ("XMRUSDT", "LEOUSDT")
SINIF = {**{s: "kripto" for s in KRIPTO}, **{s: "hisse" for s in HISSE}, "DK_SPX": "hisse",
         **{s: "emtia" for s in EMTIA}, **{s: "bist" for s in BIST}, "BIST_XU030": "bist"}


_EVREN_OVR: dict = {}            # yalnız deneme/test: {stil: evren}; üretim koşusunda BOŞ


def evren_stil(stil: str) -> tuple:
    return _EVREN_OVR.get(stil) or EVREN_STIL[stil]


def kurallari_tamamla():
    """Yeni enstrümanların sembol kuralları (VARSAYIM: yaklaşık Binance filtreleri; tick/step yalnız adet yuvarlaması
    için, sonuca etkisi küçük). Mevcut kurallara dokunulmaz."""
    from motor.backtest.motor import SembolKurallari as SK
    adim = {"BNBUSDT": (0.01, 0.01), "XRPUSDT": (0.0001, 0.1), "TRXUSDT": (0.00001, 1.0), "ZECUSDT": (0.01, 0.001),
            "HYPEUSDT": (0.0001, 0.01), "DOGEUSDT": (0.00001, 1.0), "LINKUSDT": (0.001, 0.01),
            "ADAUSDT": (0.0001, 1.0), "XLMUSDT": (0.00001, 1.0), "BCHUSDT": (0.01, 0.001)}
    for sm, (tick, step) in adim.items():
        tarama.SEMBOL_KURALLARI.setdefault(sm, SK(tick_size=tick, step_size=step, min_qty=step, min_notional=5.0))
    for sm in HISSE:
        tarama.SEMBOL_KURALLARI.setdefault(sm, SK(tick_size=0.01, step_size=0.01, min_qty=0.01, min_notional=5.0))
    for sm in BIST + ("BIST_XU030",):
        tarama.SEMBOL_KURALLARI.setdefault(sm, SK(tick_size=0.01, step_size=1.0, min_qty=1.0, min_notional=5.0))
    tarama.SEMBOL_KURALLARI.setdefault("DK_XAG", SK(tick_size=0.001, step_size=0.01, min_qty=0.01, min_notional=5.0))
    tarama.SEMBOL_KURALLARI.setdefault("DK_NATGAS", SK(tick_size=0.001, step_size=1.0, min_qty=1.0, min_notional=5.0))
    tarama.SEMBOL_KURALLARI.setdefault("DK_SPX", SK(tick_size=0.01, step_size=0.01, min_qty=0.01, min_notional=5.0))


kurallari_tamamla()
STIL_TF = {"swing": ("4h", "1d"), "daytrade": ("30m", "1h"), "scalp": ("5m", "15m")}
MIN_ISLEM_EVREN = {"swing": 30, "daytrade": 60, "scalp": 60}
PENCERE_GUN = wf_tarama.PENCERE_GUN
SINIRLAR = secim.OynatmaAyari()                 # %1 işlem, %5 toplam stop riski, 3x, günlük %3, kill %20 (karar 14, 25)
HAIKU_DENEME = 787

# ON_KAYIT geçme ölçütleri
OLCUT = {"min_pf": 1.2, "min_islem": 100, "min_pf_en_iyi5_haric": 0.9, "min_sharpe": 0.5, "max_dusus": 0.20,
         "min_kar_enstruman_orani": 0.5, "max_tek_enstruman_pay": 0.40, "min_kar_sinif": 2,
         "k1_pf": 1.05, "k2_p": 0.05, "k3_alt": 1.0, "k4_oran": 0.60}
YAKIN_OLCUT = {**OLCUT, "min_pf": 1.1, "min_sharpe": 0.4, "max_dusus": 0.25}       # GÜNCELLEME 4: kıl payı eşikleri
N_SIM = 500
BOOT_BLOK, N_BOOT = saglamlik.BLOK, saglamlik.N_BOOT


# GÜNCELLEME 3 (ON_KAYIT): iki dönem etiketi. "kilit_oncesi": ilk tasarım (< 2025-11-01, kilit kapalı; ara/deneme çıktıları
# sonuclar/evren/kilit_oncesi/). "2020_bugun": test dönemi 2020-01-01 -> veri sonu, kilit ayrımı YOK (kilit_ac=True,
# gerekçe günlüğe yazılır); asıl çıktılar sonuclar/evren/. Ham koşu bu dönemde 2020-01-01'den başlar (öncesi kesilir).
DONEMLER = {"kilit_oncesi": {"bas": None, "kilit_ac": False}, "2020_bugun": {"bas": "2020-01-01", "kilit_ac": True}}
KILIT_GEREKCE_2020 = "karar 27 evren testi 2020→bugün (kullanıcı kararı)"
_CFG = {"veri_dizini": None, "donem": "kilit_oncesi"}
_ONB: dict = {}


def donem_kok(donem: str) -> Path:
    return CIKTI / "kilit_oncesi" if donem == "kilit_oncesi" else CIKTI


def veri_ayarla(veri_dizini=None, donem: str = "kilit_oncesi"):
    if donem not in DONEMLER:
        raise ValueError(f"bilinmeyen dönem: {donem}")
    _CFG.update(veri_dizini=veri_dizini, donem=donem)
    _ONB.clear()


def _veri(sembol: str, tf: str):
    """(mumlar, funding) — dönem ayarına göre. Kilit yalnız 2020_bugun döneminde ve gerekçeyle açılır."""
    k = (sembol, tf, _CFG["donem"], str(_CFG["veri_dizini"]))
    if k not in _ONB:
        if len(_ONB) >= 6:
            _ONB.clear()
        d = DONEMLER[_CFG["donem"]]
        kl = {"kilit_ac": d["kilit_ac"], "gerekce": KILIT_GEREKCE_2020 if d["kilit_ac"] else None}
        mumlar = tf_mumlari(sembol, tf, d["bas"], None, dizin=_CFG["veri_dizini"], **kl)
        try:
            fund = depo.funding_oku(sembol, d["bas"], None, dizin=_CFG["veri_dizini"], **kl)
        except FileNotFoundError:
            fund = None
        _ONB[k] = (mumlar, fund)
    return _ONB[k]


def stil_tf_listesi(ad: str) -> tuple:
    return tarama.STRATEJI_TF.get(ad) or STIL_TF[kayit.al(ad).stil]


# ============================================================================ 1. ham koşu
def ham_yolu(dizin: Path, ad: str, tf: str, sembol: str) -> Path:
    return Path(dizin) / f"{ad}--{tf}--{sembol}.parquet"


def islem_ozet(d: pd.DataFrame, ayar_no: int) -> pd.DataFrame:
    """Motor işlem tablosu -> saklanan ince biçim. sf = risk$/nominal (secim.islem_tablosu_hazirla ile aynı kural:
    |r| < 0.05 satırları komşudan doldurulur), stop_mesafe = risk$/miktar (K2 için; küçük |r|'de NaN)."""
    d = d.sort_values("giris_zamani", kind="stable").reset_index(drop=True)
    r = d["r"].to_numpy(dtype=float)
    miktar = d["miktar"].to_numpy(dtype=float)
    nominal = miktar * d["giris_fiyati"].to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        risk_usd = np.where(np.abs(r) >= 0.05, np.abs(d["net_pnl"].to_numpy(dtype=float) / r), np.nan)
        sf = risk_usd / nominal
        sm = risk_usd / miktar
    sf = pd.Series(sf).ffill().bfill().fillna(0.05).clip(lower=1e-4).to_numpy()
    return pd.DataFrame({
        "ayar_no": np.full(len(d), ayar_no, dtype=np.int16),
        "giris_zamani": pd.DatetimeIndex(d["giris_zamani"]).as_unit("ns"),
        "cikis_zamani": pd.DatetimeIndex(d["cikis_zamani"]).as_unit("ns"),
        "yon": d["yon"].to_numpy(dtype=np.int8), "r": r.astype(np.float32),
        "sf": sf.astype(np.float32), "stop_mesafe": sm.astype(np.float32)})


_BOSLUK = pd.DataFrame({"ayar_no": np.array([], dtype=np.int16),
                        "giris_zamani": pd.DatetimeIndex([], tz="UTC").as_unit("ns"),
                        "cikis_zamani": pd.DatetimeIndex([], tz="UTC").as_unit("ns"),
                        "yon": np.array([], dtype=np.int8), "r": np.array([], dtype=np.float32),
                        "sf": np.array([], dtype=np.float32), "stop_mesafe": np.array([], dtype=np.float32)})


def _yaz_atomik(df: pd.DataFrame, yol: Path):
    gecici = yol.with_suffix(".tmp")
    df.to_parquet(gecici, index=False)
    gecici.replace(yol)


def ham_gorev(ad: str, tf: str, sembol: str, carpan: float = 1.0, dizin: Optional[Path] = None,
              yeniden: bool = False, kesin: bool = True) -> dict:
    """Tek (strateji, tf, sembol): tüm adayları koş, işlemleri yaz. Yan dosya (.json) en son yazılır. Biten atlanır.
    veri_ayarla(...) ile dönem/veri dizini kurulu olmalı."""
    dizin = Path(dizin) if dizin is not None else CIKTI / "ham"
    dizin.mkdir(parents=True, exist_ok=True)
    yol = ham_yolu(dizin, ad, tf, sembol)
    yan = yol.with_suffix(".json")
    if yan.exists() and not yeniden:
        return {"atlandi": True}
    t0 = time.perf_counter()
    meta = {"strateji": ad, "tf": tf, "sembol": sembol, "carpan": carpan, "veri_yok": False, "hata": ""}
    try:
        mumlar, fund = _veri(sembol, tf)
    except (FileNotFoundError, ValueError) as e:          # K-B: bu tf'de verisi olmayan enstrüman dışarıda
        meta.update(veri_yok=True, hata=f"{type(e).__name__}: {e}"[:200])
        if not kesin:                                     # veri henüz inmemiş olabilir: yan dosya YAZMA, bekle
            return {**meta, "veri_bekliyor": True}
        yan.write_text(json.dumps(meta, ensure_ascii=False))
        return meta
    except Exception as e:  # noqa: BLE001
        meta.update(hata=f"{type(e).__name__}: {e}"[:200])
        yan.write_text(json.dumps(meta, ensure_ascii=False))
        return meta
    if (not DONEMLER[_CFG["donem"]]["kilit_ac"]) and len(mumlar) and mumlar.index.max() >= kilit.KILIT_BASLANGIC:
        raise RuntimeError("ham koşu kilitli döneme girdi")           # asla olmamalı
    adaylar, kurma_hatalari = wf_tarama.aday_listesi(ad, True)
    kurallar = tarama.SEMBOL_KURALLARI.get(sembol, tarama.VARSAYILAN_KURAL)
    ay = wf_tarama.maliyet_ayarlari(kurallar, carpan)
    parcalar, hatalar, n_kosu = [], list(kurma_hatalari), 0
    for no, (etiket, s) in enumerate(adaylar):
        try:
            r = backtest(funding.stratejiye_hazirla(s, mumlar, fund, sembol, tf), s, ay, fund)
        except Exception as e:  # noqa: BLE001  (K-L)
            hatalar.append((etiket, f"{type(e).__name__}: {e}"))
            continue
        n_kosu += 1
        if len(r.islemler):
            parcalar.append(islem_ozet(r.islemler, no))
    tum = pd.concat(parcalar, ignore_index=True) if parcalar else _BOSLUK
    _yaz_atomik(tum, yol)
    meta.update({"adaylar": [e for e, _ in adaylar], "n_aday": len(adaylar) + len(kurma_hatalari), "n_kosu": n_kosu,
                 "n_hata": len(hatalar), "hata_ornegi": hatalar[0][1][:160] if hatalar else "",
                 "hata_etiket": hatalar[0][0][:80] if hatalar else "",
                 "n_islem": int(len(tum)), "veri_bas": str(mumlar.index[0]), "veri_bit": str(mumlar.index[-1]),
                 "sure_sn": round(time.perf_counter() - t0, 2)})
    yan.write_text(json.dumps(meta, ensure_ascii=False))
    return meta


_SON = {"zaman": None}


def _isci_ham(ayar: dict):
    veri_ayarla(ayar.get("veri_dizini"), ayar.get("donem", "kilit_oncesi"))
    _SON["zaman"] = ayar.get("son")


def _ham_isci(g: dict):
    if _SON["zaman"] is not None and time.time() > _SON["zaman"]:
        return {"ertelendi": True, **g}
    try:
        return {**g, **ham_gorev(g["strateji"], g["tf"], g["sembol"], g.get("carpan", 1.0), g.get("dizin"),
                                                  kesin=g.get("kesin", False))}
    except Exception as e:  # noqa: BLE001
        return {**g, "hata": f"{type(e).__name__}: {e}"}


def ham_gorevleri(stiller=("swing", "daytrade", "scalp"), stratejiler=None, tfler=None, evren=None) -> list:
    stratejiler = list(stratejiler) if stratejiler else list(kayit.tum_stratejiler())
    out = []
    for ad in stratejiler:
        stil = kayit.al(ad).stil
        if stil not in stiller:
            continue
        for tf in stil_tf_listesi(ad):
            if tfler and tf not in tfler:
                continue
            for sembol in (evren or evren_stil(stil)):
                out.append({"strateji": ad, "stil": stil, "tf": tf, "sembol": sembol})
    out.sort(key=lambda g: (g["stil"] != "swing", g["stil"] != "daytrade", g["tf"], g["sembol"], g["strateji"]))
    return out


def havuz_calistir(isci, gorevler: list, surec: int, baslat, ayar: dict, butce_sn: Optional[float], ilerleme=True,
                   etiket="") -> list:
    """Süreç havuzu; bütçe dolunca yeni görev başlatılmaz (işçi 'ertelendi' döner). Sonuçlar sırayla toplanır."""
    ayar = {**ayar, "son": (time.time() + butce_sn) if butce_sn else None}
    sonuc, t0 = [], time.perf_counter()
    if surec <= 1:
        baslat(ayar)
        it = (isci(g) for g in gorevler)
        havuz = None
    else:
        havuz = mp.get_context("fork").Pool(surec, baslat, (ayar,))
        it = havuz.imap_unordered(isci, gorevler, chunksize=1)
    try:
        for s in it:
            sonuc.append(s)
            if ilerleme and len(sonuc) % 25 == 0:
                print(f"[{etiket}] {len(sonuc)}/{len(gorevler)}  {time.perf_counter() - t0:.0f} sn", flush=True)
    finally:
        if havuz is not None:
            havuz.close()
            havuz.join()
    return sonuc


def ham_tara(stiller=("swing", "daytrade", "scalp"), stratejiler=None, tfler=None, surec: int = 4,
             butce_sn: Optional[float] = None, dizin: Optional[Path] = None, veri_dizini=None, carpan: float = 1.0,
             donem: str = "kilit_oncesi",
             hatalari_yeniden: bool = False, ilerleme: bool = True, evren=None, kesin: bool = False) -> dict:
    dizin = Path(dizin) if dizin is not None else donem_kok(donem) / "ham"
    dizin.mkdir(parents=True, exist_ok=True)
    tum = ham_gorevleri(stiller, stratejiler, tfler)
    if evren:
        tum = [g for g in tum if g["sembol"] in set(evren)]
    kalan = []
    for g in tum:
        yan = ham_yolu(dizin, g["strateji"], g["tf"], g["sembol"]).with_suffix(".json")
        if yan.exists():
            if hatalari_yeniden and json.loads(yan.read_text()).get("hata") and not json.loads(yan.read_text()).get("veri_yok"):
                yan.unlink()
            else:
                continue
        kalan.append({**g, "carpan": carpan, "dizin": dizin, "kesin": kesin})
    if ilerleme:
        print(f"[ham] toplam {len(tum)} görev, kalan {len(kalan)}", flush=True)
    sonuc = havuz_calistir(_ham_isci, kalan, surec, _isci_ham, {"veri_dizini": veri_dizini, "donem": donem}, butce_sn, ilerleme, "ham")
    ert = sum(1 for s in sonuc if s.get("ertelendi"))
    hata = sum(1 for s in sonuc if s.get("hata") and not s.get("veri_yok") and not s.get("ertelendi"))
    return {"toplam": len(tum), "kalan_basta": len(kalan), "yapilan": len(sonuc) - ert, "ertelenen": ert, "hata": hata}


# ============================================================================ 2. evren walk-forward
class _Seri(wf_tarama.AdayIslemleri):
    """Bir (ayar, enstrüman) işlem listesi; eğitim penceresi için (n, +R, -R)."""

    def nkz(self, bas, bit) -> tuple:
        i, j = self.aralik(bas, bit)
        j = max(i, min(j, int(self.cikis.searchsorted(bit, "right"))))
        return j - i, float(self._poz[j] - self._poz[i]), float(self._neg[j] - self._neg[i])


def seriler_kur(ham: dict) -> dict:
    """ham: {sembol: DataFrame(ayar_no, giris_zamani, cikis_zamani, r, ...)} -> {ayar_no: {sembol: _Seri}}."""
    nesne: dict = {}
    for s, df in ham.items():
        if df is None or not len(df):
            continue
        for no, g in df.groupby("ayar_no", sort=True):
            nesne.setdefault(int(no), {})[s] = _Seri(g.reset_index(drop=True))
    return nesne


def evren_secimi(nesne: dict, e0, e1, min_islem: int) -> Optional[tuple]:
    """Bir eğitim penceresinde ayar seçimi: evren toplamı PF(R). -> (ayar_no, pf, n) | None. YALNIZ [e0, e1) bilgisi."""
    en, en_anahtar = None, None
    for no in sorted(nesne):
        n = 0
        k = z = 0.0
        for sr in nesne[no].values():
            a, b, c = sr.nkz(e0, e1)
            n += a
            k += b
            z += c
        if n < min_islem:
            continue
        pf = k / z if z > 0 else (math.inf if k > 0 else math.nan)
        if math.isnan(pf):
            continue
        anahtar = (pf, n, -no)
        if en_anahtar is None or anahtar > en_anahtar:
            en, en_anahtar = no, anahtar
    return None if en is None else (en, en_anahtar[0], en_anahtar[1])


def evren_wf(ham: dict, pencereler: list, min_islem: int, sira: tuple = EVREN_GENEL) -> tuple:
    """-> (oos DataFrame [ham sütunları + sembol, pencere], secimler). Tek ortak ayar her enstrümanda aynı."""
    nesne = seriler_kur(ham)
    parcalar, secimler = [], []
    for w, (e0, e1, t0, t1) in enumerate(pencereler):
        sec = evren_secimi(nesne, e0, e1, min_islem)
        secimler.append({"pencere": w, "test_bas": str(t0), "test_bit": str(t1),
                         "secilen": None if sec is None else sec[0],
                         "egitim_pf": None if sec is None else sec[1], "egitim_islem": None if sec is None else sec[2]})
        if sec is None:
            continue
        for s in sira:
            sr = nesne[sec[0]].get(s)
            if sr is None:
                continue
            d = sr.dilim(t0, t1).copy()
            if len(d):
                d["sembol"] = s
                d["pencere"] = w
                parcalar.append(d)
    oos = pd.concat(parcalar, ignore_index=True) if parcalar else pd.DataFrame()
    return oos, secimler


def sembol_cakismasini_ele(oos: pd.DataFrame) -> tuple:
    """Aynı enstrümanda bir önceki KABUL edilen işlem hâlâ açıkken (giriş < önceki çıkış) başlayan işlemi at.
    Yalnız pencere sınırlarında (farklı ayarlar) olabilir. -> (süzülmüş DataFrame, atılan sayı)."""
    if not len(oos):
        return oos, 0
    d = oos.sort_values(["sembol", "giris_zamani"], kind="stable")
    tut = np.ones(len(d), dtype=bool)
    sem = d["sembol"].to_numpy()
    g = pd.DatetimeIndex(d["giris_zamani"]).asi8
    c = pd.DatetimeIndex(d["cikis_zamani"]).asi8
    son_cikis, onceki = None, None
    for i in range(len(d)):
        if sem[i] != onceki:
            onceki, son_cikis = sem[i], None
        if son_cikis is not None and g[i] < son_cikis:
            tut[i] = False
            continue
        son_cikis = c[i]
    return d[tut].reset_index(drop=True), int((~tut).sum())


def oynatma_tablosu(oos: pd.DataFrame, sira: tuple = EVREN_GENEL) -> pd.DataFrame:
    """Sıra: giriş zamanı, eşitlikte evren sırası (deterministik ret/kabul önceliği)."""
    ordn = {s: i for i, s in enumerate(sira)}
    t = pd.DataFrame({"kol": oos["sembol"].to_numpy(), "sembol": oos["sembol"].to_numpy(), "yon": oos["yon"].to_numpy(),
                      "giris": pd.DatetimeIndex(oos["giris_zamani"]), "cikis": pd.DatetimeIndex(oos["cikis_zamani"]),
                      "r": oos["r"].to_numpy(dtype=float), "sf": oos["sf"].to_numpy(dtype=float),
                      "stop_mesafe": oos["stop_mesafe"].to_numpy(dtype=float) if "stop_mesafe" in oos else np.nan})
    t["_o"] = t["sembol"].map(ordn).fillna(len(ordn)).to_numpy()
    t = t.sort_values(["giris", "_o"], kind="stable").drop(columns="_o").reset_index(drop=True)
    return t


def _pf(r) -> float:
    return wf_tarama.pf_hesapla(np.asarray(r, dtype=float))


def en_iyi5_haric_pf(r) -> float:
    r = np.asarray(r, dtype=float)
    if not len(r):
        return math.nan
    kes = max(1, math.ceil(0.05 * len(r)))
    return _pf(np.sort(r)[::-1][kes:])


def genislik(tablo: pd.DataFrame, kabul: list, islem_pnl: dict) -> dict:
    """Enstrüman/sınıf bazında kabul edilen işlem sayısı ve net (K-F)."""
    net, adet = {}, {}
    for i in kabul:
        s = tablo["sembol"].iat[i]
        p = islem_pnl.get(i)
        adet[s] = adet.get(s, 0) + 1
        net[s] = net.get(s, 0.0) + (p[1] if p else 0.0)
    kar = [s for s in net if net[s] > 0]
    toplam = sum(net.values())
    en_buyuk = max(net, key=lambda s: net[s]) if net else ""
    sinif_net: dict = {}
    for s, v in net.items():
        sinif_net[SINIF.get(s, "diger")] = sinif_net.get(SINIF.get(s, "diger"), 0.0) + v
    return {"n_enstruman_islemli": len(net), "n_enstruman_kar": len(kar),
            "enstruman_kar_orani": len(kar) / len(net) if net else math.nan,
            "tek_enstruman_pay": (net[en_buyuk] / toplam) if (net and toplam > 0) else math.nan,
            "en_buyuk_enstruman": en_buyuk, "sinif_net": sinif_net,
            "n_sinif_kar": sum(1 for v in sinif_net.values() if v > 0),
            "enstruman_net": {s: round(v, 6) for s, v in net.items()}, "enstruman_adet": adet}


def kasa_metrikleri(tablo: pd.DataFrame, oos_bas, oos_bit, ayar=None) -> dict:
    """Tek kasa yeniden oynatma + metrikler (K-E, K-F). tablo: oynatma_tablosu çıktısı."""
    if not len(tablo):
        return {"islem_sayisi": 0, "n_oos_ham": 0, "kabul": [], "pnl": {}}
    bit = max(pd.Timestamp(oos_bit), pd.DatetimeIndex(tablo["cikis"]).max())
    res = secim.yeniden_oyna(tablo, ayar or SINIRLAR, bas=oos_bas, bit=bit)
    kabul = list(res["kabul"])
    r = tablo["r"].to_numpy(dtype=float)[kabul]
    gun = res["gunluk"]
    getiri = res["getiri"].to_numpy(dtype=float)
    std = getiri.std(ddof=1) if len(getiri) > 1 else np.nan
    ozs = np.r_[1.0, gun.to_numpy(dtype=float)]
    zirve = np.maximum.accumulate(ozs)
    pnl_kabul = [res["islem_pnl"][i][1] for i in kabul if i in res["islem_pnl"]]
    pk = np.array(pnl_kabul, dtype=float)
    z = -pk[pk < 0].sum()
    m = {"n_oos_ham": int(len(tablo)), "islem_sayisi": int(len(kabul)),
         "net_getiri": float(res["nakit_son"] - 1.0),
         "profit_factor": _pf(r) if len(r) else math.nan,
         "pf_en_iyi5_haric": en_iyi5_haric_pf(r),
         "sharpe": float(getiri.mean() / std * np.sqrt(365)) if std and std > 0 else math.nan,
         "max_dusus": float(((zirve - ozs) / zirve).max()),
         "pf_kasa": float(pk[pk > 0].sum() / z) if z > 0 else math.nan,
         "toplam_r": float(r.sum()) if len(r) else 0.0,
         "red_toplam_risk": res["sayac"]["red_toplam_risk"], "red_kaldirac": res["sayac"]["red_kaldirac"],
         "red_gunluk": res["sayac"]["red_gunluk"], "red_kill": res["sayac"]["red_kill"],
         "kirpilan": res["sayac"]["kirpilan"], "gunluk_limit_olayi": res["sayac"]["gunluk_limit_olayi"],
         "kill_olayi": res["sayac"]["kill_olayi"], "zorla_kapanan": res["sayac"]["zorla_kapanan"]}
    m.update(genislik(tablo, kabul, res["islem_pnl"]))
    m["kabul"] = kabul
    m["pnl"] = {i: res["islem_pnl"][i][1] for i in kabul if i in res["islem_pnl"]}
    m["getiri_serisi"] = res["getiri"]
    return m


def _yok(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def olcutleri_degerlendir(m: dict, olcut: dict = OLCUT) -> dict:
    """ON_KAYIT ölçüt 1 ve 2. -> {'g1','g2','gecti','nedenler': [...], 'basarisiz_sayi'}. NaN = geçmez."""
    n1, n2 = [], []

    def k(liste, ad, v, ok, metin):
        if _yok(v):
            liste.append(f"{ad} hesaplanamadı")
        elif not ok(v):
            liste.append(metin.format(v))

    k(n1, "net", m.get("net_getiri"), lambda v: v > 0, "net {:.3f} <= 0")
    k(n1, "pf", m.get("profit_factor"), lambda v: v >= olcut["min_pf"], "PF {:.2f} < " + str(olcut["min_pf"]))
    k(n1, "islem", m.get("islem_sayisi"), lambda v: v >= olcut["min_islem"], "işlem {} < " + str(olcut["min_islem"]))
    k(n1, "pf5", m.get("pf_en_iyi5_haric"), lambda v: v >= olcut["min_pf_en_iyi5_haric"],
      "en iyi %5 hariç PF {:.2f} < " + str(olcut["min_pf_en_iyi5_haric"]))
    k(n1, "sharpe", m.get("sharpe"), lambda v: v >= olcut["min_sharpe"], "Sharpe {:.2f} < " + str(olcut["min_sharpe"]))
    k(n1, "dusus", m.get("max_dusus"), lambda v: v <= olcut["max_dusus"], "düşüş {:.3f} > " + str(olcut["max_dusus"]))
    k(n2, "enstruman_orani", m.get("enstruman_kar_orani"), lambda v: v >= olcut["min_kar_enstruman_orani"],
      "kârlı enstrüman oranı {:.2f} < " + str(olcut["min_kar_enstruman_orani"]))
    k(n2, "tek_enstruman", m.get("tek_enstruman_pay"), lambda v: v <= olcut["max_tek_enstruman_pay"],
      "tek enstrüman payı {:.2f} > " + str(olcut["max_tek_enstruman_pay"]))
    k(n2, "sinif", m.get("n_sinif_kar"), lambda v: v >= olcut["min_kar_sinif"],
      "kârlı sınıf {} < " + str(olcut["min_kar_sinif"]))
    return {"g1": not n1, "g2": not n2, "gecti": not n1 and not n2, "nedenler": n1 + n2,
            "basarisiz_sayi": len(n1) + len(n2)}


def yakin_wf_mi(m: dict, ol: Optional[dict] = None) -> bool:
    """GÜNCELLEME 4 / K-P: WF ölçütlerinde en çok BİR ölçüt kaçar ve o kıl payı eşiklerini (PF >= 1.1, Sharpe >= 0.4,
    düşüş <= %25) geçer; yani gevşek eşiklerle hepsi geçer VE sıkı eşiklerde başarısız sayısı <= 1. Geçenler de dahildir."""
    ol = ol or olcutleri_degerlendir(m)
    return ol["basarisiz_sayi"] <= 1 and olcutleri_degerlendir(m, YAKIN_OLCUT)["gecti"]


def kapi_sayisi(kapi_basarisiz) -> int:
    return len([x for x in str(kapi_basarisiz or "").split(";") if x])


def listeler(wf: pd.DataFrame, sag: pd.DataFrame) -> tuple:
    """GÜNCELLEME 4. -> (iyi, iyiye_yakin) DataFrame'leri: stil bazında skora (Sharpe x (1 - K2 p)) göre sıralı.
    iyi = tüm WF ölçütleri + K1-K4. iyiye yakın = iyi değil ve (WF'de başarısız ölçüt sayısı + başarısız sağlamlık kapısı)
    <= 1, WF'deki kaçış kıl payı eşikleri içinde (K-P). Strateji düzeyi; enstrüman sıralaması yok."""
    if not len(sag):
        return pd.DataFrame(), pd.DataFrame()
    d = wf.merge(sag[["strateji", "tf", "saglam_mi", "kapi_basarisiz", "rnd_p", "m2_pf", "pf_boot_alt", "par_oran",
                      "hata"]].rename(columns={"hata": "sag_hata"}), on=["strateji", "tf"], how="inner")
    d = d[d["sag_hata"].fillna("") == ""].copy()
    d["kapi_sayisi"] = d["kapi_basarisiz"].map(kapi_sayisi)
    d["toplam_kacan"] = d["basarisiz_sayi"].fillna(99) + d["kapi_sayisi"]
    d["skor"] = d["sharpe"] * (1 - d["rnd_p"])
    iyi = d[(d["gecti"] == True) & (d["saglam_mi"] == True)]                          # noqa: E712
    yakin = d[(d["yakin_wf"] == True) & (d["toplam_kacan"] <= 1) & ~d.index.isin(iyi.index)]   # noqa: E712
    srt = lambda x: x.sort_values(["stil", "skor"], ascending=[True, False]).reset_index(drop=True)    # noqa: E731
    return srt(iyi), srt(yakin)


def ham_yukle(dizin: Path, ad: str, tf: str, evren=EVREN_GENEL) -> tuple:
    """-> (ham {sembol: df}, adaylar [etiket], bilgi). Bitmemiş (yan dosyası olmayan) görev varsa RuntimeError."""
    ham, bilgi = {}, {"disarida": [], "hatali_sembol": [], "n_kosu": 0, "n_aday": 0, "n_hata": 0, "adaylar": None,
                      "veri_bas": {}, "veri_bit": {}, "hata_ornegi": ""}
    for s in evren:
        yol = ham_yolu(dizin, ad, tf, s)
        yan = yol.with_suffix(".json")
        if not yan.exists():
            raise RuntimeError(f"ham koşu bitmemiş: {yan.name}")
        meta = json.loads(yan.read_text())
        if meta.get("veri_yok"):
            bilgi["disarida"].append(s)
            continue
        if meta.get("hata") and "adaylar" not in meta:
            bilgi["hatali_sembol"].append(s)
            continue
        ham[s] = pd.read_parquet(yol)
        bilgi["n_kosu"] += meta["n_kosu"]
        bilgi["n_aday"] = max(bilgi["n_aday"], meta["n_aday"])
        bilgi["n_hata"] += meta["n_hata"]
        bilgi["veri_bas"][s] = pd.Timestamp(meta["veri_bas"])
        bilgi["veri_bit"][s] = pd.Timestamp(meta["veri_bit"])
        if meta["hata_ornegi"] and not bilgi["hata_ornegi"]:
            bilgi["hata_ornegi"] = meta["hata_ornegi"]
        if bilgi["adaylar"] is None:
            bilgi["adaylar"] = meta["adaylar"]
    return ham, bilgi["adaylar"], bilgi


def analiz_araligi(bilgi: dict, stil: str, min_kapsama: float = wf_portfoy.MIN_KAPSAMA) -> tuple:
    """K-C. -> (analiz_bas, bitis, pencereler)."""
    veriler = {s: pd.DataFrame(index=pd.DatetimeIndex([t])) for s, t in bilgi["veri_bas"].items()}
    bas = wf_portfoy.analiz_baslangici(veriler, list(veriler), min_kapsama)
    bit = max(bilgi["veri_bit"].values()) + pd.Timedelta(1, "ns")
    egitim, test = PENCERE_GUN[stil]
    return bas, bit, pencereler_uret(bas, bit, egitim, test)


def evren_wf_kos(ad: str, tf: str, stil: str, dizin: Path, evren=None, pencere_gun: Optional[dict] = None,
                 min_islem: Optional[dict] = None, ayar=None) -> tuple:
    """Bir (strateji, tf) için tam evren WF + tek kasa + metrikler. -> (satır dict, oos DataFrame (kabul/pnl sütunlu))."""
    evren = evren or evren_stil(stil)
    ham, adaylar, bilgi = ham_yukle(dizin, ad, tf, evren)
    egitim_g, test_g = (pencere_gun or PENCERE_GUN)[stil]
    kisa = [s_ for s_ in list(ham) if (bilgi["veri_bit"][s_] - bilgi["veri_bas"][s_]) < pd.Timedelta(days=egitim_g + test_g)]
    for s_ in kisa:                                       # K-N: WF için yeterli geçmişi olmayan enstrüman dışarıda
        ham.pop(s_)
        bilgi["veri_bas"].pop(s_)
        bilgi["veri_bit"].pop(s_)
    satir = {"strateji": ad, "stil": stil, "tf": tf, "n_enstruman_evren": len(evren), "n_enstruman": len(ham),
             "kisa_gecmis": ",".join(kisa), "disarida": ",".join(bilgi["disarida"]),
             "hatali_sembol": ",".join(bilgi["hatali_sembol"]), "n_aday": bilgi["n_aday"], "n_kosu": bilgi["n_kosu"],
             "n_aday_hata": bilgi["n_hata"], "hata_ornegi": bilgi["hata_ornegi"], "hata": ""}
    if not ham:
        satir.update(gecti=False, nedenler="hiç enstrümanda ham sonuç yok")
        return satir, pd.DataFrame()
    if pencere_gun:
        egitim, test = pencere_gun[stil]
        bas = wf_portfoy.analiz_baslangici({s: pd.DataFrame(index=pd.DatetimeIndex([t])) for s, t in bilgi["veri_bas"].items()},
                                           list(ham), wf_portfoy.MIN_KAPSAMA)
        bit = max(bilgi["veri_bit"].values()) + pd.Timedelta(1, "ns")
        pencereler = pencereler_uret(bas, bit, egitim, test)
    else:
        bas, bit, pencereler = analiz_araligi(bilgi, stil)
    satir["analiz_bas"] = str(bas)
    satir["n_pencere"] = len(pencereler)
    if not pencereler:
        satir.update(gecti=False, nedenler="veri pencereye yetmiyor")
        return satir, pd.DataFrame()
    oos_bas, oos_bit = pencereler[0][2], pencereler[-1][3]
    mi = (min_islem or MIN_ISLEM_EVREN)[stil]
    oos, secimler = evren_wf(ham, pencereler, mi, evren)
    satir.update({"oos_bas": str(oos_bas), "oos_bit": str(oos_bit),
                  "n_islemli_pencere": sum(s["secilen"] is not None for s in secimler),
                  "secimler": json.dumps([{**s, "ayar": (adaylar[s["secilen"]] if s["secilen"] is not None else None)}
                                          for s in secimler], ensure_ascii=False, default=str)})
    secilenler = [s["secilen"] for s in secimler if s["secilen"] is not None]
    if secilenler:
        sc = pd.Series([adaylar[i] for i in secilenler]).value_counts()
        satir.update(n_farkli_ayar=int(len(sc)), en_sik_ayar=str(sc.index[0]), en_sik_pay=float(sc.iloc[0] / len(secilenler)),
                     en_sik_ayar_no=int(pd.Series(secilenler).value_counts().index[0]))
    if not len(oos):
        satir.update(gecti=False, nedenler="OOS işlemi yok", islem_sayisi=0)
        return satir, pd.DataFrame()
    oos, atilan = sembol_cakismasini_ele(oos)
    tablo = oynatma_tablosu(oos, evren)
    m = kasa_metrikleri(tablo, oos_bas, oos_bit, ayar)
    satir["cakisma_atilan"] = atilan
    kabul, pnl, seri = m.pop("kabul"), m.pop("pnl"), m.pop("getiri_serisi")
    for kx in ("sinif_net", "enstruman_net", "enstruman_adet"):
        satir[kx] = json.dumps(m.pop(kx), ensure_ascii=False)
    satir.update(m)
    for sn in ("kripto", "hisse", "emtia", "bist"):
        satir[f"net_{sn}"] = json.loads(satir["sinif_net"]).get(sn, math.nan)
    ol = olcutleri_degerlendir(m)
    satir.update(g1=ol["g1"], g2=ol["g2"], gecti=ol["gecti"], nedenler="; ".join(ol["nedenler"]),
                 basarisiz_sayi=ol["basarisiz_sayi"])
    satir["yakin_wf"] = bool(yakin_wf_mi(m, ol))
    # OOS işlemleri (kabul + pnl sütunlu) sonraki aşamalar için
    out = tablo.copy()
    out["kabul"] = False
    out.loc[kabul, "kabul"] = True
    out["pnl"] = np.nan
    for i, p in pnl.items():
        out.loc[i, "pnl"] = p
    out["oos_bas"] = str(oos_bas)
    out["oos_bit"] = str(oos_bit)
    return satir, out


# ---------------------------------------------------------------------------- wf aşaması
def _wf_isci(g: dict):
    if _SON["zaman"] is not None and time.time() > _SON["zaman"]:
        return {"ertelendi": True}
    t0 = time.perf_counter()
    try:
        satir, oos = evren_wf_kos(g["strateji"], g["tf"], g["stil"], g["ham"])
        if len(oos):
            yol = g["oos"] / f"{g['strateji']}--{g['tf']}.parquet"
            _yaz_atomik(oos, yol)
    except RuntimeError as e:
        if "bitmemiş" in str(e):
            return {"ertelendi": True, "neden": str(e)}
        satir = {"strateji": g["strateji"], "stil": g["stil"], "tf": g["tf"], "hata": f"RuntimeError: {e}", "gecti": False,
                 "nedenler": "hata"}
    except Exception as e:  # noqa: BLE001
        satir = {"strateji": g["strateji"], "stil": g["stil"], "tf": g["tf"], "hata": f"{type(e).__name__}: {e}"[:300],
                 "gecti": False, "nedenler": "hata"}
    satir["sure_sn"] = time.perf_counter() - t0
    return satir


def _csv_yaz(df: pd.DataFrame, yol: Path):
    _yaz_atomik(df, yol.with_suffix(".parquet"))
    df.to_csv(yol.with_suffix(".csv"), index=False)


def wf_asamasi(stiller=("swing", "daytrade", "scalp"), surec: int = 4, butce_sn: Optional[float] = None,
               cikti: Path = CIKTI, ilerleme: bool = True, hatalari_yeniden: bool = False,
               donem: str = "2020_bugun", stratejiler=None) -> dict:
    cikti = Path(cikti)
    (cikti / "oos").mkdir(parents=True, exist_ok=True)
    yol = cikti / "wf_evren.parquet"
    onceki = pd.read_parquet(yol) if yol.exists() else pd.DataFrame()
    if hatalari_yeniden and len(onceki):
        onceki = onceki[onceki["hata"].fillna("") == ""]
    bitmis = set(zip(onceki["strateji"], onceki["tf"])) if len(onceki) else set()
    kalan = []
    for g in ham_gorevleri(stiller, stratejiler):
        k = (g["strateji"], g["tf"])
        if k in bitmis or any(x["strateji"] == k[0] and x["tf"] == k[1] for x in kalan):
            continue
        kalan.append({"strateji": k[0], "stil": g["stil"], "tf": k[1], "ham": cikti / "ham", "oos": cikti / "oos"})
    if ilerleme:
        print(f"[wf] kalan {len(kalan)} kombinasyon", flush=True)
    sonuc = havuz_calistir(_wf_isci, kalan, surec, _isci_ham, {"veri_dizini": None, "donem": donem}, butce_sn, ilerleme, "wf")
    yeni = [s for s in sonuc if not s.get("ertelendi")]
    ert = len(sonuc) - len(yeni)
    if yeni:
        tum = pd.concat([onceki, pd.DataFrame(yeni)], ignore_index=True)
        _csv_yaz(tum, cikti / "wf_evren")
        for s in yeni:                        # deneme kaydı: yalnız YENİ biten, hatasız kombinasyonlar (çift sayma yok)
            if s.get("hata", "") == "" and s.get("n_kosu"):
                deneme_kaydi.kaydet(s["strateji"], "evren", s["tf"], s.get("n_aday", 0), s.get("n_pencere", 0), s["n_kosu"])
    return {"yeni": len(yeni), "ertelenen": ert, "gecen": int(sum(bool(s.get("gecti")) for s in yeni))}


# ============================================================================ 4. sağlamlık
def rastgele_evren(oos: pd.DataFrame, pencere_sinirlari: list, n_sim: int, seed: int, tf: str, veri_al,
                   atr_periyot: int = saglamlik.ATR_PERIYOT) -> dict:
    """K-H. oos: giris_zamani, cikis_zamani, yon, sembol, stop_mesafe (+ pencere). Her işlem için aynı enstrüman, yön, tutma
    süresi (mum), stop/ATR katı; giriş zamanı aynı test penceresinde rastgele. veri_al(sembol) -> (mumlar, MotorAyarlari).
    -> {'toplam_r': dizi(n_sim), 'n_gecersiz', 'n_islem'}"""
    rng = np.random.default_rng(seed)
    toplam = np.zeros(n_sim)
    gecersiz = n_islem = 0
    stop_med = float(np.nanmedian(oos["stop_mesafe"].to_numpy(dtype=float))) if len(oos) else math.nan
    for sembol, d in oos.groupby("sembol", sort=True):
        mumlar, ay = veri_al(sembol)
        idx = mumlar.index
        o, h = mumlar["acilis"].to_numpy(float), mumlar["yuksek"].to_numpy(float)
        l, c = mumlar["dusuk"].to_numpy(float), mumlar["kapanis"].to_numpy(float)
        atr = gst.atr(mumlar["yuksek"], mumlar["dusuk"], mumlar["kapanis"], atr_periyot).to_numpy(float)
        n = len(mumlar)
        aralik = pd.Series(idx).diff().median()
        gj = idx.get_indexer(pd.DatetimeIndex(d["giris_zamani"]))
        if (gj < 0).any():
            raise ValueError(f"{sembol}: OOS girişi mum indeksinde yok ({int((gj < 0).sum())}/{len(gj)})")
        hm = np.maximum(1, np.rint((pd.DatetimeIndex(d["cikis_zamani"]) - pd.DatetimeIndex(d["giris_zamani"])) / aralik)
                        ).astype(int)
        mesafe = d["stop_mesafe"].to_numpy(float)
        mesafe = np.where(np.isfinite(mesafe) & (mesafe > 0), mesafe, stop_med)
        a_ = atr[np.maximum(gj - 1, 0)]
        with np.errstate(divide="ignore", invalid="ignore"):
            mult = mesafe / a_
        gec = np.isfinite(mult) & (mult > 0)
        mult = np.where(gec, mult, np.median(mult[gec]) if gec.any() else 1.0)
        yon = d["yon"].to_numpy(int)
        w = d["pencere"].to_numpy(int)
        lo = np.empty(len(d), dtype=int)
        hi = np.empty(len(d), dtype=int)
        for k in range(len(d)):
            t0, t1 = pencere_sinirlari[w[k]]
            lo[k] = max(1, int(idx.searchsorted(t0, "left")))
            hi[k] = min(int(idx.searchsorted(t1, "left")), n - hm[k])
            if hi[k] <= lo[k]:                               # pencere sonunda yer yok: pencere içinde en geç olanı kullan
                hi[k] = lo[k] + 1
        kayma, skayma = ay.kayma_bps / 1e4, ay.stop_kayma_bps / 1e4
        taker = ay.komisyon_taker_yuzde / 100
        u = rng.random((n_sim, len(d), saglamlik.YENIDEN_CEKIM))
        n_islem += n_sim * len(d)
        for s in range(n_sim):
            top = 0.0
            for k in range(len(d)):
                for e in range(saglamlik.YENIDEN_CEKIM):
                    j = int(lo[k] + u[s, k, e] * (hi[k] - lo[k]))
                    j = min(max(j, 1), n - 2)
                    hk = min(int(hm[k]), n - 1 - j)
                    if not np.isfinite(atr[j - 1]):
                        continue
                    r = saglamlik._tek_islem_r(o, h, l, c, atr, j, int(yon[k]), hk, float(mult[k]), kayma, skayma, taker)
                    if r is not None:
                        top += r
                        break
                else:
                    gecersiz += 1
            toplam[s] += top
    return {"toplam_r": toplam, "n_gecersiz": gecersiz, "n_islem": n_islem}


def komsu_evren_pf(ad: str, etiket: str, tf: str, evren, oos_bas, oos_bit, carpan: float = 1.0) -> dict:
    """K4: en sık ayarın komşuları; her biri tüm enstrümanlarda kilit öncesi tüm veride koşulur, evren toplamı PF(R)
    (girişi [oos_bas, oos_bit) olan işlemler). veri_ayarla ile dönem kurulu olmalı."""
    s0 = saglamlik.ayar_coz(ad, etiket)
    komsular = saglamlik.komsu_parametreler(s0.parametreler, s0.parametre_izgarasi or {})

    def evren_pf(st):
        rs = []
        for sembol in evren:
            try:
                mumlar, fund = _veri(sembol, tf)
            except (FileNotFoundError, ValueError):
                continue
            ay = wf_tarama.maliyet_ayarlari(tarama.SEMBOL_KURALLARI.get(sembol, tarama.VARSAYILAN_KURAL), carpan)
            try:
                t = backtest(funding.stratejiye_hazirla(st, mumlar, fund, sembol, tf), st, ay, fund).islemler
            except Exception:  # noqa: BLE001  (K-L: o sembolde işlemsiz)
                continue
            if not len(t):
                continue
            g = pd.DatetimeIndex(t["giris_zamani"])
            t = t[(g >= oos_bas) & (g < oos_bit)]
            if len(t):
                rs.append(t["r"].to_numpy(float))
        return _pf(np.concatenate(rs)) if rs else math.nan

    merkez = evren_pf(s0)
    pfler, detay, hatalar = [], [], []
    for p, yon, v in komsular:
        try:
            pf = evren_pf(s0.yeni(**{p: v}))
        except ValueError as e:
            hatalar.append(f"{p}={v}: {e}"[:100])
            continue
        pfler.append(pf)
        detay.append(f"{p}{'+' if yon > 0 else '-'}={v}:{pf:.2f}")
    a = np.array(pfler, dtype=float)
    iyi = int((a > 1).sum()) if len(a) else 0
    return {"par_merkez_pf": merkez, "par_n_komsu": len(komsular), "par_n_gecerli": len(pfler), "par_n_pf_gt1": iyi,
            "par_oran": iyi / len(pfler) if pfler else math.nan,
            "par_min_pf": float(np.nanmin(a)) if len(a) and not np.all(np.isnan(a)) else math.nan,
            "par_hata": len(hatalar), "par_detay": " | ".join(detay)}


def saglamlik_oneri(satir: dict, olcut: dict = OLCUT) -> tuple:
    def gec(v, ok):
        return not _yok(v) and ok(v)
    k = {"K1_maliyet2_pf": gec(satir.get("m2_pf"), lambda v: v >= olcut["k1_pf"]),
         "K2_rastgele_p": gec(satir.get("rnd_p"), lambda v: v <= olcut["k2_p"]),
         "K3_boot_alt": gec(satir.get("pf_boot_alt"), lambda v: v > olcut["k3_alt"]),
         "K4_komsu_param": gec(satir.get("par_oran"), lambda v: v >= olcut["k4_oran"])}
    kaybeden = [a for a, ok in k.items() if not ok]
    return (not kaybeden), ";".join(kaybeden)


def _sag_isci(g: dict):
    if _SON["zaman"] is not None and time.time() > _SON["zaman"]:
        return {"ertelendi": True}
    t0 = time.perf_counter()
    satir = {"strateji": g["strateji"], "stil": g["stil"], "tf": g["tf"], "hata": ""}
    try:
        _sag_icerik(g, satir)
        satir["saglam_mi"], satir["kapi_basarisiz"] = saglamlik_oneri(satir)
    except Exception as e:  # noqa: BLE001
        satir["hata"] = f"{type(e).__name__}: {e}"[:300]
        satir["saglam_mi"], satir["kapi_basarisiz"] = False, "hata"
    satir["sure_sn"] = time.perf_counter() - t0
    return satir


def _sag_icerik(g: dict, satir: dict):
    cikti = g["cikti"]
    ad, tf, stil = g["strateji"], g["tf"], g["stil"]
    w = g["wf"]
    oos = pd.read_parquet(cikti / "oos" / f"{ad}--{tf}.parquet")
    oos_bas, oos_bit = pd.Timestamp(w["oos_bas"]), pd.Timestamp(w["oos_bit"])
    kabul = oos[oos["kabul"]].sort_values("cikis", kind="stable")
    rng_tohum = zlib.crc32(f"{ad}|{tf}|evren".encode()) ^ g["tohum"]
    satir.update({"wf_islem": int(w["islem_sayisi"]), "wf_pf": float(w["profit_factor"]), "wf_sharpe": float(w["sharpe"]),
                  "en_sik_ayar": w["en_sik_ayar"]})
    # K1: maliyet x2 — ham koşu x2 (ayrı dizin) + aynı evren WF + aynı yeniden oynatma
    m2_dizin = cikti / "ham_m2"
    for s in evren_stil(stil):
        ham_gorev(ad, tf, s, 2.0, m2_dizin, kesin=True)
    s2, oos2 = evren_wf_kos(ad, tf, stil, m2_dizin)
    satir.update({"m2_kill_olayi": s2.get("kill_olayi", 0), "m2_islem_ham": int(len(oos2)),
                  "m2_pf_limitsiz": _pf(oos2["r"]) if len(oos2) else math.nan})        # bilgi: sert limit/kill öncesi PF
    satir.update({"m2_islem": s2.get("islem_sayisi", 0), "m2_pf": s2.get("profit_factor", math.nan),
                  "m2_net": s2.get("net_getiri", math.nan), "m2_sharpe": s2.get("sharpe", math.nan)})
    # K2: rastgele giriş
    ham_oos = oos.rename(columns={"giris": "giris_zamani", "cikis": "cikis_zamani"}).copy()
    pencere_sinirlari = [(pd.Timestamp(s["test_bas"]), pd.Timestamp(s["test_bit"])) for s in json.loads(w["secimler"])]
    ham_oos["pencere"] = _pencere_ata(ham_oos["giris_zamani"], pencere_sinirlari)
    cache = {}

    def veri_al(sembol):
        if sembol not in cache:
            mumlar, _ = _veri(sembol, tf)
            ay = wf_tarama.maliyet_ayarlari(tarama.SEMBOL_KURALLARI.get(sembol, tarama.VARSAYILAN_KURAL), 1.0)
            cache[sembol] = (mumlar, ay)
        return cache[sembol]

    rs = rastgele_evren(ham_oos, pencere_sinirlari, g["n_sim"], rng_tohum, tf, veri_al)
    gercek = float(oos["r"].sum())
    p = float((1 + (rs["toplam_r"] >= gercek).sum()) / (len(rs["toplam_r"]) + 1))
    satir.update({"rnd_n_sim": g["n_sim"], "rnd_p": p, "rnd_gercek_r": gercek,
                  "rnd_ort_r": float(rs["toplam_r"].mean()), "rnd_std_r": float(rs["toplam_r"].std(ddof=1)),
                  "rnd_yuzdelik": float((rs["toplam_r"] < gercek).mean()),
                  "rnd_gecersiz": rs["n_gecersiz"] / max(1, rs["n_islem"])})
    # K3
    lo, hi, med = saglamlik.pf_boot(kabul["r"].to_numpy(float), BOOT_BLOK, N_BOOT, np.random.default_rng(rng_tohum + 1))
    satir.update({"pf_boot_alt": lo, "pf_boot_ust": hi, "pf_boot_medyan": med})
    # K4
    satir.update(komsu_evren_pf(ad, w["en_sik_ayar"], tf, evren_stil(stil), oos_bas, oos_bit))
    # DSR (rapor)
    gs = g["getiri"]
    for nm, n in (("deneme", g["n_deneme"]), ("kombinasyon", g["n_komb"])):
        d = saglamlik.deflated_sharpe(gs, n, g["sr_varyans"])
        satir[f"dsr_{nm}"] = d["dsr"]
        satir[f"sr0_{nm}_yillik"] = d["sr0"] * math.sqrt(365)
    satir.update({"dsr_n_deneme": g["n_deneme"], "dsr_n_kombinasyon": g["n_komb"], "sr_varyans": g["sr_varyans"]})


def _pencere_ata(giris: pd.Series, sinirlar: list) -> np.ndarray:
    t0 = pd.DatetimeIndex([a for a, _ in sinirlar])
    gi = pd.DatetimeIndex(giris)
    w = t0.searchsorted(gi, "right") - 1
    return np.clip(w, 0, len(sinirlar) - 1)


def toplam_deneme(yol=None) -> int:
    return sum(k["toplam_kosu"] for k in deneme_kaydi.oku(yol)) + HAIKU_DENEME


def saglamlik_asamasi(surec: int = 4, butce_sn: Optional[float] = None, cikti: Path = CIKTI, n_sim: int = N_SIM,
                      tohum: int = 0, ilerleme: bool = True, donem: str = "2020_bugun", stratejiler=None) -> dict:
    cikti = Path(cikti)
    wf = pd.read_parquet(cikti / "wf_evren.parquet")
    aday = wf[((wf["gecti"] == True) | (wf["yakin_wf"] == True)) & (wf["hata"].fillna("") == "")]   # noqa: E712
    yol = cikti / "saglamlik.parquet"
    onceki = pd.read_parquet(yol) if yol.exists() else pd.DataFrame()
    bitmis = set(zip(onceki["strateji"], onceki["tf"])) if len(onceki) else set()
    sr_h = saglamlik.sr_varyansi(wf)
    n_deneme = toplam_deneme()
    n_komb = int(len(wf))
    # ham işlemlerden stop mesafesi + yan bilgi yüklemesi görev içinde
    gorevler = []
    for rec in aday.to_dict("records"):
        if (rec["strateji"], rec["tf"]) in bitmis or (stratejiler and rec["strateji"] not in stratejiler):
            continue
        oos = pd.read_parquet(cikti / "oos" / f"{rec['strateji']}--{rec['tf']}.parquet")
        gorevler.append({"strateji": rec["strateji"], "stil": rec["stil"], "tf": rec["tf"], "wf": rec, "cikti": cikti,
                         "n_sim": n_sim, "tohum": tohum, "n_deneme": n_deneme, "n_komb": n_komb, "sr_varyans": sr_h,
                         "getiri": _gunluk_dizi(oos, rec)})
    if ilerleme:
        print(f"[sag] geçen {len(aday)}, kalan {len(gorevler)}; N_deneme={n_deneme} N_komb={n_komb}", flush=True)
    sonuc = havuz_calistir(_sag_isci, gorevler, surec, _isci_ham, {"veri_dizini": None, "donem": donem}, butce_sn, ilerleme, "sag")
    yeni = [s for s in sonuc if not s.get("ertelendi")]
    if yeni:
        _csv_yaz(pd.concat([onceki, pd.DataFrame(yeni)], ignore_index=True), cikti / "saglamlik")
    return {"yeni": len(yeni), "ertelenen": len(sonuc) - len(yeni), "saglam": int(sum(bool(s.get("saglam_mi")) for s in yeni))}


def _gunluk_dizi(oos: pd.DataFrame, w) -> np.ndarray:
    """DSR için: yeniden oynatmanın günlük getirisi (aynı tablo, aynı sert limitler -> WF ile aynı seri)."""
    tablo = oos[["kol", "sembol", "yon", "giris", "cikis", "r", "sf", "stop_mesafe"]].reset_index(drop=True)
    m = kasa_metrikleri(tablo, pd.Timestamp(w["oos_bas"]), pd.Timestamp(w["oos_bit"]))
    return m["getiri_serisi"].to_numpy(dtype=float)


# ============================================================================ 5. seçim
def yay_serisi(oos: pd.DataFrame, oos_bas, oos_bit) -> pd.Series:
    k = oos[oos["kabul"]]
    d = pd.DataFrame({"giris_zamani": k["giris"], "cikis_zamani": k["cikis"], "r": k["r"].astype(float)})
    return secim.gunluk_getiri(d, "yay", bas=oos_bas, bit=oos_bit)


def kor_matrisi(seriler: dict, min_ortak: int = secim.MIN_ORTAK_GUN) -> pd.DataFrame:
    ad = list(seriler)
    m = pd.DataFrame(np.nan, index=ad, columns=ad)
    for a in ad:
        for b in ad:
            if a == b:
                m.loc[a, b] = 1.0
                continue
            ortak = seriler[a].index.intersection(seriler[b].index)
            if len(ortak) >= min_ortak:
                x, y = seriler[a].loc[ortak], seriler[b].loc[ortak]
                m.loc[a, b] = float(np.corrcoef(x, y)[0, 1]) if x.std() > 0 and y.std() > 0 else math.nan
    return m


def secim_yap(wf: pd.DataFrame, sag: pd.DataFrame, seriler: dict, n_secim: int = secim.N_SECIM) -> pd.DataFrame:
    """Stil başına skor = Sharpe x (1 - K2 p); korelasyon <= 0.5 (K-I). -> seçilenler DataFrame (ajan, sira, ...)."""
    d = wf.merge(sag[["strateji", "tf", "saglam_mi", "rnd_p", "m2_pf", "pf_boot_alt", "par_oran", "kapi_basarisiz"]],
                 on=["strateji", "tf"], how="inner")
    d = d[(d["gecti"] == True) & (d["saglam_mi"] == True)].copy()                # noqa: E712
    d["skor"] = d["sharpe"] * (1 - d["rnd_p"])
    cikti = []
    for stil, g in d.groupby("stil"):
        g = g.sort_values("skor", ascending=False)
        kimlikler = [f"{a}|{t}" for a, t in zip(g["strateji"], g["tf"])]
        kor = kor_matrisi({k: seriler[k] for k in kimlikler})
        sec = secim.acgozlu_sec(kimlikler, kor, None, n_secim=n_secim, n_yedek=0, esik_korr=secim.ESIK_KORR)
        for sira, k in enumerate(sec["secim"], 1):
            row = g.iloc[kimlikler.index(k)].to_dict()
            row.update(ajan=stil, sira=sira, max_korr=sec["max_korr"].get(k, math.nan))
            cikti.append(row)
    return pd.DataFrame(cikti)


# ============================================================================ 6. kilitli dönem (bilgi)
KILIT_GEREKCE = "karar 27 evren stratejileri, bilgi amaçlı (kilit kullanılmış)"


def kilit_bilgi_kos(ad: str, tf: str, stil: str, dizin: Path, veri_dizini=None, evren=None, ayar=None) -> dict:
    """Ayarı kilit başlangıcında biten son eğitim penceresinden seç; kilitli dönemde değiştirmeden koş (kilit_ac=True)."""
    evren = evren or evren_stil(stil)
    ham, adaylar, bilgi = ham_yukle(dizin, ad, tf, evren)
    egitim, _ = PENCERE_GUN[stil]
    L = kilit.KILIT_BASLANGIC
    nesne = seriler_kur(ham)
    sec = evren_secimi(nesne, L - pd.Timedelta(days=egitim), L, MIN_ISLEM_EVREN[stil])
    satir = {"strateji": ad, "stil": stil, "tf": tf, "hata": ""}
    if sec is None:
        satir.update(ayar="", islem_sayisi=0, nedenler="son eğitim penceresinde yeterli işlem yok")
        return satir
    no = sec[0]
    etiket = adaylar[no]
    satir.update(ayar=etiket, egitim_pf=sec[1], egitim_islem=sec[2])
    st = saglamlik.ayar_coz(ad, etiket)
    ay_s = None
    parcalar = []
    for sembol in ham:
        mumlar = tf_mumlari(sembol, tf, None, None, dizin=veri_dizini, kilit_ac=True, gerekce=KILIT_GEREKCE)
        try:
            fund = depo.funding_oku(sembol, None, None, dizin=veri_dizini, kilit_ac=True, gerekce=KILIT_GEREKCE)
        except FileNotFoundError:
            fund = None
        ay_s = wf_tarama.maliyet_ayarlari(tarama.SEMBOL_KURALLARI.get(sembol, tarama.VARSAYILAN_KURAL), 1.0)
        try:
            t = backtest(funding.stratejiye_hazirla(st, mumlar, fund, sembol, tf), st, ay_s, fund).islemler
        except Exception:  # noqa: BLE001
            continue
        if not len(t):
            continue
        o = islem_ozet(t, no)
        o = o[pd.DatetimeIndex(o["giris_zamani"]) >= L].copy()
        o["sembol"] = sembol
        o["son_mum"] = mumlar.index[-1]
        parcalar.append(o)
    if not parcalar:
        satir.update(islem_sayisi=0, nedenler="kilitli dönemde işlem yok")
        return satir
    oos = pd.concat(parcalar, ignore_index=True)
    bit = oos["son_mum"].max() + pd.Timedelta(1, "ns")
    oos, atilan = sembol_cakismasini_ele(oos.drop(columns="son_mum"))
    tablo = oynatma_tablosu(oos, evren)
    m = kasa_metrikleri(tablo, L, bit, ayar)
    for kx in ("kabul", "pnl", "getiri_serisi"):
        m.pop(kx, None)
    for kx in ("sinif_net", "enstruman_net", "enstruman_adet"):
        m[kx] = json.dumps(m[kx], ensure_ascii=False)
    satir.update(m)
    satir.update(kilit_bas=str(L), kilit_bit=str(bit), cakisma_atilan=atilan)
    return satir


# ============================================================================ portföy stratejileri (karar 24 yolu)
def portfoy_asamasi(donem: str = "2020_bugun", surec: int = 4, stratejiler=None, tf: str = "1d",
                    cikti: Optional[Path] = None, semboller=None) -> pd.DataFrame:
    """Hedef-ağırlık (portföy) stratejileri aynı dönemle, swing/daytrade evreninde wf_portfoy yolu ve karar 24 ölçütleriyle.
    wf_portfoy aynen kullanılır; yalnız veri okuması dönem ayarına göre (2020_bugun: kilit_ac=True + gerekçe) yapılır.
    Sağlamlık için saglamlik_portfoy ayrıca çalıştırılır (bu akışta yok). Çıktı: <kok>/portfoy_wf.csv."""
    from motor.arastirma import wf_portfoy as wp
    from motor.portfoy import veri as pveri
    d = DONEMLER[donem]
    kok = Path(cikti) if cikti else donem_kok(donem)

    def _veri_kilitli(evren, tf_):
        wp._ONBELLEK.clear()
        wp._ONBELLEK[(evren, tf_)] = pveri.veri_yukle(
            evren, tf_, d["bas"] or wp._AYAR["baslangic"], wp._AYAR["bitis"], wp._AYAR["veri_dizini"],
            kilit_ac=d["kilit_ac"], gerekce=KILIT_GEREKCE_2020 if d["kilit_ac"] else None)
        return wp._ONBELLEK[(evren, tf_)]

    orijinal = wp._veri
    wp._veri = _veri_kilitli
    try:
        sonuc = wp.wf_portfoy(f"evren_{donem}", stratejiler, "evren", semboller or EVREN_GENEL, tf, surec,
                              cikti_dizini=kok / "portfoy", analiz_baslangic=d["bas"])
    finally:
        wp._veri = orijinal
    if len(sonuc):
        sonuc.to_csv(kok / "portfoy_wf.csv", index=False)
    return sonuc


# ============================================================================ CLI
def _kilit_asamasi(cikti: Path, ayar=None):
    sec = pd.read_csv(cikti / "secim.csv")
    out = []
    for r in sec.to_dict("records"):
        out.append({**kilit_bilgi_kos(r["strateji"], r["tf"], r["stil"], cikti / "ham"), "ajan": r["ajan"], "sira": r["sira"]})
    df = pd.DataFrame(out)
    df.to_csv(cikti / "kilit_bilgi.csv", index=False)
    return df


def main(argv=None):
    ap = argparse.ArgumentParser(description="Evren stratejileri taraması (karar 27)")
    ap.add_argument("asama", choices=["ham", "wf", "saglamlik", "secim", "kilit", "portfoy"])
    ap.add_argument("--donem", choices=sorted(DONEMLER), default="2020_bugun")
    ap.add_argument("--stil", nargs="*", default=["swing", "daytrade", "scalp"])
    ap.add_argument("--tf", nargs="*", default=None)
    ap.add_argument("--stratejiler", nargs="*", default=None)
    ap.add_argument("--surec", type=int, default=4)
    ap.add_argument("--butce", type=float, default=None, help="saniye; dolunca yeni görev başlatılmaz")
    ap.add_argument("--hatalari-yeniden", action="store_true")
    ap.add_argument("--semboller", nargs="*", default=None)
    ap.add_argument("--kesin", action="store_true", help="verisi hâlâ olmayan (sembol, tf) için 'dışarıda' kaydı yaz")
    a = ap.parse_args(argv)
    kok = donem_kok(a.donem)
    if a.asama == "ham":
        print(ham_tara(tuple(a.stil), a.stratejiler, a.tf, a.surec, a.butce, donem=a.donem,
                       hatalari_yeniden=a.hatalari_yeniden,
                       evren=a.semboller, kesin=a.kesin))
    elif a.asama == "wf":
        print(wf_asamasi(tuple(a.stil), a.surec, a.butce, kok, hatalari_yeniden=a.hatalari_yeniden, donem=a.donem))
    elif a.asama == "saglamlik":
        print(saglamlik_asamasi(a.surec, a.butce, kok, donem=a.donem))
    elif a.asama == "secim":
        from motor.arastirma import wf_evren_rapor
        wf_evren_rapor.secim_ve_ozet(kok)
    elif a.asama == "kilit":
        from motor.arastirma import wf_evren_rapor
        wf_evren_rapor.kilit_ve_ozet(kok, a.donem)
    elif a.asama == "portfoy":
        print(portfoy_asamasi(a.donem, a.surec).shape)


if __name__ == "__main__":
    main()
