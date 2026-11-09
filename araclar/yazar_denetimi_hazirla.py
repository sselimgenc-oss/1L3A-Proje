# -*- coding: utf-8 -*-
"""Yazar denetimi hazirlayici.

Amac: onerilen/yedek strateji ailelerinde "farkli yazar sayisi" sisikligini kontrol etmek.

Ne yapar:
  1. stratejiler/aileler.json icinden secim.durum = ONERILEN veya YEDEK olan aileleri alir.
  2. Her aile-kart ciftine, kartin yazarini veri/kart_dizini.csv (kaynak_yazar) dan ekler.
  3. Asagidaki ETIKET tablosundaki her cift icin etiketi (ayni / yakin / farkli) yazar.
     Etiketler kartin kendi ad/ozet/long_giris metnine bakilarak elle verildi.
  4. stratejiler/yazar_denetimi.csv yazar ve konsol ozetini basar.

Calistirma: python3 araclar/yazar_denetimi_hazirla.py
"""
import csv
import glob
import json
import os

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AILE_DOSYA = os.path.join(KOK, "stratejiler", "aileler.json")
KART_DIZIN = os.path.join(KOK, "veri", "kart_dizini.csv")
KART_KLASOR = os.path.join(KOK, "veri", "kartlar_ham")
CIKTI = os.path.join(KOK, "stratejiler", "yazar_denetimi.csv")

KOD = {"a": "ayni", "y": "yakin", "f": "farkli"}

