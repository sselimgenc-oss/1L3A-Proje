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

# Tur 5 (2026-11-11)
Önceki tur dosyalarına dokunulmadı; yalnız `kaynak_dogrulama_tur5.csv` (60 satır) ve `yeni_aday_taramasi_tur5.md` eklendi, bu bölüm eklendi. Kod yazılmadı. 4 Sonnet ajanı okudu/taradı, Fable hakem oldu. Kart dosyalarına, `adaylar.csv` ve `aileler_v3.csv`'ye dokunulmadı (yeni kart yok).

## 1. Açık kaynaklar (kaynak_dogrulama_tur5.csv)
60 satır: 12 aynı, 16 farklı, 20 kaynakta yok, 12 kaynak okunamadı.
- **De Nicola (Ledger):** birincil metin yine OKUNAMADI (ledger.pitt.edu TLS/503; Unpaywall/Crossref/OpenAlex yalnız meta; SSRN/CORE/Europe PMC proxy 403; web.archive tünel koptu). Zaman ölçeği, eşik, tutma, maliyet, OOS hâlâ ikincil kaynağa dayanıyor. PDF'i kullanıcı tarayıcıdan indirip sağlarsa okunur.
- **pre-FOMC:** kripto uyarlaması bulunamadı. Lucca-Moench ana pencere 14:00→14:00 (duyuru 14:15, 1994-2011, 49 bp); 2011 sonrası pencere sonu 13:45 (KWG 2021); KWG: drift 2015 sonrası "essentially disappeared". FOMC tarihleri federalreserve.gov'dan alınabilir (2015-2020 yıllık sayfalar, 2021+ takvim); plansız toplantı = tek günlük conference call / notation vote. Olay başına duyuru saati tablosu henüz çıkarılmadı.
- **btc-gecelik (Quantpedia, tablo görselleri okundu):** nihai gece-only strateji tüm örnek CAR %68,38, Sharpe 2,40, MDD %-17,24; IS Sharpe 2,15; OOS (2021-10-18 sonrası) CAR %20,09, Sharpe 1,14, MDD %-11,17. Kartın "%35 / -%12" tüm-gün MAX(10) stratejisine ait (OOS %35,65). Maliyet ve işlem sayısı yok. N=5'in Sharpe'ı N=10'dan yüksek.
- **cuma-15 (Miralles):** Tablo 7: Cuma 15:00 sonrası 4s ort. +0,0038 log (t=3,98), komşu hücreler de anlamlı. Toplam ~1680 t-testi (168 + 1512; sayı tablolardan hesaplandı), düzeltme yok. Sharpe yalnız grafikte (Şekil 2-3 görsel tahmin; kanıt alanına yazılmaz). Çalışma kâğıdı bulunamadı.
- **donchian-ansambl (Zarattini):** ağırlık = 9 modelin eşit ortalaması, model başına min(0,25/σ; %200); %20 eşik yalnız vol ayarında; ay sonu evren + 1/B sermaye; evren filtresi ≥365 gün listeli + 30g medyan hacim ≥2 milyon USD; sinyal kapanışta, aynı kapanış fiyatından icra (ek gecikme yok); 365/252 yazmıyor; maliyet 10 bps (tek yön/gidiş-dönüş yazmıyor); long-short Combo Sharpe 1,31 (long-only 1,58). Sürüm ayrımı (Nisan/Ekim 2025) PDF'ten yapılamadı.
- **funding-7g (Vine + motor):** kaynak = günlük settlement TOPLAMI, 7 günlük ortalama, 1 gün kaydırma; son ödeme DEĞİL. Motor (`motor/strateji/funding.py:6-9,37-51`) mum kapanışındaki SON settlement'ı ffill ediyor → 1d barda günün yalnız 00:00 ödemesi sinyale giriyor. Motor funding PnL'i ise settlement başına gerçek perp fiyatıyla işliyor (kaynaktan daha gerçekçi). `Funding7gTercil` varsayılan evreni 3 coin (BTC/ETH/SOL): 13-15 coin çağrıda açıkça verilmeli. Vine repo'su okunamadı.

