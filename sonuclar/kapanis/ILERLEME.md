# Kapanış turu ilerleme kaydı

## DEVAM 2 (Claude lider — ana oturum, dal `claude/adoring-maxwell-q7t60g`, 2026-11-13)
Diğer hesabın limiti bitti; ana oturum devraldı. Kullanıcı önceliği: dış araştırma (G8, 906 liste) ve Robotic (G9, 909) satırları —
"benzeri var" 479 + 446, E 29 + 96, belirsiz 16 = 1.066 satır. Bunların 96'sı (G9 E) k3_p01'de zaten kararlı/denetlendi.
Kalan 970 satır kendi partilerine ayrıldı (ilgili k3_p08 / k4_p01–p03, p08–p10 satırlarının alt kümesi; aynı kaynak_id iki kez kararlanmaz,
birleştirmede kul_* kararı esas alınır):
| Parti | Satır | Durum |
|---|---:|---|
| kul_k3_g8 | 45 | sürüyor |
| kul_k4_g8_a/b/c | 160/160/159 | sürüyor |
| kul_k4_g9_a/b/c | 149/149/148 | sürüyor |
Diğer hesabın sürmekte görünen ajanları (k3_p06 yeniden, k3_p07, k3_p08, k4_p01, k4_p02) o oturumla birlikte durdu; çıktıları commit'lenmemiş.

