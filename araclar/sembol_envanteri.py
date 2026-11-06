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

# Taban (USDT oncesi) isimlere gore sinif. Liste, sadece bilinen isimleri
# icerir; geri kalan aktif semboller kripto sayilir, bilinmeyenler belirsiz.
TRADFI_EMTIA = {"XAU", "XAG", "XPT", "XPD", "CL", "BZ", "NATGAS", "COPPER", "WTI", "BRENT"}
TRADFI_HISSE = {
    "TSLA", "NVDA", "AAPL", "MSTR", "COIN", "SPY", "QQQ", "AMZN", "GOOGL",
    "META", "MSFT", "HOOD", "PLTR", "CRCL",
}
BELIRSIZ = set()


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


def tur_belirle(sembol, son_ay):
    """Sadece aktif (son ay 2026-09 veya 2026-10) semboller siniflandirilir."""
    if son_ay not in AKTIF_AYLAR:
        return "pasif"
    taban = sembol[:-4] if sembol.endswith("USDT") else sembol
    if taban in TRADFI_EMTIA:
        return "tradfi_emtia"
    if taban in TRADFI_HISSE:
        return "tradfi_hisse"
    if taban in BELIRSIZ:
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
        tur = tur_belirle(sembol, son_ay) if aylar else "pasif"
        satirlar.append(
            {
                "sembol": sembol,
                "ilk_ay": ilk_ay,
                "son_ay": son_ay,
                "ay_sayisi": len(aylar),
                "tur": tur,
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
        sayilar[satir["tur"]] = sayilar.get(satir["tur"], 0) + 1
    print(f"Yazildi: {CIKTI_YOLU} ({len(satirlar)} satir)")
    print(f"Tur dagilimi: {sayilar}")


if __name__ == "__main__":
    main()
