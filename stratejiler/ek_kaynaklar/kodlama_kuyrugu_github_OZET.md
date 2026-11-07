# GitHub taraması: kodlama kuyruğu (tekilleştirilmiş) — ÖZET

_2026-11-07. Girdi: `github_g1..g7_*.csv` içindeki `durum=yeni` satırlar. Çıktı: `kodlama_kuyrugu_github.csv`. Kod yazılmadı, commit edilmedi._

## 1. Sayılar

- Girdi: **295 satır** (g1 46, g2 87, g3 21, g4 30, g5 92, g6 4, g7 15) -> **137 aile** (79 tek satırlı, 58 çok satırlı; 17 aile birden fazla dosyadan satır birleştiriyor).
- Kodlanabilirlik (aile / satır): **A 46 / 95**, **B 68 / 169**, **C 23 / 31**.
- Durum (aile / satır): **yeni 100 / 204**, **ayar_modu 14 / 59**, **ayar 21 / 30**, **mevcut 2 / 2**.
- Çapraz: yeni A 30, yeni B 48, yeni C 22; ayar_modu A 5, B 9; ayar A 10, B 11; mevcut A 1, C 1.
- **Kodlanacak yeni sınıf/aile (yeni, A+B): 78.** Bunların 1'i (`gosterge-egim-yuzde-esik`) 33 satırı tek genel sınıfta toplar; gerçek iş yükü bu yüzden satır sayısından çok daha küçük.
- Gerçek tekrar (mevcut/ayar/ayar_modu) 37 aile / 91 satır: yeni iş 'sınıf yazmak' yerine parametre/mod eklemek.
- Beklenenden az `mevcut:` çıkması: ilk tarama zaten kodlu olanları işaretlemişti (`mevcut:...` satırları bu dosyaya girmedi); kalan 'yeni' satırların çoğu gerçekten yeni mantık çıktı. Kodlu karşılığı olanlar `ayar:` olarak işaretlendi (çekirdek aynı, parametre/küçük genişletme farkı).

## 2. Stil dağılımı

| Stil | Aile | Satır |
|---|---|---|
| swing | 46 | 96 |
| daytrade | 63 | 146 |
| scalp | 28 | 53 |

Not: kaynaktaki stil etiketleri sıklıkla gerçek zaman dilimiyle uyuşmuyor (1m/5m Gekko/NFI kuralları 'scalp' etiketli); karar 11 gereği scalp önerileri ≥15m'ye kaydırıldı. EA31337 satırları (57) 'daytrade' sayıldı, M1-H8 arası genel; 15m-1h önerildi.

## 3. `ayar_modu` aileleri (ayrı liste: yeni sınıf yok, mevcut genel sınıfa gösterge/mod eklenir)

| Aile | Hedef sınıf | Eklenecek mod | Satır | Öncelik |
|---|---|---|---|---|
| `yeni__bant-dokunusu-stokastik-onayi` | `swing__bant-donus` | onay={stokastik,stochrsi} (+ saf %B) | 3 | A |
| `yeni__gosterge-sinyal-sifir-kesisimi` | `swing__macd-sinyal` | gosterge={trix,tsi,kvo,obv,ad,pvt,mfi,uo,emv,decycler,tdld}; mod={sinyal,sifir,esik} | 12 | A |
| `yeni__kesit-skor-kombinasyonu-momentum-carry` | `pf__kesit_ls` | skor={kombine,carry} | 2 | A |
| `yeni__osilator-esik-donusu-gosterge-modlari` | `swing__rsi-asiri-donus` | gosterge={uo,tsi,stc,mfi,wpr} (mevcut: rsi, demarker) | 7 | A |
| `yeni__rotasyon-skor-modlari-triplersi-bb` | `pf__rotasyon` | skor={bb_uzaklik,hacim} + TripleRSI filtresi | 2 | A |
| `yeni__atr-chandelier-nrtr-donus` | `swing__supertrend-psar` | gosterge={chandelier,nrtr,ha_atr,atr_ma} | 6 | B |
| `yeni__bant-dokunusu-orta-cizgi-egimi` | `swing__bant-donus` | bant_tipi={envelope,tma,sve} + orta çizgi eğimi | 5 | B |
| `yeni__ichimoku-puan-skoru` | `swing__ichimoku` | mod='skor' | 1 | B |
| `yeni__mama-fama-itrend-cma-ma-turleri` | `swing__ma-kesisim` | ma_tipi={mama,itrend,cma,hma,wma} | 3 | B |
| `yeni__osilator-cizgi-kesisimi-genel` | `swing__macd-sinyal` | gosterge çifti + kaydırma/üst-TF seçeneği | 4 | B |
| `yeni__piyasa-rejim-filtreleri-genislik-ftd-dagitim` | `pf__ref_filtreli_long` | giris={genislik,ftd,dagitim_gunu} | 4 | B |
| `yeni__portfoy-agirlik-semalari-hrp-minvar-mvo` | `pf__sabit_sepet` | agirlik={hrp,min_var,mvo} | 4 | B |
| `yeni__rsi-dinamik-esik-tepe-dip-medyani` | `swing__rsi-asiri-donus` | esik_modu='dinamik_medyan' | 2 | B |
| `yeni__rsi-uyarlanir-esik-ve-periyot` | `swing__rsi-asiri-donus` | esik_modu='uyarlanir' (50±k·std / ATR oranı), gosterge='arsi' | 4 | B |

