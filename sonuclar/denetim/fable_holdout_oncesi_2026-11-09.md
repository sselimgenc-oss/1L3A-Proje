# v2 holdout öncesi bağımsız denetim (Fable) — 2026-11-09

## Kısa özet (Türkçe, sade)

**Karar: GO (holdout açılabilir) — kod değişikliği gerekmiyor; aşağıdaki 5 "önce yaz, sonra koş" adımı şartıyla.**

- BLOCKER (engel): **0**. SHOULD-FIX (koşmadan önce yapılmalı, hepsi belge/prosedür, kod değil): **5**. NOTE (bilgi): **14**.
- Kod ön kayda (ON_KAYIT_V2) uyuyor. Mühürlü sayıları ham çıktılardan yeniden hesapladım: eleme kapıları, p-değerleri,
  BH (7 keşif), s = 0.5 birebir çıktı. Geliştirme aşamaları 2025-11-08 sonrasını hiç okumamış (kilit günlüğünde holdout
  gerekçeli tek okuma yok). İki stratejide ileriyi görme (lookahead) yok (kesilmiş veri testi: 0 fark).
- Holdout modülünü gerçek holdout verisine dokunmadan, geliştirme döneminin son yılını "sözde holdout" yaparak uçtan uca
  çalıştırdım: 28 saniyede hatasız bitti, işlemler ham çıktıyla birebir aynı. Yani koşu sırasında çökme riski düşük.
- Veri var: kripto 15m/1d 2026-11-06'ya, hisse/emtia 1d 2026-10-30'a kadar (35/35 enstrüman).

Koşmadan ÖNCE DURUM.md'ye yazılması gerekenler (sonuç görüldükten sonra yazılırsa değeri kalmaz):
1. **Hata kuralı:** holdout raporunda herhangi bir set stratejisinin `hatalar` sütunu boş değilse sonuç "hatalı koşu"
   sayılır ve kapı GEÇTİ kabul edilmez (kod bu durumda sessizce eksik enstrümanla devam ediyor).
2. **Açıklama:** `dis__gauss-stoch-eth` havuzda `kilit_gorulmus=hayir` görünüyor ama Katman 4 kilit testinde (2026-11-07)
   4h + ızgara ayarıyla 4 enstrümanda (ETH, SOL, META, NVDA) 2025-11-01 → 2026-11-05 döneminde koşulmuş; sonuçları
   `sonuclar/kilit/sonuc.csv`'de duruyor. Seçim bu sonuçlara bakmadı (mekanik), ama holdout raporunda yazılmalı.
3. **Dondurma:** koşu temiz çalışma kopyasında (commit 2eb73f1 ya da yalnız belge değiştiren torunu) yapılır; veri
   yenilenmez; `motor/arastirma/v2/` içine yeni .py dosyası EKLENMEZ (mühür bozulur); koşudan önce veri dosyalarının
   sha256 listesi kaydedilir; holdout günlüğü hemen commit edilir.
4. **Veri sonu notu:** rapor tek tarih yazıyor (2026-11-06); hisse/emtia 2026-10-30'da, kripto funding 2026-10-31'de bitiyor.
5. **Yorum notu:** "GEÇTİ" ne demek, önceden yazılsın: set kapısındaki p_set şartı pratikte çok kolay (özellikle 15m
   stratejide rastgele girişin beklenen sonucu maliyet yüzünden eksi; sıfır kâr bile "anlamlı" çıkıyor). Belirleyici
   şart fiilen "net > 0". Ayrıca evren 2026-11-07'de seçildi (ör. ZEC: gauss'un geliştirmedeki en iyi enstrümanı).
   Holdout geçerse bu "gerekli ama yeterli değil" bir kanıttır; asıl sınav paper.

Ek bilgi: geliştirme döneminin son yılında (2024-11 → 2025-11) ewo-ema-ofset tek başına hafif ekside (net −%0.6),
2025 yılı ΣR'si 3.9 (önceki yıllar 12–38). Holdout'ta budanma ihtimali yüksek; bu beklenen bir sonuçtur, hata değildir.

