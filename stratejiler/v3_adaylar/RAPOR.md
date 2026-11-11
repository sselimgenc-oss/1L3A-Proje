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
