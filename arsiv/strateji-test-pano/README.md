# Sg Test Panel - All-Weather SPS-03 Otonom Portföy Panosu

Bu paket, 10.8 yıllık SPS-03 backtest onaylı 27 lider stratejinin ve 7 alt havuz hesabının canlı simülasyonunu ve otomatik takibini sağlar.

## Kurulum ve GitHub Pages Canlı Yayını
1. Bu zip içeriğini GitHub reposunun ana dizinine yükleyin.
2. Repo sayfasında Settings -> Pages sekmesine gidin.
3. Build and deployment -> Source kısmından "Deploy from a branch" ve "main / (root)" seçin.
4. Settings -> Actions -> General -> Workflow permissions kısmından "Read and write permissions" seçip kaydedin.
5. GitHub Actions her saat başı (:11 geçe) bot_engine.py motorunu çalıştırarak data.json dosyasını ve piyasa fiyatlarını günceller.
