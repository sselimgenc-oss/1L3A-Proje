# Kapanış turu — kodlama ajanı talimatı

Lider planlar ve denetler. Sen yalnız sana verilen partiyi kodlarsın. Türkçe yaz (kod adları ASCII).

## Önce oku
- `CLAUDE.md`, `sonuclar/kapanis/ON_KAYIT_KAPANIS.md` (sondaki ekler dahil, özellikle ek 3: K6 standart ayar).
- `sonuclar/kapanis/ILERLEME.md` sonundaki politika kararları (stopsuz eşiği, stop-emir uyarlaması, geleceksiz biçim).
- Arayüz: `motor/strateji/temel.py` (sinyal sözleşmesi), `motor/strateji/cikislar.py` (`CikisAyarlari`: `azalan_roi` = Freqtrade ROI tablosu,
  `geri_cekilme_yuzde`/`geri_cekilme_min_kar_yuzde` = iz süren kâr, `stop_basamaklari`, `zaman_cikisi_mum`, `atr_iz_suren_k` …).
- Örnek: `motor/strateji/kapanis/k2_kaynak.py` ve testi `testler/test_kapanis_k2_kaynak.py`. Göstergeler: `motor/strateji/gostergeler*.py`,
  yardımcı `motor/strateji/daytrade/_ortak.py:cerceve`. Var olan göstergeyi yeniden yazma; yoksa kendi dosyanda yaz.

## Girdi
`sonuclar/kapanis/kod_girdi/<parti>.csv`: her satır bir kaynak kural (`kural_tam`, `ayar`, `tf`, `yon`, `not`).
`K6_STANDART` satırlarında `not` alanındaki standart değerler AYNEN kullanılır.

## Yapılacak
1. Yeni dosya: `motor/strateji/kapanis/kod_<parti>.py`. Her kaynak satır için bir sınıf (aynı yapıdaki satırlar tek sınıf + farklı
   `varsayilan_parametreler` alt sınıfları olabilir). Sınıf adı `ad = "kapanis__<kisa-ad>-<kimlik>"` (kimlik: X005:123 → s0123,
   X008:L17#3 → x8l17-3). `parametre_izgarasi = {}` (ızgara yok). Docstring: kaynak kimliği, kural özeti, uyarlamalar.
2. Kural `kural_tam`'daki gibi; kendi kodun. Üçüncü taraf kodu KOPYALAMA. Sinyal kapanmış mumdan; gelecek verisi yok
   (shift(-), center=True, tüm-seri istatistiği YOK). Çoklu TF gerekiyorsa üst TF yalnız KAPANMIŞ mumdan (`motor/strateji/htf.py` varsa onu kullan).
3. Her girişte stop zorunlu: kaynak stopu; yoksa ya da ≤ −%50 ise ATR(14)×3 uyarlaması.
4. Varyant listesi (`ayar` JSON listesi ya da `tf` "4h|1d"): sınıf tek; her varyant bir parametre seti. Partinin sonunda
   `VARYANTLAR = [{"kimlik": "<kaynak_id>#v1", "sinif": "<ad>", "parametreler": {...}, "tf": "4h"}, ...]` listesi yaz — her satır ve
   her varyant/TF bir kayıt (tek varyantlı satır da bir kayıt). Bu liste koşu listesinin kaynağıdır.
5. Kodlanamayan satır olursa sınıf yazma; `VARYANTLAR` yerine `KODLANAMADI = [{"kimlik":..., "neden":...}]` listesine yaz (ör. motorun
   ifade edemediği emir tipi). Uydurma çözüm yok.
6. Kayıt: `motor/strateji/kayit.py`'ye DOKUNMA (lider ekler). Mevcut dosyaları değiştirme.
7. Test: `testler/test_kapanis_kod_<parti>.py`. Her sınıf için sentetik veriyle: (a) en az bir sinyal üretir (gerekirse kurala uygun
   sentetik seri kur), (b) son N mum değişince önceki sinyaller değişmez (lookahead testi), (c) her `yon != 0` satırında `stop` dolu ve
   doğru tarafta. `VARYANTLAR` her kaydının sınıfı örneklenebilir. `python -m pytest testler/test_kapanis_kod_<parti>.py -q` geçmeli.
8. git commit/push YAPMA. `git add -A` yok. Gerçek veriyle (veri/mumlar) koşu YAPMA — sonuç görülmeden kalınacak.

## Rapor (≤12 satır)
Sınıf sayısı, VARYANTLAR kayıt sayısı, KODLANAMADI listesi, test sonucu, yaptığın uyarlamalar (satır kimliğiyle).
