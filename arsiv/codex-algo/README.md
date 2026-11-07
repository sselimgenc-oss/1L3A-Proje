# Codex Algo

Claude çalışmalarından bağımsız, yalnız bu depoda yaşayan çoklu piyasa backtest, ayrı
10.000 USD paper hesapları ve Streamlit pano projesidir. Gerçek emir göndermez.

## Kapsam

- Kripto: BTC, ETH, SOL — Binance açık OHLCV verisi
- ABD: SPY, QQQ, AAPL, MSFT, NVDA — Yahoo Finance
- BIST: XU100, THYAO, ASELS, TUPRS, BIMAS — Yahoo Finance
- Emtia: GLD, SLV, USO ETF'leri — Yahoo Finance
- Dokuz bağımsız Codex strateji uyarlaması
- Sinyalde kapanış, işlemde sonraki bar ve piyasa bazlı maliyet
- %70 eğitim / %30 dönem-dışı test ve iki kat maliyet stresi
- Üç bağımsız 10.000 USD paper hesabı: tek-zaman, 1W→1D ve 1D+4H→1H
- Paper işlemleri yalnız strateji × varlık uygunluk kapısından sonra başlar

Strateji seçiminin gerekçeleri ve sınırlamaları için
[`docs/STRATEGY_REVIEW.md`](docs/STRATEGY_REVIEW.md) dosyasına bakın.
Pano ayrıca üç PDF'den çıkarılan A/B/C karar matrisini ve her adayın mevcut durumunu gösterir.
Arşiv genişlik bulguları [`docs/ARCHIVAL_RESULTS.md`](docs/ARCHIVAL_RESULTS.md) içinde kayıtlıdır.
2020+ kaynak taraması ve reddedilen veri kümeleri
[`docs/DATA_SOURCE_AUDIT.md`](docs/DATA_SOURCE_AUDIT.md) içinde kayıtlıdır.
PC–mobil senkron pano başlıklarının bağımsız karşılığı
[`docs/DASHBOARD_PARITY.md`](docs/DASHBOARD_PARITY.md) içinde tanımlıdır.

## Kurulum

```bash
UV_CACHE_DIR=/tmp/codex-algo-uv-cache uv venv .venv
UV_CACHE_DIR=/tmp/codex-algo-uv-cache uv pip install --python .venv/bin/python -e '.[dev]'
```

## Doğrulama ve kullanım

```bash
.venv/bin/pytest
.venv/bin/ruff check .

# Tüm geçmiş verileri indirip strateji/enstrüman matrisini çalıştırır
.venv/bin/codex-algo research --refresh

# Ortak 10.000 USD paper portföyünü günceller
.venv/bin/codex-algo paper-init
.venv/bin/codex-algo paper-update
.venv/bin/codex-algo paper-status

# Ağ/veri engeli varsa bekler; her 30 dakikada mekanik zinciri yeniden dener
.venv/bin/codex-algo monitor --interval-minutes 30

# Canlı sağlayıcı engelliyse, ayrı ve paper'a bağlanmayan 2013-2018 ABD arşiv ön elemesi
.venv/bin/codex-algo archive-research
.venv/bin/codex-algo archive-research --broad

# 01.01.2020 sonrası çoklu-zaman araştırması
.venv/bin/codex-algo mtf-research --mode daily --refresh
.venv/bin/codex-algo mtf-research --mode hourly --refresh

# Sağlayıcı engelliyse, kullanıcı/vendor OHLCV CSV'sini doğrulayarak yalnız bu depoya alır
.venv/bin/codex-algo mtf-import --file /okuma/yolu/AAPL.csv --symbol AAPL --interval 1d
.venv/bin/codex-algo mtf-research --mode daily --symbols AAPL

# Yerel pano
.venv/bin/streamlit run app.py --server.address 127.0.0.1 --server.headless true
```

Pano varsayılan olarak `http://localhost:8501` adresinde çalışır. Bu adres yalnız yerel
doğrulama içindir; depo veya pano herkese açık yayımlanmamalıdır.

## Özel ve senkron barındırma

PC ve mobil aynı veriyi görmek için tek bir HTTPS sunucu, parola ve kalıcı disk gerekir.
Uygulama bu düzen için hazırlanmıştır: web panosu ile 30 dakikalık worker aynı süreçte çalışır,
çalışma verisi `/app/runtime` altında kalır ve `DASHBOARD_PASSWORD` yoksa hosted erişim kapalıdır.

Yerel Docker doğrulaması:

```bash
export DASHBOARD_PASSWORD='yerel-olarak-belirleyin'
docker compose up --build
```

`compose.yaml` portu yalnız `127.0.0.1` üzerinde açar. Parolayı `.env` veya Git'e eklemeyin.
Bulut için `render.yaml` başlangıç şablonudur. Servis kurulurken:

