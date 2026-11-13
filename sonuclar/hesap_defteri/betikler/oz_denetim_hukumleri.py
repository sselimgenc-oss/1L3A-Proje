"""Kaynağa dönülerek okunmuş 40 örneğin insan/model hükümlerini açıkça kaydeder.
Bu bir strateji testi değil; kanıt/etiket muhasebesinin öz denetimidir.
"""
import csv,json,hashlib,random
from envanter import ROOT,OUT,write

def load(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
NOTES={
1:'Gerçek EmaHizaliOlgunYukselis sınıfı ve özgün wf_evren kayıt 730/833 açıldı: iki gecti=False; 15m 268, 5m 98 işlem. Eleme nedenleri ve grid seçimleri kaynakla uyumlu.',
2:'S0299 alt BB/yatay bant ve üst banda çıkış kuralı mevcut. BENZERI_TEST beyanı ayrı; birebir uygulama sonucu kanıtlanmadığı için BELIRSIZ doğru.',
3:'Kaynak açıkça kural_metni_yok ve addan_tahmin diyor. Aile benzerliğinden ölçülmüş sonuç türetilmedi.',
4:'Robotic dosya yolu/adı kaynakla aynı. negative_shift bayrağı rapor beyanı; asıl üçüncü taraf dosya yok, kesin F/G/B yapılmadı.',
5:'GGR 12 ay oluşum/6 ay işlem/20 çift/2sigma kaynakta var. Bizdeki pairs ailesiyle tam eşitlik gösterilmedi; hisse/pairs diye otomatik H yapılmadı.',
6:'Katalogda pairs adı/URL ve dış Sharpe var, tam kural yok. Aynı kaynak kaydının birebir kopyaları bağlanmış; dış Sharpe proje geçişi sayılmadı.',
7:'XLSX P3-009 yeniden açıldı; Delta-RSI kesişim ve seçilebilir filtreler, tam filtre ayarı eksik. Aynı kaydın tam alan kopyası birleşmiş; test sonucu uydurulmadı.',
8:'Kaynak bilgi(okunmadı), mekanik boş; başka satırla aynı denmesi doğrulanmış tekilleştirme yapılmadı.',
9:'Carter kartında çoklu TF EMA/GHL/QTI mevcut; özel formül belirsizliği ve aile atfı tam test kanıtı değil.',
10:'S0794 çiftin 30/1 ortalaması, 0.2 giriş/0.1 çıkış tanımı var; genel pairs sonucuna eşitlenmedi.',
11:'Kaynak ad/path doğru; adjust_trade_position ve normalize bayrakları asıl kod olmadan bağımsız doğrulanamıyor.',
12:'S0854 kayan Johansen 250/20 ve -z büyüklük; başka pairs ayarıyla aynı test sayılmadı.',
13:'Çok ufuklu momentum kartı ve yazarın negatif sonucu var; dış yazar ölçümü bizim B hükmü yapılmadı.',
14:'OFI/aggressor verisi ihtiyacı mevcut. Envanter veri_yok beyanı korundu; güncel uygulama/ret zinciri kesin değil.',
15:'S0510 Keltner/yeşil mum/orta bant çıkışı tanımlı. BENZERI beyanı bağımsız test kanıtına çevrilmedi.',
16:'BTC 22UTC/2saat kaynak kuralı korundu. Mevcut id atfı tam kural/stop/koşu eşitliği yerine geçmedi.',
17:'Pairs için dış sonuç iddiası var; tam mekanik kaynak kataloğunda yok. Aynı katalog kopyası birleştirildi, genel pairs sonucu aktarılmadı.',
18:'S0230 günlük/1h Alligator ve buy-stop ekleri var; tek TF genel Alligator testi aynı sayılmadı.',
19:'TechnicalExampleStrategy kaynak CMF kuralı/ad/URL mevcut. kodlandi envanter iddiası özgün kaynakla eşdeğerlik hükmü yapılmadı.',
20:'MA Reverse dış iki aylık 31 işlem ve %85 DD beyanı var. Modern 1L3A elemesi diye etiketlenmedi.',
21:'TrendFollowingStrategy için sonuc_freqtrade_dakika.csv atfı var ama dosya yok. Atıftaki PF değerlerinden B üretilmedi.',
22:'S0769 EMA200+ROC bandı ve long-only kuralı var. S0768 veya genel ROC ile otomatik birleştirilmedi.',
23:'TQQQ için ikincil ret gerekçesi ortalama düşürme diyor; asıl katalogda yeniden alım kuralı yok. Kesin F hükmü verilmedi.',
24:'Robotic MultiMA dosyası doğru. KULLANILABILIR etiketi test geçişi veya bizim uygulama kanıtı değil.',
25:'Düzeltme öncesi BELIRSIZ eksik sınıflamaydı. Asıl mekanik özet açıkça LLM tabanlı sistem diyor; küresel kural düzeltmesiyle G_ML.',
26:'Kesitsel momentum 30 mum/topK ve yakınsama filtresi kaynakta var; genel pf__rotasyon sonucu kaynağın testi sayılmadı.',
27:'MASTER kayıt209 ve özgün on_eleme kayıt209 açıldı; araç/altyapı seti, strateji değil. Belgeli D ve araç birimi doğru.',
28:'Düzeltme öncesi BELIRSIZ eksik sınıflamaydı. Asıl varlık opsiyon ve opsiyon zinciri gereksinimi açık; küresel kural düzeltmesiyle H.',
29:'Denham kartında kırılım/dönüş yön ayrımı ve aralık süresi belirsiz; aile atfı kaynak alt kuralına test sonucu üretmiyor.',
30:'Robotic Trix dosya/ad/TF kaydı doğru. Sadece kârda çıkış bayrağından stopsuz grid hükmü türetilmedi.',
31:'Özgün on_eleme kayıt1072 açıldı: 3 dakika ve OOS yok gerekçesi. Kaynak ES/3dk ile uyumlu; belgeli kodlamama D, performans B değil.',
32:'Robotic FreqAI ve pozisyon büyütme bayrakları var; asıl kod yokken bunlar yalnız rapor beyanı, BELIRSIZ gerekçesi açık.',
33:'RSI/ADX alt modları ayrı mekanik varyantlar olarak kaynak JSONda korunmuş. PINGPONG tarifinde ekstra alım yok; ortalama düşürme diye yanlış F yapılmadı.',
34:'Robotic Momentumv2 dosya/4h/stop kaydı aynı; kullanılabilirlikten geçmiş proje testi türetilmedi.',
35:'Sharp MR SMA2/8 ve ROC sıralama kuralı var. Connors ailesi adı ve dış metrikler tam test eşitliği yapılmadı.',
36:'S0819 EMA21 geri çekilme/likit500/ROC sırası/4gün kuralı var. Genel MA ailesiyle aynı sonuç denmedi.',
37:'NQ ORB için aynı iddiası var; kaynağın kuralı tam değil ve metrikler eksik. Ad/ailenin yakınlığıyla birleştirilmedi.',
38:'Python ticaret makinesi adlı ilk katalog satırı ile sonraki RSI/BB notu ayrı tutulmuş; tam kaynak/test hükmü kesinleştirilmedi.',
39:'Robotic quantumfirst path/ad/TF aynı; kendi proje sonuç kanıtı bulunmadığı için belirsiz.',
40:'SURGE-WSI için sonraki HMM notu var, ilk kaynak model türünü göstermiyor; önceki G hükmü bağımsız doğrulanmış sayılmadı.'}

def main():
    sample=load(OUT/'ara/P9_oz_denetim_orneklemi.csv');table=load(OUT/'tekil_stratejiler.csv');byid={r['tekil_id']:r for r in table}
    expected=random.Random(20261113).sample(sorted(byid),40)
    assert [r['tekil_id'] for r in sample]==expected
    old=load(OUT/'ara/P9_ikinci_orneklem_duzeltme_oncesi.csv');assert [r['tekil_id'] for r in old]==expected
    for r,prev in zip(sample,old):
        n=int(r['ornek_no']);r['denetim_hukmu']='denetlendi';r['hata']='hayir';r['gerekce']=NOTES[n];r['ikinci_gecis_onceki_durum']=prev['atanan_durum'];r['ikinci_gecis_hatasi']='evet' if n in (25,28) else 'hayir';r['nihai_durum']=byid[r['tekil_id']]['durum']
        assert r['atanan_durum']==r['nihai_durum']
        if n==25:assert r['atanan_durum']=='G_ML'
        if n==28:assert r['atanan_durum']=='H_BIZIM_EVRENDE_UYGULANAMAZ'
    write('ara/P9_oz_denetim_orneklemi.csv',sample,list(sample[0]))
    checks=dict(tohum=20261113,nufus=len(table),sirala='tekil_id artan',ornek=40,ilk_taslak_sistematik_etkilenen=12,ilk_ornek_hata_orani=0.30,ilk_ornek_sinir='İlk taslak hata anının tam değişmez snapshotı yok; gözlenen 7 ad+5 tür/kanıt sorununun eski 40 üzerindeki etkisi kaydedildi.',ikinci_gecis_hata=2,ikinci_gecis_hata_orani=0.05,ikinci_duzeltme_sonrasi_ayni_40_kalan_hata=0,son_ayni_40_kontrol_hata_orani=0.0,tekil_tablo_sha256=hashlib.sha256((OUT/'tekil_stratejiler.csv').read_bytes()).hexdigest(),sinir='Son sıfır oran aynı 40 üzerindeki düzeltme kontrolüdür; yeni bağımsız üçüncü örneklem veya tüm tablonun hatasızlık güvencesi değildir. BELIRSIZ etiketler özgün kod eksikliğini gidermez.')
    (OUT/'ara/P9_oz_denetim_sonucu.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2));print(checks)
if __name__=='__main__':main()
