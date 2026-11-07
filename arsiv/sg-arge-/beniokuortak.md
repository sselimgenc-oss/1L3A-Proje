# 🚀 Autonomous Multi-AI Quantitative Trading Framework

Bu proje, finansal piyasalar için kantitatif borsa stratejileri geliştirmek, optimize etmek ve backtest (geriye dönük test) süreçlerini otomatikleştirmek amacıyla **Claude Code** ve **ChatGPT Codex** ekosistemlerini hibrit ve otonom bir yapıda buluşturur.

---

## 🤖 Model Rolleri ve Sorumluluk Matrisi

Sistem içi maliyetleri, token tüketimini ve haftalık limitleri optimize etmek için roller sıkı bir şekilde ayrıştırılmıştır:

| Model / Ekosistem | Rol | Temel Sorumluluklar |
| :--- | :--- | :--- |
| **Claude Opus 5.5** | Danışman & Denetçi (Auditor) | - Finansal stratejilerin mantıksal denetimi<br>- Token ve haftalık limit optimizasyonu<br>- Görevlerin efor ve maliyet analizine göre Claude veya Codex tarafına dengeli dağıtımı |
| **Claude Code Sonnet 5.5** | Moderatör (Moderator) | - Günlük iş akışı koordinasyonu<br>- GitHub üzerindeki görev sırasının (Queue) yönetimi<br>- Mimari bütünlüğün korunması |
| **GPT-5.6 Sol** | Görev Yürütücüsü (Worker) | - Claude tarafından atanan görevlerin işlenmesi<br>- Python tabanlı borsa stratejisi kodlarının yazılması (Backtrader, VectorBT, Pandas vb.) |
| **GPT-5.6 / Sol 6.1** | Geliştirme & İyileştirme Danışmanı | - Codex tarafındaki kod kalitesinin artırılması<br>- Algoritmik performans ve hız optimizasyonu önerileri |

---

## 🔄 GitHub Üzerinden Otonom İletişim Protokolü

İki farklı AI ekosistemi doğrudan insan müdahalesi olmadan GitHub üzerinden haberleşir:

1. **15 Dakikalık Periyodik Yoklama (Heartbeat):** 
   Her iki yapay zeka ekosistemi de repo içerisindeki durum dosyalarını (`state.json` veya aktif GitHub Issue etiketlerini) **15 dakikada bir** kontrol ederek sıranın kendisine gelip gelmediğini denetler.
   
2. **Dürtme (Poke / Ping) Mekanizması:** 
   Moderator (Sonnet 5.5) veya Denetçi (Opus 5.5) kritik bir görev atadığında, GitHub Issue yorumlarında ilgili modeli etiketleyerek `@codex-worker` veya `@claude-moderator` şeklinde "dürterek" 15 dakikalık bekleme süresini baypas edebilir ve anlık tetikleme sağlayabilir.

3. **Veri Akışı ve Versiyonlama:** 
   - Strateji parametreleri, ham veriler ve backtest sonuç raporları `strategies/` ve `results/` klasörleri altında saklanır.
   - Her tur sonunda yapılan değişiklikler anlamlı commit mesajlarıyla (`[Claude-Mod]`, `[Codex-Sol]` etiketleriyle) depoya işlenir.

---

## 📂 Proje Yapısı

```text
├── .github/
│   └── workflows/          # Otomasyon ve tetikleyici betikler
├── strategies/             # Geliştirilen borsa stratejileri (Python)
├── backtests/              # Backtest sonuçları, metrikler ve loglar
├── data/                   # Piyasa veri setleri (CSV / Parquet)
├── state.json              # AI'lar arası sıra ve görev durum takip dosyası
└── README.md