---

## 0. Scope, method, constraints honoured

- Read: `ON_KAYIT_V2.md`, all of `motor/arastirma/v2/*.py`, relevant v1 helpers (`secim.yeniden_oyna`, `secim.kumeler`,
  `evren_k2`, `wf_evren._veri/veri_ayarla/DONEMLER`, `wf_evren_holdout` seal helpers, `veri/depo`, `veri/yeniden_ornekle`,
  `veri/kilit`), the two sealed strategies, outputs in `sonuclar/evren/v2/`, `sonuclar/kilit_acilis.jsonl`, DURUM leader log.
- Not audited in depth: `araclar/havuz_v2_olustur.py` clustering (2.7) and labels (pool was sealed before any v2 run and
  cannot affect holdout validity); `v2_ek.py` / `sinif_ici.py` (none of them is in the set); `spa.py` (report only).
- Holdout NOT run. No call with donem "holdout". No price data ≥ 2025-11-08 read. The only contact with post-dev data
  is parquet footer min/max timestamp statistics (data-end check). All python checks ran with `we.veri_ayarla(None,
  "2017_gelistirme")` and `L3A_KILIT_LOG` redirected to the scratchpad; `git status` is clean after the audit.
- Disclosure: while grepping for strategy names I saw 4 rows of `sonuclar/kilit/sonuc.csv` (Katman 4 locked-period
  results of dis__gauss-stoch-eth 4h). This is pre-existing project output, not v2 holdout output; see S2.

## 1. Verdict

**GO**, conditional on the five pre-run documentation/procedure items (S1–S5). No code change is required, therefore
no re-seal and no re-run of earlier stages.

| class | count |
|---|---|
| BLOCKER | 0 |
| SHOULD-FIX | 5 |
| NOTE | 14 |

If the leader nevertheless wants a code change in `motor/arastirma/v2/` (e.g. to make S1 fail-closed in code): the only
legitimate path is delete `set_muhru.json` → change code → re-run `set` only → verify `set.csv` sha256 is still
`c753e66a…`, s = 0.5, `saglamlik.csv`/`test.csv`/`eleme.csv` hashes unchanged → commit. That is a bug-fix re-seal
(deterministic, no development result changes), not a post-result change. I do not recommend it: S1 can be closed by a
pre-declared rule at zero risk.

## 2. SHOULD-FIX (before the run; all cheap, none needs code)

**S1 — Holdout continues silently on partial universe.** `GercekSaglayici.tek_islemler` (holdout.py:198-216):
(a) a symbol whose data ends before HOLDOUT_BAS is skipped with no trace; (b) any per-symbol exception is appended to
`hatalar` and the symbol is dropped, yet the set gate is still evaluated and `paper_girdisi.json` can still be written.
v1 holdout marked such rows `hata`; ON_KAYIT_V2 0.5 says "hata = satır hata, sayılır". A dropped symbol can move the
result in either direction. Residual risk is low (dry run: 0 errors, 34/34 and 13/13 symbols; footer stats show all
35 instruments have data through the window), but the run is one-shot. Fix: pre-declare in DURUM.md before the run
"non-empty `hatalar` ⇒ result is flagged and the gate is NOT counted as passed" (fail-closed, conservative against a
false pass). No re-run of earlier stages.

**S2 — `kilit_gorulmus` is literally compliant but substantively wrong for a set member.** 2.9 was implemented as
"files with 'set' in the name under sonuclar/kilit + final_set.json + son1ay" → 10 rows flagged. But Katman 4
(2026-11-07, gerekçe "Katman 4 kilitli dönem testi") ran 322 rows / 130 strategies on 2025-11-01 → 2026-11-05, i.e.
on ~98% of the holdout window. `dis__gauss-stoch-eth` is among them (ETHUSDT, SOLUSDT, DK_META, DK_NVDA; 4h; WF grid
settings) with results in `sonuclar/kilit/{gruplar,secilen_ayarlar,sonuc}.csv`. `dis__ewo-ema-ofset` is not.
Effect on validity: none on the mechanical gate (v2 selection never read these files; kilit log confirms v2 stages read
only with the development gerekçe). Effect on honesty of the report: the holdout report will print `hayir`. The pool
file is hash-sealed and must not be edited. Fix: add the disclosure to DURUM.md now and to the v2 report text; the
weakness is in my own 2.9 wording.

