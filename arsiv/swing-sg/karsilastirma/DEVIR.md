# Koordinatör devir notu (12 Ekim 2026)

Eski koordinatör: session_011BRVoXb6shVtKMUVB7Sb5H (uzun geçmiş; token tasarrufu için devredildi, arşivlenebilir).
Ayrıntılar: `karsilastirma/EKIP.md` (ekip kuralları, strateji adları, gerçek para planı v1, yol haritası) ve `karsilastirma/DENETIM_12EKIM.md` (denetim + çapraz denetim + Codex analizi).

## Kullanıcı ve çalışma kuralları
- **Her zaman Türkçe** yaz (İngilizce yazınca rahatsız oldu). Kısa, net, jargonsuz; sonucu önce söyle. Gereksiz kötümser ton kullanma, dengeli ve dürüst ol.
- "Benden onay istemene gerek yok, her türlü işlemine onayım var." Yalnız şunlarda sor: gerçek para, test ortasında kural değişikliği, botu durdurma, maliyetli/geri alınamaz adım, herkese açık yüzey (public repo/Pages yasak; panel özel kalır: "ben görsem yeter").
- **Test kuralı:** 60 günlük kağıt test (9–10 Ekim → 9–10 Aralık) bitene kadar strateji kuralları değişmez; yalnız gerçek hata düzeltmesi (ekip dalı → kagit-deneme iş akışı → PR → birleştir).
- **Kullanıcı kararı (12 Ekim):** panelde ve stratejilerde yeni optimizasyon/deney YOK. Aralık'a kadar yalnız izleme + hata düzeltme.
- **Token tasarrufu:** kullanım limiti dar (7 günlük uyarı). Alt ajan/yeni deney açma; kısa çalış.

## Oturumlar
- Ekip oturumları (strateji, algo, day trade) arşivlendi; hata düzeltmeleri koordinatörde.
- **Panel güncelleyici:** session_012zeiJo3K4ANnisxVVBWBqp (Sonnet). Rutin trig_01QxwwmpqYNBzCG8Fd965fww, 3 saatte bir :31. Adımlar: dev dalından `karsilastirma` checkout → `python3 -m karsilastirma.panel_veri --cikis ... --onceki ...` → ArtifactData batch (if_version). Yalnız [alarm] seviyesinde koordinatöre send_message + PushNotification.

## Repolar ve dallar (sselimgenc-oss)
| Hesap | Repo | Ekip dalı | Bot durum dalı |
|---|---|---|---|
| Swing + Trend kolları | swing-sg | claude/exciting-hypatia-lxexf6 (panel, karsilastirma/ burada) | kagit-durum, kagit-trend-durum |
| Strateji (Seviye Kırılımı + Güçlü–Zayıf Sepeti) | strateji-sg | claude/dreamy-cannon-lsimjy | kagit-durum |
| Algo (Trend Avcısı + Panik Dönüşü) | algo-sg | claude/optimistic-franklin-9w0pdk | kagit-durum |
| Day trade (Akşam Momentumu, Tuzak Kırılım, Trend Günü Molası) | day-trade-sg | claude/confident-ramanujan-j7tq1t | kagit-durum |
Botlar main'den GitHub Actions ile çalışır (cron sık atlanır; botlar geçmişi yeniden oynattığı için veri kaybı yok). workflow_dispatch 403 verir; test için ekip dalına push ile kagit-deneme iş akışı.

## Panel
https://claude.ai/artifact/XCVNapDZJFWbVKq59dGysU (özel, db capability; koleksiyonlar hesaplar/{id}, islemler/{id}, meta/ozet). Kaynak: swing-sg dev dalı `karsilastirma/panel/index.html`, veri `panel_veri.py`, koni `koni.py`/`koni.json`. Yeniden yayın: Artifact publish (url ile; önce read).

## Takvim
- **22 Ekim:** Aralık karar kartı (strateji bazında: rol, kağıt sonuç, beklenti uyumu, korelasyon, uygulanabilirlik; DENETIM E bölümündeki DSR/kuyruk/öneriler ve iki beklenti: iyimser + stres).
- **Her Pazartesi 08:47 (TR):** tüm hesaplar haftalık değerlendirme.
- **9–10 Aralık:** son değerlendirme + gerçek para önerisi.

## Güncel görüş (kullanıcıya söylenen)
- Hiçbir sistem tek başına kanıtlanmış değil; en sağlamlar trend kolları ve Güçlü–Zayıf Sepeti, sonra swing; algo ve Seviye Kırılımı zayıf; day trade eleme adayı.
- Aralık planı: 5.000 $, 1x, eşit ağırlık, 3–4 sistem; kaldıraç birkaç ay gerçek sonuçtan sonra. Ölçüt: TL mevduat ≈ dolar bazında yıllık ~%15 (aylık ~%1,2).
- v2 önerileri (yalnız aday, dondurulmuş kodla yeni ileri testten önce gerçek paraya girmez): KGT %40/KMN %60, algo kollarına ters oynaklık ağırlığı, day trade BTC SMA200, swing stop ≤ %15.

## Açık takip
- Swing: DOT/APT/NEAR emirleri (PR #5 düzeltmesi) botun sonraki çalışmasında açıldı mı.
- Day trade 0 işlem: BTC 4s filtresi alışları kesiyor (hata değil).
- Trend BTC kapanmamış günlük mum kullanıyor (etkisi geçici; değiştirilmedi).
