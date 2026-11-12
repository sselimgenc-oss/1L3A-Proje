# Dış liste ↔ arşiv: derin geçiş (BENZERI_TEST'in açılması)

Hazırlayan: Claude (alt ajan), 2026-11-12. Repoda hiçbir dosya değiştirilmedi; yeni test koşulmadı (yalnız kod/ayar okundu, mevcut sonuç dosyaları okundu, bazı olay sayıları betikle sayıldı).

## Kullanıcıya özet

1. İlk geçişte "benzerini test ettik" denen ve kullanılabilir olan satırların sayısı ~340 değil **301**'di; hepsini tek tek açtım: eşleşen arşiv stratejisinin koduna, parametre ızgarasına, dış/kart ayarlarına ve hangi zaman dilimlerinde koşulduğuna baktım.
2. Sonuç: **89 satır (%30)** gerçekten kapsanıyor (fark önemsiz), **208 satır (%69)** "benzeri" ama dış kuralın bir parçası (çıkış, filtre, zaman dilimi, teyit) bizde hiç denenmemiş, **4 satırın** eşleşmesi yanlış.
3. Yani senin şüphen yerindeydi: "benzeri test edildi" çoğu zaman "aynı fikir denendi, bu ayrıntı denenmedi" demek.
4. Ama 208'in büyük kısmı önemsiz: **197'si** kozmetik ayrıntı ya da kanıtsız birleşik kural (107'sinde dış kaynakta hiç kanıt yok). Gerçekten dikkat çeken yalnız 11 satır.
5. Bunların 7'si ayrı bir bulgu: eşleştiği arşiv sınıfı **kodlanmış ama hiç koşulmamış** (Larry Williams volatilite kırılımı ×6, z-skor ×1). Bunlar "test edildi" sayılamaz.
6. İlk geçişin hata oranı (rastgele 20'şer satır, tohum 20261113): "ZATEN_TEST" örneğinde 2 kesin + 5 ince hata (%35 toplam); "BIZDE_YOK" örneğinde 1 kesin + 2 ince hata (%15 toplam). Örnek küçük, yüzdeler kaba.
7. 119 fikir ailesinde "elendi" denen 94 aileden yalnız 9'u gerçek geniş test (klasik RSI, Bollinger dönüşü, MA kesişimleri); 52'si kısmen (çekirdek denendi ama dış varyantın bileşeni değil); 33'ü zayıf temsilci; 22 aile arşivde hiç yok.
8. Neden böyle oldu: v2 yalnız varsayılan ayarla ve 1 günlükle koştu; geniş ayar taraması yalnız v1'de var; dış kurallardan çevrilen stratejilerin çoğu tek bir zaman dilimi çiftinde (1g/4s, 1s/30dk ya da 15dk/5dk) koşuldu; 26 sınıf kodlanıp hiç koşulmadı.
9. İki çelişki aslında "test edilmedi" değil "test edildi ama dış kuralın aynısı değil": Donchian ansamblı (motorun zorunlu ATR×3 stopu ve 2019+ evren farkı; kapı farkı −0,017 Sharpe) ve gürültü bölgesi gün içi momentum (brüt kâr 2,3 bps, maliyet 13 bps; kill 121. işlemde kesti).
10. Aday listesi 12 madde (ADAYLAR.md). Önerim: plan bir turda 2–3 teste izin veriyor; en temizi kodlu-koşulmamış ikili (volatilite kırılımı, adaptif trend 6s) ve Donchian'ı test değil ileri-veri izleme olarak ele almak.
11. Hiçbir şey canlıya dokunmuyor; kararlar sende. Bu analiz tek kişilik okuma yargısıdır (çalıştırılmış test değil); belirsizlikler en altta.

---

## 1. Yöntem (kısa)

- **Girdi:** `karsilastirma.csv` (707 satır), `strateji_listesi.csv`, `kanit_ekleri.csv`, `arsiv_envanteri.csv`, arşiv kodu (`motor/strateji/…`), ayar dosyaları (`stratejiler/kart_ayarlari`, `dis_ayarlari`), v1 WF sonuçları (`wf_evren.parquet`), v2 (`eleme.csv`), v3 (`eleme.csv`, `INCELEME_NOISE.md`).
- **Bir arşiv stratejisinin "ayar uzayı"** = varsayılan + kart ayarları + dış ayarlar + parametre ızgarası (v1 WF bunları tarıyor; v2 yalnız varsayılan). Zaman dilimi kapsamı = aynı gövde adlı swing/daytrade/scalp klonlarının v1 WF'te koşulduğu TF'ler (swing 1g/4s, daytrade 1s/30dk, scalp 15dk/5dk); `dis__…` stratejileri tek TF çiftinde.
- **Sınıf kuralı (katı):**
  - `FARK_ONEMSIZ`: giriş çekirdeği aynı; filtre, çıkış türü ve TF arşivdeki ayar uzayında ya da komşusunda (ara TF, ızgaranın hemen dışındaki sayısal uzantı, kozmetik stop/TP biçimi).
  - `FARK_TEST_EDILMEDI`: giriş filtresi/teyidi, çıkış mekanizması (zaman, iz stop, seviye, R-katlı hedef…), TF (uzak), rejim veya giriş tetikleyicisi arşivde bu çekirdekle hiç koşulmamış, **ya da** eşleşen sınıf hiç koşulmamış. "Anlam" sütunu ayrıca düşük/orta/yüksek (yüksek = hiç koşulmamış sınıf; orta = dış kanıt var ya da yeni bilgi içeriyor; düşük = kozmetik/kanıtsız bileşik). Bu anlam sütunu benim yargım.
  - `ARSIV_ESLESMESI_YANLIS`: ilk eşleşme çekirdeği içermiyor; doğru sınıf ayrı sütunda.
- Çıktı: `benzeri_derin.csv` (301 satır; 6 boyut: giriş, filtre, çıkış, stop, TF, yön).

## 2. Sonuç: 301 satırın yeni sınıfı

| Yeni sınıf | Satır | Pay |
|---|---|---|
| FARK_ONEMSIZ | 89 | %30 |
| FARK_TEST_EDILMEDI | 208 | %69 |
| ARSIV_ESLESMESI_YANLIS | 4 | %1 |
| Toplam | 301 | |

- Aile kırılımı: Trend 45 / 125 / 2, Ortalamaya dönüş 44 / 83 / 2 (önemsiz / test edilmedi / yanlış).
- FARK_TEST_EDILMEDI içinde anlam: yüksek 7 (hepsi **hiç koşulmamış** v3 sınıfı: S0078, S0244, S0248, S0249, S0250, S0321 = `v3__volatilite-kirilim-k05`; S0643 = `v3__z-skor-karsit`), orta 4 (S0147 ATH + 10×ATR iz stop, S0198 MA kesişimi + kanal tetiği, S0235 15 dk Donchian, S0447 BTC trend + ADX + geniş ATR iz), düşük 197.
- FARK_TEST_EDILMEDI'nin dış kanıt dağılımı: kanıt yok 107, backtest iddiası 79, akademik etiketli 20, canlı iddia 2. ("Akademik" etiketi dış listedeki etikettir; içinde tez, kısa dergi/rapor ve tek yıllık örneklemler de var, kanıt gücü değişken.)
- Test edilmeyen bileşenin türü (gerekçe metinlerinden kaba anahtar kelime sayımı, bir satır birden çok türe girebilir): çıkış mekanizması ≈ 95, filtre/teyit ≈ 66, TF ≈ 41, bileşik/çok koşullu ≈ 27.
- En çok işlenen arşiv ailelerinde: `rsi-asiri-donus` 11 önemsiz / 23 test edilmedi, `bant-donus` 19 / 14, `ma-kesisim` 13 / 15, `donchian-kirilim` 5 / 9, `ma-geri-cekilme` 1 / 12, `macd-sinyal` 1 / 12, `supertrend-psar` 0 / 9, `stokastik-donus` 0 / 8.
- Yanlış eşleşmeler (4): S0087 (DI kesişimi, `macd-sinyal` değil `dis__adx-di-esik-kesisimi`), S0314 (Donchian(200) MR, `bant-donus` değil `dis__ortalamaya-donus-gerilme` ters_kirilim), S0192 (AR+MA dizilimi → `dis__ma-dizilim-5-10-30`), S0571 (EMA oranı bandı → `dis__ema21-sapma`). Hepsinin doğru sınıfı FARK_TEST_EDILMEDI.

**Ailelere göre tipik "denenmemiş" ayrıntılar (kodla doğrulandı):**
- `macd-sinyal`: fiyat>EMA trend filtresi parametresi yok (yalnız sıfır filtresi); MACD+EMA100/200 kuralları bu yüzden denenmedi.
- `donchian-kirilim`: scalp (15dk/5dk) klonu yok; çıkış penceresi en çok 20 (TRB 50–200 yok); piramit yok.
- `ma-kesisim`: 30dk/1s klonu yok (swing 1g/4s + scalp 15dk/5dk); zaman çıkışı ayarı yok; RSI/ADX-dönüş/HA teyidi yok.
- `bant-donus`: giriş "banda dışına çıkıp içeri dönüş"; "alt banda temas = al" 1g'de yalnız `dis__ortalamaya-donus-gerilme` bb_stretch (iki bar %B<eşik) ile örtülü; Keltner/Donchian bant türü yok.
- `rsi-asiri-donus`: SMA5/SMA10 geri kazanım çıkışı yok (Connors tipi); bölge-içi tutma, MTF RSI ve zaman çıkışı yok.
- `stokastik-donus`, `ardisik-bar-tukenme`: düz K/D kesişimi (bölgesiz), kapanış-kapanış düşüşü (arşivde mum rengi), aynı gün çıkışı yok.
- Piramit / kâr-ekleme (Turtle satırları): motor tek pozisyon, test edilemez.

## 3. İlk geçişin hata oranı (denetim)

Yöntem: `random.Random(20261113).sample` (sıralı id listesinden) ile ZATEN_TEST (115) ve BIZDE_YOK (64) kümelerinden 20'şer satır; aynı yöntemle (arşiv kodu/ayarı açıldı, TF ve bileşen karşılaştırıldı). Satır satır: `denetim_ornek.csv`.

| Örnek | n | Doğru | İnce hata | Kesin hata | Kesin hata oranı (Wilson %95) | Toplam sorun |
|---|---|---|---|---|---|---|
| ZATEN_TEST | 20 | 13 | 5 | 2 | %10 (%3–%30) | %35 (%18–%57) |
| BIZDE_YOK | 20 | 17 | 2 | 1 | %5 (%1–%24) | %15 (%5–%36) |

- ZATEN kesin hatalar: **S0153** (eşleşen `v3__adaptivetrend-6s-momentum` hiç koşulmamış), **S0586** (dış kuralda RSI(2) aşırı satım eşiği yok; arşivde r3 modu eşikli).
- ZATEN ince hatalar: S0188 (kural günlük, `dis__volatility-system` yalnız 1s/30dk), S0003 (1s TF + Hilbert filtresi), S0030 (üst-TF SMA50 = 4s'te ≈ SMA600; arşivde 4s EMA50), S0021 (arşiv uyarlamasında iki AND koşulu eksik), S0011 (Turtle piramidi yok).
- BIZDE_YOK kesin hata: **S0034** (`v3__saatlik-asiri-tepki` aynı fikir; kodlu, koşulmamış). İnce: S0623 (`pf__pairs` benzeri; ilk geçişte aynı tür satırlar BENZERI sayılmıştı, tutarsız), S0163 (`pf__kesit_ls` skor=donus; düşük güven).
- Tüm 115 ZATEN içinde eşleşen arşiv durumu "test_edilmedi" olan **4** satır var (S0092, S0153, S0245, S0533 kısmen): bunlar örneklemden bağımsız kesin hata.
- Tüm 707 içinde hiç koşulmamış bir arşiv sınıfına bağlı **21** satır var (ZATEN 4, BENZERI 17; 10'u kullanılabilir).
- Çıkarım: ZATEN sınıfının yaklaşık üçte biri dış kuralın birebir kapsandığı anlamına gelmiyor; ama sadece 20 satırlık örnek, güven aralığı geniş.

## 4. Aile düzeyi kapsama (119 grup) — `aile_kapsami.csv`

Her aile için: eşleşen arşiv sınıfları, WF aday-ayar toplamı, TF kapsamı, v1/v2/v3 kapıları, koşulmamış sınıflar, paper/canlı bağı, dış kaynakların en güçlü kanıtlı satırı ve onun bizim koştuğumuzdan farkı, açık cevap.

| Cevap | Aile sayısı | Anlamı |
|---|---|---|
| GERCEK_TEST | 9 | Çekirdek ≥100 ayar ve dış satırların TF'lerini kapsayan TF'lerde koşuldu; dış varyantların çoğu bu uzayın içinde (M05, M09, M10, M11, M13, T16, T17, T21, T26) |
| KISMI_TEST | 52 | Çekirdek gerçekten denendi ama dış varyantların çoğu ek bileşen içeriyor (T24, T27, M01, M25, M35, T31, T01 …) |
| ZAYIF_TEMSILCI | 33 | Az ayar, tek TF çifti ya da evren yetersiz (M24 IBS, T22 MA dizilimi, T28 Faber, T44 ATH, T47–T49 kesitsel/rotasyon, T06 …) |
| TEST_YOK | 22 | Arşivde karşılığı yok (Hurst, kontrarian göstergeler, LW HL-ortalama zarfı, Larry Williams 9.1/9.2, HiLo, CDC, piramit, VIX/makro, arbitraj…) |
| KODLU_KOSULMADI | 1 | T10 Asya/Londra aralık kırılımı (3 sınıf kodlu, sonuç yok) |
| GERCEK_TEST_AMA_DISKARSILASTIRMA_FARKLI | 2 | T03 Donchian ansamblı, T08 gürültü bölgesi: v3'te koşuldu ama dış kuralın aynısı değil |

"Elendi" denen 94 aile: 9 gerçek, 2 özel, 52 kısmi, 31 zayıf. Yani **"elendi" ifadesinin 94'ünden yalnız 11'i "bu aile gerçekten ve dış varyantıyla test edildi ve elendi" diye okunabilir**; geri kalanı daha dar bir şeyin elendiğini söylüyor.

**Dikkat çeken aileler**

| Aile | Cevap | Not |
|---|---|---|
| T03 Çoklu Donchian ansambli | Test edildi, ama dış stop yapısıyla değil | v3 P6: Sharpe 0,978 ≤ al-tut 0,995 (−0,017). Bizde ek zorunlu ATR(14)×3 stopu; dış kuralda yalnız kanal-orta-nokta iz stopu; evren 2019+ (dış 2015+). |
| T08 Gürültü bölgesi | Test edildi, ama maliyet/çözünürlük farkıyla | DK_SPX 30dk; brüt +2,3 bps vs maliyet ≈ 13 bps; kill 121. işlemde (tüm 2645 işlemde PF 0,43); motor hatası yok (`INCELEME_NOISE.md`). |
| T06 Larry Williams volatilite kırılımı | Çekirdek **hiç koşulmadı** | Yalnız komşu Dual Thrust v1'de koşuldu. |
| M24 IBS | Zayıf temsilci, ama "az farkla" | pf__ibs_donus v1 WF 1d geçti; v2 Sharpe 0,44 < 0,5; net×2 +%8,9. |
| T44 ATH + geniş ATR iz | Zayıf temsilci | Arşivde n=50–200 gün, ATR stop 2–4; dış kural n sınırsız, 10×ATR. |
| T46 TSMOM / T28 Faber | Kısmi / zayıf | Kapılar (≥200 işlem, −%20 kill) yavaş sinyali yapısal eliyor; dis__sma200-ls K2 p=0,004 ama keşif çıkmadı. |
| M01 Connors RSI(2) | Kısmi | 116 ayar, 6 TF'de koşuldu; ama dış çıkış (SMA5 geri kazanım) bu çekirdekte yok; dış kanıt zaten çürütücü. |
| M13 Kripto BB scalp | Gerçek | v1'de 5/16 satır geçti; paper'daki ewo ailesi bu ailenin komşusu. |

## 5. Neden ilk geçiş şişkindi? (sistematik bulgular)

1. **v2 tek ayar:** v2 her stratejiyi yalnız varsayılan (ya da ilk kart) ayarla, 1 günlükte koştu; geniş ayar taraması yalnız v1 WF'te (çoğu 1g/4s veya klon TF'leri). v1 kapıları ve v2 kapıları farklı ön kayıtlarla.
2. **Tek TF çifti:** Dış kurallardan çevrilen 355 `dis__…` stratejisinin **hepsi** tek bir TF çiftinde koşuldu (1g/4s: 141, 1s/30dk: 138, 15dk/5dk: 76; eşleşen kümede 111 sınıf: 42 / 42 / 27). Dış satır başka TF'deyse ilk geçiş buna bakmadı.
3. **Klon boşlukları:** MACD/Donchian/MA kesişimi gibi ailelerin bazı TF klonları yok (ör. Donchian'ın scalp klonu, MA kesişiminin daytrade klonu).
4. **Hiç koşulmamış sınıflar:** 26 sınıf (23 v3 aday + 3 portföy) kodlanmış ama sonuç dosyasında yok; 21 dış satır bunlara bağlı.
5. **Parametre uzantısı ≠ aynı:** SMA 100/300, RSI(60), ROC(60), 20-40 gün sabit tutma gibi ızgara dışı değerler "benzeri" sayılmıştı; ben yakın komşusu koşulmuşsa önemsiz (güven orta), çıkış penceresi/tutma süresi gibi yapısal olanları test edilmedi saydım.
6. **Piramit/kademeli ekleme** (Turtle, antimartingale) motor desteği yok: bunlar "benzeri" değil "test edilemez".

## 6. Aday listesi

`ADAYLAR.md`: 12 aday, her biri için kural, neden aday, dış kanıt (iddia), uygulanabilirlik, veri, olay sayısı (betikle sayıldı), risk, felaket stopu notu. Başlıklar: A1 Kripto Donchian ansamblı, A2 Adaptif trend 6s, A3 LW volatilite kırılımı (kodlu-koşulmamış), A4 Gürültü bölgesi (maliyet sorusu), A5 ATH + 10×ATR iz, A6 IBS ortalaması + 1 gün, A7 DV2, A8 Hurst rejim filtresi, A9 Kontrarian göstergeler, A10 HL-ortalama zarfı, A11 EMA-eğim filtreli osilatör dönüşü, A12 Faber/TSMOM sepeti.

## 7. Belirsizlikler (açık yazıyorum)

- **Hiçbir şey çalıştırılmadı.** Sınıflar kod/ayar/sonuç dosyasını okuyarak yapıldı. "Fark sonucu değiştirmez" hükmü kanıt değil, kanıta dayalı akıl yürütme (aynı ailenin geniş ayar uzayının tamamı v1'de net/PF eksi ya da kapılarda kaldı).
- **Tek kişilik yargı.** Özellikle (a) ara TF'yi "kapsanmış" saymam (3s, 6s, 2s), (b) ızgara dışı sayısal uzantıyı önemsiz saymam, (c) "anlam" derecelendirmesi benim. Farklı bir okuyucu 89'u 70–110 aralığında bulabilir. Bu yüzden 208 sayısı katı bir "en az bir bileşen farklı" sayımıdır; "önemli fark" sayısı 11'dir.
- **Bant-dönüş ailesi:** "alt banda temas = al" ile "banttan içeri dönüş" farkını çoğu satırda önemsiz saydım (1g'de bb_stretch örtüşüyor); ben bunu ölçmedim.
- **Aile cevapları (GERCEK/KISMI/ZAYIF) eşik kuralıyla üretildi** (aday-ayar toplamı ≥100 ve dış TF'lerle ≥%65 uyum vb.); ilk geçişin grup→arşiv eşleşmesi kısmen yanlış olduğundan bazı grup sınırları gürültülü (ör. T21 "GERCEK" ama dayandığı `dis__ema-esik-trend` yalnız 1g/4s ve %0,5'e kadar eşik). `aciklama` sütunundaki elle yazılmış notlar (T03, T08, T44, M24 …) daha güvenilir.
- **Denetim örneği küçük** (n = 20 + 20); hata oranı aralıkları geniş. İnce/kesin ayrımı benim.
- **Olay sayıları** yalnız `veri/mumlar` 5 dk dosyası olan 22 sembolde (12 kripto + 7 hisse + XAU + WTI), geliştirme döneminde (≤ 2025-11-07); ATH/DV2/IBS/vol-kırılım tanımları kaynağın metninden basitleştirildi (DV2 yüzdelik penceresi 126 gün varsayım). İşlem sayısı değil sinyal sayısıdır.
- İlk geçişteki "kullanılabilir" kararı ve "BENZERI/ZATEN" ana sınırı bu çalışmada yeniden sorgulanmadı (BIZDE_YOK ve ZATEN yalnız 20'şer örnekle denetlendi; 227 "kullanılamaz" BENZERI satıra bakılmadı).

## 8. Dosyalar

Hepsi `/tmp/claude-0/-home-user/d9801314-f689-5b3c-ae41-5973e32ea499/scratchpad/derin_gecis/` altında:
- `RAPOR.md` (bu dosya), `ADAYLAR.md`
- `benzeri_derin.csv` (301 satır: dis_id, eslesen_arsiv_id, fark_boyutlari, yeni_sinif, gerekce + dogru_sinif_yanlis_eslesme_icin, fark_anlami, ek_etiket, ilk sınıf/eşleşme, dış kanıt türü, TF, piyasa)
- `denetim_ornek.csv` (40 satır, ZATEN 20 + BIZDE_YOK 20)
- `aile_kapsami.csv` (119 satır)
- `ara/` (betikler ve ara dosyalar: `build.py`, `aile.py`, `aile_yaz.py`, `denetim.py`, `sayim.py`, `k/*.txt` satır kararları)
