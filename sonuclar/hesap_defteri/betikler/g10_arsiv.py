#!/usr/bin/env python3
"""G10_ARSIV: arsiv/ altindaki eski projelerin strateji listeleri -> ham satirlar.

Cikti: ara/G10_ARSIV_ham.csv, ara/G10_ARSIV_kaynaklar.csv, ara/G10_ARSIV_elle_kararlar.csv, ara/G10_ARSIV_NOTLAR.md
Elle kararlar (kod/kaynak okunarak verildi) bu dosyadaki SATIRLAR tablosundadir; betik yalniz CSV/NOTLAR uretir ve
kontrol yapar (hedef sinif kod_kaydi.csv'de var mi, TEKRAR hedefi gercek satir mi). Test kosmaz.
Calistirma: python3 sonuclar/hesap_defteri/betikler/g10_arsiv.py   (repo kokunden)
"""
import csv
import collections
from pathlib import Path

KOK = Path(__file__).resolve().parents[3]
ARA = KOK / "sonuclar/hesap_defteri/ara"

HAM_SUTUN = ["ham_id", "kaynak_id", "kaynak_satir_no", "kaynaktaki_ad", "kisa_mantik", "aile", "eslesme", "hedef",
             "ayar_id", "ayar_dosyasi", "fark", "on_durum", "neden_kodu", "neden_metni", "kanit", "not"]

# ------------------------------------------------------------------ kaynaklar (A-id)
# (id, yol, tur, satir_veya_kayit, not)
KAYNAKLAR = [
    ("A001", "arsiv/algo-sg/STRATEJILER.md", "birincil:eski_proje_rapor", "8", "algo-sg A1/A2/B + elenen fikirler (S1-S3, geri test, 24s momentum)"),
    ("A002", "arsiv/algo-sg/STRATEJILER_GUNLUK.md", "birincil:eski_proje_rapor", "7", "algo-sg 1W/1D: D1, D2 + elenen girisler"),
    ("A003", "arsiv/algo-sg/docs/A_V2_VE_KALDIRAC.md", "birincil:eski_proje_rapor", "1", "A v2 (rejime bagli short); kaldirac testi strateji degil"),
    ("A004", "arsiv/swing-sg/STRATEJILER.md", "birincil:eski_proje_rapor", "3", "swing-sg S1/S2/S3"),
    ("A005", "arsiv/swing-sg/deneyler/CODEX_ADAYLAR.md", "birincil:kullanici_listesi", "11", "Codex 1. liste: 11 GitHub repo (baslik 12 diyor); C1-C4 testleri bu repolarin 4'u"),
    ("A006", "arsiv/swing-sg/deneyler/CODEX2_ADAYLAR.md", "birincil:kullanici_listesi", "6", "Codex 2. liste: 6 yeni repo; D1-D3 testleri bu repolarin 3'u"),
    ("A007", "arsiv/swing-sg/trend/stratejiler.py", "birincil:kullanici_listesi", "8", "brainbrick-trades long-only 8 kural (docstring satir 7-14); trend/OZET.md, SONUCLAR_TREND.md sonuc"),
    ("A008", "arsiv/strateji-sg/RAPOR.md", "birincil:eski_proje_rapor", "4", "strateji-sg Faz 1: SAKK, GPK, Faz-1 A/B ortak payda testleri"),
    ("A009", "arsiv/strateji-sg/RAPOR_KRIPTO.md", "birincil:eski_proje_rapor", "3", "KGT v1-v3 + 'calismayanlar' tablosundaki girisler"),
    ("A010", "arsiv/strateji-sg/RAPOR_PA.md", "birincil:eski_proje_rapor", "7", "SKA(CBF) + elenen PA kurulumlari (Galen Woods)"),
    ("A011", "arsiv/strateji-sg/RAPOR_EPA.md", "birincil:kullanici_listesi", "2", "kullanicinin EPA fikri: A (pullback) ve B (breakout)"),
    ("A012", "arsiv/strateji-sg/RAPOR_S2.md", "birincil:eski_proje_rapor", "4", "KMN + ortalamaya donus denemeleri"),
    ("A013", "arsiv/strateji-sg/RAPOR_HGT.md", "birincil:eski_proje_rapor", "1", "HGT (20 Strateji Sistem #5 uyarlamasi, 52 varyant tek strateji sayildi)"),
    ("A014", "arsiv/day-trade-sg/daytrade/strategies.py", "birincil:eski_proje_kod", "14", "STRATEGIES sozlugu 15 anahtar; S11 = S10'un at_utc=14 ayari -> 14 ayri mantik; hepsi repo_kodlari.csv daytrade_py (G3)"),
    ("A015", "arsiv/scalp-sg/src/strategies.py", "birincil:eski_proje_kod", "3", "s1/s2/s3; repo_kodlari.csv scalp_py (G3)"),
    ("A016", "arsiv/codex-algo/src/codex_algo/strategies.py", "birincil:eski_proje_kod", "9", "STRATEGIES 9 kural; repo_kodlari.csv codex_py (G3)"),
    ("A017", "arsiv/codex-algo/src/codex_algo/mtf_strategies.py", "birincil:eski_proje_kod", "8", "MTF 8 kural; repo_kodlari.csv codex_py (G3)"),
    ("A018", "arsiv/algo-sg/DIS_STRATEJILER.md", "bilgi:G2_kapsami", "0", "186 sonuc satiri = stratejiler/dis_envanter.csv (freqtrade 68, awesome 32, jesuistm 11, kural 73) = G2 (D001); ham satir YAPILMADI"),
    ("A019", "arsiv/OZET.md", "bilgi:esleme_belgesi", "0", "S2 esleme tablosu ve S3 'denendi-basarisiz' = 1L3A karari; esleme kaniti"),
    ("A020", "arsiv/strateji-sg/tv/aday.csv ; tv_eleme_dali/ham/meta*.json", "bilgi:G2_kapsami", "0", "TradingView 164 + 41 aday = G2; ham satir YAPILMADI"),
    ("A901", "dal:claude/haiku-arge-5-enstruman:sonuclar/haiku_arge/GELISTIRME_ON_KAYIT.md", "bilgi:birlesmemis_dal", "0", "12 gelistirme varyanti: YENI STRATEJI SAYILMADI (karar NOTLAR'da); haiku__varyant sinif dosyasi dalda"),
    ("A902", "dal:claude/haiku-arge-5-enstruman:sonuclar/haiku_arge/SONUC_GELISTIRME.md", "bilgi:birlesmemis_dal", "0", "12 varyantin akibeti: WF 5 gecti, hicbiri K2/K3'ten gecmedi"),
    ("A911", "dal:claude/haiku-strateji-arastirma:stratejiler/ek_kaynaklar/test/SONUC_2026-11.md", "birincil:birlesmemis_dal", "3", "TrendRider, Leah E015, ETH 4s kirilim yeniden testi"),
    ("A912", "dal:claude/haiku-strateji-arastirma:stratejiler/ek_kaynaklar/test/PORTFOY_SONUC_2026-11.md", "birincil:birlesmemis_dal", "3", "GTAA 10 ay SMA, momentum varlik dagilimi, sektor momentum"),
    ("A913", "dal:claude/haiku-strateji-arastirma:stratejiler/ek_kaynaklar/test/PORTFOY_DERIN_2026-11.md", "bilgi:birlesmemis_dal", "0", "A912'deki kurallarin saglamlik testi (yeni strateji yok)"),
    ("A914", "dal:claude/haiku-strateji-arastirma:stratejiler/ek_kaynaklar/test/SON_ADIMLAR_2026-11.md", "bilgi:birlesmemis_dal", "0", "GTAA paper onerisi + 20 varlik GTAA/momentum (A912 kurallarinin evren varyanti)"),
]

# ------------------------------------------------------------------ satirlar (elle karar)
# anahtarlar: k=kaynak_id, n=satir_no, ad, m=kisa_mantik, a=aile, e=eslesme, h=hedef, f=fark, o=on_durum,
#             nk=neden_kodu, nm=neden_metni, c=kanit, no=not, adalet=bool (eski projede elenmis, 1L3A'da dogrudan test yok)
OZ = "arsiv/OZET.md"
S = []


def r(k, n, ad, m, a, e, h="", f="", o="", nk="", nm="", c="", no="", adalet=False):
    S.append(dict(k=k, n=n, ad=ad, m=m, a=a, e=e, h=h, f=f, o=o, nk=nk, nm=nm, c=c, no=no, adalet=adalet))


# ---- A001 algo-sg/STRATEJILER.md
r("A001", "1", "algo-sg Strateji A1 - 4H Donchian20 + hacim", "4H kapanis 20 mum zirvesini/dibini hacim>1.5x ile kirar; EMA100+BTC EMA200 filtre; 2xATR stop, %25 1R kismi, iz suren.",
  "trend", "KOD", "onceki__4s-kirilim", c="motor/strateji/onceki/kirilim_4s.py:1 ; arsiv/algo-sg/STRATEJILER.md#A1",
  no="Sinif docstring'i A1'i dogrudan kaynak gosteriyor. Sapma: 1H giris yerine kendi TF'sinde; BTC filtresi yerine ayni sembolun gunluk EMA200'u, short'a da ayna.")
