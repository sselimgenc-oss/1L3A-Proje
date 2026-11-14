# G8 kod denetimi (bağımsız hakem) — 2026-11-13

Kapsam: `motor/strateji/kapanis/kod_g8_kod_1..8.py`, testleri, girdi CSV'leri. Gerçek veriyle koşu yapılmadı, sonuç görülmedi, repo değiştirilmedi.
Betikler: bu klasörde `butunluk.py`, `goster.py`, `lookahead.py`. Örneklem tablosu: `hakem_kod_ornek.csv` (32 sınıf, seed=13, dosya başına 4).

## Özet hüküm
- 8 dosyanın hepsi KABUL (yeniden yazım gerekmez). 32 örnek sınıfta kural dışı ekleme ya da eksik koşul bulunmadı; 2 "emin değilim", 1 küçük sapma, 1 TF/altyapı sorunu.
- Lookahead: bulunmadı. Bağımsız kesme testi: 404 VARYANT kaydı x 2 sentetik seri x 7 kesme noktası, tüm sütunlar -> 0 fark.
- Düzeltilecekler küçük: 1 stop politikası ihlali (147), 5 kayıtta desteklenmeyen TF (1w/1M), eksik "yaklasik" işaretleri, 1 çift hipotez (X005:5).
- Mevcut testler: 519 geçti.

## 1. Örneklem (32 sınıf) — bkz. hakem_kod_ornek.csv
Uyumlu 26; yaklaşık-işaretli/işaretlenmeli 2 (43, 310); küçük sapma 1 (210); emin değilim 2 (379 hedef sabit mi kayan mı; 509 "3 gün" sayımı); TF sorunu 1 (639).
Ortak gözlemler:
- Tek basamaklı ROI partiler arasında farklı: parti 1 limit `hedef`, parti 5/8 `azalan_roi` (kapanışta). Sonuçları küçük de olsa farklılaştırır; tek kural seçilmeli.
- Parti 8'de CikisAyarlari sınıfta değil örnekte (`__init__`) kuruluyor: koşu betiği ayarı örnekten okumalı.
- Yüzde stoplar sinyal kapanışından hesaplanıyor (dolum sonraki açılış) — belgeli ortak uyarlama.

