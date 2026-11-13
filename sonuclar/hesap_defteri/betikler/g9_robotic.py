#!/usr/bin/env python3
"""G9_ROBOTIC hesap defteri betiği.

Girdi : birleşmemiş claude/adoring-maxwell-q7t60g dalındaki
        sonuclar/dis_arastirma/2026-11_freqtrade_robotic/ (dosya_listesi.csv, kume_listesi.csv, canli_akraba/*)
        (ROBOTIC_DIZIN ortam değişkeniyle ya da aşağıdaki varsayılan yolla verilir; salt okunur kopya)
        + sonuclar/hesap_defteri/ara/kod_kaydi.csv, stratejiler/ek_kaynaklar/github_g1_freqtrade.csv, stratejiler/dis_envanter.csv
Çıktı : sonuclar/hesap_defteri/ara/G9_ROBOTIC_ham.csv (909 satır), G9_ROBOTIC_elle_kararlar.csv, G9_ROBOTIC_NOTLAR.md

Karar sırası (dosya düzeyi):
  1. dosya_sinif ML_FREQAI (+ LLM karar veren dosya)            -> G_ML
  2. Aynı ad + aynı mantık, H001 (github_g1_freqtrade) satırı    -> TEKRAR (hedef H001:<satır>)   [TEKRAR_EXACT]
  3. DCA_POZISYON_BUYUTME                                        -> F_YASAK_TIP (dca/martingale)
  4. LOOKAHEAD_YUKSEK ya da canli_akraba/ewo_aile.csv "EVET"     -> D lookahead
  5. DIGER_KULLANILAMAZ                                          -> D (şablon/geçersiz/LLM)
  6. küme kararı (KUME_KARAR elle doğrulama; yoksa önceki ajan kararı "doğrulanmadı")
Temsilci: kümenin dosya_listesi.csv'deki İLK dosyası. ESDEGER kararı yalnız temsilciye verilir, kümenin diğer üyeleri
BENZER (parametre/ek koşul farkı açılmadı) olur. Küme içi TEKRAR VERİLMEZ: kume_listesi "kopya" ifadesi, katalogun
dosya_listesi'ne HİÇ GİRMEYEN byte-özdeş kopyalarını sayar (kopya_sayisi); kümedeki dosyalar Jaccard>=0.7 benzer, özdeş değil.
"""
import csv
import collections
import os
import re
import sys

KOK = "/home/user/1L3A-Proje"
R = os.environ.get("ROBOTIC_DIZIN", "/tmp/claude-0/-home-user-1L3A-Proje/bee1199a-0b5d-5964-8f7d-e654dea778f9/scratchpad/ref_adoring/sonuclar/dis_arastirma/2026-11_freqtrade_robotic")
DAL = "dal:claude/adoring-maxwell-q7t60g:sonuclar/dis_arastirma/2026-11_freqtrade_robotic/"
ARA = KOK + "/sonuclar/hesap_defteri/ara/"
KAYNAK = {"dosya_listesi": "B001", "kume_listesi": "B002", "rapor": "B003", "canli": "B004", "e0v1e": "B005", "ewo": "B006"}
H001 = "stratejiler/ek_kaynaklar/github_g1_freqtrade.csv"
D001 = "stratejiler/dis_envanter.csv"


