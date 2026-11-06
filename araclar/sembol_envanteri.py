"""Binance USDT-M vadeli sembol envanteri.

UYARI (lider denetimi): `tur_tahmini` sutunu el listesine dayanir ve EKSIKTIR
(AMD, AVGO, ASML, COST, CRWD gibi bircok hisse 'kripto' gorunur). Kesin
siniflandirma Binance exchangeInfo (underlyingType/underlyingSubType) ile,
API'ye erisebilen sunucudan yapilacak. ilk_ay/son_ay bilgisi guvenilirdir.

Binance API'ye bu makineden erisilemedigi icin veri data.binance.vision
S3 listesinden okunur (XML). Her sembol icin 5m klasorundeki .zip
dosyalarindan ilk ve son ay bulunur.

Cikti: veri/sembol_envanteri.csv
Sutunlar: sembol, ilk_ay, son_ay, ay_sayisi, tur

tur degerleri:
  tradfi_hisse  ABD hisse/ETF ticker'lari (<TICKER>USDT)
  tradfi_emtia  emtia (altin, gumus, petrol, dogalgaz, bakir vb.)
  kripto        yukaridakiler disinda aktif semboller
  belirsiz      kesin siniflandirilamayan aktif semboller
  pasif         son ay 2026-09 / 2026-10 olmayan veya 5m verisi olmayan
"""

import csv
import os
import re
import time
import xml.etree.ElementTree as ET

import requests

S3_URL = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
KLINE_ON_EK = "data/futures/um/monthly/klines/"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

ISTEK_ARASI_BEKLEME = 0.05  # saniye, nazik olmak icin
DENEME_SAYISI = 3
ZAMAN_ASIMI = 30  # saniye

AKTIF_AYLAR = {"2026-09", "2026-10"}

CIKTI_YOLU = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "veri",
    "sembol_envanteri.csv",
)

# Siniflandirma: taban isim (kotu quote ekleri ve _TARIH son eklerinden arindirilmis)
# TRADFI_EMTIA ve TRADFI_HISSE'de yoksa ve BELIRSIZ'de de yoksa -> kripto (varsayilan).
# BELIRSIZ: emin olunamayan isimler (tahmin yerine isaretlendi).
TRADFI_EMTIA = {"XAU", "XAG", "XPT", "XPD", "CL", "BZ", "NATGAS", "COPPER", "WTI", "BRENT"}

TRADFI_HISSE = {
    # ABD hisseleri
    "AAOI", "AAPL", "ABBV", "ACN", "ADBE", "AKAM", "ALAB", "AMAT", "AMC", "AMD",
    "AMGN", "AMZN", "APLD", "APP", "ARM", "ASTS", "AVGO", "AXTI", "BAC", "BB",
    "BBX", "BILL", "BMNR", "BRKB", "BX", "C", "CAT", "CEG", "CFG", "CIEN",
    "COHR", "COIN", "COST", "CRCL", "CRDO", "CRM", "CRML", "CRWD", "CRWV", "CSCO",
    "CVNA", "CVX", "DASH", "DDOG", "DELL", "DIS", "DJT", "DKNG", "EBAY", "EQT",
    "F", "FIS", "FLNC", "GEV", "GLW", "GME", "GOOGL", "GPS", "GPRO", "GS",
    "GTLB", "HD", "HEI", "HIMS", "HOOD", "HPE", "HUT", "IBKR", "IBM", "INTC",
    "IONQ", "IR", "IREN", "JPM", "KLAC", "KO", "LLY", "LRCX", "MARA", "MCD",
    "MDB", "MDT", "MELI", "MET", "META", "MP", "MRK", "MRNA", "MRVL", "MSFT",
    "MSTR", "MU", "NBIS", "NET", "NFLX", "NKE", "NOK", "NOW", "NVDA", "NVO",
    "OKLO", "ON", "ONDS", "ORCL", "OXY", "O", "PANW", "PATH", "PDD", "PFE",
    "PLTR", "PYPL", "QCOM", "RDDT", "RDW", "RIVN", "RKLB", "SHOP", "SMCI", "SMR",
    "SNDK", "SNOW", "SNPS", "SOFI", "STRC", "T", "TEAM", "TEM", "TER", "TSLA",
    "TSM", "TTWO", "TWST", "TXN", "UB", "UBER", "UNFI", "UNH", "USAR", "V",
    "VKTX", "VRT", "VST", "WDC", "WMT", "XOM", "ZM", "ZS",
    # Yabanci hisseler (ABD disi, tradfi)
    "ASML", "BABA", "BYD", "HANMI", "HK0625", "HK0700", "HK0992", "HK1810",
    "HYUNDAI", "KUAISHOU", "LGELECTRONICS", "MEITUAN", "NAVER", "POPMART",
    "SAMSUNG", "SHELL", "SKHYNIX", "SONY", "TENCENT",
    # ETF ve kaldirac ETF'leri
    "EIDO", "EWJ", "EWT", "EWY", "EWZ", "EWZS", "GDX", "IWM", "KODEX200", "KORU",
    "MSTU", "MUU", "NVDL", "QQQ", "SLX", "SMH", "SOXL", "SOXS", "SPY", "SQQQ",
    "TBT", "TMF", "TQQQ", "TSLL", "TZA", "URNM", "UVXY", "XBI", "XLE",
    "CSOPSAMSUNG2L", "CSOPSKHYNIX2L",
}

