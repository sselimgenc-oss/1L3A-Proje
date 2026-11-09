# Test sonuçları — 1. tur (2026-10-10)

Veri: 39 enstrüman (25 kripto: 1 yıl 15dk; ABD hisse, BIST, altın, petrol: Yahoo sınırı nedeniyle
yalnızca ~60 gün 15dk). Giriş 15dk, yön 4s/1s. Eğitim = ilk %70, test = son %30.
Maliyet tek yön: kripto %0,08, ABD %0,03, BIST %0,06, emtia %0,03. Hedef: kazanma ≥ %45, PF ≥ 1,3.

## Strateji özeti (tüm enstrümanlar, net)

| Strateji (kaynak) | İşlem eğt/test | Kazanma eğt/test | PF eğt/test | Net beklenti R eğt/test | Brüt beklenti R eğt/test |
|---|---|---|---|---|---|
| S1 Trend geri çekilme (Lien, Backus, Wallace) | 2848 / 1247 | %38 / %36 | 0,72 / 0,65 | −0,13 / −0,17 | 0,00 / −0,02 |
| S2 Momentum 20-100 (Lien, Bernstein) | 32 / 10 | %31 / %40 | 0,20 / 0,30 | −0,64 / −0,48 | −0,27 / −0,10 |
| S3 Açılış aralığı kırılması (Christensen, Roy, Tranquil) | 593 / 186 | %51 / %50 | 0,81 / 0,78 | −0,11 / −0,12 | 0,01 / 0,01 |
| S4 Bollinger dönüşü (Velez, Lien) | 1873 / 764 | %53 / %55 | 0,53 / 0,58 | −0,18 / −0,15 | −0,02 / −0,02 |
| S5 Önceki gün tepe/dip kırılması (Lien iç gün, Bernstein) | 323 / 142 | %40 / %41 | 0,49 / 0,50 | −0,35 / −0,34 | −0,03 / −0,05 |
| S6 Sahte kırılma / Fader (Lien, Christensen, Bernstein) | 3500 / 1420 | %50 / %52 | 0,77 / 0,79 | −0,12 / −0,10 | 0,01 / 0,01 |
| S7 VWAP geri alma (Christensen) | 3270 / 1354 | %48 / %46 | 0,74 / 0,65 | −0,14 / −0,20 | −0,02 / −0,05 |
| S8 Camarilla L3/H3 (Tranquil Trader) | 3327 / 1332 | %50 / %52 | 0,65 / 0,76 | −0,17 / −0,11 | 0,01 / 0,02 |

Hiçbiri hedefi (PF ≥ 1,3) tutmuyor; hepsi maliyet sonrası zararda.

## Teşhis
- **Brüt (maliyetsiz) beklenti her stratejide ≈ 0R.** Sinyaller yönü tahmin etmiyor; zarar
  maliyetten geliyor (kriptoda 15dk işlemde gidiş-dönüş maliyet riskin %10–40'ı).
- **4s/1s trend filtresi kalıcı avantaj vermiyor.** Kripto 15dk'da ileri getiriler: eğitim
  döneminde (düşüş) uzun işlemler −%0,14, kısa işlemler +%0,29 (gün sonuna kadar); test döneminde
  tam tersi (uzun +%0,59, kısa −%0,16). Filtre yalnızca dönemin genel yönünü yansıtıyor.
- **S6 koşul analizi (kripto):** saat, ADX, yön ve trend uyumu kırılımlarının hiçbirinde tutarlı
  brüt avantaj yok; yalnızca çok oynak günlerde (günlük ATR > %7,5) brüt +0,06/+0,14R, net yine eksi.
- **Hisse/BIST/emtia:** 15dk veri ~60 gün; test dönemi ~18 gün, işlem sayıları 5–80. Bazı
  pozitif hücreler (ör. emtia S1 PF 1,1–2,1) bu örneklemle istatistiksel olarak anlamlı değil.
