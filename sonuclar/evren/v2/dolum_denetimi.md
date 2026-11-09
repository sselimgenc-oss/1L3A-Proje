# P0-5 Fill-assumption audit: dip-buy scalp strategies (evren WF, 2017_gelistirme)

Scope: investigation only; no repo file modified. Dev data only (cut at 2025-11-01 via default `kilit_ac=False`). Scratch code: this directory
(`motor_pes.py` = copy of engine with pessimism knobs, `run.py`, `diag.py`, `sweep.py`, `unm.py`; logs `log_*`, `diag_*`, `sw_*`).
Repro set: 12 liquid crypto symbols (BTC ETH SOL DOGE LINK XRP ADA BNB TRX XLM BCH ZEC), 2017-08 .. 2025-10, per-symbol cost table
(`evren_maliyet.maliyet_ayarlari`), the strategy's most frequent WF parameter set (`en_sik_ayar`), pooled PF on net_pnl.
Sanity: the pessimism copy with all knobs = 0 reproduces `backtest()` trade list exactly (`DataFrame.equals` True).

## Verdict: NOT an engine fill bug. Delay effect is a real "falling-knife filter" effect for the two 5m strategies, but the edge is thin and fill-sensitive. Overall: UNCLEAR-to-WEAK, not artifact.

* Engine fill/ordering model is causal and conservative (no lookahead found).
* "Delay raises PF" is true only for the two 5m strategies (ewo 5m, aroon 5m) and marginally ewo 15m. For cluc 15m and bb-alt 15m delay LOWERS PF
  (saglamlik.csv: bb 1.46->1.07, ewo15 1.66->1.29, cluc 1.23->1.09 as well; only ewo5 1.63->1.82 and aroon5 1.47->1.80 rise).
  Note those WF-level `g1_pf` numbers are lower than WF baseline for the 15m ones too, so the "suspicious" pattern is specific to the 5m pair.
* The mechanical reason is NOT a cheaper entry price; it is removal of crash-continuation trades (see check 3).
* None of the 5 is `saglam_mi` (all fail K5_dsr; cluc also K3_boot_alt). Edge under realistic-pessimistic fills: ~PF 1.0-1.6 and in 2025 ~flat/negative.

## 1. Entry price / lookahead  (OK)
* `motor/backtest/motor.py:1-3` docstring and code: signal row i is computed from bar i; `bekleyen_giris` is stored at bar-close (motor.py:480-481) and filled
  at bar i+1 OPEN: `fiyat = _tick(D(o) * (1 + yon*kayma))` (motor.py:301), `o` = acilis[i+1]. Stop taken from signal-bar values (stop = close - k*ATR computed at bar i,
  `motor/strateji/dis/_gosterge_d3.py` D3Taban.sinyaller ~l.54-60). Strategy indicators use only closes up to bar i (checked `kosullar()` of the 5 classes:
  `d11i_github.py` l.100-138 bb-alt, l.312-337 ewo, aroon l.66-95; `d9_atlanan_b.py` l.237-251 cluc; cluc volume filter uses `.shift(1)` mean). No lookahead.
* Entry bar: entry is at open, so the same bar's full high/low is entirely AFTER the fill; checking stop with `l <= p.stop` on the entry bar (motor.py:341-358)
  is correct (not using pre-entry range). Entry with `o <= stop` is rejected (`gecersiz_stop`, motor.py:303-305), so no entry-bar stop_gap.
* Costs on entry: slippage `kayma_bps` + taker; position size uses cost-inclusive risk (`motor/risk/limitler.py:40-43`).

## 2. Intrabar ordering  (pessimistic, OK)
* motor.py:340-358: order is stop_gap, hedef_gap, stop_vur, hedef_vur -> stop wins when both touched in the same bar (docstring l.4). Stop fill = stop price minus
  `stop_kayma` (5-12 bps by symbol), gap fill = open. These strategies have no fixed target (hedef NaN); exits are `cikis_long` signal (evaluated at close i, filled at open i+1,
  motor.py:466, 283-286), time exit (`zaman_cikisi_mum`) and ATR stop. Signal exit fills at next open with `kayma` + taker.
* Residual optimism (not lookahead): a stop fill at stop price (+5-12 bps) is unrealistic in flash crashes where the bar trades far through the stop intrabar.
  My stress `S` knob (stop filled X% of the way from stop to bar low) hits exactly the trades that carry the edge-losses (see check 5/numbers).