**S3 — Seal does not cover everything the holdout executes; freeze by procedure.** Not hashed: `motor/arastirma/secim.py`
(replay engine), `evren_k2.py` (K2 core), `wf_tarama.py` (PF), `motor/veri/{depo,yeniden_ornekle,kilit}.py`,
`motor/strateji/funding.py`, `gostergeler*.py`, `cikislar.py`, `dis/_gosterge_d2.py` (gauss_kanal, stoch_rsi),
`_gosterge_d5.py` (cti), `_gosterge_d11i.py` (ewo), and the data files in `veri/mumlar/` (gitignored). The git check
only tests ancestry, not a clean tree. Today `git diff aab8590 HEAD` touches only DURUM.md and the three set files, so
the state is fine. Fix: run from a clean tree at 2eb73f1 (or a doc-only descendant); do not refresh data; store
`sha256sum veri/mumlar/*/*.parquet` and `git rev-parse HEAD` next to the holdout log; single foreground run
`python -m motor.arastirma.v2 holdout --holdout-bir-kez`; commit `holdout/` immediately.
Trap: `v2_modul_hashleri()` globs `motor/arastirma/v2/*.py`, so ADDING a file there (e.g. the missing `kardes.py` or a
report module) before the holdout makes the seal check fail (safe, but confusing). Any exception after the "basladi"
line burns the one shot — there is no retry path by design.

**S4 — "Data end" is not one date.** Footer statistics: crypto 5m → 2026-11-06 23:55 (13/13); DK_ 1h → 2026-10-30
(22/22; hisse 19:00, emtia 20:00 UTC); crypto funding → 2026-10-31 16:00. `veri_sonu()` reports max of 1d ends =
2026-11-06. Consequences: TradFi leg of the swing strategy has a window one week shorter; crypto trades open after
2026-10-31 carry no funding (verified the engine tolerates funding ending early; effect ≤ a few trades). Fix: write the
three dates in the report/DURUM. No code change.

**S5 — Pre-register how a PASS will be read.** (a) p_set is weak by construction for the 15m leg: random entries with
the same exits pay costs and lose. Measured on three development pseudo-years (2022/23/24-11-08 + 364 d, B = 2,000):
ewo null mean −8…−11 R, 95th percentile −2…−5 R, so T = 0 already gives p < 0.05; pooled set null 95th percentile
+3…+22 R versus realised T_set 37…94 R. In the 2024-11 pseudo-year ewo had K2 p = 0.001 with standalone net −0.56%.
The binding condition is effectively `net > 0`. The size claim "false pass ≤ 5% under no edge" holds only for the null
"entries exchangeable with random entries in the same quarter", not for "zero expected profit". (b) Universe membership
was fixed on 2026-11-07, after the window; the swing leg is long-only (591/591 accepted trades long), 76% of ΣR from
crypto, best instrument ZECUSDT (39.6 of 113.9 R), best year 2025. `net > 0` is exposed to this look-ahead; the K2 part
is not (conditioned on instrument/direction/quarter). Both are properties of the frozen design (mine), not bugs, and
0.3 forbids changing them. Fix: state this in DURUM.md before the run so the reading is not post hoc.

## 3. Spec fidelity (ON_KAYIT_V2) — result of line-by-line check

