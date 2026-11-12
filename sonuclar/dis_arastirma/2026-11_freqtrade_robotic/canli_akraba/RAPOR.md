# Canlı stratejilerin akrabaları: dis__ewo-ema-ofset ve dis__e0v1en

Kapsam: yalnız okuma. Repoda hiçbir dosya değişmedi, dış kod çalıştırılmadı (yalnız metin okundu; tarama betikleri scratchpad'de, `-I` ile).
Ekler: `e0v1e_karsilastirma.csv` (24 satır), `ewo_aile.csv` (96 satır = 95 strateji + 1 yardımcı dosya).

## Kullanıcıya özet
1. Canlı kodda lookahead (gelecekten bilgi sızıntısı) YOK. Kanıt: sinyal mum kapanışında üretilir, giriş sonraki açılışta (`motor/backtest/motor.py:4`); paper/canlı yalnız kapanmış mumları verir (`motor/canli/paper_veri.py:158`) ve her turda `gecmis[:t]` ile hesaplar (`motor/canli/paper_sinyal.py:5`, `:143`). Tekrar modu da uyuşuyor (ewo 46/46, e0v1en 81/83).
2. e0v1en gerçekten tek bir Freqtrade stratejisinin uyarlaması: ssssi/freqtrade_strs `E0V1EN.py` (dry_run). Ama uyarlama çok değişmiş: 5 dk yerine 15 dk, stop -%25 yerine -%6, zaman çıkışı ve CCI/fastk çıkışları kârda/zararda ayrımı kaldırılmış, trailing ve stop sonrası bekleme yok.
3. ewo-ema-ofset tek bir stratejinin uyarlaması DEĞİL; BBMod/NFI/ElliotV8 fikirlerinden bizim kurduğumuz bir sentez. Eşikler (EMA8×0,96, EWO%(5,35) < -3, RSI14<30, CTI<-0,5) kaynaklarda yok, bizim varsayımlarımız (kod yorumunda da "VARSAYIM" yazıyor).
4. Önemli ayrıntı: kod açıklaması kaynağı "BBMod ewo/ewo_2" diye gösteriyor (`d11i_github.py:314`), ama BBMod'un ewo kolları EWO'nun ÜSTÜNDE alım yapar (EWO > -5,585 ve EWO > 4,179); bizim kol EWO'nun ALTINDA (< -3) alıyor. En yakın akraba: NFI buy_13/buy_17 ve ElliotV8'in `EWO < ewo_low` dalı (ikisi de aşırı düşüşte alım).
5. Orijinal E0V1E dry-run sonucu (197 işlem, %73,6 kazanma, PF 1,48, 35 gün) bize kanıt olarak taşınamaz: 5 dk, -%25 stop, kısa dönem, canlı değil.
6. EWO ailesinde 21 dosyada (EI/Auto_EI "t4c0s" serisi) gerçek lookahead var (tüm veri üzerinden `.mean()`); katalogun otomatik taraması bunu 0 gösteriyor, yani kaçırmış. Bizim kodu ETKİLEMİYOR (bizim EWO sabit pencereli, nedensel).
7. Akrabalarda olup bizde olmayan korumalar: 1 saatlik trend filtresi (NFI), pump koruması (NASOS/EI3/NFI), BTC filtresi, e0v1en'de 24 saatlik değişim filtresi (e0v1en'de VAR, ewo'da YOK). Plan gereği canlıdayken eklenmeyecek; yalnız risk notu.
8. Orijinallerde "fiilen stopsuz" tasarım (-%25 ... -%99 stop) ve sık küçük kâr hedefi var; bizde sert stop var. Bu, bizim sonuçların orijinallerle kıyaslanamayacağı anlamına gelir (iyi yönde: daha az tail risk; kötü yönde: stop'ta kesilen işlemler orijinalde toparlanabilirdi).
9. Canlıyı etkileyen yeni risk bulgusu yok; bulgular belgeleme/beklenti yönetimi ve "kaynak kanıtı yok" niteliğinde.
10. Emin olmadıklarım: "53_Sharpe" adının anlamı (kodda açıklama yok), ewo'daki EWO şartının fiilen gereksiz (EMA8×0,96 ile zaten örtüşüyor olabilir) olup olmadığı (veriyle ölçmedim), aile sınıflamasının ~75 dosyası regex+örnekleme ile.

---

## 0. Canlı kodda lookahead kontrolü (doğrudan okuma)

Okunan: `motor/strateji/dis/d5_ek.py:573-610` (E0v1en), `motor/strateji/dis/d11i_github.py:313-339` (EwoEmaOfset), `motor/strateji/dis/_gosterge_d3.py` (D3Taban, hizli_stokastik), `_gosterge_d5.py:76` (cti), `_gosterge_d11i.py:47` (ewo_yuzde, williams_r), `motor/strateji/gostergeler.py` (sma/ema/rsi), `gostergeler_b2.py` (gecis, cci), `motor/strateji/dis/_gosterge_d4.py:32` (mum_gun_tahmin), `motor/backtest/motor.py`, `motor/canli/paper_sinyal.py`, `paper_veri.py`, `borsa/motor_kopru.py`.

- Tüm göstergeler geriye bakan: `rolling` (merkezsiz), `ewm(adjust=False)`, `shift(1)`, `pct_change(n)`, kayan pencere korelasyon (cti). `center=True`, `shift(-n)`, tüm-seri istatistiği yok.
- `mum_gun_tahmin` (`_gosterge_d4.py:32-40`) günde mum sayısını ilk 201 mumun medyanından kestirir; 15 dk için sabit 96. Sızıntı değil, sadece sabit kestirim.
- Motor zamanlaması: sinyal mum i kapanışı, giriş i+1 açılışı; stop mum içi high/low ile, aynı mumda stop+hedef olursa stop sayılır (`motor.py` başlık 4-8). Stop sinyal mumunun kapanışından kurulur (`d5_ek.py:607`), giriş fiyatı sonraki açılış: tutarlı.
- Canlı yolu: `tek_karar` yalnız `mumlar<=t` ile `sinyaller()` çağırıp son satırı alır; kapanmamış mum atılır (`paper_veri.py:158`). Yani repaint yapısal olarak imkânsız; ayrıca tekrar modu uyumu bunu ölçüyor.
- Küçük teknik not (hata değil): RSI Wilder özyinelemesi (`ewm(alpha=1/n, adjust=False)`) TA-Lib'in SMA tohumlamasından başlangıçta farklı; yüzlerce mum sonra yakınsıyor. Backtest ile canlı pencere uzunluğu farkı pratikte ihmal edilebilir (tekrar modu 46/46 ve 81/83 eşleşme bunu destekliyor).
- Sonuç: gerçek hata/lookahead şüphesi bulmadım.

## 1. Kaynak belirleme

### dis__e0v1en
- Kaynak: `ssssi/freqtrade_strs`, `binance/dry_run/E0V1EN.py` (+ `E0V1EN.json`). Kodda belge #16 olarak anılıyor (`d5_ek.py:82`). Envanter satırı: `stratejiler/ek_kaynaklar/github_g1_freqtrade.csv:77`. Yerel kopya: `/home/user/gh/ssssi_freqtrade_strs/binance/dry_run/E0V1EN.py`.
- Sürüm: EN = "E0V1E + 24 saatlik değişim filtresi". Aynı repoda `dry_run/buy1_and_buynew/E0V1E.py` önceki sürüm (filtresiz). Robotic deposundaki `E0V1E__2.py` ile `ssssi E0V1E.py` yakın akraba (Robotic sürümü ma120/ma240 çıkışları ve CCI mantığı eklenmiş).
- Orijinal parametreler (ssssi EN): TF 5m; buy_1: RSI20 düşüyor, RSI4<40, RSI14>42, close<SMA15×0,973, CTI20<0,69; buy_new: RSI4<34, RSI14>28, close<SMA15×0,96, CTI<0,69; 24s değişim kod varsayılanı -15..+50 (JSON'daki dry-run değerleri: buy_1 -25,8..+122,9; buy_new -24,3..+24,3). Stop -%25, trailing +%3'ten sonra %0,2, ROI yok, stop sonrası 96 mum bekleme.
- Bizim: kod varsayılanı ile aynı giriş eşikleri (kart ayarı yok, `stratejiler/paper_v2_seti.json` notu: "v2 VARSAYILAN ayarlar"). 24s filtresi: her iki giriş için -%15..+%50 (JSON'daki dry-run değerleri değil; buy_1/buy_new ayrımı yok).
- Bilerek yapılan uyarlamalar (kod yorumundan, `d5_ek.py:82-90`): 5m->15m; stop -%25 -> %6 ("orijinal çok geniş"); `custom_exit`'teki "kâr>-%3 iken CCI" ve "7s/10s kâr eşikli zaman çıkışı" kâra baktığı için vektörel sinyalde yok -> tek zaman çıkışı (28 mum = 7 saat); CCI periyodu belgede yok (20 varsayım); trailing opsiyonel ama verilmedi.
- Kayıtlı ama bilinmesi gereken farklar: fastk>84 çıkışı bizde kâr şartsız ve her iki etikette; orijinalde yalnız kâr>0 ve yalnız `buy_new`. CCI>80 çıkışı bizde kâr şartsız; orijinalde kâr>-%3 şartlı (daha kötü pozisyonda tutar). Zaman çıkışı bizde 7 saatte koşulsuz; orijinalde 7 saatte yalnız zarar >= -%5 ise, 10 saatte >= -%10 ise.

### dis__ewo-ema-ofset
- Tek kaynak yok. `d11i_github.py:314-321` kaynak olarak "freqtrade BBMod `ewo`/`ewo_2` ve iterativv/NostalgiaForInfinity X* (EWO + ofset + RSI/CTI/Williams; r_14/r_480)" gösteriyor; `stratejiler/kodlama_github_d11i.csv:12` ve `ek_kaynaklar/kodlama_kuyrugu_github_OZET.md:62` "5 satırlık ortak çekirdek" diyor. Yani bir sentez/yeniden yorum.
- Sürüm/parametre: bizim `ewo` kolu = close < EMA8×0,96 VE EWO%(EMA5-EMA35)/close×100 < -3 VE RSI14<30 VE RSI4<45 VE CTI20<-0,5; çıkış close>EMA16, 32 mum, 3×ATR stop (`d11i_github.py:322-339`). Kaynaklarda bu değerler yok: BBMod `is_ewo`: close<EMA8×0,942, close<EMA16×1,084, RSI4<45, RSI14<35 ve EWO(50,200)/low > -5,585 (yön ters); `ewo_2`: EWO > 4,179 ve 1h EMA200 yükseliyor (`/home/user/gh/ssssi_freqtrade_strs/binance/Archive/BBMod.py:532-541, 455-463`). NFI buy_13: close < SMA30×offset ve EWO(50,200) < -11,4, 1h trend korumalı (Robotic `Combined_NFIv7_SMA.py:2068`); buy_17: close<EMA20×offset ve EWO<-12,8.
- Bilerek yapılan uyarlamalar (kod açıklamasından): EWO mutlak fiyat yerine yüzdeye çevrildi ("VARSAYIM", ızgara -1,5..-6); `wr_uzun_n` 480 mum (5m) -> 160 (15m); yalnız long; r_deadfish ve gumbo (T3) kolları kodlanmadı; çıkış orijinallerde ROI tablosu+trailing+kârda satış iken bizde EMA16 üstü + 32 mum + ATR stop. `derin_dip` kolu kodda var ama varsayılan kapalı (`kol="ewo"`), yani canlıda kullanılan yalnız `ewo` kolu.
- Ölçek notu: kaynaklardaki EWO(50,200) 5 dk ölçeğindeki eşikler (-8..-20 veya +2..+12). Bizim EWO(5,35)%<-3 farklı bir ölçek; eşdeğerlik iddia edilemez.
- Uyarlamada "R tabanlı çıkış": ikisinde de çıkış R mantığı (stop = risk birimi, boyut stopa göre) motor/risk tarafından veriliyor; orijinaller ise yüzde stop + ROI. Bu bilinçli fark.

## 2. E0V1E dört dosya ile e0v1en: özet (ayrıntı `e0v1e_karsilastirma.csv`)

| Konu | Bizim e0v1en | Robotic E0V1E.py | E0V1E_53_Sharpe | E0V1E__2 | Cluc_E0V1E_ROI |
|---|---|---|---|---|---|
| Giriş | buy_1+buy_new tam | Neredeyse yalnız RSI4<40 (diğer koşullar yorumda) | Eşikler farklı: RSI4<65, RSI14>19, SMA×0,961, CTI<-0,04 | Bizimle aynı eşikler (+volume>0) | Farklı strateji: nfi32 kolu (CTI<-1,096 = ulaşılamaz, iddia), ewo_low/lambo2/local_uptrend kolları |
| Çıkış | fastk>84 veya CCI>80 + 28 mum | fastk(kârda)+CCI+ma120/240 | fastk>61 kârda + cci_loss + ma120 | E0V1E.py ile aynı mantık | Fisher/HA çıkışı + 7 kademeli ROI |
| Stop | %6 sabit | -%25 + trailing | -%25 + trailing | -%25 (devre dışı notu), kaldıraç 5 | özel stop, HSL -%13,4 |
| 24s filtresi | var (-15/+50) | yok | yok | yok | yok |
| TF | 15m | 5m | 5m | 5m | 5m |

- "53_Sharpe" nedir: dosyada hiçbir açıklama yok. Yorum satırları yalnız "Optimized minimal ROI / stoploss / buy / sell parameters"; parametre değerleri `DecimalParameter`/`IntParameter` varsayılanlarına gömülmüş (CTI -0,04, RSI4 65, RSI14 19, SMA 0,961, fastx 61). İddia: Freqtrade hyperopt'u Sharpe kayıp fonksiyonuyla çalıştırıp çıkan sonucun sınıfa gömüldüğü bir dosya ("53" büyük olasılıkla epoch/sıra numarası veya sonuç değeri; koddan kesinleştirilemez). Aynı depoda `mk4.py` dosyaları `SharpeHyperOptLossDaily` komutunu açıkça yazıyor (aynı yazar çevresi için ima, kanıt değil). Hyperopt sonucu olduğu için örneklem-içi uyum riski yüksek (iddia).
- Robotic `E0V1E.py` bozuk/kırpılmış görünür: `buy_1` ve `buy_new` koşullarının neredeyse hepsi yorum satırında; giriş fiilen "RSI4<40 veya <34 ve volume>0". Bizim stratejiyle kıyaslanabilir değil.
- Cluc dosyasında `nfi32_rsi_14` varsayılanı yanlışlıkla `buy_params['nfi32_rsi_4']`'ten (49) okunuyor (satır 242: `default=buy_params['nfi32_rsi_4']`); ayrıca `is_btc_safe` ve `is_pump_safe` yorum satırıyla kapatılmış ("# is_btc_safe & # broken?"), yazarın kendisi BTC/pump filtresini bozuk bulmuş.

## 3. EWO ailesi (95 strateji + 1 yardımcı) — ayrıntı `ewo_aile.csv`

"Aile" etiketi (catalog.json `family == elliott-wave`) gevşek: dosyada bir EWO fonksiyonu geçiyorsa giriyor. Bizimle aynı çekirdek olanlar küçük bir alt küme.

| Alt grup | Dosya | Bizimle ilişki |
|---|---|---|
| A1 Elliot çekirdeği (EWO + EMA ofset dip): ElliotV2/V4/V531/V5HO(+Mod2/3)/V7/V8HO/V8_original(+ichi)/Elliotv8, bestV2, overwatch, V8ichi, RalliV1 | 18 | Aynı çekirdek fikir: close < EMA×low_offset ve (EWO yüksek+RSI) veya EWO düşük. En yalın atalar. |
| A2 çekirdek + EWO açısı/kayan eşik: AngleWave, AngleWaveCT | 2 | Ek filtre. |
| A3 çekirdek + DCA/BTC/çok kol: twinturboV8, ttV8dca*, turbov8 | 7 | Ek kollar ve DCA (bizde yasak). |
| B NASOS (v4/v5/RV6 + modlar) | 8 | Aynı çekirdek, EWO low-bazlı; pump/BTC korumalı. |
| C1 EI3v2 cofi | 9 | cofi + EWO; pump/BTC korumalı, bazıları DCA/short. |
| C2 EI/t4c0s serisi (EI1/EI4/EI5/Auto_EI) | 21 | Çekirdeği paylaşır; EWO_MEAN genel ortalamayla lookahead içerir. |
| E NFI/Frog çok koşullu (EWO bir koşul) | 23 | EWO yalnız 30-80 koşuldan biri; yüzlerce koruma; stop -%99. |
| F farklı (ElliotWave 4h dalga sayımı, HEW, PCA3_short, custom diverjans, GeneTrader, eltoro/eltoro1_4 BTC-EWO rejim, DataframePopulator) | 8 | Ortak çekirdek yok. |

Bizim konumumuz: orijinal değil, ata da değil; bizim sürüm A1/NFI(buy_13/17) fikirlerinin torunu-yeniden-yorumu. A1'in "EWO düşük" dalıyla kavramsal olarak aynı kol (aşırı düşüşte dip alımı), ama RSI14 ve CTI süzgeçleri bizim eklememiz, eşikler bizimdir, çıkış tamamen farklıdır. Doğrudan "torun" demek için bir atadan kopyalanma kanıtı yok; "sentez" demek daha dürüst.

## 4. Kritik kontroller

### (a) Lookahead / bilinen hata
- Bizim iki strateji: yok (bölüm 0).
- Katalog: EWO ailesinde "high" lookahead bayrağı 5 dosyada, hepsi çekirdek dışı (`dirty LA/`): `DataframePopulator.py` (shift(-n), 591/630), `PCA3_short.py` (shift(-n) 704/737, center=True 467), `HEW.py` (argrelextrema 380, center=True 266), `GeneTrader_gen5...py` (center=True 539), `custom.py` (valuewhen shift(-n) 639).
- Katalogun KAÇIRDIĞI: C2 serisinde 21 dosyada (EI1/EI4/EI5/Auto_EI ve türevleri) `dataframe['EWO_MEAN_UP'] = dataframe['EWO_UP'].mean()` ve `dataframe['move_mean'] = dataframe['move'].mean()`: tüm veri setinin ortalaması, yani backtestte gelecek bilgisi (ör. `EI4_t4c0s_V2.py:308-311, 354`). Bu ortalama `buy1ewo/buy2ewo` eşiği ve custom_stoploss'ta kullanılıyor. Bu dosyalar "aile"de olduğu için, backtest sonuçlarına güvenilmemeli. Bizim motor EWO için sabit pencereli EMA kullanır, etkilenmez.
- Katalogun "medium whole_series_stat" bayrakları (CryptoFrog/NASOS/NFI46: HA_High/HA_Low) satır-bazlı `max(axis=1)`, yanlış pozitif.
- Bilinen hata: Cluc dosyasında CTI eşiği ulaşılamaz (`-1,096`), `nfi32_rsi_14` varsayılan kopyası; BTC/pump filtresinin "broken?" notu. `custom_exit`te global `TMP_HOLD` listeleri (Robotic E0V1E*): yeniden başlatmada kaybolan durum.

### (b) Bizde kaybolmuş koruma var mı
- ewo: 24s/pump/BTC/hacim filtresi yok. Orijinal BBMod `is_ewo` da yok ama NFI buy_13/17 (1h EMA50>EMA100, SMA200_1h yükseliyor, safe_dips), NASOS/EI3 (`pump_strength`, `recentispumping`), EI3 (BTC, hacim pump uyarısı) var. Plan §3 rejim filtresini bilerek dışarıda bırakıyor: yalnız not.
- e0v1en: orijinaldeki 96 mum stop sonrası bekleme yok; stop %6 olduğu için orijinalden çok daha sık stop yenir ve hemen yeniden girilebilir (ölçülmedi, risk notu). 24s değişim filtresi var ama JSON'daki dry-run değerlerinden daha geniş/ farklı (buy_new için orijinal dry-run ±24,3; bizde -15/+50).
- Orijinallerde zarardaki pozisyonu elde tutmak tasarımın parçası (stop -%25/-%99). Bizim sert stop daha güvenli ama "kaynak dry-run sonuçları" ile kıyas geçersiz.

### (c) Daha sağlam görünen varyant (iddia, doğrulanmadı)
- Doğrulanmış bir varyant yok. Katalogdaki 5 E0V1E dosyasının hiçbiri bizimkinden "daha sağlam" diye işaretlenebilecek bir kanıt taşımıyor: 53_Sharpe hyperopt sonucu gibi görünüyor (örneklem-içi), Robotic E0V1E kırpık, E0V1E__2 ssssi E0V1E ile aynı çekirdek, Cluc farklı strateji.
- EWO tarafında dikkat çeken tek fikir: NFI buy_13'ün "EWO düşük + 1h trend yukarı" koruması (bizim kolun trend filtresiz eşleniği). Bu, plan gereği şimdi eklenemez; ancak yeni ön kayıt + yeni paper ile test edilebilecek bir hipotez olarak not.
- ElliotV8_original / Elliotv8 en yalın, en çok kopyalanmış (18 dosyanın atası) ve lookahead'siz; ama kendi başına kârlılık kanıtı yok (kodda backtest sonucu/etiket yok).

## 5. Canlı için risk notları (öneri değil, bulgu)
1. Kanıt aktarımı yok: e0v1en'in kaynağındaki kayıt (35 gün dry-run, 5 dk, -%25 stop) bizim 15 dk/%6 stop kurulumunu desteklemez. Bizim kanıt zaten kendi testlerimizden (v2 holdout 46 işlem ewo, e0v1en 2025-11..2026-11 keşif p 0,0015 ama "KIRILGAN"); plan (§1, §10) bunu zaten söylüyor.
2. ewo'nun "kaynak doğrulandı" izlenimi yanlış olabilir: DURUM.md ve plan metinleri "Freqtrade topluluk stratejisinden uyarlandı" çağrışımı yapıyor; ewo için bu doğru değil, eşikler bizim. Bu, "bilinen çalışan ayar" güvencesi vermez; yalnız bizim holdout'umuz var (46 işlem).
3. EWO şartı muhtemelen yedekli (hipotez): close<EMA8×0,96 ile EWO%(5,35)<-3 yüksek ölçüde örtüşüyor olabilir; ölçülmedi. Doğrulanırsa "EWO" ismi sadece etiket olur; stratejinin gerçek davranışı "EMA'dan %4 aşağı + RSI14<30 + CTI dip" olur. Canlıya etkisi yok, anlatım/emeklilik kuralı yorumlarını etkiler.
4. e0v1en'in "fastk>84 veya CCI>80" çıkışı zararda da çalışır (orijinalde kârda); kayıpların %65'i tam stop (`sonuclar/teshis/stop_cikis/rapor.md`) bulgusuyla tutarlı: bizim uyarlamada küçük kâr + tam stop profili var. Orijinaldeki "zararı bekle" davranışı bilinçli kaldırıldı.
5. Katalog taramasına güvenilmemeli (EI serisini kaçırdı); bu rapordaki aile sınıflaması da regex+örnekleme (yaklaşık 20 dosya satır satır okundu, kalanı özellik çıkarımı ve ad benzerliği) ile yapıldı.

## 6. Emin olmadıklarım
- "53_Sharpe" anlamı (yalnız iddia).
- ewo'daki EWO şartının gereksizliği (ölçmedim, repoda hesap yaparak doğrulayabilirdim ama kod çalıştırmadım).
- A1 grubunun içindeki küçük farklar ve B/E gruplarının tüm koşulları: büyük dosyalarda (NFI 2.000-4.600 satır) yalnız EWO/offset/koruma satırlarına baktım.
- Orijinal E0V1EN canlı performansı hakkında kanıt yok (README'de copy-trading bağlantısı var, sonuç yok); dry-run görüntüsü (`dry_run_record_20250209_20250316.jpg`) bu raporda görsel olarak okunmadı, sayılar repodaki envanter notundan (`github_g1_freqtrade.csv:77`).
