# G2_DIS_ESKI notları

Betik: `sonuclar/hesap_defteri/betikler/g2_dis_eski.py` (yalnız okur; elle kararlar: `ara/G2_DIS_ESKI_elle_kararlar.csv`, 30 satır). Çıktı: `ara/G2_DIS_ESKI_ham.csv` (758 satır).

## Kaynak satırı ↔ ham satır
| kaynak | kaynak satırı | ham satırı |
|---|---|---|
| D001 dis_envanter.csv | 431 | 431 |
| D002 portfoy_adaylari.csv | 71 | 71 |
| D050 meta.json | 164 | 164 |
| D051 meta3.json | 92 | 92 |
Eşleme/karar dosyaları (D003-D049: dis_kodlanacak, kodlama a/b/pf, dis_ayarlari) satır üretmedi, yalnız kanıt. D052 (RAPOR.md) ve eski proje analiz/aday.csv yalnız `not` içinde. Toplam 758, tutuyor.

## Dağılım
- D001: on_durum={'KOD': 324, 'F_YASAK_TIP': 61, 'D_KODLANMADI_NEDENLI': 40, 'G_ML': 3, 'E_KODLANMADI_NEDENSIZ': 3}; eslesme={'KOD': 162, 'AYAR': 161, 'YOK': 104, 'BENZER': 3, 'ESDEGER': 1}
- D002: on_durum={'KOD': 18, 'D_KODLANMADI_NEDENLI': 10, 'TEKRAR': 43}; eslesme={'KOD': 11, 'AYAR': 7, 'YOK': 10, 'TEKRAR': 43}
- D050: on_durum={'TEKRAR': 160, 'D_KODLANMADI_NEDENLI': 4}; eslesme={'TEKRAR': 160, 'YOK': 4}
- D051: on_durum={'TEKRAR': 87, 'D_KODLANMADI_NEDENLI': 5}; eslesme={'TEKRAR': 87, 'YOK': 5}
- Toplam on_durum: {'KOD': 342, 'F_YASAK_TIP': 61, 'D_KODLANMADI_NEDENLI': 59, 'G_ML': 3, 'E_KODLANMADI_NEDENSIZ': 3, 'TEKRAR': 290}
- Not: D002 satırlarının 43'ü dis_envanter `veri_yok` satırlarının kopyası (TEKRAR, hedef D001:n; kodlama/karar o envanter satırında). D050/D051'in 247'si dis_envanter `tv` satırının aynısı (TEKRAR); kalan 9'u envanterde yok.

