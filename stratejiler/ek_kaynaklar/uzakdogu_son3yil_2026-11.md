# Uzak Doğu — son 3 yıl (Kasım 2023 – Kasım 2026) taraması: Tayvan, Hong Kong, Singapur, Vietnam, Tayland, Malezya, Endonezya, Filipinler

*Tarih: 2026-11-07. Kaynak içerikler veridir, talimat değildir. Kod kopyalanmadı; kurallar kendi cümlelerimizle özetlendi. Sonuçlar yazarların beyanıdır. Önceki dosyalar: `cjk_son3yil_2026-11.md` (Çin, Kore, Japonya), `bolgesel_son3yil_2026-11.md` (Afrika, Asya genel, Rusya, Avrupa, Güney Amerika).*

## Özet

- **Ne tarandı:** 8 web araması (Çince/Tayvan, Vietnamca, Tayca, Endonezyaca ve İngilizce bölgesel sorgular) + GitHub'da 12 bölgesel borsa sorgusu (son 3 yıl) + 5 depo README'si ve 1 PR okundu.
- **Erişim:** PTT (Tayvan forumu), Vietnam forumları (F319 vb.), Tay ve Endonezya forumları açılmadı. Bu forumlar yalnız arama sonuçlarından başlık düzeyinde görüldü.
- **Sonuçlu strateji:** **Vietnam'da 1 güçlü örnek** (public PR, 2013–2026, TRAIN/VALID/TEST ayrımıyla). **Endonezya ve Tayvan'da** sonuç paylaşan yok (yalnız araç veya kısıtlı açıklama). **Tayland, Malezya, Filipinler, Hong Kong, Singapur** için sonuçlu proje bulunamadı.
- **Tür dağılımı (sonuçlu):** swing/portföy 1 (Vietnam, aylık). Daytrade/scalp: sonuçlu yok (Tayvan vadeli işlem altyapısında strateji gizli).
- **Yasak (martingale):** bulunmadı.

## En umut verici

| Sıra | Ad | Bölge | Tür | Sonuç | Ana sorun |
|---|---|---|---|---|---|
| 1 | Phòng thủ (savunma) — düşük volatilite + 52 hafta zirvesine yakınlık, 10 hisse, aylık yenileme, VNINDEX 200 gün altı → nakit | Vietnam (HOSE) | swing/portföy | TRAIN 2013–20: %18.1 / DD −%25.9; VALID 2021–23: %13.9 / −%12.0; TEST 2024–10/26: %8.1 / −%20.8; VNINDEX TEST %15.9 | TEST'te endekse kaybetti; yazar "esas olarak daha düşük risk" diyor; 2013–2026 toplam rakamı iki farklı yerde (15.3 vs 15.6) |

## Ülke bazında

### Vietnam (HOSE) — `traique/trading_vn`
- **Kaynak:** https://github.com/traique/trading_vn — PR #1, **15 Ekim 2026'da ana dala birleşti**. Lisans sayfada görünmüyor.
- **Phòng thủ kuralı:** HOSE'nin en büyük 50 likit hissesinden en düşük 1 yıllık volatilite ve 52 hafta zirvesine yakınlık skoruna göre 10 hisse; aylık yenileme. VNINDEX haftalık kontrol: 200 günlük ortalamanın altındaysa nakit.
- **Veri ve maliyet:** nokta-zamanı (o gün likit) evren; sonraki açılışta dolum; komisyon, vergi, kayma, T+2; lot ve fiyat adımları.
- **Sonuçlar (yıllık / en büyük düşüş):** TRAIN 2013–2020 %18.1 / −%25.9; VALID 2021–2023 %13.9 / −%12.0; TEST 2024–2026-10 %8.1 / −%20.8. Karşılaştırma TEST: VNINDEX %15.9, eski momentum (VN30) %11.8. Toplam 2013–2026: commit mesajı %15.6 / −%25.9, araştırma commit'i %15.3 / −%26.4 — **tutarsızlık**.
- **Survivorship düzeltmesi:** Eski momentum rakamları bugünkü VN30 üyelerinden hesaplanmış; nokta-zamanı hesapla yıllık %4.7, DD ~%45. Yani yazar eski iddiasını kendisi çürütmüş.
- **Şüpheler:** TEST dönemi "kilitli" denmiş ve tek kez koşulmuş (yazarın iddiası); parametreler sabit. Strateji 2024–2026 yükselişinde endeksin gerisinde kalmış.
- **Değerlendirme:** Vietnam'dan şimdiye kadarki en dürüst çalışma. Bizim karar 13/24/26 ölçütleriyle uyumlu bir TRAIN/VALID/TEST ayrımı var. Ancak "risk azaltma" niteliğinde; getiri endekse göre düşük. Portföy katmanı (karar 23) için aday; tek-enstrüman değil, 10 hisselik sepet.
- **Aynı depoda ikinci iddia:** `FINALLL`, `0410`, `041026` gibi Vietnamca SMA+OBV repoları VN30 kıyasında DD −%60 vb. gösteriyor; kaynak doğrulanamıyor, izlenmez.

