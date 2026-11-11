# Seçim yöntemi meta-testi — ÖN KAYIT ("seçim rastgele mi?")

Tarih: 2026-11-11. Fikir: kullanıcı ("zamanda geri gidip sına; o gün seçseydik kimi seçerdik; rastgele kârlılarla
karşılaştır"). Tasarım: lider + Fable (hüküm: "düzeltmeyle doğru"). Durum: kullanıcı onayı ve hesaplayıcı seçimi bekliyor.
Hesaplamadan ÖNCE yazıldı; koşudan önce betiğin sha256'sı bu dosyaya eklenip commit edilir. Tek koşu; çıktı görüldükten
sonra hiçbir parametre değişmez. Bu test strateji SEÇMEZ; seçim YÖNTEMİMİZİN rastgeleden iyi olup olmadığını ölçer.

## Neden bu tasarım (sade)
- Son ~12 ay (2025-11-08 →) v2 holdout'u: kullanıldı ve 8 paper stratejisi ona bakılarak seçildi → kirli, OKUNMAZ.
- 8–16 hafta swing için çok kısa → bunun yerine geliştirme döneminde 11 örtüşmeyen 6 aylık pencere.
- Stratejiler birbirine bağımlı → çıkarım birimi PENCERE (11 sayı), işaret çevirme testi.
- Güç düşük, yanlılık "seçim çalışıyor" yönünde (evren 2026'da seçildi; kapılar geliştirme verisi görüldükten sonra
  tasarlandı) → olumsuz bulgu güvenilir, olumlu bulgu indirimle okunur.

## SPEC

**Girdi (yalnız okuma, yalnız geliştirme dönemi; tarihi ≥ 2025-11-08 olan HİÇBİR şey okunmaz)**
- Havuz: `sonuclar/evren/v2/eleme.csv` içinde `durum != hata` ve dosyası olan satırlar (beklenen ~212).
- İşlem bazlı günlük MTM: `sonuclar/evren/v2/mtm/x2/<strateji>--<tf>--<sembol>.parquet` (`islem_no, gun, kum_r`);
  işlem listesi `v2/ham/x2/*.parquet` (`giris_zamani, cikis_zamani, r, fonlama_r`); PF için `x1`.
- Strateji günlük R serisi: işlem başına günlük artış = `kum_r` farkı (ilk gün = `kum_r`); işlem ve enstrüman
  üzerinden UTC gün toplamı; eksik gün = 0.
- Önce doğrulama: her işlemin son `kum_r` değeri ham'daki net `r`'ye eşit (tolerans 1e-4) ve `fonlama_r` dahil mi →
  tutmazsa DUR ve raporla.
- Kasa limiti / kill yok; ham 1R birim.

**Kesimler (örtüşmeyen, sabit)**
- T_k = 2020-05-08, 2020-11-08, 2021-05-08, …, 2025-05-08 (11 kesim, 00:00 UTC).
- Ölçüm penceresi k = [T_k, T_k + 6 takvim ayı); sonuncusu 2025-11-07 dahil biter.
- Geriye bakış k = [stratejinin analiz başlangıcı, T_k), genişleyen.
- Uygunluk: T_k öncesi ≥ 730 günlük seri.

**Seçim vekili (her T_k'de yalnız geriye bakış verisi)**
- G1: ΣR(×2) > 0 ve PF(×1, T_k öncesi kapanan işlemler) ≥ 1.2.
- G2: kapanan işlem ≥ 27 × geriye bakış yılı.
- G3: en iyi enstrüman çıkarılınca ΣR(×2) > 0 ve en iyi takvim yılı çıkarılınca ΣR(×2) > 0.
- Puan = geriye bakış günlük R(×2) serisinin t-istatistiği: ort / sd × √(gün sayısı).
- S_k = G1–G3'ü geçenlerden puana göre ilk 10; 10'dan az geçen varsa hepsi; 3'ten az ise N1'den puan sırasıyla 3'e tamamla.
  Kesim başına geçen sayısı kaydedilir.
- Sadakat kontrolü (yalnız rapor): T = 2025-11-08'de tam geliştirme verisiyle vekil; G1–G3 geçenlerin gerçek 18 `gecti`
  satırıyla örtüşmesi ve (varsa) Spearman(puan, −p_ust).

**Karşılaştırma grupları**
- N1 (ana): geriye bakış ΣR(×2) > 0 olan tüm uygun stratejiler (S_k dahil).
- N2: tüm uygun stratejiler (eşit ağırlık hepsi).
- N3: S_k'nin `etiket` dağılımına göre tabakalanmış N1.

**Ana ölçü (tek, önceden kayıtlı)**
- score_i,k = i'nin pencere k'daki ΣR(×2) ÷ (geriye bakış günlük sd_i × √(pencere gün sayısı)); işlem yoksa 0.
- P_i,k = k'daki tüm uygun stratejiler içinde score'un yüzdelik sırası (0–100, eşitlikte ortalama).
- D_k = ort P(S_k) − ort P(N1_k). İstatistik: D̄ = 11 D_k'nin ortalaması.

**Çıkarım**
- Ana: {D_k} üzerinde kesin işaret çevirme permütasyonu (2^11 = 2048), tek yönlü p_yukarı = P(D̄* ≥ D̄), p_aşağı simetrik;
  t dağılımından %90 GA (sd = 10).
- Strateji başına ya da pencere içi havuzlanmış p karara girmez.

**Karar kuralı (koşudan önce sabit)**
- "SEÇİM ÇALIŞIYOR": D̄ ≥ +5 yüzdelik puan VE p_yukarı ≤ 0.10.
- "SEÇİM ZARARLI": D̄ ≤ −5 VE p_aşağı ≤ 0.10.
- Aksi: "RASTGELEDEN AYIRT EDİLEMİYOR" → canlı planı için rastgele sayılır.

**Kararın canlı plana etkisi (önceden yazıldı)**
- Rastgele / belirsiz: kapılar yalnız bozukları eler; geçenler eşit risk, küçük boyut, mümkün olduğunca çok ve farklı
  etiketli; sıralamaya göre ağırlık ya da "en iyiyi büyüt" yok.
- Çalışıyor: sıralamaya sınırlı güven (ör. üst yarıya en çok 1,5× ağırlık); asıl teyit yine paper.
- Zararlı: sıralama terk edilir, eşit ağırlık.

**İkincil (yalnız rapor; kararı değiştiremez)**
- Aynı D̄, N2 ve N3'e karşı.
- Pencere başına Spearman sıra IC (geriye bakış puanı ↔ ölçüm puanı, tüm uygunlar), ortalama ve işaret çevirme p.
- İsabet: S_k ortalama ölçüm ΣR'si N1 medyanını geçen pencere sayısı / 11.
- S_k, N1, N2 ve kapıyı geçen/kalanlar için strateji başı ortalama ölçüm ΣR(×2).
- Pencere içi rastgeleleştirme p: N1'den aynı boyutta 10.000 rastgele çekiliş, tohum 20261111.
- Dayanıklılık: 12 aylık ufuk (5 pencere); 24 aylık kayan geriye bakış; +3 ay kaydırılmış kesimler (ayrı koşu, ek örnek
  sayılmaz); ilk 5 ve ilk 20; v1 havuzunda tekrar (`2017_gelistirme/oos/*.parquet`, `kabul == True`, `pnl`, kesimler
  2021-05-08'den).

**Süreç**
- Bu dosya + betiğin sha256'sı ilk koşudan önce commit edilir. Tek koşu.
- Betik okunan en büyük tarihin < 2025-11-08 olduğunu sert biçimde doğrular; sessiz try/except yok.

**Çıktılar** (`sonuclar/evren/meta_test/`)
- `kesimler.csv`: kesim başına n_uygun, n_kapı_geçen, S_k üyeleri, N1/N2/N3'e karşı D_k, IC_k, S/N1/N2 ortalama ΣR.
- `secilenler.csv`: strateji × kesim — puan, kapılar, P_i,k, ölçüm ΣR.
- `ozet.json`: D̄, p_yukarı, p_aşağı, GA, karar etiketi, ikinciller, sadakat kontrolü, girdi hash'leri, commit.
- `rapor.md`: kısa Türkçe özet; karar etiketi ve yanlılık uyarıları (2026'da sabitlenen evren, geliştirme verisinde
  sonradan tasarlanan kural, 11 pencereyle düşük güç).

## Betik sha256
(koşudan önce eklenecek)