# Emin olunamayan isimler (tahmin yerine belirsiz isaretlendi)
BELIRSIZ = {
    "ACT", "ACU", "AGT", "AI", "AIA", "AIN", "AIO", "AIOT", "AKE", "ANTHROPIC",
    "ARC", "ARIA", "ARX", "ASR", "ATA", "AVAAI", "AWE", "AZTEC", "B", "B2", "B3",
    "BAN", "BANK", "BARD", "BEL", "BID", "BR", "BSP", "BTCU", "BTW", "BWET",
    "CBRS", "CC", "CHIP", "CLO", "COLLECT", "COMMON", "CT", "CXMT", "CYPH", "CYS",
    "D", "DAM", "DF", "DMC", "DOLO", "DOOD", "DRAM", "EDEN", "EPIC", "EPT",
    "ESP", "ESPORTS", "ETHU", "FF", "FLEX", "FLM", "FLUID", "FOGO", "FOLKS",
    "FORM", "FWDI", "G", "GIGADEV", "GRAM", "GUA", "H", "HANA", "HIGH", "HIPPO",
    "HOME", "IDOL", "IN", "INTW", "JCT", "KSM", "KSTR", "LA", "LITE", "M",
    "MINIMAX", "MON", "MVLL", "NAORIS", "NFP", "NXPC", "OL", "OPENAI", "OPG",
    "OPN", "OURA", "PAXG", "PAYP", "PREDICT", "Q", "QNTX", "RAM", "RAYSOL", "RE",
    "S", "SAMSUNGEM", "SECZ", "SHAZ", "SKDD", "SKHY", "SKUU", "SNXX", "SPACE",
    "SPCX", "SPCXUSD1", "STM", "STXX", "TANSSI", "TRADOOR", "TREE", "TST", "UAI",
    "UNITREE", "US", "USDBRL", "USDEX", "VIC", "XAUT", "XNY", "XPIN", "ZEST",
    "ZHIPU", "ZHONGJI", "A", "AT",
}

# Vadeli (tarihli) kontratlar: BTCUSDT_260925 gibi; taban isim BTC/ETH olarak sinifa girer.
# Bunlar sureklilik (perpetual) degil, raporda ayrica belirtilir.


def istek_yap(oturum, parametreler):
    """S3 listesini ceker. Hata olursa en fazla DENEME_SAYISI kez dener."""
    son_hata = None
    for deneme in range(1, DENEME_SAYISI + 1):
        try:
            cevap = oturum.get(S3_URL, params=parametreler, timeout=ZAMAN_ASIMI)
            cevap.raise_for_status()
            kok = ET.fromstring(cevap.content)
            time.sleep(ISTEK_ARASI_BEKLEME)
            return kok
        except (requests.RequestException, ET.ParseError) as hata:
            son_hata = hata
            time.sleep(1.0 * deneme)
    raise RuntimeError(f"istek {DENEME_SAYISI} denemede basarisiz: {parametreler}: {son_hata}")


def sembol_listesi(oturum):
    """Klines altindaki tum sembol klasorlerini (sayfalayarak) dondurur."""
    semboller = set()
    marker = ""
    while True:
        parametreler = {"delimiter": "/", "prefix": KLINE_ON_EK}
        if marker:
            parametreler["marker"] = marker
        kok = istek_yap(oturum, parametreler)
        son_prefix = None
        for onek in kok.findall("s3:CommonPrefixes/s3:Prefix", NS):
            son_prefix = onek.text
            ad = onek.text[len(KLINE_ON_EK):].rstrip("/")
            if ad:
                semboller.add(ad)
        kesildi = kok.findtext("s3:IsTruncated", default="false", namespaces=NS) == "true"
        if not kesildi:
            break
        yeni_marker = kok.findtext("s3:NextMarker", default="", namespaces=NS) or son_prefix
        if not yeni_marker or yeni_marker == marker:
            raise RuntimeError("sayfalama ilerlemiyor (sembol listesi)")
        marker = yeni_marker
    return sorted(semboller)


