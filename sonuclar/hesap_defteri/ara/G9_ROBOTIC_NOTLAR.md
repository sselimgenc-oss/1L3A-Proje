# G9_ROBOTIC notları (betik: sonuclar/hesap_defteri/betikler/g9_robotic.py)

## Sayılar
- Kaynak B001 dosya_listesi.csv: 909 veri satırı -> 909 ham satır (kayıp yok). 909 dosya -> 540 küme (kume_listesi.csv; B002 başlığı 540 diyor, bu doğru).
- on_durum: D_KODLANMADI_NEDENLI=526, G_ML=123, F_YASAK_TIP=112, E_KODLANMADI_NEDENSIZ=96, TEKRAR=51, KOD=1
- eslesme: BENZER=446, YOK=411, TEKRAR=51, ESDEGER=1
- neden_kodu: benzer_var=446, ml=122, dca=107, -=97, lookahead=66, kopya=51, backtest_gecersiz=11, martingale=5, arac_sablon=2, llm=1, rastgele_giris=1
- E_KODLANMADI_NEDENSIZ: 96 dosya = 81 küme (BIZDE_YOK/BELIRSIZ + elle reddedilen eşleşmeler).
- KOD/AYAR: yok. Repoda (stratejiler/, motor/, DURUM.md) 'robotic' geçmiyor: bu kaynaktan hiçbir dosya doğrudan kodlanmamış. Tek ESDEGER: K237 SuperTrendPure -> swing__supertrend-psar (ATR periyot/çarpan çekirdekte yok, ızgaraya varsayıldı).
- kanit sütunundaki `yol:N` = veri satırı (başlık hariç), ham_id numarasıyla aynı.

## Küme içi TEKRAR neden verilmedi (talimattan sapma)
kume_listesi'ndeki 'katalogda N birebir kopya çökertilmiş' ifadesi, dosya_listesi'ne HİÇ girmeyen özdeş kopyaları sayar (kopya_sayisi). Kümedeki dosyalar mantık benzerliği (Jaccard>=0.7) ile gruplanmış, özdeş değil (ör. EI3v2_tag_cofi_green ve _2 farklı TF/stop). Bu yüzden küme içi TEKRAR yok. Temsilci = kümenin dosya_listesi'ndeki ilk dosyası; ESDEGER yalnız temsilciye, üyeler BENZER.

## TEKRAR (51 dosya)
Robotic deposu freqtrade-strategies kopyalarını içeriyor: dosya adı stratejiler/ek_kaynaklar/github_g1_freqtrade.csv (H001) 'ad' ile birebir aynı ve çekirdek metni H001 mekanik_ozet ile çelişmeyen 51 dosya TEKRAR -> H001:<satır> (hedef satırın akıbeti `not`ta). Bunların 3'ü Robotic'te DIGER şablon (BreakEven, DoesNothing, FixedRiskRewardLoss), 2'si lookahead/DCA/ML bayraklı (DevilStra, GodStra K143 vb.). Çekirdeği özetle çelişenler TEKRAR DEĞİL (AwesomeMacd, ReinforcedQuickie, SmoothScalp, Strategy003, Strategy004, wtc; GodStra K402 varyantları): `olası tekrar: H001:n` notu var. Ayrıca ssssi akrabaları (E0V1E/E0V1EN->H001:75, ClucHAnix->76, BBMod->81) TEKRAR değil, notlu. D001 (dis_envanter) çakışması varsa `not`ta.

## Doğrulama kapsamı
- BENZERI_TEST+ZATEN_TEST toplam 295 küme; 107'si (%36) sınıf kodu/belgesi açılarak elle karar verildi (51 ZATEN + 56 BENZERI; her sınıf >=1 kez açıldı: cover seçimi). Kalan 188 küme: 'önceki ajan kararı, doğrulanmadı' (BENZER, benzer_var; hedef = önceki ilk id, diğerleri `not`ta). Bu 446 BENZER satırın 322'si doğrulanmamış.
- Elle doğrulananlarda önceki ajan eşleşmesini REDDETTİĞİM kümeler (eşleşme YOK -> E): K039,K042,K026,K040,K041,K055,K066,K087,K326,K361,K053,K064,K061,K198,K301,K316. Eşleşmeyi DEĞİŞTİRDİĞİM: K025 (-> dis__ft-binh-cluc), K317 (-> dis__wtc-wavetrend), K071 (-> dis__flawless-bbrsi), K315, K144, K204, K081.
- ZATEN_TEST (önceki ajanın 'yüksek güven'i) çoğunda tutmadı: bilgi 'ZATEN' idi, ben ESDEGER değil BENZER yazdım (EWO/NFI kümeleri: EWO ölçeği, RSI4/CTI, çıkış farklı; canli_akraba/RAPOR.md ile uyumlu). Freqtrade örnek stratejileri ise TEKRAR oldu.
- Şüpheli doğrulanmamış eşleşme örneği: B001:549 quantumfirst -> dis__strategy005 (gösterge-ailesi eşleşmesi).

## Bulgular / tutarsızlıklar
- kume_listesi 'çekirdek_mantik' çıkarımı güvenilmez: çıkışlarda 'VEYA' birleştirmesi AND koşulları da VEYA gösteriyor (ör. Strategy002, Quickie); bu yüzden çıkış VE/VEYA farkını BENZER gerekçesi yapmadım. Bazı çekirdekler çelişkili (K039 mfi<20 ve >80).
- EWO ailesi: canli_akraba/ewo_aile.csv 'EVET (katalog KACIRDI)' diyen EI/t4c0s serisi (EWO_MEAN tüm-veri ortalaması) KULLANILABILIR sınıfındaydı; bunları D lookahead yaptım (ewo_aile notlu 17 lookahead satırının KULLANILABILIR olanları; sayı yaklaşık'dan; ML/DCA olanlar o sınıfta kaldı).
- Canlı akraba: ewo-ema-ofset için ESDEGER yok (14 ZATEN kümesi BENZER); E0V1E.py kırpık, E0V1E__2 giriş aynı ama çıkış/stop/TF/24s farklı -> BENZER dis__e0v1en.
- HarmonicDivergence (K227): pivot geriye yazma, BENZER swing__rsi-diverjans; lookahead şüphesi kodlamadan önce sınanmalı.
- ayarlar_d11j_ek/d12b_ek'e bağlı satır yok.
- Envanter dışı kaynak yok. aile sütunu (trend/MR/diger) çekirdek metninden anahtar kelimeyle kestirildi, yaklaşık.

## Öz kontrol
Rastgele 10 ham satır (seed 7) dosya_listesi.csv'deki satıra geri izlendi: 10/10 ad ve satır no tuttu. kisa_mantik<=160, kaynaktaki_ad<=120, ham_id tekil.
