# Paper v2 kabul testi (tekrar modu ↔ holdout)

Dönem: 2025-11-08 → 2026-11-06 (holdout). Her strateji kendi 10.000 USD kasasında, s = 0.5, v2 varsayılan ayar. Net = kasa son özsermayesi / 10000 − 1 (açık pozisyonlar veri sonunda kapatılır).

| strateji | etiket | holdout net | holdout yeniden | paper net | fark (puan) | ham/kabul (holdout) | paper işlem | ortak | sadece H | sadece P | teşhis limitsiz H / P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| dis__e0v1en | iyi_gorundu | +1.97% | +1.97% | +1.54% | -0.43 | 83/83 | 84 | 81 | 2 | 3 | +1.97% / +1.54% |
| dis__ewo-ema-ofset | dogrulandi | +3.67% | +3.67% | +3.64% | -0.03 | 46/46 | 46 | 46 | 0 | 0 | +3.67% / +3.64% |
| dis__gauss-stoch-eth | dogrulandi | +10.37% | +10.37% | +6.11% | -4.26 | 159/137 | 123 | 95 | 42 | 28 | +8.15% / +6.78% |
| dis__haftalik-macd-gunluk-ma | iyi_gorundu | +2.37% | +2.37% | +2.35% | -0.03 | 65/64 | 57 | 57 | 7 | 0 | +4.66% / +4.42% |
| dis__hma-atr-rider | iyi_gorundu | +2.79% | +2.79% | +9.61% | +6.82 | 282/230 | 279 | 230 | 0 | 49 | +8.31% / +8.52% |
| dis__jt-awesome-osilator | iyi_gorundu | +23.09% | +23.09% | +8.90% | -14.19 | 208/112 | 70 | 61 | 51 | 9 | +17.41% / +16.36% |
| dis__lube | iyi_gorundu | +2.99% | +2.99% | +2.55% | -0.44 | 20/20 | 21 | 20 | 0 | 1 | +2.99% / +2.55% |
| dis__uc-ortalama-boga-sma60 | iyi_gorundu | +9.04% | +9.04% | +9.31% | +0.27 | 48/48 | 42 | 42 | 6 | 0 | +9.04% / +8.94% |
| dis__voltarget-trend | iyi_gorundu | +2.52% | +2.52% | +1.27% | -1.24 | 140/98 | 22 | 6 | 92 | 16 | +4.41% / +7.34% |
| pf__sabit_sepet | iyi_gorundu | +7.76% | — | +7.80% | +0.04 | 363/— | 21 | — | — | — | — |

## Strateji bazında yorum