## 2. Lookahead
- Kalıp taraması (shift(-, center=True, iloc[-1], resample, bfill, tüm-seri mean/std/max): hiçbiri yok. `cummax` (147, 503) ve `expanding` (parti 7) nedensel. Gün gruplamaları (244, 780, `_gelisen_gunluk`) yalnız tamamlanmış önceki günleri (shift(1)) ya da gün içi cummax/cummin kullanıyor. Üst TF her yerde `htf.ust_zaman` (kapanmış mum; değer bir alt mum gecikmeli gelir, muhafazakâr).
- Bağımsız kesme testi (`lookahead.py`): 0 fark. 7 kayıtta sentetik seride sinyal çıkmadı (15, 177, 296#v2, 454, 577, 679, 751) — bunlarda çıkış sütunları yine karşılaştırıldı; kendi testlerinde sinyal var.
- Test kalitesi: anlamlı ama iki zayıflık var. (a) Parti 2-8 geleceği yalnız x2,5 çarparak değiştiriyor; ölçekten bağımsız gelecek özelliği (ör. sonraki mumun IBS'i, mum yönü) bu yöntemle yakalanmaz. Yalnız parti 1 ayrıca veri kesme testi yapıyor. (b) Parti 4 tüm TF'leri günlük sentetik veriyle sınıyor. Öneri: parti 2-8 testlerine kesme (`m.iloc[:k]`) karşılaştırması eklensin.

## 3. Sanal pozisyon kullananlar
| Sınıf | Etki | "yaklasik" işareti |
|---|---|---|
| p2: 185, 189 | çıkış sanal durumdan | VAR |
| p3: 294, 310, 325 | iz stop/çıkış sanal pozisyondan | VAR |
| p4: 397 | kapanış bazlı chandelier, giriş mumu sinyal serisinden | ILERLEME'de var, VARYANTLAR'da YOK |
| p2: 115, 181, 182, 183, 208, 210, 219 | yalnız GİRİŞ süzgeci (çıkış mumunda giriş yok; 208'de 8 mum sayımı da) | YOK — çıkışı etkilemiyor ama gerçek pozisyondan ayrışırsa giriş kaçar; not düşülmeli |
| p5: 495 | takvim/fiyat durum makinesi (pozisyon değil) | gerekmez |
| p7: 676, 727; p8: 790; p1: 73 | sinyal serisi durumu / emir ömrü (pozisyon değil) | gerekmez |
Ayrıca ILERLEME'de "yaklaşık" sayılan ama VARYANTLAR kaydında `yaklasik` anahtarı olmayanlar: p1 41, 43; p4 397; p5 554, 556; p6 574, 577, 578, 635, 655; p7 679. Yalnız parti 2 ve 3 anahtarı yazıyor.

## 4. VARYANTLAR bütünlüğü
- 317 girdi satırının hepsi ya VARYANTLAR'da ya KODLANAMADI'da (eksik 0, ikisinde birden 0, fazladan 0). KODLANAMADI toplam 32 (ILERLEME 33 diyor; 1 fark, önemsiz).
- Kimlikler tekil (dosya içi ve dosyalar arası). `ad` değerleri tekil. Python sınıf adı çakışması yalnız yardımcı `_Taban` (p4-p8), zararsız.
- Dış atıflar çözülüyor: X005:83 -> `k2_kaynak.DonchianEma2RS0083`; X005:594 -> `kod_g8_kod_3.Rsi2Sma5S0253` (eşik 10; sınıf `<=`, kural `<` — ihmal edilebilir). İkisi de verilen parametrelerle örnekleniyor.
- Varyant sayıları girdiyle uyumlu (138: 8, 306: 36, 540: 8, 544: 4, L15#2: 6 ...). Tek fazlalık: 405'te girdi tf '1d', kod 4h+1d.
- SORUN A (TF): tf='1w' -> 367, 384 (p4), 438 (p5), 639 (p6); tf='1M' -> 606 (p6). `depo.aralik_suresi` ve `yeniden_ornekle` bu TF'leri tanımıyor; sınıflar mumları doğrudan haftalık/aylık bekliyor. Parti 2 (136, 141) ve parti 7 (737) aynı işi 1d + ust_zaman/ay sonu ile yapıyor: tutarsız. Aylık barda ATR14x3 stop fiyatı aşabilir (stop negatif = fiilen stopsuz) — veri görmediğim için emin değilim, ama %50 sınırı kodda yok.
- SORUN B (çift hipotez): X005:5 `MacdEma100S0005` = `jesse_kaynak.MacdEmaS0005` (ILERLEME: düşülecek) hâlâ VARYANTLAR'da.
- SORUN C (evren): VARYANTLAR'da evren alanı yok; 594 girdisinde evren yalnız BTCUSDT, ETHUSDT. Koşu listesi evreni girdi CSV'sinden almalı.
- `kayit.py`'de bu sınıfların kaydı yok (talimat gereği lider ekleyecek).

## 5. Stop politikası
- X005:147 (`tum-zaman-zirve-iz`): kaynak stopu 10xATR(14); "<= -%50 ise ATR14x3" sınırı yok. Sentetik seride bile bir girişte mesafe >= %50 çıktı. Düzeltilmeli.
- Diğer yüzde stoplar < %50 (en büyük: 571 %31,8; 25 %26,5; 552/727 %25). Kaynak seviyeli stoplarda (314, 600, 653) %50 sınırı var.

## 6. Üçüncü taraf kod kopyası
Belirti yok: Freqtrade/Backtrader/TA-Lib çağrı kalıbı, İngilizce yorum bloğu ya da yabancı adlandırma bulunmadı; kod vektörel ve proje yardımcılarıyla yazılmış. Kaynak depolarla birebir karşılaştırma yapmadım (kaynaklar elimde değil) — bu yüzden "şüphe yok" diyorum, "kanıtlandı" demiyorum.

## Dosya başına
| Dosya | Hata | Not | Hüküm |
|---|---|---|---|
| kod_1 | 1 (X005:5 çift hipotez) | 41/43 yaklasik anahtarı | KABUL |
| kod_2 | 1 (147 stop sınırı) | 7 sanal süzgeç notu | KABUL, 147 düzelt |
| kod_3 | 0 | — | KABUL |
| kod_4 | 2 (367, 384 tf 1w) | 397 yaklasik anahtarı; 405 4h; 379 emin değilim | KABUL, TF kararı |
| kod_5 | 1 (438 tf 1w) | 554/556 anahtar; 509 emin değilim | KABUL |
| kod_6 | 2 (639 tf 1w, 606 tf 1M) | 574/577/578/635/655 anahtar; 594 evren | KABUL, TF kararı |
| kod_7 | 0 | 679 anahtar | KABUL |
| kod_8 | 0 | CikisAyarlari örnekte | KABUL |
