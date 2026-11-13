# Hesap defteri — alt ajan ortak talimatı

Bu dosya tüm alt ajanlar için ortaktır. Lider (ana oturum) planlar ve denetler; ajan yalnız kendi grubunu yapar.

## Mutlak kurallar
1. **Hiçbir şeyi uydurma.** Her durumun kanıtı bir dosya yolu (+ satır/strateji id). Kanıt yoksa `BELIRSIZ` + neden.
2. **Test KOŞMA, strateji kodu yazma/değiştirme.** Mevcut hiçbir dosyayı değiştirme. Yalnız şuraya yaz:
   `sonuclar/hesap_defteri/ara/<GRUP>_*.csv|md` ve `sonuclar/hesap_defteri/betikler/<grup>_*.py`.
   `ILERLEME.md`, `kaynaklar.csv` ve başka grupların dosyalarına DOKUNMA (lider günceller).
3. `sonuclar/` altında dev symlinkler olabilir: **`grep -r sonuclar` YAPMA**, hedefli dosya oku; `find` kullanırsan `-maxdepth` ver.
4. Mühürlü klasörler yalnız okunur: `sonuclar/evren/v2/`, `sonuclar/kilit/`, `sonuclar/final/`, `ON_KAYIT*` dosyaları.
5. Gizli anahtar/şifre/kişisel bilgi görürsen kopyalama. Kitap/PDF metnini kopyalama: `kisa_mantik` kendi cümlen, ≤160 karakter.
6. git komutu çalıştırma (commit/push/checkout yok). Lider commit eder.
7. Kestirme yok: "benzer / zaten var / kopya" kararını isimden verme; hedef sınıfın kodunu (`motor/strateji/...`,
   `motor/portfoy/stratejiler/...`) açıp kuralı karşılaştır. Aynı hedefe giden çok satırı grupla, sınıfı bir kez oku.
8. Kaynak dosyadaki her strateji satırı bir ham satır olur. **Hiçbirini atlama.** Sayı tutmuyorsa nedenini NOTLAR'a yaz.
9. Türkçe yaz. CSV: UTF-8, virgül ayraçlı, `csv` modülüyle (tırnaklama otomatik).

## Yardımcı dosyalar (lider hazırladı)
- Kodlu strateji kaydı (`ad` = strateji id): `sonuclar/hesap_defteri/ara/kod_kaydi.csv`
  (521 satır: 492 tek-grafik + 29 portföy `pf__*`; sütunlar ad, tur, stil, dosya, sinif, satir).
- Kaynak envanteri ve kaynak_id'ler: `sonuclar/hesap_defteri/kaynaklar.csv`. ham_id üretirken bu id'leri kullan.
  Envanterde olmayan bir kaynak bulursan NOTLAR'a yaz; geçici id olarak `<GRUP_ONEKI>Y01, Y02…` kullan.
- Birleşmemiş `claude/adoring-maxwell-q7t60g` dalının `sonuclar/dis_arastirma` içeriği şurada açık:
  `/tmp/claude-0/-home-user-1L3A-Proje/bee1199a-0b5d-5964-8f7d-e654dea778f9/scratchpad/ref_adoring/sonuclar/dis_arastirma/`.
  Kanıt yolunda bu dosyaları `dal:claude/adoring-maxwell-q7t60g:sonuclar/dis_arastirma/...` diye yaz.
- Araştırma hattının aday ayar kümesi: `motor/arastirma/tarama.py::_ayar_listesi` = varsayılan + `stratejiler/kart_ayarlari/<ad>.json`
  + `stratejiler/dis_ayarlari/<ad>.json` + sınıfın `parametre_izgarasi`. `ayarlar_d11j_ek.json` / `ayarlar_d12b_ek.json` bu kümeye
  GİRMİYOR görünüyor (yalnız testlerde okunuyor) — kendi grubunda bunlara bağlı satır varsa doğrula ve yaz.