`ayar:` aileleri (21; mevcut sınıfın parametre ayarı veya çok küçük genişletme) CSV'de `durum=ayar:<ad>` olarak, hedef sınıfıyla birlikte duruyor. `gosterge-egim-yuzde-esik` (EA31337 'tek gösterge eğimi' kalıbı) hiçbir mevcut sınıfa gösterge modu olarak oturmadığı için `yeni` bırakıldı; mevcut sınıfların hiçbirinde 'N bar eğim + yüzde eşik' modu yok. Tek genel sınıf olarak kodlanması öneriliyor (aşağıda 2. madde).

## 4. Öne çıkan 15 aile

1. `yeni__rsi-boga-ayi-rejim-esikleri` — 7 satır, A, daytrade, yeni. 7 Gekko dosyası tek mantıkta: rejime göre (SMA50/SMA1000) farklı RSI periyodu ve eşik; kural tam, mevcut rsi-asiri-donus bunu karşılamıyor.
2. `yeni__gosterge-egim-yuzde-esik` — 33 satır, B, daytrade, yeni. 33 satırı (EA31337 + Gekko + OctoBot) tek genel sınıfa indirger: gösterge seç, N bar eğim ve yüzde eşik; en yüksek 'satır başına sınıf' tasarrufu.
3. `yeni__gosterge-sinyal-sifir-kesisimi` — 12 satır, A, swing, ayar_modu:swing__macd-sinyal. 12 satır, ayrı sınıf gerekmez: macd-sinyal'e gösterge seçeneği (TRIX, TSI, KVO, OBV, A/D, PVT, MFI, UO, EMV, Decycler).
4. `yeni__osilator-esik-donusu-gosterge-modlari` — 7 satır, A, swing, ayar_modu:swing__rsi-asiri-donus. 7 satır: rsi-asiri-donus'a UO, TSI, STC, MFI, Williams %R modu; yeni sınıf yok.
5. `yeni__atr-chandelier-nrtr-donus` — 6 satır, B, swing, ayar_modu:swing__supertrend-psar. 6 satır; Chandelier Exit, NRTR ve HA-ATR izleyen çizgi sistemleri supertrend-psar'a mod olarak girer.
6. `yeni__tepeden-dusus-yuzdesi-dip-alim` — 4 satır, A, daytrade, yeni. 4 kaynakta 'tepeden %X düşüşte al' (martingale ekleri atılmış); kapitülasyondan farklı ölçü.
7. `yeni__asiri-bolge-sonrasi-osilator-kesisimi` — 3 satır, A, daytrade, yeni. Son 10 mumda aşırı bölge + sinyal kesişimi; RSI+MACD ve ADX+Stokastik şablonu, kural tam.
8. `yeni__ust-tf-ma-yon-filtreli-ma-kesisimi` — 4 satır, B, daytrade, yeni. 4 satır, 3 repo (freqtrade, algo-trader çerçevesi, EA31337); üst-TF MA yön filtresi ma-kesisim'in eksik özelliği.
9. `yeni__kesit-skor-kombinasyonu-momentum-carry` — 2 satır, A, swing, ayar_modu:pf__kesit_ls. Portföy: çok-faktörlü z-skor ve funding carry skoru pf__kesit_ls'e mod; kripto evreni için uygun.
10. `yeni__portfoy-agirlik-semalari-hrp-minvar-mvo` — 4 satır, B, swing, ayar_modu:pf__sabit_sepet. Portföy: HRP, min-varyans, MVO ağırlık modları pf__sabit_sepet'e; karar 23'ün portföy katmanını zenginleştirir.
11. `yeni__ama-egri-donus-filtresi` — 3 satır, A, swing, yeni. Kaufman AMA eğri dönüşü + std eşikli filtre; 3 satır, kural tam, mevcut KAMA stratejisinden farklı.
12. `yeni__rsrs-egim-esigi` — 2 satır, A, swing, yeni. RSRS (yüksek-düşük regresyon eğimi) hem tek sembol hem rotasyon; kural tam, yeni gösterge.
13. `yeni__momentum-roc-filtreli-uzun-yonlu` — 3 satır, A, swing, yeni. ROC/Momentum>0 filtresi + MA kesişimi / stokastik geri çekilme; 3 basit kural, hızlı test.
14. `yeni__stockbee-momentum-burst` — 2 satır, A, swing, yeni. Günlük %4 kırılım + hacim + dar taban; hisse evreninde (Mag7+S&P>500 mlr$) uygulanabilir.
15. `yeni__ewo-ema-ofset-asiri-satim` — 5 satır, B, scalp, yeni. NFI/BBMod'un 5 satırlık ortak çekirdeği (EMA ofset + EWO + CTI + Williams); kripto için, yüzdeye çevrilerek B.