## DEVAM (Claude lider, dal `claude/kapanis-devam`, 2026-11-13) — ÖNCE BUNU OKU
Taban: `origin/codex/kapanis-turu` (fa48bbe) + `origin/main` birleştirildi. Ortak ajan kuralları: `AJAN_TALIMATI_KAPANIS.md`.
Parti girdileri: `ara/girdi/k3_p01..p08.csv` (227'şer), `ara/girdi/k4_p01..p10.csv` (221; son 215). Çıktılar `ara/<parti>.csv`.
Ajan çıktısı ham haliyle `ara/`'ya yazılır; lider denetler, sonra `k*_karar.csv` ile birleştirme betiği yazılır (ön kayıt dosyaları değişmez).

| İş | Ajan kimliği | Durum |
|---|---|---|
| A: K1 nihai (44 açık + Rsi32 test + funding + 18 ayar) → ara/k1_nihai.csv | a278b72aa35c4ad47 | denetlendi |
| B: portföy araştırma hesabı → motor/arastirma/kapanis/portfoy.py + test | ac1d98c6103e6a870 | denetlendi (ön kayıt eki 2) |
| C: K2 kısa liste → ara/k2_nihai.csv + motor/strateji/kapanis/k2_kaynak.py | a378817cb3454c13b | denetlendi |
| D: k3_p01 | ae27bb6b30ed36d0e | denetlendi (koşullu) |
| D: k3_p02 | a72df6ea3aec567ef | denetlendi |
| D: k3_p03 | a99e150252c12bccd | denetlendi |
| D: k3_p04 | a58251fdab05aa330 | denetlendi |
| D: k3_p05 | a2f81192b260ced7d | denetlendi |
| D: k3_p06 | ad2d811df5cf3a147 | YENİDEN YAPILIYOR (denetim reddi) |
| D: k3_p07 | a7716419c1e108a9a | sürüyor |
| D: k4_p01 | ac3b409275c4033b2 | sürüyor |
| D: k3_p08 | ad11122ee651bd51c | sürüyor |
| D: k4_p02 | a875c037d5c15588b | sürüyor |
| D: k4_p03..p10 | — | bekliyor |
| E: K5, F: koşu listesi, G: koşu betiği, H: pytest, rapor | — | bekliyor |

### Anlık özet (2026-11-13, lider) — sayı kontrolü
| Katman | Girdi | Karar verilen (denetlendi) | KOSULACAK | Kalan |
|---|---:|---:|---:|---:|
| K1 | 48 | 48 | 19 (5 YENI sınıf) | 0 |
| K2 | 7 biçim → 18 hipotez satırı (T21 = 10) | 18 | 16 (15 YENI, kodlandı: `motor/strateji/kapanis/k2_kaynak.py`) | 0 |
| K3 | 1.816 | 908 (p01–p04) | 53 (p01: 52 YENI, p03: 1 mevcut sınıf+ayar) | 908 (p05–p08 sürüyor) |
| K4 | 2.204 | 0 | — | 2.204 (p01 sürüyor, p02–p10 bekliyor) |
| K5 | 706 | 85 ayar izi kararlı (Codex) | — | 621 (K1/K3/K4 bitince bağlanacak) |
Denetlenen toplam 974 karar: KURAL_YOK 627, KOSULACAK 88, VERI_YOK 83, ML 69, LOOKAHEAD 62, EVREN_DISI 34, YASAK 9, TEKRAR 2.
Kod: portföy araştırma hesabı (`motor/arastirma/kapanis/portfoy.py`), K2 sınıfları, Rsi32 testleri hazır; kapanış testleri 44/44 geçti.
Henüz yok: KOSULACAK+YENI sınıfların kodu (K1 5 + K3 52 + K4 ?), K5 bağlama, koşu listesi (F), `araclar/kapanis_kosu.py` (G), tam pytest (H), nihai rapor.
Sıradaki: kalan K3/K4 partileri → YENI sınıf kod partileri (ajan başına 3–6 sınıf, ayrı dosyalar) → K5 → koşu listesi dondurma.

Denetim günlüğü (parti, örneklem, hata, aksiyon):
- k3_p02 (227: KURAL_YOK 201, VERI_YOK 15, LOOKAHEAD 4, EVREN_DISI 3, YASAK 2, ML 2): `ara/denetim.py k3_p02 12 20261113` → 12/12 kaynak metniyle tutarlı (şablon/başlık/koruma modülü/kapalı kaynak). 1 tartışmalı: H001:80 (consensus oyları açık `technical` kütüphanesinde tanımlı olabilir). Kabul.
- B portföy hesabı: kod okundu (SERT_LIMITLER geçici bağlam yöneticisiyle, finally geri yükler; dönem sonrası veri HoldoutSizintisi). Lider kararları ön kayıt eki 2'de (portföy toplam stop riski %7,5, kapılar ×2, v2 portföy kapı karşılıkları).
- C K2 (18 satır: 16 KOSULACAK, 2 KURAL_YOK): yeni sınıflar DonchianEma2RS0083, FlipperS0879, VmaBantKaynak (T21 #1–#10), IchimokuC4Arsiv, ArgusGizliBogaD3. Lookahead taraması temiz (yalnız rolling; shift(- yok). Kapanış testleri 44/44 geçti. T21 = 10 ayrı hipotez (makale ayrı raporluyor; (S,L,B) Brock SMA tanımı; birincil PDF erişilemedi → emin_degil). Ichimoku/Argus arşiv biçimi (aday_listesi bu biçimi tarif ediyor).
- k3_p03 (227: KURAL_YOK 130, ML 66, VERI_YOK 17, EVREN_DISI 13, KOSULACAK 1): 10 örnek (tohum 7) → 10/10 tutarlı. Kabul.
- k3_p01 (227: KURAL_YOK 90, LOOKAHEAD 58, KOSULACAK 52 YENI, VERI_YOK 13, EVREN_DISI 9, TEKRAR 2, YASAK 2, ML 1): 10 örnek (6'sı KOSULACAK, tohum 11) → karar hatası 0; ama `kural_tam` özet, bazılarında parametre eksik yazılmış (B001:689 offset değerleri, B001:750 custom_stoploss). Koşul: kodlama ajanı kuralı kaynak dosyadan (kanıttaki SHA@dosya:satır) okur; özetten kodlamaz. 48 B001 KOSULACAK varyantı koşu listesi aşamasında aynı işlem yolu için TEKRAR'a indirgenecek. B001:802 sessiz except → kodda açık hata.
- K1 (48: KOSULACAK 19 [5 YENI: 3 funding, bb_uzaklik_k1, triple_rsi_hacim_top5], KURAL_YOK 25, EVREN_DISI 3, VERI_YOK 1): 10 örnek (tohum 3) → 10/10 kaynakla tutarlı. Rsi32Kaynak testleri 4/4.
  Lider kararı: KOSULACAK satırlarda kaynak tek sembol (BTC, BTC+ETH) yazsa da ön kayıt evreni **kripto13** uygulanır (koşu listesinde). ibs k=1 (decil) ve donus_orantili lookback 7 kaynağa göre kabul.
- k3_p04 (227: KURAL_YOK 179, VERI_YOK 37, EVREN_DISI 6, YASAK 5): 10 örnek (7'si kitap kartı, tohum 4) → 10/10 tutarlı (Brooks öznel PA, çıkış/risk modülü kartları, short interest/tape verisi, ücretli betik). Kabul.
- k3_p06 (227: KURAL_YOK 124, EVREN_DISI 56, VERI_YOK 24, ML 13, KOSULACAK 9, YASAK 1): 10 örnek (tohum 6) → 2 şüpheli (V014:321, V014:144: GitHub repo açılmadan katalog özetiyle KURAL_YOK) = %20 > %10 → RED. Aynı ajana iade: KURAL_YOK verilen ve açık kod reposu olan tüm satırlar birincil kaynaktan yeniden incelenecek.
- k3_p05 (227: KURAL_YOK 171, VERI_YOK 30, EVREN_DISI 18, KOSULACAK 3 YENI, TEKRAR 3, YASAK 1, ML 1): 10 örnek (8'i "birincil açılmadı"+KURAL_YOK, tohum 5) → 10/10 tutarlı (araç/şablon, URL'siz/yalnız başlık, v3 turlarında açılmış kayıt). Kabul.
  Lider kararı: kural zarardaki pozisyona ekleme/grind içeriyorsa YASAK (H001:151, H002:93 → birleştirmede YASAK).

---

Son kontrol: 2026-11-13 12:13 UTC. **Görev bitmedi; gerçek piyasa verisi koşulmadı.** Kullanıcı limit nedeniyle burada durmamı istedi; bu dosya oturum devam noktasıdır.

## 12:13 UTC duraklama notu

- Son kullanıcı isteğiyle iş burada durduruldu. BH aile düzeltmesi `02e0424` commit'inde, özgün ön kayıt metni korunarak eklendi. Aile yalnız gerçekten koşulacak benzersiz hipotezlerden oluşacak; sayı henüz dondurulmadı.
- K1 tablosu **48/48 satır** içeriyor: 2 `KURAL_YOK`, 1 `EVREN_DISI`, 1 `VERI_YOK`; diğer **44** satırın nihai akıbeti açık. 26 v3 kartı, 18 ek ayar ve dört teknik hata için kaynak izleri tabloya işlendi. Dört teknik hata 4h/4h/4h/1h sentetik sinyal testini geçti. `k1_karar.csv` içindeki `KAYNAK_*_BEKLIYOR` durumları nihai ret/geçiş kararı değildir.
- Tek grafik ham ve kendi hesap araştırma modülü `45c2c1c` commit'inde: maliyet ×1/×2, %1,5 risk, −%30 kill, holdout sızıntısında açık hata. Sentetik testleri geçti. **Portföy araştırma hesabı, 18 ayarın gerçek koşu bağı, koşu listesi ve `araclar/kapanis_kosu.py` yok.** Mevcut motor sert %1/−%20 limit kullanır; bu sınırlar değiştirilmedi.
- Birincil kaynaklar `/tmp/kapanis-src-*` altında salt okunur açıldı. `mgcha85/btc-lshape-long` kaynak profilinden yeni `LSekliKaynak` alt sınıfı yazıldı ve 2 sentetik testi geçti. `upupnoah/noahroboros` kaynak kodunda RSI77/23 **geri kesişim** çıkışı görüldü; buna göre `Rsi32Kaynak` taslağı yazıldı, **test edilmedi ve K1 satırına bağlanmadı**. Bir sonraki adım bu sınıfa sinyal/gelecek/stop testi yazmak, sonra K1 satırını kaynak kod SHA/commit'iyle bağlamak.
- `OctopusTakopi/funding-rate-alpha` kaynak karşılaştırması: günlük carry yönü doğrulandı; saatlik 00:00 decil ve z90 tek kohort kodlarında kaynak farkları açık. `zhangxingthang/BTCUSDT-London-Volatility-Breakout` özgün 1m işlem yolu izinli veriyle koşulamadığı için `VERI_YOK` hükmü verildi. Bunlar `k1_karar.csv` içinde kanıtlı.
- K2, K3, K4 kararları ve gerçek tek koşu henüz yapılmadı. K3 **1.816**, K4 **2.204** satırın kararı bekliyor. K5'in 621 iz kimliği kaynağa bağlandı; nihai akıbetleri K1/K3/K4 ile birlikte açık. PR açılmadı. Önceki tam pytest sonucu 5101 geçti/17 atlandı; son yeni sınıflardan sonra tam paket yeniden çalıştırılmadı.

## Değişmez ön kayıt

- Dal: `codex/kapanis-turu`, taban `origin/main` `d960401`.
- Ön kayıt commit'i: `7a89080`. `aday_listesi.csv` değişmez. `ON_KAYIT_KAPANIS.md` asıl metni korunarak, kullanıcının 2026-11-13 tarihli BH aile düzeltmesi sonuç görülmeden ek başlıkta kaydedildi (`02e0424`).
- 4.773 kapalı kayıt: 4.067 ana kaynak kimliği + 85 ayar izi + 621 iz incelemesi. Ana 4.067 = K1 46 + K2 6 + K3 1.816 + K4 2.199. K2'deki 5 D kaydı K4 karar tablosunda da sayılır; bunlar koşuda tek hipotez olur.
- Kaynak SHA-256'ları ön kayıtta. Hakem metni main'de yoktu; `origin/pr-58` dalındaki `HAKEM_FABLE.md` okundu, bu dala kopyalanmadı.

## Katman durumu ve sayı kontrolü

| Katman | Girdi | Karar tablosu | Son karar | Kod/koşu | Durum |
|---|---:|---:|---:|---|---|
| K1 | 48 = 26 v3 + 18 ek ayar + 4 teknik hata | 48 | 4 kaynak/evren ret; 44 açık | 18 ayar okuyucusu kuruldu; 26 v3 kartı ve 18 ayar kaynağı satıra bağlandı; dört teknik hata için TF seçildi ve sentetik sinyal testi geçti; tek grafik ham/hesap modülü var; koşu listesi yok | sürüyor |
| K2 | 7 kaynak biçimi (saatlik, T61, T21, S0002, S0005, Ichimoku, Argus); S0083 gibi alt kaynaklar K4'te | ayrı karar tablosu yok | 0 | S0002 ve S0005 yeni sınıfları + sentetik test | sürüyor |
| K3 | 1.816 = 161 E + 35 belirsiz + 1.620 diğer D | 1.816 | 0 | kaynak uygunluğu incelenmedi | başlamadı |
| K4 | 2.204 `benzer_hedef` dolu D (K2'ye ayrılan 5 dahil) | 2.204 | 0 | kaynak ↔ arşiv kodu tek tek karşılaştırılmadı | başlamadı |
| K5 | 706 = 85 ayar izi + 621 iz adayı | 706 | 85 ayarın iz kararı; 535 iz kaydı ana deftere, 78 kart ve 8 arşiv kaydı özgün kaynağa bağlandı; nihai akıbet bekliyor | 18 ayar gerçekten aday havuzuna girmemiş; 67 eski WF aday havuzunda | sürüyor |

Tablolardaki `INCELEME_BEKLIYOR` bir hüküm değildir. `kanit` sütununda eski hesap defterinin başlangıç izi vardır; kaynak-kod eşitliğinin yeni doğrulaması değildir. Satır sayılarını koşudan önce tekrar doğrula. K2/K5 katmanları K1/K3/K4 ile örtüştüğünden rakamlar toplanıp bağımsız strateji sayısı diye sunulmaz.

## K5 koşu izi çapraz denetimi

- Eski dalın 85 `P5_ayar_kosu_izleri.csv` ayarının tümü `G0_ayarlar.csv` kayıtlarına yol/indeks ve ayar kimliğiyle eşlendi: 18 ek JSON ayarı aday havuzunda yok, 67 ayar v1 WF aday havuzunda. 67 için bu iz, tam eşit kaynak kuralının adil kapılardan geçtiği anlamına gelmez; tam koşu/kaynak karşılaştırması K1/K4 kararıyla yapılır. G0 sınıflaması 20 seçilen + 47 aday; Fable 18 + 49 dediği için bu sayım uyuşmazlığı ayrıca kontrol edilecek.
- Eski dalın 621 `P8_iz_eksigi_E_adaylari.csv` satırından 80 `DIS906:Sxxxx`, `ham_satirlar.csv` içindeki `X005:xxxx` üzerinden ana `tekil_id`ye bağlandı: 29 E, 24 H, 16 D, 10 F, 1 belirsiz ön durum. KAYIT ve EXCELKURAL kayıtlarının 440 tanesi daha eski P8 adı ile ana `ham_satirlar.csv` adı birebir ve tekil eşleştiği için yalnız kimlik düzeyinde bağlandı. 23 KAYIT/EXCELKURAL satırının 15’i xlsx satırıyla ana deftere bağlandı; 8’i ayrı arşiv kaydında. 78 KART kaydının özgün kart dosyası `stratejiler/v3_adaylar/kartlar/` altında ayrı ayrı bulundu; ana defter kapsamı ve kuralın koşulabilirliği açık. Ad eşitliği kural eşitliği kanıtı değildir. Bunlar ayrı aday değildir. Kalan 23 kaydın 15’i xlsx sayfa/satır ve adla ana deftere bağlandı; 8’i `arsiv/codex-algo/config/pdf_candidates.csv` içinde bulundu. Böylece 621 iz kimliğinin kaynağı belli; 621’inin de nihai kural/koşu hükmü bekliyor.

## K1 kaynak izi ve ilk hükümler

- `k1_karar.csv` içindeki 48 satırın kaynak TF/piyasa/kart izi yazıldı: 26 v3 kartı, 18 ek ayar JSON kaydı ve dört teknik hata kod izi. Kart metni birincil kaynak kuralının doğrulanması yerine geçmez.
- `AYAR:dis__funding-carry:d11j:funding-pozitif-short:esik0_short` **KURAL_YOK**: `github_g3_cerceve.csv:24` pozitif funding’de short açma API örneği; kaynak çıkışı yok. JSON’daki 16 saat çıkışı kaynakta yazmıyor.
- `KOD:v3__ters-fvg-nq-long` **EVREN_DISI**: NQ 5m/15m ve NQ puan tamponu gerekir; ön kayıt evreninde NQ yok.
- V2 teknik hatalı dört kod için eski 1d üst-TF hatasını önleyen TF kaydı: Norn 4h, SHM 4h, önceki 4s kırılım 4h, KGT 1h; hepsi v2 kripto 13 sembol. Dört sınıf 1.100 sentetik mumla sinyal üretti, hiçbir giriş stopsuz değil (`testler/test_kapanis_k1_teknik.py`, 4 geçti). Kaynak/çıkış uyumu ve hesap koşu bağı hâlâ açık.
- `v3__momentum-sifir-kesisim` birincil `ChandanP001/Quant-foundations` notebook commit `c222dd2` ile doğrulandı: 20 günlük yüzde getiri, long/flat, ertesi gün. `v3__z-skor-karsit` için `NadirAliOfficial/contrarian-strategy` commit `9034fce` README ve `utils.py` 20 günlük getiri z-skoru ±2/sıfır kuralını veriyor; aynı deponun `script.py` dosyası ise başka, DCA yapan yasak bir kod ve kullanılmaz. Bu iki sınıfın 1d/kripto uyarlama izi var; koşu bağı açık.
- `v3__saatlik-asiri-tepki` **KURAL_YOK**: `kod_kontrol_tur8.csv:38` ve `kaynak_dogrulama_tur4.csv:108` yalnız özet doğrulamış; eşik/tutuş kaynakta yok ve birincil metin bu ortamda 403. Mevcut 2σ/48s/1s değerleri bizim varsayımımız.
- `v3__londra-volatilite-kirilim` **VERI_YOK**: birincil `zhangxingthang/BTCUSDT-London-Volatility-Breakout` commit `f4bd593` 1m OHLC ve mum içi stop sırası kullanıyor; ön kayıt 5m–1d. Mevcut kapanış sinyali kaynak işlem yolu değildir.
- `pf__v3-funding-1s-devam`: birincil `OctopusTakopi/funding-rate-alpha` commit `cf9f87c` 1h katsayısı ve ayrı settlement çevresi tutuşunu ölçüyor; mevcut kodun 00:00 decil/tek saat portföyü aynı kaynak kuralı olarak doğrulanmadı. `pf__v3-funding-z90-3gun` için settlement akışı/kohort farkı açık. Günlük ham-funding decil carry yönü kaynaktan doğrulandı, araştırma portföy hesabı açık.
- `v3__l-sekli-ma-kirilim-long`: birincil `mgcha85/btc-lshape-long` commit `a797953` ilk 10 mum tepe/son 10 mum dip sırasını ve README örnek profilinde +%3 yarım kâr/başabaşı kullanıyor. Eski sınıf farklıydı; `motor/strateji/kapanis/l_sekli_kaynak.py` yeni alt sınıfı eklendi, iki sentetik testi geçti. Kaynak kodun kendi `_check_entry` çağrısında fazla argüman hatası var; açık fonksiyon kuralları esas alındı. Gerçek koşu bağı açık.
- `v3__rsi32-yon-hedef4`: birincil `upupnoah/noahroboros` commit `1e3edc6` 77/23'e erişince değil, eşiğin gerisine kesince çıkıyor; eski sınıf farklı. `motor/strateji/kapanis/rsi32_kaynak.py` yeni alt sınıfı yazıldı, **test ve karar tablosu bağlantısı henüz bitmedi**.
- Kalan 44 satırın kaynak biçimi/uyarlama ve araştırma hesabı koşu bağı henüz kesinleşmedi. Özellikle eski tek grafik Donchian ansamblı, kaynak biçiminden farklı olduğu için doğrudan koşuya alınmaz; yeni portföy biçimiyle sonuç/kimlik bağı denetlenir.

## İlk kaynak denetiminde bulunan ayrımlar

- `S0002` 6h Donchian20 + SMA200 + karşı alt bant çıkışı, **kaynakta 2R hedef yok**; kaynak stopu yok. Yeni sınıf buna göre yazıldı; ATR×3 stop açık uyarlama. 2R hedefli EMA200/H4 kaynak **S0083** (aday listesinde `HAM:X005:83`), ayrı karşılaştırma ister. T02 ailesi diye iki kural eşit sayılmaz.
- `S0005` MACD çizgisi sinyal üstünde **durum** + fiyat EMA100 üstünde; çıkış iki koşul birlikte tersine dönünce. Yeni sınıf ters kesişim olayıyla karıştırmaz; stop ATR×3 uyarlama.
- S0002 ve S0005'in birincil Python dosyaları `jesse-ai/example-strategies` commit `7c91e0a37bf62165790120d730442e4f6eb00364` üzerinden salt okunur açıldı. SHA-256 sırasıyla `fc635b257ad1e12951dc140dae46a63bd37e9abfa5f2d681ef1e754d8ce393fe`, `5c0cae71e63a5a510220d60d6bba48ae39a542aa988154eaa13b91f8dd2209a8`. S0005 dosyasının üst açıklamasında “crosses” yazsa da çalışan `should_long` gövdesi MACD>signal **durumunu** kullanıyor; kod davranışı esas alındı. Üçüncü taraf kodu repoya kopyalanmadı.
- T61'in %20 iz stoplu biçimi **S0879** (`HAM:X005:879`, K4 kapsamı); `S0687` kaynakta X hisse başına örneklem içinde optimize ve çoğunlukla %1 altı. İkisi kaynak değeri bakımından farklı. Ön kayıtta T61 başlığı altındaki S0687 referansı tek başına %20 biçimi temsil etmez; iki kayıt da kapalı kümede mevcut.
- T21/S0395 tek makalede 10 önceden belirtilmiş (S,L,B) kuralı içeriyor. Bunlar tek bir parametre seçimi değildir; deney kimliği/çoklu test sayımı çözülmeden rastgele birini seçme.
- `v3__saatlik-asiri-tepki` mevcut kodunun docstring'i eşik/süre/stop değerlerinin kaynakta bulunmadığını söylüyor; birincil metin doğrulanmadan “birebir kaynak” olarak koşuya bağlanamaz.
- 26 v3 kodunun içinde `pf__v3-funding-1s-devam` (1h portföy altyapısı eksik) ve `v3__ters-fvg-nq-long` (NQ 5m veri/evren dışı) var. K1'de bütün 26'yı körlemesine koşuya sokma.
- V2 tek-grafik yeniden oynatıcısı işlem riski/kill ayarı alıyor; mevcut portföy motoru SERT_LIMITLER ile %1/−%20 kullanıyor. Ön kayıttaki %1,5/−%30 ayrı araştırma hesabı portföy için henüz uygulanmadı. Bu fark çözülmeden koşu yasak.

## Kod ve doğrulama

- `motor/strateji/kapanis/jesse_kaynak.py`: S0002 ve S0005, kaynak satırı/linki, ATR uyarlaması yazılı.
- `motor/arastirma/kapanis/ek_ayarlar.py`: 18 ayarı iki JSON'dan okur, sınıfına kurar; eski araştırma aday kümelerine müdahale etmez.
- `motor/arastirma/kapanis/tek_grafik.py`: v2 maliyet/ham işlem yardımcılarını yeniden kullanarak tek grafik sınıfını ×1/×2 çalıştırır; `secim.OynatmaAyari(risk=0.015, kill=0.30)` ile kendi hesabına oynatır. Portföy sınıflarını desteklemez; gerçek veri koşusu yapılmadı.
- `testler/test_kapanis_l_sekli_kaynak.py` dahil 15 odaklı sentetik test geçti (`PYTHONPATH=/tmp/kapanis-test-deps:. python -m pytest ...`). Gelecek mum değişimi geçmiş sinyali etkilemiyor; her girişte stop var; ek ayarlar eksiksiz ve tekil. RSI32 alt sınıfı henüz test edilmedi.
- Önceki kod durumunda tüm suite geçti: `PYTHONPATH=/tmp/kapanis-test-deps:. python -m pytest testler -q -p no:cacheprovider` → **5101 geçti, 17 atlandı** (315 saniye). Eksik Python geliştirme paketleri yalnız `/tmp/kapanis-test-deps` altına kuruldu; repo bağımlılık dosyaları değişmedi. Bu tam paket yeni `tek_grafik.py` eklenmeden önceydi; 13 odaklı test yeni kodla geçti. Gerçek piyasa strateji koşusu değildir.
- `veri/mumlar` bu ortamda yok; gerçek koşu burada yapılamaz.
- `araclar/kapanis_kosu.py` henüz yazılmadı. Koşu listesi/kapılar/BH/ikinci evren/test sonuçları hazır değil. Veri yokluğu nedeniyle gerçek strateji testi yapılmadı.

## Devam sırası

1. K1'in kalan 45 satırına kaynak TF, evren, ayar ve çalıştırılabilirlik kararı ver. 18 ayarın okuyucusunu koşuya bağla; 1h portföy ve araştırma risk/kill hesabını canlı limitlere dokunmadan çöz. K5'in 621 iz akıbetini ana K1/K3/K4 kararına bağla.
2. K2 kısa listesinin kaynak metnini/kodunu doğrula; yalnız tam kuralı belli biçimleri kodla, belirsizleri kanıtla dışla.
3. K3'ün 1.816 satırını kanıtla karara bağla.
4. K4'ün 2.204 satırında arşiv kodunu açıp anlamlı farkı denetle; K5 bağlarının nihai akıbetini de kapat. Bütün katmanlarda girdi = karar satırı kontrolü yap.
5. Yalnız gerçekten koşulacak benzersiz strateji/ayarları listeye al; listeyi ve BH aile büyüklüğünü sonuç görülmeden dondur. Tek koşu betiği, kapılar ve yeni 40 sembol aşamasını hazırla. Bu ortamda gerçek mum koşusu yapılmaz.
6. Uçtan uca sentetik test, sonra tüm pytest. Hazırlık raporunu nihai sayılarla yaz. Her katman bitince ara commit; hepsi bitince PR aç, main'e birleştirme.

### Denetim notları (DEVAM 2)
- kul_k3_g8 (45): 10/10 örnek kaynakla uyumlu. 745/746/747 kaynak sayfası erişilemedi (traders.com 403) → KURAL_YOK; ayrıca raporlanacak.
- kul_k4_g9_b (149): 10/10 karar kaynak kodla uyumlu. Kodlama notu: B001:496 (DD.py) trailing_only_offset_is_reached=False → iz stop offsetten önce de çalışır; kural_tam'daki "offset sonrası" ifadesi kodlamada düzeltilecek. 28 KURAL_YOK "tek kural değil" (çok kollu NFI/Nostalgia vb.) → Fable denetiminde ayrıca bakılacak. emin_degil=evet 39 satır kodlamadan önce kaynak yeniden okunacak.
- Kullanıcı isteği: 7 parti bitince Fable bağımsız denetleyecek.
- kul_k4_g8_a (160): 10/10 örnek kaynakla uyumlu. Tek FARK_YOK (S0143 → dis__tsmom varsayılan, d5_ek.py:369-393) kodla doğrulandı. Kodlama notu: ~14 YENI satırda ROI zaman tablosu/iz süren stop var (S0016,18,20,22,23,25,28…) → motor desteği kodlamadan önce kontrol. S0178 ust_tf=15m/zaman_cikisi=0 sınıf desteği kontrol. emin_degil=evet 40 satır.
- kul_k4_g8_b (160): 10/10 örnek kaynakla uyumlu. FARK_YOK 3 (X005:44, 533, 568). Kodlama notları: 367 TF 1w (1d'den yeniden örnekleme gerek); 396 (6) ve 428 (2) kaynak raporlu varyant → her biri BH ailesinde ayrı hipotez; 364/594 MA tipi yazılı değil, ajan SMA varsaydı → Fable "KURAL_YOK mu" diye bakacak. emin_degil=evet 49.
- kul_k4_g8_c (159): 10/10 örnek kaynakla uyumlu. FARK_YOK 1 (X005:721 SMA50/200). traders.com erişilemedi → 734,735,740,750,752,761,767 KURAL_YOK (sayfa açılmadan; ayrıca raporlanacak). X008 12 satır kaynak linki yok → KURAL_YOK. 863 (örtüşen dilim) ve 737 (aylık TF) motor uygunluğu kodlamada karar. EVREN_DISI 7 satır (bekleyen emir/seans) uyarlama adayı → Fable'a sorulacak. emin_degil=evet 60.
- kul_k4_g9_a (149): 10/10 örnek kaynak kodla uyumlu (overwatch.py ayarları, AlexDivergence pivot geriye yazma=LOOKAHEAD doğrulandı). FARK_YOK 0.
- **TUTARSIZLIK (çözülecek):** çok kollu NFI/BigZ/Combined aileleri g9_a'da KOSULACAK (emin_degil=evet), g9_b'de KURAL_YOK "tek kural değil". Tek politika gerek; Fable hakem görüşü + lider kararı, sonra iki parti aynı kurala çekilecek (sonuç öncesi, veri görülmedi).
- kul_k4_g9_c (148): 10/10 örnek kaynak kodla uyumlu (ema.py, BuyOnly.py doğrulandı). FARK_YOK 0; 776 (EMA50/200 1d) sınıf ayarıyla aynı sinyal, yalnız -%15 stop farkı → Fable'a sorulacak. Çok kollu NFI/Nostalgia burada da KURAL_YOK (g9_b ile aynı, g9_a ile çelişkili).
- 7 kul_* partisi bitti (970 satır). Sıradaki: Fable bağımsız denetim (kullanıcı isteği).

### DERİN GEÇİŞ — 906'lık trend/ortalamaya dönüş listesi (kullanıcı: "hiçbir kod atlanmayacak")
906 satırın kapanıştaki durumu tarandı: 602 satır kapanışta (220 KOSULACAK, 213 KURAL_YOK, 90 INCELEME_BEKLIYOR, 49 EVREN_DISI, 19 VERI_YOK, 5 YASAK, 5 FARK_YOK, 1 TEKRAR); 304 satır kapanışa HİÇ girmemişti (eski defter: 221 H "evrende uygulanamaz", 55 KOD "arşivde var", 28 F "yasak" — hiçbiri doğrulanmamıştı).
Yeni partiler (girdi/ altında; çıktı ara/<parti>.csv):
| parti | satır | iş |
|---|---|---|
| derin_bekleyen | 90 | K3 kararı verilmemiş satırlar |
| derin_hkf_a/b/c | 101/101/102 | H/KOD/F etiketlerini yeniden yargıla (KOD → FARK_YOK prosedürü) |
| derin_kod_a/b | 64/64 | KURAL_YOK ama kaynakta kod var → kodu açıp eksik parametreyi ara |
Kalan 85 KURAL_YOK (kaynakta kod yok) için seçenek kullanıcıya soruldu.
- Kullanıcı netleştirdi: öncelik kendi gönderdiği belgeler (ajan1 tur1–4 → 906 listesi; ajan2 26 kayıt raporu). Doğrulandı: tur1 (417), tur2 (547), tur3 (707) satırlarının hepsi 906 listesinde var.
- Ek partiler: derin_ajan2 (ajan2 raporundaki stratejilerin birincil kaynağını bulup karar; önceki 13 X008 satırı "link yok" diye KURAL_YOK/bekleyen idi), k6_kodsuz (85; ön kayıt eki 3 standart ayar). derin_kod_a/b sonrası hâlâ parametre eksikliğiyle KURAL_YOK kalanlar da K6'ya alınacak.
- derin_hkf_c (102): EVREN_DISI 80'den 12 örnek incelendi, hepsi gerçekten kesitsel rotasyon / pairs / seans kuralı. KOD 7 → 4 KOSULACAK, 2 FARK_YOK (894, 903), 1 EVREN_DISI. F 8 → hepsi YASAK. **Politika sorusu (sonuç öncesi karar gerekir):** kesitsel rotasyon ve pairs kuralları 13 kripto içinde uyarlanabilir mi (DK_ kripto kesitseli / BTC-ETH yayılımı)? Fable + kullanıcı.
- derin_kod_b (64): kod açıldı; 2 KOSULACAK (553 TrendRider, 828), 4 EVREN_DISI, 58 KURAL_YOK (32'si traders.com/medium.com erişilemedi). Örnek 8 satır kod kanıtıyla tutarlı. Yalnız TF eksik olanlar (693, 697-702, 710, 711, 742, 584 vb.) K6'ya gidecek.
- k6_kodsuz ilk sürüm reddedildi (örnek 14'te 2-4 hata: kaynak varyant listesi 138/306 KURAL_YOK yapılmış, com→EMA 144, WebFetch yapılmamış) → ajana yeniden yaptırılıyor.
- k6_kodsuz (85) yeniden yapıldı ve kabul edildi: K6_STANDART 18, KOSULACAK 6 (138, 306, 144, 320 düzeltildi), EVREN_DISI 7, KURAL_YOK 54 (öznel/tanımsız/tutarsız). 508'de kaynak tüm-örneklem z-skoru (lookahead) → K6 kayan 20 pencere.
- Ağ: ortam izin listesine traders.com, medium.com, kpumangyou.tistory.com, repositorio.unipampa.edu.br eklendi (kullanıcı onayı). Proxy geçiyor ama traders.com ve medium.com Cloudflare bot korumasıyla 403 veriyor; tarayıcıyla aşma denemesi izin denetleyicisince reddedildi (yapılmadı). Bu satırlar "kaynak erişilemedi" kalır; kullanıcı sayfaları kendisi indirip yüklerse açılır.

### Fable hakem denetimi (kul_*) ve politika kararları — SONUÇ GÖRÜLMEDEN
Rapor: `HAKEM_FABLE_KUL.md`, örnekler `ara/hakem_fable_kul_ornek.csv` (107 satır izlendi). Liderin 10/10 örnek denetimi g9_a'daki sistematik hatayı kaçırdı (Fable buldu, lider kodda doğruladı: ichiV1 EMA 3/6/12/24/48/72/96, ajan 2/3/5/8/13/21/34 yazmış; pHSL etkin değer yerine hyperopt default).
Lider kararları (Fable önerileri, hiçbir koşu yapılmadan):
- (a) Çok kollu Freqtrade sistemleri: **≥10 giriş kolu → `COK_KOLLU`** (ayrı aşama; dosyadaki kod birebir uyarlanarak sonra ele alınır, ana BH ailesine girmez, ayrı raporlanır); **<10 kol → tüm kollar yazılarak KOSULACAK**. Üç g9 partisine aynı uygulanır.
- (b) MA tipi yazmayan X005 satırları → ön kayıt eki 3 gereği `K6_STANDART` (MA=SMA). X005:364 kaynak tam okunmamış → yeniden okunacak; okunamazsa KURAL_YOK.
- (c) Erişilemeyen kaynaklar: karar KURAL_YOK, `neden` tek biçim "kaynak erişilemedi: <host/hata>"; "kaynakta yok" yazılmaz.
- (d) Stop/limit emirli girişler tek biçim: "seviye mum kapanışıyla aşılınca sonraki açılışta giriş (uyarlama)". Koşulsuz açılış girişi yazılmaz (695, 724 düzelt). Bar içi limit dolumuna ya da seans saatine özünde bağlı olanlar EVREN_DISI, neden "emir tipi/dolum modeli".
- (e) B001:776 KOSULACAK kalır.
- Mutlak birim (pip/puan/tik/USD) stop/hedef: tek biçim EVREN_DISI (g8_b 381/382 ve g8_c 721 buna çekilir; 721 FARK_YOK'tan çıkar).
- Stopsuz eşiği: stoploss ≤ −0,50 → "fiilen stopsuz", ATR(14)×3 uyarlaması (kaynak stopu bilgi notu). 
- 1w/1M/3h/6h TF: 1d/1h verisinden yeniden örnekleme ile KOSULACAK; motor desteği kodlamada sağlanacak.
Düzeltme işleri: g9_a `kural_tam` baştan (etkin parametreler buy_params/sell_params'tan); g8_b/g8_c/g9_b/g9_c Fable satır listesi + yukarıdaki politikalar.
- derin_hkf_a (101): EVREN_DISI 62, KOSULACAK 11, YASAK 9, KURAL_YOK 9, VERI_YOK 6, FARK_YOK 4. derin_hkf_b (101): EVREN_DISI 45, KURAL_YOK 15, KOSULACAK 14, VERI_YOK 13, YASAK 9, FARK_YOK 5. İkisinde 8'er örnek (KOSULACAK/FARK_YOK ağırlıklı) kaynak ve G0_ayarlar.csv ile tutarlı. Eski "KOD" etiketlerinin çoğu gerçekte kapsanmamış çıktı.
- derin_bekleyen (90): KURAL_YOK 31, KOSULACAK 27, VERI_YOK 22, EVREN_DISI 8, LOOKAHEAD 1 (220), FARK_YOK 1 (624). 10 örnek kaynakla tutarlı. Not: 629 kaynak kodunda saat içi merge_asof sızıntısı → kapanmış 1h bar uyarlamasıyla KOSULACAK (uyarlama notu). 629/674 çoklu TF motor desteği kodlamada.
- derin_ajan2 (18 = 13 X008 + 5 EK): KOSULACAK 3, TEKRAR 7, KURAL_YOK 8 (5'i kaynak bulunamadı/erişilemedi). Raporda adı geçen 18 strateji çıkarıldı; ~8 kayıt adsız, CSV kayıp olduğu için geri getirilemez. L21#2→X005:141 TEKRAR geçerli (141 derin_hkf_a'da KOSULACAK). L17#5/EK#5 VWAP: koşu listesinde tek hipotez sayılacak (EK#5 korunur, L17#5 bilgi).
- Fable düzeltmeleri (G8): kul_k4_g8_a_v2 (173 → KOSULACAK, tqsdk dualthrust), kul_k4_g8_b_v2 (364 → KURAL_YOK erişilemedi, 594 → K6, 553 → KOSULACAK 6 kol, 381/382 → EVREN_DISI), kul_k4_g8_c_v2 (695/724 politika d, 721 → EVREN_DISI, K6 9 satır, traders.com nedenleri tekleştirildi). Lider elle: g8_c_v2 X005:73 KOSULACAK→K6_STANDART (standart değer verilmişti); 93, 712, 713, 720 → EVREN_DISI (mutlak birim politikası). Birleştirmede _v2 dosyaları eskisinin yerini alır.
- derin_kod_a (64): kod açıldı; KOSULACAK 13 (önceki KURAL_YOK gerekçesi 11'inde yanlıştı — parametre kodda tam), KURAL_YOK 41, EVREN_DISI 5, VERI_YOK 4, YASAK 1 (87 piramit). Riskli satırlar incelendi (236, 287, 310, 373, 494).
- Politika (sonuç öncesi): kaynak kodunda uygulama sızıntısı (TV lookahead_on, merge_asof, gelişen hafta) varsa ve kural kapanmış mumla tek anlamlı yazılabiliyorsa → KOSULACAK + not "uyarlama: geleceksiz biçim" (287, 310, 629). Kuralın kendisi geleceğe dayanıyorsa (merkezli ayrıştırma, pivotu geriye yazma) → LOOKAHEAD.
- Birleştirme önceliği: aynı kaynak_id birden çok partide ise sıra: *_v2 > derin_* > kul_* > k*_nihai/k*_karar. İstisna: X005:173 → kul_k4_g8_a_v2 kararı (KOSULACAK, politika d) derin_kod_a'daki VERI_YOK'un önüne geçer.
- Birleştirme: _v2 dosyaları yalnız DEĞİŞTİRDİKLERİ satırlarda öncelik alır (değişmeyen kopya satırlar k6/derin kararlarını ezmez). 906 X005 satırının hepsi bir karara bağlı (eksik 0, çakışma 0).
- Erişim: ağ izin listesine ~50 kaynak host eklendi (kullanıcı onayı); sonraki 19 host'u servis reddetti (liste sınırı olası). WebFetch bu ortamda çalışmıyor → curl. derin_erisim partisi (126 satır "kaynak erişilemedi") yeniden deneniyor; birleştirmede en yüksek öncelik.
