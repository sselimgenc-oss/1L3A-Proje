# ÖN KAYIT — Teşhis testleri C (stop/çıkış) ve D (düzenlilik)

Koşudan ÖNCE yazıldı; sonuçtan sonra değişmez. TEŞHİS (descriptive): yeni ayar arama YOK, varyant optimizasyonu YOK,
strateji değiştirme YOK, "ne olurdu" (stop değiştirip yeniden backtest) simülasyonu YOK. Sonuç canlı planı değiştirmez.
Tek koşu. Sonuç sonrası değişiklik olursa rapor.md'de "SONUÇ SONRASI DEĞİŞİKLİK" başlığıyla yazılır.

Sorular: (1) "İyi trader'lar %40 kazanmayla bile kaybı hemen keser, kârı koşturur; bizim stoplarımız nasıl?" (2) "Düzenli
işlem açan, istikrarlı strateji istiyorum."

## Strateji kümesi (paper'daki 10; id'ler eleme.csv ve ham/x2 dosyalarından doğrulandı)
Canlı 4: dis__e0v1en, dis__ewo-ema-ofset, dis__hma-atr-rider, dis__lube. Yedek 2: dis__gauss-stoch-eth,
dis__haftalik-macd-gunluk-ma. Diğer 3: dis__uc-ortalama-boga-sma60, dis__jt-awesome-osilator, dis__voltarget-trend.
Portföy pf__sabit_sepet: Test C dışı (MFE/MAE yok), yalnız Test D.

