# Volatilite yönetimli long — tasarım notu

Moreira–Muir kartı yön sinyali üretmez. Her ay başında önceki **tam takvim
ayının** günlük getiri varyansını hesaplar ve pozisyon ağırlığını buna ters
orantılı günceller. Mevcut `Strateji.sinyaller` sözleşmesi yalnız yön, stop,
hedef ve çıkış döndürür; aylık hedef ağırlığı veya pozisyonu yeniden dengeleme
emrini taşımaz. Sabit long sinyali yazmak kartın temel kuralını uygulamaz.

Uygulama için araştırma ve yürütme katmanlarında, sinyal anında bilinen hedef
ağırlık ve aylık yeniden dengeleme desteği gerekir. Önerilen nedensel uyarlama:
önceki ayın günlük getirilerinden örneklem varyansı, önceden seçilmiş yıllık
volatilite hedefi ve en çok 1,0 ağırlık. Kaynaktaki tüm örneklemi kullanan
ölçek sabiti ileriye bakmaya yol açar; kullanılmamalı. Motorun zorunlu stop
koşulu için ayrıca ATR(14) × 2 koruma stopu gerekir. Bu tasarım tamamlanmadan
kart `kodlama_v3.csv` içinde `belirsiz` olarak kalır.

Kaynak: https://www.nber.org/papers/w22208.pdf