| Rule | Status |
|---|---|
| 1 constants, seed `crc32(f"{s}\|{tf}\|{asama}") ^ 20261109`, B1 500, B2 10k/10k/5k, q 0.10, boot 20/2000 | exact |
| 1.1 default setting only | exact (`varsayilan_strateji`: first kart setting else class default; both set members `varsayilan`) |
| 1.2 TradFi funding | exact in effect; applied post-trade in `ham.islem_hazirla` instead of inside `motor.py` (section 10 said motor); long-only, calendar time, not multiplied by ×2; verified DK_NVDA mean 0.046 R/trade |
| 1.3 p = (1+#{sim ≥ T})/(B+1) | exact; NaN sims count in B (conservative) |
| 2.4 primary tf | exact for set members (envanter `zaman_dilimi` empty → 1d, although the docstring says 4h) |
| 2.10 m = 939 | exact, read from pool seal |
| 3 MTM path | last value = trade R verified; ∏(1+daily) = replay cash for both members (1.48697, 1.87969) |
| E1–E5 | exact; recomputed independently for both members (below) |
| 5.1 K2 | exact: instrument, direction, stop/ATR14 multiple, own exits, calendar quarter UTC, pre-replay ΣR after overlap filter, cost ×1 |
| 5.3 two stages | exact: stage 2 only if p1 ≤ 0.02, fresh seed `k2b`, final p from stage-2 partial files only (recomputed) |
| 5.3 p = 1 rows | exact: 198 eliminated + 6 error + 1 unsupported-exit (ivanov, `kismi`) = 205 rows at p = 1 |
| 5.4 BH | exact: sort (p, "ad\|tf"), k* = 7 (p₍₇₎ = 0.0004 ≤ 0.000745; p₍₈₎ = 0.0034 > 0.000852) |
| S1–S4 | exact; bear day uses index(d−1) vs SMA200 ending d−1, 5-day ffill, entry-day assignment, < 20 ⇒ pass+flag |
| 6.2 clustering / order / greedy / label | exact (order p → ×2 PF(R) → alphabetical; ≤ 3 per style; one per cluster; one per label per style) |
| 6.2 s | exact; recomputed table identical; s = 0.5 (95th pct max DD 14.37%; s = 0.6 → 17.0%) |
| 6.3 seal contents | present: set, s, 5 file hashes, cost table hash, ON_KAYIT_V2 hash (13f17f53…), git commit, strategy + common + v2 module hashes, universe signature. Gaps → S3, N3 |
| 7 holdout | matches items 1–6 (details in section 5) |
| 9 sibling universe, CLI `havuz`/`rapor` | NOT implemented (N2) |

Coding agents' declared readings — judgement:

| Reading | Judgement |
|---|---|
| S2: < 2 valid neighbours = fail | Not a reading; it is the spec text. Extra: any neighbour run error ⇒ fail (conservative). Not binding (5–38 valid neighbours everywhere) |
| Unmeasurable correlation = separate cluster | Spec text; coded as ρ = 0 inside average linkage ("tends to separate"). Not binding (all pairs > 100 weeks) |
| Set window = max of analysis starts (2019-07-05) | Genuine reading, not obviously conservative (drops 2018-05 → 2019-07 of the swing leg). I recomputed with the earliest start: table 0.1429 @0.5, 0.1696 @0.6 → s = 0.5 either way. Harmless |
| Cluster exclusion applied across styles | Conservative; not binding |
| Portfolio arm additive; ×2 Sharpe for ordering | Not triggered (no portfolio discovery) |
| No funding in random-entry draws (TradFi or crypto) | Conservative for longs (real T pays funding, null does not; ETH 1d: 18.0 R → 13.5 R with funding). Both set members are long-only |
| Weekly series starts at first active day | Benign |
| Strategy-level holdout net = standalone single-account replay at s | Reasonable reading of 7.4 |

Timeline note: test/robustness/set/holdout code was committed at 22:24, after the elimination result (18 survivors,
21:58) existed. The readings above were therefore chosen knowing the survivors but not their p-values. None of them is
binding for the sealed set, so I attach no consequence.

## 4. Correctness checks performed

- **Leakage.** Development reads go through `we._veri` with `bit = 2025-11-08` (exclusive) plus `sizinti_kontrol` and
  the `veri_bit` check in `ham_yukle`. Latest entry in ham: 2025-11-06 (gauss), 2025-11-04 (ewo); the `cikis_zamani`
  of 2025-11-08 00:00 is the close stamp of the 11-07 bar, not holdout data. `kilit_acilis.jsonl`: 0 lines with the
  HOLDOUT gerekçe; no `holdout/` directory exists anywhere under `sonuclar/`.
- **Lookahead.** Truncation test (60/85/97% of history) on gauss (BTC, ZEC, DK_NVDA, DK_XAU 1d) and ewo (ETH, SOL 15m):
  0 differing cells in any signal column.
- **Costs.** Crypto funding is inside motor R; TradFi funding subtracted post-trade; cost table hash eb585319… in all
  stages.
- **Seeds / determinism / resumability.** Recomputed stage-2 draws for gauss BTCUSDT and DK_NVDA with the row seed:
  identical to stored partials. Partial files: 34 and 13 symbols, B matches. 6,814 side files per cost multiplier =
  13,628 tasks; no duplicated (symbol, entry) rows; `test.csv` has 222 unique rows.
- **Error rows.** 4 swing rows fail with "1d üst TF olarak kullanılamaz": the strategies need a higher timeframe than
  their base and rule 2.4 assigns 1d (source field empty). 2 portfolio rows: default needs symbols outside the universe.
  1 row: unsupported exit module. All handled as pre-registered (row counted in m, p = 1). Only power is lost.
  Re-running them at 4h now would be a post-result change — do not.
- **Sealed numbers recomputed from raw ham files.**

| | gauss-stoch-eth 1d | ewo-ema-ofset 15m |
|---|---|---|
| net ×1 / ×2 | 1.4870 / 1.3016 | 1.8797 / 1.3017 |
| PF(R) ×1, accepted | 2.0137 | 1.4616 |
| accepted / raw trades, instruments | 591 / 1208, 34 | 767 / 1055, 13 |
| ΣR; ex best instrument; ex best year | 113.9; 74.4 (ZEC); 70.3 (2025) | 109.0; 91.1 (SOL); 70.6 (2020) |
| class shares | kripto 76.1%, hisse 16.9%, emtia 6.9% | — |
| kill ×1 | 0 | 0 (24 daily-limit events, 122 forced closes) |
| T, final p (stage-2 only) | 227.71, 1/10001 (max sim 173.2) | 160.93, 1/5001 (max sim −47.1) |

All equal `eleme.csv` / `test.csv` / `saglamlik.csv`. E4 for gauss passes on kripto + hisse (16.9% vs 15% floor — thin).

## 5. Holdout module (section 7) review

- Seal → `muhur_kontrol` currently passes; mismatch in any of 5 files, cost table, ON_KAYIT_V2, common modules, v2
  modules, universe, strategy sources, set.csv vs seal, s ∉ grid ⇒ `HoldoutHatasi` before anything is read. Empty set ⇒
  refused.
- Once-only: "basladi" is appended before the provider is built; a second call raises `HoldoutTekrarHatasi`; no force
  flag; CLI needs `--holdout-bir-kez`; blocked under pytest; `GercekSaglayici` cannot be constructed outside the stage.
- Data: the only `veri_ayarla(None, "holdout")` in v2 is `GercekSaglayici.__init__`. That period is `bas=None, bit=None`,
  so warm-up history is loaded and there is no fallback to a development cut. Trades are filtered to entry ≥ 2025-11-08.
  A signal on the 11-07 close enters at the 11-08 open and is counted once (it could not fill in development).
- Gate: single account, cost ×1, risk s × 1%, other hard limits unchanged; `net > 0` and `p_set ≤ 0.05`, NaN fails;
  T_set = Σ pre-replay R after overlap filter; null = index-aligned sum of per-strategy draws, B = 5,000, seed `hset`,
  quarter clipped at HOLDOUT_BAS; portfolio rows excluded from p (none in the set). Evaluated on the unpruned set.
- Pruning only if the gate passed: net ≤ 0 or own K2 p (B = 2,000, seed `hk2`) > 0.25 or NaN ⇒ removed, no replacement.
  Gate failed ⇒ no `paper_girdisi.json`.
- Report: per strategy net, PF(R), trade count, K2 p, `kilit_gorulmus`, universe-membership note, data end.
- **Dry run of the real code path.** Subclassed `GercekSaglayici` without its `__init__`, kept the development data
  period, set `sabit.HOLDOUT_BAS = 2024-11-08` in-process and called `holdout._kos` with the real seal into a scratch
  directory: finished in 28 s, no symbol errors, provider trades identical to ham ×1 (181 and 92 trades, 0 differing
  symbols), report written. This exercises every line the real run will execute except the two lines that switch the
  data period. The 52 tests in `testler/test_v2_test_set_holdout.py` pass.

## 6. NOTES

- N1. Report's PF(R) and trade count are pre-replay (all signals), `net` is post-replay; they can disagree (dry run:
  ewo PF 1.17, net −0.56%). Label accordingly when presenting.