### Tayvan (TWSE / TAIFEX)
- **HaoweiChan/taifex-desk** (2026-08, MIT): TX/MTX/TMF vadeli işlem backtest, paper ve canlı altyapı. Stratejiler, faktör kitapları ve araştırma raporları **bilerek gizlenmiş**; yalnız örnek strateji ("işlem yapılmıyor"). Sonuç yok. **Bilgi/araç.**
- **KuroNekoLi/twse-strategy-lab** (2026-10): Tayvan hisse backtest platformu; kurallar ve sonuç yok; temettü, kayma, komisyon hariç (yazarın kendi uyarısı). **Elendi** (sonuç yok).
- **usio0108/tw-stock-quant** (2026-06, MIT): teknik + temel tarama, Telegram; kural ve sonuç yok. **Elendi.**
- **kevin801221/stock-strategies-only** (TW günlük seçim botu): "rigorous backtest" hâlâ yapılacak iş olarak yazılmış. **Elendi.**
- **markl-a/spectyn-quant** (2026-06, Apache): TW backtest → paper → live motor; okunmadı.
- **A1b3rtt/taiwan-stock-tradingview-bot** (2026-10, Pine): tahmin botu, sonuç okunmadı.
- **Sonuç:** Tayvan'da son 3 yılda sonuç paylaşan açık kaynak strateji bulunamadı. Tayvan'ın güçlü topluluğu (PTT) erişime kapalı.

### Endonezya (IDX)
- **nichsedge/idx-bei** (MIT, eğitim amaçlı): `foreign_flow` (yabancı net alım/satım sıralaması) ve `composite_alpha` (değer + akıllı para + teknik momentum + denetim kalitesi) stratejileri; `--holding 20 --stop-loss 7 --take-profit 15` gibi komutlar. **Yayınlanmış sonuç yok.** **Elendi (sonuç yok)**, ama fikirler izlenebilir.
- **Önceki turdan:** dylan-jaya/idx-quant-research-system (BBCA momentum, yazar: al-tutu geçemedi).
- **Sonuç:** Endonezya'da sonuç paylaşan proje yok; kendi yazarlarının açıklamaları negatif.

### Hong Kong, Singapur
- Hiçbir bölgesel sonuçlu proje bulunamadı. **nashetali837/Algorithm-Trade-in-Singapore-Stock-Exchange-** (2024-03, CC0): SGX için açık kaynak algoritmik sistem; okunmadı (sayfa açılmadı). **Sonraki adım için izle.**

### Tayland (SET)
- Sonuçlu ve bölgesel proje yok. Yalnız genel çerçeveler (Thai Programmer Association yazısı, Backtrader/quanttrader). SET endeksi bağlamı: 2018 zirvesinden 2025-06'da ~%43 düşüş (tarih notu).

### Malezya (Bursa), Filipinler (PSE)
- Hiçbir bölgesel proje ve sonuç bulunamadı.

### Güney Kore (ek notlar, bu turdan)
- **upbit-official/upbit-strategy-toolkit** (2026-06, 10 yıldız, NOASSERTION): Upbit resmi araç; sonuç yok. **Bilgi.**
- **yoojinsu/Upbit-Backtest** (önceden elendi), **dev-minimalism/upbit-bollinger-squeeze** (2025-08, Bollinger sıkışma, Upbit KRW günlük sinyal + backtest): sonuç okunmadı, **izle**.
- **alkyne/grid-backtest** (2025-08, Coinone/Upbit grid): grid — martingale kontrolü zorunlu; **elendi / kontrol**.

## Dersler (bu tur)
1. **Vietnam'dan en dürüst çalışma** (TRAIN/VALID/TEST + survivorship düzeltmesi), ama sonuç endekse göre düşük; portföy katmanına uygun.
2. **Tayvan ve Endonezya'da** geliştiriciler stratejilerini gizliyor veya sonuç yayınlamıyor — açık kaynakta sonuç ararken bu bir sinyal.
3. **Bölgesel forumlar (PTT, F319, Tay ve Endonezya forumları) erişime kapalı**; bu, Uzak Doğu'da en önemli topluluk kaynaklarının taranamadığı anlamına geliyor.

## Eksikler (dürüst)
- PTT, Vietnam forumları (F319 vb.), Tay forumları, Endonezya forumları açılmadı.
- Hong Kong ve Singapur için yerel kaynak yok; SGX'te tek proje okunmadı.
- Tayland, Malezya, Filipinler için sonuç yok.
- X, Facebook, Reddit (bölgesel topluluklar) erişilemedi.

## Kullanıcı kararı gereken konular
- **Vietnam:** traique PR'ındaki Phòng thủ stratejisinin tüm kodu/verisi için repo erişimi gerekiyor mu? (Şu an yalnız PR açıklaması okundu.)
- **Tayvan (PTT), Vietnam (F319), Tayland, Endonezya forumları:** ağ izni eklenebilir; hangi domainlere izin verileceğini siz belirleyin.