| strateji | yorum |
|---|---|
| dis__e0v1en | 81/83 işlem eşleşti; eşleşen işlemlerin K/Z toplamı farkı -3 USD. Fark -0.43 puan neredeyse tamamen başlangıç etkisi (neden 4): ZEC'te 2025-11-08'in ilk saatlerinde paper-only 3 işlem (-58 USD) ve holdout-only 2 işlem (-19 USD; giriş saatleri farklı). Limitler hiç bağlamadı. |
| dis__ewo-ema-ofset | Tam uyum: 46/46 işlem birebir eşleşti (limitler hiç devreye girmedi); fark 0.03 puan (maliyet/yuvarlama). |
| dis__gauss-stoch-eth | Limitler kaldırılınca fark -1.4 puan (neden 4: 4 başlangıç işlemi -35 USD; neden 5: ortak işlem K/Z'si -9%). Limitliyken fark -4.3: paper'da tavan (neden 1) 202 girişi kırptı / 166'sını reddetti; holdout oynatmasında 22 red (neden 1, 2). |
| dis__haftalik-macd-gunluk-ma | Uyum: 57 işlem eşleşti, fark 0.03 puan (holdout'ta 7 işlem tavanla paper'dan farklı kabul edildi; limitsiz 4.66 / 4.42). |
| dis__hma-atr-rider | Mekanik uyum (limitsiz 8.31 / 8.52, 282/282 işlem). Limitli fark +6.8 puan tamamen neden 1: kayan stop (ATR izi) nedeniyle anlık stop riski küçülür, paper 49 ek girişi kabul eder (+458 USD; ölçüm: anlık risk / başlangıç risk toplamı medyan 0.42); holdout oynatması başlangıç riskini sabit tuttuğu için 52 girişi reddeder. |
| dis__jt-awesome-osilator | Mekanik uyum (limitsiz 17.41 / 16.36, 208/208 işlem; ortak işlem K/Z'si -6%). Limitli fark -14.2 puan, neden 1: sabit stoplu kârdaki pozisyonlarda anlık stop riski büyür (ölçüm: giriş anlarında anlık risk / başlangıç risk toplamı medyan 1.94, p90 3.78), paper 138 girişi reddedip 149'unu kırptı ve 70 işlem yaptı; holdout oynatması başlangıç riskini sabit tuttuğu için 208 ham işlemin 112'sini kabul etti. Günlük -%3 limiti paper'da 1 kez tetiklendi (4 işlem), holdout oynatmasında hiç (neden 3/5). |
| dis__lube | 20/20 holdout işlemi eşleşti. Fark 0.44 puan: paper'da ek 1 işlem (başlangıç etkisi, -32 USD; neden 4) + özsermaye boyutu (neden 5). |
| dis__uc-ortalama-boga-sma60 | Uyum: 42 işlem eşleşti; holdout'ta 6 işlem kabul edilip paper'da ayrıca girmedi (nedenler 1-2); limitsiz 9.04 / 8.94. |
| dis__voltarget-trend | Limitsiz: +2.9 puan (neden 4: ilk barda 17 yarı-trend girişi, +495 USD). Limitliyken -1.2: tavan çok sık bağlar (687 red); hangi işlemlerin girdiği iki tarafta farklı (6 ortak işlem). |
| pf__sabit_sepet | Uyum: portföy ölçeği (s = grup payı 0.5) ↔ pf_net = prod(1 + s x günlük getiri) - 1; fark 0.04 puan. |

`teşhis limitsiz`: ölçüm amaçlı; HESAP limitleri (toplam stop riski, kaldıraç, günlük -%3, kill) iki tarafta da kaldırılır, işlem mekaniği (giriş/çıkış/boyut/maliyet) karşılaştırılır. Üretimde limitler ASLA gevşetilmez.

## Fark nedenleri (belgelenmiş)
1. **Toplam açık stop riski ölçüsü (%5 tavan).** Holdout oynatması (`secim.yeniden_oyna`) her açık işlemin *başlangıç* risk tutarını sabit toplar; motorlar (backtest, portföy, paper)
   tavanı pozisyonun *anlık* stopa mesafesiyle ((fiyat − stop) × miktar) ölçer. Kayan (trailing) stoplu stratejide (hma-atr-rider) paper daha az giriş reddeder; sabit stoplu kârdaki
   pozisyonlarda daha çok. Tavan bağlayıcı olduğunda hangi işlemlerin girdiği ve boyutları iki tarafta farklıdır. Paper, motorun sert limit uygulamasıdır; holdout ölçümü yaklaşıklıktır.
2. **Reddedilen girişin akıbeti.** Holdout'ta reddedilen işlem sonsuza dek kaybolur; paper'da sinyal sürüyorsa sonraki barlarda yeniden denenir (farklı giriş tarihi -> "sadece paper"/"sadece holdout").
3. **Günlük -%3 limitinin zorla kapatması.** Holdout, açık işlemleri R yolunun doğrusal ara değeriyle değerler ve yeniden girmez; paper gerçek son fiyattan (stop kayması) kapatır ve sinyal sürüyorsa sonra yeniden girer.
4. **Başlangıç etkisi.** Holdout yalnız girişi >= 2025-11-08 olan işlemleri sayar (o tarihte açık olan pozisyon sayılmaz); paper tekrarı düz başlar ve sinyali süren stratejide ilk barda
   (TradFi için ilk işlem günü) yarı-trendde girer. Canlı paper'da da aynıdır (strateji o günkü durumdan başlar).
5. **Özsermaye tanımı (boyutlandırma).** Holdout: nakit + yalnız açık işlemlerin zararı (muhafazakâr); paper: gerçek MTM özsermaye (açık kâr dahil) -> kârlı dönemde paper'ın pozisyonları biraz daha büyük.
6. **Funding.** Kripto: aynı gerçek seri. TradFi (DK_): holdout sürekli süre x giriş fiyatı x %0.01/8s (yalnız long); tekrar modu 8 saatte bir ayrık, o anki fiyatla (short'a yazılmaz; aynı kural). Canlı paper
   gerçek Binance TradFi funding'ini öder ve ayrı alanda tutar.
7. **Ayrıntılar.** Adım/tick yuvarlaması ve min notional (paper'da `min_notional` ile reddedilen çok küçük girişler), sembol kuralları varsayılanı; etkileri küçük.
