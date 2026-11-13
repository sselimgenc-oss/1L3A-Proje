# G10_ARSIV NOTLAR

## Kaynak -> ham satir sayisi (kaynaklar: G10_ARSIV_kaynaklar.csv)
A001 algo-sg/STRATEJILER.md 8; A002 STRATEJILER_GUNLUK.md 7; A003 A_V2 1; A004 swing-sg STRATEJILER 3; A005 CODEX_ADAYLAR 11 (baslik 12 diyor, tabloda 11 repo: fark kaynakta);
A006 CODEX2 6; A007 brainbrick 8; A008 RAPOR 4; A009 RAPOR_KRIPTO 3; A010 RAPOR_PA 7; A011 EPA 2; A012 RAPOR_S2 4; A013 HGT 1;
A014 day-trade-sg 14 (STRATEGIES 15 anahtar, S11=S10 ayari); A015 scalp-sg 3; A016/A017 codex-algo 9+8; A911 Haiku test 3; A912 Haiku portfoy 3. Toplam 105.

## Dagilim
eslesme: KOD 6, BENZER 45, TEKRAR 43, YOK 11. on_durum: KOD 6, D 50, TEKRAR 43, E 3, H 2, G 1.

## Proje bazinda
- algo-sg: 16 strateji bulundu (A1,A2,B,D1,D2,A v2 + 10 elenen fikir/giris); 2 KOD (A1,B); baska envanterde 0.
- strateji-sg: 18 bulundu (KGT, KMN, SAKK, GPK, EPA-A/B, HGT, PA x7, ortalamaya donus x3, 1S giris x2...); 2 KOD (KGT, KMN); TV 164 + 41 aday G2'nin (satir yapilmadi).
- swing-sg: S1-S3 (2 KOD) + Codex 17 repo/fikir (5 TEKRAR: V014/P001) + brainbrick 8 (0 kodlu, hepsi BENZER/YOK).
- day-trade-sg 14, scalp-sg 3, codex-algo 17: hepsi 1L3A'da kodlu degil; P001'de (repo_kodlari) zaten var -> 34 TEKRAR.
- sg-pano, strateji-test-pano, sg-algo-proje: strateji icermiyor (pano/bot motoru). sg-arge-: G3.
- Haiku strateji arastirma dali: 3 TEKRAR (G5 son1ay) + 3 BENZER (GTAA, momentum, sektor momentum -> pf__trend_sepet/pf__rotasyon).

## Kapsam disi birakilanlar
- algo-sg/DIS_STRATEJILER.md 186 satir = stratejiler/dis_envanter.csv (freqtrade/awesome/jesuistm/kural) = G2 (D001). Satir yapilmadi.
- strateji-sg tv/aday.csv, tv_eleme_dali meta = G2.
- Haiku Ar-Ge 12 varyant (haiku__don-/liwei-/rsi- ema200, vol, ema-vol, notrend/noband/hedef2): YENI STRATEJI SAYILMADI. Neden: uc mevcut sinifa (donchian-kirilim, atr-rsi-liwei, rsi-momentum-esik) EMA200/oynaklik filtresi ekleyip cikaran on-kayitli filtre varyantlari; yeni giris mantigi yok. Akibet: WF'de 5/120 gecti, hicbiri K2/K3 saglamliktan gecmedi ("gelistirilemedi", SONUC_GELISTIRME.md). 120 elenen x 5 enstruman yeniden testi de yeni strateji degil.
- Elenen "varyant" olarak sayilmayanlar: A yalniz long, KGT Mag7/BIST/emtia, kaldirac, BTC rejim/gorece guc filtreleri, GTAA 20 varlik, swing-sg T1/S4 'bizim' surumleri.

## Tutarsizliklar / bulgular
- CODEX_ADAYLAR.md baslik "12 strateji" ama 11 repo tablosu var.
- swing__pin-bar ve swing__ma-geri-cekilme sinif kodlari dogrudan acilmadi (A010:7, A011:1 fark metni dogrulanmamis).
- BENZER satirlarin cogu, hedef sinifin docstring'i okunarak karsilastirildi (kod govdesi degil).
- ayarlar_d11j_ek/d12b_ek bu grupta kullanilmadi (AYAR satiri yok).

