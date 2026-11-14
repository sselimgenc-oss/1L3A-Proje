# Kapanış turu — alt ajan ortak talimatı

Lider (ana oturum) planlar ve denetler. Ajan yalnız verilen partiyi/kod işini yapar. Türkçe çalış.

## Önce oku
- `CLAUDE.md`, `sonuclar/kapanis/ON_KAYIT_KAPANIS.md` (asıl metin + en alttaki "Ön kayıt düzeltmesi — sonuç görülmeden" eki),
  `sonuclar/kapanis/ILERLEME.md` (Codex'in bulguları), görevde adı geçen karar tablosu.
- Satırın kaynak kuralı: `sonuclar/kapanis/aday_listesi.csv` (`strateji_id` = karar tablosundaki `kaynak_id`; `kaynak_kurali`,
  `eslesen_kod`, `kanit` sütunları). Eski hesap defteri izi: `sonuclar/hesap_defteri/ham_satirlar.csv` (tekil_id → ham_id, kaynak),
  `sonuclar/hesap_defteri/kaynaklar.csv` (kaynak_id → dosya yolu). Birleşmemiş dal dosyaları için lider kopyası:
  `/tmp/claude-0/-home-user-1L3A-Proje/bee1199a-0b5d-5964-8f7d-e654dea778f9/scratchpad/ref_adoring/sonuclar/dis_arastirma/`.
- Kodlu sınıflar: `sonuclar/hesap_defteri/ara/kod_kaydi.csv` (ad → dosya:sınıf:satır). Eski test sonuçları:
  `sonuclar/hesap_defteri/ara/G0_kod_akibet.csv` (her kodlu stratejinin v1/v2/v3 koşusu, TF, ayar), `G0_ayarlar.csv`.

## Ön kayıttan özet (değişmez)
Dönem ≤ 2025-11-07 (holdout okunmaz). Evren: `motor.arastirma.v2.sabit.evren_listesi('kripto')` 13 Binance USDT perp; DK_ yalnız
kaynağın vazgeçilmez şartıysa. Veri: yalnız 5m–1d OHLCV + funding. Risk %1,5, kill −%30, ana karar maliyet ×2. Kaynak parametre/TF/
yön/çıkış kaynaktaki biçimiyle; ızgara/optimizasyon yok. Kaynak stopu yoksa ATR(14)×3 felaket stopu = "uyarlama".
**Eksik parametreye keyfi değer verilmez → KURAL_YOK.** Sinyal kapanmış mumdan, dolum sonraki açılış.

## Karar seçenekleri ve gereken kanıt
- `KOSULACAK`: kural tam (giriş, çıkış ya da stop, TF, yön, parametre değerleri kaynakta yazılı). Kanıt: kaynak link/dosya:satır +
  kuralın parametreleri `kural_tam` sütununda tek satırda. Mevcut sınıf birebir uyguluyorsa `sinif` = o sınıf ve `ayar` = parametre
  JSON'u (sınıfın `varsayilan_parametreler` anahtarlarıyla); uygulamıyorsa `sinif` = `YENI` ve `kural_tam` kodlanacak tanım.
- `KURAL_YOK`: kaynakta giriş/çıkış/eşik/periyot eksik ya da öznel (ör. "güçlü trend", el ile çizgi, kapalı kod). Hangi parametre eksik yaz.
- `VERI_YOK`: 5m–1d OHLCV + funding dışı veri gerekir (orderbook, tick, 1m, opsiyon, on-chain, temel, haber, VIX, makro…). Hangisi yaz.
- `EVREN_DISI`: kural belli ama işlem yolu 13 kripto perp'te uygulanamaz (hisse kesitsel geniş evren, belirli hisse/ETF çifti, forex
  paritesi, seans/gap kuralı kriptoda anlamsız, emtia vadeli yuvarlama…). Neden yaz.
- `YASAK`: martingale, DCA, ortalama düşürme, stopsuz grid, piramit ekleme (risk artıran). `ML`: model/öğrenme/LLM karar verir.
  `LOOKAHEAD`: kaynak kuralı geleceği kullanır (shift(-), center=True, tüm-seri istatistiği, kapanmamış mum) ve geleceksiz biçimi yazılı değil.
