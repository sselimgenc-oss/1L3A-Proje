# Strateji hesap defteri — ilerleme

Başlangıç: 2026-11-13. Dal: `codex/hesap-defteri`. Güncel inceleme tabanı: `a07d18d` (PR #56).
Yalnız kaynak okuma ve bu klasöre yazma yapılıyor. Test/strateji koşulmadı; kaynak strateji kodu değiştirilmedi.
**İş tamamlanmadı. RAPOR.md ve nihai tekil tablo henüz üretilmedi.** Ara tablolardaki geçici akıbetler nihai hüküm değildir.

| Parça | Kapsam | Durum | Sayı kontrolü / denetim |
|---|---|---|---|
| P1 | Kaynak dosyaları, ilk Git eklenme tarihleri, SHA256 | bitti | 2.535 dosya; okuma hatası 0; anlamsal kaynak rolleri P5–P7 ile tamamlanacak |
| P2 | Kod sınıfları, tuple atamalar, miras alınan stil, kayıt kapsamı | denetlendi | 522 ad: 492 tek-grafik, 29 kayıtlı portföy, 1 kayıt dışı örnek; yinelenen ad 0 |
| P3 | Sonuç CSV kayıtları, kapılar ve işlem/TF/ayar kanıtları | sürüyor | 57 tabloda 48.018 satır; dosya bazında fark 0; JSON/arşiv özel sonuçlarının kapsam denetimi kaldı |
| P4 | Kitap kartları ve yönlendirmeler | bitti | 810 benzersiz kart = 333 aile + 70 ret + 35 çıkış/risk modülü + 372 yeni eşleştirme; 226 ayarın 226'sında koşu kaydı var; mantık eşdeğerliği P8'de |
| P5 | GitHub/Freqtrade/TV ve arşiv | sürüyor | 4.889 yapılandırılmış ham/karar/ayar satırı; 2 Excel'de 281+243 satır; arşiv belgeleri ve toplu kayıtlar incelenecek |
| P6 | v3 aday katalogları ve karar zinciri | sürüyor | 17 katalog: 2.592 satır = 2.592 ilk karar; 1.903 ad ve 635 URL eşleşmesi; 54 atıf ayrıca denetlenecek; mantık eşleştirmeleri henüz doğrulanmadı |
| P7 | Dış araştırmalar ve RoboticAutomations | sürüyor | a07d18d alındı; 906 son liste ve 909 dosya bulundu; eski turlar ham sayıma dahil değil; 5.828 ara satırın çoğu destekleyici karar/harita, tekil strateji sayısı DEĞİL |
| P8 | Tekilleştirme + kanıtlı akıbet | sürüyor | Kod kimlikleri için geçici tablo var; kaynak–kod mantık eşleştirmesi tamamlanmadı |
| P9 | Adalet + çapraz kontrol + 40 örnek öz denetim + son rapor | bekliyor | Nihai tekil tablo tamamlanmadan rastgele 40 satır denetimi yapılmayacak |

## Kaynak listesi ve ara çıktılar
- Tam dosya envanteri: `kaynaklar.csv`; tarihler ilk Git eklenmesidir, kullanıcıdan geliş tarihi diye sunulmaz.
- `ara/P1_P2_sayim.json`, `ara/P2_kod_denetimli.csv`, `ara/P2_denetim.json`.
- `ara/P3_test_sonuclari.csv`, `ara/P3_sayi_kontrolu.csv`, `ara/P3_v2_yapisal_kapi.csv`, `ara/P3_v2_hata_satirlari.csv`.
- `ara/P4_ham.csv` … `ara/P7_ham.csv`, `ara/P4_P7_sayi_kontrolu.csv` (536 dosya/listede fark 0).
- `ara/P4_kitap_izleri.csv`, `ara/P4_kitap_sayim.json`.
- `ara/P6_katalog_karar_izleri.csv`, `ara/P6_sayi_kontrolu.csv`, `ara/P6_atif_dogrulama_kuyrugu.csv`.
- `ara/P8_kod_akibet_GECICI.csv`, `ara/P8_kod_tarihce.csv`, `ara/P8_v3_kosulmayan_26.csv`.
- `ara/belge_atiflari.csv`: 409 belgeden 3.122 otomatik atıf; anlamsal inceleme yerine geçmez.

## PR #56 ile eklenen kaynaklar
- `sonuclar/dis_arastirma/2026-11_trend_ortalamaya_donus/ajan1/`: **906** satırlık son liste ana kaynaktır.
- `ajan1/tur1/` (417), `tur2/` (547), `tur3/` (707): **sürüm geçmişi**. Kullanıcının açık talimatıyla ana ham satır / bağımsız kaynak sayısına katılmaz. Üst küme ve id/link sürekliliği ayrıca denetlenecek.
- `karsilastirma/`: 707 eski satırın eşleştirme iddiaları; doğrudan doğru kabul edilmeyecek.
- `derin_gecis/`: 301 benzerlik hükmü, 119 aile kapsamı, önceki 40 örnek denetimi (bizim P9 örneklemimiz değildir).
- `tur4_degerlendirme/`: yeni 199 ve 30 öncelik hükmü; 906'nın alt kümesi/karar katmanı, ayrı yeni strateji havuzu diye sayılmayacak.
- `ajan2/derin_arastirma_26_kayit_raporu.md`: 26 beyanı var; atıf yapılan CSV repoda yok. Raporda tek tek adı olmayan kayıtlar uydurulmayacak; kapsam sınırı ayrıca kaydedilecek.
- `sonuclar/dis_arastirma/2026-11_freqtrade_robotic/`: 909 dosya, 540 küme; `canli_akraba/` karar/karşılaştırma katmanı.

## Şimdiye kadar dosyadan doğrulanan bulgular (nihai rapor değil)
- v2: E1 ve E3 doğru, E2/E4/E5 nedeniyle elenen **73** satır. Yapısal kapıdan kalmak, kendiliğinden haksız eleme anlamına gelmez.
- v2: **6 hata satırı** var; performans başarısızlığı diye kodlanmadı (4 üst TF/alt TF çakışması, 2 evren uygunluğu).
- v3: **35 kod tanımı**, **9 eleme sonucu**, diğer **26** için incelenen sonuç tablolarında başarılı strateji koşusu kanıtı yok. Birim test varlığı stratejinin araştırmada koşulduğu anlamına gelmez.
- `veri/kart_dizini.csv` 438 satır; güncel kartlar 810. Dizin güncel bütün kitap kartlarını kapsamıyor.
- `stratejiler/ek_kaynaklar/son1ay_2026-11.csv` kayıt 14'te fazla CSV alanı var; `_fazla_sutunlar` altında korunuyor, sessizce atılmadı.
- İşlemsel ad tablosundaki 2 holdout geçişi SET kapısıdır; bireysel üstünlük iddiası değildir. Paper üyeliği eski eleme kararını silmez.

## Yeniden üretme (veri denetim betikleri; test/backtest DEĞİL)
Depo kökünden sırayla:
```
python sonuclar/hesap_defteri/betikler/envanter.py
python sonuclar/hesap_defteri/betikler/ham_kaynaklar.py
python sonuclar/hesap_defteri/betikler/kod_denetimi.py
python sonuclar/hesap_defteri/betikler/sonuclar.py
python sonuclar/hesap_defteri/betikler/kitap_izleri.py
python sonuclar/hesap_defteri/betikler/v3_izleri.py
python sonuclar/hesap_defteri/betikler/belge_atiflari.py
python sonuclar/hesap_defteri/betikler/kod_akibeti.py
```
Betikler yalnız standart kütüphane kullanır; strateji modüllerini import etmez, ağ erişimi/paket kurulumu yapmaz.

## Devam noktası
1. P7 yapısal denetimi BİTTİ: 906 son liste, üç eski turun ID/link sürekliliği ve 909→540 üyelik toplamları doğrulandı (`ara/P7_sayim.json`). 707+199=906, çakışma yok. Eski turlarda 18 kural/parametre alanı değişimi kaydedildi; eski satırlar yeni ham strateji sayılmadı. Ajan2 26 beyanının tekil satır CSVsi hâlâ yok.
2. P5/P6: arşiv Markdown strateji tablolarını ve 54 açık atıf kuyruğunu tamamla; destekleyici kararları yeni strateji diye sayma.
3. P8: kaynak kurallarını kod ve gerçekten koşulan ayarlarla karşılaştır. “Benzer/tekrar” iddiasını isimden onaylama; farkı test edilmeyenleri koru. Ham–tekil bağlantısı henüz yapılmadı.
4. P3/P9: hata/atlanma ile performans elemesini ayır; güncel tekil tablo üzerinden seed 20261113 ile 40 kayıt geri izle. Sonra RAPOR.md, commit ve PR. Main'e push/merge yok.

## Saatlik kontrol
Kullanıcı 2026-11-13'te her saat kontrol ve kesinti sonrası devam istedi. Otomatik oturum başlatma/zamanlayıcı aracı mevcut değil; olmayan yetki vaat edilmiyor.
Oturum sürerken saat başlarında bu dosya, Git durumu, kaynak–çıktı farkları ve kalan kuyruk kontrol edilecek. Kullanım sınırında oturum yeniden başlatılamaz; çalışma yeniden etkin olduğunda bu kayıt başlangıç noktasıdır.
İlk saat kontrol hedefi: **13 Kasım 2026 05:00 TSİ (02:00 UTC)**.

## Son ara denetim
`ara/P8_manuel_mantik_denetimi.csv`: Donchian 6h, MACD+EMA100, Faber 10-ay, AdaptiveTrend, Kore volatilite kırılımı ve Robotic K001 kural/kod karşılaştırmaları yazıldı. Önceki eşleştirme hükümleri doğrudan alınmadı. Faber 10 ay-sonu kapanış ortalaması ile günlük 300 günlük ortalama eşit değildir. AdaptiveTrend sınıfında iz süren stop ayarı yok; bu nedenle dokümandaki ATR iz-stop iddiası sınıf davranışı diye tekrar edilmedi.

### 05:00 TSİ saat kontrolü — 2026-11-13 02:00:39 UTC
- Git: yalnız `sonuclar/hesap_defteri/` untracked; korunması istenen mevcut dosyalarda yerel değişiklik yok.
- 327 ana kaynak, 57 sonuç tablosu, 674 ara dosya/listenin kaynak–çıktı farkı 0.
- Ana ham: 8.552 kayıt; eski 417/547/707 turlarında çift sayım yok. 26 strateji beyanlı rapor tek toplu eksik-liste kaydı olarak korundu; 26 isim uydurulmadı.
- Kod günlüklerinden 227 açık kaynak bağlantısı (137 farklı kitap kartı, 87 dış envanter satırı; bazı kartlarda birden çok kayıt) bulundu; konum/ad bütünlük kontrolünde hata 0. Mantık eşitliği bundan otomatik çıkarılmıyor.
- Sıradaki: P5 bağlantılarını akıbet zincirine ekle; kaynak/kod ve temsilci farkını koru; tekil tablonun son kontrolü; seed 20261113 ile 40 kayıt öz denetimi; sonra rapor ve PR.
- Bir sonraki saat kontrol hedefi: 06:00 TSİ (03:00 UTC).

### 06:00 TSİ saat kontrolü — 2026-11-13 03:00 UTC civarı
- Git hâlâ yalnız denetim klasöründe değişiklik gösteriyor; main a07d18d tabanı korundu.
- 906/909 kapsam ve eski sürüm kontrolleri tamam. 77 belgenin ayrıntılı kural bölümleri aynı ham kayıtlara eklendi.
- İlk 40 örnekte sistematik 12 kayıt etkisi (%30) görüldü: Robotic ad alanı, geniş yasak-tür regexi, doğrulanmamış ML ve eksik arşiv sonuç zinciri. Etkilenen parçalar topluca düzeltildi; son nüfus üzerinden öz denetim tekrarlanacak. Bu oran gizlenmeyecek.
- Kaynak profilleri ile operasyonel uygulamalar ayrı tutuluyor; tekil profil toplamı bağımsız alım-satım algoritması sayısı değildir.
- Sıradaki: belge/ayar izi kapsamı, son 40 örnek, nihai CSV/rapor ve PR. Sonraki kontrol 07:00 TSİ / 04:00 UTC.
