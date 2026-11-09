#!/usr/bin/env python3
# NOT (lider): `durum` sütunu lider tarafından sonradan eklendi (yasak_katlama/dca/izgara, veri_yok, ml, arac_sablon, gecersiz_lookahead, test_edilebilir); bu betik yeniden çalıştırılırsa o sütun kaybolur.
# -*- coding: utf-8 -*-
"""Dış kaynaklı strateji envanteri.

Kaynaklar (yalnız metin okunur, arşiv kodu çalıştırılmaz):
- arsiv/strateji-sg/tv/pine ve tv_eleme_dali/pine (TradingView Pine betikleri), eleme sonuçları
- arsiv/algo-sg/dis_kaynak/ft/strategies (freqtrade), sonuc_freqtrade*.csv
- arsiv/algo-sg/dis_kaynak/sonuc_kural.csv (kurallar.py), sonuc_awesome.csv, sonuc_jesuistm.csv

Çıktı: stratejiler/dis_envanter.csv (bir satır = bir strateji).
Otomatik alanlar: kaynak, ad, dosya, onceki_sonuc, zaman_dilimi (dosyada açıkça yazılıysa).
Elle özetlenen alanlar (gostergeler, mekanik_ozet, kategori, benzer_1l3a_aile, veri_ihtiyaci):
aşağıdaki ANN_* sözlükleri; dosyalar okunarak yazıldı, uydurma değil. Tek istisna: TV
DCA/ızgara şablonları (_tv_otomatik) analiz notundaki standart cümleden türetilir.

Kullanım: python3 araclar/dis_envanter.py   (CSV'yi yazar ve özeti basar)
"""
import collections
import csv
import json
import os
import re


