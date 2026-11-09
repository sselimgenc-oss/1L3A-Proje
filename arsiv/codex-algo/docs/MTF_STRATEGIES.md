# Evrensel çoklu-zaman stratejileri

Tarih: 14 Ekim 2026

Bu hat, mevcut tek-zamanlı dokuz Codex uyarlamasından ayrıdır. Claude'un test ettiği Hybrid
Breakout, Squeeze Momentum ve MACD ReLoaded burada da kullanılmaz.

## Mimariler

### Haftalık yön → günlük işlem

Üst rejim yalnız tamamlanmış haftalık mumdan hesaplanır. Haftalık kapanış EMA20 üstünde ve
EMA20>EMA40 ise yükseliş yönü geçerlidir. Alt zaman sinyali günlük kapanışta oluşur, emir
varsayımı sonraki günlük açılıştır.

- Haftalık Rejim + Günlük Kırılım: 20 günlük tepe kırılımı; 10 günlük dip veya EMA20 çıkışı.
- Haftalık Rejim + Günlük Geri Çekilme: EMA20 geri kazanımı ve RSI14>50; EMA50/RSI40 çıkışı.
- Haftalık Rejim + Günlük Ortalamaya Dönüş: alt Bollinger+RSI2; orta bant/RSI70 çıkışı.
- Haftalık Rejim + Günlük Momentum: EMA20>50 ve ROC20>%5; ROC<0 veya rejim kaybı çıkışı.

### Günlük+4 saatlik yön → 1 saatlik işlem

Hem tamamlanmış günlük hem tamamlanmış 4 saatlik mumlarda kapanış EMA20 üstünde ve
EMA20>EMA50 olmalıdır. İşlem sinyali 1 saatlik kapanışta, uygulama sonraki saatlik açılıştadır.

- 1S Geri Çekilme: EMA20 geri kazanımı ve RSI; EMA50/RSI çıkışı.
- 1S Kırılım: 24 saatlik tepe kırılımı; 12 saatlik dip veya EMA20 çıkışı.
- 1S Ortalamaya Dönüş: alt Bollinger+RSI2; orta bant/RSI70 çıkışı.
- 1S SuperTrend: SuperTrend(10,3)+EMA50 giriş ve rejim çıkışı.

## Evren

- BIST30: yapılandırmada açıkça listelenen 30 sembol.
- ABD25: 25 büyük ABD şirketi.
- KRIPTO25: stabil coin ve sarılı varlıklar dışındaki 25 büyük/likit Binance spot çifti.
- EMTIA: altın, gümüş, petrol, doğal gaz, bakır ve tarımı temsil eden altı likit ETF.

Evren sabit/güncel bileşenlerle geçmişe yürütüldüğü için hayatta kalma yanlılığı taşır. BIST30
ve piyasa-değeri listeleri dönemsel olarak değişir; sonuçlar tarihsel bileşen endeksi değildir.

## Veri ve kabul disiplini

- Başlangıç talebi 01.01.2020'dir; enstrüman daha sonra işleme açıldıysa fiili başlangıç yazılır.
- Yahoo ücretsiz 1 saatlik veri 2020'ye ulaşmazsa kısaltılmış hisse/BIST/emtia testi reddedilir.
- Binance 1 saatlik kripto verisi 2020'den itibaren sayfalanabilir; ağ izni gerektirir.
- İşlem maliyetleri piyasa/sembol bazlıdır ve iki kat maliyet stresi uygulanır.
- Tam dönem, %70/%30 OOS, al-tut ve fazla getiri birlikte raporlanır.
- Bir stratejinin her piyasaya uyacağı varsayılmaz; özet hem genel hem piyasa bazında üretilir.
- MTF sonucu doğrudan paper'a girmez. Önce yeterli işlem, pozitif OOS, maliyet dayanıklılığı ve
  makul düşüşle piyasa-strateji eşleşmesi seçilir.

## Dışa kapalı ortamda veri aktarımı

Sağlayıcı erişimi engelliyse `mtf-import` komutu, MTF evrenindeki bir sembole ait günlük veya
saatlik CSV'yi doğrulayarak `data/cache/` içine alır. Gerekli alanlar zaman, open, high, low,
close ve volume'dür. Yanlış frekans, geçersiz mum, negatif hacim ve evrende olmayan sembol
reddedilir; 01.01.2020 öncesi satırlar atılır. Kaynak dosyanın özeti ve fiili tarih kapsamı
`state/import_provenance.json` içinde saklanır. Bu yöntem veri lisansını kendiliğinden çözmez;
kullanılan dosyanın lisansı ve kurumsal eylem düzeltmeleri ayrıca doğrulanmalıdır.
