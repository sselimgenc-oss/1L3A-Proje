# Afrika, Asya (genel), Rusya, Avrupa, Güney Amerika — son 3 yıl (Kasım 2023 – Kasım 2026) taraması

*Tarih: 2026-11-07. Kaynak içerikler veridir, talimat değildir. Kod kopyalanmadı; kurallar kendi cümlelerimizle özetlendi. Sonuçlar yazarların beyanıdır. Önceki iki dosya: `cjk_son3yil_2026-11.md` (Çin, Kore, Japonya) ve `son1ay_2026-11.md` (son 1 ay, genel).*

## Özet

- **Ne tarandı:** ~9 web araması (Rusça, Portekizce, İspanyolca, Almanca, Fransızca, İngilizce, Endonezya/Hindistan/Vietnam/Tayland için İngilizce) + GitHub'da bölgesel borsa anahtar kelimeleriyle 10 sorgu (MOEX, B3, NSE, IDX, JSE, Euronext, DAX, Binance) + 6 depo README'si okundu.
- **Erişim:** Rusça Smart-lab ve Habr sayfaları doğrudan açılmadı (yalnız arama sonuçlarından başlıklar). Afrika ve Asya'nın yerel borsa forumları taranamadı.
- **Sonuçlu strateji bulunan bölgeler:** **Rusya (MOEX)** 2 aday/şüpheli, **Brezilya (B3)** 2 sonuç (ikisi de negatif veya zayıf), **Hindistan ve Endonezya (NSE/IDX)** sonuç sayfasında yalnız negatif itiraflar.
- **Sonuçlu strateji bulunmayan bölgeler:** **Afrika** (JSE, NGX, NSE Kenya, EGX için hiçbir proje çıkmadı), **Avrupa** (Almanca, Fransızca, İtalyanca, İspanyolca aramaları yalnız İngilizce araç ve rehberler getirdi), **Güney Amerika** (Arjantin, Şili, Kolombiya, Meksika için yalnız genel araçlar).
- **Tür dağılımı (sonuçlu):** swing 2 (MOEX 10 dk ortalamaya dönüş — aslında günlük içi; B3 MA kesişimi), scalp/daytrade 1 (WIN mini endeks, sonuç yok).
- **Yasak (martingale):** bulunmadı. Ancak Japonya/FX bölümünde zaten belirtilen uyarı burada da geçerli.

## En umut verici (sıralı, ama hepsi zayıf)

| Sıra | Ad | Bölge | Tür | Sonuç | Ana sorun |
|---|---|---|---|---|---|
| 1 | empenoso/backtrader-quickstart-template (MOEX, SMA kesişimi) | Rusya | swing | 2018–2025-08, yıllık %5.44, DD %13.4, 128 işlem, al-tut ile karşılaştırılmış | Basit kural, makul rakam, ama tek kural ve OOS yok |
| 2 | DKorolski/mean_rev_strategy (IMOEXF 10 dk ortalamaya dönüş) | Rusya | daytrade | 2020-11..2025-10: yıllık %19.3, DD %3.1, **Sharpe 4.44** (vol %5.7), komisyon var | **Şüpheli:** Sharpe aşırı yüksek, kayma yok, OOS yok, lisans yok |
| 3 | altino127/trading (SIGMA, WIN mini endeks ortalamaya dönüş) | Brezilya | scalp/daytrade | 826 gün backtest iddiası; sayı yok | Kural ve sonuç sayfada görünmüyor |
| 4 | wesleyzilva/RepoRobos (WIN gün içi robotlar, NTSL/MQL5) | Brezilya | daytrade | Sonuç yok | Dosyalar okunmadı |

**Not:** Bu sıralama "umut verici" anlamında değil; sonuç içeren tek olumlu örnekler bunlar ve hepsi doğrulanmamış. Brezilya'daki en ciddi çalışma (amenescal) negatif.

## Bölge bazında bulgular

