"""C denetimi analiz dosyaları (1-2. turun yeniden incelenen betikleri): kontrol/kanıt metinleri elle, 'ne yapıyor' çeviri modülünün açıklamasından."""
import importlib, re, pathlib
from tv.analiz_yaz import A
def doc(mod):
    m = importlib.import_module(f"tv.stratejiler.{mod}"); return (m.__doc__ or "").strip(), m
def al(i, mod, kontrol, kanit, onceki, ek=""):
    d, m = doc(mod)
    A(i, d, f"{m.TF} (çeviri)", ",".join(getattr(m, "EVREN", getattr(m, "SEMBOL", []))), kontrol, "al",
      f"Önceki tur gerekçesi: «{onceki}». B2 kesin-eleme listesinde (kapalı kaynak, strategy() yok, gerçek repaint/lookahead, DCA/grid/martingale, veri yok) bu betik YOK; kod okundu ve `tv/stratejiler/{mod}.py` olarak çevrilip test edildi. {ek}".strip(),
      kanit=kanit, hedef=mod)
T = "temsilci seçilmedi"
al("Fckzv8iH","sq_reversal","Yalnız geçmiş mumlar; security/pivot yok. Repaint yok.",[r"shortcondition|longcondition",r"valin\s*=",r"strategy\.entry"],T)
al("ghocsiv7","gap_fill","Yalnız önceki mum ve seans başı; `change(time(\"D\"))`. Repaint yok.",[r"upgap|dngap",r"valuewhen",r"strategy\.(entry|exit|close_all)"],T,"Gün içi mantık: saatlik hisse verisiyle.")
al("i9tJOtjl","lube","Sürtünme hesabı geçmiş 500 muma bakar; eşikler `[5]` gecikmeli. Repaint yok.",[r"friction",r"long=|short=|end=",r"strategy\.(entry|close)"],T)
al("NfihxKxr","penny_st","ta.supertrend yön değişimi; sabit TP/SL. Repaint yok.",[r"buySignal|sellSignal",r"strategy\.exit",r"exitOnFlip"],T)
al("x39mKkAp","narrow_state","Yalnız kapanmış mum koşulları. Repaint yok.",[r"isNarrowState|isElephant",r"condLong|condShort",r"strategy\.(entry|exit)"],T)
al("HDSdFMa3","bb_rsi_lo","Yalnız geçmiş mum; stop emri bir mum geçerli. Repaint yok.",[r"long\s*=|close_long",r"strategy\.entry",r"strategy\.cancel"],"kopya (Bollinger+RSI; uCV8I4xA tutuldu)","Parametreler farklı (RSI6, BB200, yalnız long, çıkış kuralı var) → kopya değil.")
al("zopumZ8a","bb_rsi_b","Yalnız geçmiş mum. Repaint yok.",[r"RSIvalue|RSIlength",r"strategy\.entry",r"strategy\.cancel"],"kopya (Bollinger+RSI; uCV8I4xA tutuldu)","RSI16/45 ve BB20 → uCV8I4xA'dan (RSI6/BB200) farklı varsayılanlar.")
al("25Ffpyo0","sweep_sky","`ta.pivothigh(high, 5, 5)` 5 mum gecikmeli onay (repaint değil); seviye onaydan sonra kullanılıyor.",[r"pivothigh|pivotlow",r"sell_signal|buy_signal",r"strategy\.entry"],"likidite süpürme pivot girişi (repaint riski)")
al("mmrInMTp","mom_seq","Yalnız geçmiş mum dizisi. Repaint yok.",[r"validBullishSequence|validBearishSequence",r"longSetup",r"strategy\.entry"],T)
al("49jNhJXM","seq_snap","Yalnız geçmiş mum dizisi + RSI. Repaint yok.",[r"runIsBullish",r"longSetup",r"strategy\.entry"],"scalper (5dk veri yok)","Betik 5 dk ile sınırlı değil (hiçbir saat/seans kodu yok), saatlik test edildi.")
al("YfPnKE22","macd_ashi","Stop emirleri `strategy.cancel` ile bir mum; repaint yok.",[r"crossover\(delta|crossunder\(delta",r"strategy\.entry",r"strategy\.exit"],T)
al("Eq4kPrrJ","golden_trident","`ta.highestbars(high, 30)==0` yalnız geçmiş; repaint yok.",[r"ph\s*:=|pl\s*:=",r"dir\s*=",r"longTrigger",r"strategy\.(entry|close|exit)"],"swing-anchored VWAP; temsilci seçilmedi")
al("mzv5SGie","silver_macro","`request.security(...,lookahead_off)`; DXY/US10Y günlük veri.",[r"request\.security",r"exitCondition\s*=|entryCondition\s*=",r"strategy\.(entry|close)"],T,"Veri: ^TNX (Yahoo); DXY çıkışı varsayılanda kapalı.")
al("rKsnPJbJ","fib_conf","Yalnız geçmiş aralıklar. Repaint yok.",[r"fibLevels|isNear",r"longCondition|shortCondition",r"strategy\.(entry|exit)"],T)
al("o9dV6uWc","ema_mtf_stoch","`request.security(...,lookahead_off)` üst TF stokastik; çeviride son kapanmış mum.",[r"mtfRes",r"stochLong|stochShort",r"strategy\.(entry|exit|close)"],T)
al("n9ty3SVh","quantum_st","SuperTrend; tablo için `request.security(...lookahead_off)` yalnız görsel. Repaint yok.",[r"buySignal|sellSignal",r"strategy\.entry",r"request\.security"],T)
al("V87nRt9v","macd_sniper","Yalnız geçmiş mum. Repaint yok.",[r"longSignal|shortSignal",r"strategy\.(entry|exit|close)"],T)
al("M6uONKNI","bb_power","Yalnız geçmiş mum. Repaint yok.",[r"bull_cross|bear_cross",r"squeezeReleased",r"strategy\.(entry|exit)"],T)
al("OUOx3rYT","ribbon_flip","Yalnız geçmiş mum. Repaint yok.",[r"flipBull|flipBear|pullBull",r"strategy\.(entry|exit)"],T)
al("LcA4mcE6","conf_rank","`barstate.isconfirmed`; geçmiş mum. Repaint yok.",[r"scoreL|scoreS",r"longSig|shortSig",r"strategy\.(entry|exit|close)"],T)
al("egTb7TgJ","gauss_eth","Gauss filtresi geçmiş; repaint yok.",[r"longCondition\s*=",r"closeCondition\s*=",r"strategy\.exit"],"kopya (Gaussian Channel; erJi1tWf tutuldu)","Giriş mantığı erJi1tWf'den farklı (bant kırılımı + StochRSI + SMA200 rejimi + alt bant stop).")
al("d1JxXpid","gauss_btc","Gauss filtresi geçmiş; repaint yok.",[r"longCondition\s*=",r"closeCondition\s*=",r"strategy\.exit"],"kopya (Gaussian Channel; erJi1tWf tutuldu)","Giriş mantığı erJi1tWf'den farklı.")
al("71yKm18B","ichi_sol","Bulut `[displacement]` ile geçmişe kaydırılmış; repaint yok.",[r"tkCrossUp|aboveCloud",r"longCondition\s*=",r"strategy\.(entry|close|exit)"],"kopya (Ichimoku; boHD0HzE tutuldu)","TK-kesişim + MFI + bulut tabanı stopu → boHD0HzE'den farklı mantık.")
al("xx3enmiW","ichi_tier","HTF `lookahead_off`; bulut geçmişe kaydırılmış.",[r"strongBull|neutralBull|weakBull",r"htfBullish",r"strategy\.(entry|exit|close)"],"kopya (Ichimoku; boHD0HzE tutuldu)","Kademeli (güçlü/nötr/zayıf) kesişim + HTF onayı → farklı mantık.")
al("ZLcmWQtj","pmax_rsi","Yalnız geçmiş; repaint yok.",[r"Pmax_Func",r"buySignalk|sellSignallk",r"strategy\.entry"],"kopya (PMax/OTT ailesi; temsilciler tutuldu)","RSI üzerinde T3 + PMax → fiyat PMax'inden farklı gösterge.")
al("nVECqIQx","one_pct_week","Haftalık seans; yalnız geçmiş. Repaint yok.",[r"newSession",r"strategy\.entry",r"strategy\.exit"],"eğitim (TASC makale örneği)","TASC makalesi örnek kod ama gerçek bir alım-satım kuralı (haftalık -%1 limit alış, +%1 hedef) içeriyor.")
al("bFXf4IXh","kelly_bands","Stop emirleri `strategy.cancel` ile yönetilir; repaint yok.",[r"crossUpper|crossLower",r"strategy\.entry",r"useKelly"],"eğitim (Kelly boyutlandırma örneği)","Örnek ama gerçek bir bant-kırılım giriş kuralı içeriyor.")
for i in ("IHVPG6TS","jjhUHcje","xAEG4ZJG"):
    d, m = doc("ma_demo")
    A(i, "TradingView'in örnek stratejisi: SMA(14) ile SMA(28) kesişimi (IHVPG6TS: yön değiştir + $ cinsinden profit/loss; jjhUHcje: yalnız long + kademeli iz süren stop örneği; xAEG4ZJG: yalnız belirli tarih/saat penceresinde işlem). Asıl konu emir mekaniği.", "1g (çeviri)", "kripto,abd,bist,emtia",
      "Yalnız geçmiş SMA'lar. Repaint yok.", "al", f"Önceki tur 'eğitim/şablon' diye elemişti; sinyal SMA(14/28) kesişimi gerçek bir kural → ortak sinyal `tv/stratejiler/ma_demo.py` ile test edildi (SL/TP/zaman penceresi örneklerinin kendileri çevrilmedi: sinyal aynı).",
      kanit=[r"crossover\(sma\(close, 14\)",r"strategy\.entry",r"strategy\.exit"], hedef="ma_demo")