# Her aile icin, kaynak_kartlar sirasiyla "kod|gerekce" listesi.
# kod: a = ayni, y = yakin, f = farkli
ETIKET = {
"swing__ma-kesisim": [
"y|Haftalik 30 MA yonu ve fiyat ustu; kesisim degil, durum filtresi.",
"y|50/200 EMA ust uste durumu rejim filtresi; kesisim tetigi yok.",
"a|Kisa ve uzun EMA kesisimi; aile mekanigiyle birebir.",
"a|26 EMA'nin 50 SMA'yi yukari kesmesi; kesisim tetigi var.",
"y|MA dizilimi ve sikisma; kesisim degil, siralama tetigi.",
"y|MA gecisinden sonra geri cekilme tetigi; kesisim ana giris degil.",
"a|9 EMA'nin 13 EMA'yi yukari kesmesi.",
"a|4 SMA'nin 9 SMA'yi yukari kesmesi.",
"y|Fiyatin MA ustunde kalmasi; kesisim degil, konum tetigi.",
"a|Kisa MA uzun MA'yi yukari keser; altin kesisim.",
"a|10 SMA'nin 20 SMA'yi yukari kesmesi.",
"a|50 SMA'nin 200 SMA'yi yukari kesmesi (altin capraz).",
"a|10 SMA'nin 20 SMA'yi yukari kesmesi.",
"a|10 SMA'nin 50 SMA'yi yukari kesmesi.",
"a|EMA9'un EMA13'u kesmesi, EMA13 EMA50 ustunde.",
"y|MA'larin yonu (ucu de yukseliyor); kesisim tetigi yok.",
"a|50 SMA'nin 200 SMA'yi yukari kesmesi.",
"a|20 MA'nin 50 MA'yi yukari kesmesi.",
],
"swing__macd-sinyal": [
"a|MACD cizgisinin sinyal cizgisini yukari kesmesi.",
"a|MACD cizgisinin sinyal cizgisini yukari kesmesi.",
"a|MACD cizgisinin sinyal cizgisini yukari kesmesi.",
"a|MACD cizgisinin sinyal cizgisini yukari kesmesi.",
"y|Sinyal cizgisinin sifir cizgisini gecmesi; farkli cizgi kesisimi.",
"a|MACD cizgisi sinyal cizgisini yukari keser.",
"y|EMA13 yonu ve histogram rengi; MACD kesisimi tetik degil.",
"a|MACD cizgisinin sifir cizgisini yukari gecmesi (ailede var).",
],
"scalp__stokastik-donus": [
"y|Stokastik kesisimi var ama asiri bolge sarti yok; RSI ek filtre.",
"a|Stokastik 20 altindan cikip %D'yi yukari keser; aile mekanigi.",
"a|Stokastik 20 altindan yukari kesisim, EMA trend filtresi.",
"a|Stokastik asiri satimdan yukari kesisim, EMA50/100 filtresi.",
"y|Stokastik RSI ve HMA gecisi; tetik fiyatin HMA'yi gecmesi.",
"y|Stokastik ayrismasi iki zaman diliminde; bolge cikisi farkli tetik.",
],
"scalp__ma-kesisim": [
"y|EMA 5/7 uzun kurali acik degil; kesisim varsayimi belirsiz.",
"y|EMA kesisimi kirilim mumuna bagli; tetik kirilim.",
"a|EMA14'un EMA50'yi yukari kesmesi.",
"y|MA3/MA7 kesisimi var ama tetik Bollinger sapma mumu.",
"y|Regresyon cizgisi kirilimi; MA kesisimi degil.",
"a|EMA5'in EMA34'u yukari kesmesi (RSI onayiyla).",
"y|MA egimi ve fiyat-MA konumu; kesisim tetigi yok.",
"y|EMA8 fiyat kesisimi ve EMA konumu; MA kesisimi degil.",
"y|RSI ile WMA kesisimi; fiyatin HMA ustune cikmasi tetik.",
"y|Fiyatin HMA65'i mum kapanisiyla gecmesi; MFI ayri tetik.",
],
"swing__ma-geri-cekilme": [
"a|10/20/50 EMA'ya geri cekilme ve tutunma; aile mekanigi.",
"a|50 SMA'ya geri cekilme ve sicrama.",
"a|50 MA'ya geri cekilme, donus mumuyla uzun.",
"y|Dusus trendinde 200 SMA desteginden alim; trend ters.",
"a|Yukselis trendinde 20/40 SMA bolgesine geri cekilme.",
"a|20 EMA dinamik destege geri cekilme ve sicrama.",
"a|50 EMA'ya geri cekilme ve reddetme mumu.",
"a|20 SMA'ya geri cekilme ve temas mumu.",
],
"swing__cift-dip-tepe": [
"a|Cift dip, boyun cizgisi ustu teyit; aile mekanigi.",
"a|Cift dip, boyun cizgisi ustu teyit; aile mekanigi.",
"a|Cift tepe acik satis; boyun cizgisi mekanigi.",
"a|Cift dip boyun cizgisi kirilimi.",
"y|Cift dip ters donus mumuyla; boyun kirilimi tetik degil.",
"y|Cift dip donusu; kirilim tetigi kitapta belirsiz.",
"a|Cift dip, boyun cizgisi yukari kirilimi.",
"a|Cift dip, boyun cizgisi kirilimi; RSI teyidi.",
],
"swing__konsolidasyon-kirilim": [
"a|Konsolidasyon sonrasi hacimli kirilim.",
"a|Dar konsolidasyondan kirilim.",
"a|Destek kirilimi; kisa taraf ayni mekanik.",
"a|Konsolidasyon ust siniri kirilimi.",
"a|Direnc kirilimi ve hacim onayi.",
"a|Yatay direnc kirilimi, hacim onayi.",
"y|Hacim patlamasi ve fiyat artisi; konsolidasyon kirilimi sart degil.",
],
"swing__dar-aralik-kirilim": [
"a|Daralma sonrasi hacimli kirilim (VCP).",
"a|NR7 dar araligin ustunde kapanis kirilimi.",
"a|Ic bar ust sinirinin kirilmasi.",
"a|Ic bar kumesi ust sinirinin kirilmasi.",
],
"scalp__bant-donus": [
"a|Keltner alt bant disina cikis ve geri donus; stokastik onayi.",
"a|Alt Bollinger bant asiri satim ve orta banda donus.",
"a|Alt bant disi asiri satim ve geri donus.",
"a|Bollinger(40,2), RSI(5) ve ADX<25 onayi; aileyle ayni.",
"a|Bollinger(40,2), RSI(5) ve ADX<25 onayi; aileyle ayni.",
"a|RSI(5) ve Keltner alt bant; 200 EMA filtresi.",
],
"swing__trend-cizgisi-kanal": [
"a|Trend cizgisi kirilimi.",
"a|Kanal alt cizgisine dokunup tepki.",
"a|Trend cizgisi yeniden testi ve tepki.",
"a|Yukselis trend cizgisinden tepki.",
"a|Kanal alt cizgisi kirilimi; kisa taraf.",
"a|Kanal disina cikip geri donus.",
"a|Kanal alt cizgisinden alim.",
],
"swing__rsi-diverjans": [
"y|RSI M ve W yapisi; uyumsuzluk degil, RSI formasyonu.",
"a|RSI boga uyumsuzlugu ve 21 EMA teyidi.",
"a|SSTO uyumsuzlugu; osilator ayrismasi.",
"a|OBV uyumsuzlugu; osilator-fiyat ayrismasi.",
"a|RSI boga uyumsuzlugu.",
"a|MACD histogram uyumsuzlugu.",
"y|RSI basarisizlik salinimi; uyumsuzluk degil, RSI yapisi.",
"a|RSI boga sapmasi ile donus.",
],
"swing__mum-yutan-donus": [
"a|Cubuk tersine donus; iki mumlu donus formasyonu.",
"a|Yutan mum ve doji donus onayi.",
"y|Karsit desen; giris tetigi ve mum tanimi belirsiz.",
"a|Dis gun (outside bar) donus sinyali.",
"a|Boga yutma donus formasyonu.",
"a|Yutan mum, hacim onayiyla.",
"a|Yutan mum trend sonu donusu.",
"a|Iki bar tersine donus.",
],
"swing__fib-geri-cekilme": [
"a|Fibonacci geri cekilme seviyesinden trend yonunde giris.",
"a|%60 geri cekilme penceresi; ayni geri cekilme mekanigi.",
"a|Fibonacci geri cekilme seviyesi destek ve tepki.",
"a|Fibonacci geri cekilmesi, kisa taraf.",
"a|%61,8 geri cekilme donusu, kisa taraf.",
"a|Fibonacci %38,2-50 geri cekilme ve onay.",
"a|Fibonacci %50 geri cekilme alimi.",
],
"swing__bant-donus": [
"y|W dip/M tepe formasyonu bant uzerinde; bant dokunusu tetik degil.",
"a|Alt Bollinger bant donusu ve teyit.",
"a|Alt bant dokunusu ve RSI<30 birlikte.",
"a|Alt Bollinger bant alti kapanis ve ortalamaya donus.",
"a|Bant dokunusu, ADX filtresi ve geri donus mumu.",
],
"swing__aralik-ticareti": [
"a|Destek bolgesinde yatay aralik alimi.",
"a|Destek bolgesinden salinim ve alim.",
"a|Destek ustu kapanisla kutu alimi.",
"a|Yatay aralik sinirindan alim.",
"a|Kutu destekten alim, direnc hedefi.",
],
"swing__bayrak-flama": [
"a|Yuksek sikli bayrak kirilimi (direk ustu).",
"a|Bayrak kirilimi, trend devami.",
"a|Bayrak/flama ust cizgi kirilimi.",
"a|Bayrak ust cizgisi kirilimi, hacimle.",
],
"swing__goreceli-guc-momentum": [
"a|Goreceli guc donusu ve kirilim filtresi.",
"a|Lider hisse, geri cekilme alimi; momentum secimi.",
"a|Goreceli guc, geri cekilmede alim.",
],
"scalp__ma-geri-cekilme": [
"a|200 EMA trendinde 20 EMA geri cekilme alimi.",
"a|EMA10/21 orta noktasina geri cekilme.",
"a|200 EMA'ya geri cekilme ve sicrama.",
"y|200 EMA'ya ikinci kirilim ve tutunma; geri cekilme farkli tetik.",
"a|5 SMA geri cekilmesi ve stokastik donusu.",
"a|Mini-pup geri cekilmesi ve stokastik tetik.",
],
"daytrade__orb": [
"f|Ilk saat yonu; acilis araligi kirilimi kullanilmiyor.",
"a|Acilis araligi ustunde kapanisla giris.",
"a|Ilk uc dakika araligi, kirilim yonunde giris.",
"a|ORB flamasi cift tarafli kirilim.",
"y|ORB sinirinin basarisiz kirilimi; ters yon tetik.",
"y|ORB'nin tekrar test ve red sonrasi kirilim.",
"y|ORB'ye geri cekilme girisi; kirilim yerine pullback.",
"y|ORB'ye tekrarli geri donus; sayim tetigi.",
"a|Acilis bosluğu ve acilis araligi kirilimi.",
],
"swing__rsi-asiri-donus": [
"a|RSI(2) asiri satim donusu.",
"a|RSI 30 yukari kesisi; aile mekanigi.",
"a|RSI 30'un geri cikisi ile uzun.",
],
"scalp__supertrend-psar": [
"y|Supertrend ustunde ve pivot R1 kirilimi; trend donusu degil.",
"y|PSAR yalniz filtre; tetik heikin ashi ve RSI.",
"a|HalfTrend yon degisimi sinyali.",
],
"scalp__macd-sinyal": [
"a|MACD histogrami sifir donusu = MACD-sinyal kesisimi (lider duzeltmesi).",
"y|Histogram ve yavas stokastik; sinyal kesisimi tetik degil.",
"y|TSI cizgi caprazi; farkli gosterge, benzer caprazlama mekanigi.",
],
"scalp__rsi-asiri-donus": [
"a|RSI 30 asiri satim ve hacim osilatoru onayi.",
"y|RSI asiri satim ve aralik alt siniri; tetik aralik.",
"a|RSI(7) 30 ustune cikis, asiri satim donusu.",
],
"daytrade__trend-yapi-dow": [
"a|Onceki salinim tepesinin kirilmasi.",
"y|Yukselen trend tanimi belirsiz; trend takibi tetigi.",
"y|Yuksek dip yapisi ve VWAP; kirilim tetigi yok.",
],
"scalp__rsi-momentum-esik": [
"y|RSI 30 alti ve mum; 50 esigi yerine farkli tetik.",
"a|RSI 30 esiginin yukari kirilimi.",
],
"scalp__heikin-ashi-donus": [
"a|HA mum renk degisimi ile yeni yon.",
"a|HA mum renk donusu, karsi-trend giris.",
],
"daytrade__konsolidasyon-kirilim": [
"f|Alt golge basinc bolgesi; konsolidasyon kirilimi degil.",
"a|Ogle kanali ust siniri kirilimi.",
"a|Kirilim oncesi duraklama, stop giris.",
"a|Yuksek hacimli direnc kirilimi.",
],
"daytrade__kirilim-geri-test": [
"a|Kirilim sonrasi geri cekilme ve yeniden test.",
"y|Uc mumluk sikisma bolgesi; yeniden test degil, kirilim kurulumu.",
"a|Kopma pivot seviyesinde yeniden test.",
],
"daytrade__bant-donus": [
"a|Alt Bollinger bant desteginden boga mumu.",
"a|Bant ihlali ve ters donus mumu.",
],
"scalp__rsi-diverjans": [
"a|RSI boga uyumsuzlugu ve bant teyidi.",
"a|CCI uyumsuzlugu; osilator-fiyat ayrismasi.",
"a|RSI uyumsuzlugu ve filtre ile alim.",
],
"daytrade__aralik-ticareti": [
"a|Aralik alt sinirinda alim, karsi sinir hedefi.",
"a|Iki yatay sinir arasinda alim.",
"a|Aralik sinirinda ters islem.",
],
"scalp__geri-cekilme-fiyat-eylemi": [
"a|Iki bacakli geri cekilmede trend yonunde giris.",
"a|Trend gununde kisa toparlanma; aile mekanigi.",
"a|Dusuk hacimli geri cekilme, trend yonunde alim.",
],
"daytrade__pivot-seviye": [
"a|Pivot etrafinda geri cekilme ve donus.",
"a|CPR seviyelerinde destek ve kirilim.",
"a|Pivot seviyesinde tepki ve alim.",
],
"scalp__cci-esik": [
"a|CCI -100 ve -30 esik kirilimi.",
"a|CCI +100 esik kirilimi.",
"y|CCI dip ve donus; esik kirilimi degil, dip yapisi.",
],
"daytrade__vwap-donus": [
"a|VWAP +-2 sapma bandindan ortalamaya donus.",
"y|VWAP destegi ve RSI; bant disi uc yok.",
"y|VWAP geri cekilmesinde dip alimi; bant donusu degil.",
],
"daytrade__gap-doldurma": [
"a|Acilis bosluğunu kapatma (dolum) mekanigi.",
"a|Bosluk kapanisi ve Y-kapanis seviyesinden giris.",
],
"scalp__konsolidasyon-kirilim": [
"a|1 dk konsolidasyon kirilimi, trend yonunde.",
"a|Blok ust siniri kirilimi.",
"a|Yuvarlak sayi aralik ust bariyeri kirilimi.",
"a|Ic aralik ust siniri kirilimi.",
"a|Devrilme noktasi (ARB) bariyer kirilimi.",
],
"scalp__seviye-tepki": [
"a|Yuvarlak seviye tepkisi ve alim emri.",
"a|Destek seviyesi ve HA donusu.",
"a|Onceki gun dibi ve HA donusu.",
"a|Yuvarlak sayi dibi ve HA donusu.",
"y|Yuvarlak seviye aralik ticareti; tepki tetigi yok.",
],
"daytrade__bb-sikisma-kirilim": [
"a|Bant genisligi daralmasi sonrasi bant kirilimi.",
],
"daytrade__donchian-kirilim": [
"y|Williams fraktal kirilimi; Donchian kanali degil.",
"a|Donchian ust bant geri cekilme ve kirilim.",
],
"daytrade__stokastik-donus": [
"a|Williams %R asiri bolge cikisi ve geri donus.",
],
"daytrade__vwap-trend": [
"a|VWAP yukari kesisimi.",
"y|VWAP alti konum; kesisim tetigi tanimsiz.",
],
"scalp__cift-dip-tepe": [
"a|Yanal piyasada destek/direnc yakininda cift dip/tepe.",
"a|Trend geri cekilmesinde cift tepe/dip.",
"a|Gun ici cift tepe, acik satis.",
"a|Gun ici uclu tepe, acik satis.",
"a|Gun ici cift dip, boyun ustu alim.",
"a|Uclu dip, formasyon tepesi kirilimi.",
],
"daytrade__pin-bar": [
"a|Aralik dibinde pin bar donusu.",
"a|Seviyede fitil reddi ve alim.",
],
"daytrade__ma-geri-cekilme": [
"a|EMA geri cekilme bolgesinde trend yonunde giris.",
],
}


