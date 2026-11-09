# tv-eleme durumu (3. tur + denetim, 13 Eki 2026)

Görev: `tv/GOREV3.md` (A–E). Önceki tur: 164 link → 41 aday → 36 çevrildi → 3 geçti (hybrid_brk, sqzmom, macd_reloaded).

## Bu oturumda bitenler
- [x] Dal güncellendi (origin/tv-eleme çekildi), veri indirmesi başladı (`python3 -m tv.veri`, kripto 1g/1s önbellek, git dışı).
- [x] 3. tur: 92 link çekildi (`tv/ham/meta3.json`, Pine `tv/pine/`), 87 açık / 5 kapalı.
- [x] Altyapı: `tv/analiz_yaz.py` (her betik için `tv/analiz/<id>.md`), motorda bacak desteği (`olcek`, `bacaklar`), 5dk kripto + VIX/SPX verisi.
- [x] 3. tur DCA/grid ailesi (46 betik) kodla doğrulandı, `tv/analiz/` yazıldı → kesin eleme.

## Sürüyor / kalan
- [ ] 3. tur kalan ~45 betik: analiz dosyası + çeviri (aday listesi aşağıda).
- [ ] C: 1-2. tur 123 elenen + 5 çevrilemeyen yeniden inceleme (B çıtası; "temsilci seçilmedi" gerekçesi geçersiz sayılıyor).
- [ ] B3: yazar iddiası ↔ bizim sonuç (`tv/sonuclar/dogrulama.csv`), 3 geçenin çeviri doğrulaması.
- [ ] B4: kalanlar için kural bazında değer/eşik farkı tablosu (RAPOR).
- [ ] D: yeni geçenler `gecenler.json` + `kagit.py` (strateji başına 3.333,33 $, strateji bazında başlangıç).
- [ ] RAPOR, PR.

## 3. tur karar özeti (kodu okunarak)
- Kesin eleme: DCA 30 + grid 16 (46), kapalı 5, 5 dk/1 dk gün içi veri yok (kAYwdfND, KOfsPM9h, 7SSRGEbI, 6HYQYnFl, AeYVHi9k, 6ve1ax1D), şablon (8z6wbyw5), alt-TF delta (OvE4qQgh).
- Çevrilecek adaylar: nuqVC5F7 d117dN6D 9qFCuXqF 8I2576zL 2wyXTTMc T5kd1bJ2 i3Uc79fF 6XPbhz9C 97gxVA5b XRZCjbFr bA9UFcgj 95JBkzXV mfw4fJST 7UNWrm2O mqh6UJ9p Pv1GvUVs NJb4BQ5n PETNavGq 3fea8k4Z BtDUET5k jd1KSVn7 uycyVpIq TJuVmOfk XGqSzuxJ FJZvYKaB pMOjQJwT IqUET4xO 6zYF9Xts T3t4yoJx teYPT1m0 HyzpDR9t Tkrjao7P ErcSuPyN GoUoySJs.

## Ara durum (oturum içi)
- 3. tur çeviriler yazıldı ve koşuldu (ilk koşu): geçenler compress_brk, ibs_rev, rsi_gauss, atr_rider (B3 doğrulaması ve yeniden koşu bekliyor).
- gost.highest/lowest NaN yayılımı hatası düzeltildi (NaN içeren pencerede -inf dönüyordu) → TÜM stratejiler son halde yeniden koşulacak.
- C denetimi (123 elenen): okunup çevrilenler: sq_reversal gap_fill lube penny_st narrow_state bb_rsi_lo bb_rsi_b sweep_sky.
- C kuyruğu (sırada): Qg1Jra51 Ip667jzb nRklAGPI rLkjr2sQ + "temsilci seçilmedi" listesinin kalanı + lookahead/pivot/SMC iddialarının satır kanıtı.