## 3. How delay is implemented and why PF rises  (real conditioning effect)
* `GecikmeliStrateji` (`motor/arastirma/wf_evren.py:345-376`): `sinyaller().shift(1)` of ALL signal columns (yon, stop, hedef, zaman_cikisi_mum, cikis*), calendar columns excluded
  (test `testler/test_y3_gecikme_takvim.py`). So entry moves from open[i+1] to open[i+2]; the stop LEVEL stays anchored to close[i] (stale); exits also shift.
  Implementation is correct; no bug.
* Decomposition (pooled 12 symbols; `diag_*.txt`, `unm.py`):

| strategy | base PF | delay-all | delay entry only | delay exit only |
|---|---|---|---|---|
| ewo 5m | 1.517 | 1.857 | 1.839 | 1.512 |
| aroon 5m | 1.853 | 1.969 | 1.941 | 1.881 |
| ewo 15m | 1.903 | 2.041 | 2.084 | 1.880 |
| cluc 15m | 1.436 | 1.301 | 1.311 | 1.426 |
| bb-alt 15m | 1.229 | 1.154 | - | - |

  Exit delay is irrelevant; the entry delay does everything.
* Not a "better price": delayed entry price is on average 1.1% (ewo5), 0.9% (aroon5), 1.2% (ewo15), 1.3% (cluc15) HIGHER than the base entry; only 28-33% of delayed
  entries are cheaper (the bounce has already started in most cases).
* Real source: the delayed entry is rejected via `gecersiz_stop` when open[i+2] <= stale stop (61/1200 ewo5, 21/915 aroon5, 19/590 ewo15, 66/1243 cluc15, 27/2346 bb).
  The base trades that get skipped are almost all immediate stop-outs: ewo5 68 trades, meanR -0.85, sumR -57.9 (61 of 68 exit by stop); aroon5 21 trades meanR -1.03 (all stop);
  ewo15 19 trades meanR -0.94; bb 27 trades meanR -0.81. Matched trades (kept by delay) have PF: ewo5 1.77 (delay 1.857), aroon5 2.06 (1.97), ewo15 2.16 (2.04), bb 1.28 (1.15).
  So the delay is a "wait one bar; skip if the knife already went through k*ATR" filter. It is tradable in live (you see the open of bar i+2 and the stale stop), i.e. a
  real effect, NOT lookahead. In ewo5, the matched-only comparison shows meanR 0.247 vs 0.252 (delay) - entry timing itself adds nothing; the whole PF jump = avoiding ~6% of signals
  that cost -0.85R each. Those trades are flash-crash continuation events (big adverse moves), exactly where the engine's stop fill (stop - 8 bps) is least trustworthy.
* Implication: base PF is depressed by crash-continuation losers that a trivial pre-entry guard ("skip if price at fill time already < stop") would remove; the engine's base entry
  does not apply that guard at i+1 because the signal bar's close is still above the stop. A rule "re-check stop vs. fill price at entry" is already there (`gecersiz_stop`), so base
  catches only o[i+1] <= stop. Delay simply gives the knife one more bar to declare itself.

