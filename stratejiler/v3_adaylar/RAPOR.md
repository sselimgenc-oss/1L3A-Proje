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