# ANN_TV: ad/id -> (gostergeler, mekanik_ozet, kategori, benzer_1l3a_aile, veri_ihtiyaci)
ANN_TV = {
 "0vvrOpg1": [
  "HalfTrend",
  "HalfTrend yön değişince long/short; ters sinyalde çevirir.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "0wggzSk5": [
  "RSI",
  "RSI sinyalinde taban emri; düşen sapmalarda ek alım, ortalama maliyetten kâr; zarar-durdur yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "14l4u5gJ": [
  "Likidite süpürme, ATR",
  "Likidite süpürme sinyalinde pozisyonu katlayarak ekler; ortalama giriş ±1.5 ATR, stop yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "25Ffpyo0": [
  "Hacim, SMA20, tepe/dip seviyeleri",
  "Onaylı tepe/dip seviyesi hacimle süpürülüp geri kapanınca ters yönde giriş.",
  "kirilim",
  "swing__sahte-kirilim",
  "ohlcv"
 ],
 "2SC4QXCp": [
  "RSI",
  "Short DCA: RSI sinyalinde taban emri, yükselen sapmalarda katlamalı ek emirler; SL var.",
  "diger",
  "",
  "ohlcv"
 ],
 "2lGyzYkC": [
  "Dış sinyal (ext_source)",
  "Strateji şablonu: giriş dışarıdan gelen sinyale bağlı, kendi sinyali yok.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "2wyXTTMc": [
  "SMA200, gerçekleşen oynaklık",
  "SMA200 üstünde oynaklığa göre maruziyet; haftalık yeniden dengeleme, rejim bozulunca tam çıkış.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "3SHJZytF": [
  "HMA(50), Supertrend",
  "HMA ve Supertrend aynı yönde olunca giriş; çelişkide (choppy) çıkış.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "3VLM19TH": [
  "Fiyat aralığı (ızgara)",
  "Sabit aralıkta 23 seviyeli ızgara: seviye altında alım, üst seviyede satım; stop yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "3fea8k4Z": [
  "HMA(34), CCI(25), CCI(50), ATR, EMA20",
  "HMA üstü kapanış ve CCI pozitifken long; 1.75 ATR stop, EMA20 altında çıkış.",
  "trend_takip",
  "swing__cci-esik",
  "ohlcv"
 ],
 "3k4TWbWm": [
  "Trend rezonansı",
  "Çin A-hisse uzun trend rezonansı; Çin borsa verisi ve sembolleri gerektirir.",
  "trend_takip",
  "",
  "ohlcv+diger"
 ],
 "3wdQu7P3": [
  "ATR, MFI(14), AlphaTrend",
  "AlphaTrend izleyen çizgisi AT, AT[2]'yi keserse yön değiştirir.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "49jNhJXM": [
  "Mum örüntüsü, RSI(14)",
  "Kırmızı mumdan sonra 5 ardışık yeşil mum ve RSI>40 yükselirse long; stop ana mum dibi, hedef 1.5R.",
  "formasyon",
  "swing__mum-coklu-formasyon",
  "ohlcv"
 ],
 "4OsZ6QMo": [
  "RSI",
  "Long DCA: RSI sinyalinde taban emri; düşen sapmalarda ek alım, ortalamaya göre kâr; zarar-durdur yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "4jxYYaGU": [
  "İz süren stop/hedef",
  "Kendi girişi olmayan yardımcı: kullanıcı sinyaline bağlı iz süren stop ve hedef uygular.",
  "diger",
  "",
  "ohlcv"
 ],
 "5Tg2Es4G": [
  "RSI",
  "BTC için long DCA botu (webhook/3Commas): RSI girişli, ek alımlı; ortalama maliyete göre çıkış.",
  "diger",
  "",
  "ohlcv"
 ],
 "6HYQYnFl": [
  "Açılış aralığı (30 dk), hacim",
  "MNQ 1 dk: ilk 30 dk aralık kırılımı, hacim patlaması, iki kademeli kâr alma; gün sonu kapanış.",
  "kirilim",
  "daytrade__orb",
  "ohlcv"
 ],
 "6XPbhz9C": [
  "Tepe düşüşü, IBS, SMA50, ATR",
  "10g tepe ve ort. aralığa göre düşüşte IBS<0.3 ve SMA50 üstünde long; 2 ATR stop, iki bacakta çıkış.",
  "ortalamaya_donus",
  "",
  "ohlcv+diger"
 ],
 "6kaqC3R8": [
  "RSI, VWAP",
  "RSI/VWAP sinyalinde taban emir, ortalama düşüren ek emirler (3Commas); ortalamaya göre çıkış.",
  "diger",
  "",
  "ohlcv"
 ],
 "6ve1ax1D": [
  "ORB, FVG, OTE, BOS/MSS, likidite süpürme",
  "NQ/MNQ çok girişli süper scalper; 20 kademeli ekleme ve 20 desenli akıllı çıkış.",
  "diger",
  "",
  "ohlcv"
 ],
 "6zYF9Xts": [
  "Supertrend(3.11, 16)",
  "Supertrend yön değişiminde long/short; her zaman piyasada (ters çevirme).",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "71yKm18B": [
  "Ichimoku (20/60/120), MFI",
  "Tenkan Kijun'u yukarı keser, fiyat bulut üstünde ve MFI>50 ise long; Kijun altında çıkış.",
  "trend_takip",
  "swing__ichimoku",
  "ohlcv"
 ],
 "7OLnQI4B": [
  "Açılış aralığı (08:30-09:30 Chicago)",
  "Açılış aralığında süpürme-dönüş; 50 puan kâr, 25 puan stop.",
  "kirilim",
  "daytrade__orb",
  "ohlcv"
 ],
 "7SSRGEbI": [
  "Açılış aralığı (09:30-09:45 NY), ATR",
  "NY açılış aralığı kırılımı (09:45-11:30), ATR tabanlı stop-hedef; 11:30'da kesim.",
  "kirilim",
  "daytrade__orb",
  "ohlcv"
 ],
 "7UNWrm2O": [
  "T3 (RSI uzunluklu), BB, KC, LazyBear momentum",
  "RSI'ye göre uzunluğu değişen T3 yön değiştirir; sıkışma ve momentum aynı yönde ise long/short.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "7cAVZopZ": [
  "Fiyat aralığı (ızgara)",
  "Sabit aralıkta 36 seviyeli ızgara; seviye altında alım, üst seviyede satım; stop yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "83hmaEOQ": [
  "EMA200, ADX(20), swing, FVG",
  "EMA200 trendinde likidite süpürme, yapı kırılımı ve FVG geri çekilmesinde giriş; iki bacaklı çıkış.",
  "diger",
  "",
  "ohlcv"
 ],
 "8I2576zL": [
  "Son 2 mum değişimi, ATR(14)",
  "ONE/USDT: iki mumda %5-7 düşüşte long; tepe kırılımı veya ATR izleyen stop ile çıkış.",
  "ortalamaya_donus",
  "",
  "ohlcv"
 ],
 "8K1gTPV0": [
  "RSI",
  "Long DCA (katlamalı): RSI girişli taban emir, sapmada katlanan ek alımlar; ortalamaya göre çıkış.",
  "diger",
  "",
  "ohlcv"
 ],
 "8OS1nbr8": [
  "Zarar serisi",
  "Martingale botu: zarar sonrası üstel pozisyon artışı; kesin ret kuralına girer.",
  "diger",
  "",
  "ohlcv"
 ],
 "8Ti8z8QO": [
  "RSI (15dk/1s/4s), Stoch K/D, ATR",
  "Üç zaman dilimi RSI skoru aynı yönde ve 15dk Stoch kesişimi → giriş; 1.5 ATR stop, 3 ATR hedef.",
  "momentum",
  "",
  "ohlcv"
 ],
 "8z6wbyw5": [
  "Kullanıcı seçimli göstergeler",
  "Kullanıcının seçtiği göstergelerle giriş kuralı kurduğu şablon; kendi strateji mantığı yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "95JBkzXV": [
  "RSI(14), Bollinger",
  "RSI<30 ve alt banda değmede long, RSI>70 ve üst bantta short; RSI 50 veya orta bantla çıkış.",
  "ortalamaya_donus",
  "swing__rsi-asiri-donus",
  "ohlcv"
 ],
 "97gxVA5b": [
  "BB genişlik yüzdeliği, SMA20/200, ATR",
  "Bant genişliği sıkışması ve 20g tepe kırılımı, hacim ve SMA200 üstünde long; 2 ATR stop, izleyen stop.",
  "kirilim",
  "swing__bb-sikisma-kirilim",
  "ohlcv"
 ],
 "9Iwinz7I": [
  "Stokastik",
  "Stoch kesişiminde giriş, sabit 100 tick kâr hedefi, her sinyalde ekleme; stop yok.",
  "momentum",
  "scalp__stokastik-donus",
  "ohlcv"
 ],
 "9cxy1Yu9": [
  "Sıkışma momentumu, EMA50, BTC EMA50",
  "Sıkışma momentumu yukarı dönünce ve fiyat EMA50 üstünde (BTC filtresi) long; eğim dönünce çıkış.",
  "trend_takip",
  "",
  "ohlcv+diger"
 ],
 "9qFCuXqF": [
  "Donchian(20), 10 mum çıkış",
  "20 mum Donchian kırılımında long/short; 10 mum dip/tepeyle izleyen çıkış.",
  "kirilim",
  "swing__donchian-kirilim",
  "ohlcv"
 ],
 "AeYVHi9k": [
  "Açılış aralığı, CHoCH, FVG, ATR",
  "ABD seansında ORB, CHoCH ve FVG birleşimiyle kapanışta giriş; ATR izleyen stop, 2R hedef.",
  "kirilim",
  "daytrade__orb",
  "ohlcv"
 ],
 "B7MQqWes": [
  "RSI(14), MFI, EWO, hacim",
  "RSI 40/60 kesişimi, MFI, EWO ve hacim teyidiyle long/short; ters sinyalde döner.",
  "momentum",
  "swing__rsi-momentum-esik",
  "ohlcv"
 ],
 "BtDUET5k": [
  "MACD, Stoch (günlük), ATR, EMA20",
  "MACD sinyal kesişimi ve günlük Stoch K>D (K<80) ile long; 1.75 ATR stop, EMA20 altında çıkış.",
  "momentum",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "CItvSvqk": [
  "Pivot direnç/destek, hacim, EMA200, ATR",
  "Pivot direnci hacimle yukarı kırılıp EMA200 üstündeyse long; destek kırılırsa short.",
  "kirilim",
  "swing__konsolidasyon-kirilim",
  "ohlcv"
 ],
 "CtFpKECD": [
  "Heikin Ashi, SuperTrend(3.44), ADX(22), hacim",
  "HA mum desenleri, SuperTrend yönü, ADX≥22 ve yapı filtresiyle seans içinde giriş; 1R hedef.",
  "trend_takip",
  "swing__heikin-ashi-donus",
  "ohlcv"
 ],
 "DG9ePZuk": [
  "SuperTrend(10,3,hl2)",
  "SuperTrend yön değişimi bir mum gecikmeli uygulanır; %8 stop, sonra %2.5 izleyen stop.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "DkDNMQsn": [
  "Dar aralık kümelenmesi, ATR, hacim",
  "10 mumluk dar aralık kırılımı ve hacim onayı; seans sonu kapanış, %0.5 stop, kısmi kâr.",
  "kirilim",
  "daytrade__konsolidasyon-kirilim",
  "ohlcv"
 ],
 "DwdC6FT4": [
  "Pivot merkezi, ATR(x3) bantları",
  "Pivot merkez çizgisi ±ATR×3 bantları; trend dönüşünde yön değiştirir.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "EA1AXZui": [
  "Seans VWAP, sapma",
  "Seans VWAP'inden ters dönüş; 13:30-20:00 UTC arası işlem.",
  "ortalamaya_donus",
  "daytrade__vwap-donus",
  "ohlcv"
 ],
 "EcEYc8ap": [
  "DMI/ADX, EMA9, EMA50, ATR",
  "DMI yönü ve ADX≥20 trendinde EMA9'a geri çekilip yeniden yukarı çıkınca long; chandelier stop.",
  "trend_takip",
  "swing__ma-geri-cekilme",
  "ohlcv"
 ],
 "EjLwVtgp": [
  "Fraktal tepe ve dipleri",
  "Son üç fraktal tepe ortalaması yükselirken fiyat son fraktali kırarsa long; 3 bar içinde bozulursa çıkış.",
  "kirilim",
  "",
  "ohlcv"
 ],
 "Eq4kPrrJ": [
  "Tepe/dip yapısı (30 mum), EMA200, ATR(20)",
  "Tepe/dip yapısıyla yön; yukarıda EMA200 ve geniş aralıkta yeni long; yön dönünce çıkar; 8 ATR felaket stopu.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "ErcSuPyN": [
  "Awesome Oscillator (AC), EMA100",
  "AC dönüş desenlerinde stop-giriş; fiyat EMA100 üstünde; trend dönünce tüm kademeler kapanır.",
  "momentum",
  "",
  "ohlcv"
 ],
 "FDeprmix": [
  "Supertrend, Donchian kanal, HTF Supertrend, hacim",
  "Supertrend ve 4s üst zaman dilimi yükselişte, hacimli Donchian kırılımında long; ATR stop ve hedef.",
  "kirilim",
  "swing__donchian-kirilim",
  "ohlcv"
 ],
 "FJZvYKaB": [
  "Açılış aralığı (13:00 UTC), hacim, ATR",
  "13:00 UTC açılış aralığı tepesinin yukarı kırılımında long (14:00-16:30); stop aralık, hedef 2.5 aralık.",
  "kirilim",
  "daytrade__orb",
  "ohlcv"
 ],
 "Fckzv8iH": [
  "LazyBear sıkışma momentumu, KC/BB",
  "Momentum sıfırın altında yukarı dönünce long, üstünde aşağı dönünce short; hep piyasada.",
  "momentum",
  "",
  "ohlcv"
 ],
 "G40dtEbK": [
  "Sıkışma (BB/KC), momentum",
  "Sıkışma bitince momentum yükseliyorsa long (düşüyorsa short); momentum ters dönünce çıkış.",
  "kirilim",
  "swing__bb-sikisma-kirilim",
  "ohlcv"
 ],
 "G5ro3y87": [
  "Stochastic %K/%D, MACD histogramı",
  "Aşırı bölgede Stoch %K/%D kesişimi ve MACD histogram sıfır kesişimiyle giriş.",
  "momentum",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "GM1bUrIF": [
  "RSI, VWAP",
  "INJ için 3Commas DCA: RSI/VWAP taban emri, ortalama düşüren ek emirler; ortalamaya göre çıkış.",
  "diger",
  "",
  "ohlcv"
 ],
 "GhH6mW5c": [
  "RSI",
  "Long DCA (katlamalı): RSI girişli taban emir, sapmada ek alımlar; ortalamaya göre kâr; stop yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "GoeqO1ev": [
  "Swing tepe/dip likidite seviyeleri, hacim, ATR",
  "Likidite seviyesi iğneyle aşılıp içeride kapanınca, onay mumuyla ters yönde giriş; stop iğne ±1.2 ATR, 1.5R hedef.",
  "kirilim",
  "swing__sahte-kirilim",
  "ohlcv"
 ],
 "H2U52D79": [
  "Fiyat aralığı (ızgara)",
  "Sabit aralıkta 67 seviyeli ızgara: seviye altında alım, üst seviyede satım; stop yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "HDSdFMa3": [
  "RSI(6), Bollinger(200,2)",
  "RSI(6) 50'yi yukarı keser ve kapanış BB alt bandını yukarı keserse long; 50 aşağı kesişince çıkış.",
  "momentum",
  "swing__rsi-momentum-esik",
  "ohlcv"
 ],
 "HPbRZvsV": [
  "VAR(2), OTT (%1.4)",
  "VAR ile OTT bandı kesişimi: fiyat OTT'yi yukarı keserse long, VAR aşağı keserse short; hep piyasada.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "Hrc7Gfqe": [
  "McGinley Dynamic(65), ATR(28)",
  "McGinley bantlı iz süren çizgi yön değiştirince giriş; kademeli kâr alma (1R/2R/3R) ve iz süren çıkış.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "HyzpDR9t": [
  "Awesome Oscillator, fraktal, EMA100",
  "Trend onayında AO tabak deseninde sinyal tepesine stop-giriş; trend aşağı dönünce tüm kademeler kapanır.",
  "momentum",
  "",
  "ohlcv"
 ],
 "IGJPEi7L": [
  "Stochastic %K/%D, RSI",
  "Aşırı bölgede Stoch %K/%D kesişimi ve RSI eşik kesişimiyle long/short.",
  "momentum",
  "scalp__stokastik-donus",
  "ohlcv"
 ],
 "IHVPG6TS": [
  "SMA(14), SMA(28)",
  "SMA14/SMA28 kesişiminde yön değiştirir (TradingView örnek stratejisi); asıl konu emir mekaniği.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "Ip667jzb": [
  "MA kesişimi",
  "Hareketli ortalama kesişimiyle giriş; ayrıntılı kural kaynak modülündedir.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "IqUET4xO": [
  "Alligator, fraktal, ATR yüzdeliği",
  "Alligator dişi üstünde yukarı fraktalda stop-giriş (düşük oynaklıkta); stop %3 ya da aşağı fraktal.",
  "kirilim",
  "",
  "ohlcv"
 ],
 "IvMdQJNW": [
  "Fiyat aralığı (ızgara)",
  "Sabit aralıkta 37 seviyeli ızgara: seviye altında alım, üst seviyede satım; stop yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "JtopWlYQ": [
  "RSI",
  "Long DCA (katlamalı): RSI girişli taban emir, sapmada ek alımlar; ortalamaya göre kâr; stop yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "KOfsPM9h": [
  "Pivot seviyeleri, hacim osilatörü, EMA150, ATR",
  "NSE 5 dk: pivot kırılımı, hacim eşiği ve EMA150 filtresi; ATR×3.2 izleyen stop; gün sonu kapanış.",
  "kirilim",
  "daytrade__pivot-seviye",
  "ohlcv"
 ],
 "KX7AgFeB": [
  "Açılış aralığı (08:30-15:00), Fibonacci",
  "08:30-15:00 açılış aralığı kırılımı ve Fibonacci seviyeleriyle gün içi giriş.",
  "kirilim",
  "daytrade__orb",
  "ohlcv"
 ],
 "LcA4mcE6": [
  "EMA55/233, RSI, verimlilik oranı, oynaklık yüzdeliği, hacim",
  "Beş bileşenli 0-100 skor; ≥85 olunca giriş, <35 olunca çıkış; 3 ATR izleyen stop.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "M6uONKNI": [
  "BB taşma osilatörü (14), ATR(30)",
  "Bollinger taşma gücü osilatörü sıkışma sonrası 50'yi keserse long/short; 1.4 ATR stop, 1.5R hedef.",
  "kirilim",
  "swing__bb-sikisma-kirilim",
  "ohlcv"
 ],
 "M9taaIkp": [
  "Seçilen osilatör",
  "Seçilen osilatörün sinyallerini arka arkaya işleyen analiz aracı; bağımsız strateji mantığı yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "MQDDEl1e": [
  "Mum içi hacim/emir akışı yaklaşıklaması",
  "Mum içi emir akışını yaklaşıklayan göstergelerle giriş (pyramiding=3); gerçek emir akışı verisi yok.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "MvlwAzSg": [
  "EMA21, EMA50, ATR",
  "EMA21 EMA50'yi yukarı keserse long, aşağı keserse short; 5 mum dip/tepe stop, 1R hedef.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "N1OCoFkf": [
  "BB genişliği, ATR, hacim",
  "BB sıkışması (genişlik ortalamanın %80 altı) sonrası bant kırılımı ve hacimle giriş; ATR×1.5 stop, ATR×3 hedef.",
  "kirilim",
  "swing__bb-sikisma-kirilim",
  "ohlcv"
 ],
 "NJb4BQ5n": [
  "TMA(100) bull/bear çifti",
  "EURUSD: TMA önfiltreli bull/bear çiftinin kesişimiyle long/short; sinyal çizgisi altında kapanışla çıkış.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "NfihxKxr": [
  "Supertrend(2.0,10), SMA20 hacim, SMA50",
  "Supertrend dönüşü, hacim ve SMA50 filtresiyle giriş; %10 hedef, %5 stop; ters dönünce çıkış.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "NgSIfKQx": [
  "Supertrend(10,1.8), EMA200",
  "BTCUSD Supertrend dönüşünde, EMA200 filtresiyle giriş; ters dönüşte pozisyon kapanır.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "OEeqwUwB": [
  "Fiyat aralığı (ızgara)",
  "Sabit aralıkta ızgara: seviye altında alım, üst seviyede satım; stop yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "OUOx3rYT": [
  "EMA21, ATR(10) bantları",
  "EMA21 ± 2 ATR izleyen bantlar; yön dönüşünde ve geri çekilmede giriş; bant stop, 2R hedef.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "OvE4qQgh": [
  "Likidite süpürme, delta (alt TF hacim farkı), swing",
  "Swing tepe/dip iğne taraması ve alt zaman dilimi hacim farkı (delta) emilimi; ters yönde giriş, R hedef.",
  "kirilim",
  "swing__sahte-kirilim",
  "ohlcv"
 ],
 "P5Gu6F8k": [
  "SuperTrend (ATR10×3, hl2)",
  "SuperTrend yön dönüşünde giriş; hep piyasada (long/short).",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "PETNavGq": [
  "CCI(14), CCI25, CCI50, MFI, EMA50/20, ATR",
  "CCI sıfırı yukarı keser, CCI25/50 ve MFI teyidiyle long; 1.75 ATR stop, EMA20 altında çıkış.",
  "momentum",
  "swing__cci-esik",
  "ohlcv"
 ],
 "PdJvHIfQ": [
  "Önceki gün tepe/dip seviyeleri, pivot",
  "Önceki günün tepe/dip seviyesinde kırılım sonrası onayla giriş; stop son pivot, 2R hedef.",
  "kirilim",
  "swing__seviye-tepki",
  "ohlcv"
 ],
 "Pv1GvUVs": [
  "KST, LSMA200, Alligator, Choppiness, ATR",
  "KST yukarı keser, fiyat LSMA200 ve Alligator üstündeyse long; 1.5 ATR stop, 3.5 ATR hedef.",
  "momentum",
  "",
  "ohlcv"
 ],
 "Qg1Jra51": [
  "RSI, pivot dip/tepe",
  "RSI'de iki dip uyumsuzluğu ve RSI zirvesinin kırılımında long; hedef iki dip arası fiyat zirvesi.",
  "momentum",
  "swing__rsi-diverjans",
  "ohlcv"
 ],
 "SBFz8vXU": [
  "Fiyat aralığı (ızgara)",
  "Sabit aralıkta 20 seviyeli ızgara: seviye altında alım, üst seviyede satım; stop yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "Sg2qyDDe": [
  "KAMA, Kalman filtresi, pivot BOS/CHoCH",
  "Trend yönü ve yapı kırılımı (BOS/CHoCH) birlikte görülünce giriş; 3 ATR stop, ters sinyalde çıkış.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "T5kd1bJ2": [
  "Gauss filtresi, ATR filtreli TR, Stoch(RSI)",
  "Gauss filtresi yükselirken kapanış bant üstündeyse ve Stoch(RSI) K>D ise long; bant altında çıkış.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "TDxSLJRA": [
  "Williams VIX Fix, StochRSI",
  "VIX Fix filtreli dip dönüşünde long; stokastik aşırı alım kesişiminde çıkış; yalnız long.",
  "ortalamaya_donus",
  "",
  "ohlcv"
 ],
 "TJuVmOfk": [
  "Williams %R(14), Supertrend",
  "Williams %R −80'i yukarı keserse long, −20'yi aşağı keserse short; Supertrend süzgeci; ters sinyalde döner.",
  "momentum",
  "scalp__stokastik-donus",
  "ohlcv"
 ],
 "TbK1rB5B": [
  "Supertrend, ADX (rejim)",
  "ADX ile rejim seçimi: trendde Supertrend çarpanı 1.75, yatayda yeni giriş kapalı; dönüşte yön değiştirir.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "Tkrjao7P": [
  "AO/AC, Alligator, EMA100",
  "AO ve AC yükselirken yeşil bar serisinde giriş, en çok 5 kademe; trend dönünce ya da seri kırılınca kapanış.",
  "momentum",
  "",
  "ohlcv"
 ],
 "U0wTnRuE": [
  "Range Filter, Heikin-Ashi, SMI, 1s HA",
  "Range Filter ve HA yönleri aynıysa (üst zaman dilimi HA teyidi) giriş; 2.5 ATR izleyen stop, RF ters dönünce çıkış.",
  "trend_takip",
  "scalp__heikin-ashi-donus",
  "ohlcv"
 ],
 "U3mcySX9": [
  "Teknik özet, kalabalık görüşü",
  "Teknik özet ile dış 'kalabalık görüşü' verisini birleştirir; ek veri kaynağı gerektirir.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "UVosPbFA": [
  "MACD(14,39,9), EMA99, ADX(11), hacim",
  "Taze MACD kesişimi, EMA99 trendi, ADX>20 ve hacim filtresiyle giriş; 2.5 ATR acil stop, kâr koruma çıkışı.",
  "trend_takip",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "V87nRt9v": [
  "MACD, EMA200, ADX(20), ATR",
  "MACD yukarı kesişimi, fiyat EMA200 üstünde, MACD sıfırın altında ve ADX>20 ise long; 2 ATR stop, 2R hedef.",
  "momentum",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "VFzCk3HX": [
  "Mahsul takvimi, fiyat seviyeleri",
  "Tarım vadeli ürünlerinde mahsul takvimine göre kademeli short satış; hedge mantığı; ek veri gerekir.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "VO6DY8s1": [
  "VAR-MACD (12,26), VAR(9)",
  "VAR hareketli ortalamalı MACD histogramı sıfırı keserse yön değiştirir.",
  "momentum",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "VuYM89Tw": [
  "ATR(480)×14 izleyen çizgi (Activator)",
  "Uzun ATR tabanlı izleyen çizgiyle kesişimde yön değiştirir (Grover Llorens Activator).",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "W67tJltC": [
  "ROC, RSI, hacim z-skoru",
  "ROC, RSI ve hacim z-skorlarının uyarlamalı bileşiği sıfırı keserse giriş (ATR×2 stop), ters kesişimde çıkış.",
  "momentum",
  "",
  "ohlcv"
 ],
 "WpJ5ym7u": [
  "Pivot SuperTrend, KivancST, SMA20",
  "Pivot merkezli SuperTrend yön değişimi ya da KivancST dönüşü + SMA20 yönü; hep piyasada.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "X0F9OE4L": [
  "EMA(8-55) yelpazesi, RSI, hacim, ATR",
  "Beş EMA yelpazesi açılırken RSI ve hacim süzgecinde giriş; ATR×2 stop, 2R hedef, yelpaze kapanınca çıkış.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "XGqSzuxJ": [
  "EMA50 (günlük), RSI(4s), MACD, yutan mum, ATR, hacim",
  "BTC: günlük EMA50 ve 4s RSI süzgeciyle, MACD+yutan mum+hacim patlamasında giriş; SL sonrası ters yön, 24 saat bekleme.",
  "formasyon",
  "swing__mum-yutan-donus",
  "ohlcv"
 ],
 "XK8XbDhT": [
  "Günlük kapanış karşılaştırması",
  "Son günün kapanışı bir öncekinden yüksekse long, düşükse short; en basit kapanış karşılaştırması.",
  "momentum",
  "",
  "ohlcv"
 ],
 "XRZCjbFr": [
  "50g kanal konumu, SMA200, ATR",
  "Kanalın alt %25 bölgesinde ve SMA200 üstünde long; kanal ortasında hedef, kanal altı ATR stop.",
  "ortalamaya_donus",
  "swing__aralik-ticareti",
  "ohlcv"
 ],
 "YfPnKE22": [
  "DEMA(12/25) MACD, SMA15, Heikin Ashi",
  "Heikin Ashi üzerinde DEMA MACD'nin sıfır kesişimiyle long/short; %10 hedef, %3 stop.",
  "momentum",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "ZLcmWQtj": [
  "RSI üzerinde T3, PMax (RSI-ATR)",
  "RSI üzerinde T3 ve PMax; T3 PMax'i yukarı keserse long, aşağı keserse short; hep piyasada.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "Za5HKgrL": [
  "FVG (boşluk), NY açılışı",
  "10:00 NY'de ilk FVG tespitinde gün içi giriş; kısa vadeli ve tek olay.",
  "diger",
  "",
  "ohlcv"
 ],
 "bA9UFcgj": [
  "SMA250, SMA5, RSI(3)",
  "SMA250'nin %2 altında, SMA5 üstünde RSI(3) 70'i yukarı keserse short (SPY); SMA5 altı ya da SMA250 üstünde çıkış.",
  "ortalamaya_donus",
  "",
  "ohlcv"
 ],
 "bFXf4IXh": [
  "EMA(20), ATR(10) bandı",
  "EMA20 ± ATR bandının üst bandı kırılınca stop-al; TP/SL kapalı; Kelly boyutlandırma çevrilmedi.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "bajhb6V9": [
  "Yutan mum (engulfing), pivot bölgesi",
  "Trend yönünde yutan mum ve pivot bölgesi dokunuşunda giriş; ortalamanın altında 5 kademeli ekleme, stop yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "boHD0HzE": [
  "Ichimoku (tenkan, kijun, bulut, chikou)",
  "Tenkan/Kijun kesişimi, pozitif bulut ve fiyat bulut üstünde ise long (tersi short); ters kesişimde çıkış.",
  "trend_takip",
  "swing__ichimoku",
  "ohlcv"
 ],
 "cJhpIJ2w": [
  "Stokastik %K(250), VAR(50), OTT",
  "Stokastik tabanlı VAR serisine OTT uygulanır; seri OTT[2]'yi keserse yön değiştirir.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "d117dN6D": [
  "SMA(24), SMA(31), CCI(11)",
  "Saatlik SMA24 SMA31'i aşağı keserken ve CCI(11) −80'i aşağı keserse 3 mum içinde long; %3.25 stop, izleyen stop.",
  "ortalamaya_donus",
  "",
  "ohlcv"
 ],
 "d1JxXpid": [
  "Gaussian kanal (144), StochRSI",
  "Gaussian kanal ve StochRSI (K>80 ya da <15) ile giriş; alt bant stop.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "dwgn7hrE": [
  "RSI aralığı sıkışması, EMA50 eğimi, ATR",
  "RSI aralığı sıkışıp kırılırsa EMA50 eğimi yönünde giriş; ATR×2 stop. (Pine hedef hatası düzeltilmiş.)",
  "kirilim",
  "",
  "ohlcv"
 ],
 "dxhgQwyI": [
  "Supertrend(14,3.5), EMA200, ADX(25), DI",
  "Supertrend yönü, EMA200, ADX≥25 ve DI yönü birlikte olunca giriş; Supertrend ters dönünce çıkış.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "eENf7NpJ": [
  "VAR(40), OTT (%1)",
  "VAR ile OTT kesişimi: MAvg OTT'yi yukarı keserse long, aşağı keserse short.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "edChhkxo": [
  "Zigzag pivotları, harmonik oranlar",
  "Zigzag pivotlarından XABCD harmonik oranları (Gartley/Bat/Butterfly/Crab) tespit edilip D'de giriş.",
  "formasyon",
  "swing__harmonik-abcd",
  "ohlcv"
 ],
 "egTb7TgJ": [
  "Gaussian kanal (89), StochRSI, SMA200",
  "Gaussian kanal ve StochRSI K>80 ya da <25 ile SMA200 rejiminde giriş; yeşil mum şartı; alt bant stop.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "erJi1tWf": [
  "Gaussian filtre (144), TR bandı",
  "Fiyat Gaussian orta çizgiyi yukarı keserse long, aşağı keserse short; filtrelenmiş TR bandı.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "fmPC9fWd": [
  "NQ hacim şoku",
  "Chicago saatinde NQ hacim şokuna tepki veren gün içi kural; kısa vadeli.",
  "diger",
  "",
  "ohlcv"
 ],
 "gU6RDuh5": [
  "Harici gösterge çıktısı",
  "Başka bir göstergenin çıktısını giriş/çıkış olarak okuyan şablon; kendi mantığı yok.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "ghocsiv7": [
  "Açılış boşluğu (gap)",
  "Seans açılış boşluğunu kapanışa doğru ters yönde işlemek; hedef boşluk dolumu, stop yok, seans sonu çıkış.",
  "ortalamaya_donus",
  "daytrade__gap-doldurma",
  "ohlcv"
 ],
 "gqaZYhUN": [
  "Donchian(20) zirve, hacim, EMA20/50, RSI, ATR",
  "20 mum zirve kırılımı, hacim ve EMA20>EMA50 ile long; düşüş trendinde zayıf kırılım short; ATR stoplar.",
  "kirilim",
  "swing__donchian-kirilim",
  "ohlcv"
 ],
 "hezSShJr": [
  "SMA50/150/200, dar aralık, hacim",
  "SMA50>150>200 yükselen trendde sıkışma sonrası hacimli zirve kırılımında stop-giriş; %8 stop, kademeli kâr al.",
  "kirilim",
  "swing__konsolidasyon-kirilim",
  "ohlcv"
 ],
 "hoCPm5UY": [
  "bar_index",
  "Pozisyon boyutu örneği: belirli bar indekslerinde rastgele long/short; strateji mantığı yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "i3Uc79fF": [
  "BB(20,1σ), RSI(42/70)",
  "BB alt bandın altında ve RSI>42 ise long; üst bandın üstünde ve RSI>70 ise çıkış; SL/TP yok.",
  "ortalamaya_donus",
  "scalp__bant-donus",
  "ohlcv"
 ],
 "i9tJOtjl": [
  "LUBE: aralık oranı (sürtünme), FIR eğimi",
  "Son 500 mumda bugünkü kapanışı içeren aralık oranı düşükken FIR eğimine göre long/short; orta eşikte çıkış.",
  "diger",
  "",
  "ohlcv"
 ],
 "jd1KSVn7": [
  "HMA(8), HMA(9), HMA(20), ATR",
  "HMA(8)>HMA(9)>HMA(20) rejimi başlarsa long; MFE≥1.5 ATR sonrası tepeden %5.75 izleyen stop.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "jjhUHcje": [
  "SMA(14), SMA(28)",
  "TradingView örnek stratejisi: SMA14/SMA28 kesişiminde yalnız long, kademeli izleyen stop örneği.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "kAYwdfND": [
  "30 dk pivot destek/direnç, hacim deltası",
  "30 dk pivotlarını destek/direnç alır; 5 dk mumda hacim deltası ve fiyat koşuluna göre ters yönde giriş.",
  "destek_direnc",
  "swing__seviye-tepki",
  "ohlcv"
 ],
 "kbYTJ8V2": [
  "KAMA(10), SMA200",
  "KAMA(10) 3 bar yükselir ve fiyat SMA200 üstündeyse long (aşağıda short); %4 stop, %6 izleyen stop.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "kzp8e4X3": [
  "Pivot tepe/dip (2 sol/1 sağ)",
  "Onaylı pivot tepesinin üstüne stop-al, pivot dibinde stop-sat emri; hep piyasada.",
  "kirilim",
  "",
  "ohlcv"
 ],
 "lDGmh7ou": [
  "UT Bot, ATR(10)",
  "ATR izleyen stop çizgisini fiyat kesince yön değiştirir (UT Bot v2).",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "m1JDhFR9": [
  "EMA20, EMA50, ATR, yapı filtresi",
  "EMA20/50 trendinde altın kesişim, geri çekilme ya da sıkışma kırılımında giriş; ATR izleyen stop.",
  "trend_takip",
  "swing__ma-geri-cekilme",
  "ohlcv"
 ],
 "mfw4fJST": [
  "VIX MACD(12,26,9)",
  "VIX'in MACD'si aşağı keserse endeks long (korku azalıyor), yukarı keserse çıkar.",
  "momentum",
  "swing__macd-sinyal",
  "ohlcv+diger"
 ],
 "mmrInMTp": [
  "Mum dizisi (5 yeşil mum)",
  "Kırmızı ana mumdan sonra 5 ardışık yeşil mum → long; stop ana mum dibi, hedef 1.5R.",
  "formasyon",
  "swing__mum-coklu-formasyon",
  "ohlcv"
 ],
 "mpjNqADq": [
  "SuperTrend(10,3,hl2), EMA50, hacim, rejim",
  "Rejime göre çarpanlı SuperTrend yön dönüşünde 5 bileşenli skor ≥65 ve EMA50 uyumunda giriş.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "mqh6UJ9p": [
  "ATR, ATR-SMA(45), RSI(15)",
  "ATR oynaklık bandında RSI(15)>60 ise long, <40 ise short; tepeden %1.5 izleyen stop, hedef %3/%6.",
  "momentum",
  "",
  "ohlcv"
 ],
 "mzv5SGie": [
  "EMA150, ABD 10Y faizi, 20g tepe",
  "Gümüşte hep long; EMA150 altı, makro faiz tetikleri veya ani düşüşte çıkış.",
  "trend_takip",
  "",
  "ohlcv+diger"
 ],
 "n8bgynWl": [
  "Trailing emir altyapısı",
  "Giriş türleri ve izleyen emirler için altyapı şablonu; sinyali dışarıdan gelir, kendi mantığı yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "n9ty3SVh": [
  "SuperTrend(ATR 15, çarpan 9.1, hl2)",
  "Geniş çarpanlı SuperTrend yön değişiminde long/short; hep piyasada.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "nHGK4Qtp": [
  "PMax, EMA(hl2,10), ATR(10)×3",
  "EMA(hl2,10) PMax çizgisini yukarı keserse long, aşağı keserse short.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "nRklAGPI": [
  "SPY/QQQ EMA10/21, ADX(13), SMA7, BTC",
  "QQQ long-only makro sistem: SPY ve QQQ EMA koşullarıyla giriş, makro çıkış; düşüş sınırı hedefi.",
  "trend_takip",
  "",
  "ohlcv+diger"
 ],
 "nVECqIQx": [
  "Haftalık açılış limiti",
  "Pazartesi açılışının %1 altına limit alış; +%1 hedef; cuma kapanışında çıkış.",
  "ortalamaya_donus",
  "",
  "ohlcv"
 ],
 "njQsSFjo": [
  "EMA9/21/50, VWAP, RSI(5), HTF",
  "EMA trendinde geri çekilme veya 20 mum kırılımıyla giriş; üst zaman dilimi yönüne ters işlem yok.",
  "trend_takip",
  "swing__ma-geri-cekilme",
  "ohlcv"
 ],
 "nuqVC5F7": [
  "RSI(100), Heikin Ashi",
  "RSI(100)>46 ve 7 ardışık yükselen HA mumunda short; %2.1 hedef, %2.5 stop.",
  "ortalamaya_donus",
  "",
  "ohlcv"
 ],
 "o9dV6uWc": [
  "EMA38/62, MTF Stochastic, ATR",
  "EMA38>EMA62 trendinde 4s Stoch K 50'yi yukarı keserken yerel K>D → long; ATR stop, 1.5R sonrası izleyen stop.",
  "momentum",
  "swing__stokastik-donus",
  "ohlcv"
 ],
 "ouvmvItR": [
  "Order block (itki mumu), hacim SMA20, ATR",
  "İtki mumunun önceki mumu order block; bölge ilk kez yeniden test edilip yön mumu kapanınca giriş.",
  "destek_direnc",
  "swing__talep-arz-bolgesi",
  "ohlcv"
 ],
 "pMOjQJwT": [
  "BB(20,2) gecikmeli, saat penceresi",
  "Hafta içi 14:00-14:40 UTC'de BB bandına limit emirle ters işlem; hedef orta band, 14:40'ta kapanış.",
  "ortalamaya_donus",
  "daytrade__bant-donus",
  "ohlcv"
 ],
 "qp9BoNyS": [
  "LazyBear squeeze momentum",
  "Sıkışma bitişinde momentum işaretine göre long/short; momentum ters dönünce çıkış.",
  "kirilim",
  "swing__bb-sikisma-kirilim",
  "ohlcv"
 ],
 "rKsnPJbJ": [
  "Fibonacci seviyeleri (20/50/100 mum), EMA50",
  "Son 20/50/100 mumun fib seviyelerinden biri kapanışa yakınsa ve EMA50 trendi yönünde giriş; %1.5 stop, 2R hedef.",
  "destek_direnc",
  "swing__fib-geri-cekilme",
  "ohlcv"
 ],
 "rvBgD3aP": [
  "ZigZag pivotları, Elliott dalga",
  "ZigZag'da 5 dalgalı itki veya dalga-4 geri çekilişi tespit edilince yön değiştirme ve giriş.",
  "formasyon",
  "",
  "ohlcv"
 ],
 "uCV8I4xA": [
  "RSI(6), Bollinger(200,2)",
  "RSI(6) 50'yi yukarı keser ve fiyat BB alt bandını aşarsa long; RSI 50 aşağı ve üst bant aşağı kesişince short.",
  "ortalamaya_donus",
  "swing__bant-donus",
  "ohlcv"
 ],
 "uycyVpIq": [
  "Ichimoku Tenkan/Kijun, bulut",
  "Tenkan/Kijun yukarı kesişimde long; Tenkan bulut üstündeyken aşağı kesişimde çıkış.",
  "trend_takip",
  "swing__ichimoku",
  "ohlcv"
 ],
 "vWG3tMJh": [
  "Laguerre RSI (alpha 0.2)",
  "Laguerre filtresinin yukarı/aşağı bileşenleri kesişince long/short; hep piyasada.",
  "momentum",
  "",
  "ohlcv"
 ],
 "wVNfdkHu": [
  "WMA(63), WMA(510), SMA(41), RSI(33)",
  "Hızlı ve makro WMA kesişimi; kapanış SMA41 üstünde ve RSI 42-48 bandında ise giriş.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "x39mKkAp": [
  "EMA20, SMA200, ATR",
  "EMA20 ile SMA200 dar aralıktayken trend yönünde gövdeli mum ya da dönüş mumuyla giriş; 2 ATR stop, 2R hedef.",
  "kirilim",
  "swing__dar-aralik-kirilim",
  "ohlcv"
 ],
 "xAEG4ZJG": [
  "SMA(14), SMA(28)",
  "TradingView örnek stratejisi: SMA14/SMA28 kesişimi; yalnız belirli tarih/saat penceresinde işlem.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "xJ5iSXIS": [
  "RSI, VWAP",
  "Tomukas Wave VWAP DCA: RSI/VWAP taban emri, ortalama düşüren ek emirler; ortalamaya göre çıkış.",
  "diger",
  "",
  "ohlcv"
 ],
 "xx3enmiW": [
  "Ichimoku (tenkan/kijun), günlük HTF",
  "Tenkan/Kijun yukarı kesişimi ve günlük Tenkan>Kijun teyidiyle long; 1.5 ATR stop, 3 ATR hedef.",
  "trend_takip",
  "swing__ichimoku",
  "ohlcv"
 ],
 "yMCa3XZD": [
  "SMA200 tabanlı MACD histogramı",
  "SMA tabanlı MACD histogramı sıfırı keser, MACD>0 ve hızlı>yavaş, 26 bar önce kapanış SMA200 üstündeyse long.",
  "trend_takip",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "ycDUERPO": [
  "VAR (OTT periyodu 1), OTT",
  "VAR çizgisi OTT[2]'yi keserse yön değiştirir (destek çizgisi kesişimi).",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "zopumZ8a": [
  "RSI(16), Bollinger(20,2)",
  "RSI(16) 45'i yukarı ve kapanış BB alt bandını yukarı keserse long; RSI 55 aşağı, üst bant aşağı kesişince short.",
  "ortalamaya_donus",
  "swing__bant-donus",
  "ohlcv"
 ],
 "zpIyp7KB": [
  "Initial Balance (ilk saat)",
  "İlk saat aralığı (initial balance) kırılımında gün içi giriş.",
  "kirilim",
  "daytrade__orb",
  "ohlcv"
 ],
 "zudiHFjK": [
  "EMA, ATR (XAU)",
  "XAU 15 dk EMA-ATR kesişimi, sesli uyarı; gün içi.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "oxvR5vMy": [
  "Sabit puan ızgarası, baseline",
  "Sabit puan ızgarasında baseline kayar; zarar sonrası pozisyon katlanır (martingale).",
  "diger",
  "",
  "ohlcv"
 ],
 "rkHHEvJ1": [
  "VWAP, 3. standart sapma",
  "Gün içi VWAP 3. standart sapma bandından ortalamaya dönüş.",
  "ortalamaya_donus",
  "daytrade__vwap-donus",
  "ohlcv"
 ],
 "sk6MVZEb": [
  "Londra/NY aralığı",
  "Londra ve NY seans aralığı kırılımında gün içi giriş (5 dk).",
  "kirilim",
  "daytrade__orb",
  "ohlcv"
 ],
 "t7Tp4qnu": [
  "Açılış aralığı (5 dk ORB)",
  "5 dakikalık açılış aralığı (ORB) kırılımıyla gün içi scalp.",
  "kirilim",
  "daytrade__orb",
  "ohlcv"
 ],
 "sf4Hf10r": [
  "20:00 NY aralık mumu",
  "MGC (mikro altın) 5 dk: 20:00 NY aralık mumu sonrası giriş; $445 risk, $1000 ödül.",
  "kirilim",
  "daytrade__orb",
  "ohlcv"
 ],
 "1OnkbAiE": [
  "Hacim profili (VAH/VAL), hacim ort., ATR, pivot, RSI",
  "Hacim profili değer alanı (VAH/VAL) dışına hacimli kırılımda giriş; sabit stop ve hedef.",
  "kirilim",
  "",
  "ohlcv"
 ],
 "2u7KKcCG": [
  "Trend çizgisi kırılımı, AO, EMA, ADX, ATR",
  "Trend çizgisi kırılımı; AO, EMA ve ADX süzgeçli long/short; sabit stop ve kısmi kâr alma.",
  "kirilim",
  "swing__trend-cizgisi-kanal",
  "ohlcv"
 ],
 "5zL50iGH": [
  "Yuvarlak fiyat seviyeleri (altın), mum yönü",
  "XAU 15 dk: yuvarlak seviye kesişimi ve mum yönüyle alış/satış; sabit stop ve hedef.",
  "destek_direnc",
  "swing__seviye-tepki",
  "ohlcv"
 ],
 "69ZFfJ5L": [
  "XGBoost olasılık modeli, RSI, ATR, EMA",
  "XGBoost olasılık eşiğinde long/short; model periyodik yeniden eğitilir; izleyen stop ile çıkış.",
  "diger",
  "",
  "ohlcv"
 ],
 "6sorh9ZW": [
  "SMA, EMA, VWMA, WMA",
  "Hızlı ve yavaş MA kesişiminde (ya da seçili sinyal kaynağında) long/short; çoklu giriş.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "9IoAQC1M": [
  "Yutan mum, pin bar, S/R bölgeleri, ATR, RSI",
  "Destek/direnç bölgesinde yutan veya pin bar onaylı giriş; kısmi ve tam kâr alma, stop.",
  "formasyon",
  "swing__mum-coklu-formasyon",
  "ohlcv"
 ],
 "Dln4aFaM": [
  "NR7, iç bar (inside day), SMA",
  "Dar aralık (NR7) ve iç bar sonrası yükseliş mumunda long; yalnız uzun, kapanışta çıkış.",
  "kirilim",
  "swing__dar-aralik-kirilim",
  "ohlcv"
 ],
 "GoUoySJs": [
  "MTF yutan mum, günlük/4s teyit, ATR",
  "BTC: MTF yutan mum ve günlük/4s teyidinde giriş; stop sonrası ters yön (flip), piramitleme.",
  "formasyon",
  "",
  "ohlcv"
 ],
 "JeRCEqWU": [
  "Order block, FVG, UT Bot, EMA9/21, MACD, RSI, DMI, VWAP",
  "Order block ve FVG bölgelerinde UT Bot, EMA9/21 kesişimi ve MACD/RSI teyidiyle giriş.",
  "diger",
  "",
  "ohlcv"
 ],
 "L7P3quUz": [
  "VWAP, RSI, DMI/EMA, ATR, VWAP bantları",
  "VWAP kesişimi ve bantlarla trend veya ortalamaya dönüş modu; RSI aşırı bölge teyidi.",
  "ortalamaya_donus",
  "daytrade__vwap-donus",
  "ohlcv"
 ],
 "LA06Kpl1": [
  "Fibonacci %50 seviyesi",
  "Fibonacci %50 düzeltme seviyesinden giriş; stop ve hedef seviyeleri; Pine test ikizi.",
  "destek_direnc",
  "swing__fib-geri-cekilme",
  "ohlcv"
 ],
 "On7JaUut": [
  "Pivot tepe/dip, ATR, SMA",
  "Likidite süpürmesi sonrası yapı kırılımında (structure flip) pozisyon; ATR tabanlı stop ve hedef.",
  "kirilim",
  "swing__sahte-kirilim",
  "ohlcv"
 ],
 "OqjKbuRp": [
  "Yutan mum, sabah/akşam yıldızı, EMA",
  "Yutan mum ve sabah/akşam yıldızı desenlerinde stop-giriş; TP1 kısmi kâr, stop.",
  "formasyon",
  "swing__mum-coklu-formasyon",
  "ohlcv"
 ],
 "PkUPYbw7": [
  "Pivot dönüşü, arz/talep bölgesi, DMI/EMA, ATR",
  "Pivot dönüşü arz/talep bölgesinde giriş; kademeli TP1-TP3 kâr alma ve stop.",
  "destek_direnc",
  "swing__talep-arz-bolgesi",
  "ohlcv"
 ],
 "QMvHkvdQ": [
  "Yapı kırılımı (BOS), likidite süpürme, order block, FVG",
  "HTF ve MTF yön uyumu, likidite süpürme ve iskonto/prim bölgesinde order block veya FVG girişi.",
  "diger",
  "",
  "ohlcv"
 ],
 "RQHNSLbH": [
  "HTF yapı, VWAP, ATR, yüzdelik",
  "HTF piyasa yapısı önyargısına göre aralık dönüşünde limit giriş; stop ve TP.",
  "kirilim",
  "",
  "ohlcv"
 ],
 "SfyBCHIJ": [
  "Lorentzian ML sınıflandırıcı, SuperTrend, EMA",
  "Lorentzian makine öğrenmesi sınıflandırıcısıyla giriş; SuperTrend ve yapı ile çıkış.",
  "diger",
  "",
  "ohlcv"
 ],
 "SlWseGFp": [
  "Günlük likidite süpürme, ATR",
  "Günlük likidite süpürmesi ve yapı teyidiyle long/short; TP1 kısmi, TP2 tam kâr.",
  "kirilim",
  "swing__sahte-kirilim",
  "ohlcv"
 ],
 "T3t4yoJx": [
  "Sıkışma, momentum, hacim, RSI, EMA, lineer regresyon",
  "2 saatlik grafikte sıkışma sonrası hacimli momentum kırılımında long/short; kademeli TP ve stop.",
  "kirilim",
  "swing__bb-sikisma-kirilim",
  "ohlcv"
 ],
 "Z8EhgIzs": [
  "Trend yönü, güçlü sinyal skoru",
  "Trend yönü değişince long/short; güçlü sinyalde ek giriş; karşıt sinyalde kapanış.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "Zl0fql8o": [
  "VWAP, trend ve momentum, ATR",
  "VWAP trend ve momentum koşullarında long/short; ATR tabanlı stop ve hedef.",
  "trend_takip",
  "daytrade__vwap-trend",
  "ohlcv"
 ],
 "aVzNdTMg": [
  "Hızlı/yavaş SMA, Fibonacci supertrend",
  "Hızlı-yavaş SMA kesişimi ve Fibonacci supertrend trend çizgisi kırılımında long/short; trend çizgisi çıkışı.",
  "trend_takip",
  "swing__trend-cizgisi-kanal",
  "ohlcv"
 ],
 "ab5k064U": [
  "ATR, DMI, EMA, pivot, yüzdelik",
  "Trend ve pivot koşullarıyla long/short; SL, başa-baş (BE) ve trend değişimi çıkışları.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "adstHm9N": [
  "Kesirli EMA kesişimleri",
  "Kesirli EMA kesişimleri ardışık onayla long/short giriş; geri dönüşte çıkış.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "bOcHnaiQ": [
  "Fibonacci geri çekilme, Supertrend, ATR",
  "Supertrend kesişimiyle giriş; Fibonacci geri çekilme seviyelerinde stop; supertrend kesişimiyle çıkış.",
  "destek_direnc",
  "swing__fib-geri-cekilme",
  "ohlcv"
 ],
 "f9xLZqpF": [
  "EMA MACD, RSI, stokastik, tahmin motoru",
  "EMA MACD, RSI ve stokastik kesişimlerinin birleşimi ve tahmin motoru ile giriş.",
  "diger",
  "",
  "ohlcv"
 ],
 "fM3YQz8i": [
  "ATR trend, MA (HMA/WMA/TEMA/VWMA)",
  "Fiyatın MA'yı low/high ile kesmesiyle long/short; ATR tabanlı sabit TP/SL.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "fiGIFuyH": [
  "UT Bot (ATR izleyen), STC osilatörü",
  "UT Bot ve STC birlikte kesişince giriş; kısmi TP ve stop.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "iILE5e3m": [
  "EMA kesişimi (hızlı/yavaş), TP/SL araç seti",
  "EMA kesişimiyle al/sat; TP/SL araç seti ile çıkış ve pozisyon yönetimi.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "jSNZ1CmV": [
  "Yapı kırılımı (BOS), swing, order block, FVG, HMA",
  "Yapı kırılımı (BOS) ve order block/FVG girişleri; stop ve hedef.",
  "diger",
  "",
  "ohlcv"
 ],
 "mVkDf8qh": [
  "SMA/EMA kesişimi, MACD, RSI, DMI, pivot",
  "Hızlı ve yavaş MA kesişimiyle long/short; TP/SL; ters sinyalde pozisyon kapanır.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "mikVFwAu": [
  "Yatay kanal destek/direnç, ATR, EMA, RSI",
  "Destek/direnç kanalından dönüş ve kanal kırılımıyla long/short; kademeli kâr alma ve stop.",
  "destek_direnc",
  "swing__trend-cizgisi-kanal",
  "ohlcv"
 ],
 "nmnHkA02": [
  "Dış sinyal (connectome simülasyonu)",
  "Sinyali harici bir sinek beyni simülasyonundan alan görsel şablon; mekanik edge doğrulanamadı.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "oq1Ju4Ha": [
  "EMA9/21, VWAP, MACD, RSI (5 dk), EMA çıkış",
  "SOL 5 dk: EMA9/21 kesişimi, VWAP, MACD ve RSI onayıyla giriş; EMA ile çıkış.",
  "trend_takip",
  "scalp__ma-kesisim",
  "ohlcv"
 ],
 "rLkjr2sQ": [
  "Çift dokunma (double tap), ATR, en yüksek/en düşük",
  "Çift dokunma seviyeleri ve tarih filtresiyle giriş; ATR tabanlı stop ve hedef.",
  "formasyon",
  "swing__cift-dip-tepe",
  "ohlcv"
 ],
 "teYPT1m0": [
  "ATR, DMI, EMA, pivot",
  "NORN WEAVE (FEHU): trend ve pivot koşullarıyla long/short; SL, başa-baş ve trend değişimi çıkışları.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "uOlzLqTw": [
  "EMA, ATR, pivot",
  "Trend filtreli trend çizgisi kırılımıyla long/short; sabit stop ve hedef.",
  "kirilim",
  "swing__trend-cizgisi-kanal",
  "ohlcv"
 ],
 "x3kpQqJ5": [
  "EMA200, BOS/CHoCH, FVG",
  "EMA200 ve yapı (BOS/CHoCH) teyidi ile FVG girişi; çift FVG onayı; çoklu stop ve hedef.",
  "diger",
  "",
  "ohlcv"
 ],
 "HnelYN0A": [
  "Gece aralığı (0-7 saat), stop emirleri",
  "Altın 15 dk: gece aralığının yüksek/düşüğünde stop-giriş (OCO); yüzde ya da aralık stop; 20:00'de kapanış.",
  "kirilim",
  "daytrade__orb",
  "ohlcv"
 ],
 "OTfw8b2a": [
  "Yok (kayıtlı işlem listesi)",
  "CSV'deki kayıtlı işlemleri yeniden oynatan rapor aracı; kendi strateji mantığı yok.",
  "diger",
  "",
  "ohlcv"
 ]
}

# ANN_FT: ad/id -> (gostergeler, mekanik_ozet, kategori, benzer_1l3a_aile, veri_ihtiyaci)
ANN_FT = {
 "ADXMomentum": [
  "ADX, +DI/-DI, momentum",
  "ADX>25 ve +DI>-DI, momentum pozitifken long; ADX veya momentum bozulunca çıkış.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "ASDTSRockwellTrading": [
  "MACD",
  "MACD>0 ve MACD sinyal çizgisi üstünde long; sinyal altına inince çıkış (5 dk).",
  "momentum",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "AdxSmas": [
  "ADX(25), SMA kısa/uzun",
  "ADX>25 iken kısa SMA uzun SMA'yı yukarı keserse long; ADX<25 veya ters kesişimde çıkış.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "AlmgrenChrissStrategy": [
  "RSI",
  "RSI 45/55 eşiklerinde giriş; Almgren-Chriss yürütme mantığı; 15 dk testte tamamlanamadı.",
  "diger",
  "",
  "ohlcv"
 ],
 "AverageStrategy": [
  "EMA kesişimi",
  "Hızlı ve yavaş EMA kesişiminde al/sat; hacim filtresi (4s).",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "AwesomeMacd": [
  "MACD, Awesome Oscillator, ADX",
  "MACD>0 ve AO yukarı dönünce long; MACD veya AO sıfırın altına inince çıkış.",
  "momentum",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "Bandtastic": [
  "RSI, MFI, EMA, Bollinger alt bantları",
  "RSI ve MFI düşük, EMA hızlı>yavaş ve fiyat alt Bollinger bantlarının altındayken long; RSI yükselince çıkış.",
  "ortalamaya_donus",
  "swing__bant-donus",
  "ohlcv"
 ],
 "BbandRsi": [
  "RSI(14), Bollinger alt bant",
  "RSI<30 ve fiyat alt Bollinger bandının altındayken long; RSI>70 ile çıkış.",
  "ortalamaya_donus",
  "swing__rsi-asiri-donus",
  "ohlcv"
 ],
 "BinHV27": [
  "SMA bantları (yüksek/alçak), EMA, DI, RSI",
  "Fiyat SMA bantlarının altında, -DI ve RSI yükselirken long; SMA üstünde çıkış.",
  "ortalamaya_donus",
  "",
  "ohlcv"
 ],
 "BinHV45": [
  "Bollinger genişliği, kapanış farkı, alt kuyruk",
  "Bant genişliği, kapanış farkı ve uzun alt kuyruk eşikleriyle alt banda uzak düşüşte long.",
  "ortalamaya_donus",
  "",
  "ohlcv"
 ],
 "BreakEven": [
  "Yok (minimal_roi = 0)",
  "Boş giriş/çıkış sinyali; yalnız minimal_roi ile kapanan iskelet, sinyal mantığı yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "CCIStrategy": [
  "CCI (iki periyot), CMF, MFI",
  "CCI iki periyotta < -100 ve CMF, MFI aşırı satımdayken long; CCI>100 ile çıkış.",
  "ortalamaya_donus",
  "swing__cci-esik",
  "ohlcv"
 ],
 "CMCWinner": [
  "CCI, MFI, CMO",
  "CCI<-100, MFI<20 ve CMO<-50 aşırı satım dönüşünde long; CCI>100 ve MFI>80 ile çıkış.",
  "ortalamaya_donus",
  "swing__cci-esik",
  "ohlcv"
 ],
 "ClucMay72018": [
  "EMA100, Bollinger alt bant, hacim, ADX, MACD, RSI",
  "Fiyat EMA100 altında ve alt bandın %1.5 altındayken (hacim süzgeci) long; orta banda gelince çıkış.",
  "ortalamaya_donus",
  "swing__bant-donus",
  "ohlcv"
 ],
 "CofiBitStrategy": [
  "EMA, Stoch (fastk/fastd), ADX",
  "Fiyat EMA low altında, stokastik düşükte kesişince long; fiyat EMA high üstünde ya da Stoch 70 kesişiminde çıkış.",
  "momentum",
  "scalp__stokastik-donus",
  "ohlcv"
 ],
 "CombinedBinHAndCluc": [
  "Bollinger, EMA, mum gövde/kuyruk oranları",
  "BinH ve Cluc koşullarının birleşimi: alt bant dışı düşüş mumu ile long; orta bantta çıkış.",
  "ortalamaya_donus",
  "scalp__bant-donus",
  "ohlcv"
 ],
 "CustomStoplossWithPSAR": [
  "PSAR, RSI",
  "PSAR yön değişimine göre giriş; PSAR tabanlı izleyen stop örneği.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "DevilStra": [
  "SMA ve çapraz göstergeler",
  "Çoklu koşullu kesişim girişi; normalizasyon tüm veriyi kullanıyor (geleceği görüyor, geçersiz).",
  "diger",
  "",
  "ohlcv"
 ],
 "Diamond": [
  "SMA/EMA kesişimleri (kısmen yorumda)",
  "Kesişim koşullu şablon; göstergeler yorum satırında, mekanik kural tam değil.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "DoesNothingStrategy": [
  "Yok",
  "İşlem yapmayan iskelet strateji; sinyal üretmez (test amaçlı).",
  "diger",
  "",
  "ohlcv"
 ],
 "EMASkipPump": [
  "EMA kısa/orta, hacim (30 mum ort.×20), en düşük",
  "Pump-dump koşullarını (hacim patlaması) atlayıp EMA altında dip alımı; EMA üstünde çıkış.",
  "ortalamaya_donus",
  "",
  "ohlcv"
 ],
 "FAdxSmaStrategy": [
  "ADX, SMA",
  "ADX ve SMA koşullarının toplu sağlanmasında uzun/kısa giriş; kapanış koşuluyla çıkış.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "FOttStrategy": [
  "OTT, VAR, ADX, EMA",
  "VAR çizgisi OTT'yi yukarı keserse long, aşağı keserse short; ters kesişimde çıkış.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "FReinforcedStrategy": [
  "ADX, EMA, SMA",
  "ADX/SMA koşullu çoklu giriş; çıkış koşulları ile kapanış.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "FSampleStrategy": [
  "RSI, TEMA, Bollinger orta, MACD, MFI, SAR, Stoch",
  "RSI 30 ve 70 kesişimlerinde TEMA ve Bollinger orta bant koşuluyla long/short; RSI 70'te çıkış.",
  "momentum",
  "",
  "ohlcv"
 ],
 "FSupertrendStrategy": [
  "Supertrend x3 (alım), x3 (satım)",
  "Üç supertrend 'up' iken long; satım supertrend'leri 'down' olunca çıkış.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "FixedRiskRewardLoss": [
  "ATR, RSI",
  "Sabit risk/ödül oranını custom_stoploss ile uygulayan örnek; giriş RSI/ATR koşullu.",
  "diger",
  "",
  "ohlcv"
 ],
 "Freqtrade_backtest_validation_freqtrade1": [
  "SMA kısa/uzun",
  "Hızlı ve yavaş SMA kesişimiyle long/short; motor doğrulama örneği.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "GodStra": [
  "Çoklu koşul, DFIND ve kesişimler",
  "Koşullu kesişim girişi (12 saat); normalizasyon şüpheli, mekanik kural net değil.",
  "diger",
  "",
  "ohlcv"
 ],
 "GodStraNew": [
  "Çoklu koşul (normalize göstergeler)",
  "4 saat çoklu koşullu giriş; normalizasyon tüm veriyi kullanıyor (geleceği görüyor, geçersiz).",
  "diger",
  "",
  "ohlcv"
 ],
 "Heracles": [
  "Hyperopt ile seçilen alım koşulu",
  "Hyperopt ile belirlenen alım koşulları; kural optimizasyonla seçilir.",
  "diger",
  "",
  "ohlcv"
 ],
 "HourBasedStrategy": [
  "Saat (hour)",
  "Belirli saat aralığında alış, başka saat aralığında satış; zaman tabanlı.",
  "diger",
  "",
  "ohlcv"
 ],
 "InformativeSample": [
  "EMA20/50, 15 dk SMA20 (informative)",
  "1 saat EMA20>EMA50 ve 15 dk kapanış SMA20 üstünde long; ters koşulda short.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv+diger"
 ],
 "Low_BB": [
  "Bollinger alt bant, CCI, MACD, MFI, RSI",
  "Kapanış alt Bollinger bandının %2 altına inince long; kısa vadeli ortalamaya dönüş.",
  "ortalamaya_donus",
  "scalp__bant-donus",
  "ohlcv"
 ],
 "MACDStrategy": [
  "MACD, CCI",
  "MACD sinyal üstünde ve CCI eşik altındayken long; MACD altına inip CCI eşik üstüne çıkınca çıkış.",
  "momentum",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "MACDStrategy_crossed": [
  "MACD kesişimi, CCI",
  "MACD sinyali yukarı keserken CCI ≤ -50 ise long; aşağı kesişim ve CCI ≥ 100'de çıkış.",
  "momentum",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "MultiMa": [
  "Çoklu hareketli ortalama (TEMA)",
  "Birden çok MA'nın geçmiş değerle karşılaştırması ile giriş; ters koşulda çıkış.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "MultiRSI": [
  "SMA5, SMA200, RSI (yeniden örneklenmiş)",
  "SMA5≥SMA200 ve RSI, üst zaman dilimi RSI eşiklerinin altındayken long; üst TF RSI yükselince çıkış.",
  "ortalamaya_donus",
  "swing__rsi-asiri-donus",
  "ohlcv"
 ],
 "PatternRecognition": [
  "TA-Lib mum örüntüleri (CDL)",
  "Seçilen TA-Lib mum örüntüsü (örn. CDLHIGHWAVE) sinyaline göre giriş ve çıkış; günlük.",
  "formasyon",
  "swing__mum-coklu-formasyon",
  "ohlcv"
 ],
 "PowerTower": [
  "Kapanışların üssü (shift)",
  "Son üç kapanışın üst üste güçlü yükselişinde long; kapanış dizisi bozulunca çıkış.",
  "momentum",
  "",
  "ohlcv"
 ],
 "Quickie": [
  "ADX, MACD, TEMA, Bollinger orta, SMA200",
  "ADX>30 ve TEMA yükselirken kısa vadeli long; TEMA Bollinger orta üstüne çıkınca çıkış.",
  "momentum",
  "",
  "ohlcv"
 ],
 "ReinforcedAverageStrategy": [
  "EMA kısa/orta kesişimi, üst TF SMA",
  "Kısa-orta EMA kesişimi ve üst TF SMA üstünde long; ters kesişimde çıkış.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "ReinforcedQuickie": [
  "EMA kısa/orta, Bollinger alt bant, en düşük",
  "Fiyat EMA'ların altında, alt bantta ve dipte iken long; EMA üstünde çıkış.",
  "ortalamaya_donus",
  "scalp__bant-donus",
  "ohlcv"
 ],
 "ReinforcedSmoothScalp": [
  "MFI, Stoch fastd/fastk",
  "MFI ve stokastik düşükken long; EMA high üstünde çıkış (scalp).",
  "momentum",
  "scalp__stokastik-donus",
  "ohlcv"
 ],
 "Scalp": [
  "ADX, EMA low/high, Stoch",
  "Fiyat EMA low altında, ADX>30 ve stokastik<30 iken long; EMA high üstünde ya da Stoch 70 kesişiminde çıkış.",
  "momentum",
  "scalp__stokastik-donus",
  "ohlcv"
 ],
 "Simple": [
  "MACD, RSI, Bollinger üst bant eğimi",
  "MACD>0 ve sinyal üstünde, üst bant yukarı, RSI>70 iken long; RSI>80 ile çıkış.",
  "momentum",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "SmoothOperator": [
  "MFI, RSI, CCI, yumuşatılmış ortalama",
  "MFI, RSI ve CCI karışımı yumuşatılmış ortalama 4 bar artınca long; >100 ve düşüşte çıkış.",
  "momentum",
  "",
  "ohlcv"
 ],
 "SmoothScalp": [
  "ADX, EMA low/high, MFI, Stoch fastk",
  "Fiyat EMA low altında, ADX>30, MFI ve stokastik düşükken long; EMA high üstünde ya da Stoch 70'te çıkış.",
  "momentum",
  "scalp__stokastik-donus",
  "ohlcv"
 ],
 "Strategy001": [
  "EMA20/50/100, Heikin Ashi",
  "EMA20 EMA50'yi yukarı keser, HA kapanışı EMA20 üstünde ve yeşil mumsa long; HA kapanış EMA20 altına inince çıkış.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "Strategy001_custom_exit": [
  "EMA20/50/100, RSI, Heikin Ashi",
  "Strategy001 ile aynı giriş; özel çıkış fonksiyonu ekli.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "Strategy002": [
  "RSI, Stoch, CDLHAMMER, SAR, Fisher RSI, Bollinger",
  "RSI<30, stokastik<20, alt bant altı ve çekiç mumu ile long; SAR kapanış üstü ve Fisher RSI>0.3 ile çıkış.",
  "ortalamaya_donus",
  "swing__rsi-asiri-donus",
  "ohlcv"
 ],
 "Strategy003": [
  "RSI, Fisher RSI, SMA, SAR, MFI, Stoch",
  "RSI<28, Fisher RSI<-0.94 ve kapanış SMA altındayken long; SAR kapanış üstü ya da Fisher RSI>0.3 ile çıkış.",
  "ortalamaya_donus",
  "swing__rsi-asiri-donus",
  "ohlcv"
 ],
 "Strategy004": [
  "ADX, CCI, Stoch",
  "ADX>50 ya da yavaş ADX>26 ve CCI<-100 ile stokastik dönüşünde long; ADX<25 ile çıkış.",
  "momentum",
  "swing__cci-esik",
  "ohlcv"
 ],
 "Strategy005": [
  "MACD, SMA, Stoch, hacim, SAR, RSI",
  "Hacim ortalamanın 4 katı, fiyat SMA altı ve Stoch D>K iken long; RSI satım eşiğini yukarı kesince çıkış.",
  "ortalamaya_donus",
  "",
  "ohlcv"
 ],
 "Supertrend": [
  "Supertrend x3 (alım/satım)",
  "Üç supertrend 'up' iken long; satım supertrend'leri 'down' olunca çıkış.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "SwingHighToSky": [
  "CCI, RSI (zaman kaydırmalı)",
  "Zaman kaydırmalı CCI ve RSI eşikleri düşükken (aşırı satım) long; satım eşikleri aşılınca çıkış.",
  "ortalamaya_donus",
  "swing__cci-esik",
  "ohlcv"
 ],
 "TDSequentialStrategy": [
  "TD Sequential sayımı",
  "TD Sequential sayımı 8'i aşınca alım; satım sayımı 8'i aşınca satım; ters bölgede çıkış.",
  "formasyon",
  "",
  "ohlcv"
 ],
 "TWAPStrategy": [
  "RSI",
  "RSI 45/55 eşiklerinde TWAP yürütme ile alım/satım; işlemleri zamana yayar.",
  "diger",
  "",
  "ohlcv"
 ],
 "TechnicalExampleStrategy": [
  "CMF",
  "Chaikin para akışı (CMF) sıfırın altına ya da üstüne geçişinde short/long; örnek strateji.",
  "momentum",
  "",
  "ohlcv"
 ],
 "TrendFollowingStrategy": [
  "Trend (SMA/EMA), OBV",
  "Kapanış trend çizgisini yukarı keserken OBV yükseliyorsa long; aşağı kesişte çıkış.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "TrendRiderStrategy": [
  "Günlük EMA200, EMA50, ADX, ATR, RSI, MACD, BB, OBV",
  "Günlük EMA200 üstünde geri çekilme ve EMA50 koşullarıyla long; RSI çıkış eşiği ve ATR stop.",
  "trend_takip",
  "swing__ma-geri-cekilme",
  "ohlcv"
 ],
 "UniversalMACD": [
  "Özel MACD (umacd)",
  "Özel MACD değeri belirli aralıkta iken long; ayrı çıkış aralığında kapanış.",
  "momentum",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "VolatilitySystem": [
  "ATR",
  "Kapanış değişimi ATR'yi aşarsa long (aşağı ise short), ters sinyalde çıkış; volatilite kırılımı.",
  "kirilim",
  "",
  "ohlcv"
 ],
 "Zeus": [
  "Çoklu koşul, normalize göstergeler",
  "Normalizasyon tüm veriyi kullanıyor (geleceği görüyor); düzeltilince avantaj kayboluyor.",
  "diger",
  "",
  "ohlcv"
 ],
 "hlhb": [
  "RSI(50), EMA5/10, ADX(25)",
  "RSI 50'yi yukarı keser, EMA5 EMA10'u keser ve ADX>25 iken long; RSI 50 aşağı kesince çıkış.",
  "trend_takip",
  "swing__rsi-momentum-esik",
  "ohlcv"
 ],
 "mabStra": [
  "SMA (mojo, hızlı, yavaş) oranları",
  "Üç hareketli ortalamanın oran koşulu ile long; çıkış oranlarının ters koşulu.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "multi_tf": [
  "RSI (BTC, ETH, 1 saat)",
  "BTC ve ETH 1 saatlik RSI eşiklerinin birlikte sağlanmasında long; RSI>70 ile çıkış.",
  "ortalamaya_donus",
  "",
  "ohlcv+diger"
 ],
 "wtc": [
  "WaveTrend (wt1/wt2), stokastik, def",
  "WaveTrend kesişimi ve stokastik/def aralık filtreleriyle long/short; ters kesişimde çıkış.",
  "momentum",
  "",
  "ohlcv"
 ]
}

# ANN_KURAL: ad/id -> (gostergeler, mekanik_ozet, kategori, benzer_1l3a_aile, veri_ihtiyaci)
ANN_KURAL = {
 "BT01": [
  "SMA 10, SMA 30",
  "SMA10 SMA30'u yukarı keserse long; kesişim tersine dönünce çıkış.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "BT02": [
  "SMA 10, SMA 20",
  "SMA10 SMA20'yi yukarı keserse long; ters kesişimde çıkış.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "BT03": [
  "SMA 15, SMA 50",
  "SMA15 SMA50'yi yukarı keserse long; ters kesişimde çıkış.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "BT04": [
  "SMA 13, SMA 50",
  "SMA13 SMA50'yi yukarı keserse long; ters kesişimde çıkış.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "BT05": [
  "SMA 10, SMA 30",
  "SMA10/30 kesişiminde long-short döner; hep piyasada.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "BT06": [
  "SMA 15 (kapanış)",
  "Kapanış SMA15 üstüne çıkınca long, altına inince short; hep piyasada.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "BT07": [
  "SMA 15 (kapanış)",
  "Kapanış SMA15 üstündeyken long; altına inince çıkış.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "BT08": [
  "SMA 30 (kapanış)",
  "Kapanış SMA30 üstüne çıkınca long, altına inince short.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "BT09": [
  "SMA 30 (kapanış)",
  "Kapanış SMA30 üstündeyken long; altına inince çıkış.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "BT10": [
  "SMA 10 (kapanış)",
  "Kapanış SMA10 üstündeyken long; altına inince çıkış.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "BT11": [
  "SMA 5, SMA 15",
  "SMA5/15 kesişiminde limit giriş; %2 stop ve %2 hedef.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "BT12": [
  "EMA 10, EMA 20",
  "EMA10/20 kesişiminde giriş; %2 stop ile çıkış.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "BT13": [
  "RSI (35/65)",
  "RSI 35 ve 65 eşiklerinin kesişiminde L/S giriş; RSI 50'de çıkış.",
  "ortalamaya_donus",
  "swing__rsi-asiri-donus",
  "ohlcv"
 ],
 "BT14": [
  "MACD, SMA 30, ATR (3x)",
  "MACD kesişimi ve düşen SMA30 teyidinde giriş; 3 ATR stop (Tharp).",
  "momentum",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "BT15": [
  "Günlük getiri (dip)",
  "Günlük düşüş %1 ve üzerindeyse al, 2 gün tut (buy the dip).",
  "ortalamaya_donus",
  "swing__yeni-dip-sonrasi-donus",
  "ohlcv"
 ],
 "BT16": [
  "20 mum zirvesi",
  "20 mum zirvesine dokununca al, 2 gün tut.",
  "kirilim",
  "swing__donchian-kirilim",
  "ohlcv"
 ],
 "BT17": [
  "Haftanın günü, ±%3 braket",
  "Belirli haftanın günlerinde ±%3 braket emir, 7 gün tut.",
  "diger",
  "",
  "ohlcv"
 ],
 "BT18": [
  "MACD 12/26/9, SMA 10/30",
  "MACD ve SMA çift sinyali aynı anda olunca long.",
  "trend_takip",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "BP01": [
  "SMA 10, SMA 20",
  "SMA10/20 kesişiminde ters yöne dön (stop-and-reverse), hep piyasada.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "BP02": [
  "SMA 10/25, ATR (100)",
  "SMA10/25 kesişimi ile giriş; 2 ATR iz süren stop.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "BP03": [
  "SMA 50, SMA 100, 20/10 gün kanal",
  "SMA50/100 rejiminde 20 gün kırılım girişi, 10 gün çıkış.",
  "kirilim",
  "swing__donchian-kirilim",
  "ohlcv"
 ],
 "BP04": [
  "RSI (30), günlük + haftalık",
  "Günlük ve haftalık RSI(30) 70 üstündeyse long; %8 stop.",
  "momentum",
  "swing__rsi-momentum-esik",
  "ohlcv"
 ],
 "BP05": [
  "Özellik vektörü, kNN (7)",
  "Özelliklerle kNN tahmini; 48 mum sonrası getiri eşiğine göre long/short, ±%0.4.",
  "diger",
  "",
  "ohlcv"
 ],
 "FM01": [
  "SMA 200, volatilite",
  "SMA200 üstünde long, altında short; %10 hedef volatilite ile boyutlandırma.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "FM02": [
  "SMA 20 (kapanış)",
  "Kapanış SMA20 üstünde long, altında short.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "FM03": [
  "EMA 20 (kapanış)",
  "Kapanış EMA20 üstünde long, altında short.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "FM04": [
  "ROC 20",
  "20 günlük getiri pozitifse long, negatifse short.",
  "momentum",
  "",
  "ohlcv"
 ],
 "FM05": [
  "SMA 20, SMA 50",
  "SMA20/50 kesişiminde long-short.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "FM06": [
  "GMMA (çoklu EMA)",
  "Çoklu EMA (GMMA) yönüne göre long-short.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "FM07": [
  "Bollinger (20, 2)",
  "Bollinger bant kırılımında long veya short.",
  "kirilim",
  "swing__bollinger-cift-bant-trend",
  "ohlcv"
 ],
 "QD01": [
  "SMA 50 (kapanış)",
  "Kapanış SMA50 üstündeyken long.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "QD02": [
  "SMA 20, SMA 60 (4 saat)",
  "4 saatlik SMA20/60 kesişiminde long-short (BTC şablonu).",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "QD03": [
  "Üç hareketli ortalama, mum rengi",
  "Üç ortalamayı kesen boğa mumunda long; ters koşulda short.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "QD04": [
  "Üç hareketli ortalama, SMA 60",
  "Üç ortalamayı kesen boğa mumu, SMA60 trend süzgeci ile long.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "QD05": [
  "Donchian 20/10, ATR (2x)",
  "Turtle: 20 gün kırılımda giriş, 10 gün kırılımda çıkış; 2 ATR stop.",
  "kirilim",
  "swing__donchian-kirilim",
  "ohlcv"
 ],
 "QD06": [
  "MACD, RSI, ADX",
  "MACD>0, 50<RSI<75 ve ADX>20 birlikte iken long.",
  "momentum",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "QD07": [
  "MACD, KDJ (4 saat)",
  "MACD ve KDJ onayında giriş; %2 stop, %5 sonrası %1 iz süren stop.",
  "momentum",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "QD08": [
  "SuperTrend (10, 3)",
  "SuperTrend yukarı dönünce long, aşağı dönünce çıkış.",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "QD09": [
  "SMA 20, SMA 50",
  "SMA20 SMA50 üstündeyken long.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "QD10": [
  "EMA 20, EMA 50",
  "EMA20 EMA50 üstündeyken long.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "QD11": [
  "SMA 20 (kapanış)",
  "Kapanış SMA20 üstündeyken long.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "QD12": [
  "BTC çekirdek, SMA 50 (1 saat)",
  "BTC'de long çekirdek; fiyat SMA50 altındayken hedge uygulanır.",
  "trend_takip",
  "",
  "ohlcv+diger"
 ],
 "QD13": [
  "Katmanlı alım (1 saat)",
  "Zarar sonrası katmanlı pozisyon artışı (martingale); kesin ret kuralı.",
  "diger",
  "",
  "ohlcv"
 ],
 "QD14": [
  "Kademeli alım (1 saat)",
  "Düşüşte kademeli alım (DCA); ortalama maliyete göre çıkış.",
  "diger",
  "",
  "ohlcv"
 ],
 "QD15": [
  "60 günlük getiri (sıralama)",
  "En güçlü 4 coin haftalık yenilenir; eşit ağırlıkla long.",
  "momentum",
  "swing__goreceli-guc-momentum",
  "ohlcv+diger"
 ],
 "QD16": [
  "60 günlük volatilite (sıralama)",
  "En düşük volatiliteli 4 coin haftalık tutulur (long).",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "QD17": [
  "20 günlük momentum (sıralama)",
  "En güçlü 5 coin haftalık yenilenir (long).",
  "momentum",
  "swing__goreceli-guc-momentum",
  "ohlcv+diger"
 ],
 "QD18": [
  "Fiyat ızgarası (1 saat)",
  "Sabit fiyat aralığında ızgara alım-satım; stop yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "AQ01": [
  "SMA 10, SMA 20",
  "SMA10 SMA20 üstündeyken long.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "AQ02": [
  "SMA 5, SMA 20",
  "SMA5 SMA20 üstündeyken long.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "AQ03": [
  "Momentum skoru, BTC filtresi, ATR iz",
  "Momentum sıralaması en güçlü coinlere long; BTC filtresi ve %15 iz süren stop.",
  "momentum",
  "swing__goreceli-guc-momentum",
  "ohlcv+diger"
 ],
 "AQ04": [
  "SMA 5, 10, 30",
  "SMA5>SMA10>SMA30 dizilimi varken long.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "AQ05": [
  "Trend yargı kuralı, ATR",
  "Çoklu koşullu trend yargısı ile long; %5 stop.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "AQ06": [
  "SMA 5 (kapanış)",
  "Kapanış SMA5'in %1 üzerindeyse long.",
  "trend_takip",
  "",
  "ohlcv"
 ],
 "AQ07": [
  "Eşit ağırlık",
  "Coinler eşit ağırlıkla aylık yeniden dengelenir (long).",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "AQ08": [
  "Gerçekleşen volatilite",
  "Ters volatilite ağırlıklı portföy, aylık yeniden dengeleme.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "AQ09": [
  "Minervini trend şablonu, %10 stop",
  "Minervini trend şablonu sağlanınca long; %10 stop.",
  "trend_takip",
  "swing__konsolidasyon-kirilim",
  "ohlcv"
 ],
 "OB01": [
  "Bollinger bantları (4 saat)",
  "Bollinger bant sapmasında ortalamaya dönüş, 4 saat.",
  "ortalamaya_donus",
  "swing__bant-donus",
  "ohlcv"
 ],
 "OB02": [
  "EMA 21 (%2 bant), 4 saat",
  "Fiyat EMA21'den %2 uzaklaşınca ortalamaya dönüş.",
  "ortalamaya_donus",
  "",
  "ohlcv"
 ],
 "OB03": [
  "EMA 50 sapması, 4 saat",
  "EMA50'den sapmada ortalamaya dönüş işlemi.",
  "ortalamaya_donus",
  "",
  "ohlcv"
 ],
 "OB04": [
  "StochRSI",
  "StochRSI uç değerlerinde ters yönde giriş (4 saat).",
  "momentum",
  "swing__stokastik-donus",
  "ohlcv"
 ],
 "OB05": [
  "SMA 50, SMA 200",
  "SMA50 SMA200'ü yukarı keserse long (altın kesişim).",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "OB06": [
  "RSI (10)",
  "RSI<28'de al; %15 stop, %25 hedef.",
  "ortalamaya_donus",
  "swing__rsi-asiri-donus",
  "ohlcv"
 ],
 "OB07": [
  "EMA 9, EMA 21 (4 saat)",
  "EMA9 EMA21'i keserse yön değiştir.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "OB08": [
  "RSI ve hareketli ortalama (uç seviyeler)",
  "RSI-MA uç seviyelerinde (39.57/67.45) giriş.",
  "momentum",
  "swing__rsi-asiri-donus",
  "ohlcv"
 ],
 "OB09": [
  "RSI ve hareketli ortalama (normal seviyeler)",
  "RSI-MA normal seviyelerinde (48.62/53.63) giriş.",
  "momentum",
  "swing__rsi-momentum-esik",
  "ohlcv"
 ],
 "OB10": [
  "Düzenli alım (4 saat)",
  "Akıllı DCA: kademeli alım, ortalama maliyete göre çıkış.",
  "diger",
  "",
  "ohlcv"
 ],
 "OB11": [
  "Düzenli alım (haftalık)",
  "Haftalık basit DCA; satış kuralı yok.",
  "diger",
  "",
  "ohlcv"
 ],
 "OB12": [
  "Endeks ağırlığı (BTC, ETH, SOL)",
  "BTC/ETH/SOL eşit ağırlıkta; ±%5 sapmada yeniden dengeleme.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "BB01": [
  "Trailing trade ayarları (1 saat)",
  "Binance bot örnek ayarı: iz süren giriş-çıkış.",
  "diger",
  "",
  "ohlcv"
 ],
 "BB02": [
  "EMA 9, EMA 21, SMA 200",
  "EMA9/21 momentumu ve SMA200 üstünde long; %5 iz süren stop.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv"
 ],
 "BB03": [
  "Sabit ağırlık (BTC/ETH/SOL)",
  "Sabit ağırlıklı (0.5/0.3/0.2) portföy, 4 saatte yeniden dengeleme.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "BB04": [
  "Momentum sıralaması (30 mum)",
  "En güçlü 3 coin long; 1 saatlik yeniden dengeleme.",
  "momentum",
  "swing__goreceli-guc-momentum",
  "ohlcv+diger"
 ]
}

# ANN_AWESOME: ad/id -> (gostergeler, mekanik_ozet, kategori, benzer_1l3a_aile, veri_ihtiyaci)
ANN_AWESOME = {
 "AS01": [
  "Yıllık getiri (dönemsel)",
  "12 aylık döngüde en iyi 5 long, en kötü 5 short; aylık.",
  "momentum",
  "swing__goreceli-guc-momentum",
  "ohlcv+diger"
 ],
 "AS02": [
  "52 hafta zirvesi",
  "Yıllık zirveye en yakın 5 coin long, en uzak 5 short; 3 dilim.",
  "kirilim",
  "swing__donchian-kirilim",
  "ohlcv+diger"
 ],
 "AS03": [
  "365 gün getiri (ROC)",
  "Yıllık getirisi en yüksek 5 coin long, aylık yenilenir.",
  "momentum",
  "swing__goreceli-guc-momentum",
  "ohlcv+diger"
 ],
 "AS04": [
  "300 günlük SMA",
  "Kapanış 300 günlük SMA üstündeki coinler eşit ağırlık, aylık.",
  "trend_takip",
  "swing__ma-kesisim",
  "ohlcv+diger"
 ],
 "AS05": [
  "Beta (BTC'ye göre)",
  "Düşük betalı üçte bir long, yüksek betalı üçte bir short (BAB).",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "AS06": [
  "Getiri tutarlılığı (212/182 gün)",
  "İki pencerede de üst üçte bir long, alt üçte bir short; 6 ay tut.",
  "momentum",
  "",
  "ohlcv+diger"
 ],
 "AS07": [
  "365 gün getiri (3/3)",
  "En iyi 3 long, en kötü 3 short; yıllık getiriye göre.",
  "momentum",
  "swing__goreceli-guc-momentum",
  "ohlcv+diger"
 ],
 "AS08": [
  "365 gün getiri (5/5)",
  "En iyi 5 long, en kötü 5 short; yıllık getiriye göre.",
  "momentum",
  "swing__goreceli-guc-momentum",
  "ohlcv+diger"
 ],
 "AS09": [
  "365 gün getiri (1/1)",
  "En iyi 1 long, en kötü 1 short (stil rotasyonu).",
  "momentum",
  "swing__goreceli-guc-momentum",
  "ohlcv+diger"
 ],
 "AS10": [
  "6 aylık getiri, çeyreklik",
  "En iyi 3 coin 6 aylık getiriyle çeyreklik long.",
  "momentum",
  "swing__goreceli-guc-momentum",
  "ohlcv+diger"
 ],
 "AS11": [
  "Haftalık getiri std (365 gün)",
  "En düşük volatilite 6 coin long, aylık.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "AS12": [
  "Momentum ve volatilite",
  "Yüksek volatilite yarısında momentum sıralaması, 6 dilimle long/short.",
  "momentum",
  "",
  "ohlcv+diger"
 ],
 "AS13": [
  "BTC/ETH 90 günlük getiri",
  "Son 90 günde iyi olan BTC ya da ETH'ye %100, çeyreklik.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "AS14": [
  "Mesafe yöntemi (120 gün, 5 çift)",
  "Normalize fiyat mesafesi çiftleri; sapmada çift işlemi.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "AS15": [
  "Mesafe yöntemi (365 gün, 20 çift)",
  "Daha geniş çiftlerle mesafe tabanlı çift işlemi.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "AS16": [
  "Eşit ağırlık, dengelenmemiş",
  "Günlük dengelenen eşit ağırlık ile dengelenmeyen arasındaki fark.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "AS17": [
  "Günlük getiri dağılımı (2 std)",
  "Üst/alt 2 std sayısı farkı; en düşük 5 long, en yüksek 5 short.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "AS18": [
  "Haftalık kısa dönüş (7/30 gün)",
  "7 günün en kötü 5'i long, 30 günün en iyi 5'i short.",
  "ortalamaya_donus",
  "",
  "ohlcv+diger"
 ],
 "AS19": [
  "Getiri çarpıklığı (365 gün)",
  "En düşük çarpıklık 5 long, en yüksek 5 short.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "AS20": [
  "365 gün getiri işareti, volatilite",
  "Zaman serisi momentumu; ters volatilite ağırlık, %10 hedef vol.",
  "trend_takip",
  "",
  "ohlcv+diger"
 ],
 "AS21": [
  "Dolar hacmi (küçük ölçek)",
  "En küçük 5 long, en büyük 5 short (hacim vekili), aylık.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "AS22": [
  "ETH/BTC oranı, SMA 20, WTI-Brent",
  "Harici emtia spread'ine göre ETH/BTC yönü.",
  "diger",
  "",
  "ohlcv+diger"
 ],
 "AS23": [
  "Kalıntı momentum (BTC regresyonu)",
  "BTC'ye regresyon kalıntısının 12 aylık getirisi; beşlik long/short.",
  "momentum",
  "",
  "ohlcv+diger"
 ],
 "AS24": [
  "Takvim (ay dönümü)",
  "Ay dönümü günlerinde BTC alımı, takvim tabanlı.",
  "diger",
  "",
  "ohlcv"
 ],
 "AS25": [
  "Takvim (maaş günü)",
  "Ayın 15-16'sı arasında BTC, takvim tabanlı.",
  "diger",
  "",
  "ohlcv"
 ],
 "AS26": [
  "Takvim (ocak ayı)",
  "Ocak ayı mevsimselliği ile BTC işlemi.",
  "diger",
  "",
  "ohlcv"
 ],
 "AS27": [
  "Takvim (vade haftası)",
  "Son Cuma'nın bulunduğu vade haftası, takvim tabanlı.",
  "diger",
  "",
  "ohlcv"
 ],
 "AS28": [
  "Saat aralığı (22-00 UTC)",
  "BTC gün içi mevsimsellik: 22-00 UTC arası işlem.",
  "diger",
  "",
  "ohlcv"
 ],
 "AS29": [
  "Tüm zamanların zirvesi, ATR (10)",
  "Tüm zamanların zirvesi kırılımında long; 1 ATR iz süren stop.",
  "kirilim",
  "swing__donchian-kirilim",
  "ohlcv"
 ],
 "AS30": [
  "10 gün zirvesi",
  "10 gün zirvesinde long (Padysak-Vojtko MAX).",
  "kirilim",
  "swing__donchian-kirilim",
  "ohlcv"
 ],
 "AS31": [
  "10 gün dibi",
  "10 gün dibinde long (Padysak-Vojtko MIN).",
  "ortalamaya_donus",
  "",
  "ohlcv"
 ],
 "AS32": [
  "Aşırı tepki (ertesi gün)",
  "Aşırı tepkiden sonra ertesi gün ters yönde işlem (Caporale-Plastun).",
  "ortalamaya_donus",
  "",
  "ohlcv"
 ]
}

# ANN_JT: ad/id -> (gostergeler, mekanik_ozet, kategori, benzer_1l3a_aile, veri_ihtiyaci)
ANN_JT = {
 "JT_MACD_osilator": [
  "MACD (12, 26)",
  "MACD çizgisinin sinyal kesişimiyle long/short (günlük, coin başına).",
  "momentum",
  "swing__macd-sinyal",
  "ohlcv"
 ],
 "JT_Heikin_Ashi": [
  "Heikin Ashi mumları",
  "Heikin Ashi ters mum birikimi ile piramitleme; yüksek kazanma, kuyruk riski.",
  "trend_takip",
  "swing__heikin-ashi-donus",
  "ohlcv"
 ],
 "JT_Awesome_osilator": [
  "Awesome Oscillator",
  "AO işaret değişiminde long/short (günlük).",
  "momentum",
  "",
  "ohlcv"
 ],
 "JT_Parabolic_SAR": [
  "Parabolik SAR",
  "PSAR yön değişiminde ters pozisyon (stop-and-reverse).",
  "trend_takip",
  "swing__supertrend-psar",
  "ohlcv"
 ],
 "JT_RSI_30_70": [
  "RSI (14)",
  "RSI 30 altından yukarı dönünce long, 70 üstünden aşağı dönünce short.",
  "ortalamaya_donus",
  "swing__rsi-asiri-donus",
  "ohlcv"
 ],
 "JT_RSI_omuz_bas_omuz": [
  "RSI, omuz-baş-omuz",
  "Omuz-baş-omuz formasyonu ve RSI teyidiyle short; RSI 4 puan artınca ya da 5 mum sonra çıkış.",
  "formasyon",
  "swing__bas-omuz",
  "ohlcv"
 ],
 "JT_Shooting_Star": [
  "Mum gövde ve fitil oranları",
  "Ters çekiç (shooting star) mumunun ertesi onayıyla short; 7 mum tutma.",
  "formasyon",
  "swing__pin-bar",
  "ohlcv"
 ],
 "JT_Bollinger_W": [
  "Bollinger (75), bant genişliği",
  "W dibi Bollinger formasyonunda long; bant daralınca çıkış (saatlik).",
  "formasyon",
  "swing__cift-dip-tepe",
  "ohlcv"
 ],
 "JT_London_Breakout": [
  "Tokyo aralığı (1 saat)",
  "Tokyo seansı aralığının Londra açılışında kırılımında giriş.",
  "kirilim",
  "daytrade__orb",
  "ohlcv"
 ],
 "JT_Dual_Thrust": [
  "Önceki 5 gün aralığı, gün açılışı",
  "Önceki aralığa göre gün açılışı ± kırılımında giriş; gün sonunda kapanış.",
  "kirilim",
  "daytrade__orb",
  "ohlcv"
 ],
 "JT_Pair_trading": [
  "Eşbütünleşme (Engle-Granger), kalıntı z-skoru",
  "Eşbütünleşik coin çiftlerinde kalıntı z-skoru uç değerlerde çift işlemi (10 coin, 45 çift).",
  "ortalamaya_donus",
  "",
  "ohlcv+diger"
 ]
}


# ---------------------------------------------------------------- yollar ve sabitler
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARS = os.path.join(KOK, "arsiv")
TV = os.path.join(ARS, "strateji-sg", "tv")
TV_ELEME = os.path.join(ARS, "strateji-sg", "tv_eleme_dali")
DK = os.path.join(ARS, "algo-sg", "dis_kaynak")
FT_DIR = os.path.join(DK, "ft", "strategies")
CIKTI = os.path.join(KOK, "stratejiler", "dis_envanter.csv")
AILE_DOSYA = os.path.join(KOK, "stratejiler", "aileler.json")

ALANLAR = ["kaynak", "ad", "dosya", "gostergeler", "mekanik_ozet", "zaman_dilimi",
           "veri_ihtiyaci", "onceki_sonuc", "kategori", "benzer_1l3a_aile"]
KATEGORILER = {"trend_takip", "ortalamaya_donus", "kirilim", "momentum", "formasyon",
               "destek_direnc", "diger"}
VERI = {"ohlcv", "ohlcv+diger"}
KAYNAK_SIRA = ["tv", "freqtrade", "kural", "awesome", "jesuistm"]
OZET_EN_FAZLA_KELIME = 20


def _rel(yol):
    return os.path.relpath(yol, KOK).replace(os.sep, "/")


def _oku_json(yol):
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def _oku_csv(yol):
    with open(yol, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _sayi(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _aile_idleri():
    return {a["aile_id"] for a in _oku_json(AILE_DOSYA)}


def _sonuc_metni(r, kaynak_dosya):
    """Eski test sonucu: IS/OOS PF ve Sharpe + ön eleme ölçütüne göre geçti/kaldı.
    Ölçüt (stratejiler/DIS, dis_envanter kararı): PF IS ve OOS > 1.2, Sharpe IS ve OOS > 0.5,
    stres PF > 1.1 (stres sütunu yoksa bu koşul atlanır, metinde belirtilir)."""
    if r.get("hata"):
        return f"hata: {r['hata']} ({kaynak_dosya})"
    pfi = _sayi(r.get("pf_is", r.get("pf_IS")))
    pfo = _sayi(r.get("pf_oos", r.get("pf_OOS")))
    shi = _sayi(r.get("sh_is", r.get("sharpe_IS")))
    sho = _sayi(r.get("sh_oos", r.get("sharpe_OOS")))
    if pfi is None or pfo is None:
        return f"sonuç yok ({kaynak_dosya})"
    ps = _sayi(r.get("pf_stres"))
    gecti = (pfi > 1.2 and pfo > 1.2 and (shi or -9) > 0.5 and (sho or -9) > 0.5
             and (ps is None or ps > 1.1))
    sh_metin = lambda v: "-" if v is None else f"{v:.2f}"
    stres = "" if ps is None else f"; stres PF {ps:.2f}"
    return (f"PF IS {pfi:.2f} / OOS {pfo:.2f}; Sh IS {sh_metin(shi)} / OOS {sh_metin(sho)}{stres} "
            f"→ {'geçti' if gecti else 'kaldı'} ({kaynak_dosya})")


# ---------------------------------------------------------------- TradingView (Pine)
def _tv_otomatik(metin):
    """Pine şablon DCA / ızgara betikleri: analiz notunun standart cümlesinden türetilir."""
    if metin.startswith("Spot/vadeli long DCA"):
        return ("RSI", "RSI girişli long DCA: taban emir ve ek alımlar, ortalama maliyete göre kâr.",
                "diger", "", "ohlcv")
    if metin.startswith("Spot/vadeli short DCA"):
        return ("RSI", "RSI girişli short DCA: taban emir ve ek satışlar, ortalama maliyete göre kâr.",
                "diger", "", "ohlcv")
    m = re.search(r"sabit fiyat aralığını (\d+|\?) seviyeye", metin)
    if m:
        seviye = "" if m.group(1) == "?" else f"{m.group(1)} "
        return ("Fiyat aralığı (ızgara)",
                f"Sabit aralıkta {seviye}seviyeli ızgara: seviye altında alım, üst seviyede satım; stop yok.",
                "diger", "", "ohlcv")
    return None


def _tv_ad(pid, aday, metin_pine):
    if pid in aday and aday[pid]["ad"]:
        return aday[pid]["ad"]
    m = re.search(r"strategy\(\s*(?:title\s*=\s*)?['\"]([^'\"]+)['\"]", metin_pine)
    if m:
        return m.group(1)
    for satir in metin_pine.splitlines():
        s = satir.strip()
        if s.startswith("//") and not re.search(r"©|@version|Mozilla|license", s, re.I):
            t = s.lstrip("/ ").strip()
            if t:
                return t[:80]
    return pid


def tv_satirlar(ann_tv):
    pine_yollari = {}
    for kok in (TV, TV_ELEME):
        pd_ = os.path.join(kok, "pine")
        for f in sorted(os.listdir(pd_)):
            if f.endswith(".pine"):
                pid = f[:-5]
                pine_yollari.setdefault(pid, os.path.join(pd_, f))
        # tv/pine öncelikli: setdefault ilk gördüğünü tutar (TV önce gelir)
    aday = {r["id"]: r for r in _oku_csv(os.path.join(TV, "aday.csv"))}
    kararlar = _oku_json(os.path.join(TV_ELEME, "analiz", "_kararlar.json"))
    gecen_ham = _oku_json(os.path.join(TV, "gecenler.json"))
    gecen = {g["ad"] if isinstance(g, dict) else g for g in gecen_ham}
    sonuc = {}
    for kok in (TV_ELEME, TV):
        sd = os.path.join(kok, "sonuclar")
        for f in sorted(os.listdir(sd)):
            if f.endswith(".json"):
                d = _oku_json(os.path.join(sd, f))
                sonuc.setdefault(d["pine_id"], (f"{_rel(sd)}/{f}", d))
    satirlar = []
    for pid in sorted(pine_yollari):
        yol = pine_yollari[pid]
        metin_pine = open(yol, encoding="utf-8", errors="replace").read()
        ad = _tv_ad(pid, aday, metin_pine)
        if pid in ann_tv:
            gost, ozet, kat, aile, veri = ann_tv[pid]
        else:
            otom = _tv_otomatik(_analiz_ozeti(pid))
            if otom is None:
                raise SystemExit(f"TV {pid}: elle yazılmış ya da otomatik özet yok")
            gost, ozet, kat, aile, veri = otom
        m = re.search(r"^\s*timeframe\s*=\s*['\"]([^'\"]+)['\"]", metin_pine, re.M)
        zaman = m.group(1) if m else ""
        k = kararlar.get(pid)
        s = sonuc.get(pid)
        if s and s[1]["ad"] in gecen:
            onceki = (f"geçti: PF {s[1]['olcut']['pf']:.2f}, Sharpe {s[1]['olcut']['sharpe']:.2f} "
                      f"({s[0]})")
        elif s:
            onceki = (f"kaldı: PF {s[1]['olcut']['pf']:.2f}, Sharpe {s[1]['olcut']['sharpe']:.2f} "
                      f"({s[0]})")
        elif k and k.get("karar") == "ele":
            gerekce = re.split(r"(?<=\.)\s", k.get("gerekce", ""))[0][:160]
            onceki = f"ön elemede elendi: {gerekce} (tv_eleme_dali/analiz/_kararlar.json)"
        elif k and k.get("karar") == "al":
            onceki = "ön elemeyi geçti, test sonucu yok (tv_eleme_dali/analiz/_kararlar.json)"
        else:
            onceki = ""
        satirlar.append({"kaynak": "tv", "ad": ad, "dosya": _rel(yol), "gostergeler": gost,
                         "mekanik_ozet": ozet, "zaman_dilimi": zaman, "veri_ihtiyaci": veri,
                         "onceki_sonuc": onceki, "kategori": kat, "benzer_1l3a_aile": aile})
    return satirlar


def _analiz_ozeti(pid):
    yol = os.path.join(TV_ELEME, "analiz", pid + ".md")
    if not os.path.exists(yol):
        return ""
    t = open(yol, encoding="utf-8").read()
    m = re.search(r"## Ne yapıyor\n+(.*?)(\n## |\Z)", t, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


# ---------------------------------------------------------------- freqtrade
# Normalizasyonda tüm verinin min/max değerini kullanan ve bu yüzden geleceği gören stratejiler
# (stratejiler/DIS: arsiv/algo-sg/DIS_STRATEJILER.md §4). Sonuçları geçersiz sayılır.
GECERSIZ_FT = {"GodStraNew", "Zeus", "DevilStra"}


def ft_satirlar(ann_ft):
    dakika = {r["strateji"]: r for r in _oku_csv(os.path.join(DK, "sonuc_freqtrade_dakika.csv"))}
    ana = {r["strateji"]: r for r in _oku_csv(os.path.join(DK, "sonuc_freqtrade.csv"))}
    satirlar = []
    for f in sorted(os.listdir(FT_DIR)):
        if not f.endswith(".py"):
            continue
        ad = f[:-3]
        if ad not in ann_ft:
            raise SystemExit(f"freqtrade {ad}: özet yok")
        gost, ozet, kat, aile, veri = ann_ft[ad]
        yol = os.path.join(FT_DIR, f)
        t = open(yol, encoding="utf-8", errors="replace").read()
        m = re.search(r"timeframe\s*=\s*['\"](\w+)['\"]", t)
        zaman = m.group(1) if m else ""
        if ad in ana:
            onceki = _sonuc_metni(ana[ad], "sonuc_freqtrade.csv")
        elif ad in dakika:
            onceki = _sonuc_metni(dakika[ad], "sonuc_freqtrade_dakika.csv")
        else:
            onceki = ""
        if ad in GECERSIZ_FT:
            onceki += " — normalizasyon geleceği görüyor (DIS: geçersiz)"
        satirlar.append({"kaynak": "freqtrade", "ad": ad, "dosya": _rel(yol), "gostergeler": gost,
                         "mekanik_ozet": ozet, "zaman_dilimi": zaman, "veri_ihtiyaci": veri,
                         "onceki_sonuc": onceki, "kategori": kat, "benzer_1l3a_aile": aile})
    return satirlar


# ---------------------------------------------------------------- kural / awesome / jesuistm
def _tum_tf():
    return {r["strateji"]: r["tf"] for r in _oku_csv(os.path.join(DK, "sonuc_tum.csv"))}


def sonuc_tabanli(kaynak, dosya_csv, dosya_kod, ann, anahtar, kayit_satir, kaynak_adi):
    satirlar = []
    for r in _oku_csv(os.path.join(DK, dosya_csv)):
        key = r[anahtar] if anahtar else r["strateji"]
        if key not in ann:
            raise SystemExit(f"{kaynak} {key}: özet yok")
        gost, ozet, kat, aile, veri = ann[key]
        zaman = r.get("tf") or _tum_tf().get(r["strateji"], "")
        satirlar.append({"kaynak": kaynak_adi, "ad": r["strateji"], "dosya": _rel(os.path.join(DK, dosya_kod)),
                         "gostergeler": gost, "mekanik_ozet": ozet, "zaman_dilimi": zaman,
                         "veri_ihtiyaci": veri, "onceki_sonuc": _sonuc_metni(r, dosya_csv),
                         "kategori": kat, "benzer_1l3a_aile": aile})
    return satirlar


# ---------------------------------------------------------------- birleştirme ve doğrulama
def envanter():
    aile_idleri = _aile_idleri()
    satirlar = []
    satirlar += tv_satirlar(ANN_TV)
    satirlar += ft_satirlar(ANN_FT)
    satirlar += sonuc_tabanli("kural", "sonuc_kural.csv", "kurallar.py", ANN_KURAL, "id", None, "kural")
    satirlar += sonuc_tabanli("awesome", "sonuc_awesome.csv", "awesome.py", ANN_AWESOME, "id", None, "awesome")
    satirlar += sonuc_tabanli("jesuistm", "sonuc_jesuistm.csv", "jesuistm.py", ANN_JT, None, None, "jesuistm")
    satirlar.sort(key=lambda r: (KAYNAK_SIRA.index(r["kaynak"]), r["ad"].lower()))
    hatalar = []
    for r in satirlar:
        if r["kategori"] not in KATEGORILER:
            hatalar.append(f"{r['dosya']}: kategori {r['kategori']!r}")
        if r["veri_ihtiyaci"] not in VERI:
            hatalar.append(f"{r['dosya']}: veri {r['veri_ihtiyaci']!r}")
        if r["benzer_1l3a_aile"] and r["benzer_1l3a_aile"] not in aile_idleri:
            hatalar.append(f"{r['dosya']}: aile {r['benzer_1l3a_aile']!r} yok")
        if len(r["mekanik_ozet"].split()) > OZET_EN_FAZLA_KELIME:
            hatalar.append(f"{r['dosya']}: özet {len(r['mekanik_ozet'].split())} kelime")
    if hatalar:
        raise SystemExit("Doğrulama hataları:\n" + "\n".join(hatalar))
    return satirlar


def csv_yaz(satirlar):
    with open(CIKTI, "w", encoding="utf-8", newline="") as f:
        yazar = csv.DictWriter(f, fieldnames=ALANLAR)
        yazar.writeheader()
        for r in satirlar:
            yazar.writerow({a: r[a] for a in ALANLAR})


def rapor(satirlar):
    say = lambda liste: collections.Counter(liste)
    print(f"Toplam satır: {len(satirlar)}")
    print("Kaynak başına:", dict(say(r["kaynak"] for r in satirlar)))
    print("veri_ihtiyaci=ohlcv:", sum(r["veri_ihtiyaci"] == "ohlcv" for r in satirlar))
    print("Kategori:", dict(say(r["kategori"] for r in satirlar).most_common()))
    print("1L3A ailesi bulunan:", sum(bool(r["benzer_1l3a_aile"]) for r in satirlar))
    print("ohlcv ve 1L3A ailesi yok:")
    for r in satirlar:
        if r["veri_ihtiyaci"] == "ohlcv" and not r["benzer_1l3a_aile"]:
            print(f"  [{r['kaynak']}] {r['ad']} | {r['mekanik_ozet']}")


if __name__ == "__main__":
    sat = envanter()
    csv_yaz(sat)
    rapor(sat)