## 2. Yeni aday taraması (madde 3)
**Bulunamadı.** 17 arama + 8 sayfa; hiçbir aday yeni aile getirmedi ya da mevcut temsilciden daha güçlü kanıtlı (makale + OOS + maliyet dahil + verimize uygun) değildi. Ayrıntı: `yeni_aday_taramasi_tur5.md`. Fable: sonuç makul ve TALIMAT'ın izin verdiği türde, ama kapsam dar; doğru ifade "bu erişimle bulunamadı", "literatürde yok" denemez. Yan bulgu: Han-Kang-Ryu (özet) ve Bianchi vd. (tam metin) kesit momentum/ters dönüş kazancının maliyetten sonra küçüldüğünü ya da illikit coinlerde toplandığını söylüyor.

## 3. Fable hükmü: ön kayıtta hangi değer
| Kart | Ön kayıt kararı |
|---|---|
| saatlik-asiri-tepki | **Test bekletilsin** (birincil metin yok). Koşulacaksa tek koşu: 1 saat, k=2, tut=1, adı "özete dayalı bizim saatlik hipotezimiz"; 48 mum σ ve ATR×2 bizim eklememiz. 5 dk ile 1 saati birlikte koşup iyisini seçmek yasak |
| pre-FOMC | Ana koşu = kaynak penceresi (giriş duyurudan 24s15dk önce, çıkış duyurudan 15 dk önce; 2011 sonrası 13:45). Kartın sabit 14:00 çıkışı kullanılmaz; kapanış→13:45 yalnız ikincil. Olay başına duyuru saati tablosu testten önce çıkarılır; plansız toplantı dışlanır; 2016+ ayrı raporlanır (beklenti ~0); geçme ölçütü önceden yazılır; karttaki "20 bp" yerine 49 bp (1994-2011) |
| btc-gecelik | Kaynak kuralları (N=10, Cuma/Pzt/Salı geceleri, yeniden giriş); kanıt alanı nihai OOS Sharpe 1,14 (maliyetsiz) ile düzeltilir; N optimize edilmez; temiz sınav 2024-10-15 sonrası; "tüm geceler" yalnız dayanıklılık satırı; MAX tanımı/DST/tatil tek değere sabitlenir |
| cuma-15 | Elenmeye yakın ama tek ucuz ön kayıtlı test: yalnız tek hücre (Cuma 21:00 UTC giriş, 4 saat, sabit UTC-5); komşu saat/ufuk denenmez; karar dönemi 2022+; net pozitif değilse aile kapanır. (Fable'ın kaba Bonferroni eşiği ~4,2 > t=3,98.) |
| donchian-ansambl | Mevcut kod kaynağın stratejisi değil → kaynağa göre yeniden kodla ya da "bizim oylama varyantımız" diye adlandır. Kaynak değerleri: 9 pencere, kapanış kanalı, orta-kanal iz stop, σ90, %20 eşik, ay sonu evren, long-only. İcra motorun "sonraki bar açılışı"nda kalsın (sapma beyanı). Yıllandırma 365 (252 pozisyonları ~%20 büyütür). Maliyet: motorun gerçekçi değeri + 10 bps tek yön duyarlılığı. Açık tasarım sorusu: motor stopsuz hedef açmıyor, kaynakta 9 iz süren stop var |
| funding-7g | Ana koşu = günlük toplam (kod değişikliği gerekir; karar ana oturum/kullanıcıda). Son-settlement sürümü aday olarak koşulmaz ("eski varyant" diye raporlanır). Karar koşusu stoplu (ATR×3, "bizim eklememiz"), stopsuz yalnız kaynak kıyası. Evren 13-15 coin açıkça sabit; tek ayar (7g/tercil/haftalık); 6 bp/taraf hizalı kıyas koşusu; beklenti düşük (kaynak OOS Sharpe 0,39) |
Kesitsel kartlarda (funding-7g, fip, kripto-max, donchian çoklu coin) karar ölçütü maliyet sonrası net sonuç olmalı; maliyet duyarlılık satırı ve short bacak ayrı rapor. Bianchi'nin 20-40 bp'si küçük/illikit coinler içindir, üst stres değeri olarak kullanılır.

## 4. Kritik 5 madde
1. Funding sinyali kaynakla aynı değil (son settlement) ve varsayılan evren 3 coin: ikisi düzelmeden funding-7g testi kaynağı sınamaz.
2. Donchian yeniden kodlanmadan kaynağa atfedilemez; yıllandırma, stop seçimi, maliyet testten önce yazılmalı.
3. De Nicola birincil metni hâlâ yok; test bekletilmeli.
4. pre-FOMC'de duyuru saati tablosu çıkarılmadı; sabit 14:00 çıkış hatalı; 2016+ beklenti sıfıra yakın.
5. btc-gecelik ve cuma-15'te kanıt maliyetsiz ve seçim örnek içi; karar yalnız örnek sonrası dönemde, tek ön kayıtlı ayarla.

## Dürüst sınırlar (tur 5)
- İkincil kaynaklar: De Nicola tamamen ikincil; KWG metni ikincil kopya (tablolar kısmen bozuk; 0,092/0,054 birimi doğrulanmadı); Lucca-Moench 49 bp teyidi bir substack'ten; ardıl makalelerin yalnız başlıkları var.
- Görselden okunan rakamlar (Quantpedia tabloları, Miralles Şekil 2-3) aktarım hatası taşıyabilir; bir Quantpedia tablosunda kaynak hatası şüphesi var (Vol rakamları tutarsız).
- 1680 test sayısı ve Bonferroni eşiği tablolardan/hakemden hesaplanan çıkarımlardır, kaynakta yazmıyor.
- Vine repo'su ve lisansı okunamadı (GitHub erişimi); Vine'ın walk-forward ayrıntıları yok, OOS yeniden üretilemez.
- Motor tarafında yalnız funding yolu satır satır okundu; donchian icra gecikmesi ve motorun gerçek maliyet düzeyi doğrulanmadı.
- `uyum` etiketleri yer yer tutarsız (btc-gecelik kartının "%35"i bir satırda "ayni", başka satırda "farkli"); not sütunu esas alınmalı.
- Yeni aday taraması dar kapsamlıydı (Han-Kang-Ryu, Guo vd., Kurihara yalnız özet).

## Devam noktası
1. Kullanıcı: De Nicola PDF'i (Ledger, tarayıcıdan), funding günlük-toplam kod değişikliği ve donchian yeniden kodlama kararları.
2. pre-FOMC duyuru saati tablosunun federalreserve.gov'dan çıkarılması.
3. Tur 6 (veri_yok etiketleme) ayrı PR.

# Tur 6 (2026-11-11)
Önceki tur dosyalarına dokunulmadı; yalnız `veri_yok_etiket_tur6.csv` (514 satır) eklendi, bu bölüm eklendi. Kod ve kart yazılmadı. Etiketleme 13 Haiku ajanıyla yapıldı (derin okuma yok), 30 satırı Sonnet kontrol etti; Fable kullanılmadı.

## 1. Girdi
`on_eleme.csv`, `on_eleme_tur2_kod_yok.csv`, `on_eleme_tur3.csv` içinde son kararı `veri_yok` olan satırlar (aynı aday birden çok dosyada geçiyorsa (url, ad) anahtarıyla tek satır; son tur kazanır) = **485**, + `kodlama_v3.csv` durum=veri_yok **29 kart** = **514 satır**. Talimattaki "~636" ham toplamdı; tekilleştirme ve sonraki turun karar değiştirmesi farkı açıklıyor. Her satır için tam bir çıktı satırı var (girdi-çıktı sırası ve `kaynak_dosya`+satır numarası eşleşmesi doğrulandı). Parça 12'de ajan 32 satırın `ad` metnini kısaltıp çevirmişti; `ad` girdiden geri yazıldı.

## 2. Örnek kontrol (Sonnet, 30 rastgele satır)
- Kesin hata: **0/30 (%0)**; alan bazında 0. Belirsiz: 1 (TSLA satırı: Binance'te ABD hisse perp'i olabilir; etiket tanımı "kripto perp" olduğu için hata sayılmadı).
- Kaçırılan ("bilinmiyor" ama netleşebilir): 4 satır / 6 alan (ücretsiz 3, geçmiş 1, işlem-bizde 2).
- **Uyarı:** Sonnet de URL açmadı, yalnız `neden`/`ad`/bağlam ile yargıladı; bu nedenle %0 hata "etiketler kaynakla doğrulandı" demek DEĞİL, "metinle tutarlı" demektir.
- Sistematik zayıflık: `ucretsiz_kaynak` (426/514) ve `gecmis_yeterli` (459/514) çoğunlukla **bilinmiyor**; bu iki alan eksik dolduruldu.

## 3. Özet tablo
`3 kriter de evet` = ucretsiz_kaynak=evet VE gecmis_yeterli=evet VE bizde_islenebilir=evet.

| gereken_veri | toplam aday | 3 kriter de evet | işlem bizde: hayır | işlem bizde: evet/bilinmiyor | en sık 3 veri_ayrinti |
|---|---|---|---|---|---|
| hisse_fiyat | 115 | 0 | 91 | 24 | jse top 100 hisse günlük fiyat (5); sh510300 (çin csi300 etf) günlük fiyat (3); nse hisse ohlcv (2) |
| hisse_temel | 63 | 0 | 52 | 11 | kazanç sürprizi + açıklama tarihi (2); tahakkuk (bilanço kalemleri) (1); bilanço varlık büyümesi (1) |
| opsiyon | 60 | 0 | 59 | 1 | opsiyon zinciri (2); nifty opsiyon zinciri (2); iron condor opsiyon zinciri (2) |
| diger | 55 | 1 | 37 | 18 | çin konvertibl tahvil fiyat ve prim (4); esg puanı + fiyat momentumu (2); açık short (short interest) verisi (2) |
| forex | 49 | 0 | 49 | 0 | eurusd 5dk (mt5) (2); eurusd m5 (2); kur geçmişi (majör çiftler) (1) |
| endeks | 44 | 0 | 42 | 2 | dünya hisse endeksleri (ülke) (1); ülke endeksleri (1); imoex vadeli 10dk (1) |
| alt_1dk | 44 | 1 | 25 | 19 | krx hisse 1 dk ohlcv (6); dakikalık ohlcv ve hacim (vwap) (1); m3/m5 tetik, 5 dk altı zaman dilimi (mt5) (1) |
| haber_duygu | 24 | 0 | 9 | 15 | şirket bildirim metinleri (10-k/8-k) (1); piyasa duygu endeksi (1); kazanç çağrısı transkriptleri (metin) (1) |
| emir_defteri | 24 | 1 | 17 | 7 | lob ve tick verisi (hft, market making) (1); binance-upbit fiyat ve emir defteri (1); emir defteri dengesizligi (1) |
| vadeli_emtia | 14 | 0 | 10 | 4 | vix vadeli kontrat eğrisi (1); çoklu vade emtia kontrat eğrisi (1); altın (xau) tik ve intraday fiyat (1) |
| onchain | 12 | 0 | 11 | 1 | pump.fun memecoin on-chain akisi (1); on-chain ve duyarlilik verisi (1); solana dex ve on-chain fonlama (1) |
| makro_takvim | 10 | 0 | 2 | 8 | fred: cpi, ppi, cfnai, reel faiz, vix (1); politika faizi, cpi ve doviz paritesi (1); vix, kredi spreadi, faiz serileri (1) |

Genel: bizde_islenebilir = hayır **404**, bilinmiyor **96**, evet **14**; ücretsiz_kaynak evet 61 / hayır 27 / bilinmiyor 426; geçmiş_yeterli evet 46 / hayır 9 / bilinmiyor 459. **Üç kriterin hepsi evet olan yalnız 3 satır** var.

## 4. Ana bulgu ve öneri (karar kullanıcı ve ana oturumda)
**Darboğaz çoğunlukla veri değil, işlem piyasası:** 514 adayın 404'ü (%79) işlemini hisse/forex/opsiyon/endeks/vadeli gibi bizim açamadığımız bir piyasada yapıyor (forex 49/49, opsiyon 59/60, endeks 42/44, hisse 143/178 "hayır"). Bu adaylara veri eklemek onları açmaz.

Etiketleri "işlem bizde evet/bilinmiyor" olan satırlara göre sıralarsak en çok aday açabilecek 3 veri ihtiyacı (hepsi düşük-orta güven; ücretsizlik/geçmiş alanları çoğunlukla doğrulanmadı):
1. **makro_takvim (8 aday; en yüksek güven):** FRED serileri (CPI/PPI/faiz/VIX/kredi spreadi) + federalreserve.gov FOMC takvimi (aynı veri pre-FOMC kartının duyuru saati tablosunu da açar). Ücretsiz, geçmiş uzun. FRED anahtarı gerekir (anahtar repoya girmez).
2. **alt_1dk (19 aday):** çoğu dakikalık Binance/kripto verisi; Binance arşivi (`data.binance.vision`) 1 dk veriyi zaten ücretsiz sunuyor. ENGEL: DURUM.md karar 3 min zaman dilimini 5 dk yapıyor; bu adaylar ancak bu karar değişirse açılır. (KRX 1 dk gibi hisse satırları dahil değil; "evet/bilinmiyor" içinde karışık.)
3. **haber_duygu (15 aday; düşük güven):** çoğu ücretli ya da bilinmiyor (haber/duygu/transkript); kripto duygu endeksi gibi bir ücretsiz kaynak olabilir ama doğrulanmadı. "diger" kategorisi (18 evet/bilinmiyor) heterojen, tek veri kaynağı önerilemedi.
Önerim: önce 1'i (ucuz, belirgin), 2 için karar 3'ü kullanıcıyla konuş, 3'ü açmadan önce kaynakları gerçekten kontrol et.

## Dürüst sınırlar (tur 6)
- Etiketler yalnız `neden`/`ad` metnine dayanıyor (derin okuma yok; URL çoğunlukla açılmadı). Ücretsiz/geçmiş alanları çoğu satırda bilinmiyor; tablodaki "3 kriter de evet" sayıları bu yüzden alt sınırdır, gerçek sayı daha yüksek olabilir.
- Hisse satırlarında "işlem bizde hayır" kararı Binance'in ABD hisse/emtia perp'leri (DURUM.md karar 6) göz ardı edilerek verilmiş olabilir: ABD hisse/endeks/emtia geçen ~13 hisse satırı bu açıdan tartışmalı. Dukascopy hisse verisi zaten var; bu satırlar "veri_yok" yerine başka bir engelle (ör. temel veri, çok sembol) elenmiş olabilir.
- "Tekilleştirme" anahtarı (url, ad); aynı strateji farklı adlarla geçiyorsa mükerrer kalmış olabilir (örn. Asya satır 35 ile 15 aynı makale).
- Birkaç satırda ajan kaynak tahmini yaptı (ör. Binance public veri, Ken French kütüphanesi) ve notta belirtti; doğrulanmadı.
- Bir repoda açık FRED API anahtarı görüldü (satır "quant-macro"); değer kopyalanmadı, depo sahibinin iptal etmesi gerekebilir.
- Yasak kategoriler (ML, HMM, genetik algoritma, ortalama düşürme şüphesi) etiketlendi ama notta işaretlendi; ayrıca dışarıda bırakılmadı.

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

---

# Tur 8 (2026-11-11)
Kod-kaynak çapraz kontrolü. Güncel `main` (PR #31 ve #32 dahil) üzerinden; **kod değiştirilmedi**, yalnız `kod_kontrol_tur8.csv` (139 satır) eklendi. 4 Sonnet ajanı kodlanmış sürümleri satır satır okudu (sentetik veriyle küçük denemeler yaptılar, repoya yazmadılar), Fable ajan iddialarını koddan doğrulayıp sıraladı.

## 1. Kapsam
7 kodlu temsilci: donchian (`pf__v3-donchian-ansambl`), vol-yönetimli (`pf__v3-vol-yonetimli-long`), funding-7g (`funding_gunluk_toplam` ile), FIP, noise-alanı (`v3_adaylar_4.py`), btc-gecelik, saatlik-aşırı-tepki. **cuma-15, kripto-max ve pre-FOMC'nin kodu yok** (1'er `kodda_yok` satırı; kod yazılmadan test edilemez).

## 2. Sonuç
139 satır: **ayni 74, farkli 21, kodda_yok 11, belirsiz 33**. Önem: yüksek 11 (farklı 8, kodda_yok 1, belirsiz 2), orta 34, düşük 94. `farkli` ve `kodda_yok` satırlarının hepsinde önem gerekçesi `not` sütununda. **Lookahead: hiçbir kodlanmış temsilcide bulunmadı** (donchian ve vol-yönetimli ilk 500 günü kısaltma/Mart fiyatını x4 yapma denemesiyle, funding-7g sentetik testle; noise-alanı ve btc-gecelik shift/cumsum kod okumasıyla).

## 3. Test sonucunu en çok değiştirecek 5 fark (Fable sıralaması; "düzelt" kararı kullanıcıda)
1. **noise-alanı:** giriş anındaki max(üst bant, VWAP) motora **sabit mum-içi stop** olarak veriliyor (kaynakta yalnız yarım saatlik kontrolde cari bantla karşılaştırılır); boyut %1 risk / dar stop mesafesi (3x tavan), ön kayıt sabit %100; fitil değmesi çıkış tetikler (+5 bps), kapanış hâlâ bant dışındaysa aynı gün yeniden giriş. Gün sonu çıkışı 15:30 mumunda `cikis=True`, dolum sonraki açılışta (veri yalnız seans mumlarıysa gece tutma; veri bu ortamda yok, doğrulanamadı). → **DÜZELT (test öncesi)**.
2. **FIP:** kod skoru `işaret(mom90) × (pozitif gün − negatif gün)/90` (kartla aynı); ama düzgün DÜŞEN coin +1 alıp long oluyor, yani sıralama "momentum" değil "düzgünlük". Da-Gurun-Warachka'da (açılmadı, hafızadan) ID momentuma göre sıralı gruplar içinde kullanılır. → **kaynak doğrulanmadan "FIP momentum" diye koşulmamalı**; doğrulanamazsa "bizim düzgünlük sıralamamız" diye beyan.
3. **btc-gecelik:** 1 saatlik ATR(14)×2 **sabit** stop (kaynak stopsuz; 18-66 saatlik tutuşta dar) ve MAX(10) tanımı = önceki 10 NY takvim gününün en yüksek **HIGH**'ı (ön kayıt: 16:00 **kapanışı** ≥ önceki 10 günün en yüksek 16:00 kapanışı; kod daha sıkı). → **DÜZELT/tek değere bağla** (MAX için ucuz yol kodu ön kayda çekmek; stop için karar kullanıcıda).
4. **donchian:** ATR(14)×3 **iz süren** stop (kaynakta yok; zirve kapanıştan 3 ATR geri çekilme = tam çıkış), stop sonrası strateji modeli hâlâ long saydığı için yeniden giriş yalnız model değişince/%20 sapmada; sabit 13 sembol listesi (ay sonu evren seçimi, hacim/yaş filtresi yok: hayatta kalma yanlılığı). → stopsuz kaynak-sadık kıyas koşusu **ya da beyan**; sabit evren: veri kısıtı, "sonuç yukarı yanlı olabilir" beyanı.
5. **vol-yönetimli:** ağırlık `0,20 / (önceki takvim ayı günlük getiri STD'si × √252)`, tavan 1, 1/n: std'nin tersi (vol hedefleme), ön kayıt satırı "varyansın tersi" diyor (iç çelişki: Tur 4 Fable "sabit hedef vol + tavan 1" demişti, kod buna uyuyor); √252 kriptoya da uygulanmış (kripto vol'ü ~%17 düşük ölçülür); ATR×2 iz süren stop sonrası pozisyon ay sonuna kadar nakitte. Ön kayıtta "boyut katmanı", kodda bağımsız strateji. → ön kayıt satırı düzeltilerek **beyan**, kripto için 365 küçük bir düzeltme adayı, stopsuz kıyas satırı.
Hemen ardından: **funding-7g ve FIP'te portföy motorunun %5 toplam stop riski kırpması** (ATR×3 stopla fiili brüt kabaca 0,3-0,55; hedef "brüt 1,0") ve `zarar_buyutme` hedefi aşağı çekiyor; Sharpe ölçekten büyük ölçüde bağımsız, mutlak getiri/MDD ve sayısal eşikler etkilenir → ön kayıtta beyan.