- `TEKRAR`: aynı işlem kuralı (giriş+çıkış+filtre+TF+yön aynı) başka bir satırda/koşuda var → `bagli_kimlik` = o satırın kaynak_id'si
  ya da koşu/sınıf. **Anahtar kelime ya da ad eşleşmesi kanıt değildir**; iki kuralı yan yana yaz.
- (Yalnız K4) `FARK_YOK`: eşleşen arşiv sınıfının KODUNU açtın ve kaynak kural sınıfın varsayılan ayarı ya da test edilmiş ayarı
  (kart/dış ayar/ızgara içi) ile aynı; `kanit` = sınıf dosya:satır + hangi koşu (G0_kod_akibet.csv: v1 TF / v2 ayar) bunu kapsadı.
  `FARK_VAR`: kodda olmayan filtre/çıkış/TF/yön/ızgara dışı parametre var → kural tamsa `KOSULACAK` gibi doldur (sinif YENI ya da
  sınıf+ayar), değilse `KURAL_YOK`. K4'te çıktı kararı `FARK_YOK` / `KOSULACAK` / `KURAL_YOK` / `EVREN_DISI` / `VERI_YOK` /
  `YASAK` / `ML` / `LOOKAHEAD` / `TEKRAR` olur ve `fark` sütunu doldurulur.

## Kaynağa erişim
- Önce `aday_listesi.csv` kural metni ve eski envanter satırı. Kural metni eksikse birincil kaynağa bak: GitHub için
  `git clone --depth 1 <url> /tmp/kapanis-src-<ad>` (salt okunur; repoya KOPYALAMA), web sayfası için mevcut araçlar. Erişilemezse
  bunu yaz; tahminle doldurma (→ KURAL_YOK, neden "kaynak erişilemedi").
- Commit SHA'sını (`git -C <dir> rev-parse HEAD`) kanıta yaz.

## Kurallar
- Dokunma: `motor/canli/**`, `stratejiler/canli_ayar*.json`, `stratejiler/paper_v2_seti.json`, CANLI_LIMITLER, SERT_LIMITLER, mevcut
  sınıfların davranışı, `sonuclar/evren/v2/`, `sonuclar/kilit/`, `sonuclar/final/`, `ON_KAYIT*`, `aday_listesi.csv`, `k*_karar.csv`.
  Yalnız görevde verilen çıktı yoluna yaz.
- `sonuclar/` altında `grep -r` YAPMA (dev symlinkler); hedefli dosya oku, `find` için `-maxdepth`.
- git commit/push/checkout YAPMA (lider yapar). `git add -A` yok. Üçüncü taraf kodu kopyalama; kendi cümlen/kodun, lisansı not et.
- Yasak tipler kodlanmaz. Sessiz try/except yok. Gizli bilgi kopyalanmaz.
- Kod işlerinde: yalnız yeni dosya/sınıf (gerekirse miras); her yeni sınıfa sentetik test: (1) sinyal üretir, (2) gelecek mumlar
  değişince geçmiş sinyaller değişmez, (3) her girişte stop var. Testleri `python -m pytest <dosya> -q` ile çalıştır.

## Satır partisi çıktısı: `sonuclar/kapanis/ara/<parti>.csv`
Sütunlar (sırayla): `kaynak_id,karar,neden,kural_tam,sinif,ayar,tf,evren,yon,bagli_kimlik,fark,kanit,emin_degil,not`
- Girdi satır sayısı = çıktı satır sayısı (her kaynak_id bir kez). `INCELEME_BEKLIYOR` bırakma.
- `evren`: `kripto13` ya da açık sembol listesi. `yon`: long / short / iki. `emin_degil`: evet/boş.
- Bitince ≤12 satır rapor: sayı kontrolü, karar dağılımı, `emin_degil=evet` satır listesi, KOSULACAK+YENI satır sayısı.
