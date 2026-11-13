# Dünya çapında açık kaynak strateji taraması — Trend Takip ve Ortalamaya Dönüş

## Teslim edilen dosyalar

Katı doğrulama filtresinden geçen **26 benzersiz strateji** derlendi; bunların **13'ü TREND**, **13'ü ORTALAMAYA_DONUS** ailesinde. İstenen **200+ toplam / aile başına 100+** hedefi, kalite ve erişilebilirlik koşullarından ödün vermeden bu taramada karşılanamadı. Özellikle kural bütünlüğü, somut piyasa-zaman dilimi ve yeniden açılabilir kaynak şartlarından biri eksik olan kayıtlar sayı artırmak amacıyla eklenmedi.

[**strateji_listesi.csv — UTF-8, 26 doğrulanmış strateji**](sandbox:/mnt/data/strateji_listesi.csv)

[**ozet.md — dağılımlar, arketipler, kanıt sıralaması, boşluklar ve 10-satır denetimi**](sandbox:/mnt/data/ozet.md)

## Doğrulama standardı

CSV'deki stratejiler doğrudan açılan kaynaklardan çıkarıldı. Örneğin Donchian backtester, 20 günlük giriş/10 günlük çıkış kanalı, 2×ATR stop ve ertesi gün açılışında yürütme kuralını açıkça veriyor; ayrıca bugünkü barı kanaldan dışlayarak lookahead'i önlediğini belirtiyor. citeturn206320view4turn847327view1 Freqtrade Strategy001 ve Strategy002 kodlarında sırasıyla EMA/Heikin-Ashi trend kuralları ile RSI–Stoch–Bollinger–Hammer ortalamaya dönüş kuralları doğrudan doğrulandı. citeturn847327view6turn847327view5

Bölgesel örneklerde Kore Fintrix çalışması KOSPI/KOSDAQ büyük hisselerinde Bollinger alt-bandı girişi, -%3 stop, üst-band hedefi ve beş günlük zaman çıkışını 2021–2026 verisinde test ediyor ve negatif sonucu da açıkça raporluyor. citeturn847327view7 Hindistan kaynağı Nifty Spot üzerinde günlük, dört saatlik ve bir saatlik EMA/Supertrend stop-and-reverse sistemlerini 2015–2025 dönemiyle tanımlıyor. citeturn847327view2 Japonca Qiita kaynaklarında hem tekil hisselerde 25 günlük Bollinger stratejisi hem de TOPIX500 üzerinde beş yıllık Bollinger olay çalışması açık kurallarla yayımlanmış durumda. citeturn721748view4turn721748view5

Çin/FМZ kaynağında Binance Futures BTC_USDT için bir saatlik backtest üstbilgisi, EMA9/21 kesişimi ve %1 stop/%2 hedef doğrudan kodda görülebiliyor; açıklama metni ayrıca bir ve dört saatlik MACD teyidinden söz ediyor. Bu metin-kod farkı CSV'de özellikle not edildi. citeturn847327view3turn237167view2 StockSharp örneklerinde RSI, Bollinger, Z-score ve VWAP mean-reversion sistemlerinin beş dakikalık varsayılan parametreleri ve stopları açıkça belgeleniyor. citeturn309425view0turn847327view8turn847327view4turn309425view3

## Kanıt ve risk notları

En güçlü kayıtlar arasında 513 ABD hissesinde 20.572 işlemi, güven aralıklarını ve rastgele giriş kontrollerini raporlayan EMA pullback testi; maliyet ve slippage dahil 3.786 işlemli Kore Bollinger testi; Faber'ın akademik 10-ay SMA yaklaşımını kodlayan quantstrat örneği; Nifty'nin çoklu zaman dilimi testleri ve AAPL/STLD/IBM üzerinde açık Python backtesti yer alıyor. citeturn136161view4turn847327view7turn680418view19turn847327view2turn721748view4 Kaynakta verilen performans rakamları CSV'de yalnızca **iddia** olarak tutuldu; örneğin StockSharp ZScore sayfasının yaklaşık %121 yıllık getiri iddiası test dönemi vermediği için doğrulanmış performans şeklinde yorumlanmadı. citeturn847327view4

Freqtrade Triple Supertrend kaynağı kendi Supertrend uygulamasının akademik/orijinal göstergeyle doğrulanmadığını açıkça belirttiğinden `ŞÜPHELİ` olarak işaretlendi. citeturn847327view9 MQL5'teki MACD EA ise destek/direnç seviyelerinin öznel olduğunu bizzat belirttiği için tamamen mekanik tekrar üretilebilirlik açısından aynı bayrakla kaydedildi. citeturn255644view4 Bu teslimatta somut piyasa **ve** zaman dilimi şartını birlikte güvenle sağlayan martingale/DCA/stopsuz-grid örneği bulunmadığından, sırf `YASAK_TİP` satırı oluşturmak için daha gevşek kayıt kabul edilmedi.

## Yeniden denetim ve kapsam boşlukları

Rastgele seçilen **S006, S001, S005, S012, S023, S015, S003, S017, S022 ve S002** satırlarının linkleri araştırmanın sonunda tekrar açıldı. On kaynağın tamamı yeniden erişilebildi ve temel giriş/çıkış/stop-parametre özetleri yeniden karşılaştırıldı; bu örneklemde kural çelişkisi saptanmadı. Donchian, Nifty Supertrend, FMZ BTC, Z-score, iki Freqtrade stratejisi, Kore Bollinger ve StockSharp Bollinger kayıtlarının yeniden açılan metinleri bu denetimi doğrudan destekliyor. citeturn847327view1turn847327view2turn847327view3turn847327view4turn847327view5turn847327view6turn847327view7turn847327view8turn847327view9

Hedefin gerisinde kalınan başlıca alanlar TradingView'in oturum/robot erişimi sorunlu açık script sayfaları; kapalı veya giriş gerektiren Discord/Telegram arşivleri; X/Facebook/Instagram/TikTok içerikleri; GitLab, Gitee ve Codeberg'in yeterince açık ve tam-kurallı sonuç vermeyen bölümleri; cTrader/NinjaTrader/AmiBroker/MetaStock toplulukları; ayrıca Afrika, Orta Doğu, Latin Amerika ve bazı Güneydoğu Asya dilleridir. Bu eksiklik, söz konusu bölgelerde strateji olmadığı anlamına gelmez; yalnızca bu teslimatta **açılabilir link + tam mekanik kural + somut piyasa + somut zaman dilimi** eşiğini güvenle geçen yeterli sayıda kayıt doğrulanamadığı anlamına gelir.

---

**Erişim notu (sonradan eklendi):** Bu raporda görünen `sandbox:/mnt/data/` CSV ve Markdown bağlantıları orijinal araştırma oturumunda erişilebilir dosyalara dönüştürülememiştir. Raporun 26 kayıtlık CSV'si bu dosyadan çıkarılamamıştır. Ayrı sunulan 547 kayıtlık kütüphane CSV'si bu raporun veri seti değildir.