## Ham satır çıktısı: `sonuclar/hesap_defteri/ara/<GRUP>_ham.csv`
Sütunlar (bu sırayla):
| sütun | anlam |
|---|---|
| ham_id | `<kaynak_id>:<satir_no>` (ör. `H003:17`) |
| kaynak_id | kaynaklar.csv'deki id |
| kaynak_satir_no | CSV: başlık hariç 1'den başlayan veri satırı; JSON liste: indeks+1; MD: tablo/madde sıra no ya da `L<satır>`; XLSX: `sayfa!satır` |
| kaynaktaki_ad | kaynaktaki ad (≤120 karakter) |
| kisa_mantik | giriş/çıkış özü, kendi cümlen (≤160) |
| aile | `trend` / `MR` / `diger` |
| eslesme | `KOD` / `AYAR` / `ESDEGER` / `BENZER` / `TEKRAR` / `YOK` (aşağıda) |
| hedef | KOD/AYAR/ESDEGER/BENZER: strateji id (`ad`); TEKRAR: diğer ham_id |
| ayar_id | AYAR ise ayar kimliği (kart_id / dis_id / ayar_id) |
| ayar_dosyasi | AYAR ise ayarın yazılı olduğu dosya |
| fark | BENZER/ESDEGER: kodla kaynak arasındaki fark (ESDEGER'de `yok`); kodu açtığını gösterecek somut ifade |
| on_durum | KOD/AYAR/ESDEGER → `KOD`; TEKRAR → `TEKRAR`; diğerleri: `D_KODLANMADI_NEDENLI` / `E_KODLANMADI_NEDENSIZ` / `F_YASAK_TIP` / `G_ML` / `H_BIZIM_EVRENDE_UYGULANAMAZ` / `BELIRSIZ` |
| neden_kodu | ör. `veri_yok`, `kural_belirsiz`, `kopya`, `benzer_var`, `kapsam_disi`, `arac_sablon`, `lookahead`, `kod_yok`, `oncelik_disi`, `martingale`, `dca`, `stopsuz_grid`, `ortalama_dusurme`, `ml`, `hisse_kesitsel`, `pairs`, `seans_gap`, `opsiyon`, `vix`, `orderbook`, `hft`, `defi`, `arbitraj` … |
| neden_metni | kısa, kendi cümlen |
| kanit | kararın/eşlemenin yazdığı dosya: `yol:satır` ya da `yol#id`; birden çoksa ` ; ` ile |
| not | serbest |

**eslesme tanımları**
- `KOD`: bir kodlama/eşleme dosyası bu satırın doğrudan bu sınıf olarak kodlandığını söylüyor VE sınıf kayıtta var.
- `AYAR`: satır mevcut bir sınıfın ayarı/modu olarak eklenmiş (kart_ayarlari / dis_ayarlari / ayarlar_d11j_ek / ayarlar_d12b_ek); ayar
  gerçekten o dosyada var mı kontrol et (yoksa `BELIRSIZ` ya da `E`).
- `ESDEGER`: bu satırdan kod yazılmamış ama sen hedef sınıfı açıp mantığın aynı olduğunu doğruladın (parametre farkı ızgara içindeyse aynı say).
- `BENZER`: bir dosya "benzer/kopya/tekrar/zaten var" diyor ama mantıkta fark var (filtre, çıkış, TF, yön, evren…) ya da doğrulayamadın.
  `on_durum` = `D_KODLANMADI_NEDENLI`, `neden_kodu` = `benzer_var`, `fark` dolu. Bu satırlar liderin "fark test edilmedi" listesine girer.
- `TEKRAR`: aynı stratejinin başka bir ham satırı (aynı URL/dosya + aynı mantık). Hedef = o ham_id. Emin değilsen TEKRAR deme.
- `YOK`: hiçbir eşleşme yok.

**on_durum kuralları**
- `E_KODLANMADI_NEDENSIZ`: hiçbir dosyada bu stratejinin akıbeti yazmıyor (en önemli grup — dikkatle ara).
- `F_YASAK_TIP`: martingale, DCA, ortalama düşürme, stopsuz grid. `G_ML`: makine öğrenmesi/LLM/model tahmini.
- `H_BIZIM_EVRENDE_UYGULANAMAZ`: hisse kesitsel (geniş hisse evreni), pairs/eşbütünleşme, seans/gap (7/24 kriptoda), opsiyon, VIX,
  orderbook/HFT, DeFi/LP, borsalar arası arbitraj… nedeni yaz.
- `D_KODLANMADI_NEDENLI`: kodlanmadı ve nedeni bir dosyada yazıyor (veri yok, kural belirsiz, araç/şablon, kapsam dışı, kopya…).
- Kaynağın kendi karar sütunu (durum/karar/neden) varsa onu esas al ama doğrula: karar `kod_yok` ya da `yeni` deyip hiçbir yerde
  kodlanmadıysa ve sonraki bir dosyada akıbeti yoksa → `E`.

## Notlar dosyası: `sonuclar/hesap_defteri/ara/<GRUP>_NOTLAR.md`
- Her kaynak için: kaynak satır sayısı ↔ üretilen ham satır sayısı (tutmuyorsa neden).
- on_durum ve eslesme dağılımı (betikle say).
- Bulduğun tutarsızlıklar (ör. "dosya X kodlandı diyor ama sınıf yok", "ayar dosyada yok").
- Envanter dışı bulduğun kaynaklar.
- Kendi öz kontrolün: rastgele 10 satırı kaynağa geri izledin mi, sonuç.

## Bitirince
Lidere ≤15 satırlık rapor ver: dosya yolları, satır sayıları, durum dağılımı, en önemli 3–5 bulgu, emin olmadıkların.
