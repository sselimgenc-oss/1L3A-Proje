# GitHub taraması, grup g6_liste_notebook: özet

CSV: `stratejiler/ek_kaynaklar/github_g6_liste_notebook.csv` (389 satır, 15 sütun). Klonlar salt okunur okundu, koda dokunulmadı, kod kopyalanmadı. Notebook'lar python ile parse edilip kod ve markdown hücreleri (ve çıktı tabloları) okundu.

## Repo başına tablo

| Repo | Taranan dosya (find) | CSV satırı | Durum dağılımı | Lisans |
|---|---|---|---|---|
| paperswithbacktest/awesome-systematic-trading | 73 (61 QC strateji dosyası, 3 README, 4 betik, paper_meta.json) | 221 | mevcut 24, ayar 6, veri_yok 57, ml 1, kural_yok 133 | LICENSE yok |
| LLMQuant/awesome-trading-agents | 19 | 65 | kural_yok 63, veri_yok 2 | CC0-1.0 |
| leoncuhk/awesome-quant-ai | 36 | 61 | mevcut 8, ayar 8, yeni 1, veri_yok 19, ml 16, kural_yok 9 | Apache-2.0 |
| je-suis-tm/quant-trading | 177 (kod ve README'ler okundu, veri CSV/PNG atlandı) | 8 (11 mevcut satıra ek) | ayar 1, veri_yok 5, kural_yok 2 | Apache-2.0 |
| LongOnly/Quantitative-Notebooks | 5 (3 notebook) | 4 | yeni 2, ml 1, kural_yok 1 | Apache-2.0 |
| rolling-panda-san/notebooks | 35 (28 notebook) | 23 | mevcut 5, ayar 8, yeni 1, veri_yok 8, ml 1 | MIT |
| KidQuant/Pairs-Trading-With-Python | 3 | 1 | ayar 1 | LICENSE yok |
| PyPatel/Options-Trading-Strategies-in-Python | 8 | 5 | ayar 1, veri_yok 3, kural_yok 1 | LICENSE yok |
| rorysroes/SGX-Full-OrderBook-Tick-Data-Trading-Strategy | 27 (11 notebook dosyası, 6 benzersiz) | 1 | veri_yok 1 | LICENSE yok |

## Okunan klasörler (kanıt)

- **awesome-systematic-trading:** `README.md` (Strategies bölümündeki 61 makale tablosu, Trading bots tablosu, kütüphane/kitap/video/blog bölümleri), `README_zh.md` ve `README_ja.md` (aynı 65 makale bağlantısı, ek içerik yok), `static/strategies/*.py` (61 dosyanın tamamı, her birinin başlık yorumu ve QC uyarlama notları; yalnızca bir dosya, `pairs-trading-with-stocks`, uzantısız), `scripts/paper_meta.json` (3803 makale başlığı + piyasa etiketi), `scripts/*.py` (README üreten altyapı, strateji yok).
- **je-suis-tm:** kök dizindeki 10 strateji betiği (signal_generation kısımları), `Oil Money project/` (README, NOK/CAD/COP/RUB betikleri, üretim haritası), `Monte Carlo project/`, `Options Straddle backtest.py`, `VIX Calculator.py`, `Smart Farmers project/` (README + betikler), `Ore Money project/` (yalnız README ve CSV), ana README. Not: `data/` CSV'leri ve `preview/` görselleri okunmadı.
- **leoncuhk:** `README.md` (10 strateji bölümü, bulgu/makale/araç listeleri), `book/myquant/chapter1..11.md` ve `toc.md` (kod blokları okundu), `book/Systematic Trading ... .md` (Carver notları), `think/*.md` (5 not), `tools/pybroker.ipynb` (tüm hücreler), `docs/reviews/*.md` (PR inceleme kayıtları, strateji yok), `paper/*.pdf` (ikili, okunmadı; yalnız README özeti).
- **LLMQuant:** `README.md` (Agents, MCPs, Skills, Resources bölümleri: 115 giriş), `README.zh-CN.md` aynı içerik, CONTRIBUTING ve şablonlar (strateji yok).
- **Notebook repoları:** LongOnly 3/3, KidQuant 1/1, rolling-panda-san 28/28 (sandbox dahil), SGX 6 benzersiz notebook (Model_Selection tam, diğer beşinin fonksiyon ve markdown başlıkları; `.ipynb_checkpoints` kopyaları atlandı; `order_book_*.csv` veri dosyaları açılmadı). `Data_Problem.txt` (Çince, bozuk kodlama) başlık düzeyinde okundu.
- **PyPatel:** 4 strateji betiği + `README.md` + 3 C++ dosyası.

## Öne çıkan bulgular (yeni veya işe yarar)

Yeni (`yeni`) sayısı düşük çünkü bu kaynaklar zaten daha önce taranmış ailelerle (pf__kesit_ls, pf__rotasyon, pf__pairs, dis__tsmom vb.) büyük ölçüde örtüşüyor:

1. **ETF gün içi momentum (Gao 2018, rolling-panda-san):** seansın ilk 30 dk getirisi ve kapanıştan 60-30 dk önceki getiri, son 30 dk'yı aynı işaretle öngörür. SPY'da yalnız ilk dilim Sharpe 0.51, iki sinyal birlikte 0.59 (brüt); getirinin çoğu 2008 ve Mart 2020'den geliyor. Kripto 7/24 olduğu için seans tanımı yok; BIST/ABD hissesi gerekir. En ilginç yeni aile adayı.
2. **Karar 27 ile ilgili:** Connors dörtlüsü (3 gün düşüş + SMA200, 10 gün dip + SMA200, Double 7's, ay sonu 5 gün kala) BIST ve ABD hisse endekslerinde denenebilir. SPY'da brüt Sharpe 0.58-0.75, al-tut 0.55; ama getiri düşük (yıllık %3.6-7.3) ve hepsi mevcut ailelerin ayarı (ardisik-bar-tukenme, min10-dip, ay-donumu).
3. **Trend (rolling-panda-san):** Moskowitz TSMOM Sharpe 1.04 (50 vadeli, 60 yıl, brüt), 252 günlük kırılım 0.98, Çin vadelilerinde 1.31. Baltas 2020 sürekli sinyal (Newey-West t-değeri, ±1 kırpma) pf__cta'da yok: ayar adayı. Devir hızını %30'dan fazla düşürüyor.
4. **LongOnly/KO-PEP:** korelasyon bozulunca dünün kaybedeni al, gün içi (kaybederse bir gün daha) tut; kümülatif %335, kazanma %68, ama yazar alfanın 2011'den sonra çürüdüğünü ve son dönemin -%9.7 olduğunu kendisi yazıyor (yalnız iki hisse, aşırı uyum riski yüksek). Dikkatli ele alınmalı.
5. **PyBroker örneği:** dünkü dip altı kapanışta long (3 bar), dünkü zirve üstü kapanışta short (2 bar). Basit ve kural net; mevcut ailelerde birebir karşılığı yok.

Çalışmayan şeyler (kaynağın kendi raporu): emtia çarpıklığı Sharpe 0.01, intra-curve -0.12, Monte Carlo fiyat tahmini (yazı-tura doğruluğu), crack spread 1994 sonrası bozuluyor, FX carry 0.30, je-suis-tm Oil Money getirisi ortalama ~%2.

## Strateji içermeyen / zayıf repolar

- **LLMQuant/awesome-trading-agents:** 115 girişin tamamı LLM ajanı, MCP sunucusu veya beceri paketi. Deterministik kural yok. 57 ajan ve 8 beceri/MCP girişi `kural_yok` olarak satırlandı (CSV'de 65 satır); 40+ MCP (veri, borsa bağlantısı, araştırma, tahmin piyasası) altyapı olduğu için atlandı. İçinde sayılan "11 strateji", "6 strateji", "20+ strateji", "86 faktör" gibi içerikler README satırında listelenmiyor.
- **rorysroes/SGX:** strateji yok; tam emir defteri tick verisiyle 10 sn içinde dolum olasılığı tahmini (5 sınıflandırıcı). Hem emir defteri verisi hem ML gerektiriyor: `veri_yok`.
- **PyPatel:** 4 strateji da ya opsiyon/piyasa genişliği verisi (VIX, TRIN, put/call) ya da 55 günlük Donchian (Turtle). C++ dosyaları Monte Carlo opsiyon fiyatlayıcı, strateji değil.
- **KidQuant:** eğitim notebook'u; tek strateji (oran z-skoru çift işlemi) ve kod ile metin birbirine ters.
- **Awesome kütüphane/kitap/video/blog/kurs listeleri** (awesome-systematic-trading ~136 kütüphane, ~55 kitap, 22 video, blog, kurs; leoncuhk araç/veri/kitap listeleri): strateji değil, atlandı.

## Belirsizlikler ve dikkat notları

- `onceki_sonuc` içindeki tüm sayılar kaynağın kendi beyanı veya notebook çıktısı, doğrulanmadı ve çoğu brüt (maliyetsiz). awesome tablosundaki Sharpe değerleri makalenin kendi aktif penceresinde, brüt ve çok yüksek `t` ile seçilmiş en iyi 61 replikasyon; seçilim yanlılığı var.
- awesome-systematic-trading'in 61 makalelik tablosu ile `paper_meta.json`'daki kripto içeren 89 başlık için kural metni yoktur; `kural_yok`. 3803 başlığın kripto içermeyen kalan 3714'ü tek tek satırlanmadı (başlık + piyasa etiketinden başka bilgi yok, Binance evrenine uymuyor).
- awesome QC dosyalarındaki bazı eşleştirmeler `dis_envanter.csv`'deki "awesome" satırlarına ve `pf__kesit_ls`, `pf__rotasyon`, `pf__gem`, `pf__sabit_sepet`, `pf__trend_sepet`, `pf__pairs` docstring'lerine dayanıyor (kural okunarak doğrulandı). `dis_envanter.csv`'de 32 awesome satırından 23'ü `veri_yok` görünüyor; bunların faktör/rotasyon/çift/sepet/CTA olanları sonradan pf__ ailelerinde kodlanmış (pf__ docstring'leri bu awesome adlarını kaynak gösteriyor), dis_envanter durumu güncellenmemiş. Bu satırlarda `mevcut:pf__...` yazdım; eski dosyayı değiştirmedim.
- "Double 7's" kuralı rolling-panda-san notebook'unda yazmıyor (özel kütüphane); kural başka listelerden (repo_kodlari.csv A6-001) alınıp `ayar_durumu`ta belirtildi.
- KidQuant z-skor kodu, kendi metniyle ters işaretli çalışıyor; hangisinin doğru olduğu belirsiz.
- Baltas notebook'unda bir tablo satırında bozuk volatilite (470) görünüyor (veri hatası); o satırın Sharpe'ı güvenilmez, YZ tahmincisi satırı (1.07) kullanıldı.
- **Güvenlik notu:** `PyPatel/.../TRIN_strategy.py` ve `PCR_strategy.py` dosyalarında kaynak depoya yazılmış bir veri sağlayıcı (Quandl) anahtarı var. Değer CSV'ye veya bu özete kopyalanmadı; bu anahtar zaten kamuya sızmış sayılmalı ve projeye taşınmamalı.
- `book/myquant` kodlarının tamamı sentetik veri demosu: sonuç iddiası yok. Kitabın kendisi bazı ML örneklerinde doğruluğun ~%50 olmasını beklenen sonuç sayıyor.
- PDF'ler (`leoncuhk/paper/*.pdf`) okunmadı; yalnız README özeti kullanıldı, ilgili satırlarda belirtildi.
