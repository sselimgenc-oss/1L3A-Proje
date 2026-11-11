# v3 aday araştırması — rapor (2026-11-10)

## Özet
- Taranan ham satır: **2515** (15 katalog dosyası, `ham/`). Hepsi `on_eleme.csv`'de, hiçbiri atlanmadı.
- Ön eleme kararları (belirsizler ikinci bakıştan sonra): kod_yok 799, veri_yok 523, yasak 519, tekrar 364, arac 218, kart 92, belirsiz 0.
- `kart` çıkan 92 satır, aynı kaynağın tekrarları birleştirilince ve 13 aday kaynak okunamadığı ya da ML/kural eksikliği nedeniyle reddedilince **72 karta** indi (`kartlar/`, ret gerekçeleri `REDDEDILENLER.txt`).
- Bu 72 kartın 7'si araştırma oturumunun ilk turunda (makale/blog taraması) yazıldı, 65'i katalog satırlarından.
- Kartların 45'inde `veri_uygun = true`, 27'sinde false (hisse/ETF/ülke/tahvil evreni ya da takvim verisi gerekiyor).
- Stil: swing 53, daytrade 19, scalp 0. Gün içi kripto (talimat önceliği 1) zayıf kaldı.

## Fable hakem sonucu (`fable_hakem.csv`, 0-10 puan)
Fable yalnız kart metnine baktı; kaynak URL'leri açmadı, strateji test etmedi. En yüksek puan 7: **hiçbir kartta güçlü, doğrulanmış kanıt yok.**
`adaylar.csv` sütunu `oncelik`: 1 = Fable'ın ilk 15'i, 2 = puan ≥ 4, 3 = geri kalan.

İlk 15 (puan):
1. swing__donchian-ansambl-vol-hedef__zarattini (7)
2. swing__funding-7g-haftalik-tercil__vine (7)
3. daytrade__gunici-momentum-noise-alani__zarattini (6)
4. daytrade__ilk-yari-saat-momentum__shen (6)
5. daytrade__saat-21-23-utc__padysak (6)
6. daytrade__saatlik-asiri-tepki-tersine__denicola (6)
7. daytrade__asya-kutu-kirilim-ma50__mutiiria (5)
8. daytrade__funding-1s-devam__octopustakopi (5)
9. swing__adaptivetrend-6s-momentum__arxiv (5)
10. swing__fip-kesitsel-momentum__baptoudur (5)
11. swing__funding-kesit-decil-carry__octopustakopi (5)
12. swing__haftalik-30sma-20h-kirilim-trix__ccadic (5)
13. swing__kirmizi-mum-2x-hacim-ertesi-gun__habr (5)
14. swing__momentum-btc-rejim-top5__adensvaz (5)
15. swing__volatilite-kirilim-k05__mskim (5)

Fable'ın 3 genel riski:
1. Kanıt neredeyse tamamen doğrulanmamış iddia (README/Quantpedia özeti, örneklem içi, maliyetsiz). Tek gerçek OOS bildiren funding-7g-vine: OOS Sharpe 0,39, PBO 0,81. Akademik kartlarda eşik/stop/pencere bizim uyarlamamız; test öncesi ön kayıtla sabitlenmezse uydurma riski bize geçer.
2. Evren uyumsuzluğu: kesitsel kartlar yüzlerce hisse/coin varsayıyor, bizde 13-15 coin ve az sayıda hisse var. `veri_uygun` işaretleri iki yönde de hatalı olabilir (12-1 momentum, ERC-6ETF, ters-FVG-NQ fazla iyimser; FOMC, opsiyon vade, payday, tatil öncesi, noise-alanı fazla kötümser; DK_SPX var). Takvim kartları yılda 8-12 işlem üretir.
3. Lookahead/icra tuzakları (funding zaman damgası, aynı mumda stop/hedef sırası, Kalman/pairs parametre sızıntısı) ve mevcut havuzla tekrar (IFR2/RSI2, btfd, ORB/Londra, voltarget-trend, v2 funding). Test bütçesini şişirip çoklu test yanlılığını artırır.