## 4. Freqtrade-style exits (ROI / trailing / custom)
* The 5 strategies use none of them: only ATR stop (k*ATR from signal close), `cikis_long` signal (e.g. close > EMA16, close > BB mid) and time exit (ewo 32 bars, aroon 24 bars; cluc/bb none).
  Their `cikis_ayarlari` is the default (no ROI table, no trailing; grep of `cikis_ayarlari` in d11i_github/d9_atlanan_b shows only other classes). The ROI/trailing/geri_cekilme
  paths in the engine (motor.py:454-478) use only closed-bar data (close, `p.ekstrem` updated at bar close) and exit at next open - causal - but are not exercised here.
  Original freqtrade `minimal_roi`/`stoploss` semantics (evaluated per candle on the candle's own close, executed by the exchange) are replaced by next-open fills, which is more conservative.

## 5. Costs (OK)
* `sonuclar/evren/maliyet_tablosu.csv` / `evren_maliyet.py:66-71,83-88`: taker 5 bps/side; kayma 2 (BTC, ETH), 3 (large alts), 5 (ZEC/HYPE/XLM/BCH) bps; stop_kayma 5/8/12 bps. Engine applies
  entry slippage+taker on entry (motor.py:301, 322-323), exit slippage+taker on signal/time exits (motor.py:283-286) and stop slippage+taker on stops (motor.py:354-355); funding from real series.
  Both legs charged. Hedef (limit) exits have no slippage but none are used here. Round trip ~14-26 bps; cost x2 (carpan 2) keeps all 5 > 1 (table below).
* Weak point: 3-12 bps slippage is small relative to the adverse selection of buying/selling a panic bar. See stress.

## Numbers: does the edge survive a pessimistic-but-realistic fill model?
Pooled 12 crypto symbols, PF on net_pnl. Variants (copy of engine, `motor_pes.py`): `cost2` = fees+slippage x2; `E10` = entry fill moved 10% of the way from open to bar high
(long) ; `XS10` = signal/time exits 10% from open toward low AND stop fills 10% of the way from stop to bar low; `delay1`= GecikmeliStrateji(1). (Stop-first ordering is already in base.)

| strategy (tf) | n | base | cost x2 | E10 | E10+XS10 | E15+XS15 | E10+XS10+delay1 | E25+X25+S25 | E50+X50+S50 (extreme) |
|---|---|---|---|---|---|---|---|---|---|
| ewo 5m | 1180 | 1.52 | 1.41 | 1.34 | 1.23 | 1.12 | 1.33 | 0.92 | 0.56 |
| aroon 5m | 915 | 1.85 | 1.73 | 1.68 | 1.58 | 1.46 | 1.61 | 1.24 | 0.83 |
| ewo 15m | 570 | 1.90 | 1.81 | 1.69 | 1.53 | 1.38 | 1.50 | 1.12 | 0.66 |
| cluc 15m | 1243 | 1.44 | 1.34 | 1.26 | 1.15 | 1.03 | 0.96 | 0.83 | 0.49 |
| bb-alt 15m | 2346 | 1.23 | 1.13 | 1.12 | 1.05 | 0.97 | 0.94 | 0.82 | 0.54 |

Concentration / regime (base trades, from `sw_*.txt`):
* Remove the 10 best-R days: ewo5 1.52->1.23, aroon5 1.85->1.47, ewo15 1.90->1.50, cluc15 1.44->1.20, bb 1.23->1.12. Top days are flash-crash dates (2020-03-13, 2023-08-17, 2021-05-10/21, 2024-12-09, 2024-01-03).
* 2025 (dev period through Oct): ewo5 PF 0.50 (n=41), ewo15 0.55 (26), bb 0.93 (170), cluc 1.08 (69), aroon 1.39 (24). Recent decay for the ewo family.
* 2017-19 is spot-proxy data (no funding), ewo5/cluc PF there is similar to 2020+, so not the driver.
* Survival summary: aroon 5m is the most robust (PF >= 1.45 at E15+XS15); ewo 5m/15m survive moderate stress (1.1-1.5) but not extreme; cluc 15m and bb-alt 15m are marginal (PF ~1.0 at E15+XS15, <1 with delay) - effectively cost-fragile.

## Recommendations
1. No engine fix required for look-ahead; fill/ordering code is sound. Do not describe the K1c result as "entry price improvement"; it is a skip-filter effect.
2. Add a test pinning the filter semantics: signal on bar i, bar i+1 gaps/closes below stop -> base enters at open[i+1] and is stopped on bar i+1, delayed run rejects with `gecersiz_stop`
   (`testler/test_y3_gecikme_takvim.py`-style, tiny synthetic bars). Also log `reddedilenler` counts in saglamlik K1c output so the PF jump can be attributed (matched vs skipped).
3. Make K1c more informative: report PF of matched-only trades (base trades that also exist under delay), and add a "stale-stop rejection off" variant (re-anchor stop to fill: stop = fill - k*ATR)
   to separate timing from filter effects. Treat g1_pf > base PF as a red flag requiring attribution, not as extra robustness.
4. Add an adverse-fill stress to the robustness suite (e.g. entry/exit/stop at X% of open->extreme range, X in {10,15,25}); gate on PF > 1.1 at E15+XS15. cost x2 alone is too lenient
   (scalps survive it but not range-proportional slippage). The `PES` knobs in `motor_pes.py` are a ready 10-line patch (entry price at motor.py:301, exit open at 283-285, stop fill at 354).
5. Stop-fill realism: for `stop` exits on bars whose range exceeds ~k*ATR, fill at a worse level than stop-8bps (e.g. midpoint stop->low). The edge of all 5 lives in tail events, which is where this matters most.
6. Consider adding the "skip if open already < stop / price fell > k*ATR since signal" guard directly to these strategies (it is what delay actually does), then re-run WF; expect PF ~ matched-only values above.
7. Because 2025 shows decay for the ewo family and all 5 fail DSR (K5), keep them out of the final set until re-validated with the stress above.
