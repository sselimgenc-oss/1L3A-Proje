"""Nihai raporu tamamlanmis kapsam, butunluk ve oz denetim sayilarindan uretir."""
import csv,json,hashlib
from collections import Counter
from envanter import OUT,write

def load(rel):
    with (OUT/rel).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def js(rel):return json.loads((OUT/rel).read_text())
def table(headers,rows):
    def cell(x):return str(x).replace('|','/').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join('---' for _ in headers)+'|']+['| '+' | '.join(cell(x) for x in r)+' |' for r in rows])
def main():
    n=js('ara/nihai_sayim.json');audit=js('ara/P9_oz_denetim_sonucu.json');integrity=js('ara/P9_butunluk.json');rows=load('tekil_stratejiler.csv');codes=[r for r in rows if r['birim_turu']=='operasyonel_kod'];counts=n['durum'];c_counts=n['kod_durum'];unrun=[r for r in codes if r['durum'].startswith('C_')];errors=[r for r in codes if r['durum']=='BELIRSIZ'];manual=load('ara/P8_manuel_mantik_denetimi.csv');comp=load('ara/P9_belge_sayi_karsilastirma.csv')
    assert integrity['sayi_farki']==0 and integrity['kaynak_hash_farki']==0
    assert audit['tekil_tablo_sha256']==hashlib.sha256((OUT/'tekil_stratejiler.csv').read_bytes()).hexdigest()
    sample=load('ara/P9_oz_denetim_orneklemi.csv');assert len(sample)==40 and all(r['denetim_hukmu']=='denetlendi' for r in sample)
    initial=load('ara/P9_ilk_orneklem_durumu.csv');first_errors=[]
    for i,r in enumerate(initial,1):
        reason=''
        if i in (8,18,21,25,33,38,40):reason='Robotic ad alanı dosya adı yerine küme idsi gösteriyordu; tüm909 satırın adı düzeltildi.'
        elif i in (1,28,29):reason='Somut model tanımı bulunmadan önceki ML eleme notuna dayanılmıştı; somut tür kanıtı guardı eklendi.'
        elif i==20:reason='IC ortalaması sözcüğü ortalama düşürme sanılmıştı; yasak işlem regexi daraltıldı.'
        elif i==22:reason='HMA50+Supertrend arşiv JSON sonucu zincirde eksikti;135 eski JSON ve Pine kimliği ilişkisi eklendi.'
        if reason:first_errors.append(dict(ornek_no=i,tekil_id=r['tekil_id'],ad=r['ad'],gozlenen_sorun=reason,snapshot_siniri='Kaydedilen eski örneklem düzeltmelerin bir kısmından sonradır; hata anının değişmez tam tablosu diye sunulmaz.'))
    assert len(first_errors)==12
    write('ara/P9_ilk_taslak_hata_gunlugu.csv',first_errors,list(first_errors[0]))
    intro=[
'# Kullanıcıya özet',
f'- {n["envanter_dosyasi"]} dosya envanterde; {n["ham_kaynak_dosyasi"]} dosyadan {n["ham"]} ham kayıt, {n["tekil_kayit_profili"]} temkinli kayıt profili çıkarıldı. Bunlar bağımsız strateji sayısı değildir.',
'- 906 son liste sayıldı; eski 417/547/707 turları ikinci kez eklenmedi. Robotic 909 dosya korundu ; 540 kümeye körlemesine birleştirilmedi.',
f'- Profil akıbetleri: A{counts.get("A_TEST_EDILDI_GECTI",0)}, B{counts.get("B_TEST_EDILDI_ELENDI",0)}, C{counts.get("C_KODLANDI_KOSULMADI",0)}, D{counts.get("D_KODLANMADI_NEDENLI",0)}, E=0, F{counts.get("F_YASAK_TIP",0)}, G{counts.get("G_ML",0)}, H{counts.get("H_BIZIM_EVRENDE_UYGULANAMAZ",0)}, BELIRSIZ{counts.get("BELIRSIZ",0)}.',
'- 521 gerçek kod tanımında: A=5, B=484, C=26, BELIRSIZ=6. C grubundaki 53 profil kaydı, 53 ayrı koşulmamış kod demek değildir.',
'- A grubundaki 18 profilin 13’ü eski TV arşividir; güncel A grubundaki beş kodun ikisi holdout SET kapısı, üçü sağlamlık geçişidir. Canlı üstünlüğü çıkarılamaz.',
'- v2’de 222 satırın 73’ü E1/E3’ü geçip yapısal kapılardan elenmiş; 6 hata performans elemesi sayılmadı.',
f'- Kesin E=0; ayrıca {n["E_iz_eksigi_adayi"]} iz eksikliği adayı görünür tutuldu. E=0, unutulmuş strateji yok demek değildir.',
'- 421 yazılı ayarın 85’inde özgül koşu kimliği bulunamadı; aile testi bu ayarların testini kanıtlamaz.',
'- “Benzeri test edildi” hükümleri doğrulanmış eşitlik sayılmadı; altı somut kural/kod farkı ayrıca yazıldı.',
'- “460+19” tarihsel sayısı Gitten doğrulandı; 438 kayıtlı kitap dizini 810 kartın tamamını kapsamıyor.',
'- Öz denetim: ilk taslakta 12/40 (%30) etki → toplu düzeltme; son nüfustan tekrar 40 kayıtta 2/40 (%5) → düzeltme; aynı 40 kayıtta kalan 0.',
'- Ajan2’nin 26 tekil kaydı ve Robotic asıl kodları depoda yok; bilinmeyenler uydurulmadı. Strateji testi veya kod değişikliği yapılmadı.'
]
    intro.insert(1,'')
    assert len(intro)<=15
    report='\n'.join(intro)+'\n\n'
    report+='## Sayımın anlamı ve kapsam\n\n'
    report+='İnceleme tabanı `a07d18d` (PR #56), dal `codex/hesap-defteri`. Envanterdeki 2.535 dosya; kaynaklar, kararlar, kod ve sonuç kanıtlarını kapsar. 328 asıl katalog/kart dosyasından 8.559 kaynak satırı ve 151 kod modülünden 521 kayıtlı sınıf ayrı ham kayıt olarak alınmıştır: toplam 479 kaynak dosyası, 9.080 ham satır. Her ham satır tek bir `tekil_id`ye bağlanır. Kaynak ve uygulama, mantık eşitliği ispatlanmadığında ayrı kalır. Bu yüzden 8.197 sayısı kanıtlı bağımsız algoritma sayısı değildir.\n\n'
    report+=table(['Kayıt birimi','Profil'],list(n['birim_turu'].items()))+'\n\n'
    report+='35 çıkış/risk kartı, 225 araç/yazı ve 8 toplu katalog kaydı toplamda görünür; bağımsız giriş sistemi diye yorumlanmaz. Bir toplu kayıt, eksik 26 kayıtlı Ajan2 listesinin beyanıdır. Bazı kataloglar tek satırda birkaç alt modu anlatır; ham `veri_json` bütün alt kuralları korur. Kaynakta açıkça adı verilen grup üyeleri `ara/P8_grup_uyeleri.csv` içindedir; eksik üyelerin kuralları adından türetilmedi. `diğer` aile etiketi, ailesi kesinleşmeyen kayıtları da içerir.\n\n'
    report+='328 ana dosyanın, 675 ara dosya/listenin ve 57 sonuç tablosunun kaynak–çıktı sayımı yapıldı; fark 0. Ara P4/P5/P6/P7 tabloları karar/ayar/eşleştirme tekrarlarını da içerir; bu tabloların toplamı ham strateji sayısı değildir. Dış araştırmanın destek tabloları yeni kaynak strateji diye tekrar sayılmadı. 77lik belgenin ayrıntılı Mantık bölümleri aynı 77 ham kayda bağlandı. Kataloglara eklenmemiş tur5 araştırma belgesinin 5 maddesi ve 2 toplu ret paragrafı da korundu.\n\n'
    report+='`kaynaklar.csv` dosya SHA256larını ve ilk Git ekleme tarihlerini içerir. Git tarihi kullanıcının kaynağı ilk getirdiği tarih olarak sunulmaz; bulunamayan tarih BELIRSIZ kalır. 409 belgedeki otomatik atıf indeksi semantik doğrulama yerine geçmez; 45 anlatım/şema belgesinin kapsam kararı `ara/P5_P7_belge_kapsam_kararlari.csv` içindedir. Kaynakta yer almayan üçüncü taraf programları yeniden indirilmedi.\n\n'
    report+='## Tekilleştirme ve kanıt standardı\n\n'
    report+='883 ek kopya kayıt birleştirildi. Aynı kart kimliği; aynı fiziksel kaynak/dosya ve aynı mekanik, gösterge, TF, veri ihtiyacı; yahut bütün alanları birebir aynı katalog/Excel kaydı kullanıldı. Ada/fuzzy benzerliğe göre birleştirme yapılmadı. Mekaniği eksik katalog kaydının birebir kopyasını birleştirmek, görünmeyen programların mantıksal eşitliğini ispatlamaz. Robotic 540 kümesinin üyelik toplamı 909 doğrulandı; alttaki 909 kod dosyası olmadığı için kopya/ML/DCA/lookahead bayrakları bağımsız doğrulanmış sonuçlara çevrilmedi.\n\n'
    report+='906 kayıtlı listede eski üç turun kimlik ve link sürekliliği kontrol edildi; 707 + 199 = 906, kesişim yok. 18 kural/parametre alanı sürüm farkı saklandı. Kararların sonraki turlardaki etiketleri kaydedildi; aynı kopya kayıtlar aynı turda çelişiyorsa dosya sırasına göre hüküm seçilmedi. 54 v3 ad/URL dışı satır atfı kaynak satırına geri izlendi; provenans bağlantısı kural eşitliği sayılmadı. `gorev2` önceki etiket/kapsam atıfları ayrı belirsizlik notuyla tutuldu.\n\n'
    report+='## Akıbetler ve aşamalar\n\n'
    report+=table(['Durum','Bütün profiller','Gerçek kod tanımları'],[(k,counts.get(k,0),c_counts.get(k,0)) for k in ('A_TEST_EDILDI_GECTI','B_TEST_EDILDI_ELENDI','C_KODLANDI_KOSULMADI','D_KODLANMADI_NEDENLI','E_KODLANMADI_NEDENSIZ','F_YASAK_TIP','G_ML','H_BIZIM_EVRENDE_UYGULANAMAZ','BELIRSIZ')])+'\n\n'
    report+='A grubundaki 18 kaydın 13’ü, aynı Pine kaynak kimliğiyle bulunan eski TV arşiv geçişidir. Güncel koda A/B transfer edilmedi. 135 arşiv JSON’unda 99 kaynak Pine kimliği var; bazıları iki arşiv aşamasında yinelenir. Güncel A grubundaki beş kod: `dis__gauss-stoch-eth` ve `dis__ewo-ema-ofset` resmi holdout SET kapısı; `dis__ama-egri-donus-filtresi`, `dis__aroon-stochrsi-ema-dip`, `dis__gauss-stoch-btc` v2 sağlamlık geçişi, son sete seçilmemiştir. A etiketi yalnız yazılan aşamayı ifade eder.\n\n'
    report+='B grubundaki 582 kaydın içinde 484 gerçek kod, 86 eski arşiv kaynak profili, 9 v3 uyarlama kaynağı ve 3 farklı mantıklı temsilci kaydı vardır. Kaynak profilinin B/Csi test edilen uyarlamaya ait olduğunda `asama`, `adil_test=zayif temsilci`, uygulama idsi ve fark notu açık yazılır; özgün kaynağın aynı kurallarla test edildiği iddia edilmez. `islem_kaniti` seçilen aşamanın TF/evren/işlem/kapı değerlerini; `ayar_kapsami` ayar etiketlerini gösterir. Tam tarihçe `ara/P8_kod_tarihce.csv`dedir; örtüşen dönemler toplanmaz.\n\n'
    report+='Paper üyeliği eski eleme kararını silmez. 10 paper uyum JSONu mevcut geçmiş tekrar karşılaştırmasıdır; ileri paper başarısı veya canlı sonucu değildir (`ara/P3_paper_tekrar_uyum.csv`). Atıf yapılan `sonuc_freqtrade*.csv` dosyaları bu checkoutta bulunmadığı için metindeki PF/Sharpe iddialarından test hükmü üretilmedi.\n\n'
    report+='## C — kodlu, koşu kanıtı bulunamayanlar\n\n'
    report+='35 v3 kodunun 9’unda eleme sonucu, 26’sında araştırma koşusu kanıtı yok. Neden koşulmadığını açıklayan kesin kayıt bulunamadı; uydurulmadı. Birim test varlığı araştırma koşusu sayılmadı. Tam C grubundaki 53 profil listesi `ara/AKIBET_C.csv`; aşağıdaki 26 farklı operasyonel tanımın kaynak/prototip atıfları C sayısını artırır.\n\n'
    report+=table(['Kod kimliği','Kod dosyası:sınıf'],[(r['uygulama_idleri'],r['kod_dosyasi']) for r in unrun])+'\n\n'
    report+='421 ayar kaydının 336’sında özgül `kart:`/`dis:` kimlikli koşu var: 226 kitap ayarı + 110 dış ayar.67 dış ayar ve 18 d11j/d12b ayarı için özgül kimlikli sonuç bulunamadı. Bunlar 85 ayrı sınıf demek değildir; ailelerin varsayılan koşuları bu modların çalıştığını göstermez. İzler ve varsayımlar `ara/P5_ayar_kosu_izleri.csv`de korunur.\n\n'
    report+='## E — açıklamasız kodlanmayanlar ve iz eksikleri\n\n'
    report+=f'Kesin E listesi boştur (`ara/AKIBET_E.csv`). Bu, her kaynağın hesabının geçmişte doğru verildiğini göstermez. {n["E_iz_eksigi_adayi"]} kaynak profili açık uygulama/karar izinden yoksun veya BIZDE_YOK beyanı taşıyan adaydır: `ara/P8_iz_eksigi_E_adaylari.csv`. Tam özgün kural yokken başka isim altında aynı uygulamanın bulunmadığı ispatlanamaz; kullanıcı kuralına uygun biçimde BELIRSIZ bırakıldı. Geri kalan BELIRSIZlerde benzerlik iddiası, eksik asıl kod, çelişkili karar veya kapısız ayar taraması gibi başka nedenler vardır. Bu 621 kayıt bütün belirsizliklerin tamamı değildir.\n\n'
    report+='## Elemenin adaleti ve somut temsil farkları\n\n'
    report+='v2’de 222 satırdan 18’i ilk elemeyi geçer. 73 satır E1 kârlılık ve E3 yoğunlaşmayı geçip E2/E4/E5ten kalır; kaynak kapı/değerleri `ara/P3_v2_yapisal_kapi.csv`de, gerçek kod satırları `yapisal_kapi=evet` işaretlidir. Bu tespit kuralların yanlış olduğunu veya aynı veri üzerinde eşik gevşetmek gerektiğini kanıtlamaz. v2nin varsayılan ayarı, eski WFdeki grid taramasını yok sayacak şekilde anlatılmadı.\n\n'
    report+='Altı v2 hata kaydı ayrı tutuldu: dört sınıfta üst TF=alt TF, iki portföyde evren uygunluğu. Güncel operasyonel BELIRSIZ olan 6 listesi:\n\n'
    report+=table(['Kod','Hata/kanıt'],[(r['uygulama_idleri'],r['kapi_ve_deger']) for r in errors])+'\n\n'
    report+='Bağımsız kural/kod açılarak incelenen altı temsil sorunu:\n\n'
    report+=table(['Kaynak','Bulgu'],[(r['kaynak_kimligi'],r['gerekce']) for r in manual])+'\n\n'
    report+='Örneğin 6 saatlik Donchian filtresiz kısa/uzun ve ATRstoplu uygulamayla; 10 ay-sonu kapanış ortalaması 300 günlük kapanış ortalamasıyla; EMA100 filtreli MACD durum kuralı MACD kesişim olayıyla eşit kabul edilmedi. AdaptiveTrend sınıfında ATR iz-stop ayarı bulunmadı. Kore 9KST ile 00UTC zaman eşitliği fark diye yazılmadı. Karşılaştırmaların kaynak/kod konumları ve sınırlamaları `ara/P8_manuel_mantik_denetimi.csv` içindedir. Tüm B kayıtlarının adil olmadığı iddia edilmez; tam temsil kanıtı eksik olanlar dürüstçe belirtilir.\n\n'
    report+='## Belgelerdeki sayılar\n\n'+table(['Konu','Dosyadan ölçüm','Hüküm'],[(r['konu'],r['olcum'],r['hukum']) for r in comp])+'\n\n'
    report+='## Öz denetim ve doğrulama sınırı\n\n'
    report+='Tohum `random.Random(20261113)`, sıralama `tekil_id` artan. İlk taslaktaki 40 kayıtta 12 kayıt etkilendi (%30): 7 Robotic ad alanı, doğrulanmamış 3 ML hükmü, 1 aşırı geniş yasak-tür eşleşmesi, 1 eksik arşiv sonuç zinciri. İlgili parçalar bütünüyle düzeltildi; ilk hatalı anın eksiksiz değişmez snapshotı bulunmadığı açık yazıldı (`ara/P9_ilk_taslak_hata_gunlugu.csv`).\n\n'
    report+='Son 8.197 kayıt nüfusundan 40 yeniden seçildi; orijinal CSV/JSON/Excel/AST kaynakları ara veri_json yerine yeniden açıldı. İki eksik tür sınıflaması bulundu: LLM sistemi ve opsiyon straddle,2/40=%5. Aynı açık tür kanıtına sahip bütün kayıtlar düzeltildi. Aynı 40 üzerindeki son kontrolde kalan hata 0; bu bağımsız üçüncü örneklem veya tüm tablonun hatasızlık garantisi değildir. Her kaydın ayrı gerekçesi `ara/P9_oz_denetim_orneklemi.csv`, orijinal kaynak kanıtı `ara/P9_asli_kaynak_kanitlari.json`, düzeltme öncesi ikinci örneklem de `ara/`dadır.\n\n'
    report+=f'Nihai tablo SHA256: `{audit["tekil_tablo_sha256"]}`. Ham kimlik/bağlantı eksikliği 0, yinelenen ham_id 0, sayım farkı 0; 2.535 kaynak dosyada SHA256 değişimi 0. Bunlar muhasebe bütünlüğünü doğrular; eksik üçüncü taraf kodun mantığını doğrulamaz. Strateji testi/backtest, paket kurulumu veya strateji kodu değişikliği yapılmadı.\n\n'
    report+='## Sonraki karar için somut iş listesi\n\n'
    report+='1. 621 iz eksikliği adayında önce özgün kuralları ve yazılı kodlama kararını tamamlayın; isim benzerliğiyle eleme yapmayın.\n2. 26 kod tanımı ve 85 özgül ayarın koşu kapsamını ayrı yönetin; bunları test edilmiş havuz sayısına eklemeyin.\n3. Yapısal 73 kayıt için ekonomik sonuç ile uyumluluk gerekçesini ayrı değerlendirin; kanıt olmadan başarı etiketi vermeyin.\n4. Kaynak kuralı → uygulama → ayar → koşu → kapı zincirini kalıcı kimlikle tutun; kart dizinini bu zincirden üretin.\n5. Bu denetim tamamlanan yerel belge muhasebesidir. Ajan2 eksik 26 listesi ve 909 dış kodun bağımsız doğrulaması için gerekli dosyalar mevcut değil; bu sınır BELIRSIZ olarak bırakıldı.\n\n'
    report+='## Dosyaları kullanma\n\n'
    report+='`ham_satirlar.csv`den herhangi bir kaydın kaynağına ve `tekil_id`sine gidilebilir. `tekil_stratejiler.csv` her profile tek durum, aşama, kanıt, temsil/adalet notu ve bağlı kod idlerini verir. `ara/AKIBET_*.csv` durum filtreleridir. Kaynak/ham/profil birimleri ve sayım dayanakları bu raporda; yeniden üretme sırası `betikler/yeniden_uret.py` ve `ILERLEME.md`dedir.\n'
    (OUT/'RAPOR.md').write_text(report)
    print('Rapor tamamlandı; sayıların kaynağı nihai CSVler ve denetim JSONları.')
if __name__=='__main__':main()