## 5. C (kural eksik/kodlanamaz) aileler

- `yeni__acik-islem-tikac-acici` (1): Çok-pozisyonlu portföy durumuna bağlı; tek-grafik kalıba uymaz; rejim girdisi (#18) eksik.
- `yeni__adx-evaluator-ema2-ema20` (1): Özet kesik; skor->karar eşleme yok.
- `yeni__btc-eth-rsi-es-zamanli` (1): Giriş eşik değerleri yok; çapraz-sembol koşulu (BTC+ETH) tek-grafik arayüzüne uymaz.
- `yeni__consensus-oy-puani-short` (6): Her oyun tanımı dış kütüphanede/eksik; eşik ve ağırlıklar kural olarak yazılı değil. dis__confluence-rank farklı (kendi 5 bileşenli skoru).
- `yeni__faktor-notr-agirlik-pole` (1): Alfa vektörü girdisi yok; pf__pca_statarb faktör nötr çekirdeğe yakın ama alfa kaynağı farklı.
- `yeni__hilbert-sar-rejim-siniflayici` (1): Hilbert HT_TRENDMODE TA-Lib'e özgü, tanım özetinde yok; ağırlık tabloları (asıl strateji) yok.
- `yeni__kismi-derisk-doom-stop` (1): Kademeli azaltma fikri risk modülü olabilir; ancak orijinal sistem grind ile yeniden ekleme yapıyor (martingale-benzeri riskli) ve stop yok: aynen alınamaz.
- `yeni__korelasyon-matrisi-batch-ornegi` (1): API örneği; tam giriş/çıkış kuralı yok.
- `yeni__ma-kirilim-aralik-orani` (1): Kural kesik ve 'dakika başına oran' tanımsız.
- `yeni__mabstra-ma-oran-kurali` (1): Oran eşikleri ve ortalama periyotları (mojo, hızlı, yavaş) kaynak özetinde yok: kural eksik.
- `yeni__nfi-pmax-ichimoku-moderi` (1): Moderi göstergesi tanımsız, alt kurallar kısmi; dis__pmax-giris ayrıca mevcut.
- `yeni__ozel-macd-turevleri` (2): Gösterge tanımları (umacd, crystalball) ve eşikler eksik/özel; Gekko özel kodu.
- `yeni__ozsermaye-egrisi-suzgeci-ve-kayan-sistem-secimi` (2): Meta/seçici katman, strateji değil; kayan seçim zaten karar 13 walk-forward çerçevesi; ikinci seviye aşırı uyum riski.
- `yeni__robbot-yukselis-ortalamasi-taban` (1): Taban türetimi ve profit parametresi tanımsız: kural eksik.
- `yeni__rsi-dip-klinger-donus-kademeli-satis` (1): Özet kesik; kademeli satış yapısı belirsiz.
- `yeni__rsi-kisa-uzun-ortalama-skoru` (1): Skor formülü özet dışında (uzun liste kesik); not eşlemesi belirsiz.
- `yeni__spx-sse-esikli-gecis` (1): Şanghai endeksi verisi yok; eşikler tek örnekte optimize edilmiş görünüyor. pf__gem benzeri çerçeve.
- `yeni__stratlv-sma-ustu-dar-bolge` (1): PingPong kısmı boş; üst bant (SMA x1.009) anlamı belirsiz.
- `yeni__tma-cg-kanal-oku` (1): Yeniden boyanan (repaint) özel gösterge; ok mantığı kapalı kaynak.
- `yeni__tongdaxin-stokastik-seciciler` (1): Çin platformu formülü; özet kesik ve çizgi tanımları eksik.
- `yeni__trailing-trade-atr-stop-piramit` (2): Giriş kuralı yok (gate); piramitleme mutlak üst sınır ister, ekleme riski %1 kuralıyla çelişebilir.
- `yeni__trend-yapi-sabit-seviye-yesil-mum` (1): Sabit seviye elle girilen parametre; otomatik seviye tanımı yok.
- `yeni__mum-formasyon-bit-alani` (1): Hangi desenlerin hangi bitte olduğu özette yok; swing__mum-coklu-formasyon 3+ mum desenlerini kapsıyor (sınıf zaten var).

## 6. Belirsizlikler

- **Özet kesikliği:** kaynak CSV'lerdeki `mekanik_ozet` bazı satırlarda kırpılmış (NFI, EA31337, Carstens, Tongdaxin, Andean, NWE). Bunlarda kural yalnız görünen kısımdan çıkarıldı, uydurma yapılmadı; eksik kısımlar `not` içinde 'devamı kesik' diye işaretli ve kodlayıcı kaynak satırdaki tam metne bakmalı.
- **Birleştirme kararı:** 'aynı mantık' sınırı yargı gerektirir. En geniş birleştirme `gosterge-egim-yuzde-esik` (33 satır) ve `gosterge-sinyal-sifir-kesisimi` (12). Kodlayıcı gerekirse alt aileye böler; satır listesi CSV'de.
- **ayar vs yeni sınırı:** EWO/CTI/Williams filtreleri, rejim-RSI eşikleri, üst-TF filtre, çıkış modu gibi eklemeler sınıfa parametre eklemeyi gerektiriyor. Parametre farkı olmayıp küçük genişletme isteyenler `ayar:` yazıldı ama `not`ta belirtildi (ör. dis__sqz-donus, dis__min10-dip, onceki__kapitulasyon).
- **Eşdeğerlik tespitleri:** Didi Index = SMA(3)/SMA(20) kesişimi (SMA8'e bölme sadeleşir); z-skor<=-2 = BB(20,2) alt bandı; Martingale V1/V2/V3 yalnız giriş kuralı alındı, katlama/ekleme kodlanmaz (martingale yasağı).
- **Mutlak eşikler:** MACD hist 0.025, ATR %0.01, EWO -5.585, pip eşikleri, USD hacim eşikleri fiyat/enstrüman birimine bağlı; B etiketli ailelerde yüzde/ATR'ye çevrilmeli.
- **Zaman dilimi:** Gekko/zenbot/EA31337 satırlarında zaman dilimi 'kullanıcı ayarı'; öneriler 15m-1d aralığında benim tahminim. 1 dk dayanaklı kurallar (speed, loosai, Strat, stopTrailing) 5m+'ya taşınınca anlam değiştirir.
- **Repaint/ileriye bakış riski:** TMA True, Nadaraya-Watson, ZigZag, fraktal, lineer regresyon mumları nedensel (onaylı/tek yanlı) uygulanmak zorunda; bu, orijinal sonuçlarla uyumu bozar.
- **Veri ihtiyacı:** funding (yalnız kripto), 168/252/1000 barlık ısınma, haftalık+günlük birleşimi, ABD hisse evreni (stockbee), BTC/ETH çapraz süzgeç; pf aileleri 3+ sembol ister. Şanghai endeksi, altcoin genişliği/dominans, KO/PEP çifti evrende yok.
- **Lisans:** 141 kaynak satırı GPL/AGPL repoda (CSV'de GPL kaynaklı satır içeren 64 aile işaretli) (EA31337, NFI, everget, ai-trader, OctoBot, banbot, freqtrade-strategies, MoniGoMani). CSV `not` sütununda işaretli; kural kendi cümlelerimizle, kod kopyalanmadan yazılır. Gekko repo lisanssız (çoğu alt dosya farklı yazar): aynı yöntem. Obfuske edilmiş Gekko dosyaları (2xTheMarket) çözülüp anlatım olarak alındı.
- **Önceki sonuç bilgisi:** bu CSV'lerdeki satırların çoğunun ek önceki-sonuç kaydı yok; kuyrukta öncelik 'kodlanabilirlik' (A/B/C) ve yeniliktir, beklenen getiri değil. Kitap iddiaları ve README kazanma oranları kanıt sayılmadı.
- **Doğrulama kapsamı:** mevcut kaydı (378 strateji) sınıf docstring/parametreleriyle karşılaştırdım; 'yeni' kararlarını tek tek koşturup eşleştirmedim. Aynı mantığın başka adla kayıtlı olma ihtimali düşük ama sıfır değil (özellikle gösterge-modlu dis__ sınıfları).