## ADALET listesi (eski projede elenmis, 1L3A'da ayni form test edilmedi; 39 satir)
OZET.md §3 "Denendi - basarisiz" maddeleri 1L3A kararidir; asagidakiler eski proje sonucuna dayaniyor:
- A001:4 algo-sg elenen: 1H RSI/Bollinger trend yonunde geri cekilme (S1) -> daytrade__bant-donus
- A001:5 algo-sg elenen: 1H Donchian kirilimi (S2) -> daytrade__donchian-kirilim
- A001:6 algo-sg elenen: Fibonacci %50-61.8 olculu hareket geri cekilmesi (S3) -> swing__fib-geri-cekilme
- A001:7 algo-sg elenen: 4H kirilim sonrasi 1H geri test girisi -> daytrade__kirilim-geri-test
- A001:8 algo-sg elenen: 24 saatlik momentum patlamasi -> YOK
- A002:2 algo-sg D2 - Elder 'kirmizi degil' + gunluk kapitulasyon donusu -> onceki__kapitulasyon
- A002:3 algo-sg elenen: Elder Uclu Ekran (haftalik yukari + gunluk RSI2 asiri satim) -> swing__rsi-asiri-donus
- A002:4 algo-sg elenen: Turtle 20g kirilim + haftalik Donchian(10) yonu -> swing__donchian-kirilim
- A002:5 algo-sg elenen: Turtle 20g kirilim + Elder yonu -> swing__donchian-kirilim
- A002:6 algo-sg elenen: Elder Impulse ilk gun girisi -> YOK
- A002:7 algo-sg elenen: Halsey olculu hareket (kitap seviyeleri %61.8/%78.6/-%23.6) -> dis__halsey-olculu-hareket
- A005:8 lutfi-zain/quant-lttd-ichimoku -> swing__ichimoku
- A006:3 logiccrafterdz/Argus - gizli bogа uyumsuzlugu (D3) -> swing__rsi-diverjans
- A006:6 MajidUppal/CSCI278 (S2) - bilesik 10 gosterge skoru (D2) -> dis__gosterge-oy-toplami
- A007:1 brainbrick 037 - gunluk+haftalik SMA50 trend -> dis__sma200-ls
- A007:2 brainbrick 007 - 12 ay trend (gunluk+haftalik getiri>0) -> dis__tsmom
- A007:3 brainbrick 050 - volatilite hedefli maruziyet -> pf__v3-vol-yonetimli-long
- A007:4 brainbrick 001 - 12-1 momentum en iyi %10 -> pf__rotasyon
- A007:5 brainbrick 020 - artik (beta-arindirilmis) 12-1 momentum -> pf__kesit_ls
- A007:6 brainbrick 007P - 12 aylik getirisi pozitif olan tumu -> pf__rotasyon
- A007:7 brainbrick 012 - 252 gun en dusuk volatilite %10 -> pf__rotasyon
- A007:8 brainbrick 089 - emtia degeri (5 yil once fiyat / bugun) -> YOK
- A008:1 strateji-sg SAKK - Seans acilis kutusu kirilimi (5 dk) -> daytrade__orb
- A008:2 strateji-sg GPK - Gunluk pivot/CPR kirilimi (1s day trade) -> onceki__kgt-gun
- A008:4 strateji-sg Faz1 ortak payda B - ust TF trend + BB/RSI/VWAP donusu -> scalp__bant-donus
- A009:2 strateji-sg elenen: 1G+4S yon + 1S RSI dip geri cekilme (Cift RSI) -> daytrade__rsi-asiri-donus
- A009:3 strateji-sg elenen: 1G+4S yon + 1S Donchian kirilimi -> daytrade__donchian-kirilim
- A010:1 strateji-sg SKA/CBF - Sikisma (Tikaniklik) Kirilim Arizasi (4S) -> daytrade__sahte-kirilim
- A010:2 strateji-sg elenen PA: Trend Cubugu Arizasi (TBF) -> swing__geri-cekilme-fiyat-eylemi
- A010:3 strateji-sg elenen PA: Yavaslama (DEC) -> swing__ardisik-bar-tukenme
- A010:4 strateji-sg elenen PA: Dorua Karsi (ANT) -> swing__ardisik-bar-tukenme
- A010:5 strateji-sg elenen PA: Basinc Bolgesi (PZ) -> daytrade__konsolidasyon-kirilim
- A010:6 strateji-sg elenen PA: Zayif Geri Cekilme (WPB) -> swing__geri-cekilme-fiyat-eylemi
- A010:7 strateji-sg elenen PA: Pin bar (51 Str. 7.3) -> swing__pin-bar
- A011:1 strateji-sg EPA-A - EMA 8/21/55 pullback + mum + S/D + trend cizgisi -> swing__ma-geri-cekilme
- A012:2 strateji-sg elenen: 4S/1G Bollinger + RSI(2) ortalamaya donus -> swing__bant-donus
- A012:3 strateji-sg elenen: kesitsel kisa vadeli donus (gecen haftanin kaybedeni) -> pf__kesit_ls
- A012:4 strateji-sg elenen: IBS donusu (gunluk, 151 §4.4) -> pf__ibs_donus
- A013:1 strateji-sg HGT - haftalik yon / gunluk islem (20 Str. #5) -> dis__ma-mukemmel-siralama

Ozellikle: A006:3 (gizli diverjans, eski projede sisteme Sharpe katan tek Codex adayi, "S4 adayi"), A005:8 (Ichimoku C4 OOS PF 2.52), A002:2 (D2 kapitulasyon gunluk, stres PF 2.33), A011:2 (EPA-B, yedek), A007:6 (ABD trend portfoyu, kagit hesaba alinmisti), A002:6 ve A001:8 (hicbir yerde karari yok -> E), A007:8 (E).

## Oz kontrol
Rastgele 10 satir kaynaga geri izlendi (A001:4, A004:3, A005:4, A007:2, A008:1, A010:1, A012:4, A014:7, A016:5, A912:1): kaynak metni/kodu ve hedef sinif docstring'i acildi; TEKRAR hedefleri (P001 satir adi, V014 repo adi, Q004 satiri) betikle dogrulandi, uyari yok. Dogrulanamayanlar: yukaridaki iki sinif.
