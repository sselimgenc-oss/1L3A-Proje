# Senkron pano işlev eşlemesi

Kaynak: `Proje_Ozeti_14Ekim2026.pdf`, bölüm 5 ve kullanıcının paylaştığı SG-Test Panel
ekran görüntüsü. Claude panelinin kaynak `index.html` dosyası bu çalışma alanında yoktur; bu
belge kaynak kod eşitliği değil, tarif edilen kullanıcı işlevlerinin bağımsız Codex karşılığıdır.

| Başlık | Paylaşılan ekranlarda görülen | Bağımsız Codex karşılığı |
|---|---|---|
| Özet | Üstte toplam değer/getiri, son gün, açık pozisyon, kapanan işlem+kazanma; soru kutusu ve hızlı sorular; alarm şeritleri; son 24 saat olayları; hesap kartlarında mini eğri, düşüş, kazanma, PF, kapanan/açık, düşüş süresi, şans dışılık ve son çalışma | Ortak paper özsermayesi, nakit, düşüş, açık pozisyon, son olaylar, worker/veri sağlığı ve Codex strateji kartları |
| Karne | Her hesap için 0–100 genel puan; altı 0–10 not: Getiri, Risk, Beklenti (R), Şans dışılık, Deneyim, Çeşitlendirme; az örnekte “veri birikiyor” | Aynı altı boyut; formüller açık, az işlemde puan yerine düşük güven/veri birikiyor etiketi |
| Grafikler | Tüm hesaplar ve mevduat/BTC/Nasdaq/S&P/BIST kıyasları; seçili hesabın sermaye–beklenti çizgisi; Monte Carlo %5–95 ve %25–75 konileri; zirveden düşüş grafiği | Paper eğrileri, uygun kıyaslar, backtest beklenti konisi ve zirveden düşüş; eksik benchmark açıkça işaretlenir |
| Takvim | Aylık yeşil/kırmızı günlük dolar değişimi, hafta toplamları; seçilen günde kapanan işlemler ve gün sonu açık pozisyonların değer değişimi | İstanbul gününe göre günlük paper değişimi, kapanan işlemler, açık risk değişimi ve haftalık toplam |
| Açık pozisyonlar | Hesap ve varlık sınıfı halka grafikleri; pozisyon anlık kâr/zarar çubukları; hesap, strateji, varlık, yön, giriş, süre, giriş/stop, tutar, P/L, R ve stopa uzaklık tablosu | Strateji/piyasa dağılımı, anlık P/L, stop mesafesi ve R bazlı açık risk tablosu |
| İşlem geçmişi | Hesap/sonuç filtreleri ve arama; hesap, strateji, varlık, yön, giriş/çıkış zamanı ve fiyatı, R, P/L ve çıkış nedeni | Aynı alanlar; maliyet ve model hedef nedeni de korunur |
| İstatistik | Net P/L, işlem, kazanma, PF, ortalama kazanç, kazanç/kayıp, beklenti, SQN, en büyük kazanç/kayıp, tutma süresi, Kelly, yeşil gün, en iyi/kötü gün, Sharpe, Sortino; strateji birikimli P/L, varlık P/L, R dağılımı, süre–sonuç grafikleri | Hesaplanabilen aynı ölçüler; Kelly/SQN küçük örneklemde gösterilmez, PF sonsuz/boş durumları açık etiketlenir |
| Stratejiler | Hesap/strateji bazında kapanan, kazanma, ortalama R, P/L ve açık adet; ayrıca çıkış nedenlerinin işlem/pay/P&L kırılımı | Codex tek-zaman ve MTF stratejilerinin aynı kırılımı; Claude stratejileri eklenmez |
| Koç | Sabit kontrollerden öncelikli bulgular; düşük güven etiketi, etki ve örneklem, ilgili sayfa; en az sekiz işlemden sonra backtest karşılaştırması; strateji çıkarma “ne olurdu?” simülatörü | Kurala dayalı bulgular, veri güveni ve etki; test sürerken kural değiştirmeme uyarısı; yalnız yeterli örneklemde beklenti karşılaştırması ve çıkarma simülasyonu |
| Öğrenme | Botlardan bağımsız gölge mod; önceki işlemlerden tahmin, −0,2R altındaysa gölge filtre; gerçek/gölge sonuç, atlanacak işlem ve isabet; işlem bazında tahmin–gerçek karşılaştırması | Paper kararını değiştirmeyen, ileriye dönük gölge filtre günlüğü; yeterli geçmiş yoksa “öğreniyor”, sonuç sonradan ölçülür |
| Rapor | Ay seçimi ve Yazdır/PDF; ana KPI'lar, getiri grafiği; hesap kontrol listesi (30+ işlem, 60+ gün, DD<%10, koni içinde, PSR>%95); koç özeti | Aylık rapor, indirilebilir CSV/JSON ve yazdırılabilir görünüm; eşikler ayrı ayrı gösterilir |
| Dönemsel getiri | Günlük/haftalık/aylık düğmeleri; hesap sütunlu ısı haritası | Günlük/haftalık/aylık Codex paper getirileri ve hesap/strateji matrisi |
| Risk | Aynı varlıkta yoğunlaşma; toplam tutar ve durum; Monte Carlo ile 1x/2x/3x 60 gün ve 1 yıl düşüş olasılıkları; yeterli ortak gün sonrası hesap korelasyonu | Varlık/piyasa yoğunlaşması, −%15 fren, kaldıraç senaryoları yalnız yeterli örneklemle, strateji korelasyonu, veri ve worker sağlığı |