def oku(yol, **kw):
    with open(yol, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


dosyalar = oku(R + "/dosya_listesi.csv")
kumeler = {x["kume_id"]: x for x in oku(R + "/kume_listesi.csv")}
ewo = oku(R + "/canli_akraba/ewo_aile.csv")
kod = {x["ad"]: x for x in oku(ARA + "kod_kaydi.csv")}
h001 = oku(KOK + "/" + H001)
d001 = oku(KOK + "/" + D001)
assert len(dosyalar) == 909, len(dosyalar)


def ad_kok(yol):
    return yol.rsplit("/", 1)[-1][:-3]


# ------------------------------------------------------------------------------------------------ TEKRAR (H001)
# Aynı dosya adı + çekirdek mantık H001 mekanik_ozet ile çelişmiyor. Çekirdek metni ile özeti çelişenler DIŞARIDA bırakıldı.
TEKRAR_DISI = {  # H001 satırı: neden
    6: "AwesomeMacd: Robotic çekirdek MACD>sinyal+AO yukarı; H001 özeti MACD>0+AO dönüşü (farklı)",
    46: "ReinforcedQuickie: Robotic çekirdek üst TF SMA+MFI+hacim; H001 özeti EMA altı+alt bant+dip (farklı)",
    51: "SmoothScalp: Robotic çekirdeğinde MFI yok (Scalp ile aynı); H001 özeti MFI'lı (farklı)",
    55: "Strategy003: Robotic çekirdek stokastik/EMA kesişimi; H001 özeti RSI<28+Fisher+SMA (farklı)",
    56: "Strategy004: Robotic çekirdek stokastik dönüşü+hacim; H001 özeti ADX/CCI/stokastik (farklı)",
    66: "wtc: Robotic çekirdek yalnız wt1/wt2 kesişimi; H001 özeti stokastik/bant süzgeçleri (doğrulanamadı)",
}
TEKRAR_DOGRULANDI = {  # sınıf kodunu açıp çekirdekle karşılaştırdıklarım (kısa not)
    1: "dis__ft-adx-momentum açıldı: ADX>25+mom>0+DI>25 giriş aynı",
    8: "bbrsi: RSI<30+kapanış<alt BB, çıkış RSI>70 (çekirdek=H001 özeti)",
    13: "dis__ft-cluc-may2018 açıldı: EMA100+0.985xBB alt+hacim<20xSMA30, çıkış orta bant aynı",
    16: "dis__ft-binh-cluc açıldı: Cluc kolu aynı; BinH kolu sınıfta varsayım eşikli",
    21: "dis__ft-ema-skip-pump açıldı: giriş/çıkış aynı",
    35: "dis__ft-low-bb açıldı: kapanış<alt BB x0.98 (alt_pay=0.02 varsayılan) aynı",
    37: "dis__ft-macd-cci açıldı: MACD>sinyal+CCI eşik; sınıf VARSAYIM -50/100 eşikleri",
    38: "dis__ft-macd-cci-kesisim açıldı: MACD yukarı kesişim+CCI<=-50 aynı",
    49: "dis__ft-simple-macd-rsi açıldı: RSI>70+üst BB yükseliyor+MACD>0,>sinyal aynı",
    50: "dis__smooth-operator açıldı: MFI/RSI/CCI girişi ve karışım çıkışı aynı",
    31: "dis__heracles açıldı: aynı kaynak (4h, ROI/stop aynı)",
    33: "dis__hour-based açıldı: saat aralığı girişi aynı",
    44: "dis__quickie açıldı: ADX>30+TEMA<BB orta+yükseliyor+SMA200 üstü giriş aynı",
    57: "dis__strategy005 açıldı: fisher_rsi_norma/fastd/rsi/sma girişi aynı",
    60: "dis__td-sequential açıldı: sayım>8 giriş aynı",
    61: "dis__technical-cmf açıldı: CMF<0 long seviye kuralı aynı",
    62: "dis__trend-following-ema-obv açıldı: EMA kesişimi+OBV girişi aynı",
    54: "dis__ft-strategy002 açıldı: çekiç+alt BB+RSI<30+slowk<20 girişi aynı",
    14: "dis__ft-cmc-winner açıldı: CMO/CCI/MFI girişi aynı (çekirdekte shift(1))",
    43: "dis__power-tower açıldı: sınıf birimsiz yeniden yazım (üs yerine oran), çekirdek ham üslü",
}
tekrar_exact = {}  # dosya yolu -> (h001 satırı, not)
adlar = collections.defaultdict(list)
for j, x in enumerate(h001, 1):
    adlar[x["ad"].lower()].append(j)
for x in dosyalar:
    k = ad_kok(x["dosya"]).lower()
    if k in adlar:
        j = adlar[k][0]
        if j in TEKRAR_DISI:
            continue
        if k == "godstra" and x["kume_id"] != "K143":  # K402 GodStra varyantları: aynı mantık doğrulanamadı
            continue
        tekrar_exact[x["dosya"]] = j
OLASI_TEKRAR = {}  # TEKRAR verilmeyen ama ad aynı olanlar: dosya -> (j, neden)
for x in dosyalar:
    k = ad_kok(x["dosya"]).lower()
    if k in adlar and x["dosya"] not in tekrar_exact:
        j = adlar[k][0]
        OLASI_TEKRAR[x["dosya"]] = (j, TEKRAR_DISI.get(j, "ad aynı, mantık doğrulanamadı"))
# ssssi/freqtrade_strs akrabaları (ad benzer, çekirdek farklı -> TEKRAR değil)
AKRABA_H001 = {"E0V1E": 75, "E0V1EN": 75, "ClucHAnix_5m": 76, "ClucHAnix": 76, "BBMod": 81}
for x in dosyalar:
    k = ad_kok(x["dosya"])
    if k in AKRABA_H001 and x["dosya"] not in OLASI_TEKRAR:
        OLASI_TEKRAR[x["dosya"]] = (AKRABA_H001[k], "ssssi/freqtrade_strs akraba; çekirdek farklı/doğrulanamadı")

d001_ad = collections.defaultdict(list)
for j, x in enumerate(d001, 1):
    if x["kaynak"] == "freqtrade":
        d001_ad[x["ad"].lower()].append(j)

# ------------------------------------------------------------------------------------------------ KÜME KARARLARI
# (eslesme, hedef, fark). Yalnız ELLE DOĞRULANANLAR; diğer BENZERI_TEST kümeleri "önceki ajan kararı, doğrulanmadı".
E, B, Y = "ESDEGER", "BENZER", "YOK"
KUME_KARAR = {}


def k(kid, es, hedef, fark):
    KUME_KARAR[kid] = (es, hedef, fark)


# --- ZATEN_TEST kümeleri (51) -- tek dosyalı olup H001 ile TEKRAR olanlarda fark yalnız diğer üyeler için kullanılır
k("K013", B, "dis__ft-binh-cluc", "Cluc kolu (EMA100, BB(20,2)x0.985, hacim<20xSMA30, çıkış orta bant) aynı; sınıfta ek BinH kolu ve varsayım eşikleri; V2/V3 varyant eşikleri açılmadı")
k("K019", B, "dis__ft-binhv27", "çekirdek metni dolaylı giriş (atom çıkmadı); sınıf ile satır satır kıyas yapılamadı")
k("K023", B, "dis__ha-bb40-cluc", "çekirdek: HA kapanış<EMA yavaş ve <alt BB x çarpan, çıkış HA/EMA hızlı; sınıf: HA tipik fiyat BB(40), önceki alt bant + HA kuyruk/fark koşulları, çıkış farklı")
k("K024", B, "dis__ha-bb40-cluc", "çekirdek: HA kapanış<EMA yavaş ve <alt BB x çarpan (5m ClucHAnix); sınıf BB(40) HA tipik fiyat + ek koşullar, 15m")
k("K038", B, "dis__ft-reinforced-quickie", "çekirdek: üst TF SMA yönü + MFI<30 + hacim filtresi + alt BB, çıkış MFI>80/RSI>70/üst BB; sınıf: EMA20/50 altı + alt BB + dip_n, çıkış EMA20 üstü")
k("K057", B, "dis__ft-bandtastic", "çekirdek yalnız tetik seçimi (bb_lower1..4), süzgeçler kesik; sınıf RSI<35/MFI<35/EMA20>EMA50 varsayım eşikli")
k("K063", E, "dis__ft-cluc-may2018", "yok")
k("K070", E, "dis__ft-low-bb", "yok")
k("K076", E, "dis__ft-simple-macd-rsi", "yok")
k("K077", E, "dis__smooth-operator", "yok")
k("K090", E, "dis__heracles", "yok")
k("K123", B, "dis__ft-reinforced-smoothscalp", "çekirdek: %K/%D yukarı kesişimi + üst TF SMA + MFI + fastd eşiği; sınıf: kesişimsiz seviye (%K,%D<eşik) + açılış<EMA5 düşük x ac_k")
k("K180", E, "dis__ft-ema-skip-pump", "yok")
k("K184", B, "dis__ust-tf-ma-yon-kesisim", "çekirdek: EMA20>EMA50 durumu + 15m kapanış>SMA20 (durum); sınıf: hızlı MA yavaşı yukarı KESER + üst TF yön filtresi")
EWO_ORTAK = "sınıf: EMA8x0.96 + EWO%(5,35)<-3 + RSI14<30 + RSI4<45 + CTI20<-0.5, çıkış EMA16/32 mum/3xATR stop; "
k("K102", B, "dis__ewo-ema-ofset", "çekirdek: ma_buy ofset + RSI buy + EWO(50,200) alt/üst aralığı, çıkış ma_sell ofset; " + EWO_ORTAK + "EWO ölçeği farklı")
k("K111", B, "dis__ewo-ema-ofset", "çekirdek: ma_sell x high_offset altı + RSI<25 + RSI eşiği + EWO<ewo_low, çıkış rsi_fast>rsi_slow/ROI; " + EWO_ORTAK + "EWO ölçeği farklı")
k("K113", B, "dis__ewo-ema-ofset", "çekirdek: ma_buy ofset + RSI + kayan EWO eşiği/açı filtresi (AngleWave), ROI tablosu; " + EWO_ORTAK + "açı filtresi sınıfta yok")
k("K117", B, "dis__ewo-ema-ofset", "çekirdek: 15m max<close x profit_threshold pump süzgeci + ofset + RSI<25 (NASOSv5), EWO yok; " + EWO_ORTAK)
k("K119", B, "dis__ewo-ema-ofset", "çekirdek: close<ema_20 + EWO aralığı + ofset (NFI 5m HO), 1h RSI farkı çıkışı + ROI/trailing; " + EWO_ORTAK)
k("K190", B, "dis__ewo-ema-ofset", "çekirdek: çoklu MA ofset (Lambo) + EWO aralığı, RSI süzgeci yok; " + EWO_ORTAK)
k("K191", B, "dis__ewo-ema-ofset", "çekirdek: EMA ofset + EWO>0 (yön ters: sınıf EWO<-3); " + EWO_ORTAK)
k("K192", B, "dis__ewo-ema-ofset", "çekirdek: ma_sell x high_offset altı + RSI<25 + RSI eşiği + EWO<ewo_low (uzi3), trailing; " + EWO_ORTAK)
k("K200", B, "dis__ewo-ema-ofset", "çekirdek: RSI buy + ma_buy ofset + EWO aralığı, çıkış ma_sell aşağı kesişim; " + EWO_ORTAK)
k("K207", B, "dis__ewo-ema-ofset", "çekirdek: RSI + açılış<ma_buy ofset + EWO<ewo_high (AngleWaveCT/AWATRCT), ROI tablosu; " + EWO_ORTAK)
k("K223", B, "dis__ewo-ema-ofset", "çekirdek: NASOSv5 DanMod: pump süzgeci + ofset + RSI<25, trailing; " + EWO_ORTAK)
k("K241", B, "dis__ewo-ema-ofset", "çekirdek: ma_entry ofset + RSI entry + EWO<ewo_low + ma_exit üstü; " + EWO_ORTAK)
k("K243", B, "dis__e0v1en", "E0V1E_53_Sharpe: eşikler farklı (RSI4<65, RSI14>19, SMA15x0.961, CTI<-0.04), çıkış kârda fastk/CCI, stop -%25+trailing, 5m, 24s filtresi yok; E0V1E__2: giriş eşikleri aynı ama çıkış/stop/TF/24s filtresi farklı (canli_akraba/e0v1e_karsilastirma.csv)")
k("K251", B, "dis__e0v1en", "Robotic E0V1E.py kırpık/bozuk: giriş fiilen yalnız RSI4<40 (diğer koşullar yorumda); çıkış fastk/CCI kârda, stop -%25, 5m, 24s filtresi yok")
k("K259", E, "dis__ft-adx-momentum", "yok")
k("K264", B, "dis__ft-awesome-macd", "çekirdek: MACD>sinyal + AO yukarı (ao>ao.shift); sınıf: MACD>0 + AO dönüş (t-1<=t-2) + ADX>=20 (varsayım)")
k("K265", B, "dis__ft-awesome-macd", "çekirdek: ao.shift<0, macd>0, ao>0 (AO sıfır yukarı geçişi); sınıf AO dönüşü + ADX>=20")
k("K266", B, "dis__ft-cci-cmf-mfi", "çekirdek: üst TF MA'lar + MFI<25 + CMF<-0.1 + CCI<-100; sınıf CCI(20)&CCI(10)<-100 + CMF + MFI<30 (MA yok), çıkış CCI>100")
k("K267", B, "dis__ft-cmc-winner", "çekirdek giriş değerleri shift(1) (1 mum gecikmeli: cmo<-50, cci<-100, mfi<20); sınıf anlık mum değerleri")
k("K269", B, "dis__ft-cofibit", "çekirdek: açılış<ema_low (çarpansız) + %K/%D kesişimi + ADX eşiği; sınıf ac_k=0.99/cik_k=1.01 çarpanları ve ADX>20 varsayım")
k("K278", E, "dis__ft-macd-cci", "yok")
k("K279", E, "dis__ft-macd-cci-kesisim", "yok")
k("K287", B, "dis__ft-multi-rsi", "çekirdek: çoklu üst TF RSI eşikleri (x8, x2); sınıf tek üst TF + sabit eşik (varsayım 35/50/70)")
k("K295", B, "dis__ft-swinghightosky", "çekirdek: CCI/RSI periyotları hyperopt (cciTime/rsiTime); sınıf tek periyot (CCI20, RSI14, kayma 1) varsayım eşikli")
k("K310", E, "dis__ft-strategy002", "yok")
k("K311", B, "dis__ft-strategy003", "çekirdek: fastd/EMA50>EMA100/EMA5-10 kesişimi + MFI<16; sınıf: RSI<28 + Fisher RSI<-0.94 + kapanış<SMA40 + MFI<16")
k("K312", B, "dis__ft-strategy004", "çekirdek: hacim ortalaması + stokastik kesişimi + slowk önceki<30; sınıf: ADX/yavaş ADX + CCI<-100 + stokastik kesişimi")
k("K313", E, "dis__strategy005", "yok")
k("K314", B, "dis__ft-scalp-ema-adx", "çekirdek: açılış<ema_low + ADX>30 + %K/%D yukarı KESİŞİMİ + <30; sınıf (Scalp/SmoothScalp): kesişimsiz seviye koşulu (+MFI SmoothScalp'ta)")
k("K319", E, "dis__quickie", "yok")
k("K323", B, "dis__cryptofrog-dip", "çekirdek metni yalnız tek tetik (MFI<30) gösteriyor; sınıf dört tetikli (BB genişleme/SAR+StochRSI/...) ve HA dip ön koşulu; 9 varyant ayrıca açılmadı")
k("K341", E, "dis__trend-following-ema-obv", "yok")
k("K348", E, "dis__hour-based", "yok")
k("K352", B, "dis__power-tower", "çekirdek ham üslü fiyat karşılaştırması (close.shift(2)>close.shift(4)**pow, fiyat birimine bağlı); sınıf birimsiz oran yeniden yazımı")
k("K355", E, "dis__td-sequential", "yok")
k("K356", E, "dis__technical-cmf", "yok")
# --- BENZERI_TEST kümelerinden ELLE DOĞRULANANLAR (sınıf kodu/belgesi açıldı)
k("K219", B, "dis__aroon-stochrsi-ema-dip", "NFI X2 monoliti (çok kollu; çekirdek metni index==1); ilk 8 sınıf yalnız seçili çekirdek kolları kodluyor, monolit bütünü yok")
k("K346", B, "dis__ayin-ilk-gunu-deseni", "çekirdek: sabit ay-günü x hafta-günü x saat 00:00 takvim girişi (çıkış 23:00); sınıf: ayın ilk günü + önceki gün getirisi eşiği")
k("K227", B, "swing__rsi-diverjans", "çekirdek: çok göstergeli boğa diverjans sayımı>0 (pivot geriye yazma şüphesi); sınıf tek osilatör (RSI/CCI) diverjansı")
k("K039", Y, "", "çekirdek metni çelişkili (mfi<20 ve mfi>80 aynı koşulda); önceki eşleşme (gosterge-oy-toplami, cok-gosterge-teyit) reddedildi")
k("K042", Y, "", "çekirdek metni çelişkili (mfi<25 ve >75) + 1h BB bölge limitleri; önceki eşleşme (bant-donus, bb-stoch-gu-dip) doğrulanamadı, reddedildi")
k("K132", B, "swing__heikin-ashi-donus", "çekirdek: son 5 mumda HA MACD+SSL+momentum yukarı çaprazlarının üçü birden; sınıf: HA renk dönüşü serisi (ATR stop)")
k("K149", B, "swing__ichimoku", "çekirdek: yalnız kapanış>senkou A ve B (bulut üstü durum); sınıf kijun_bulut modu: kapanış>bulut ve >kijun, ATR stop")
k("K349", B, "dis__momentum-roc-filtreli", "çekirdek: ROCR>1.1 ve ikinci ROCR>1.01 (1m); sınıf: momentum>0/ROC+stokastik/SMA50 modları")
k("K354", B, "dis__oncekigun-kirilim", "çekirdek: kapanış 30 günlük dibi (üst TF) yukarı keser; sınıf önceki UTC günün tepe/dip seviye kırılımı")
k("K362", B, "dis__wtc-wavetrend", "çekirdek: wt1 aşırı satım/alım seviye bandı içinde (kesişim yok), çıkış wt1 işareti; sınıf wt1/wt2 kesişimi + stokastik/fark bant süzgeçleri")
k("K229", B, "dis__ft-fsupertrend", "çekirdek: üç Supertrend (hyperopt periyot/çarpan) 'up'; çıkış birleşimi çekirdekte kesik; sınıf 8/4, 9/7, 8/1 varsayım değerleri, üç satım Supertrend'i")
k("K247", B, "dis__asiri-bolge-osilator-kesisimi", "çekirdek: MACD yukarı kesişim + son 8 mumda RSI min<41 + kapanış>EMA200, çıkış RSI max>93/MACD>0; sınıf: son pencerede RSI<=alt + MACD kesişimi (EMA200 filtresi yok)")
k("K002", B, "dis__alma-macd-kesisimi", "çekirdek: MACD yukarı kesişim + SMA kısa/orta kesişimi + macd>-1e-5; sınıf: kapanış>ALMA + MACD kesişimi")
k("K025", B, "dis__ft-binh-cluc", "önceki eşleşmeler (kuvvet-endeksi-bollinger, bbpower-sqz) reddedildi; V5: Cluc+BinH karışımı (close<=önceki kapanış, close<önceki alt bant, hacim<xSMA, EMA yavaş), çıkış üst BB; sınıf VEYA kollu BinH/Cluc ayrı eşikli")
k("K026", Y, "", "çekirdek metni yok (row['buy']==1, özel kod); önceki eşleşmeler (rsi-ma-kesisim, ema-serit-yelpaze) alakasız reddedildi; olası akraba dis__ft-binh-cluc yalnız ad ailesi, doğrulanamadı")
k("K040", Y, "", "çekirdek canlı trailing-buy/dry_run kodu (iloc[-1], Trade); önceki eşleşme (ardisik-bar-tukenme) alakasız, reddedildi")
k("K041", Y, "", "çekirdek: çoklu TF +DI/-DI (5m/15m/30m) çelişkili metin; önceki eşleşme (adx-seviye-durumu, adx-di-esik-kesisimi) örtüşmüyor, reddedildi")
k("K055", Y, "", "çekirdek: TEMA alt BB'yi yukarı keser + RSI dönüş (hyperopt, ROI/trailing); önceki eşleşme (codex-wd-gunluk-donus, qqe-giris) örtüşmüyor, reddedildi")
k("K066", Y, "", "çekirdek: +DI>0.5, ADX>65, RSI<35, fastd<35 (uç eşikli deneme); önceki eşleşme (rsi-gauss-velocity, stochrsi-uc-4h) örtüşmüyor, reddedildi")
k("K087", Y, "", "çekirdek: Keltner bandı iki yönlü taşma + 4h BB genişliği + 30m RSI/ortalaması; önceki eşleşme (nw-zarf-rsi, flawless-bbrsi) örtüşmüyor, reddedildi")
k("K144", B, "swing__mum-coklu-formasyon", "çekirdek: TA-Lib CDL3INSIDE>=0 + ADX>13 + kapanış<kapanış[2] + RSI<50 (1d); sınıf: ATR eşikli 3+ mum desenleri + R hedefi (önceki geri-cekilme eşleşmesi reddedildi)")
k("K204", B, "swing__mum-coklu-formasyon", "çekirdek: TA-Lib ENGULFING/HARAMI/ABANDONEDBABY/3LINESTRIKE birleşimi + EMA açılış<kapanış süzgeci; sınıf ATR eşikli desen tanımları (önceki ma-geri-cekilme eşleşmesi reddedildi)")
k("K249", B, "swing__rsi-asiri-donus", "çekirdek: SMA hızlı/yavaş durumu + RSI eşikleri (çelişkili metin); sınıf RSI aşırı bölgeden dönüş (alt'ı yukarı keser), SMA süzgeci yok")
k("K285", B, "swing__macd-sinyal", "çekirdek: MACD histogram dönüşü (hist<0, yükselmeye başlıyor) + korelasyon filtresi; sınıf MACD çizgisi/sinyal kesişimi ya da sıfır geçişi")
k("K296", B, "dis__stoch-macd-cift", "çekirdek: EMA5 kapanış>=açılış + kapanış yükseliyor + fastd<=80 + MACD ve sinyal yükseliyor; sınıf: yavaş stokastik K/D kesişimi + MACD hist sıfır geçişi")
k("K317", B, "dis__wtc-wavetrend", "önceki eşleşmeler (gosterge-rezonansi, ema-macd-ortalamaya-donus) reddedildi; çekirdek: wt1 wt2'yi yukarı keser + macd>sinyal; sınıf: WT kesişimi + stokastik/fark bandı (MACD yok)")
k("K315", B, "swing__supertrend-psar", "önceki eşleşmeler (trend-analysis, ott-bantlari) reddedildi; çekirdek: Supertrend üstü + EMA dizilimi + ADX>25 + VOSC>0; sınıf yalnız Supertrend/PSAR yön değişimi (+opsiyonel RSI)")
k("K326", Y, "", "çekirdek: RSI + EMA7/TEMA aşağı kesişimi + canlı bid fiyatı (best_bid); önceki eşleşme (s1-geri-cekilme, bch-ha-rsi-fade) örtüşmüyor, reddedildi")
k("K361", Y, "", "çekirdek: RSI-MA eğimi + WaveTrend t1>=t2 (6h/1d, ROI -0.01); önceki eşleşme (linreg-rsi-dip, kst-skyrexio) örtüşmüyor, reddedildi")
k("K053", Y, "", "çekirdek: yalnız TEMA eğimi pozitif (1m); sınıf swing__ma-kesisim MA kesişimi kuralı değil, önceki eşleşme reddedildi")
k("K054", B, "dis__bbrsi-donus", "çekirdek: aynı mumda RSI<30 + kapanış<alt BB(20), çıkış RSI>70; sınıf: önceki mumda RSI(7)<30 & kapanış<alt BB(500), şimdi dönüş (kapanış banda geri)")
k("K064", Y, "", "çekirdek: BB alt bant teması + destek + EMA altında düşüş mumu (1m, özel kod); önceki eşleşme (pivot-hacim-ema150) örtüşmüyor, reddedildi")
k("K115", B, "dis__ma20-rsi-cmf", "çekirdek: kapanış>SMA20 durumu + RSI 30-70 bandı + kapanış>alt BB (EMA dalga adlı şablon); sınıf: SMA20 yukarı KIRILIMI + RSI trend çizgisi kırılımı + CMF")
k("K167", B, "dis__rf-ha-scalper", "çekirdek: Range-filter benzeri filtre yükseliyor, kapanış filtrenin ±%1 içinde (3m, çıkış ±%2); sınıf: Range Filter yönü + yumuşatılmış HA yönü + üst TF")
k("K197", B, "daytrade__renko-sr", "çekirdek: Renko trend dönüşü (previous-trend False->True) tek koşul, stopsuz; sınıf: Renko dönüş tuğlası + RSI/StochRSI aşırı bölge + destek bölgesi + ATR stop")
k("K250", B, "dis__mtf-rsi-trend", "çekirdek: 12h RSI>49 + kapanış>12h MA50 + dolar hacim>2M (1h); sınıf: günlük ve haftalık RSI(30)>70 + MA hizası")
k("K298", B, "dis__iki-gosterge-egimi", "çekirdek: TRIX histogram>0 + StochRSI<eşik (seviye koşulları); sınıf: iki göstergenin eğim işareti (trix-fab dahil)")
k("K305", B, "dis__hma-atr-rider", "çekirdek: HMA kısa-uzun farkı yükseliyor (2 mum) + Williams %R eşiği (15m); sınıf: HMA(20) eğimi/ATR + rejim hizası")
k("K338", B, "swing__mum-coklu-formasyon", "çekirdek: TA-Lib iki-mum desen toplamı (pattern==4, pattern_mean>4); sınıf: 3+ mum ATR eşikli desenler")
k("K351", B, "dis__ft-highwave", "çekirdek: seçilen TA-Lib mum örüntüsü hyperopt parametresi (buy_pr1==buy_vol1), günlük; sınıf yalnız CDLHIGHWAVE tanımı")
k("K142", B, "dis__vwap-alt-bant-dip", "çekirdek: VWAP low>close + kapanış<BB3 alt x0.995 + CTI + RSI14<53, çıkış zaman/RSI hızlı; sınıf: yuvarlanan VWAP(20) alt bandı dip (BB3/CTI yok)")
k("K187", B, "dis__pmax-giris", "çekirdek: RSI hızlı<30 + kapanış<TRIMA ofset(2 kat) + pmax eşiği (MultiMA TSL); sınıf: PMax yapışkan bant yön değişimi")
k("K001", B, "dis__alligator-dizilim", "çekirdek: EMA28>EMA48 durumu + StochRSI<eşik (1h); sınıf Williams Alligator (LWMA çene/diş/dudak dizilimi)")
k("K094", B, "dis__ema-esik-trend", "çekirdek: üst TF EMA50>EMA100>EMA200 hizası + SSL yukarı; sınıf EMA20>EMA60x(1+eşik) durumu")
k("K131", B, "swing__heikin-ashi-donus", "çekirdek: HA kapanış/açılış eğimi ve tahmin serisi dönüşü (HSI, 5m); sınıf HA renk dönüşü serisi")
k("K061", Y, "", "çekirdek: CMO sıfır yukarı geçişi (hyperopt, ROI/trailing); önceki eşleşme (pf__sinif_kesit_mom, kesitsel momentum portföyü) alakasız, reddedildi")
k("K071", B, "dis__flawless-bbrsi", "önceki eşleşmeler (twap-rsi, rsi-ma-kesisim) reddedildi; çekirdek: kapanış<alt BB(2σ) + RSI>30, çıkış üst BB; sınıf: alt BB(1σ) altı + RSI>42, çıkış üst band + RSI>70")
k("K081", B, "swing__ma-kesisim", "önceki eşleşmeler (codex-wd-hacim-akisi, ft-ema-skip-pump) reddedildi; çekirdek: EMA5 EMA10'u yukarı keser (1m); sınıf MA kesişimi, hızlı/yavaş periyot ızgarası 5/10'u içerdiği doğrulanmadı")
k("K088", B, "swing__bant-donus", "çekirdek: Keltner orta bandı arası + BB%b aşırı satım geri dönüşü (iki bant); sınıf: Bollinger/envelope bandı dışından geri dönüş, hedef orta bant")
k("K098", B, "dis__ha-bb40-cluc", "çekirdek: HA close delta>%0.8 + Williams %R(14) -90..-80 + KC/BB delta bandı (5m); sınıf: HA BB(40) dip + ek kuyruk/fark koşulları, Williams/KC yok")
k("K195", B, "dis__stochrsi-uc-4h", "çekirdek: 3EMA + StochRSI + ATR bileşik sinyal go_long yukarı geçişi; sınıf StochRSI %K<20 saf uç değer girişi")
k("K198", Y, "", "çekirdek: kırmızı mum gövdesi>gövde SMA (4h, stopsuz); önceki eşleşme (ft-ema-skip-pump, vwap-donus) örtüşmüyor, reddedildi")
k("K237", E, "swing__supertrend-psar", "yok")
k("K301", Y, "", "çekirdek: Aroon up/down + ADX eşikleri (1m); önceki eşleşme (adx-di-esik-kesisimi, adx-trend-baslangici) Aroon içermiyor, reddedildi")
k("K316", Y, "", "çekirdek: RSI<aşırı alım + SMA50>SMA200 + ADX>eşik (kâr hedefli çıkış); önceki eşleşme (ft-binhv27, voltarget-trend) örtüşmüyor, reddedildi")
k("K318", B, "dis__ft-fsupertrend", "çekirdek: üç Supertrend 'up'; çıkış iki satım Supertrend'i 'down' (hyperopt Opt); sınıf: üç satım Supertrend'inin ÜÇÜ de düşüşte, varsayım periyotlar")
k("K037", B, "swing__cci-esik", "çekirdek: CCI<=-57 + MFI<24 + kapanış<alt BB üçlü süzgeci, çıkış MFI/CCI/üst BB; sınıf yalnız CCI eşik kesişimi (Lambert ±100 vb.)")
for kid, v in KUME_KARAR.items():
    assert kid in kumeler, kid
    if v[1]:
        assert v[1] in kod, (kid, v[1])

DOGRULANAN_BENZERI = {kid for kid in KUME_KARAR if kumeler[kid]["sinif"] in ("BENZERI_TEST", "ZATEN_TEST")}

# ------------------------------------------------------------------------------------------------ yardımcılar
ewo_yol = {}
for i, x in enumerate(ewo, 1):
    p = x["dosya"]
    p = p.replace("AIRA/ew/", "AIRA - open code v2/strategies/elliott-wave/").replace("repo/ew/", "strategies/elliott-wave/")
    ewo_yol[p] = (i, x)

sirali = collections.defaultdict(list)
for i, x in enumerate(dosyalar, 1):
    sirali[x["kume_id"]].append(i)
temsilci = {kid: v[0] for kid, v in sirali.items()}

MR_ANAH = ("bb_lowerband", "lowerband", "bb_lower", "rsi <", "rsi_fast <", "cci <", "cci <=", "mfi <", "oversold", "offset", "ofset", "< ema", "cti <", "r_14", "willr", "dip")
TR_ANAH = ("crossed_above(ema", "crossed_above(sma", "supertrend", "adx >", "macd >", "sma_200", "ema50 >", "> ema", "ichimoku", "senkou", "trend", "fastma > slowma", "hma", "ema28 >")


def aile(x, cek):
    t = (cek or "").lower()
    mr = sum(a in t for a in MR_ANAH)
    tr = sum(a in t for a in TR_ANAH)
    if mr == 0 and tr == 0:
        return {"bollinger": "MR", "binh-cluc-mad": "MR", "elliott-wave": "MR", "nostalgia-for-infinity": "MR",
                "ichimoku": "trend", "pivot-supertrend": "trend", "moving-average": "trend", "heikin-ashi": "trend",
                "wavetrend": "diger", "rsi-momentum": "diger"}.get(x["aile_klasor"], "diger")
    return "MR" if mr > tr else ("trend" if tr > mr else "diger")


def kisa(c):
    c = re.sub(r"\s+", " ", c or "")
    c = c.replace("GIRIS:", "Giriş:").replace("CIKIS:", "Çıkış:").replace("RISK:", "Risk:").replace(" VE ", " ve ").replace(" VEYA ", " veya ")
    return c if len(c) <= 160 else c[:157] + "..."


def ad120(p):
    return p if len(p) <= 120 else "..." + p[-117:]


def tr_dosya(x):
    return DAL + "dosya_listesi.csv"


def kume_kanit(kid):
    return DAL + "kume_listesi.csv#" + kid


def sinif_kanit(hedef):
    r = kod[hedef]
    return "%s#%s" % (r["dosya"], r["sinif"])


def dosya_kanit(i):
    return DAL + "dosya_listesi.csv:%d" % i


# ------------------------------------------------------------------------------------------------ ham satırları üret
SUT = ["ham_id", "kaynak_id", "kaynak_satir_no", "kaynaktaki_ad", "kisa_mantik", "aile", "eslesme", "hedef", "ayar_id",
       "ayar_dosyasi", "fark", "on_durum", "neden_kodu", "neden_metni", "kanit", "not"]
satirlar = []
istat = collections.Counter()

for i, x in enumerate(dosyalar, 1):
    kid = x["kume_id"]
    kr = kumeler[kid]
    cek = kr["cekirdek_mantik"]
    r = {s: "" for s in SUT}
    r["ham_id"] = "B001:%d" % i
    r["kaynak_id"] = "B001"
    r["kaynak_satir_no"] = str(i)
    r["kaynaktaki_ad"] = ad120(x["dosya"])
    r["kisa_mantik"] = kisa(cek)
    r["aile"] = aile(x, cek)
    not_ = []
    sinif = x["dosya_sinif"]
    ewo_k = ewo_yol.get(x["dosya"])
    if ewo_k:
        not_.append("ewo_aile.csv#%d alt_grup: %s" % (ewo_k[0], ewo_k[1]["alt_grup"][:60]))
    d_ad = d001_ad.get(ad_kok(x["dosya"]).lower())
    kanit_ek = []
    if x["dosya"] in OLASI_TEKRAR:
        j, neden = OLASI_TEKRAR[x["dosya"]]
        not_.append("olası tekrar: H001:%d (%s)" % (j, neden))
    flag = x["bayraklar"].replace(" ; ", ",")
    if x["dosya"] in tekrar_exact and sinif != "ML_FREQAI":
        j = tekrar_exact[x["dosya"]]
        r.update(eslesme="TEKRAR", hedef="H001:%d" % j, on_durum="TEKRAR", neden_kodu="kopya",
                 neden_metni="Aynı freqtrade stratejisi github_g1_freqtrade.csv'de zaten ham satır (ad aynı, çekirdek mantık özetiyle uyumlu)",
                 kanit="%s:%d ; %s" % (H001, j, dosya_kanit(i)), fark="")
        if j in TEKRAR_DOGRULANDI:
            not_.append("sınıf/çekirdek kıyası: " + TEKRAR_DOGRULANDI[j])
        not_.append("hedef satırın akıbeti: %s / %s" % (h001[j - 1]["durum"][:50], h001[j - 1]["ayar_durumu"][:50]))
        if d_ad:
            not_.append("ayrıca dis_envanter D001:%d" % d_ad[0])
        if sinif != "KULLANILABILIR":
            not_.append("Robotic sınıfı: %s (%s)" % (sinif, x["neden"][:60]))
        r["not"] = " | ".join(not_)
        satirlar.append(r)
        istat["TEKRAR"] += 1
        continue
    if sinif == "ML_FREQAI":
        r.update(eslesme="YOK", on_durum="G_ML", neden_kodu="ml",
                 neden_metni="FreqAI/ML/model tahmini: %s" % x["neden"][:90], kanit="%s ; %s" % (dosya_kanit(i), kume_kanit(kid)))
        if "LA" in x["neden"] or "DCA" in x["neden"]:
            not_.append("ayrıca bayrak: " + x["neden"][:80])
    elif sinif == "DCA_POZISYON_BUYUTME":
        mart = "martingale" in x["neden"].lower() or "MARTINGALE_METIN" in x["bayraklar"]
        r.update(eslesme="YOK", on_durum="F_YASAK_TIP", neden_kodu="martingale" if mart else "dca",
                 neden_metni=("martingale/yeniden giriş" if mart else "adjust_trade_position ile pozisyon büyütme (DCA)") + ": " + x["neden"][:80],
                 kanit="%s ; %s" % (dosya_kanit(i), kume_kanit(kid)))
        if "LA" in x["neden"]:
            not_.append("ayrıca lookahead: " + x["neden"][:80])
    elif sinif == "LOOKAHEAD_YUKSEK":
        r.update(eslesme="YOK", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="lookahead",
                 neden_metni="Yüksek lookahead (RAPOR.md: katalog işareti veya AST kontrolü): %s" % x["neden"][:90],
                 kanit="%s ; %s" % (dosya_kanit(i), DAL + "RAPOR.md"))
    elif sinif == "DIGER_KULLANILAMAZ":
        n = x["neden"]
        if "LLM" in n:
            r.update(eslesme="YOK", on_durum="G_ML", neden_kodu="llm", neden_metni="LLM (DeepSeek) karar veriyor, deterministik değil: " + n[:70])
        elif "sablon" in n:
            r.update(eslesme="YOK", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="arac_sablon", neden_metni="Şablon/mantıksız test stratejisi: " + n[:80])
        elif "rastgele" in n:
            r.update(eslesme="YOK", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="rastgele_giris", neden_metni="Giriş rastgele sayıya dayalı: " + n[:80])
        else:
            r.update(eslesme="YOK", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="backtest_gecersiz", neden_metni=n[:110])
        r["kanit"] = "%s ; %s" % (dosya_kanit(i), kume_kanit(kid))
    elif ewo_k and ewo_k[1]["lookahead"].startswith("EVET"):
        r.update(eslesme="YOK", on_durum="D_KODLANMADI_NEDENLI", neden_kodu="lookahead",
                 neden_metni="EWO_MEAN/move_mean tüm veri .mean() ile gelecek bilgisi (canli_akraba raporu; katalog KAÇIRDI): " + ewo_k[1]["lookahead"][:60],
                 kanit="%s#%d ; %s" % (DAL + "canli_akraba/ewo_aile.csv", ewo_k[0], DAL + "canli_akraba/RAPOR.md"))
        not_.append("Robotic sınıfı KULLANILABILIR; kümenin önceki ajan eşleşmesi: %s" % (kr["eslesen_arsiv_id"] or "-"))
    else:
        # küme düzeyi karar
        if kid in KUME_KARAR:
            es, hedef, fark = KUME_KARAR[kid]
            dogr = "doğrulandı"
        elif kr["eslesen_arsiv_id"]:
            es, hedef, fark = B, kr["eslesen_arsiv_id"].split(" ; ")[0], "doğrulanmadı: önceki ajan kararı (kume_listesi eşleşmesi, gösterge-ailesi benzerliği); kural farkı açılmadı"
            dogr = "doğrulanmadı"
            not_.append("önceki ajan kararı, doğrulanmadı")
            if "eslesme guveni" in kr["notlar"]:
                m = re.search(r"eslesme guveni: ([a-z\-]+)", kr["notlar"])
                if m:
                    not_.append("önceki güven: " + m.group(1))
            if len(kr["eslesen_arsiv_id"].split(" ; ")) > 1:
                not_.append("diğer önceki eşleşmeler: " + kr["eslesen_arsiv_id"].replace(" ; ", ","))
        else:
            es, hedef, fark = Y, "", ""
            dogr = "eşleşmesiz"
        if es == E and temsilci[kid] != i:
            es, fark = B, "küme üyesi: temsilci (%s) ESDEGER doğrulandı; bu dosyanın parametre/ek koşul farkı açılmadı" % ad_kok(dosyalar[temsilci[kid] - 1]["dosya"])
        if es == E:
            r.update(eslesme="ESDEGER", hedef=hedef, fark="yok", on_durum="KOD", neden_kodu="",
                     kanit="%s ; %s" % (sinif_kanit(hedef), kume_kanit(kid)))
            not_.append("sınıf kodu açıldı, giriş+sinyal çıkışı aynı (stop/ROI motor uyarlaması); parametreler çekirdekte yok -> ızgara içinde varsayıldı")
        elif es == B:
            r.update(eslesme="BENZER", hedef=hedef, fark=fark, on_durum="D_KODLANMADI_NEDENLI", neden_kodu="benzer_var",
                     neden_metni="Benzer sınıf %s var, fark test edilmedi" % hedef,
                     kanit="%s ; %s" % (sinif_kanit(hedef), kume_kanit(kid)))
        else:
            r.update(eslesme="YOK", on_durum="E_KODLANMADI_NEDENSIZ", neden_kodu="",
                     neden_metni="Kullanılabilir küme; hiçbir dosyada akıbeti yazmıyor (RAPOR.md 'test edilebilir' akıbet değildir)" + ("; önceki eşleşme reddedildi: " + fark if fark else ""),
                     kanit="%s ; %s" % (kume_kanit(kid), dosya_kanit(i)))
            if not kr["eslesen_arsiv_id"]:
                not_.append("kume sınıfı %s" % kr["sinif"])
        if kid in KUME_KARAR and es != Y:
            not_.append("küme kararı elle doğrulandı")
        if kid in KUME_KARAR and KUME_KARAR[kid][0] == Y and kr["eslesen_arsiv_id"]:
            not_.append("önceki ajan eşleşmesi reddedildi: " + kr["eslesen_arsiv_id"].replace(" ; ", ","))
        if x["bayraklar"]:
            not_.append("bayrak: " + flag[:90])
    if kid in KUME_KARAR is False:
        pass
    r["not"] = " | ".join(n for n in not_ if n)
    satirlar.append(r)

# ------------------------------------------------------------------------------------------------ yaz
assert len(satirlar) == 909
ids = [s["ham_id"] for s in satirlar]
assert len(set(ids)) == 909
with open(ARA + "G9_ROBOTIC_ham.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=SUT)
    w.writeheader()
    w.writerows(satirlar)

with open(ARA + "G9_ROBOTIC_elle_kararlar.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["tur", "anahtar", "karar", "hedef", "aciklama"])
    for kid, (es, hedef, fark) in sorted(KUME_KARAR.items()):
        kr = kumeler[kid]
        w.writerow(["kume", kid, es, hedef, "önceki: %s/%s; %s" % (kr["sinif"], kr["eslesen_arsiv_id"] or "-", fark)])
    for dosya, j in sorted(tekrar_exact.items(), key=lambda t: t[1]):
        w.writerow(["tekrar", dosya, "TEKRAR", "H001:%d" % j, TEKRAR_DOGRULANDI.get(j, "ad aynı + çekirdek mantık özetle uyumlu (sınıf açılmadı)")])
    for dosya, (j, neden) in sorted(OLASI_TEKRAR.items()):
        w.writerow(["olasi_tekrar_degil", dosya, "TEKRAR_DEGIL", "H001:%d" % j, neden])

# ------------------------------------------------------------------------------------------------ sayımlar (NOTLAR için)
on = collections.Counter(s["on_durum"] for s in satirlar)
es = collections.Counter(s["eslesme"] for s in satirlar)
nk = collections.Counter(s["neden_kodu"] for s in satirlar)
kume_e = {dosyalar[int(s["kaynak_satir_no"]) - 1]["kume_id"] for s in satirlar if s["on_durum"] == "E_KODLANMADI_NEDENSIZ"}
print("on_durum", dict(on))
print("eslesme", dict(es))
print("neden_kodu", dict(nk))
print("E kume", len(kume_e), "dosya", on["E_KODLANMADI_NEDENSIZ"])
ver = [kid for kid in kumeler if kid in DOGRULANAN_BENZERI]
print("dogrulanan kume (BENZERI/ZATEN):", len(ver), "/", sum(1 for x in kumeler.values() if x["sinif"] in ("BENZERI_TEST", "ZATEN_TEST")))
sys.stdout.flush()