- N2. Section 9 (sibling universe) and the `rapor` stage do not exist yet. Report-only, development data only; can be
  done after the holdout, but see the glob trap in S3 if done before.
- N3. `ham` and `eleme` stages lack the post-seal write guard that test/saglamlik/set have (6.3). A stray re-run of
  `eleme` would change eleme.csv and trip the seal (safe failure); ham parquet files are not sealed but the holdout
  does not read them.
- N4. The one-shot guard is a log file inside the output directory; copying `sonuclar/evren/v2/` elsewhere and passing
  `--cikti` would permit a second run. Commit the log at once.
- N5. All 7 discoveries sit at the Monte-Carlo floor (1/10001, 1/5001). With B = 5,000 a 15m row cannot be a rank-1
  BH discovery (floor 2.0e-4 > 1.065e-4); here ranks 4–6, so no effect. Tie-break among floor p's is ×2 PF(R) as
  pre-registered.
- N6. K2 statistic uses all signals (gauss: 1,208) while the account accepts about half (591; 617 rejected by the 5%
  total-risk cap). Pre-registered ("before replay").
- N7. Near the data end the random-entry window shrinks to `[quarter start, n − hold)`; if empty, the draw collapses to
  one bar (v1 rule). Affects a handful of late trades, same as in development.