## Veri
- sonuclar/evren/v2/ham/x2/<strateji>--<tf>--<sembol>.parquet (maliyet ×2; r = funding dahil net R). Sütunlar
  (motor/arastirma/v2/ham.py `islem_hazirla`): giris_zamani, cikis_zamani (işlem tf'sindeki mum AÇILIŞ anı), yon, r, sf,
  stop_mesafe (= risk$/miktar, FİYAT birimi), fonlama_r. Giriş fiyatı ham dosyada YOK.
- Yalnız geliştirme dönemi: tüm giriş/çıkış < 2025-11-08 ve kullanılan mum < 2025-11-08; betik aksi halde HATA verir.
- Fiyat: veri/mumlar; kripto 5m, DK_ (hisse/emtia) 1h (motorun kullandığı kaynak; DK 5m eksik günlü).

## TEST C — Stop/çıkış teşhisi (araclar/teshis_stop_cikis.py)
- Giriş fiyatı türetme: motor girişi giriş tf-mumunun açılışında doldurur; giriş fiyatı = en ince seride
  [giris_zamani, giris_zamani + tf) içindeki ilk mumun açılışı (kayma payı hariç). Bulunamazsa işlem MAE/MFE'den çıkar, sayılır.
- Pencere: açılışı [giris_zamani + tf, cikis_zamani) olan en ince mumlar = giriş mumundan SONRAKİ, çıkış mumundan ÖNCEKİ
  (uçlar hariç => MAE/MFE gerçek değerin ALT SINIRI; rapora yazılır). Boş pencere => MAE=MFE=0 (geçerli alt sınır), sayılır.
- MAE_R = en kötü ters hareket / stop_mesafe, MFE_R = en iyi lehte hareket / stop_mesafe (yöne göre; en kötü = long'da
  en düşük "düşük", short'ta en yüksek "yüksek"; 0'a kırpılır).
- Ölçüler (strateji başına): kazanma oranı (r>0), ort. kazanç R, ort. kayıp R (r<=0 olanların ortalaması), payoff =
  ort kazanç / |ort kayıp|, beklenti R (=ort r); kazananların MAE medyan/%75/%90; kazananların yüzde kaçında MAE >= 0.5R ve >= 0.8R;
  kaybedenlerin yüzde kaçında MFE >= 0.5R, >= 1R, >= 2R; kazananlarda geri verilen = MFE_R − r (medyan); işlem süresi
  medyanı (gün; kazanan vs kaybeden); kayıpların yüzde kaçı tam stop (r <= −0.85) vs daha küçük (r > −0.85).
  ("önce ... indi" = çıkıştan önce herhangi bir anda ulaştı; sıralama sorusu bu pencerede ayrıca ölçülmez.)
- Sınıflama (değişmez): "kayıp kısa / kâr uzun" = payoff >= 2 VE kazanma <= %45; "çok kazan az kazan" = kazanma >= %60 VE
  payoff < 1; diğerleri "karma".

## TEST D — Düzenlilik (araclar/teshis_duzenlilik.py)
Strateji başına, tüm sembollerin işlemleri birlikte:
- Takvim: ilk giriş ayından 2025-10'a tüm aylar; yıllar ilk giriş yılından 2025'e. Aylık işlem = GİRİŞ ayına göre;
  yıl/ay ΣR = ÇIKIŞ zamanına göre. İşlemsiz ay sayılır (0).
- Ayda ortalama / medyan işlem; >=1 işlem olan ay %; en uzun işlemsiz gün (ardışık iki giriş arası, son girişten
  2025-11-08'e kuyruk dahil); yıl bazında ΣR (×2 maliyet) ve artı yıl sayısı/oranı; artı ay % (tüm aylar paydada);
  ΣR'nin en iyi 10 işlemden ve en iyi %5 işlemden (k=ceil(0.05n)) gelen payı (toplam<=0 ise pay hesaplanamaz);
  en iyi sembol çıkınca ΣR; en uzun ardışık kaybeden seri (çıkış sırası, r<0); en uzun düşüş süresi (gün; kümülatif R
  zirvesinden yeni zirveye, toparlanmamışsa 2025-11-08'e kadar).
- pf__sabit_sepet: işlem yerine günlük getiri; "işlem" = dengeleme günü; ΣR yerine günlük getiri toplamı (yüzde puan);
  en iyi %5 = en iyi %5 GÜN; sembol ve ardışık-kayıp ölçüleri uygulanmaz.
- Etiket (değişmez): "DÜZENLİ" = işlem olan ay >= %80 VE artı yıl >= yılların %70'i VE en iyi %5 işlem çıkınca kalan
  ΣR > 0; aksi "DÜZENSİZ" + tutmayan şart(lar).

## Çıktılar
sonuclar/teshis/stop_cikis/ ve sonuclar/teshis/duzenlilik/ : sonuc.csv, ozet.json, rapor.md (sade Türkçe).
Denetim: 2 strateji × 3 rastgele işlem için MAE/MFE mum verisine bakılarak elle kontrol, rapora yazılır.

## Ek-1 (koşu BAŞLAMADAN hata verdi, hiçbir sonuç görülmeden yazıldı)
İlk deneme tarih doğrulamasında durdu: veri sonunda açık kalan işlemler motorca son geliştirme mumunun BİTİŞ anıyla
(cikis_zamani = 2025-11-08 00:00 UTC, "veri sonu zorunlu kapanış") kapatılıyor; bu damga holdout verisi değil. Kural:
giriş < 2025-11-08 ve çıkış <= 2025-11-08 00:00 serbest; kullanılan mum (fiyat) < 2025-11-08 SERT kalır; çıkış damgası
dönem atamasında son geliştirme gününe (2025-11-07) yazılır, yani 2025 yılında sayılır; takvim ayı aralığı 2025-10'da biter,
2025-11'in ilk 7 günü (kısmi ay) aylık ölçülerde (işlemli ay %, artı ay %, ayda işlem) YOK SAYILIR, yıl ΣR ve toplam ΣR'ye dahildir; bu işlemlerin sayısı (n_veri_sonu_kapanis) raporda gösterilir.
Başka bir değişiklik yok. Aşağıdaki sha256 bu hâlin hash'leridir (ilk commit'teki hash'ler geçersiz).

## sha256 (koşu öncesi)
```
be559435a174f47b9ac15b612c78235b9e5bdaac5f7cf72ee68faa3c641e15cf araclar/teshis_stop_cikis.py
7b7fb0a42527c7fda989e8b1f7ff73ffb61830686220870b2b66788d4c2ca1b2 araclar/teshis_duzenlilik.py
0ce858e9a5ee54a962e6fb204be635d84265cfc25338ef58a55e9197be1e2054 testler/test_teshis_stop_cikis_duzenlilik.py
```
