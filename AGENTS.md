# 1L3A — dış ajanlar (Codex / ChatGPT vb.) için kurallar

Bu repo'nun takım lideri Claude oturumudur. Dış ajan **denetler, önerir ve PR açar; birleştirmez.**
Önce `CLAUDE.md` ve `DURUM.md` oku (kararlar ve "Lider kararları günlüğü").

## Kesin kurallar (aşılamaz)
- `main`'e doğrudan push yok. Her iş kendi dalında (`codex/<konu>`), küçük ve tek konulu PR. PR'ı BİRLEŞTİRME.
- Risk limitleri (`motor/risk/limitler.py`, SERT_LIMITLER) değiştirilmez, gevşetilmez, atlatılmaz.
- Martingale, DCA, ortalama düşürme, stopsuz ızgara yasak. Geleceği görme (lookahead) yasak. Sessiz try/except yok.
- Gizli anahtar, token, sunucu adresi asla repoya girmez. Kaynak PDF metni ve üçüncü taraf kod (GPL/AGPL) kopyalanmaz.
- Canlı para ile ilgili hiçbir şey yapılmaz. Paper motoru (`motor/canli/`) sunucuda çalışıyor: davranışını değiştiren PR'da bunu açıkça yaz.
- Yöntem/eşik değişikliği (seçim kapıları, test eşikleri, ön kayıtlar `ON_KAYIT*`) sonuç gördükten sonra önerilirse PR'da "sonuç sonrası" diye işaretle.
- Mühürlü/tarihsel çıktılara dokunma: `sonuclar/evren/v2/`, `sonuclar/kilit/`, `sonuclar/final/` (yeniden üretme).
- `veri/` altındaki kilitli dönem verisi açılmaz (`motor/veri/kilit.py`).

## PR kontrol listesi
- `python -m pytest testler -q -p no:cacheprovider` yeşil (CI aynı komutu koşar).
- Yeni davranış için test; eski bir testi gevşetme / sabit değeri sessizce güncelleme yok (gerekiyorsa gerekçesini yaz).
- PR açıklaması Türkçe ve sade: ne, neden, risk, nasıl doğrulandı.
