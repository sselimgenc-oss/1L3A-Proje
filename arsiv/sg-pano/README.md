# SG Pano · Copy trade

`sg-arge` copy trade izleme panosu. **Salt okunur; gerçek emir, para hareketi ve aracı kurum bağlantısı yok.**

## Lisans ve atıf
Bu depo [GPL-3.0](LICENSE) ile lisanslıdır. Pano/ofis tasarımı, K-11 kararıyla (`sg-arge/docs/KARARLAR_D.md`) kısmen
Etre v2 · Trading Office (ismailkaraabc) projesinden esinlenmiştir: <https://github.com/ismailkaraabc/etre-trading-office>
(GPL-3.0). Birebir alınan/çevrilen dosyalarda kaynak yolu belirtilir. Gerçek emir, cüzdan ve para çekme işlevleri alınmamıştır.

- Yayın: GitHub Pages (`main` / kök). Tek sayfa (`index.html`), erişim yöntemi değişmedi (ek hesap/şifre yok).
- Sekmeler (sürüm `pano-sade`): **Özet** (`#ozet`: hafta x/12, oda doluluğu, kol başına trader, veri tazeliği, son 5 olay; altında kapalı bölümler: tüm akış, açık işlemler, "Kararlarım değer kattı mı?") · **Trader'lar** (`#traderlar`: kol filtresi + kartlar; trader sayfası `#trader/<adres>`) · **Huni** (`#huni`: havuz → aday → oda, son tarama, aday listesi) · **Ayarlar** (`#ayarlar`: tutar hesaplayıcı, sözlük). Sayfa Özet ile açılır. Eski adresler yönlenir: `#ct/<id>`, `#kesif/<adres>` → trader sayfası; `#ctakis`, `#ctistat` → Özet; `#kesif` → Huni.
- Telefon öncelikli, kısa Türkçe; her teknik terimin yanında "?" (dokununca açıklama; tam liste Ayarlar → Sözlük). "Araştırma / sanal, yatırım tavsiyesi değil" ibaresi sabit üst bantta her sekmede görünür.
- **Canlı pilot görünümü (ön kayıt 1.5):** sanal kasa, kol toplamları ve yönetilen oda ↔ sabit kontrol kıyası görünür. Seçim etiketi ile canlı izleme eşleşmiyorsa sayfa sahte veri üretmez; ilgili alan "veri yok" kalır.
- **Veride isteğe bağlı yeni alanlar** (yoksa "bilinmiyor" yazar, çökmez): trader başına `kol` (`oda|aday|kontrol|taban|elle`), `neden_secildi`, `kirmizi_bayraklar[]` (yoksa `saglik` ışığı/nedenleri); üst düzey `golge: {hafta, hafta_toplam (varsayılan 12), oda_kapasite, oda_n}`; keşifte `havuz`, `aday_sayisi` (yoksa `islenen` ve aday sayısı).
- Testler: `node test/pano.test.js` (ana pano, Playwright; ağ yakalanır, yalnız örnek veri).
- Görev: `sg-arge/docs/GOREV_ETRE_GECIS.md` (E5); veri biçimi: `sg-arge/docs/VERI_SOZLESMESI.md` (v1.1, `surum` 1; başka sürüm reddedilir).
- Sayfa açıkken her 5 dakikada veriyi yeniden okur; üstteki **Yenile** düğmesi hemen okur.
- Sahte veri yok: veri okunamazsa sayfa hata gösterir; olmayan alanlar "veri yok" der.
- Paper/strateji araştırması kapandı; ona ait pano, sekmeler ve `data.json` kaldırıldı.