r("A001", "2", "algo-sg Strateji A2 - Gunluk Donchian20 (Turtle)", "Gunluk kapanis 20 gun zirvesini kirar; 4H EMA200 + BTC gunluk EMA200 filtre; stop 4xATR, iz suren 15xATR, %25 1R kismi.",
  "trend", "BENZER", "onceki__4s-kirilim",
  f="A2: gunluk Donchian + 4H EMA200 + BTC gunluk EMA200, stop 4xATR(4H), iz suren 15xATR; 1L3A sinifi tek TF, ema_trend=100/gunluk_ema=200 varsayilan, iz suren 10xATR (CikisAyarlari), hacim_k=0 ile hacimsiz calisir",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Sinif docstring'i yalniz A1+S2'yi kodlandi diye yaziyor; A2 parametre kombinasyonu (1d, stop 4, iz 15) ayri test edilmedi (DURUM karar 18: A+S2 birlesik).",
  c="motor/strateji/onceki/kirilim_4s.py:1-12,60-66 ; arsiv/algo-sg/STRATEJILER.md#A2", no="DENETIM.md: C=A2 (A ile %95 ayni pozisyon, korelasyon 0.77) - ayri strateji sayilmadi.")
r("A001", "3", "algo-sg Strateji B - Kapitulasyon donusu", "Coinin 24 saatlik getirisi < -%15 ise sonraki 1H aciliste long; 4xATR stop, 1R'de basabas, 96 saat zaman cikisi.",
  "MR", "KOD", "onceki__kapitulasyon", c="motor/strateji/onceki/kapitulasyon.py:1 ; arsiv/algo-sg/STRATEJILER.md#Strateji B",
  no="DURUM karar 18: yedek aday. Sapma: tek sembol, pencere mum sayisi.")
r("A001", "4", "algo-sg elenen: 1H RSI/Bollinger trend yonunde geri cekilme (S1)", "Ust TF trend yonunde 1H RSI esik alti-ustu kesis + alt BB temasi; orta banda donunce cik.",
  "MR", "BENZER", "daytrade__bant-donus",
  f="Eski: ust TF EMA50 yon filtresi + RSI esiginden geri kesis + son 3 mumda alt BB temasi, cikis orta bant/RSI; 1L3A bant-donus: bant disindan ice donus mumu, ADX<25 filtresi, RSI opsiyonel, 1h gun-sonu kapanis",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="OZET.md §3: '1S RSI/BB geri cekilme (PF<1)' eski projede basarisiz; 1L3A'da birebir kural test edilmedi, yakin aile var.",
  c="arsiv/algo-sg/algo/strategies.py:53-95 ; motor/strateji/swing/bant_donus.py:1-20 ; arsiv/OZET.md#3", adalet=True)
r("A001", "5", "algo-sg elenen: 1H Donchian kirilimi (S2)", "Ust TF trend yonunde 1H Donchian kirilimi; kisme kar + basabas, ATR iz suren.", "trend", "BENZER", "daytrade__donchian-kirilim",
  f="Eski: ust TF gunluk yon filtresi (d1_50), opsiyonel ADX/hacim, 1R kismi + iz suren; 1L3A: 1h Donchian giris_n, SMA50 trend_ma, karsi kanal cikisi, gun sonu zorunlu cikis",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="OZET.md §3 '1S Donchian' basarisiz; sinif docstring'i negatif kaniti not ediyor, 1L3A'da kural birebir test edilmedi.",
  c="arsiv/algo-sg/algo/strategies.py:98-130 ; motor/strateji/daytrade/donchian_kirilim.py:1-15 ; arsiv/OZET.md#3", adalet=True)
r("A001", "6", "algo-sg elenen: Fibonacci %50-61.8 olculu hareket geri cekilmesi (S3)", "Son bacagin %50-61.8 bolgesine geri cekilmede 1H donus; stop %78.6, hedef tepe/-%23.6; ust TF trend.", "trend", "BENZER", "swing__fib-geri-cekilme",
  f="Eski: N saatlik bacak + ust ZD yonu, 1H donus, stop %78.6; 1L3A: fraktal/zigzag pivot bacagi, giris 0.382-0.618 bolgesi, stop %100 (ayarlanabilir 0.786), tepki mumu",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="OZET.md §3 'Fibonacci / olculu hareket (OOS PF~0.85)' eski projede basarisiz; 1L3A'da bu bacak tanimiyla test edilmedi.",
  c="arsiv/algo-sg/algo/strategies.py:149-200 ; motor/strateji/swing/fib_geri_cekilme.py:1-25 ; arsiv/OZET.md#3", adalet=True)
r("A001", "7", "algo-sg elenen: 4H kirilim sonrasi 1H geri test girisi", "4H Donchian kirilimindan sonra 1H'de geri test beklenip giris (anindan girise gore kotu).", "trend", "BENZER", "daytrade__kirilim-geri-test",
  f="Eski: 4H kirilim + 1H geri test (coklu TF); 1L3A: tek TF seviye kirilimi + 1..pencere mum icinde geri test + tepki mumu, gun sonu cikis",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede kotu bulundu (STRATEJILER.md); OZET.md §3 listesinde kirilim-geri-test adi yok; 1L3A'da 4H/1H hizali form test edilmedi.",
  c="arsiv/algo-sg/STRATEJILER.md#Test edilip elenen fikirler ; motor/strateji/daytrade/kirilim_geri_test.py:1-12", adalet=True)
r("A001", "8", "algo-sg elenen: 24 saatlik momentum patlamasi", "24 saatlik log getiri esigi asilinca trend yonunde momentum devami girisi (s5 ret24_min kolu).", "trend", "YOK",
  o="E_KODLANMADI_NEDENSIZ", nk="", nm="1L3A'da bu kuralin sinifi/karari yok (dis__pump-mumu-devam 1h/4h mum getirisi+fitil esikli: farkli kural); akibeti yalniz eski proje belgesinde (WR<%45, OOS zayif).",
  c="arsiv/algo-sg/algo/strategies.py:273-300 ; arsiv/algo-sg/STRATEJILER.md#Test edilip elenen fikirler", adalet=True)

# ---- A002 algo-sg/STRATEJILER_GUNLUK.md
r("A002", "1", "algo-sg D1 - Elder haftalik yon + Halsey %50 geri cekilme", "Haftalik Elder Impulse yonunde, 20 gunluk bacagin %50'sine inip ustunde kapanista giris; 3xATR20 stop, Turtle 10g cikis.", "trend", "BENZER", "dis__halsey-olculu-hareket",
  f="Eski: haftalik Elder Impulse (EMA13+MACD hist egimi) yon filtresi, 20 gunluk aralik orta noktasi, stop 3xATR20, kismi 0.6R, Turtle 10g cikis, 1d; 1L3A: ATR-zigzag bacagi %50 girisi, %61.8 ret, hedef %123, 15m, Elder filtresi yok",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede ana evren PF 1.58 ama stres IS 1.08 (rapor); kagit bota eklenmedi. 1L3A'da Elder Impulse sinifi yok.",
  c="arsiv/algo-sg/STRATEJILER_GUNLUK.md#D1 ; motor/strateji/dis/d12a_kitap.py:508-520 ; motor/strateji/dis/d11f_github.py:13", no="Elder Impulse 1L3A'da yalniz d11f notunda 'elder-guvenli-bolge-stop' KODLANMADI olarak geciyor.")
r("A002", "2", "algo-sg D2 - Elder 'kirmizi degil' + gunluk kapitulasyon donusu", "Elder haftalik kirmizi degilse, 2 gunde >=%20 dusen coinde ertesi acilis long; 3xATR20 stop, SMA5 ustu kapanis/15 gun cikis.", "MR", "BENZER", "onceki__kapitulasyon",
  f="Eski: gunluk TF, 2 gunde %20, haftalik Elder filtresi, SMA5 (Connors) cikisi, stop 3xATR20; 1L3A: esik/pencere ayarli ama Elder filtresi ve SMA5 cikisi yok, stop 4xATR(4H), zaman cikisi",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Ayni fikir B ile (rapor kendisi yaziyor); 1L3A onceki__kapitulasyon B'den; D2'nin gunluk/Elder/SMA5 formu ayri test edilmedi. Eski sonuc: ana WR %77 PF 4.14, stres PF 2.33.",
  c="arsiv/algo-sg/STRATEJILER_GUNLUK.md#D2 ; motor/strateji/onceki/kapitulasyon.py:1-30", adalet=True,
  no="D2 eski projede stres evreninde de PF>2 (en saglam sonuclardan); yalniz 143 islem (21/yil).")
r("A002", "3", "algo-sg elenen: Elder Uclu Ekran (haftalik yukari + gunluk RSI2 asiri satim)", "Haftalik yukari yonde gunluk RSI(2) asiri satimda long.", "MR", "BENZER", "swing__rsi-asiri-donus",
  f="Eski: haftalik Elder yon + gunluk RSI2 asiri satim; 1L3A: mod 'bolgede' RSI(2)<10 + trend_ma EMA filtresi, haftalik Elder yok",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede PF 1.2-1.3, OOS/IS zayif; 1L3A'da haftalik yon filtreli form test edilmedi.",
  c="arsiv/algo-sg/STRATEJILER_GUNLUK.md#3 ; motor/strateji/swing/rsi_asiri_donus.py:1-12", adalet=True)
r("A002", "4", "algo-sg elenen: Turtle 20g kirilim + haftalik Donchian(10) yonu", "20 gun kirilimi yalniz haftalik Donchian(10) yon durumu ayniysa.", "trend", "BENZER", "swing__donchian-kirilim",
  f="Eski: haftalik Donchian(10) yon filtresi; 1L3A: giris_n 20 / cikis_n 10, trend_ma opsiyonel, haftalik yon filtresi yok",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede IS PF 2.4-3.2, OOS ~1.0 (asiri uyum); 1L3A'da haftalik filtreli form test edilmedi.",
  c="arsiv/algo-sg/STRATEJILER_GUNLUK.md#3 ; motor/strateji/swing/donchian_kirilim.py:1-30", adalet=True)