A("Ip667jzb","MA kesişimi: bkz. modül.","1g","hepsi","Yalnız geçmiş MA'lar.","al","Önceki 'kopya/genel' gerekçesi geçersiz; varsayılan ayarlarla çevrildi.",kanit=[r"fscrossup|fscrossdw",r"golong|goshort",r"strategy\.entry"],hedef="ma_cross_dyn")
al("Qg1Jra51","rsi_bulldiv","Pivotlar `lbR` mum gecikmeli; 'early' modu yalnız k<lbR sağ mumla onaylı pivotu kullanır (gelecek mum yok). Betik 'No look-ahead' diyor ve kod bunu doğruluyor.",[r"leftOk|rightOk",r"strategy\.entry",r"No look-ahead"],T)
al("nRklAGPI","qqq_macro","Üç dış sembol `request.security(..., \"D\", close)` (lookahead parametresiz = off); günlük grafikte aynı mumda.",[r"request\.security",r"longCondition\s*=",r"exitCondition\s*=",r"crashTriggerPerc"],T,"Betikteki çöküş-eşiği (%20) oran olarak karşılaştırıldığından hiç tetiklenmez: çıkarıldı.")
al("U0wTnRuE","rf_ha","HTF yön `f_htfDir()` içinde `d[1]` (son KAPANMIŞ HTF mum) ile `lookahead_on` birlikte: bu standart non-repaint kalıbıdır → önceki tur 'geleceği gören' kararı HATALIYDI.",[r"d\[1\]",r"lookahead",r"longSig|shortSig"],"geleceği gören request.security (lookahead_on, ofsetsiz)")
al("GoeqO1ev","sweep_rev","Pivotlar `pivotLen` gecikmeli, seviye onaydan sonra kayıtlı; repaint yok.",[r"pivothigh|pivotlow",r"sweepHighSignal|sweepLowSignal",r"strategy\.(entry|exit)"],"likidite süpürme pivot girişi (repaint riski); temsilci seçilmedi")
al("HPbRZvsV","ott_ex","Yalnız geçmiş; dashboard için çok `request.security` var, sinyal onlara bağlı değil.",[r"buySignalc|sellSignallk",r"strategy\.entry"],"kopya (OTT; ycDUERPO tutuldu)","Farklı varsayılanlar (VAR(2), %1.4) ve fiyat kesişimi → kopya değil.")
al("DG9ePZuk","st_rg","Yalnız geçmiş; sinyal [1] gecikmeli.",[r"buySignal\[1\]|sellSignal\[1\]",r"close_order",r"strategy\.entry"],"kopya (Supertrend; tutulanlar var)","SL/izleyen stop + 1 mum gecikmeli giriş içeren farklı strateji.")
al("WpJ5ym7u","pps","`pivothigh(prd, prd)` prd=2 mum gecikmeli; repaint yok.",[r"pivothigh|pivotlow",r"bsignal|ssignal",r"strategy\.(entry|close)"],"pivot bazlı giriş (repaint riski)")
al("ouvmvItR","ob_retest","Bölgeler yalnız kapanmış itki mumlarından; repaint yok.",[r"bullImpulse|bearImpulse",r"touched",r"strategy\.(entry|exit)"],"hacim order block (SMC), 83hmaEOQ temsilci")
al("EcEYc8ap","dmi_adx3","Yalnız geçmiş. Repaint yok.",[r"pullbackLongTrigger",r"chandLong",r"strategy\.(entry|exit|close)"],T)
al("CtFpKECD","shinobi_ha","`ta.pivothigh(ha_high, 5, 5)` 5 mum gecikmeli; repaint yok.",[r"buy_setup|sell_setup",r"swing_bull_ok|struct_bull",r"strategy\.(entry|exit)"],"Heikin Ashi + pivot; temsilci seçilmedi")
al("8Ti8z8QO","mtf_stack","`request.security(...,lookahead_off)`; repaint yok.",[r"score1|score2|score3",r"longTrigger",r"strategy\.(entry|exit|close)"],"çoklu zaman dilimi + pyramiding")
print("ok")