- N8. `yeniden_ornekle` session mode flags thin bars against the median sub-bar count of the loaded range; the median
  could in principle differ between development and full-history loads. Dry-run equality shows no effect on
  development bars.
- N9. ewo-ema-ofset buys 15m closes more than 4% below EMA8 (flash-crash bars). Fill realism was covered by P0-5; real
  slippage in such bars is a paper-stage risk, not a holdout-validity issue. ΣR by year: 2020 38.4, 2021–24 12–14,
  2025 3.9; last development year standalone net −0.56% at s = 0.5. Pruning in the holdout is a likely outcome.
- N10. gauss-stoch-eth pays material crypto funding (ETH: 25% of gross R). Included in results.
- N11. The earlier "2020→bugün" universe run (2026-11-07 18:06, 259 reads, ~4 min) read through the data end but left
  one parquet in `sonuclar/evren/ham/`; no results for the set members exist from it.
- N12. A failed/interrupted run after "basladi" has no recovery path. Runtime is under a minute; run in the foreground
  with no timeout or budget wrapper.
- N13. Pruning uses the standalone net of each strategy, the gate uses the joint account; a strategy can be pruned
  while the set passes (seen in the dry run). Intended.
- N14. Pool construction (2.3, 2.6, 2.7) was not re-derived in this audit.

## 7. Files

- This report: `/tmp/claude-0/-home-user/d9801314-f689-5b3c-ae41-5973e32ea499/scratchpad/fable_holdout_oncesi_denetim.md`
- Check scripts (same directory): `chk1.py` (gates, s, alternative window), `chk2.py` (p from partials, determinism,
  funding gap, MTM), `chk3.py` (funding in R), `la.py` (lookahead), `dry.py` / `dry2.py` (holdout dry run),
  `null.py` (pseudo-year null), dry-run output `dry_2024-11-08/holdout/`.