r("A002", "5", "algo-sg elenen: Turtle 20g kirilim + Elder yonu", "20 gun kirilimi, yon filtresi haftalik Elder Impulse.", "trend", "BENZER", "swing__donchian-kirilim",
  f="Eski: Elder Impulse yon filtresi + kismi kar; 1L3A'da Elder filtresi yok",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede kismi karla PF 1.2-1.3; 1L3A'da test edilmedi.",
  c="arsiv/algo-sg/STRATEJILER_GUNLUK.md#3 ; motor/strateji/swing/donchian_kirilim.py:1-30", adalet=True)
r("A002", "6", "algo-sg elenen: Elder Impulse ilk gun girisi", "Haftalik Elder Impulse renk degisiminin ilk gununde yonde giris.", "trend", "YOK",
  o="E_KODLANMADI_NEDENSIZ", nm="1L3A'da Elder Impulse tabanli giris sinifi yok; akibeti yalniz eski proje belgesinde (OOS PF ~1.0-1.2, stres sonuclari birkac uc islemle sisiyor).",
  c="arsiv/algo-sg/STRATEJILER_GUNLUK.md#3", adalet=True, no="Kitap karti (Elder) G1 grubunda olabilir; lider tekillestirmede kontrol etsin.")
r("A002", "7", "algo-sg elenen: Halsey olculu hareket (kitap seviyeleri %61.8/%78.6/-%23.6)", "Halsey kitabindaki seviyelerle geri cekilme girisi; stop %78.6, hedef tepe ve -%23.6.", "trend", "BENZER", "dis__halsey-olculu-hareket",
  f="Eski: giris %61.8, stop %78.6, hedef tepe/-%23.6, 1d; 1L3A: giris %50, ret %61.8, hedef %123 uzatma, ATR-zigzag bacak, 15m",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede WR %52-54 PF ~1.15 (elendi); OZET §3 Fibonacci/olculu hareket maddesiyle ayni aile; 1L3A'da bu seviyeler test edilmedi.",
  c="arsiv/algo-sg/STRATEJILER_GUNLUK.md#3 ; motor/strateji/dis/d12a_kitap.py:508-520", adalet=True)

# ---- A003
r("A003", "1", "algo-sg A v2 - rejime bagli short", "A'nin short islemleri yalniz BTC gunluk kapanis < EMA200 iken; mevcut A'dan kotu bulundu.", "trend", "BENZER", "onceki__4s-kirilim",
  f="Eski: short yalniz BTC<EMA200; 1L3A: short ayni sembolun gunluk EMA200'une gore ayna filtre (short=True) ya da short=False ayari",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede A v2 OOS Sharpe 0.56 vs 1.04 (A mevcut): onerilmedi. 1L3A sinifi short filtresini kendi sembolune gore ayna uyguluyor, BTC rejimi degil.",
  c="arsiv/algo-sg/docs/A_V2_VE_KALDIRAC.md#Gorev 1 ; motor/strateji/onceki/kirilim_4s.py:19-24", adalet=False, no="'A yalniz long' = short=False ayari (ayri satir yapilmadi).")

# ---- A004 swing-sg
r("A004", "1", "swing-sg S1 - Trend geri cekilme (haftalik yon + EMA10 + RSI)", "Haftalik HA yesil + SMA20 ustu; gunluk EMA50 trend; EMA10'a geri cekilme + RSI<65; ertesi acilis; 1R'de yarisi, EMA50 alti cikis.", "trend", "KOD", "onceki__s1-geri-cekilme",
  c="motor/strateji/onceki/s1_geri_cekilme.py:1 ; arsiv/swing-sg/STRATEJILER.md#S1", no="DURUM karar 18: S1 alindi. Sapma: piyasa rejimi filtresi (sinif endeksi) kodlanmadi.")
r("A004", "2", "swing-sg S2 - Sikisma sonrasi kirilim", "Haftalik EMA10>30 + rejim; ATR(5)/ATR(50)<0.9; 20g Donchian kirilimi hacim>=ort, kapanis ust %40; 2xATR stop, 1.5R'de yarisi.", "trend", "KOD", "onceki__4s-kirilim",
  c="motor/strateji/onceki/kirilim_4s.py:1-18 ; arsiv/swing-sg/STRATEJILER.md#S2", no="Sinif docstring'i S2'yi A1 ile birlestirdigini yaziyor (DURUM karar 18). Sapma: haftalik EMA10/30 yon ve sinif rejim filtresi yok; sikisma/kapanis_konum/cikis_kanal parametreleri varsayilan KAPALI.")
r("A004", "3", "swing-sg S3 - Trend icinde asiri satim donusu (RSI2)", "Haftalik HA + SMA200 ustu; RSI(2)<10; ertesi gun limit emir kapanis-0.5ATR; SMA10 ustu/RSI2>70 cikis; 2xATR stop.", "MR", "BENZER", "swing__rsi-asiri-donus",
  f="Eski: limit emirle giris (kapanis-0.5xATR), haftalik HA + SMA200 filtre, cikis SMA10/RSI2>70, 10 gun; 1L3A: RSI(2)<10 'bolgede' modu giris mum kapanisi, trend_ma EMA, cikis RSI 50 kesisimi",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="DURUM karar 18 'S3 alinmadi' (OZET §2: ham kenar zayif R~+0.04); benzer aile 1L3A'da var, S3'un limit-giris formu ayri test edilmedi.",
  c="arsiv/swing-sg/STRATEJILER.md#S3 ; DURUM.md:100 ; motor/strateji/swing/rsi_asiri_donus.py:1-12 ; arsiv/OZET.md#2")

# ---- A005 Codex 1. liste (swing-sg/deneyler/CODEX_ADAYLAR.md tablo satir no)
KD = "stratejiler/v3_adaylar/ham/github-backtest-katalog-denetimli__tumu.csv"
r("A005", "1", "erhungn/volatility-regime-momentum", "ATR-normalize momentum + volatilite genislemesi filtresi, 10 gunluk tutus, 6 enstruman.", "trend", "TEKRAR", "P001:383",
  o="TEKRAR", nk="", c="arsiv/swing-sg/deneyler/CODEX_ADAYLAR.md#1 ; stratejiler/ek_kaynaklar/repo_kodlari.csv:383 (url=github.com/erhungn/volatility-regime-momentum)",
  no="Eski projede 'bizim' C1 testi: OOS PF 1.46, yillik %14.7, sisteme eklenince Sharpe 1.40->1.35; sisteme eklenmedi. Lider: tekillestirmede P001:383 akibeti bu satira da uygulanmali.")
r("A005", "2", "fridary/options-flow", "Opsiyon akisi tabanli dakikalik strateji.", "diger", "YOK", o="H_BIZIM_EVRENDE_UYGULANAMAZ", nk="opsiyon",
  nm="Eski projede RED: kod yok, opsiyon verisi + dakikalik, test kisminda 9 islem. Opsiyon verisi bizim evrende yok.", c="arsiv/swing-sg/deneyler/CODEX_ADAYLAR.md#2")
r("A005", "3", "koichi055/ema-gold-trader-ea", "EMA tabanli altin MT5 EA.", "trend", "TEKRAR", f"V014:149", o="TEKRAR", c=f"arsiv/swing-sg/deneyler/CODEX_ADAYLAR.md#3 ; {KD}:149",
  no="Eski projede RED (baslangic stopu yok, tek 2025 altin bogasi).")
r("A005", "4", "kunal14901/KA-MATS", "Coklu ajan kripto stratejisi; bizim C2 testinde trend geri cekilme olarak uyarlandi.", "trend", "TEKRAR", "V014:42", o="TEKRAR", c=f"arsiv/swing-sg/deneyler/CODEX_ADAYLAR.md#4 ; {KD}:42",
  no="Eski projede BELKI; 'bizim' C2 testi OOS PF 1.17, DD -%23, Sharpe 1.40->1.19 (eklenmedi). Ayni depo V014'te iki kez var (42 ve 552).")
r("A005", "5", "abailey81/Crypto-Statistical-Arbitrage", "Piyasa notr cift islemi / istatistiksel arbitraj, 32 borsa.", "MR", "TEKRAR", "V014:51", o="TEKRAR", c=f"arsiv/swing-sg/deneyler/CODEX_ADAYLAR.md#5 ; {KD}:51",
  no="Eski projede RED (acigasatis, veri yok, vadeli egri PF 28 inandirici degil).")
r("A005", "6", "jicheolha/crypto-trading-bot", "Bollinger sikisma kirilimi, kripto vadeli; bizim C3 testinde sikisma kirilimi olarak uyarlandi.", "trend", "TEKRAR", "V014:53", o="TEKRAR", c=f"arsiv/swing-sg/deneyler/CODEX_ADAYLAR.md#6 ; {KD}:53",
  no="Eski projede BELKI (sinyal kodu gizli, islemlerin %60'i short); C3 testi OOS 52 islem PF 0.55 (eklenmedi).")
r("A005", "7", "niranjan-kamal/ES_futures", "ES vadeli, 6.5x kaldirac, 43 islem; opsiyon verisi gerekli.", "diger", "YOK", o="H_BIZIM_EVRENDE_UYGULANAMAZ", nk="opsiyon",
  nm="Eski projede RED: 6.5x kaldirac, 43 islem, opsiyon verisi yok.", c="arsiv/swing-sg/deneyler/CODEX_ADAYLAR.md#7")