## 4. Eskimiş ön kayıt satırları (PR #32 sonrası)
funding-7g günlük toplam artık kodda (`funding_gunluk_toplam`; Tur 4/5 "farklı" hükmü eskidi), evren 13 coin (kayıttaki "varsayılan 3 coin" eskidi), `min_periods` kayıtta 2 / kodda 7, `min_sembol` funding-7g'de 2 (FIP'te 5). Pazartesi hizası ve `Takvim.mom`'un skip içermediği teyit edildi. Zamanlama temiz: funding-7g skoru t-7..t-1 barlarının ortalaması, dolum Salı 00:00 (efektif 1 gün gecikme + 1 bar dolum).

## Dürüst sınırlar (tur 8)
- **Gerçek veriyle hiçbir koşu yok** (`veri/mumlar` bu ortamda yok); ajanların sayıları (fiili brüt, kırpma adetleri, stop çıkışı oranı) sentetik veriden; Fable'ın büyüklük tahminleri kaba el hesabı. "Sonucu ne kadar değiştirir" sıralaması yargıdır, ölçüm değil.
- Fable'ın okumadığı: saatlik-aşırı-tepki sınıfı (`v3_adaylar.py`; ajan D kodu okudu: lookahead yok, dolum sonraki açılış, ciddi hata yok), `funding.py` gövdesi, koşu betikleri/maliyet tablosu, veri hazırlama katmanı, testler. Bu satırlardaki ajan iddiaları Fable tarafından doğrulanmadı.
- 74 `ayni` satır tek tek denetlenmedi; kaynak cümleleri Tur 4/5 aktarımlarına dayanıyor (Quantpedia/Vine özet düzeyinde, Da-Gurun-Warachka açılmadı, De Nicola birincil metni yok).
- Ajan etiketleri yer yer tutarsız: `kodda_yok` hem "kart kodlanmamış" hem "kaynakta olmayan kural kodda var" için kullanıldı; önem dereceleri ajanlar arasında aynı ölçüyle verilmedi (Fable vol-yönetimli stopunu "orta" yerine yüksek sayıyor).
- Koşuda fiilen hangi parametre/maliyet/evrenin geçeceği koşu betiğine bağlı; sınıf varsayılanlarını doğrulamak koşuyu doğrulamak değildir.