## Dürüst sınırlar (kullanıcı/ana oturum bilmeli)
- **Linkler her zaman açılmadı.** İlk 8 ön eleme parçasında (p00–p07, ham dosyaların başı: MASTER, doğrulanan 48 ve `__tumu` başı) satırlarda URL yoktu ya da ajanlar sayfaları açmadı; kararlar satır metnine dayanır. Sonraki parçalarda ajanlar çoğu GitHub/web sayfasını açtı, ama README ile sınırlı kaldı (strateji dosyaları okunmadı); 403/404/5xx dönen sayfalar için karar satır bilgisine dayanıyor. Bu yüzden 799 `kod_yok` kararı (kural README'de yok) zayıf dayanaklı: asıl kaynak kod okunsa bir kısmı kart olabilir.
- `belirsiz` 226 satırın ikinci bakışı Sonnet ajanlarıyla yapıldı, ancak bir kısmı yine sayfa açılmadan karara bağlandı (ajanlar raporunda belirtti).
- MASTER katalog satırlarında URL boştu; Quantpedia kartları (10) kaynak sayfası slug tahminiyle bulunup yalnız Quantpedia özetinden yazıldı, orijinal makaleler okunmadı. Kanıt alanları buna göre "kısmen".
- MDPI, Wiley, Taylor&Francis, Springer, Elsevier, Ledger makaleleri 403/503 verdi; bu yüzden 5 kaynak karta dönüşmedi (`REDDEDILENLER.txt`). Kullanıcı metni sağlarsa yeniden denenebilir.
- Kart sayısal sonuçlarının tamamı "iddia (doğrulanmadı)". Hiçbir strateji test edilmedi.
- `araclar/kart_dogrula.py` yalnız `veri/kartlar_ham/` altına bakar; v3 kartları ayrı bir betikle (zorunlu alanlar, kart_id=dosya adı, kaynak/veri_uygun/kodlanabilirlik biçimi) kontrol edildi, hata kalmadı. Haiku biçim kontrolü ayrıca yapılmadı; kontrolü ana oturum betikle yaptı.
- Web arama haftalık sınıra takıldı: ilk turdan sonra yeni arama yapılamadı. Talimattaki "boşlukları ara" adımı (gün içi kripto, baz/funding, SSRN/arXiv) bu yüzden yapılmadı; yalnız ham listeler ve ilk turun 7 kartı işlendi.
- Ajan çıktılarında `ad` alanı bazı satırlarda repo adı, bazılarında başlık; `on_eleme.csv` ham sütun sırasına göre birleştirildi.
- `adaylar.csv`'de `kanit_var` değerleri ajanların beyanıdır.

## Devam noktası (sonraki oturum)
1. Web araması açılınca: gün içi kripto (5m–1h), funding/baz/kesit, SSRN/arXiv boşluklarını ara.
2. `kod_yok` satırlarından GitHub repolarında strateji dosyasını okuyup kart çıkabilecekleri yeniden tara.
3. Kaynağı okunamayan 5 makaleyi (REDDEDILENLER.txt) tam metinle tekrar dene.
4. Hakem puanları kart metninden; kaynakları açıp bir kez daha doğrulama düşünülmeli.

## Dosyalar
`on_eleme.csv` (2515 satır), `kartlar/*.json` (72), `adaylar.csv` (72), `fable_hakem.csv` (72), `REDDEDILENLER.txt`, bu rapor. `ham/` ve `TALIMAT.md` değiştirilmedi.

---

# Tur 2 (2026-11-11)
Tur 1 metnine dokunulmadı; yalnız dosyalara satır/dosya eklendi.

## Özet
- **Gemini** (`gemini_dr_6bolge.csv` 69 + `gemini_dr_afrika.csv` 8 = 77 satır): `on_eleme.csv` sonuna eklendi (artık 2592 veri satırı). Kararlar: tekrar 24, belirsiz 19, kod_yok 19, veri_yok 7, kart 4, yasak 2, arac 2. Gemini'nin birçok linki/tarifi uydurma ya da yanlıştı (404 repo, kodla uyuşmayan stop/lisans); karar kodu/sayfayı açıp okuyarak verildi. Açılmayan fmz/tistory/dergipark satırları `belirsiz` bırakıldı.
- **kod_yok yeniden bakış** (`on_eleme_tur2_kod_yok.csv`, tur 1'in 799 satırının tamamı, tur1_karar sütunuyla): kod_yok 277, kart 162, belirsiz 103, yasak 95, veri_yok 94, tekrar 46, arac 22. Yani tur 1'de `kod_yok` denen satırların yaklaşık beşte biri, asıl kod açılınca kural çıkan satırlar çıktı. Bu 162 + Gemini'nin 4 satırı, aynı kaynakların birleştirilmesi ve tur 1 kartlarıyla çakışanların elenmesiyle 135 benzersiz adaya indi.
- **Kart yazımı:** 135 adaydan 60 kart yazıldı (75 aday kaynak/kod açılıp okunduktan sonra tekrar, lookahead/örneklem içi seçim, ML, martingale benzeri ya da kural çıkarılamadığı için `REDDEDILENLER_tur2.txt`'ye gitti).
- **Web araması** (artık açık): 12 yeni kart; gün içi kripto 3, funding/baz/kesit 5, yayımlanmış kanıt 4. Tur 1'de okunamayan makalelerin açık kopyası denendi: Heliyon "turn-of-the-candle" PMC'den okundu (etki 1 dakikalıkta, 5m altı: ret). MDPI, Springer, Ledger yine okunamadı; Wiley/Shen zaten kartlı.
- **Toplam yeni kart: 72** (`kartlar/` artık 144 kart). `adaylar.csv` 144 satır. Stil: daytrade 37, swing 35 (scalp 0). `veri_uygun` true 62, false 10.
- `REDDEDILENLER_tur2.txt`: 110 satır (ad | url | neden).

## Fable hakem sonucu (yalnız yeni 72 kart, `fable_hakem.csv`'ye eklendi)
Fable kart metnine baktı, kaynakları açmadı. En yüksek puan 6; "ilk_20 = evet" eşiği 4 (tur 1'de 5'ti: bu turun kartları daha zayıf). `oncelik`: 1 = bu turun Fable ilk 15'i, 2 = puan ≥ 4, 3 = geri kalan (tur 1 satırlarına dokunulmadı).

İlk 15 (puan):
1. swing__kisa-vade-momentum-2-3-hafta-kesit__liu-tsyvinski-wu (6)
2. swing__btc-gecelik-max10-hafta-sonu__dujava (5)
3. swing__vol-yonetimli-long__moreira (5)
4. swing__4s-kirilim-ema200-adx__epfraghu (5)
5. daytrade__donchian20-ema100-400-xau-1s__guannings (5)
6. swing__50g-kirilim-sma-filtre-3atr-iz__wilki2021 (5)
7. daytrade__cuma-15-est-tutma-saatlik__miralles (4)
8. daytrade__orb-5dk-oynak-hisse-hacim__zarattini (4)
9. swing__kripto-max-piyango-kesit__ozdamar (4)
10. swing__kripto-30g-momentum-vol-yonetimli__grobys (4)
11. swing__rsi5-esik-70-momentum__aries744 (4)
12. daytrade__ema21-geri-cekilme-h4-yapi-xau__abbujo (4)
13. swing__hacim-patlamasi-sma50-rsi-atr-btc1g__parakh20 (4)
14. daytrade__bb-ust-kirilim-rsi-4s__tradingstrategy-ai (4)
15. swing__donchian10-ema200-egim-impuls-3atr-iz__tientung2501 (4)

Fable'ın 3 riski:
1. Kanıt neredeyse yok: çoğu kart GitHub deposu; sonuç ya yok ya tek coin/tek dönem, örneklem içi, maliyetsiz. Birkaç kaynak kendi sonucunu negatif bildiriyor ya da geri çekmiş (markov, kesit-z-skor, üst-fitil, çok-ufuk, d200-roc, 100g-roc).
2. Dolum/bar sırası iyimserliği: sinyal barının kapanışından işlem, aynı barda hedef/stop sırası, limit doluyor varsayımı; pivot/fraktal onaylı kartlarda sağ bar beklenmezse lookahead. Testte "sonraki bar açılışı + stop önce" zorunlu olmalı. Kesit kartları yüzlerce coin/hisse varsayıyor, bizde 13-15 coin ve ~17 hisse; seans kartları sunucu saati/yaz saatine bağlı; bazı `veri_uygun=true` iyimser (orb-5dk-zarattini, nikkei, gap-fade).
3. Sistematik: tur 2 çoğunlukla standart gösterge kombinasyonlarının kanıtsız GitHub varyantı ve havuz aileleriyle yoğun örtüşüyor (Donchian/kırılım ailesinden 6 kart; bant-dönüş ve RSI geri çekilme çok). Parametreler çoğunlukla aynı kısa örnekte hyperopt/Optuna/ızgara ile seçilmiş; zaman dilimi/periyot/stop çoğu kartta "kaynakta yok" ve yazan ajanın varsayımıyla doldurulmuş. Test öncesi aileleri kümeleyip tek temsilciyle sınamak ve varsayımları ön kayıtla sabitlemek önerilir.

## Dürüst sınırlar (tur 2)
- Tur 2'de `kod_yok` satırlarını Haiku ajanları okudu; 40 parçanın bir kısmı önce yalnız raw/README ile çalıştı (k06, k09 `git clone` ile yeniden yapıldı; k00 ve k32/k35/k36/k37/k38 satırlarının hiçbirinde GitHub URL yok, yani kod açılamadı, `kod_yok` kalan 277 satırın çoğu bu). Diskin dolması bazı ajanların klonlarını bozdu; etkilenen k23 (9 satır) ve k24 yeniden işlendi. Diğer parçalarda da ajanlar geçici disk/klon sorunu bildirdi (k11, k12, k16, k21, k22, k25 ve diğerleri); o satırların kararı yer yer zayıf olabilir.
- Kart yazan Sonnet ajanlarından grup 5, 13 adayı klonlamadan "ön eleme notuna/mevcut kartlara bakarak tekrar" diye reddetti (ou-statarb, trad_bot_pi42, vein_smc_bot, ai-trade, Cross-Sectional-Mean-Reversion, lhcbenac, jiamihuobi, CUATS, TRB, ETH_Perp, btc-perp-research S2/S4 vb.); bunlar kaynağı açılmadan reddedildi, sonraki turda yeniden bakılabilir. Birçok ajan ayrıca "küçük varyant = tekrar" kararlarını (RSI/MA/Donchian/pairs aileleri) kendi yargısıyla verdi: sınırdaki bazı retler (tranduy216, Initin0, trading-learn XAU, Aggressor session_level_retest) geri alınabilir.
- `araclar/kart_dogrula.py` v3 kartlarını taramıyor; kartlar `kesit-funding-baz-vekil__chi.json` alan kümesiyle karşılaştırıldı (144 kartta fark yok, kart_id = dosya adı).
- Birçok kartta periyot/zaman dilimi/stop kaynakta olmayıp `null` ya da ajan varsayımı; belirsizlikler alanına yazıldı.
- Tüm sayısal sonuçlar "iddia (doğrulanmadı)"; hiçbir strateji test edilmedi.
- Bazı repolarda açık token/API anahtarı görüldü (aatmanjoshi, wefiwett, adamincident/TRB, IchimokuBot, neelshah1903); değerler kopyalanmadı, ilgili depo sahiplerinin iptal etmesi gerekebilir.
- Aileler arası örtüşme yüksek: test bütçesi için kümeleme önerilir (Fable riski 3).

## Devam noktası (tur 3)
1. `belirsiz` kalan ~120 satır (103 + 19) ve kaynağı açılmadan reddedilen 13 grup-5 adayı.
2. `kod_yok` kalan 277 satırın URL'si olmayanları için kaynak linki bulunmalı (k00 MASTER satırları, blog/forum satırları).
3. Okunamayan makaleler (MDPI JRFM 19/9/692, Springer Brauneis, Ledger 213, Han-Kang-Ryu): kullanıcı metin sağlarsa denenir.
4. Aile kümelemesi: 144 kartı ailelere ayırıp temsilci seçmek (kod yazmadan, kart düzeyinde).

---

# Tur 3 (2026-11-11)
Tur 1-2 metnine ve dosyalarına dokunulmadı; yalnız dosya/satır eklendi. Çalışma sırasında tur 2 (PR #22) main'e birleşti; bu PR'ın farkı yalnız tur 3'tür.

## 1. Aile kümelemesi (`aileler_v3.csv`, 153 satır)
- 153 kart (144 + tur 3'ün 9 yeni kartı) **34 aileye** ayrıldı; **10 aile temsilcisi** seçildi (her aileden en çok 1-2; önce Fable puanı, sonra kural netliği, sonra kanıt; havuzdaki bir stratejinin küçük varyantı ve `veri_uygun=false` kart temsilci olamaz). Her kart için havuzdaki en yakın strateji (`havuz_v2` / `dis_envanter`) ve fark özeti yazıldı.
- Taslak Sonnet ajanıyla yapıldı, **Fable bir kez gözden geçirdi** (3 temsilci değişikliği, 5 aile düzeltmesi, ~20 `havuzda_en_yakin` düzeltmesi; yanlış/olmayan havuz adları grep ile doğrulanıp düzeltildi).
- En kalabalık aileler: kesit-momentum 12, donchian-kirilim 10, orb-seans-kirilim 8-9, rsi-trend-geri-cekilme 8, gun-takvim-olay 7, varlik-tahsis-rotasyon 7. **22 aile temsilcisiz** (hepsi havuz varyantı ya da verisi olmayan kartlardan oluşuyor).
- **Temsilciler (10):** donchian-ansambl-vol-hedef__zarattini (7), funding-7g-haftalik-tercil__vine (7), saatlik-asiri-tepki-tersine__denicola (6), gunici-momentum-noise-alani__zarattini (6; `veri_uygun=false` olmasına rağmen bilinçli istisna: DK_SPX ile test edilebilir, kabul edilmezse `hayir` yapılmalı), fip-kesitsel-momentum__baptoudur (5), btc-gecelik-max10-hafta-sonu__dujava (5), vol-yonetimli-long__moreira (5), cuma-15-est-tutma-saatlik__miralles (4), kripto-max-piyango-kesit__ozdamar (4), pre-fomc-surunme__delphic (4).
- **Test bütçesi önerileri (Fable):** (1) çekirdek 7 + yedek 3: önce Fable ≥ 5 olan yedi temsilci (dördü zaten kodlu: donchian-ansambl, funding-7g-tercil, saatlik-asiri-tepki, FIP; üçü yeni kod ister: noise-area, btc-gecelik-max10, vol-yonetimli-long); Fable 4 olan üçü (kripto-MAX, cuma-15, pre-FOMC) bütçe kalırsa, ilk elenecekler cuma-15 (168 hücreden veri kazıma) ve pre-FOMC (yılda ~8 işlem). (2) Kodlanmış ama temsilci olmayan varyantlara (saat-21-23, volatilite-kirilim-k05, asya-kutu, aralik-kirilim, orb-4s, adaptivetrend, funding-decil, funding-z90, kirmizi-mum, l-sekli, haftalik-trix) resmi ön kayıtta yeni deneme hakkı harcanmasın; kısa-vade kesit momentum (Fable 6) yeni kod olmadan mevcut `pf__kesit_ls` sınıfının tek ön-sabitlenmiş ayarı olarak koşturulabilir. (3) Serbest parametreler ön kayıtta tek değere sabitlensin (saatlik-asiri-tepki eşik/tutma, donchian-ansambl geriye bakış listesi, noise-area bant formülü); kesit kartlarında 13-15 coinde decil/quintil yerine tercil ve tek ayar; vol-yonetimli-long strateji olarak değil, mevcut set üzerinde boyut katmanı olarak ölçülsün.
- Fable ayrıca `veri_uygun` işaretlerinin FOMC, opsiyon vadesi, tatil öncesi kartlarında fazla kötümser olduğunu (DK_SPX var), gap-z-fade kartında ise fazla iyimser olduğunu not etti.

## 2. Kaynağı açılmadan reddedilenler ve sınırdaki retler (`on_eleme_tur3_gorev2.csv`, 19 satır)
Tur 2'de açılmadan reddedilen 13 grup-5 adayı + sınırdaki retler yeniden açıldı: **6 kart** (alligator-HA-zigzag, kesit-bosluk-z-fade, xunxuntj Supertrend CHOP/ER, tomasbatovsky momentum itkisi, tranduy216 MA hizalama [yalnız canlı kural], abbujo seans tepe/dip), 10 tekrar, 2 yasak (S4 RSI2 tüm örneklemde rank = lookahead; trad_bot_pi42 ortalama düşürme), 1 kod_yok. Dönen kararlar `REDDEDILENLER_tur3.txt`'de.

## 3. `belirsiz` satırlar (`on_eleme_tur3.csv`, 122 satır = tur 2'nin 103 + Gemini 19)
Hepsi Haiku ajanlarıyla kaynağı açılarak yeniden karara bağlandı: tekrar 34, yasak 26, kod_yok 24, kart 17, veri_yok 12, arac 8, belirsiz 1 (yalnız gerçekten okunamayan). Kart çıkan 17 satırın birleştirilmesi ve aile kontrolünden sonra **3 kart** yazıldı (hacim-delta-vekil, KamaFama_2, stokastik-ters-mum); 14'ü, ailesi dolu ve havuz/tur 1-2 kartlarının küçük varyantı olduğu için `REDDEDILENLER_tur3.txt`'ye gitti (27 satır).

## 4. Yeni kartlar ve Fable
Tur 3'te **9 yeni kart** (toplam **153**; `adaylar.csv` 153 satır). Fable yalnız yeni 9 kartı puanladı (`fable_hakem.csv`'ye eklendi): puanlar 1-3, hiçbiri ilk_20 eşiğini (≥ 5) geçmedi, hiçbiri aile temsilcisi olmadı. `oncelik` = 3. Tur 3 yeni kartların güçlü yanı yok: kaynağın kendi testi çoğunda olumsuz/küçük örneklem (alligator PF 0,69; hacim-delta 9 işlem -%4; momentum itkisi 13 işlem), %25 sabit stop, hata içeren kaynak kod (stokastik kartı).

## Dürüst sınırlar (tur 3)
- Bu turda yeni web taraması yapılmadı (talimat). Aile kümelemesi kart özetlerine dayanıyor; ajan bazı kartların yalnız özetini okudu, asıl JSON'larını değil.
- "Küçük varyant = tekrar" kararlarının çoğu ajan yargısıdır. Sınırdaki örnekler: Sqetchii XAU sweep-reversal, dipayansamanta Fib-FVG, viki-m13/bonds BTC SMA200, gagandocx EMA/ADX (hepsi `tekrar` yazıldı; kart yapılabilir).
- `kod_yok`'ta kalan 277 satırın URL'siz olanları için kaynak linki hâlâ bulunamadı; tur 2'nin bu sınırı geçerli.
- Fable puanları kart metnine göre; kaynaklar açılmadı.
- Hakem kümelemede bir istisna yaptı (noise-area temsilcisi `veri_uygun=false`); karar kullanıcıya/ana oturuma ait.

## Devam noktası (tur 4)
1. Kullanıcı/ana oturum: aile temsilcileri ve test bütçesi (çekirdek 7 + yedek 3) onayı; noise-area istisnası.
2. `kod_yok` kalan 277 satırın URL'siz olanları; okunamayan makaleler (MDPI JRFM 19/9/692, Springer Brauneis, Ledger 213, Han-Kang-Ryu).
3. Sınırdaki `tekrar` kararlarının (yukarıdaki 4) gözden geçirilmesi.

---

# Tur 4 (2026-11-11)
Önceki tur dosyalarına dokunulmadı; yalnız `kaynak_dogrulama_tur4.csv` (136 satır) ve `kanit_ozet_tur4.md` eklendi. Kod yazılmadı. Kaynakları 5 Sonnet ajanı okudu (kart başına iki), Fable gözden geçirdi. Haiku biçim kontrolü ayrı ajanla yapılmadı; CSV'yi betikle doğruladım (7 sütun, `uyum` değerleri geçerli).

## 1. Doğrulama sonucu (10 temsilci)
136 satır: 70 aynı, 38 farklı, 23 kaynakta yok, 5 kaynak okunamadı. Ayrıntı ve kanıt rakamları CSV ve `kanit_ozet_tur4.md` içinde.

## 2. Fable hükmü (kısa)
| Kart | Hüküm | Ön kayıtta kullanılacak |
|---|---|---|
| donchian-ansambl | Şüpheli (mevcut kodla); yeniden kodlanırsa test edilebilir | Kaynak değerleri: 9 pencere (5-360g, kapanış bazlı), ortalama ağırlık, orta-kanal iz stop, %25/σ90, %200 tavan, %20 eşik. Mevcut kod (20/55/100, 2/3 oy, ATR×3) kaynağın stratejisi DEĞİL; yeniden kodla ya da "bizim oylama varyantımız" diye adlandır |
| vol-yonetimli-long | İyi test edilebilir | Bizim uyarlama: ileriye bakmayan sabit hedef vol + tavan 1 (kaynağın c'si canlıda yok); hedef vol testten önce sabitlenir; kıyas al-tut |
| funding-7g-tercil | İyi test edilebilir, beklenti düşük (kaynak OOS Sharpe 0,39, PBO 0,81) | Kaynak: günlük toplanmış funding, 7g, 1g gecikme, tercil, haftalık, 6 bp/taraf, stopsuz. ATR stopu "bizim eklememiz" diye ayrı raporlanır. Testten önce: funding ızgarası (günlük toplam mı son settlement mı), motorun funding PnL'i, motor maliyeti |
| fip-kesitsel | Şüpheli; kaynakta sonuç yok, lisans belirsiz, asıl makale açılmadı | Kural kaynaktan (90g, %20, haftalık); min_sembol 2→5 düzeltmesi; eşikli dengeleme eklenmeyecekse sapma yazılır; funding için bizim gerçek funding |
| cuma-15 | Şüpheli (hücre kayan-pencereyle seçilmiş, OOS ve maliyet yok) | Giriş 16:00 EST = 21:00 UTC, 4 saat tutma, sabit UTC-5; kartın "kaynak tutarsız" notu yanlış |
| btc-gecelik-max10 | Şüpheli (blog, tablolar okunamadı, gece seçimi örneklem içi) | Kaynaktaki N=10, Cuma/Pazartesi/Salı geceleri, yeniden giriş; MAX tanımı ve DST/tatil boşlukları testten önce tek değere sabitlenir (varsayım diye işaretli) |
| kripto-max | Şüpheli, elenmeye en yakın (etki küçük coinlerde; evrenimizde yok) | 28 gün kayan pencere, haftalık; dilim ve evren sapması yazılır |
| pre-FOMC | Şüpheli (yılda ~8 işlem; zayıflama literatürü doğrulanmadı) | Kaynak aslında Lucca-Moench; Delphic yazısı bulunamadı. Planlı FOMC, olay başına duyuru saati takvimi; 2016+ ayrı raporlanır |
| saatlik-asiri-tepki | Şüpheli (kaynak teyitsiz) | Birincil metin okunana kadar test bekletilir (öneri) ya da "özete dayalı bizim saatlik hipotezimiz" diye kaydedilir. İkincil kaynak: 5 dk, 2σ, tek periyot; kart 1 saat |
| noise-area | İyi test edilebilir (hacim verisi şartıyla) | VM=1, 14 gün (optimize 1,5/90 kullanılmaz), 30 dk, yalnız bant girişi, max(UB,VWAP) iz stop, 16:00 çıkış; ana koşu sabit %100 boyut, dinamik ikincil |

## 3. En kritik 5 bulgu
1. DonchianAnsambl kodu kaynağın stratejisi değil.
2. saatlik-asiri-tepki'de zaman ölçeği (5 dk / 1 saat) teyitsiz.
3. funding-7g testi iki doğrulanmamış altyapı noktasına bağlı (funding ızgarası, funding PnL).
4. Eklenen ATR stopları (funding, FIP, asiri-tepki, donchian) hiçbir kaynakta yok; ön kayıtta "bizim eklememiz" diye yazılmalı, stopsuz koşu da raporlanmalı.
5. Evren darlığı (13-15 coin) dört kesitsel kartta zorunlu sapma; 10 kaynağın 8'inde gerçek OOS yok, çoğunda maliyet yok.

## 4. Kart düzeltme önerileri (kart dosyalarına dokunulmadı; ana oturum karar verir)
- noise-area: "bant formülü yok" ve "çıkış açık değil" notları yanlış (ikisi de makalede var).
- cuma-15: olay saati tanımı eklenmeli; "kaynak tutarsız" kalkmalı.
- btc-gecelik: maliyet "okunamadı" değil "kaynakta yok"; yeniden giriş eklenmeli; 35%/-12% MAX(10) açıklamasına ait.
- pre-FOMC: kaynak Lucca-Moench olarak atfedilmeli; "20 bp" 1980-1993 örneği, "54 bp" SPX sonucu (futures değil).
- kripto-max: pencere 30→28 gün.
- saatlik-asiri-tepki: "k kaynakta yok" yerine "ikincil kaynak 2σ"; birincil metin okunamadı notu.
- vol-yonetimli: "~%25 Sharpe artışı" ve Liu/Cederburg eleştirileri doğrulanamadı.
- donchian: "lookback listesi alınamadı" artık biliniyor; `aileler_v3.csv` özetindeki 20/55/100 kaynağa aykırı.

## Dürüst sınırlar (tur 4)
- Birincil metin okunamayanlar: De Nicola (Ledger; TLS/503/403), Delphic yazısı (bulunamadı), Da/Gurun/Warachka (açılmadı).
- Yalnız özet düzeyinde okunanlar: Vine paper2.html ve Dujava/Quantpedia blogu (WebFetch özeti); "baştan sona oku" şartı bu ikisinde karşılanmadı. FIP repo'su da dosya dosya özet olarak okundu.
- Sürüm riski: Donchian makalesi SSRN yerine yazarların sitesindeki revize sürümden, noise-area Şubat 2025 sürümünden okundu.
- Kod tarafı: motor gecikmesi, maliyeti, funding işleyişi, `Takvim.mom`, Pazartesi hizası kontrol edilmedi. 5 temsilci kodsuz; kodlanınca doğrulama tekrarlanmalı.
- `uyum` etiketleri yer yer tutarsız; ön kayıtta not sütununa bakılmalı.
- Madde 3 (yeni web taraması, yeni aile/daha güçlü kanıtlı aday) YAPILMADI; kart eklenmedi, `aileler_v3.csv`'ye satır eklenmedi. Sonraki tura kalır.

## Devam noktası (tur 5)
1. Gün içi kripto (5m-1h) ve funding/baz web taraması (yalnız yeni aile ya da daha güçlü kanıtlı aday).
2. De Nicola PDF'i (kullanıcı sağlarsa), Vine ve Quantpedia'nın tam metni.
3. DonchianAnsambl'in kaynağa göre yeniden kodlanıp kodlanmayacağı kararı (ana oturum/kullanıcı).

---

# Tur 7 (2026-11-11)
Önceki tur dosyalarına dokunulmadı; eklenenler: `veri/takvim/fomc.csv` + `veri/takvim/README.md` ve `stratejiler/v3_adaylar/on_kayit_girdi.csv`. Kod yazılmadı. **Bağımlılık:** `on_kayit_girdi.csv` tur 5 verisini (`kaynak_dogrulama_tur5.csv`, RAPOR Tur 5) PR #29 dalından (`claude/v3-tur5`) okuyarak üretildi; bu PR #29'dan bağımsız açıldı, ama içeriği #29'a dayanıyor (birleştirme sırası: #29, sonra bu). `RAPOR.md`'ye üç PR da ek yapıyor; sırayla birleşirken bölümler yan yana tutulmalı.

## 1. FOMC takvimi (`veri/takvim/fomc.csv`, 121 satır)
Kaynak federalreserve.gov (2013-2020 `fomchistorical<yıl>.htm`, 2021-2026 `fomccalendars.htm`, saatler her toplantının resmi basın bülteninden); çekme 2026-11-11. Sütunlar istenenler + iki ek (`tip`, `not`). Ayrıntı: `veri/takvim/README.md`.
- Yılda 8 planlı toplantı: 2013-2019 ve 2021-2026'nın hepsinde var (2026'nın Aralık toplantısı henüz yapılmadı: `planli_gelecek`). **2020'de 7:** 17-18 Mart iptal ("cancelled"), yerine 15 Mart (Pazar) plansız toplantı yapıldı.
- 110 planlı geçmiş + 5 plansız (2013-10-16, 2014-03-04, 2019-10, 2020-03-03, 2020-03-15) + 5 yazılı oylama (2020: 03-19, 03-23, 03-31, 08-27; 2025-08-22) + 1 gelecek.
- Saat yazılı: 86 toplantı 14:00 ET; 28 satır "bilinmiyor": **2013-2015'in 24 planlı toplantısı** (bültenlerde yalnız "For immediate release" yazıyor, tahmin edilmedi), 2 plansız konferans görüşmesi (sayfada açıklama yok), 2020-03-19 oylaması (bülten linki yok), 2026-12-09 (gelecek). aciklama_utc, yaz saati `America/New_York` ile hesaplandı; bültendeki EST/EDT kısaltması bununla uyumlu (uyumsuzluk yok).
- `basin_toplantisi` sayfada "Press Conference" linkinin varlığına göre; 2019-01'den itibaren her toplantıda var.
- Kullanım notu: pre-FOMC kartının "olay başına duyuru saati tablosu" 2016+ için artık hazır (2016+ planlı toplantıların tamamı 14:00 ET → KWG'ye göre pencere sonu 13:45 ET); 2013-2015 için saat henüz yok.

## 2. Ön kayıt girdi tablosu (`on_kayit_girdi.csv`, 205 satır, 10 kart)
İki Sonnet ajanı tur 4 + tur 5 csv'lerini, kartları, kanıt özetini ve RAPOR Fable kararlarını birleştirdi (tur 5, tur 4'ten yeniyse tur 5 kazandı); ben ÖNERİ satırlarını denetleyip düzelttim.
- `deger_kaynagi`: kaynak 131, bizim_varsayim 68, bizim_ekleme 6 (ATR stopları ve short-bacak raporu/ısınma eklemeleri).
- Her kart için `KANIT_OZETI` ve `ONERI` satırı var. 136 satırda `acik_soru` dolu.
- **44 satırda `on_kayit_degeri` = KARAR GEREKLI** (sayısal geçme eşiği, değerlendirme dönemi, maliyet, evren listesi vb. mevcut kayıtlarda yok; uydurulmadı). En çok: kripto-max 8, btc-gecelik 6, FIP 6, pre-FOMC 6, vol-yönetimli 5, saatlik-aşırı-tepki 4. Bu satırlarda `deger_kaynagi` yer tutucu olarak `bizim_varsayim` yazıldı (değer henüz yok, karar verilince bizim varsayımımız olacak); izin verilen üç değerden biri olsun diye.
- **ÖNERİ satırlarında düzeltme:** parça B ajanı Fable'ın açık hüküm vermediği kartlara "test et" yazmıştı. Fable'ın açıkça "test et/beklet" dediği kartlar kaldı: cuma-15 (tek ucuz ön kayıtlı test), noise-area, vol-yönetimli, funding-7g ("iyi test edilebilir"), saatlik-aşırı-tepki ("beklet"), donchian ("yeniden kodla/adlandır, sonra test"). **btc-gecelik, FIP, kripto-max, pre-FOMC için ÖNERİ = "KARAR GEREKLI (Fable açık test et/beklet demedi)"**; Fable hükmü metinde duruyor.
- Çelişkiler `acik_soru`'da: FIP dilimi (Tur 3 tercil / Tur 4 kaynak %20; sonraki tur esas alındı), kripto-max dilimi (3-4 coin / tercil), pre-FOMC 2013-2015 saati, funding-7g günlük-toplam kod değişikliği kararı, donchian izleyen stop ile motorun stopsuz hedef açmaması, noise-area VWAP tanımı.

## Dürüst sınırlar (tur 7)
- Takvim yalnız resmi sayfalardan ayrıştırıldı; sayfa yapısı değişirse yeniden üretmek gerekir (ayrıştırma betiği repoda yok). `basin_toplantisi` link varlığından türetildi.
- 2013-2015 duyuru saatleri bilinmiyor; literatürde saatin 2011 sonrası değiştiği geçiyor (doğrulanmadı).
- `on_kayit_girdi.csv` bir birleştirme: yeni karar yok; ajanlar motor kodunu yeniden okumadı (yalnız tur 4/5 csv'lerindeki aktarımlar). Tur 5 verisi henüz `main`'de olmadığı için dosya #29 birleşmeden bağımsız doğrulanamaz.
- Tablo ön kayıt değildir; ön kayıt kararı (KARAR GEREKLI satırları) kullanıcı ve ana oturumda.
