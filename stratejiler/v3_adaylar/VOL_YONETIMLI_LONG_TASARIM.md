# Volatilite yönetimli long — uygulama notu

Moreira–Muir kartı yön sinyali üretmez. Her ay başında önceki **tam takvim
ayının** günlük getiri varyansını hesaplar ve pozisyon ağırlığını buna ters
orantılı günceller. Tek-grafik `Strateji.sinyaller` sözleşmesi bu ağırlığı
taşımadığı için uygulama `pf__v3-vol-yonetimli-long` adıyla portföy katmanına
eklenmiştir.

Nedensel uyarlama önceki tam ayın günlük getirilerinden volatiliteyi kullanır;
yıllık hedef %20 ve ağırlık tavanı 1,0 önceden sabittir. Kaynaktaki tüm
örneklemi kullanan ölçek sabiti ileriye bakmaya yol açtığı için kullanılmaz.
Kaynak ABD faktörlerini incelediğinden yıllıklaştırma 252 işlem günüdür.
Motorun zorunlu stop koşulu için ATR(14) × 2 koruma stopu eklenmiştir.

Kaynak: https://www.nber.org/papers/w22208.pdf