## Ortak ekran iskeleti

- Sol menüde sayaçlar, son güncelleme, test dönemi ve ilerleme çubuğu bulunur.
- Üst KPI şeridi ve soru/hızlı-soru alanı sayfalar arasında sabit kalır.
- Para ve gün kesimleri İstanbul saatine göre gösterilir.
- “Veri az”, “veri birikiyor” ve “düşük istatistiksel güven” durumları sayıların yanında
  görünür; erken dönemde güçlü hüküm verilmez.
- Paper işlemler ile gölge öğrenme birbirinden ayrıdır; gölge sonuçlar bot kararını değiştirmez.
- Test sürerken koç bulgusu strateji kuralını otomatik değiştirmez; yeni sürüm ancak dönem
  sonunda ayrı değerlendirilir.

## Ayrım

Claude'un test ettiği Hybrid Breakout, Squeeze Momentum ve MACD ReLoaded Codex panosuna
alınmaz. Claude hesaplarının işlemleri de Codex paper sonuçlarıymış gibi gösterilmez. Görsel ve
kullanım fikri örnek alınabilir; strateji, veri, hesap ve sonuçlar tamamen ayrı kalır.

## Codex'e özgü geliştirmeler

### İlk sürümde

1. **Veri Güveni kartı:** Her piyasa/zaman dilimi için kapsam başlangıcı, son bar, eksik bar,
   veri kaynağı, SHA-256/provenans ve gecikme. Veri sağlığı bozuksa performans kartından önce
   görünür.
2. **Backtest bütünlük kartı:** Sonraki bar uygulaması, maliyet, kayma, OOS oranı, maliyet stresi,
   survivorship uyarısı ve lookahead kontrollerinin geçti/kaldı durumu.
3. **Piyasa × strateji uygunluk matrisi:** “En iyi strateji” yerine BIST/ABD/kripto/emtia ve
   1W→1D / 1D+4H→1H bazında kârlılık, OOS ve stres dayanıklılığı ısı haritası.
4. **Beklenti sapması:** Paper eğrisi ile backtest dağılımını karşılaştırır; sadece getiri değil,
   işlem sıklığı, ortalama R, maliyet ve düşüş sapmasını ayrı gösterir.
5. **Sürüm ve denetim izi:** Her sinyal/işlem hangi strateji sürümü, parametre özeti ve veri
   zamanıyla üretildiğini taşır. Test sırasında kural değişirse eski/yeni sonuç karışmaz.

### Yeterli paper verisi oluşunca

6. **Marjinal risk katkısı:** Her pozisyonun toplam portföy oynaklığına ve düşüşüne katkısı;
   aynı varlığı farklı stratejilerin tutması tek risk olarak kümelenir.
7. **Rejim haritası:** Trend/yatay, düşük/yüksek volatilite ve risk-on/off rejimlerinde strateji
   sonucu. Rejim etiketi işlemden sonra optimize edilmez; önceden tanımlanır.
8. **Champion–challenger gölge testi:** Paper'a uygun ana model ile aday model aynı veride yan
   yana yürür; aday gerçek paper sermayesine dokunmaz ve ancak önceden yazılı terfi eşiklerini
   geçerse değerlendirilir.
9. **Maliyet kırılma noktası:** Komisyon+kayma hangi seviyeye geldiğinde avantajın sıfırlandığını
   piyasa ve strateji bazında gösterir.
10. **Korelasyon kümeleri:** Sadece getiri korelasyonu değil, aynı anda zarar etme ve ortak
    düşüş korelasyonu; çeşitlendirme notu buna göre hesaplanır.

### Mobil kullanım

11. **Günlük kısa özet:** Son 24 saat, yeni/kapanan pozisyonlar, kritik alarmlar ve veri sağlığı
    tek ekranda; ayrıntılı tablolar ikinci seviyede.
12. **Alarm gelen kutusu:** Alarm nedeni, ilk görülme, son görülme, güven seviyesi ve çözüldü
    durumu; aynı hata her yarım saatte yeni alarm gibi çoğaltılmaz.

Bu ekler gerçek emir yetkisi vermez. Koç ve gölge öğrenme yalnız açıklama/araştırma üretir;
test sürerken strateji kuralını veya paper pozisyonunu otomatik değiştirmez.
