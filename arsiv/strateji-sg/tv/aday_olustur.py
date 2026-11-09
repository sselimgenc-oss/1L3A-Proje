"""Aşama 1: tv/aday.csv üretir (meta.json + pine kodu özellikleri + elle karar tablosu)."""
import json, re, csv, pathlib, html
K = pathlib.Path(__file__).parent
meta = json.load(open(K/"ham/meta.json"))
# (aile, zaman dilimi, pazar) -- seçilenler (karar=al)
AL = {
 "P5Gu6F8k":("trend","1g/4s","hepsi"), "3wdQu7P3":("trend","1g/4s","hepsi"), "eENf7NpJ":("trend","1g/4s","hepsi"),
 "ycDUERPO":("trend","1g/4s","hepsi"), "VuYM89Tw":("trend","1g","hepsi"), "0vvrOpg1":("trend","1s","kripto/hisse"),
 "3SHJZytF":("trend","1g/4s","hepsi"), "erJi1tWf":("trend","1g/4s","hepsi"), "DwdC6FT4":("trend","1g/4s","hepsi"),
 "lDGmh7ou":("trend","1g/4s","hepsi"), "kbYTJ8V2":("trend","1g/4s","hepsi"), "X0F9OE4L":("trend","1s/4s","hepsi"),
 "dxhgQwyI":("trend","1g/4s","hepsi"), "mpjNqADq":("trend","1g/4s","hepsi"), "TbK1rB5B":("trend","1s/4s","hepsi"),
 "NgSIfKQx":("trend","1s","kripto"), "yMCa3XZD":("trend","1g","hepsi"), "VO6DY8s1":("trend","1g/4s","hepsi"),
 "nHGK4Qtp":("trend","1g/4s","hepsi"),
 "uCV8I4xA":("ortalamaya dönüş","1g/4s","hepsi"), "IGJPEi7L":("ortalamaya dönüş","1g/4s","hepsi"),
 "G5ro3y87":("osilatör","1g/4s","hepsi"), "TDxSLJRA":("ortalamaya dönüş","1g","hepsi"), "W67tJltC":("ortalamaya dönüş","1s/4s","hepsi"),
 "EjLwVtgp":("kırılım","1g","hepsi"), "Dln4aFaM":("kırılım","1g","hisse"), "N1OCoFkf":("kırılım","1s/4s","hepsi"),
 "G40dtEbK":("kırılım","1g/4s","hepsi"), "FDeprmix":("kırılım","1g/4s","hepsi"), "hezSShJr":("kırılım","1s/4s","hepsi"),
 "m1JDhFR9":("kırılım","1g/4s","hepsi"), "dwgn7hrE":("kırılım","1s/4s","hepsi"), "gqaZYhUN":("kırılım","1s/4s","hepsi"),
 "CItvSvqk":("kırılım","1s/4s","hepsi"),
 "B7MQqWes":("osilatör","1s/4s","hepsi"), "cJhpIJ2w":("osilatör","1g/4s","hepsi"), "9cxy1Yu9":("trend","1g","kripto"),
 "boHD0HzE":("trend","1g/4s","hepsi"), "5zL50iGH":("kırılım","1s","emtia"), "XK8XbDhT":("ortalamaya dönüş","1g","hisse"),
 "83hmaEOQ":("SMC/ICT","1s/4s","hepsi"),
}
ELE = {
 # şablon / altyapı / eğitim / araç
 "MvlwAzSg":"şablon/altyapı (3Commas bot arayüzü)","2lGyzYkC":"şablon/altyapı (strateji şablonu)","IHVPG6TS":"eğitim/şablon (SL-TP örneği)",
 "jjhUHcje":"eğitim/şablon (kademeli iz süren stop örneği)","kzp8e4X3":"şablon (aylık getiri tablosu), calc_on_every_tick","n8bgynWl":"şablon/altyapı (trailing backtester, 2246 satır)",
 "bFXf4IXh":"eğitim (Kelly boyutlandırma örneği)","4jxYYaGU":"araç (iz süren SL/hedef aracı)","9Iwinz7I":"eğitim (kaldıraç/marjin örneği)","xAEG4ZJG":"eğitim (zaman aralığı örneği)",
 "OTfw8b2a":"araç (CSV'den rapor üretici)","M9taaIkp":"araç (osilatör değerlendirici, pyramiding=500)","hoCPm5UY":"eğitim (risk bazlı pozisyon boyu örneği)",
 "nVECqIQx":"eğitim (TASC makale örneği)","VFzCk3HX":"eğitim (TASC makale örneği)","iILE5e3m":"araç (TP/SL toolkit)","gU6RDuh5":"altyapı (webhook besleme)",
 "PkUPYbw7":"araç/prop firm kuralları sarmalayıcı","vWG3tMJh":"gösterge (Laguerre RSI), emir mantığı yok",
 # kopya
 "HPbRZvsV":"kopya (OTT; ycDUERPO tutuldu)","HDSdFMa3":"kopya (Bollinger+RSI; uCV8I4xA tutuldu)","zopumZ8a":"kopya (Bollinger+RSI; uCV8I4xA tutuldu)",
 "cJhpIJ2w_":"", "Ip667jzb":"kopya/genel (MA kesişimi; benzeri tutulan trendlerde var)","ZLcmWQtj":"kopya (PMax/OTT ailesi; temsilciler tutuldu)",
 "d1JxXpid":"kopya (Gaussian Channel; erJi1tWf tutuldu)","egTb7TgJ":"kopya (Gaussian Channel; erJi1tWf tutuldu)","71yKm18B":"kopya (Ichimoku; boHD0HzE tutuldu)",
 "xx3enmiW":"kopya (Ichimoku; boHD0HzE tutuldu)","DG9ePZuk":"kopya (Supertrend; tutulanlar var)","fiGIFuyH":"karmaşık/UT Bot+STC; lDGmh7ou tutuldu",
 # lookahead / çoklu zaman dilimi
 "U0wTnRuE":"geleceği gören request.security (lookahead_on, ofsetsiz)","Z8EhgIzs":"geleceği gören request.security (lookahead_on, ofsetsiz)",
 "9IoAQC1M":"calc_on_every_tick bağımlı + lookahead","njQsSFjo":"geleceği gören request.security (lookahead_on, ofsetsiz)","mVkDf8qh":"geleceği gören request.security + yeniden çizen pivot",
 "PdJvHIfQ":"çoklu zaman dilimi lookahead_on; karmaşık, temsilci seçilmedi","RQHNSLbH":"çoklu zaman dilimi lookahead_on; karmaşık",
 # tick bağımlı / ML / orderflow / hesaplı
 "SfyBCHIJ":"calc_on_every_tick + makine öğrenmesi (Lorentzian), canlı farklı davranır","qp9BoNyS":"calc_on_every_tick=true bağımlı (G40dtEbK ile aynı mantık tutuldu)",
 "EA1AXZui":"calc_on_every_tick bağımlı (VWAP gün içi)","rkHHEvJ1":"calc_on_every_tick bağımlı (VWAP SD gün içi)","nmnHkA02":"deneysel (sinek bağlantısı), calc_on_every_tick",
 "JeRCEqWU":"calc_on_every_tick + 1446 satır OB/FVG","mikVFwAu":"calc_on_every_tick + pyramiding","f9xLZqpF":"calc_on_every_tick + tahmin motoru",
 "adstHm9N":"calc_on_every_tick bağımlı (2222 satır)","3k4TWbWm":"calc_on_every_tick + Çin A hisse verisi","U3mcySX9":"calc_on_every_tick bağımlı + kalabalık verisi",
 "69ZFfJ5L":"makine öğrenmesi (XGBoost), eğitim verisi sızıntı riski","MQDDEl1e":"emir akışı/tick hacmi verisi gerektirir","6sorh9ZW":"pyramiding + 1266 satır, sinyal kaynağı karışık",
 "fmPC9fWd":"NQ vadeli hacim şoku (tick/seans verisi yok)",
 # <1dk / dakikalık gün içi: veri yok
 "sf4Hf10r":"5dk MGC vadeli (5dk geçmiş veri yok)","t7Tp4qnu":"ORB scalping 5dk (5dk geçmiş veri yok)","KX7AgFeB":"ORB 5dk (5dk geçmiş veri yok)",
 "49jNhJXM":"scalper (5dk veri yok)","Za5HKgrL":"gün içi 10:00 FVG (dakikalık veri yok)","HnelYN0A":"altın 15dk (15dk emtia geçmişi 60 gün)",
 "zudiHFjK":"altın 15dk (15dk emtia geçmişi 60 gün)","zpIyp7KB":"Initial Balance gün içi (dakikalık veri yok)","xJ5iSXIS":"scalper + DCA/pyramiding (5dk)",
 "14l4u5gJ":"scale-in/pyramiding scalper","bajhb6V9":"scale-in/pyramiding","sk6MVZEb":"gün içi 5dk (dakikalık veri yok)","7OLnQI4B":"gün içi sweep (dakikalık veri yok)",
 "OqjKbuRp":"çok sayıda mum formasyonu; temsilci seçilmedi","1OnkbAiE":"hacim profili (gerçek hacim profili verisi gerekir)",
 # repaint / martingale / sentetik
 "8OS1nbr8":"martingale (üstel pozisyon artışı), pyramiding","oq1Ju4Ha":"çoklu bileşen 661 satır; temsilci seçilmedi","TDxSLJRA_":"",
 "LA06Kpl1":"1424 satır 50% Fib; temsilci seçilmedi","x3kpQqJ5":"calc_on_every_tick + 3194 satır","rvBgD3aP":"Elliott dalga: repaint eden zigzag/pivot girişi",
 "edChhkxo":"harmonik formasyon: repaint eden zigzag/pivot girişi","uOlzLqTw":"trend çizgisi: pivot bazlı çizim yeniden hesaplanır (repaint)","GoeqO1ev":"likidite süpürme pivot girişi (repaint riski); temsilci seçilmedi",
 "On7JaUut":"likidite süpürme (kopya, repaint riski)","25Ffpyo0":"likidite süpürme pivot girişi (repaint riski)","jSNZ1CmV":"SMC OB+FVG: 83hmaEOQ temsilci tutuldu","QMvHkvdQ":"SMC OB+FVG: 83hmaEOQ temsilci tutuldu",
 "Eq4kPrrJ":"swing-anchored VWAP; temsilci seçilmedi","2u7KKcCG":"trend çizgisi kırılımı pivot bazlı (repaint)","WpJ5ym7u":"pivot bazlı giriş (repaint riski)","ouvmvItR":"hacim order block (SMC), 83hmaEOQ temsilci",
 "SlWseGFp":"ICT günlük likidite süpürme: günlük pivot/seans mantığı (SMC temsilcisi var)","CtFpKECD":"Heikin Ashi + pivot; temsilci seçilmedi","aVzNdTMg":"pivot trend çizgisi kırılımı (repaint) + pyramiding",
 "bOcHnaiQ":"çoklu zaman dilimi + pyramiding; karmaşık","8Ti8z8QO":"çoklu zaman dilimi + pyramiding","6kaqC3R8":"DCA/pyramiding bot (3Commas)","GM1bUrIF":"DCA/pyramiding bot (3Commas)",
 "ab5k064U":"çoklu sembol/seans, sinyal-only (alertler)","oq1Ju4Ha_":"","MTF":"",
}
CEVRILEMEDI = {
 "Dln4aFaM":"giriş ve çıkış koşulu aynı mumda (up-bar): işlem açılır açılmaz kapanır, anlamsız",
 "m1JDhFR9":"çok bileşenli (SMC bölgeleri, konsolidasyon, POC); bütçe nedeniyle çevrilmedi",
 "5zL50iGH":"yalnız 15 dk altın grafiği (betik başka dilimde hata verir); 15 dk altın geçmişi yok",
 "83hmaEOQ":"kısmi çıkış (%50 hedef + başa baş) ve seans mantığı; motor kısmi çıkış desteklemiyor",
 "mpjNqADq":"çok bileşenli skor sistemi (rejim+skor+bölge); bütçe nedeniyle çevrilmedi",
}
rows=[]
for x in meta:
    sid=x["id"]; p=K/"pine"/f"{sid}.pine"
    ad=html.unescape(x["ad"])
    src=p.read_text() if p.exists() else ""
    short=bool(re.search(r"strategy\.short|direction\.short|strategy\.direction\.(short|all)",src))
    longonly=bool(re.search(r"strategy\.direction\.long|long.?only",src,re.I)) and not short
    yon="ikisi" if short and not longonly else "long"
    tur="strategy" if x["tur"] in ("strategy","?") else x["tur"]
    if not src:
        rows.append([sid,ad,x["yazar"],x["link"],tur,"kapali","","","","","ele","kaynak kapalı (protected/invite-only)"]); continue
    if sid in AL:
        a=AL[sid]; rows.append([sid,ad,x["yazar"],x["link"],tur,"acik",a[1],yon,a[2],a[0],"al","temsilci aday (aile: %s)"%a[0] + ("; ÇEVRİLEMEDİ: "+CEVRILEMEDI[sid] if sid in CEVRILEMEDI else "")])
    else:
        neden=ELE.get(sid) or "temsilci seçilmedi: aile içinde daha basit/denenmiş aday var ya da çeviri maliyeti yüksek"
        rows.append([sid,ad,x["yazar"],x["link"],tur,"acik","",yon,"","","ele",neden])
with open(K/"aday.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["id","ad","yazar","link","tur","erisim","zaman_dilimi","yon","pazar","aile","karar","neden"]); w.writerows(rows)
from collections import Counter
print(Counter(r[10] for r in rows), Counter(r[9] for r in rows if r[10]=="al"))
