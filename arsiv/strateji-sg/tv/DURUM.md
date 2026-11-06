# tv-eleme durumu

- Aşama 1 BİTTİ: 164 link → 160 kaynak çekildi, 41 aday (`tv/aday.csv`).
- Aşama 2 BİTTİ: 36 aday çevrildi (`tv/stratejiler/`), motor `tv/motor.py`, backtest `python3 -m tv.calistir`.
- Aşama 3 BİTTİ: 3 strateji geçti (hybrid_brk, sqzmom, macd_reloaded). `tv/sonuclar/ozet.csv`, `tv/RAPOR.md` (`python3 -m tv.rapor`).
- Aşama 4 BİTTİ: `python3 -m tv.kagit --durum X` tek başına çalışıyor (canlı ve `--yerel` denendi). Başlangıç 2026-10-14 00:00 UTC, 57 gün. Saatlik tura/panele bağlama koordinatörde.
