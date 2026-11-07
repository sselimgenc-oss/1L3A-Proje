# 2020+ OHLCV veri kaynağı denetimi

Tarih: 14 Ekim 2026

Amaç, 01.01.2020 sonrası BIST30, ABD25, KRİPTO25 ve emtia evrenlerini günlük ve saatlik
OHLCV ile test edebilecek, kapsamı ve kaynağı denetlenebilir veri bulmaktır. Kapanış verisi
OHLC'ye dönüştürülmedi; lisansı veya kapsamı belirsiz veri gerçek backtest sonucu üretmek için
kullanılmadı.

| Kaynak | İnceleme sonucu | Karar |
|---|---|---|
| Yahoo Finance | Bu bulut çalışmasında proxy 403; ayrıca ücretsiz 1 saatlik tarih 2020'ye ulaşmıyor | Günlük için erişim açılırsa kullanılabilir; 2020 saatlik için kullanılamaz |
| Binance public API / Vision | Bu bulut çalışmasında proxy 403 | Erişim açılırsa kripto günlük ve saatlikte birincil kaynak |
| Plotly `all_stocks_5yr.csv` | MIT lisanslı, 2013–2018 ABD günlük verisi | Yalnız ayrı arşiv genişlik testi; 2020+ sonucu veya paper uygunluğu değil |
| `GamehunterKaan/fundhunter` | MIT; hisse dosyaları yaklaşık 2025–2026 kapanış+hacim, benchmark dosyası 2021'den itibaren çoğunlukla kapanış | OHLC ve 2020 kapsamı olmadığı için kullanılmadı |
| `AliKajevic/BIST100-Data-Pipeline` | MIT; depoda Yahoo'dan MongoDB'ye indirme kodu var, tarihsel OHLCV arşivi yok | Mevcut ağ engelini aşmıyor |
| `birdalugur/matriks_historical` | Sembol listeleri ve ön işleme kodu var; OHLCV arşivi ve açık lisans bulunamadı | Kullanılmadı |
| `alessiostomeo/btc-cycle-data` | 2012–2026 BTC günlük/saatlik dosyaları var; yalnız BTC ve depo kökünde lisans bulunamadı | Evren genişliği ve lisans şartını karşılamadığı için kullanılmadı |
| `antonyjoseph2111/Historical-Market-Data-Collector-CSV-Based-Multi-Year` | CC0 indirme kodu; veriyi yine Binance public arşivinden çekiyor, veri depoda değil | Mevcut ağ engelini aşmıyor |
| Stooq CSV | Bu bulut çalışmasında proxy 403; BIST/kripto evrenini de tam karşılamıyor | Kullanılmadı |

## Güvenli yedek yol

`codex-algo mtf-import`, kullanıcı veya lisanslı veri sağlayıcıdan alınmış CSV'yi şu kontrollerle
yalnız bu deponun `data/cache/` alanına aktarır:

- sembolün tanımlı 86 varlıklı MTF evreninde bulunması;
- zaman, open, high, low, close ve volume alanlarının varlığı;
- fiyatların pozitif, hacmin negatif olmaması ve OHLC mum ilişkilerinin geçerli olması;
- seçilen `1d`/`1h` frekansının gözlenen aralıkla uyumlu olması;
- 01.01.2020 öncesinin testten çıkarılması;
- kaynak dosya SHA-256 özeti, fiili kapsam ve hedef önbelleğin kaydedilmesi;
- var olan önbelleğin `--replace` olmadan değiştirilmemesi.

Bu mekanizma veri lisansını otomatik olarak vermez. Lisans, kurumsal eylem düzeltmesi,
borsa saat dilimi ve sembol eşlemesi veri tesliminde ayrıca doğrulanmalıdır.
