# İlerleme / Durum (güncel: 2026-10-11)

## Hedef
Kitaplara (metinler/*.md) dayalı day trade sistemi: 4s/1s yön + 15dk giriş, kazanma ≥ %45 ve kârlılık.
Kullanıcı kararıyla kapsam yalnızca kripto (ilk 25 coin).

## Şu anki durum
- **Kağıt al-sat botu çalışıyor** (kullanıcı onaylı): S10 + S13 + S15, yalnız alış, BTC 4s filtresi,
  ayrı alt hesaplar, 10.000 $, 2026-10-11 → 2026-12-10. GitHub Actions `kagit.yml` günde 2 kez;
  durum `kagit-durum` dalında; günlük rapor issue #2. Parametreler `kagit/ayarlar.json` (sürüm 0).
- **Ekip lideri:** swing-sg oturumu (session_011BRVoXb6shVtKMUVB7Sb5H). Kullanıcı talimatı (2026-10-11):
  karar/onay gerektiren konular ekip liderine sorulur, kullanıcıya doğrudan soru sorulmaz.
- **Rutin:** haftalık değerlendirme, pazartesi 08:44 İstanbul (trig_01C6uRueNnaJBkgw1jcKuK3M).

## Sonuçlar
| Test | Dönem | İşlem | Kazanma | PF | Not |
|---|---|---|---|---|---|
| Ana backtest | 2023-10 → 2026-10 | 1752 | %49,0 | 1,60 | docs/kripto_sonuc2.md (spot) |
| Stres: bugünkü evren | 2021-01 → 2023-09 | 1337 | %45,4 | 1,14 | 2022: PF 0,53 — docs/kripto_stres.md |
| Stres: + çöken coinler | 2021-01 → 2023-09 | 1811 | %44,4 | 1,15 | 2022: PF 0,66 |

## Veri
- `market-data` (son ~1 yıl, tüm sınıflar), `market-data-uzun` (kripto 2023-10 → 2026-10),
  `market-data-2021` (kripto + çöken coinler 2020-11 → 2023-10). Çekme: `.github/workflows/fetch-data.yml`,
  argümanlar `data/GUNCELLE` 2. satır, hedef dal 3. satır; GitHub runner'ında çalışır
  (bu bulut ortamının ağ politikası piyasa veri sitelerini engelliyor).
- Yerel kullanım: `git clone --depth 1 -b <dal> https://github.com/sselimgenc-oss/day-trade-sg /tmp/x`
  ve `DAYTRADE_CACHE=/tmp/x/cache`.

## Açık konular (karar ekip liderinde)
- 2022 ayı piyasasında zarar (PF < 1): rejim filtresi eklenmeli mi? Kağıt test değiştirilmeden sürüyor.
- Kural (2026-10-12, kullanıcı kararı ekip lideri üzerinden): Aralık'a kadar yeni optimizasyon/deney yok;
  yalnız bot izleme ve gerçek hata düzeltmesi (PR ile).
- Aralık değerlendirmesi için not (algo ekibi çapraz denetimi, doğrulanmadı): kağıt bot sinyali geç tanıyıp
  geçmiş mum fiyatından dolduruyor (`_session_ok` / son mum). Gerçekçi gecikmeli dolumla PF 1,60 → 1,46.
  Kağıt sonuçları bu farkla okunmalı.

## Geçmiş
- 1. tur (tüm sınıflar, S1–S8): hedef tutmadı — docs/test_sonuclari.md
- Kripto 1. tur (S10) — docs/kripto_sonuc.md; 2. tur (S13, S15, ayrı hesap, BTC filtresi) — docs/kripto_sonuc2.md
