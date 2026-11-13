# Kapı 6 teşhisi: "neredeyse her şey anlamlı" (T<0 iken p=1e-5)

Sonuç: simülatörde HATA BULUNAMADI. Belirti kapı 6'nın ne ölçtüğünden ve aday havuzunun seçilmişliğinden geliyor. Kod değiştirilmedi.
Betikler: `/tmp/claude-0/-home-user/d9801314-f689-5b3c-ae41-5973e32ea499/scratchpad/teshis/t1.py` ... `t6.py`.

## Kanıtlar (HAM:X005:244#v1, 1h, 13 sembol; T=-335,5R, 8500 işlem)
1. Aynı birim (madde 1): gerçek ham R (`tek_grafik.py:44` `tek_ham_kos`, çarpan 2,0; R = net/risk$, funding dahil) ve simülasyon
   (`kapanis_kosu.py:255` maliyet_ayarlari x2; `evren_k2.py:184` net = yön*(çıkış-giriş) - taker*(giriş+çıkış), /risk) aynı birimde.
   Geri-oynatma testi: simülatör GERÇEK giriş mumlarında koşturuldu: işlem başına korelasyon 0,998; toplam -262R (gerçek -335R), yani
   fark işlem başına +0,008R (simülatör hafif iyimser, p'yi muhafazakâr yapar). 4s-kirilim: korelasyon 0,9985; +404R gerçek, +490R replay.
2. Aynı sayı/çıkış (madde 2): `n_islem`=8500, yani `cakisma_suz` sonrası TÜM işlemler, sim'de işlem başına 1 rastgele giriş (aynı sayı,
   aynı yön, stop çarpanı mult=stop_mesafe/ATR14 ve tutma süresi aynı). `n_islem_x2`=138 farkı beklenen: `kendi_hesabi_oynat` %1,5 risk +
   -%30 kill ile durur (kill_x2=1); kapı 6 kill'siz ham R toplamıdır. Tutma süresi (`evren_k2` hm) kaynaklı yanlılık da yok:
   hm=gerçek -0,0962, hm=sabit 23 -0,0813, hm karıştırılmış -0,0935 R/işlem (ilk 6 sembol).
3. Neden sim "çok daha kötü": rastgele giriş boş hipotezi x2 maliyetle işlem başına brüt +0,019R, net -0,096R (maliyet 0,115R/işlem).
   Gerçek girişler aynı maliyeti öder (replay x0 +0,118R, x2 -0,004R; maliyet farkı 0,122R) ama brüt kenarı +0,118R. Yani strateji
   RASTGELE ZAMANLAMADAN daha az kaybediyor (sim ortalama -782R, sd 66, B=30'da hiçbir sim -335R'ye ulaşmadı). Kapı 6 "kâr var mı"
   değil "giriş zamanlaması rastgeleden iyi mi" sorusunu yanıtlar; maliyet sürüklenmesi büyük (1h, 3 ATR stop) olduğundan T<0 ve p küçük
   birlikte olabilir. 34 T<0&p<=0,05 kaydın 19'u 1h, 18'i n>5000. Bunlar K1 (net>0) zaten geçemez; tek başına kapı 6 anlamlı sayılmamalı.
4. `ek` yolu (madde 3): p oranı ek=False 151/256 (%59), ek=True 31/53 (%58): fark yok, kaynak `ek` değil. ek=None yolu `evren_k2.py:131-185`
   eski hızlı/yavaş yol; `testler/test_evren_k2_esdeger.py` 22/22 geçti. (Aynı kimlikte eski v2 sonucu dosyası yok; eski yolu doğrudan
   çalıştırıp B ile karşılaştırma yapılmadı: bu kısım kod okuma + test ile doğrulandı.)
5. v2 ile karşılaştırma: `sonuclar/evren/v2/test.csv` yalnız eleme_durum=gecti olan 17 satırı testlemiş, bunların 10'u p<=0,05 (%59). Yani
   v2'de de elemeyi geçen aday havuzunda oran aynı; "939'da birkaç keşif" paydası eleme öncesi hipotez sayısıydı. Kapanış listesi (kitap/
   önceki turdan seçilmiş kimlikler) benzer biçimde seçilmiş; %59 hatadan değil seçilmişlikten bekleniyor. Ayrıca B=100000 ile p tabanı 1e-5.
6. İstatistik yönü (madde 5): `v2/test.py:41` `sim >= gerçek` doğru. Dönem hizası (madde 4): ham `giris_zamani >= analiz_bas` (`test.py:86`),
   sim çeyrek alt sınırı analiz_bas'ı en çok bir çeyrek aşabilir (`test.py:120`, `alt_sinir` verilmiyor): ihmal edilebilir, ATR NaN ise
   geçersiz sayılır (gecersiz_oran 0).

## Kök neden ve öneri
- Kod hatası yok; bulgu tasarım: (a) boş hipotez maliyet sürüklenmeli, T<0'da p anlamsız; (b) havuz seçilmiş olduğundan yüksek anlamlılık oranı.
- Öneri 1 (uygulama yok): kapı 6'yı yalnız K1-K5'i geçenlere koş (`Baglam.k6_on_eleme_tf` tüm TF'ler için, `kapanis_kosu.py:311`); T<=0 ise p=1.
- Öneri 2: raporda p yanında `T - sim_ort` (R/işlem) ve brüt (x0) kenarı göster; "tuzak": 1h/4h kısa stoplarda sim_ort ağır negatif.
- Öneri 3 (isteğe bağlı): sim'e funding eklenmesi gerekmez (kripto replay'de gerçek funding zaten ham R'de; sim'de yok, p'yi sistematik değiştirmez).
- Karar kullanıcıda: DURUM.md kararlarıyla çelişen değişiklik önerilmedi.