r("A005", "8", "lutfi-zain/quant-lttd-ichimoku", "Ichimoku bulut trend stratejisi; bizim C4 testinde 20/60/120 Ichimoku olarak uyarlandi.", "trend", "BENZER", "swing__ichimoku",
  f="Eski: Tenkan20/Kijun60/SenkouB120, bulut kaydirma 60 (C4); 1L3A: standart 9/26/52/26 (kijun_bulut / tk_bulut modlari), Chikou yok",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede BELKI (tek varlikta 10 islem, esikler asiri ayarli); C4 OOS PF 2.52 ama KO %41 <%45, sisteme eklenince Sharpe 1.40->0.66; eklenmedi.",
  c="arsiv/swing-sg/deneyler/CODEX_ADAYLAR.md#8 ; arsiv/swing-sg/deneyler/codex_adaylar.py:107-132 ; motor/strateji/swing/ichimoku.py:1-12", adalet=True,
  no="C4 OOS ort. +0.68R en yuksek beklentili aday idi; eski projede trend/ kollariyla ayni isleve sahip denip birakildi.")
r("A005", "9", "a1shmuk/xauusd-algo-trader", "XAUUSD swing dip/tepe stratejisi, 4374 ayar.", "diger", "YOK", o="D_KODLANMADI_NEDENLI", nk="lookahead",
  nm="Eski projede RED: swing dipleri sonraki mumlarla bulunuyor (gelecegi gorme) + 4374 ayar.", c="arsiv/swing-sg/deneyler/CODEX_ADAYLAR.md#9")
r("A005", "10", "jehumtine/markov-chain", "Markov zinciri BTC 4s/1s stratejisi.", "diger", "YOK", o="D_KODLANMADI_NEDENLI", nk="lookahead",
  nm="Eski projede RED: 4s kapanisi 1s mumuna erken sizmis (bfill) = gelecegi gorme.", c="arsiv/swing-sg/deneyler/CODEX_ADAYLAR.md#10")
r("A005", "11", "michael05josh-netizen/eurusd-london-bot", "EURUSD Londra seansi botu.", "diger", "YOK", o="D_KODLANMADI_NEDENLI", nk="pnl_hatasi",
  nm="Eski projede RED: sure dolumuyla kapanan islemler kar/zarardan atilmis (sonuc gecersiz); FX seans stratejisi.", c="arsiv/swing-sg/deneyler/CODEX_ADAYLAR.md#11")

# ---- A006 Codex 2. liste
r("A006", "1", "Javier-Garzo/ern-wo-options-backtester", "SPXW opsiyon satisi (ERN, WealthyOption), stopsuz.", "diger", "TEKRAR", "V014:755", o="TEKRAR", c=f"arsiv/swing-sg/deneyler/CODEX2_ADAYLAR.md#1 ; {KD}:755",
  no="Eski projede RED (cipak opsiyon satisi, stop yok, opsiyon verisi); 1L3A karari V014/V6'da.")
r("A006", "2", "Yugo25/ema-strategy-validation", "Elle isaretlenmis 5 dk doviz EMA islemleri.", "diger", "YOK", o="D_KODLANMADI_NEDENLI", nk="kural_belirsiz",
  nm="Eski projede RED: islemler elle isaretli, kodlanamaz, ileri donem testi yok.", c="arsiv/swing-sg/deneyler/CODEX2_ADAYLAR.md#2")
r("A006", "3", "logiccrafterdz/Argus - gizli bogа uyumsuzlugu (D3)", "Fiyatta daha yuksek dip + RSI'da daha dusuk dip (gizli bogа uyumsuzlugu), 3 mum teyitli dip, SMA200 ustu, 2ATR stop, 1.5R hedef.", "MR", "BENZER", "swing__rsi-diverjans",
  f="Eski: GIZLI uyumsuzluk (fiyat HL, RSI LL); 1L3A rsi-diverjans klasik (fiyat LL, RSI HL) diverjansi kodluyor, gizli yon yok",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede Argus RED (ortalanmis pivot=gelecegi gorme) ama ileri bakma duzeltilmis D3 testi tek basina zayif (+0.09R), sisteme eklenince OOS Sharpe 1.45->1.56: 'S4 adayi'; 1L3A'da gizli diverjans sinifi yok.",
  c="arsiv/swing-sg/deneyler/CODEX2_ADAYLAR.md#3,D3 ; arsiv/swing-sg/deneyler/codex2_adaylar.py:124-141 ; motor/strateji/swing/rsi_diverjans.py:1-16", adalet=True,
  no="Eski projede sisteme Sharpe katan TEK Codex adayi (S4 adayi, Aralik degerlendirmesi); kagit bot kapandigi icin hic degerlendirilmedi.")
r("A006", "4", "remy-rm511/nasdaq-quant-ml-research - QQQ ML (D1)", "11 fiyat ozelligi ile LightGBM 5 gun sonrasi yon tahmini, yillik ileri yurumeli egitim.", "diger", "YOK", o="G_ML", nk="ml",
  nm="Makine ogrenmesi modeli (LightGBM); eski projede de RED/zayif (OOS PF 0.99).", c="arsiv/swing-sg/deneyler/CODEX2_ADAYLAR.md#4,D1 ; arsiv/swing-sg/deneyler/codex2_adaylar.py:42-86")
r("A006", "5", "maxs231/lsob-backtest", "1 saatlik BTC, kaldiracli long/short, limit emir dolumu varsayimli.", "diger", "YOK", o="D_KODLANMADI_NEDENLI", nk="maliyet_negatif",
  nm="Eski projede RED: limit emir dolumuna bagimli, yuksek kaymada negatif.", c="arsiv/swing-sg/deneyler/CODEX2_ADAYLAR.md#5")
r("A006", "6", "MajidUppal/CSCI278 (S2) - bilesik 10 gosterge skoru (D2)", "10 gostergenin tanh ortalamasi, ADX<20 ise 0; skor>0.20 iki gun ust uste long.", "trend", "BENZER", "dis__gosterge-oy-toplami",
  f="Eski: 10 gostergenin z/tanh ortalamasi + ADX<20 susturma; 1L3A: 3 gosterge (RSI, CCI, SMA5/20) oy toplami -3..+3",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede RED/BELKI: bugunun kazananlariyla geriye test, OOS yok; D2 testi KO %29, DD -%46 (hedef disi).",
  c="arsiv/swing-sg/deneyler/CODEX2_ADAYLAR.md#6,D2 ; arsiv/swing-sg/deneyler/codex2_adaylar.py:87-123 ; motor/strateji/dis/d11g_github.py:190-196", adalet=True)

# ---- A007 brainbrick (trend/stratejiler.py docstring sirasi)
r("A007", "1", "brainbrick 037 - gunluk+haftalik SMA50 trend", "Gunluk kapanis > SMA50 ve haftalik kapanis > haftalik SMA50 ise long, degilse nakit.", "trend", "BENZER", "dis__sma200-ls",
  f="1L3A sinifi SMA200 (izgara 150-250), bant ayari, long/short; haftalik SMA50 ek filtresi ve SMA50 izgarada yok",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede BTC'de Sharpe 1.28/1.04 (al-tut benzeri, DD azaldi), ETH/BIST/S&P'de al-tut'u gecmedi; OZET §3 'tek kurali altin/endeks trendi' basarisiz maddesi.",
  c="arsiv/swing-sg/trend/stratejiler.py:7 ; arsiv/swing-sg/trend/OZET.md ; motor/strateji/dis/d3_kural.py:97-110", adalet=True)