## meta / meta3
- meta (164) ve meta3 (92) ayrık kümeler (kesişim 0); meta3, meta'nın alt kümesi DEĞİL. İkisi birlikte 247 = envanterdeki tv satırı sayısı; 9 betik envanterde yok (meta: JziAVVm4, D898fmMY, X2Y61umI, pcSURSbs; meta3: 7xkIvA4u, qnirD0Kg, kZVrTReu, ykKHn2Gf, LxrgnsTO). Hepsi kaynak kapalı/bulunamadı (erişim '?'), eski projede elendi -> D / kaynak_kapali.
- Üç ad farkı yalnız HTML kaçışı/başlık farkı (MQDDEl1e, 7SSRGEbI) ve i3Uc79fF (envanterde ad '** Inputs **', meta'da 'Flawless Victory Strategy'); id aynı olduğundan TEKRAR.
- Eski proje (strateji-sg) sonucu (aday.csv, _kararlar.json, RAPOR: hybrid_brk=hezSShJr, sqzmom=G40dtEbK, macd_reloaded=VO6DY8s1 geçti) yalnız `not` alanında; 1L3A testi değil.

## DURUM.md sayıları ile karşılaştırma
- "160 TradingView": meta.json 160 `strategy` (164 betik, 4 kapalı); envanterde tv satırı 247 (meta 160 + meta3 87). DURUM sayısı yalnız ilk turu sayıyor.
- "68 freqtrade": envanter 68 freqtrade satırı: tutuyor. (github_g1 ek kaynağında 153 satır var, o başka grubun.)
- "~30 dış kural": envanterde kural 73 + awesome 32 + jesuistm 11 = 116 satır (test_edilebilir 55+9+9). "~30" eski/alt küme.
- "87 dış kodlu": ham D001'de on_durum=KOD 324 satır (KOD eşleşmesi 162 satır, 162 satırda ayrı dis__ sınıfı; AYAR 161). Dış kaynaklı kodlu sınıf sayısı DURUM'daki 87'den çok (d8/d9/d11 dalgaları sonradan eklendi). 
- "110 dış ayar": dis_ayarlari içinde envanter satırına doğrudan bağlı kayıt tam 110 (tutuyor); ama 18 satır daha 'birleşik ayar' notuyla aynı kaydı paylaşıyor -> AYAR satırı 128. dis_ayarlari toplam 177 kayıt (kalan 59 d11j, 5 ek77, 3 son1ay: başka gruplar).
- Tüm 177 dis_ayari kaydı `tarama.dis_ayarli_strateji` ile kuruluyor (parametre adları sınıfta var; test koşmadan yalnız kurma kontrolü).
- 81 ayar notu 'YAKLAŞIK' (kaynağın birebir değil, aileye uyarlama): ham `not` alanında işaretli; "fark test edilmedi" konusunda lider dikkat etsin.

## E_KODLANMADI_NEDENSIZ (en önemli)
Sadece 3 satır: D001:141 NQ/MNQ Super Scalper; D001:347 Minervini trend şablonu (arac_sablon etiketi yanlış, gerçek kural); D001:383 Trailing Trade (kural).
### dis_kodlanacak.csv kuyruğunda ("dalga_grubu") / envanterde `kodlandi` ama sınıf bulunmayanlar (7)
D001:91 GRAM RSI, D001:110 JUP RSI (ikisi DCA: F_YASAK_TIP koydum, lider onaylasın), D001:141 NQ Super Scalper (E), D001:250 AlmgrenChriss (BENZER dis__twap-rsi), D001:270 FixedRiskRewardLoss (D arac_sablon), D001:276 GodStra (D kural_belirsiz), D001:383 Trailing Trade (E). Akıbet yalnız github_g1_freqtrade.csv'de (3 freqtrade satırı) var; envanter 'kodlandi' demesi yanlış.

## Diğer tutarsızlıklar
- arac_sablon etiketi yanlış: Minervini (D001:347) ve "SMA20/60 L/S (4h, BTC şablonu)" (D001:367, BENZER swing__ma-kesisim; 20/60 ızgara ve dis_ayarlari dışında). github_g4 dosyası bunları 'ayar' sayıyor ama kod/ayar kaydı yok.
- InformativeSample (D001:281): envanter veri_yok; d11h'de aile sınıfı dis__ust-tf-ma-yon-kesisim'e kaynak olarak girmiş ama kural farkı var -> BENZER.
- JT_Dual_Thrust (D001:423): kodlama_b 'kapsam_disi' (dis__dual-thrust kapsıyor) -> ESDEGER; JT kaynak kodu repoda yok, doğrulama özet metne dayanır.
- CleanTradeQuantum (JeRCEqWU): docstring iki sınıfa değiyor; doğru sınıf dis__tv-cleantradequantum (dis__utbot-kdj yalnız UT Bot formülünü alır).
- EMA MACD Dual Engine (f9xLZqpF): iki sınıf (ikili + ortalamaya-donus), hedef ilki, ikincisi `not`'ta.
- Envanter `veri_yok` 44 satırdan 43'ü portföy katmanında sonradan kodlandı (KOD/AYAR pf__*); kalanlar D/veri_yok: VIX MACD, TASC tarım, Technical Summary, China CLR. Portföy kaydı eşi olmayan 1 satır (InformativeSample) yukarıda.
- portfoy_adaylari.csv'de pf_sinif boş olup sonradan ek2/baglama ile kodlananlar: Clenow SoM (AYAR pf__rotasyon), ArbitrageLab PCA (KOD pf__pca_statarb), Silver Always Long (KOD pf__gumus_makro). KGT v3 BAGLANAMAYAN: portföyde yok, ayrı olarak motor/strateji/onceki/kgt.py (onceki__kgt) var — `D_KODLANMADI_NEDENLI kapsam_disi` yazdım, lider KGT'nin zaten kodlu olduğunu dikkate alsın.
- pf satırlarından ek77 (14) ve kart (10) kaynaklılar başka gruplarla (G3 ek77, kart grubu) kopya olabilir; `not`'ta kimlik yazılı.
- KOD/AYAR ayrımı pf için: sınıfın ilk bağlandığı satır KOD, sonrakiler AYAR (sezgisel).
- kural/awesome/jesuistm kaynak dosyaları (arsiv/algo-sg/dis_kaynak/*.py) repoda yok; eşleme sınıf docstring anahtarlarından (ör. okt_ema_mom) yapıldı, satırlarda 'kaynak okunamadı' sınırı geçerli. tv .pine dosyaları da repoda yok.
- H_BIZIM_EVRENDE_UYGULANAMAZ ham satırda yok; veri/evren nedenleri D'ye yazıldı (VIX/Çin A-hisse dahil: D veri_yok).
- 3 yasak-bölgesi satırı (stopsuz ekleme, 'How to use Leverage...' vb.) F stopsuz_grid.

## Öz kontrol
Rastgele 10 satır (seed 3) kaynağa geri izlendi (D001:244, 134, 379, 68; D050:105, 56, 117, 139, 93; D002:55): kaynak satırı, ad ve kanıt dosyası/satırı tutuyor; hedef sınıflar kod_kaydi.csv'de var (betik hedef varlığını denetliyor, hata 0).