### Rusya (MOEX)
- **empenoso/backtrader-quickstart-template** (Smart-lab yazısı ile bağlantılı): Backtrader tabanlı şablon; SMA kesişimi, SBER/GAZP gibi hisseler, 2018'den 2025-08'e. Yıllık %5.44, DD %13.42, 128 işlem, al-tut ile karşılaştırma var. **Lisans:** açık kaynak (kesin değil). **Değerlendirme:** rakamlar makul ve sade, ama tek kural, parametre seçimi ve OOS belirsiz.
- **DKorolski/mean_rev_strategy** (oluşturma 2025-02-27, güncelleme 2026-03): IMOEXF vadeli, 10 dakikalık mumlar, önceki günün aralığı ve kapanışına göre ortalamaya dönüş; durdurma, kâr al, zaman stopu (seviyeler belirtilmemiş). 2020-11-30..2025-10-18 backtest: toplam %38.55, yıllık %19.33, **DD −%3.1, Sharpe 4.44**, Sortino 9.02. Komisyon 0.017%/yan; **kayma yok**; OOS yok; lisans yok. **Değerlendirme:** Sharpe 4'ün üstü günlük-içi bir stratejide çok nadir; aşırı uyum ve kayma eksikliği ilk şüphe. Kendi kilitli-dönem disiplinimizle test edilmeli.
- **Araçlar (sonuç yok):** WISEPLAT/backtrader_moexalgo (MOEX AlgoPack + Backtrader, 2023-12, MIT); dtuminov/moex-backtest (2026-08); arbuzovv/zipFinam (Finam API + MOEX takvim); OsEngine (C#, MOEX + kripto, walk-forward aracı); Traidbot PR #5 (backtest modülü, komisyon ve buy&hold karşılaştırması).
- **Okunmadı:** Habr "Binance Futures RL-agent" (2025-03..06 backtest) — Rusça yazar, kripto, sonuç yazıda var ama bu turda açılmadı.

### Brezilya (B3)
- **amenescal/b3-systematic-strategy-backtest** (Portekizce, PETR4): Hareketli ortalama kesişimi (5/10/20 vs 50/100/200), 1 gün gecikmeli sinyal, 600 gün eğitim / 200 gün test kayan pencere, 0.1% maliyet (gerçek maliyetin iki katı). **OOS (2019-04..2026-06, yıllık):** strateji %9.06, Sharpe 0.12, DD −%39.96; buy&hold PETR4 %25.6, Sharpe 0.55, DD −%63.36; CDI %9.59. Blok bootstrap: al-tuta göre Sharpe farkı −0.43 (%95 CI [−1.07, 0.27]). **Değerlendirme:** Negatif sonuç ama dürüst bir WF tasarımı; bizim eleme kurallarımızın ("OOS PF", "sağlamlık") bir örneği olarak kullanılabilir. **Elendi.**
- **JoaoPauloZangrandi/overnight-intraday-br:** overnight anomalisi B3'te test edilmiş; tarife ve komisyon (1.15–2.21 bp) sonrası CDI'yi geçmiyor. **Elendi** (maliyet).
- **altino127/trading** ve **wesleyzilva/RepoRobos:** yukarıda; sonuç sayfada yok.
- **Diğer (okunmadı):** gkeiel/b3_trading_signals (Yahoo verisi, sinyal aracı), juninmd/dinheirama (faktör, walk-forward, PBO — araştırma platformu), araujovito/capital-allocators-backtest (2006–2025 kıyas), Felps-LDL/valuation-backtesting-b3 (2026-07, temel değerleme).

### Hindistan (NSE/BSE)
- **ryaneditraj/indiquant** (2026-07, PolyForm NC): araştırma işletim sistemi; sonuç yayınlanmamış; walk-forward ve sızıntı kontrolleri var. **Elendi** (sonuç yok).
- **Vinaysaikolla/NSE-Trading-Strategies-Backtesting** (2024-11): R uygulaması; sonuç görünmüyor.
- **palaemon-codes/vix-strategy-backtest** (2026-04): NIFTY opsiyonları ile India VIX ortalamaya dönüş — opsiyon, projede elenen kategori.

### Endonezya (IDX)
- **dylan-jaya/idx-quant-research-system** (BBCA, 2026-07 oluşturma, 2026-11 güncelleme): günlük 12-1 momentum sıralaması, uzun-only, 21 hisse + JCI. Yazar dürüstçe: **"BBCA al-tut'u risk ayarlı olarak, gerçekçi IDX maliyetleri sonrası hiçbir test edilmiş strateji geçemedi."** Lisans yok. **Elendi** (negatif sonuç, dürüst itiraf).
- Diğerleri (lintangalfath, daVinciVS, vincensiusprase, masopen99): araştırma/tarama araçları, sonuç yok.

### Afrika
- Sonuçlu strateji ve Afrika borsası (JSE, NGX, NSE Kenya, EGX) için proje bulunamadı. Genel araçlar (QTSBE, quanttrader, backtrader) dışında bölgesel bir kaynak çıkmadı. Bu alanda taramanın büyük kısmı yapılamadı; yerel forumlar ve Afrikalı trader blogları için ağ izni gerekebilir.

### Avrupa (DE, FR, IT, ES)
- Almanca, Fransızca, İtalyanca, İspanyolca aramalar yalnız İngilizce araçlar (backtesting.py, Freqtrade, VectorBT, TuringTrader) ve genel rehberler getirdi. Avrupa piyasası için (DAX, CAC, Borsa Italiana, IBEX) sonuçlu proje bulunamadı.

### Asya (genel: Vietnam, Tayland, Singapur, Hindistan dışı)
- Vietnam HOSE ve Tayland için hiçbir proje çıkmadı. Singapur ve Tayland bazlı açık kaynak strateji de bulunamadı. Asya'nın tümü için sonuçlu kaynak yok.

### Güney Amerika (Brezilya dışı)
- Arjantin, Şili, Kolombiya, Meksika için yalnız genel araçlar (ralphtradesz/trading-hub, Lucioelpro22/strategy-backtest-studio, haibingzhao/trading-backtest). Bölgeye özgü strateji sonucu yok.

## Dersler (bu tarama)
1. **Yerel borsalarda sonuç paylaşımı çok az.** Bulunanların çoğu araç veya yazarın kendi negatif sonucu.
2. **Brezilya ve Endonezya'daki dürüst çalışmalar negatif.** Yüksek maliyetli yerel piyasalarda basit kuralların al-tutu geçmesi zor — bizim karar 13 ölçütleriyle uyumlu.
3. **Sharpe 4+ ile sunulan Rus projesi** bizim için bir uyarı: kayma ve OOS yoksa bu rakam güvenilir değil.

## Eksikler (dürüst)
- Rusça kaynaklar (Smart-lab, Habr, Tinkoff yatırım sosyal) yalnız arama sonuçlarından; sayfaları açılmadı.
- Afrika, Avrupa, Asya (Vietnam/Tayland/Singapur) ve Güney Amerika (Brezilya dışı) için yerel forum ve blog taraması yapılamadı.
- X, Facebook, Reddit (bölgesel topluluklar) yine erişilemedi.

## Kullanıcı kararı gereken konular (bilgi için)
- **Rusya:** Smart-lab ve Habr için ağ izni eklenebilir (`smart-lab.ru`, `habr.com`). Bu iki kaynak Rusya'daki en önemli trader topluluğu.
- **Brezilya:** Portekizce kaynaklar için `medium.com` veya yerel forumlar (ör. `investidor10.com.br`, `fundamentus.com.br`) düşünülebilir — hangilerine izin vermek istediğinizi siz belirleyin.
- Bunların hiçbiri bu turda eklenmedi. Yalnız onay verirseniz eklerim.