r("A007", "2", "brainbrick 007 - 12 ay trend (gunluk+haftalik getiri>0)", "Gunluk 252g ve haftalik 52h getirisi pozitifse long (orijinaldeki 52 gun hatasi 252/365'e duzeltildi).", "trend", "BENZER", "dis__tsmom",
  f="Eski: iki kosul VE (252g gunluk + 52h haftalik getiri); 1L3A tsmom: 12 takvim ayi getirisi tek kosul, ATR stop, short ayari",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede BTC IS Sharpe 1.20 / ETH 1.11 (al-tut'u gecmedi); 1L3A dis__tsmom ayni fikir (12 ay), farki sadece cift kosul.",
  c="arsiv/swing-sg/trend/stratejiler.py:8,55-60 ; motor/strateji/dis/d5_ek.py:370-385", adalet=True)
r("A007", "3", "brainbrick 050 - volatilite hedefli maruziyet", "Maruziyet = min(1, hedef vol / 60 gun yillik vol), haftalik guncelleme.", "diger", "BENZER", "pf__v3-vol-yonetimli-long",
  f="Eski: 60 gunluk vol, haftalik guncelleme, hedef parametre; 1L3A: onceki tam ayin vol'u, aylik, hedef %20, tavan 1.0",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede vol hedefleme dususu azaltti ama getiriyi daha cok kesti (BTC %12 hedef cok dusuk).",
  c="arsiv/swing-sg/trend/stratejiler.py:9 ; arsiv/swing-sg/trend/OZET.md ; motor/portfoy/stratejiler/v3.py:340-349", adalet=True)
r("A007", "4", "brainbrick 001 - 12-1 momentum en iyi %10", "Aylik, 12-1 getiri siralamasinda en iyi %10 (en az 3) esit agirlik.", "trend", "BENZER", "pf__rotasyon",
  f="Eski: hisse/ETF evreni, en iyi %10; 1L3A rotasyon: skor 'getiri' lookback 365 atla 30 = 12-1, top-k (k sabit), evren 3-13 enstruman",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede ABD IS 0.95 / BIST'te OOS dagildi: bugunun kazananlarindan liste -> sisik (hayatta kalma yanliligi).",
  c="arsiv/swing-sg/trend/stratejiler.py:10,73-74 ; motor/portfoy/stratejiler/rotasyon.py:36-66", adalet=True)
r("A007", "5", "brainbrick 020 - artik (beta-arindirilmis) 12-1 momentum", "Beta arindirilmis kalinti getirinin ort/std'si ile en iyi %10.", "trend", "BENZER", "pf__kesit_ls",
  f="Eski: 36 aylik beta regresyonu, aylik; 1L3A kesit_ls skor 'artik': 90g kayan beta, referans BTC/evren ort., k sabit",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede ABD 0.6-0.95 IS, BIST OOS dagildi; seyrek evren.",
  c="arsiv/swing-sg/trend/stratejiler.py:11,77-88 ; motor/portfoy/stratejiler/kesit.py:19-40", adalet=True)
r("A007", "6", "brainbrick 007P - 12 aylik getirisi pozitif olan tumu", "12 aylik getirisi pozitif tum varliklar esit agirlik, ay sonu.", "trend", "BENZER", "pf__rotasyon",
  f="Eski: pozitif olan hepsi; 1L3A rotasyon mutlak=True + k=evren buyuklugu ile elde edilebilir (varsayilan top-k); trend_sepet SMA tabanli",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede ABD trend portfoyu + rejim IS 1.10/OOS 1.53, DD -%13/-%8: eski projenin SECILEN trend kolu (kagit hesap 2); 1L3A'da ayni kural test edilmedi.",
  c="arsiv/swing-sg/trend/stratejiler.py:12,91-92 ; arsiv/swing-sg/trend/OZET.md#Secilen trend kollari ; motor/portfoy/stratejiler/rotasyon.py:36-66", adalet=True,
  no="Eski projede kagit hesaba alinan 3 trend kolundan biri (BTC trend, ABD trend portfoyu, emtia ETF dusuk vol).")
r("A007", "7", "brainbrick 012 - 252 gun en dusuk volatilite %10", "252 gunluk volatilitesi en dusuk %10 esit agirlik, aylik (emtia ETF'lerinde secildi).", "diger", "BENZER", "pf__rotasyon",
  f="Eski: en dusuk vol %10 / ETF %20; 1L3A rotasyon skor 'dusuk_vol' (-std, lookback ayarli), top-k, evren Binance TradFi",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede emtia ETF dusuk vol IS 0.94/OOS 1.23 (secildi); BIST'te OOS cokuyor.",
  c="arsiv/swing-sg/trend/stratejiler.py:13,95-96 ; arsiv/swing-sg/trend/OZET.md ; motor/portfoy/stratejiler/rotasyon.py:36-66", adalet=True)
r("A007", "8", "brainbrick 089 - emtia degeri (5 yil once fiyat / bugun)", "5 yil onceki fiyat / bugunku fiyat orani en yuksek ucte biri long (emtia degeri).", "diger", "YOK", o="E_KODLANMADI_NEDENSIZ",
  nm="1L3A'da emtia deger (5 yillik ters getiri) kurali yok; evrende 3 emtia var; akibeti yalniz eski proje sonuc tablolarinda (Sharpe 0.85-1.15, test edildi, secilmedi).",
  c="arsiv/swing-sg/trend/stratejiler.py:14,99-100 ; arsiv/swing-sg/trend/SONUCLAR_TREND.md:111", adalet=True)

# ---- A008 strateji-sg RAPOR.md
r("A008", "1", "strateji-sg SAKK - Seans acilis kutusu kirilimi (5 dk)", "Seansin ilk 1 saatlik dar kutusu (<=0.35 ATR), 1s EMA21/50 yonunde kutu kirilimi, 1.5R hedef, seans sonu cikis.", "trend", "BENZER", "daytrade__orb",
  f="Eski: kutu <=0.35xGunluk ATR daralma filtresi, 1s EMA21>50 trend, %20 kutu tamponu, 60 dk giris penceresi, 1.5R, 5dk; 1L3A orb: aralik_dk, tampon_atr, ust_yari_filtre, gunde_tek, daralma/trend filtresi yok",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede BTC 61 islem/6.7 yil PF 1.44, SPX PF 1.62 (CFD); XAU OOS'ta kayip; orb sinifi aile kaydinda negatif kanit (Bulkowski) not ediyor. DURUM: 5dk maliyet baskin.",
  c="arsiv/strateji-sg/RAPOR.md#3 ; arsiv/ANALIZ_strateji-sg.md#4.8 ; motor/strateji/daytrade/orb.py:1-25", adalet=True)
r("A008", "2", "strateji-sg GPK - Gunluk pivot/CPR kirilimi (1s day trade)", "Dar CPR + gunluk EMA10/20 trend; 1s kapanis R1'i yukari keser -> long; 2R hedef, gun sonu cikis.", "trend", "BENZER", "onceki__kgt-gun",
  f="Eski GPK: 2R hedef + gun sonu cikisi, BTC/SPX/UKOIL/XAU; 1L3A kgt-gun: KGT kurali + 4S EMA21/50 trend donusu cikisi + gun sonu flat, kismi kar",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="GPK KGT'nin atasi; BTC PF 1.19, XAU 0.99, komsu ayarlarin ~%48'i karli. 1L3A KGT'yi (v3) kodladi, GPK'nin 2R-hedef formu ayri test edilmedi.",
  c="arsiv/strateji-sg/RAPOR.md#4 ; arsiv/ANALIZ_strateji-sg.md#4.1 ; motor/strateji/onceki/kgt.py:1-30,146-151", adalet=True)
r("A008", "3", "strateji-sg Faz1 ortak payda A - trend + EMA bolgesine geri cekilme (5dk)", "Trend yonunde 5 dk EMA bolgesine geri cekilme girisi; kosullu ileri getiri avantaji <=0.15 ATR.", "trend", "BENZER", "scalp__ma-geri-cekilme",
  f="Eski: 5dk EMA bolgesi, kosullu getiri olcumu + backtest; 1L3A scalp ma-geri-cekilme 15m sinifi (MA'ya dokunus + sicrama mumu)",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="OZET.md §3: 5 dk geri cekilme eski projede basarisiz (avantaj<masraf); 1L3A DURUM'da BTC 5m EMA 9/21 ayni sonuc (komisyon).",
  c="arsiv/strateji-sg/RAPOR.md#1-2 ; arsiv/OZET.md#3 ; arsiv/ANALIZ_strateji-sg.md#7c", adalet=False)
r("A008", "4", "strateji-sg Faz1 ortak payda B - ust TF trend + BB/RSI/VWAP donusu", "Ust TF trend yonunde BB/RSI/VWAP asiri uzaklasma donusu (5dk).", "MR", "BENZER", "scalp__bant-donus",
  f="Eski: BB/RSI/VWAP birlesimi, ust TF trend; 1L3A scalp bant-donus: bant disi ice donus, ADX filtresi, VWAP yok",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="OZET.md §3: 5dk donus eski projede basarisiz; 1L3A'da VWAP+BB+RSI birlesik form test edilmedi.",
  c="arsiv/strateji-sg/RAPOR.md#1-2 ; arsiv/OZET.md#3", adalet=True)

# ---- A009 RAPOR_KRIPTO
r("A009", "1", "strateji-sg KGT v1-v3 - Kripto gunluk pivot kirilimi + trend takibi", "Dar CPR + gunluk EMA10>20, 1s kapanis R1 kirar -> long; 1R'de %15 kismi, 4S EMA21<50 cikis.", "trend", "KOD", "onceki__kgt",
  c="motor/strateji/onceki/kgt.py:1 ; arsiv/strateji-sg/RAPOR_KRIPTO.md#1", no="DURUM karar 18: KGT alindi. onceki__kgt-gun ayni kuralin gun-sonu varyanti (karar 21). Portfoy kisitlari BAGLANAMAYAN'da (baglama.py:175).")
r("A009", "2", "strateji-sg elenen: 1G+4S yon + 1S RSI dip geri cekilme (Cift RSI)", "1G/4S yon yonunde 1S RSI dip toparlanmasi.", "MR", "BENZER", "daytrade__rsi-asiri-donus",
  f="Eski: 1G+4S yon, 1S RSI dip/toparlanma, 15-20 coin portfoy; 1L3A: 1h RSI geri cikis, trend_ma EMA filtresi, gun sonu kapanis, tek sembol",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="OZET.md §3 '1S RSI/BB geri cekilme (PF<1)' ve 'Cift RSI geri cekilme OOS PF~0.95' eslemesi; 1L3A'da cok TF yon filtreli form test edilmedi.",
  c="arsiv/strateji-sg/RAPOR_KRIPTO.md#4 ; arsiv/ANALIZ_strateji-sg.md#7c ; motor/strateji/swing/rsi_asiri_donus.py:1-12", adalet=True)
r("A009", "3", "strateji-sg elenen: 1G+4S yon + 1S Donchian kirilimi", "Ust TF yonunde 1S Donchian kirilimi (51 Str. 3.6).", "trend", "BENZER", "daytrade__donchian-kirilim",
  f="Eski: 1G+4S yon filtresi, 15-20 coin portfoy; 1L3A: 1h SMA50 trend_ma, tek sembol",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="OZET.md §3 '1S Donchian' basarisiz (OOS PF ~1.0, DD %60-90); 1L3A'da test edilmedi.",
  c="arsiv/strateji-sg/RAPOR_KRIPTO.md#4 ; arsiv/OZET.md#3 ; motor/strateji/daytrade/donchian_kirilim.py:1-15", adalet=True)

# ---- A010 RAPOR_PA (Galen Woods kurulumlari)
WP = "arsiv/strateji-sg/RAPOR_PA.md#5"
r("A010", "1", "strateji-sg SKA/CBF - Sikisma (Tikaniklik) Kirilim Arizasi (4S)", "4S EMA21>50 yonunde 4 ic mum tikanikligi, sahte kirilim mumu, yukselis kurulum mumu; bekleyen stop emri.", "diger", "BENZER", "daytrade__sahte-kirilim",
  f="Eski: 4S, >=4 ardisik ic mum, sahte kirilim mumu + kurulum mumu tepesinde bekleyen emir, 1R'de 1/4 kismi; 1L3A: Donchian araligi ATR genislik bandi, 1-3 mumda geri donus onay mumu, 1h gun sonu",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede tum donem PF 3.18 ama mum hizalamasi 1-3 saat kayinca OOS PF 0.78, WF Sharpe 0.36 -> birakildi; 1L3A sinifi ayni Woods kartindan farkli tanimla.",
  c="arsiv/strateji-sg/RAPOR_PA.md#8-9 ; motor/strateji/daytrade/sahte_kirilim.py:1-12", adalet=True,
  no="Hizalama testi (4 saat kaydirma) 1L3A motorunda uygulanmadi: tek hizalamada guclu gorunuyor olabilir.")
r("A010", "2", "strateji-sg elenen PA: Trend Cubugu Arizasi (TBF)", "Woods trend cubugu arizasi geri cekilme kurulumu (4S/1S).", "trend", "BENZER", "swing__geri-cekilme-fiyat-eylemi",
  f="Eski: 4S bekleyen emirle giris; 1L3A geri-cekilme-fiyat-eylemi: ADX+EMA guclu trend, zayif geri cekilme olcutleri",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede 4S medyan PF 0.80; OZET §3 'Brooks H1/H2 / fiyat eylemi' maddesi.", c=f"{WP} ; motor/strateji/daytrade/geri_cekilme_fiyat_eylemi.py:11", adalet=True)
r("A010", "3", "strateji-sg elenen PA: Yavaslama (DEC)", "Ardisik dipler dusup adimlar azalinca long (Woods Yavaslama).", "MR", "BENZER", "swing__ardisik-bar-tukenme",
  f="Eski: 4S bekleyen emir; 1L3A ardisik-bar-tukenme desen='yavaslama' (4h/1d)",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede 4S PF 0.83; 1L3A'da kural ayni karttan ama bu TF/portfoyde test edilmedi.", c=f"{WP} ; motor/strateji/swing/ardisik_bar_tukenme.py:1-8", adalet=True)
r("A010", "4", "strateji-sg elenen PA: Dorua Karsi (ANT)", "Adimlar artan ardisik dipler (doruk) ters yone giris (Woods).", "MR", "BENZER", "swing__ardisik-bar-tukenme",
  f="Eski: 4S bekleyen emir; 1L3A desen='doruk'", o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede 4S PF 0.83; 1L3A'da test edilmedi.", c=f"{WP} ; motor/strateji/swing/ardisik_bar_tukenme.py:1-8", adalet=True)
r("A010", "5", "strateji-sg elenen PA: Basinc Bolgesi (PZ)", "Woods basinc bolgesi kirilimi.", "trend", "BENZER", "daytrade__konsolidasyon-kirilim",
  f="Eski: 4S bekleyen emir; 1L3A konsolidasyon-kirilim karti 'basinc-bolgesi__woods' (dar kutu + hacim)", o="D_KODLANMADI_NEDENLI", nk="benzer_var",
  nm="Eski projede 4S PF 0.81; 1L3A'da bu TF'de test edilmedi.", c=f"{WP} ; motor/strateji/daytrade/konsolidasyon_kirilim.py:9", adalet=True)
r("A010", "6", "strateji-sg elenen PA: Zayif Geri Cekilme (WPB)", "Guclu trendde zayif (az mumlu) geri cekilmeden sonra giris (Woods).", "trend", "BENZER", "swing__geri-cekilme-fiyat-eylemi",
  f="Eski: 4S; 1L3A: ADX+EMA guclu trend, geri_maks karsi mum olcutu", o="D_KODLANMADI_NEDENLI", nk="benzer_var",
  nm="Eski projede egitim PF 2.4 test 0.5 (4S medyan 0.86).", c=f"{WP} ; motor/strateji/swing/geri_cekilme_fiyat_eylemi.py:12", adalet=True)
r("A010", "7", "strateji-sg elenen PA: Pin bar (51 Str. 7.3)", "Pin bar donus mumu girisi (4S).", "diger", "BENZER", "swing__pin-bar",
  f="Eski: 4S bekleyen emirle; 1L3A pin-bar sinifi (hedef sinifin kuralini lider kontrol etsin: ben acmadim)", o="D_KODLANMADI_NEDENLI", nk="benzer_var",
  nm="Eski projede 4S medyan PF 0.82; OZET §3 PA kurulumlari/'EPA-A mum' maddesi.", c=f"{WP} ; arsiv/OZET.md#3", adalet=True,
  no="swing__pin-bar sinifi kodu bu ajan tarafindan ACILMADI (fark metni kayit adi + eski proje belgesine dayali): dogrulanmamis.")

# ---- A011 EPA
r("A011", "1", "strateji-sg EPA-A - EMA 8/21/55 pullback + mum + S/D + trend cizgisi", "4S EMA8>21>55, EMA8'e geri cekilme, mum kalitesi/konum sartlari, sinyal mumu tepesinde bekleyen emir.", "trend", "BENZER", "swing__ma-geri-cekilme",
  f="Eski: 4S, EMA 8/21/55 dizilimi, bilesen ac/kapa izgarasi (540 ayar), kismi %15-25; 1L3A ma-geri-cekilme: 10/20/50 MA'ya dokunus + sicrama mumu (docstring daytrade turevinden: sinifin kendisi acilmadi)",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede basarisiz (OOS Sharpe 0.42; hammer/engulfing katkisiz, trend cizgisi zararli). OZET §3 mum/trend cizgisi maddeleri.",
  c="arsiv/strateji-sg/RAPOR_EPA.md#Kural setleri ; arsiv/ANALIZ_strateji-sg.md#4.4 ; motor/strateji/daytrade/ma_geri_cekilme.py:1-12", adalet=True,
  no="Kullanicinin kendi fikri. swing__ma-geri-cekilme dosyasi dogrudan acilmadi; daytrade turevinin docstring'i okundu.")
r("A011", "2", "strateji-sg EPA-B - EMA 8/21/55 baglami + 4S sikisma kirilimi + hacim", "1G EMA8>21>55; 4S 18 mum <7 ATR sikisma; kirilim mumu hacim>=2x; EMA8<21 cikis; 1R'de %15 kismi.", "trend", "BENZER", "swing__konsolidasyon-kirilim",
  f="Eski: 1G EMA 8/21/55 baglam + 4S sikisma + hacim 2x + EMA8<21 cikis; 1L3A: dar kutu (maks_genislik_atr), hacim_k, opsiyonel trend EMA, hedef olculu hareket, cikis stop/hedef",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede basarili ama yedek (WR %48.9 PF 2.03 Sharpe 1.31, OOS 0.96, KGT ile kor 0.77); 1L3A'da 1G baglam+4S sikisma formu test edilmedi.",
  c="arsiv/strateji-sg/RAPOR_EPA.md#Sonuc 2 ; arsiv/ANALIZ_strateji-sg.md#7b ; motor/strateji/swing/konsolidasyon_kirilim.py:1-25", adalet=False,
  no="DURUM karar 18'de EPA-B anilmiyor ('yedek' sinifinda degil): alinmayan, sonucu iyi eski aday.")

# ---- A012 RAPOR_S2
r("A012", "1", "strateji-sg KMN - kesitsel momentum, piyasa notr", "30 coin 14 gunluk risk ayarli getiri siralamasi, 5 long/5 short, ters-vol agirlik, 14 gunde bir dengeleme.", "trend", "KOD", "pf__kesit_ls",
  c="motor/portfoy/stratejiler/baglama.py:57 ; motor/portfoy/stratejiler/kesit.py:19-24 ; arsiv/strateji-sg/RAPOR_S2.md#Secilen ayar KMN", no="portfoy_adaylari.csv satir 17 (D002:17) ile ayni strateji; evren 30 -> 13 enstruman sapmasi baglama notunda.")
r("A012", "2", "strateji-sg elenen: 4S/1G Bollinger + RSI(2) ortalamaya donus", "Rejim filtreli BB/RSI(2) asiri uzaklasma, ADX aralik filtresi, onay mumu, ortalamaya cikis (256 kombinasyon 4S + 256 gunluk).", "MR", "BENZER", "swing__bant-donus",
  f="Eski: 4S/1G, ADX aralik filtresi, onay mumu, gunluk trend ici, 15-20 coin; 1L3A bant-donus: ADX<25, rsi_esik opsiyonel, trend_ma, tek sembol",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="OZET.md §3 'Ortalamaya donus 4S/1G' basarisiz (medyan Sharpe -1.10 / -0.31); 1L3A'da ayni aile var ama eski kombinasyonlar test edilmedi.",
  c="arsiv/strateji-sg/RAPOR_S2.md#1 ; arsiv/OZET.md#3 ; motor/strateji/swing/bant_donus.py:1-25", adalet=True, no="Gunluk ayni kural (256 kombinasyon) ayni satirda sayildi.")
r("A012", "3", "strateji-sg elenen: kesitsel kisa vadeli donus (gecen haftanin kaybedeni)", "Gecen haftanin en cok dusenini al (kesitsel).", "MR", "BENZER", "pf__kesit_ls",
  f="Eski: haftalik donus, 15-20 coin; 1L3A kesit_ls skor 'donus' (long -getiri, short +getiri), lookback ayarli, evren 3-13",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede medyan Sharpe -0.99 (16 kombinasyon); 1L3A'da kisa vadeli donus skoru var ama bu kural test edilmedi.",
  c="arsiv/strateji-sg/RAPOR_S2.md#1 ; motor/portfoy/stratejiler/kesit.py:36-38", adalet=True)
r("A012", "4", "strateji-sg elenen: IBS donusu (gunluk, 151 §4.4)", "Dusuk IBS al / yuksek IBS sat, gunluk.", "MR", "BENZER", "pf__ibs_donus",
  f="Eski: tek kombinasyon, Sharpe -2.07 (yillik -%49); 1L3A pf__ibs_donus kesitsel IBS donusu (kesit_ls ibs modu)",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede basarisiz (OZET §3 IBS); ayni kural Kakushadze 151 §4.4 kaynaginda da var (G5 kapsami) - tekrar olabilir.",
  c="arsiv/strateji-sg/RAPOR_S2.md#1 ; arsiv/ANALIZ_strateji-sg.md#7c ; motor/portfoy/stratejiler/kesit.py:48-50", adalet=True,
  no="pf__ibs_donus sinifi dosyasi ayrica acilmadi; kesit_ls docstring'indeki 'ibs' skoru okundu. G5 satiri (kakushadze_151.csv §4.4) ile TEKRAR kontrolu lider'de.")

# ---- A013 HGT
r("A013", "1", "strateji-sg HGT - haftalik yon / gunluk islem (20 Str. #5)", "Haftalik EMA3>5>15>45 dizilimi + MACD hist>0; gunluk EMA dizilimi tetik; stop 5 gun dibi 1-3 ATR; cikis dizilim bozulmasi.", "trend", "BENZER", "dis__ma-mukemmel-siralama",
  f="Eski: haftalik yon (EMA 3/5/15/45 + MACD) + gunluk tetik, 52 varyant, 6-20 coin portfoy; 1L3A: tek TF SMA10>20>50>100>200 dizilimi + ADX, stop ilk olusum gunu dibi",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Eski projede basarisiz: IS Sharpe 1.39 (2020-21 bogasi), OOS <=0.25, rastgele girisle ayni; OZET §3 'Haftalik yon/gunluk islem (HGT)'.",
  c="arsiv/strateji-sg/RAPOR_HGT.md ; arsiv/OZET.md#3 ; motor/strateji/dis/d10a_kitap.py:285-290", adalet=True,
  no="1L3A'da haftalik yon+gunluk tetik formu icin en yakin sinif secildi; ust_tf=1w secenekleri ayrica test edilmedi. Kaynak 20 Trading Stratejisi Sistem #5 (G1 kitap kartlari).")

# ---- A014 day-trade-sg (repo_kodlari.csv daytrade_py: satir 50..63)
DT = [("S1_pullback", "Trend geri cekilme (Lien, Backus, Wallace)", 50, "trend"), ("S2_momentum", "20-100 momentum", 51, "trend"),
      ("S3_orb", "Acilis araligi kirilimi + pivot", 52, "trend"), ("S4_band", "Bollinger(20,2)+Stokastik donusu", 53, "MR"),
      ("S5_pdhl", "Onceki gun tepe/dip kirilimi", 54, "trend"), ("S6_fader", "Sahte kirilim / Fader", 55, "MR"),
      ("S7_vwap", "VWAP geri alma", 56, "MR"), ("S8_camarilla", "Camarilla L3/H3 donusu", 57, "MR"),
      ("S9_session", "Seans araligi kirilimi", 58, "trend"), ("S10_trendday", "Gec seans gun ici momentum (S11 = at_utc=14 ayari)", 59, "trend"),
      ("S12_strongclose", "Guclu kapanis devami", 60, "trend"), ("S13_falsebreak", "Lien yanlis kirilmalari filtreleme", 61, "MR"),
      ("S14_mac", "Bernstein MA kanali + momentum", 62, "trend"), ("S15_tdpullback", "Trend gununde EMA20/VWAP geri cekilmesi", 63, "trend")]
for i, (kid, ad, prow, aile) in enumerate(DT, 1):
    r("A014", str(i), f"day-trade-sg {kid} - {ad}", "day-trade-sg strategies.py fonksiyonu; mantik repo_kodlari.csv satirinda ozetli.", aile, "TEKRAR", f"P001:{prow}", o="TEKRAR",
      c=f"arsiv/day-trade-sg/daytrade/strategies.py (STRATEGIES) ; stratejiler/ek_kaynaklar/repo_kodlari.csv:{prow}",
      no="Ayni kod G3'te repo_kodlari (daytrade_py) olarak ham satir. S3/S9 ortak ORB hedefi; S11 ayri satir yapilmadi (S10 ayari)." if kid in ("S3_orb", "S10_trendday") else "Ayni kod G3'te repo_kodlari (daytrade_py) olarak ham satir.")

# ---- A015 scalp-sg (repo_kodlari.csv scalp_py: satir 64..66)
for i, (kid, ad, prow, aile) in enumerate([("s1_pullback", "H1 EMA8/34 yon + M5 EMA21 + Stokastik trend geri cekilme", 64, "trend"),
                                          ("s2_meanrev", "Trend yonlu ortalamaya donus (BB + RSI5)", 65, "MR"),
                                          ("s3_breakout", "Sikisma kirilimi (Volman blok + H1 mum uyumu)", 66, "trend")], 1):
    r("A015", str(i), f"scalp-sg {kid} - {ad}", "scalp-sg src/strategies.py fonksiyonu; Pine betigi tradingview/ altinda.", aile, "TEKRAR", f"P001:{prow}", o="TEKRAR",
      c=f"arsiv/scalp-sg/src/strategies.py ; stratejiler/ek_kaynaklar/repo_kodlari.csv:{prow}", no="Ayni kod G3'te repo_kodlari (scalp_py). scalp-sg DURUM.md: veri indirilemedi, backtest sonucu YOK.")

# ---- A016/A017 codex-algo (repo_kodlari.csv codex_py: satir 1..17)
CX1 = ["compression_breakout", "channel_reversion", "supertrend_regime", "fractal_breakout", "macd_sma200", "ao_ac_zones", "kst_momentum", "triple_cci_mfi", "double_cci_hma"]
CX2 = ["wd_breakout", "wd_pullback", "wd_reversion", "wd_momentum", "d4h_pullback", "d4h_breakout", "d4h_reversion", "d4h_supertrend"]
for i, kid in enumerate(CX1, 1):
    r("A016", str(i), f"codex-algo {kid}", "Codex Algo kural fonksiyonu (strategies.py); mantik repo_kodlari.csv satirinda.", "trend" if kid not in ("channel_reversion", "double_cci_hma") else "MR", "TEKRAR", f"P001:{i}", o="TEKRAR",
      c=f"arsiv/codex-algo/src/codex_algo/strategies.py ; stratejiler/ek_kaynaklar/repo_kodlari.csv:{i}", no="Ayni kod G3'te repo_kodlari (codex_py).")
for j, kid in enumerate(CX2, 1):
    r("A017", str(j), f"codex-algo {kid}", "Codex Algo MTF kural fonksiyonu (mtf_strategies.py); mantik repo_kodlari.csv satirinda.", "MR" if kid.endswith("reversion") else "trend", "TEKRAR", f"P001:{9 + j}", o="TEKRAR",
      c=f"arsiv/codex-algo/src/codex_algo/mtf_strategies.py ; stratejiler/ek_kaynaklar/repo_kodlari.csv:{9 + j}", no="Ayni kod G3'te repo_kodlari (codex_py)." + (" wd_pullback = swing-sg S1 ayni fikir (repo_kodlari notu: onceki__s1-geri-cekilme)." if kid == "wd_pullback" else ""))

# ---- A911 / A912 haiku strateji arastirma dali testleri
r("A911", "1", "Haiku test: TrendRider ozu (SMA50, BTC/ETH 1d)", "Gunluk kapanis SMA50 ustundeyse long, altinda nakit; BTC/ETH tek sembol basit simulasyon.", "trend", "TEKRAR", "Q004:3", o="TEKRAR",
  c="dal:claude/haiku-strateji-arastirma:stratejiler/ek_kaynaklar/test/SONUC_2026-11.md ; stratejiler/ek_kaynaklar/son1ay_2026-11.csv:3",
  no="G5 son1ay satir 3 (TrendRider) ile ayni strateji; Haiku testi: BTC 14.5x (al-tut 14.2x), en iyi %5 cikinca 1.96x = basarisiz. DURUM: TrendRider karar 24'ten kaldi.")
r("A911", "2", "Haiku test: Leah E015 (BTC gunluk EMA30/90)", "BTC gunluk EMA30/EMA90 kesisim trendi.", "trend", "TEKRAR", "Q004:5", o="TEKRAR",
  c="dal:claude/haiku-strateji-arastirma:stratejiler/ek_kaynaklar/test/SONUC_2026-11.md ; stratejiler/ek_kaynaklar/son1ay_2026-11.csv:5",
  no="G5 son1ay satir 5 ile ayni; Haiku testi: BTC/ETH islem sayisi <50, al-tut'un gerisinde.")
r("A911", "3", "Haiku test: ETH 4s kirilim (delta-paper-bot)", "ETH 4s kanal kirilimi trend botu.", "trend", "TEKRAR", "Q004:1", o="TEKRAR",
  c="dal:claude/haiku-strateji-arastirma:stratejiler/ek_kaynaklar/test/SONUC_2026-11.md ; stratejiler/ek_kaynaklar/son1ay_2026-11.csv:1",
  no="G5 son1ay satir 1 ile ayni; Haiku testi: PF 1.25, en iyi %5 cikinca kalan PF 0.69 = basarisiz. E014 (Leah makro, son1ay satir 4) bu test dosyalarinda YOK.")
r("A912", "1", "Haiku test: GTAA 10 aylik SMA (SPY/EFA/IEF/VNQ/DBC)", "5 ETF, her biri fiyat > 10 aylik SMA ise 1/5 pay, degilse nakit (SHY).", "trend", "BENZER", "pf__trend_sepet",
  f="Eski: ay sonu 10 aylik SMA, 5 ETF, nakit SHY; 1L3A trend_sepet: sma_gun=300 takvim gunu, nakitli=True, evren Binance TradFi/kripto (SPY/EFA/IEF/VNQ/DBC yok)",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="DURUM 2026-11-07: GTAA paper'a ALINMADI (varliklar Binance TradFi'de yok, SPY'a ustunluk bootstrap'ta kanitsiz); yeniden degerlendirme sarti Binance vekilleriyle karar 24 + >=6 ay paper. Sinif Faber GTAA'dan kodlu.",
  c="dal:claude/haiku-strateji-arastirma:stratejiler/ek_kaynaklar/test/PORTFOY_SONUC_2026-11.md ; DURUM.md:349 ; motor/portfoy/stratejiler/rotasyon.py:286-296 ; motor/portfoy/stratejiler/baglama.py:26-27", adalet=False,
  no="ek_77_strateji.md 'Varlik dagilimi paketi (Faber GTAA)' (portfoy_adaylari ek77 satir 26) ile ayni kural: P003:26 ile TEKRAR olabilir. Haiku sonuclari: Sharpe 0.86 (SPY 0.77), DD -%11, komsu SMA 6/8/10/12 hepsi SPY'i gecti, bootstrap fark [-0.33,+0.47] anlamsiz. GTAA 20 varlik varyanti ayri satir yapilmadi.")
r("A912", "2", "Haiku test: momentum varlik dagilimi (12 ay, ilk 3/8 varlik)", "8 varliktan 12 aylik getirisi en iyi 3'e esit agirlik, aylik.", "trend", "BENZER", "pf__rotasyon",
  f="Eski: 8 ETF (SPY,EFA,EEM,IEF,TLT,DBC,GLD,VNQ), nakit getirisi sifir/SHY; 1L3A baglama satir 5: FABER5 (BTC,MSFT,XAU,WTI,COPPER) lookback 365, k=3, aylik",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Kural 1L3A'da kodlu (rotasyon, Faber/Quantpedia varlik sinifi momentumu) ama ETF evreni farkli; Haiku derin testte DD -%23 > %20 kapisi: karar 24'u gecmedi.",
  c="dal:claude/haiku-strateji-arastirma:stratejiler/ek_kaynaklar/test/PORTFOY_SONUC_2026-11.md ; dal:...:PORTFOY_DERIN_2026-11.md ; motor/portfoy/stratejiler/baglama.py:44-47", adalet=False,
  no="MASTER_katalog 'asset class momentum rotational system' (V001:5) ile TEKRAR olabilir.")
r("A912", "3", "Haiku test: sektor momentum (9 sektor ETF, ilk 3)", "9 sektor ETF'inden 12 aylik getirisi en iyi 3'e esit agirlik, aylik.", "trend", "BENZER", "pf__rotasyon",
  f="Eski: ABD sektor ETF'leri; 1L3A evreninde sektor ETF yok, rotasyon sinifi ayni kuralla (k=3, lookback 365) hisse/sepet evreninde calisir",
  o="D_KODLANMADI_NEDENLI", nk="benzer_var", nm="Haiku testi: Sharpe 0.70 (SPY 0.77), DD -%39: SPY'i risk ayarli gecmiyor; evren (sektor ETF) Binance'te yok.",
  c="dal:claude/haiku-strateji-arastirma:stratejiler/ek_kaynaklar/test/PORTFOY_SONUC_2026-11.md ; motor/portfoy/stratejiler/rotasyon.py:36-66", adalet=False,
  no="MASTER_katalog 'sector momentum rotational system' (V001:64) ile TEKRAR olabilir.")


# ------------------------------------------------------------------ uretim
def ham_uret():
    sayac = collections.Counter()
    satirlar = []
    for s in S:
        e, o = s["e"], s["o"]
        if e in ("KOD", "AYAR", "ESDEGER") and not o:
            o = "KOD"
        sayac[s["k"]] += 1
        not_ = s["no"]
        if s["adalet"]:
            not_ = ("ADALET: eski projede elenmis/olumsuz sonuclu, 1L3A'da bu form dogrudan test edilmedi. " + not_).strip()
        satirlar.append({
            "ham_id": f"{s['k']}:{s['n']}", "kaynak_id": s["k"], "kaynak_satir_no": s["n"], "kaynaktaki_ad": s["ad"][:120], "kisa_mantik": s["m"][:160],
            "aile": s["a"], "eslesme": e, "hedef": s["h"], "ayar_id": "", "ayar_dosyasi": "", "fark": s["f"] if e in ("BENZER", "ESDEGER") else "",
            "on_durum": o, "neden_kodu": s["nk"] if e not in ("KOD", "TEKRAR") else "", "neden_metni": s["nm"], "kanit": s["c"], "not": not_})
    return satirlar


def kontrol(satirlar):
    kod = {x["ad"] for x in csv.DictReader(open(ARA / "kod_kaydi.csv", encoding="utf-8"))}
    uyari = []
    for x in satirlar:
        if x["eslesme"] in ("KOD", "ESDEGER", "BENZER") and x["hedef"] not in kod:
            uyari.append(f"{x['ham_id']}: hedef sinif kod_kaydi.csv'de yok: {x['hedef']}")
        if x["eslesme"] == "TEKRAR" and ":" not in x["hedef"]:
            uyari.append(f"{x['ham_id']}: TEKRAR hedefi ham_id degil")
        if len(x["ad_k"] if "ad_k" in x else x["kaynaktaki_ad"]) > 120:
            uyari.append(f"{x['ham_id']}: ad > 120")
    # TEKRAR hedef dogrulama (kaynak CSV'de satir var mi, ad uyumu)
    rk = list(csv.DictReader(open(KOK / "stratejiler/ek_kaynaklar/repo_kodlari.csv", encoding="utf-8")))
    q4 = list(csv.DictReader(open(KOK / "stratejiler/ek_kaynaklar/son1ay_2026-11.csv", encoding="utf-8")))
    kd = list(csv.DictReader(open(KOK / "stratejiler/v3_adaylar/ham/github-backtest-katalog-denetimli__tumu.csv", encoding="utf-8")))
    for x in satirlar:
        if x["eslesme"] != "TEKRAR":
            continue
        pre, n = x["hedef"].split(":")
        n = int(n)
        if pre == "P001":
            t = rk[n - 1]
            iz = x["kaynaktaki_ad"].lower()
            if x["kaynak_id"] in ("A014", "A015", "A016", "A017"):
                kimlik = x["kaynaktaki_ad"].split(" ")[1].lower()
                if kimlik.split("_")[0] not in (t["ad"].lower() + " " + t["dosya"].lower()).replace(" ", "_"):
                    uyari.append(f"{x['ham_id']} -> P001:{n} ad uyumsuz: {t['ad'][:50]}")
        elif pre == "Q004":
            t = q4[n - 1]
        elif pre == "V014":
            t = kd[n - 1]
    return uyari


def yaz(satirlar, uyari):
    with open(ARA / "G10_ARSIV_ham.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HAM_SUTUN)
        w.writeheader()
        w.writerows(satirlar)
    with open(ARA / "G10_ARSIV_kaynaklar.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kaynak_id", "grup", "yol", "tur", "satir_veya_kayit", "git_ilk_ekleme", "not"])
        for k, yol, tur, n, nt in KAYNAKLAR:
            w.writerow([k, "G10_ARSIV", yol, tur, n, "", nt])
    with open(ARA / "G10_ARSIV_elle_kararlar.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ham_id", "eslesme", "hedef", "on_durum", "neden_kodu", "adalet_bayragi"])
        for x, s in zip(satirlar, S):
            w.writerow([x["ham_id"], x["eslesme"], x["hedef"], x["on_durum"], x["neden_kodu"], int(s["adalet"])])


if __name__ == "__main__":
    sat = ham_uret()
    uy = kontrol(sat)
    yaz(sat, uy)
    print(len(sat), "satir yazildi")
    print("eslesme:", dict(collections.Counter(x["eslesme"] for x in sat)))
    print("on_durum:", dict(collections.Counter(x["on_durum"] for x in sat)))
    print("kaynak:", dict(collections.Counter(x["kaynak_id"] for x in sat)))
    for u in uy:
        print("UYARI", u)