## Ofis (animasyonlu görünüm)
`ofis/` altında ayrı bir sayfa: izometrik piksel sanatı ofis + sol pano. **Varsayılan kaynak gerçek veridir** (`sg-arge` veri dalları `copytrade-kapi` ve `copytrade-izleme`); seçim etiketi eşleşince üst şerit "Seçim v1.3 — pilot, hafta x/12" olur. Örnek veri (`ofis/ornek_durum.json`) yalnız `?durum=ornek` ile açılır. Veri okunamazsa sahte veriye düşülmez, hata yazılır.
- **Uyarlayıcı:** `ofis/gercek.js` seçim + kapı durumuna ek olarak `copytrade-izleme/izleme/durum.json` dosyasını `ofis/SEMA.md` şemasına çevirir (§9). Seçim etiketi eşleşince Lab, Finans, Risk, Oda ve Kontrol canlı olur; olaylar ve sanal kasa salt okunur veriden gelir. Veri yoksa sahte figür ya da olay üretilmez.
- **En son tarih:** veri dalı ağacı tek bir kimliksiz GitHub API çağrısıyla (`git/trees/copytrade-kapi?recursive=1`) okunur (60/saat sınırı için tek çağrı). Önce veri dalı kökündeki `son.json` (`{"secim": "<klasör>", "kapi": "<tarih>"}`; yayıncı: sg-arge `.github/scripts/son_yaz.py`) okunur; varsa API hiç çağrılmaz, yoksa tek ağaç çağrısına düşülür. Testler: `node ofis/test/gercek.test.js`, `node ofis/test/gercek_ui.test.js`.
- **Sürüm 2 (ilk 5 iş):** odaya tıklayınca iç görünüm (`#oda/lab`, Kapı, Arşiv…), ortak bilgi kutusu (masaüstü panel / telefon çekmece), `replikler.json`, iletişim işaretleri (zarf/not/ok), oda ve çalışan adlarını değiştirme (`kadro.json`). Testler: `node ofis/test/replik.test.js`, `node ofis/test/ui.test.js` (Playwright).
- **Sürüm 2b:** olay çekmecesi (filtre, kameraya git), veriden türeyen bayatlık (`esik_dk`, sis, "VERİ ESKİ"), oda iç ayrıntıları, günlük özet, isteğe bağlı ses (varsayılan kapalı).
- Düzen: ortasında avlu ve havuzlu bahçe olan iki kanatlı bina; sol dikey menü (Bina / Hat / Destek), durum plakaları (Adım 0 özgünleştirmesi, `ofis/LISANSLAR.md`).
- **Ofis paneli (`claude/ofis-panel`):** masaüstünde kart sütunu varsayılan **gizli**; ofis tuvali tüm genişliği kullanır. Sol menüde bir öğeye tıklayınca kamera o odaya gider ve ilgili kart(lar) ofisin üstünde açılır panel olarak gelir (eşleme tek tablo: `main.js` → `PANEL_ESLE`; tabloda olmayan odalar oda bilgisi kartını açar). Kapatma: ×, Esc, boş alana tıklama, aynı menüye ikinci tıklama, "Tüm ofis". Panel kapanınca kamera, panel açılmadan önceki görünüme (genelde bina) yumuşakça döner ve `#oda/…` adresi temizlenir; panel açıkken başka menüye geçilirse kamera doğrudan yeni odaya gider, elle yakınlaştırma/sürükleme kapanışta yok sayılır, geri tuşu da aynı sonucu verir, `prefers-reduced-motion` açıkken geçiş anidir. Günlük özet ofisin üst kenarında tek satırlık şerit (tıklayınca ayrıntı paneli). ◧ düğmesi klasik kart sütununu geri getirir. Telefon düzeni değişmedi (kartlar sayfada, alttan çekmece).
- Sayfa: `ofis/` (GitHub Pages'te `…/ofis/`). Belgeler: `ofis/SEMA.md` (veri), `ofis/OLAYLAR.md` (olay → animasyon), `ofis/LISANSLAR.md`.
- Deneme parametreleri: `?saat=23:14` (gün ışığı), `?hiz=2`, `?etiket=0`, `?hareket=0`, `?perf=1` (ayrıntı `ofis/SEMA.md` §6).
- Salt okunur; gerçek emir, para ve aracı kurum bağlantısı yok.

## Veri kaynağı
`index.html` içindeki iki sabit, canlı veriyi gösterir (sg-arge `copytrade-izleme` dalı, ham GitHub adresi):
- `CT_KAYNAK` = `…/copytrade-izleme/izleme/durum.json` (saatte bir güncellenir).
- `CT_KARAR` = `…/copytrade-izleme/izleme/kararlar.jsonl`. Dosya yoksa (404) "henüz karar kaydı yok" sayılır; tarayıcı bu 404'ü konsola yine de yazar, sayfa hata göstermez.

Eski veri uyarısı 90 dakikadan sonra çıkar (`CT_ESKI_DK`). "ÖRNEK VERİ" etiketi yalnız `kaynak` alanı `ornek` ile başlıyorsa görünür.
`izleme/ornek_durum.json`: sg-arge `main`'deki sabit örneğin kopyası (sahte veri); test için `CT_KAYNAK` geçici olarak `./izleme/ornek_durum.json` yapılabilir.

Keşif kaynağı `index.html` içindeki `KESIF_KAYNAK` sabitidir: veri dalındaki sabit yol `https://raw.githubusercontent.com/sselimgenc-oss/sg-arge/copytrade-kapi/kesif/kesif.json` (yayıncı `kapi_yayimla.sh` oraya yazar; tarih klasörü listelemesi ve GitHub API çağrısı yok). Canlı kaynak okunamazsa her sekmenin üstünde tam genişlikte "ÖRNEK (sahte) veri" uyarısıyla yerel örneğe düşer. Keşif'teki “Adresi kopyala” düğmesi yalnız cüzdan adresini panoya yazar; emir göndermez.

## Dosyalar
| Dosya | Görev |
|---|---|
| `index.html` | Pano (tek sayfa). |
| `test/` | Ana pano testi (`pano.test.js`) ve ortak yardımcı (`pano_yardim.js`). |
| `izleme/` | Test için sabit örnek durum (sahte veri); canlıda kullanılmaz. |
| `kesif/` | Keşif sekmesi için v1 şemasına uygun sahte aday verisi. |
| `vendor/` | Sabit sürümlü kütüphaneler: Lucide 0.460.0 (ikonlar, ISC), Tailwind 3.4.17 ile derlenmiş CSS (MIT). Dış CDN kullanılmaz. |

## Tailwind CSS'i yeniden derleme (index.html'de yeni sınıf kullanılırsa)
```bash
npm i tailwindcss@3.4.17
printf '@tailwind base;\n@tailwind components;\n@tailwind utilities;\n' > in.css
echo "module.exports = { darkMode: 'class', content: ['index.html'], theme: { extend: {} } };" > tailwind.config.js
npx tailwindcss -c tailwind.config.js -i in.css -o vendor/tailwind.3.4.17.css --minify
```

## Önbellek (Pages) ve sürüm sorgusu
`ofis/index.html` yerel CSS/JS dosyalarını `?v=<sürüm>` ile çağırır (Pages önbelleği yeni sürümü geç gösteriyordu). Kök `index.html` yalnız adında sürüm olan `vendor/` dosyalarını çağırır ve kodu sayfanın içindedir; damgalanacak yerel dosyası yoktur. **Ofis dosyalarını değiştiren her PR'da** (birleşmeden önce):
```bash
node tools/surum.js        # git kısa sha'sı; ya da: node tools/surum.js 20261028a
node test/surum.test.js
```
- **Telefon (ofis):** dolu masalı odalarda küçük rozet ("Oda 20"), açılışta kamera sığdırmadan %12 yakın, gecede figürlere açık kontur.
