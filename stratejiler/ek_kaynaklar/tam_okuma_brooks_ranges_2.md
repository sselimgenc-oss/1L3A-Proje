# Tam okuma: Al Brooks, Price Action Trading Ranges, sayfa 191-380 (parça brooks_ranges_2)

Okunan: 191-380, her sayfa sırayla. Çıktı: `veri/kartlar_ham/daytrade/Price_Action_Trading_Ranges_-_Al_Brooks_572_sayfa__tam_brooks_ranges_2.json` (6 yeni kart).

## Blok kanıtı (sayfa aralığı: konu)
- 191-199: mıknatıslar (sinyal çubuğu uçları, trend çizgisi, ölçülü hareket vb.); Bölüm III girişi: geri çekilmelerin trend -> aralık dönüşümü, iki ayaklı geri çekilme psikolojisi
- 200-209: geri çekilme tanımı, iki bacak, ekstrem testi, %60-70 yön olasılığı mantığı, güçlü trendde piyasadan giriş
- 210-214: Şekil PIII.1-2 (geri çekilmeler dönüşle başlar, MA'da L2/H2 örnekleri)
- 215-222: çıkış yapan geri çekilmeler (dik kanalda ilk TL kırılımı), Bölüm 11 ilk geri çekilme sırası (zayıflık işaretleri listesi)
- 223-233: MA geri çekilmeleri, Bölüm 12 çift tepe ayı / çift dip boğa bayrağı, baş-omuz devam formasyonu
- 234-243: başarısız çift dip, ölçülü hareket örnekleri, başarısız çift dip = kama varyantı
- 244-256: Bölüm 13 yirmi boşluk çubuğu, Bölüm 14 ilk MA boşluk çubuğu, Bölüm 15 günün kilit saatleri / stop-run
- 257-268: geç stop-run örnekleri, Bölüm 16 bacak sayma, Bölüm 17 başı (High/Low 1-2 tanımı, trend vs aralık farkı)
- 269-280: High/Low 1, 2, 3, 4 kuralları, başarısız H2/L2 evrimi, momentum ipuçları
- 281-290: bar sayımı örnekleri (Şekil 17.1-17.4)
- 291-301: Şekil 17.4-17.10 örnekleri (başarısız L2/L4, boğa trendinde L2 short yok)
- 302-312: Şekil 17.10-17.13, Bölüm 18 kama (üç itme) geri çekilmeleri başı
- 313-319: kama ayı/boğa bayrağı örnekleri, spike-ve-kanal kama, başarısız kama
- 320-325: Bölüm 19 düello çizgileri
- 326-332: Bölüm 20 baş-omuz/çift tepe-dip devam formasyonu (mevcut kart kapsıyor)
- 333-343: Bölüm IV ticaret aralığı tanımı, özellikleri, vakum etkisi, yön olasılıkları, kırılım istatistiği (~%80 başarısız)
- 344-358: aralıkta işlem (ölçekleme ikilemi, aralık günü, martingale yasağı, Şekil PIV.1-3)
- 359-369: Şekil PIV.4-9 (orta üçte bir, climax, aralık geri dönüşleri)
- 370-377: Şekil PIV.9 devamı, Bölüm 21 aralık ticareti setup listesi, Şekil 21.1 başı
- 378-380: Şekil 21.1 örnek günü (kitabın 381. sayfası aralık dışı)

## Yeni kartlar
1. daytrade__ilk-geri-cekilme-sirasi__brooks_r2 (kodlanabilirlik 1)
2. daytrade__basarisiz-cift-dip-tepe-kirilimi__brooks_r2 (2)
3. daytrade__yuksek1-dusuk1-guclu-trend-spike__brooks_r2 (1)
4. daytrade__aralik-ucunda-high1-low1-fade__brooks_r2 (1)
5. daytrade__duello-cizgileri-geri-cekilme__brooks_r2 (1)
6. daytrade__dik-kanal-ilk-trend-cizgisi-kirilimi-bekle__brooks_r2 (1)

## guncelleme_onerileri (mevcut kartlara; hepsi `Price_Action_Trading_Ranges` dosyasındaki kart_id'ler)
- daytrade__yuksek2-dusuk2-trend-geri-cekilmesi__brooks: (s.267-268) H1 ile H2 arasında en az küçük trend çizgisi kırılması olmalı, yoksa ikisi karmaşık ilk ayağın parçasıdır; (s.268) trendde H2 MA üstünde/yakınında alınabilir. (s.271-272,277-278) H2 başarısız olursa H3 (=kama boğa bayrağı) veya H4'e bak; H2 altı kırılım momentumu güçlüyse (1-2 büyük ayı çubuğu) H4'ü bekle. (s.273,278) Sinyal çubuğu küçük/doji ise stopu 2-3 tik uzağa ya da Emini'de ~2 puan para stopuna al (toplam <=8 tik). (s.286-287) İlk bacakta anlamlı trend çizgisi kırılımı yoksa H2 alma. (s.295) Boğa trendinde L2 short yok; önce güçlü trend çizgisi kırılması, sonra ikinci girişim short. (s.296) L2 MA'dan uzaksa zayıf; ikinci MA testi ilkinden daha yakın/derin olmalı.
- daytrade__yuksek2-dusuk2-aralikta-ters__brooks: (s.270,276,290) dar aralıkta/üst üste binen 3+ çubukta, doji sinyalde sayım kullanma; (s.343-344,347-349) aralık içinde stop ~2 puan (Emini ort. günlük aralık 10-15 puan), hedef 2-4 puan, aralık 3-4 puandan küçükse stop girişi yok; (s.347) H2 yalnız aralık dibinde ve MA altında.
- daytrade__cift-dip-boga-bayragi__brooks: (s.229) giriş önceki çubuk zirvesi +1 tik; ilk stop sinyal çubuğu dibi -1 tik, giriş çubuğu trend çubuğuysa stopu giriş çubuğu -1 tik'e çek, küçükse trend çubuğu oluşana kadar sıkma; (s.232) yükseliş-ve-kanal boğa trendinde kanal tabanı testindeki çift dipten en az işlem aralığının ~1/4'ü kadar sıçrama; (s.226) aralığa girmeden önceki momentum yönü kırılım yönünü destekler; (s.228) başarısız çift dip yeni kart olarak ayrıldı.
- daytrade__kama-geri-cekilme-ve-donus__brooks: (s.309-310) kama bayrakları 10-20 çubuk; trend dönüşü >=20 çubuk ve net trend kanal çizgisi gerektirir; kama geri çekilmesinde trend yönüne dönünce ilk sinyalde girilir, kama dönüşünde ikinci giriş tercih; (s.312) dik kanal kamada 17. çubuk gibi daha belirgin sinyali bekle; (s.316) H2 öncesi ilk bacak çok güçlü ise ikinci girişi (kırılım geri çekilmesi) bekle; (s.319) başarısız kama boğa bayrağı ölçülü aşağı hareket; (s.313) gap-yukarı + kama: ölçülü hareket = gap yüksekliği.
- daytrade__20-bosluk-cubugu__brooks: (s.244-245) giriş: yüksekliği EMA altında olan ilk çubukta önceki çubuk yüksekliği +1 tik buy-stop; ilk başarısız olursa ikinci giriş, üçüncüyü alma; pozisyonun bir kısmı swing; 20 sayısı keyfi; (s.248) tepe/parabolik climax sonrası tek bacak MA testi riskli, >=2 bacak bekle; (s.245) net trend dönüşü sonrası ilk boşluk çubuğu başarısız.
- daytrade__ilk-hareketli-ortalama-boslugu__brooks: (s.250-251) MA boşluk çubuğu ikinci denemesi (önceki çubuk yüksekliği üstü) mükemmel kurulum; trend yoksa MA boşluk çubuğu scalp, hedef MA, yalnız MA'ya yeterli alan varsa; (s.253) ikinci MA boşluk çubuğu kısa kurulumları.
- daytrade__gunun-onemli-saatleri-stop-run__brooks: (s.255-259) 11:30 PT civarı karşı-trend panik ayağı trend gününde ana trend çizgisini kırar, trend yönünde giriş; aralık gününde ters kırılım 11:30'da başarısız; çoğu aralık günü orta bölgede kapanır; saatler PT/ES seans bağımlı, kripto 7/24'e doğrudan taşınmaz.
- daytrade__ticaret-araligi-sinirda-dusuk-al-yuksek-sat__brooks: (s.340,374) aralık dibindeki güçlü ayı trend çubuğunun (tepede boğa çubuğunun) kapanışına/altına limit alım (üstüne limit short) veya geri dönerken stop girişi (sinyal çubuğu çok büyük değilse); (s.335-336,342) yön olasılığı: aralık ortası ~%50, tepede aşağı >=%60, dipte yukarı >=%60; önceki güçlü trend yönünde ek eğilim; (s.344) aralık MA altındaysa aşağı kırılım eğilimi, üstündeyse yukarı; (s.373-374) başlangıç için stop girişli kurulum listesi: dipte H2, tepede L2, trend çizgisi kırılımı sonrası ikinci giriş, kama bayrağı, ters dönüş çubuğu/son bayrak, kırılım geri çekilmesi; (s.343) aralık uç noktasına mikro kanalla gelindiyse kırılım geri çekilmesini bekle; (s.345) gün ortası (08:30-10:30 PT) aralık gününde işlem yapma, mükemmel olmayan girişleri alma; (s.345,351) martingale kesin ret.
- daytrade__dar-aralik-kirilim-modu__brooks: (s.270) güçlü trendde 10 çubuklu dar bayrakta kırılım yönünde stop girişi mantıklı; aralık günü orta üçte birinde çubuk sayımına dayalı işlem yok.
- daytrade__kirilim-geri-cekilmesi-ve-basarisiz-kirilim__brooks: (s.199,203) dört ve daha çok çubuklu mikro kanal kırılımı bir-iki çubukta başarısız olabilir; kırılım ile geri dönüş çubuğunun göreli gücü ve bağlamı belirleyici.
- daytrade__olculu-hareket-bacak-esitligi__brooks: (s.239,364-365,371) çift dibe göre ölçüm (bar1-bar5 yüksekliği + bar5 zirvesi), spike yüksekliği (ilk çubuk açılış/dibinden son çubuk kapanışı/zirvesine), kanal yüksekliği (kanal aşağı kırılımı için), boşluk ortası ölçümü; kırılım sonrası boğa spike'ında: risk ilk trend çubuğu dibinin altı, kâr hedefi ölçülü hareket, stopu birkaç çubuktan sonra başabaşa.
- Trends dosyasındaki daytrade__acik-trend-kucuk-geri-cekilme__brooks ve daytrade__mikro-kanal-gec-giris__brooks: (s.208,364) trend güçlüyse geri çekilmeyi beklemeden piyasadan küçük pozisyon + geniş stop (spike dibi/son salınım), geri çekilmede ek; stopu en son salınım altına izlet.

## Kart çıkmayan bölümler ve nedeni
- 191-199, 195-209 (Bölüm III giriş, mıknatıslar): kavram/psikoloji, ayrı giriş kuralı yok.
- 210-216 (şekil yorumları): mevcut kartların örnekleri.
- 281-301 (bar sayımı örnekleri): H1/H2/L1/L2 kartları kapsar; filtre ayrıntıları yukarıdaki güncelleme önerilerine yazıldı.
- 308: yükseliş-ve-kanal = iki bacak; kavram (Trends kitabındaki spike-ve-kanal kartı kapsar).
- 326-332: baş-omuz/çift tepe devam formasyonu; mevcut kart (daytrade__cift-tepe-dip-ve-omuz-bas-omuz-donusu__brooks) kapsıyor; ek bilgi: standart çift tepe girişi (dip altında stop) kırılımların %80'i başarısız olduğundan nadiren başarılı.
- 333-358 (aralık anatomisi, ölçekleme): kavram/psikoloji; sayısal olanlar (stop ~2 puan, hedef 2-4 puan, %60) güncelleme önerisine eklendi; Brooks'un "ölçekle" önerileri martingale'a yakın olduğundan (s.341, 345 ölçekleme) kart olarak sunulmadı. Not: kitap ölçeklemeyi (kaybedende ekleme) öneriyor; 1L3A kuralı (martingale yasak, risk limitleri kodda) ile çelişir, uygulanmaz.
- 359-380 (Şekil PIV.4-9, 21.1 örnekleri): bar bar örnek yorumu, yeni kural yok.

## Genel not
Bu parça ağırlıkla bar-sayım/psikoloji açıklamasıdır; kurulumların çoğu ilk turda kartlanmıştı. Yeni kartların hepsi puan 1-2 (öznel bağlam filtreleri). Sayısal parametreler (6 tik, 2 puan vb.) Emini'ye özgüdür; kriptoda ATR ile yeniden ölçeklenmeli.