def main():
    with open(AILE_DOSYA, encoding="utf-8") as f:
        ailer = json.load(f)
    sec = [a for a in ailer if a.get("secim", {}).get("durum") in ("ONERILEN", "YEDEK")]

    kart_yazar = {}
    with open(KART_DIZIN, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            kart_yazar[r["kart_id"]] = r["kaynak_yazar"]

    kart_ids = set()
    for yol in glob.glob(os.path.join(KART_KLASOR, "*", "*.json")):
        with open(yol, encoding="utf-8") as f:
            for kart in json.load(f):
                kart_ids.add(kart["kart_id"])

    satirlar = []
    for a in sec:
        aid = a["aile_id"]
        kartlar = a["kaynak_kartlar"]
        etiketler = ETIKET.get(aid, [])
        if len(etiketler) != len(kartlar):
            raise SystemExit("Etiket sayisi uyusmuyor: " + aid)
        for kid, giris in zip(kartlar, etiketler):
            if kid not in kart_ids or kid not in kart_yazar:
                raise SystemExit("Kart bulunamadi: " + kid)
            kod, gerekce = giris.split("|", 1)
            if len(gerekce.split()) > 20:
                raise SystemExit("Gerekce 20 kelimeyi asiyor: " + kid)
            satirlar.append({
                "aile_id": aid,
                "kart_id": kid,
                "yazar": kart_yazar[kid],
                "etiket": KOD[kod],
                "gerekce": gerekce,
            })

    with open(CIKTI, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["aile_id", "kart_id", "yazar", "etiket", "gerekce"])
        w.writeheader()
        w.writerows(satirlar)

    # Ozet tablo
    ozet = []
    for a in sec:
        aid = a["aile_id"]
        eski = a["yazar_sayisi"]
        ayni_y = {s["yazar"] for s in satirlar if s["aile_id"] == aid and s["etiket"] == "ayni"}
        ayniyakin_y = {s["yazar"] for s in satirlar if s["aile_id"] == aid and s["etiket"] in ("ayni", "yakin")}
        ozet.append((aid, eski, len(ayni_y), len(ayniyakin_y)))

    print("aile_id | eski yazar_sayisi | ayni yazar | ayni+yakin yazar")
    for aid, eski, ay, ayy in ozet:
        print("%s | %s | %d | %d" % (aid, eski, ay, ayy))

    print()
    print("Ayni sayisi eskisinden en az 2 dusen aileler (eski - ayni yazar >= 2):")
    for aid, eski, ay, ayy in ozet:
        if eski - ay >= 2:
            print("  %s: eski %s, ayni %d" % (aid, eski, ay))
    print("CSV satir sayisi:", len(satirlar), "->", CIKTI)


if __name__ == "__main__":
    main()
