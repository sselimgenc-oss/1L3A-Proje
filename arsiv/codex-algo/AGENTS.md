# Codex Algo çalışma sınırı

- Bu proje Claude'un depolarından ve çalışmalarından tamamen bağımsızdır.
- Yalnızca bu checkout (`/workspace/codex-algo`) içinde dosya oluştur, değiştir, test et ve çalıştır.
- Kardeş depolar yalnızca karşılaştırma ve çakışmayı önleme amacıyla salt okunur incelenebilir.
- Kullanıcı açıkça ayrıca onay vermedikçe kardeş depolarda dosya, Git metadatası, dal, çıktı veya çalışma durumu oluşturma; hiçbir şeyi değiştirme, taşıma ya da silme; bu depolarda yazan komut çalıştırma.
- Tüm yeni kod, veri, önbellek, test çıktısı ve çalışma durumu yalnızca `/workspace/codex-algo` altında tutulmalıdır.
- Claude'un test ettiği `Hybrid Breakout (hezSShJr)`, `Squeeze Momentum (G40dtEbK)` ve `MACD ReLoaded (VO6DY8s1)` stratejilerini uygulama, backtest etme veya paper teste dahil etme.
- PDF'lerdeki yazar beyanlarını doğrulanmış sonuç gibi sunma. Pine kaynağı doğrulanamayan model açıkça "Codex uyarlaması" olarak adlandırılmalıdır.
- Gerçek emir gönderme. Bu depo yalnızca backtest ve paper-test içindir.
- Sinyali kapanışta üret, işlemi sonraki barda uygula; komisyon ve kaymayı testlerden çıkarma.
- Gizli anahtarları veya kişisel verileri dosyalara, loglara ya da örnek yapılandırmalara yazma.