def ay_listesi(oturum, sembol):
    """Sembolun 5m klasorundeki .zip dosyalarindan YYYY-MM aylarini dondurur."""
    aylar = set()
    desen = re.compile(rf"{re.escape(sembol)}-5m-(\d{{4}}-\d{{2}})\.zip")
    onek = f"{KLINE_ON_EK}{sembol}/5m/"
    marker = ""
    while True:
        parametreler = {"prefix": onek}
        if marker:
            parametreler["marker"] = marker
        kok = istek_yap(oturum, parametreler)
        son_anahtar = None
        for anahtar in kok.findall("s3:Contents/s3:Key", NS):
            son_anahtar = anahtar.text
            eslesme = desen.fullmatch(os.path.basename(anahtar.text))
            if eslesme:
                aylar.add(eslesme.group(1))
        kesildi = kok.findtext("s3:IsTruncated", default="false", namespaces=NS) == "true"
        if not kesildi:
            break
        yeni_marker = kok.findtext("s3:NextMarker", default="", namespaces=NS) or son_anahtar
        if not yeni_marker or yeni_marker == marker:
            raise RuntimeError(f"sayfalama ilerlemiyor ({sembol})")
        marker = yeni_marker
    return sorted(aylar)


KOTU_EKLER = ("SETTLED", "USDT", "USDC", "BUSD", "USD1", "USD")


def taban_isim(sembol):
    """BTCUSDT -> BTC, BTCUSDT_260925 -> BTC, MDTUSDTSETTLED -> MDT, BTCUSD1 -> BTC."""
    ad = sembol.split("_")[0]
    degisti = True
    while degisti:
        degisti = False
        for ek in KOTU_EKLER:
            if ad.endswith(ek) and len(ad) > len(ek):
                ad = ad[: -len(ek)]
                degisti = True
                break
    return ad


TRADFI_ILK_AY = "2025-12"  # Binance TradFi perpetual'lari bu aydan once yok


def tur_belirle(sembol, son_ay, ilk_ay=""):
    """Sadece aktif (son ay 2026-09 veya 2026-10) semboller siniflandirilir."""
    if son_ay not in AKTIF_AYLAR:
        return "pasif"
    if "_" in sembol or not sembol.endswith("USDT"):
        return "vadeli_veya_usdt_disi"
    taban = taban_isim(sembol)
    if taban in TRADFI_EMTIA:
        return "tradfi_emtia"
    if taban in TRADFI_HISSE:
        # TradFi oncesi listelenen ayni adli semboller kripto (DASH, CVX, T, MDT...)
        return "tradfi_hisse" if ilk_ay >= TRADFI_ILK_AY else "kripto"
    if taban in BELIRSIZ or sembol in BELIRSIZ:
        return "belirsiz"
    return "kripto"


def main():
    oturum = requests.Session()
    semboller = sembol_listesi(oturum)
    print(f"Toplam sembol klasoru: {len(semboller)}")

    satirlar = []
    for sayac, sembol in enumerate(semboller, 1):
        aylar = ay_listesi(oturum, sembol)
        ilk_ay = aylar[0] if aylar else ""
        son_ay = aylar[-1] if aylar else ""
        tur = tur_belirle(sembol, son_ay, ilk_ay) if aylar else "pasif"
        satirlar.append(
            {
                "sembol": sembol,
                "ilk_ay": ilk_ay,
                "son_ay": son_ay,
                "ay_sayisi": len(aylar),
                "tur_tahmini": tur,
            }
        )
        if sayac % 50 == 0:
            print(f"  {sayac}/{len(semboller)} islendi")

    os.makedirs(os.path.dirname(CIKTI_YOLU), exist_ok=True)
    with open(CIKTI_YOLU, "w", newline="", encoding="utf-8") as dosya:
        yazici = csv.DictWriter(
            dosya, fieldnames=["sembol", "ilk_ay", "son_ay", "ay_sayisi", "tur_tahmini"]
        )
        yazici.writeheader()
        yazici.writerows(satirlar)

    sayilar = {}
    for satir in satirlar:
        sayilar[satir["tur_tahmini"]] = sayilar.get(satir["tur_tahmini"], 0) + 1
    print(f"Yazildi: {CIKTI_YOLU} ({len(satirlar)} satir)")
    print(f"Tur dagilimi: {sayilar}")


if __name__ == "__main__":
    main()