- depo olarak yalnız `codex-algo` bağlanmalı;
- `DASHBOARD_PASSWORD` sağlayıcının gizli değişken alanına girilmeli;
- `/app/runtime` için kalıcı disk ve tek çalışan instance kullanılmalı;
- sağlayıcının HTTPS alan adı üzerinden erişilmeli;
- kalıcı disk/uyumayan servis ücretli plan gerektiriyorsa harcama ayrıca onaylanmalıdır.

Hosted başlangıç komutu `codex-algo-hosted` olur. Sağlık kontrolü `/_stcore/health` yoludur.
Render dışında Railway veya bir VPS de aynı Docker imajı ve `/app/runtime` volume'u ile çalışır.
Geçici/uyuyan ücretsiz servis, yarım saatlik kontroller ve SQLite kalıcılığı için güvenilir değildir.

Paper hesapları birbirini kapatmaz: standart stratejiler `paper.sqlite3`, haftalık→günlük
stratejiler `paper_mtf_daily.sqlite3`, günlük+4s→1s stratejiler
`paper_mtf_hourly.sqlite3` içinde tutulur. Pano bu hesapların durumunu ayrı gösterir.

`monitor` yalnız veri indirme, backtest, önceden tanımlı uygunluk elemesi ve paper güncellemesi
yapar. Kod değiştirmez, gerçek emir göndermez ve başka depolara yazmaz. Sürecin çalışması bulut
çalışma alanının açık kalmasına bağlıdır; Codex uygulamasında kalıcı görev zamanlayıcısı yoksa
ortam kapatıldıktan sonra kendiliğinden yeniden başlayamaz.
Bir sağlayıcı bağlantı hatası verdiğinde aynı turdaki tekrar istekleri 60 saniyelik devre
kesiciyle durdurulur; 30 dakika sonraki tur sağlayıcıyı yeniden sınar. Yerel ve doğrulanmış
MTF önbellekleri sağlayıcı engelliyken de ayrı aşamada işlenir.

Yahoo OHLC verisi bölünme ve temettü etkilerinin sahte kırılım üretmemesi için düzeltilmiş olarak
alınır. Sinyal kapanmış mumda oluşur, paper uygulaması sonraki mumun açılışında kaydedilir.
Ortak `$` gösterimi gerçek döviz dönüşümü değildir: her varlığın yerel/USDT fiyat getirisine
10.000 USD-notional ağırlık uygular; TRY/USD kur riski ayrıca modellenmemiştir.

Arşiv ön elemesi Plotly'nin MIT lisanslı `all_stocks_5yr.csv` kümesinden yalnız AAPL,
MSFT ve NVDA'yı kullanır. Sonuçlar `archival_*` dosyalarına ayrılır; güncel doğrulama veya
paper-test uygunluğu sayılmaz.
`--broad`, en az 1.000 barı olan arşiv hisselerinde seçim yanlılığına karşı genişlik
kontrolü yapar; veri kümesinin hayatta kalma yanlılığı ayrıca panoda belirtilir.

Çoklu-zaman kuralları, 86 varlıklı evren ve veri sınırlamaları
[`docs/MTF_STRATEGIES.md`](docs/MTF_STRATEGIES.md) içinde açıklanır. Saatlik Yahoo geçmişi
2020'ye ulaşmıyorsa sistem daha kısa testi kabul etmez; eksik piyasayı sağlık raporunda gösterir.
`mtf-import`, `timestamp/date/datetime`, `open`, `high`, `low`, `close`, `volume` sütunlarını;
mum ilişkilerini, frekansı ve 2020 sonrası kapsamı doğrular. Saat damgaları yerel ise örneğin
`--timezone Europe/Istanbul` verilmelidir. Dosyanın SHA-256 özeti ve kapsamı
`state/import_provenance.json` içinde tutulur. Var olan önbellek açıkça `--replace` denmeden
değiştirilmez. İçe aktarılan veriyle testte `--refresh` kullanılmaz.

## Kalıcı ve geçici dosyalar

Kaynak kodu ile yapılandırma Git'te tutulur. İndirilen fiyatlar `data/cache/`, backtest
çıktıları ve paper veritabanı `state/` altında tutulur ve Git'e eklenmez. Hiçbir API anahtarı
gerekmez. Ağ erişiminde şu alanlar kullanılır:

- `data-api.binance.vision`
- `data.binance.vision`
- `query1.finance.yahoo.com`
- `query2.finance.yahoo.com`
- `fc.yahoo.com`

## Güvenlik sınırı

Kardeş depolar yalnız salt okunur karşılaştırılabilir. Tüm yazma, çalışma verisi ve test
çıktısı bu checkout içinde kalır. Claude'un test ettiği Hybrid Breakout, Squeeze Momentum
ve MACD ReLoaded bu projede dışlanmıştır.

