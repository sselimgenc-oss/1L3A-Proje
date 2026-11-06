# Trend / portföy stratejileri — test sonuçları

Ertesi açılışta işlem, sınıf maliyeti (BIST %0,15, kripto %0,10, diğer %0,05 tek yön), BIST ve XU endeksleri USD bazında, kaldıraç yok, yalnız long.

## 2015-22 (IS)

| grup   | varlik   | strateji                                         | toplam   | CAGR   | maxDD   |   Sharpe | piyasada   |   islem | KO   |
|:-------|:---------|:-------------------------------------------------|:---------|:-------|:--------|---------:|:-----------|--------:|:-----|
| tek    | BTC-USD  | al-tut                                           | 5141%    | 64%    | -83%    |     1.04 |            |         |      |
| tek    | BTC-USD  | 037 SMA50                                        | 5276%    | 65%    | -52%    |     1.28 | 42%        |      45 | 33%  |
| tek    | BTC-USD  | 007 12ay (düzeltilmiş)                           | 7013%    | 70%    | -73%    |     1.2  | 59%        |      14 | 64%  |
| tek    | BTC-USD  | 007 orijinal (52 gün)                            | 4939%    | 63%    | -72%    |     1.22 | 44%        |      46 | 43%  |
| tek    | BTC-USD  | T1 bizim (EMA10/30 + SMA50)                      | 5790%    | 66%    | -51%    |     1.3  | 41%        |      42 | 33%  |
| tek    | BTC-USD  | 037 SMA50 + vol %12 (orijinal)                   | 185%     | 14%    | -10%    |     1.49 | 42%        |      45 | 33%  |
| tek    | BTC-USD  | 037 SMA50 + vol %49 (IS'ten)                     | 2564%    | 51%    | -34%    |     1.4  | 42%        |      45 | 33%  |
| tek    | BTC-USD  | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 199%     | 15%    | -10%    |     1.49 | 41%        |      42 | 33%  |
| tek    | BTC-USD  | T1 bizim (EMA10/30 + SMA50) + vol %49 (IS'ten)   | 2493%    | 50%    | -35%    |     1.38 | 41%        |      42 | 33%  |
| tek    | ETH-USD  | al-tut                                           | 275%     | 29%    | -94%    |     0.76 |            |         |      |
| tek    | ETH-USD  | 037 SMA50                                        | 352%     | 34%    | -51%    |     0.83 | 31%        |      32 | 28%  |
| tek    | ETH-USD  | 007 12ay (düzeltilmiş)                           | 1007%    | 60%    | -57%    |     1.11 | 36%        |      11 | 55%  |
| tek    | ETH-USD  | 007 orijinal (52 gün)                            | 477%     | 41%    | -66%    |     0.9  | 30%        |      13 | 38%  |
| tek    | ETH-USD  | T1 bizim (EMA10/30 + SMA50)                      | 452%     | 39%    | -51%    |     0.93 | 27%        |      24 | 29%  |
| tek    | ETH-USD  | 037 SMA50 + vol %12 (orijinal)                   | 38%      | 6%     | -8%     |     0.88 | 31%        |      32 | 28%  |
| tek    | ETH-USD  | 037 SMA50 + vol %66 (IS'ten)                     | 285%     | 30%    | -40%    |     0.85 | 31%        |      32 | 28%  |
| tek    | ETH-USD  | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 39%      | 7%     | -8%     |     0.96 | 27%        |      24 | 33%  |
| tek    | ETH-USD  | T1 bizim (EMA10/30 + SMA50) + vol %66 (IS'ten)   | 319%     | 32%    | -37%    |     0.93 | 27%        |      24 | 33%  |
| tek    | XU100.IS | al-tut                                           | -17%     | -2%    | -68%    |     0.08 |            |         |      |
| tek    | XU100.IS | 037 SMA50                                        | 69%      | 7%     | -29%    |     0.57 | 26%        |      24 | 38%  |
| tek    | XU100.IS | 007 12ay (düzeltilmiş)                           | 15%      | 2%     | -43%    |     0.2  | 34%        |      16 | 50%  |
| tek    | XU100.IS | 007 orijinal (52 gün)                            | 39%      | 4%     | -42%    |     0.38 | 23%        |      16 | 56%  |
| tek    | XU100.IS | T1 bizim (EMA10/30 + SMA50)                      | 63%      | 6%     | -27%    |     0.6  | 22%        |      20 | 25%  |
| tek    | XU100.IS | 037 SMA50 + vol %12 (orijinal)                   | 21%      | 2%     | -17%    |     0.39 | 26%        |      24 | 38%  |
| tek    | XU100.IS | 037 SMA50 + vol %19 (IS'ten)                     | 29%      | 3%     | -26%    |     0.36 | 26%        |      24 | 38%  |
| tek    | XU100.IS | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 20%      | 2%     | -17%    |     0.42 | 22%        |      20 | 25%  |
| tek    | XU100.IS | T1 bizim (EMA10/30 + SMA50) + vol %19 (IS'ten)   | 27%      | 3%     | -25%    |     0.37 | 22%        |      20 | 25%  |
| tek    | XU030.IS | al-tut                                           | -27%     | -4%    | -71%    |     0.03 |            |         |      |
| tek    | XU030.IS | 037 SMA50                                        | 73%      | 7%     | -24%    |     0.59 | 26%        |      27 | 30%  |
| tek    | XU030.IS | 007 12ay (düzeltilmiş)                           | 11%      | 1%     | -43%    |     0.17 | 29%        |      18 | 44%  |
| tek    | XU030.IS | 007 orijinal (52 gün)                            | 39%      | 4%     | -27%    |     0.42 | 20%        |      18 | 50%  |
| tek    | XU030.IS | T1 bizim (EMA10/30 + SMA50)                      | 48%      | 5%     | -27%    |     0.48 | 22%        |      21 | 24%  |
| tek    | XU030.IS | 037 SMA50 + vol %12 (orijinal)                   | 23%      | 3%     | -13%    |     0.45 | 26%        |      27 | 30%  |
| tek    | XU030.IS | 037 SMA50 + vol %20 (IS'ten)                     | 34%      | 4%     | -20%    |     0.42 | 26%        |      27 | 30%  |
| tek    | XU030.IS | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 15%      | 2%     | -17%    |     0.35 | 22%        |      21 | 24%  |
| tek    | XU030.IS | T1 bizim (EMA10/30 + SMA50) + vol %20 (IS'ten)   | 20%      | 2%     | -26%    |     0.31 | 22%        |      21 | 24%  |
| tek    | ^GSPC    | al-tut                                           | 81%      | 8%     | -35%    |     0.49 |            |         |      |
| tek    | ^GSPC    | 037 SMA50                                        | 15%      | 2%     | -21%    |     0.24 | 55%        |      49 | 35%  |
| tek    | ^GSPC    | 007 12ay (düzeltilmiş)                           | 49%      | 5%     | -27%    |     0.46 | 68%        |      11 | 55%  |
| tek    | ^GSPC    | 007 orijinal (52 gün)                            | 65%      | 6%     | -10%    |     0.71 | 56%        |      30 | 57%  |
| tek    | ^GSPC    | T1 bizim (EMA10/30 + SMA50)                      | 14%      | 2%     | -17%    |     0.24 | 54%        |      50 | 34%  |
| tek    | ^GSPC    | 037 SMA50 + vol %12 (orijinal)                   | 10%      | 1%     | -18%    |     0.21 | 55%        |      49 | 35%  |
| tek    | ^GSPC    | 037 SMA50 + vol %10 (IS'ten)                     | 10%      | 1%     | -18%    |     0.21 | 55%        |      49 | 33%  |
| tek    | ^GSPC    | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 9%       | 1%     | -16%    |     0.19 | 54%        |      50 | 32%  |
| tek    | ^GSPC    | T1 bizim (EMA10/30 + SMA50) + vol %10 (IS'ten)   | 9%       | 1%     | -16%    |     0.19 | 54%        |      50 | 32%  |
| tek    | ^NDX     | al-tut                                           | 158%     | 13%    | -36%    |     0.63 |            |         |      |
| tek    | ^NDX     | 037 SMA50                                        | 69%      | 7%     | -17%    |     0.62 | 55%        |      46 | 30%  |
| tek    | ^NDX     | 007 12ay (düzeltilmiş)                           | 81%      | 8%     | -30%    |     0.5  | 71%        |      18 | 61%  |
| tek    | ^NDX     | 007 orijinal (52 gün)                            | 47%      | 5%     | -23%    |     0.43 | 58%        |      41 | 51%  |
| tek    | ^NDX     | T1 bizim (EMA10/30 + SMA50)                      | 55%      | 6%     | -17%    |     0.53 | 56%        |      47 | 30%  |
| tek    | ^NDX     | 037 SMA50 + vol %12 (orijinal)                   | 35%      | 4%     | -14%    |     0.5  | 55%        |      46 | 30%  |
| tek    | ^NDX     | 037 SMA50 + vol %14 (IS'ten)                     | 38%      | 4%     | -14%    |     0.51 | 55%        |      46 | 30%  |
| tek    | ^NDX     | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 31%      | 3%     | -14%    |     0.45 | 56%        |      47 | 28%  |
| tek    | ^NDX     | T1 bizim (EMA10/30 + SMA50) + vol %14 (IS'ten)   | 33%      | 4%     | -14%    |     0.45 | 56%        |      47 | 30%  |
| tek    | GC=F     | al-tut                                           | 55%      | 6%     | -21%    |     0.44 |            |         |      |
| tek    | GC=F     | 037 SMA50                                        | -7%      | -1%    | -26%    |    -0.03 | 36%        |      51 | 29%  |
| tek    | GC=F     | 007 12ay (düzeltilmiş)                           | 10%      | 1%     | -24%    |     0.16 | 54%        |      22 | 27%  |
| tek    | GC=F     | 007 orijinal (52 gün)                            | -1%      | -0%    | -23%    |     0.04 | 36%        |      36 | 33%  |
| tek    | GC=F     | T1 bizim (EMA10/30 + SMA50)                      | -1%      | -0%    | -26%    |     0.04 | 35%        |      46 | 33%  |
| tek    | GC=F     | 037 SMA50 + vol %12 (orijinal)                   | -4%      | -1%    | -21%    |    -0.03 | 36%        |      51 | 29%  |
| tek    | GC=F     | 037 SMA50 + vol %10 (IS'ten)                     | -2%      | -0%    | -18%    |    -0.01 | 36%        |      51 | 29%  |
| tek    | GC=F     | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | -0%      | -0%    | -21%    |     0.04 | 35%        |      46 | 33%  |
| tek    | GC=F     | T1 bizim (EMA10/30 + SMA50) + vol %10 (IS'ten)   | 1%       | 0%     | -18%    |     0.06 | 35%        |      46 | 33%  |
| bist   | evren    | eşit ağırlık al-tut                              | 134%     | 11%    | -54%    |     0.5  |            |         |      |
| bist   | evren    | 001 momentum                                     | 3015%    | 54%    | -55%    |     1.31 | 86%        |         |      |
| bist   | evren    | 001 momentum + rejim                             | 870%     | 33%    | -35%    |     1.39 | 28%        |         |      |
| bist   | evren    | 001 momentum + rejim + vol %16                   | 279%     | 18%    | -26%    |     1.21 | 28%        |         |      |
| bist   | evren    | 020 artık momentum                               | 891%     | 33%    | -43%    |     1.11 | 48%        |         |      |
| bist   | evren    | 020 artık momentum + rejim                       | 250%     | 17%    | -28%    |     0.92 | 16%        |         |      |
| bist   | evren    | 020 artık momentum + rejim + vol %19             | 119%     | 10%    | -20%    |     0.83 | 16%        |         |      |
| bist   | evren    | 007P trend portföyü                              | 145%     | 12%    | -73%    |     0.52 | 82%        |         |      |
| bist   | evren    | 007P trend portföyü + rejim                      | 97%      | 9%     | -34%    |     0.62 | 28%        |         |      |
| bist   | evren    | 007P trend portföyü + rejim + vol %12            | 39%      | 4%     | -31%    |     0.42 | 28%        |         |      |
| bist   | evren    | 012 düşük volatilite                             | 69%      | 7%     | -57%    |     0.37 | 87%        |         |      |
| bist   | evren    | 012 düşük volatilite + rejim                     | 37%      | 4%     | -51%    |     0.34 | 28%        |         |      |
| bist   | evren    | 012 düşük volatilite + rejim + vol %11           | 10%      | 1%     | -40%    |     0.17 | 28%        |         |      |
| abd    | evren    | eşit ağırlık al-tut                              | 276%     | 18%    | -32%    |     0.96 |            |         |      |
| abd    | evren    | 001 momentum                                     | 527%     | 26%    | -37%    |     0.95 | 87%        |         |      |
| abd    | evren    | 001 momentum + rejim                             | 245%     | 17%    | -26%    |     0.84 | 64%        |         |      |
| abd    | evren    | 001 momentum + rejim + vol %16                   | 168%     | 13%    | -18%    |     0.89 | 64%        |         |      |
| abd    | evren    | 020 artık momentum                               | 109%     | 10%    | -31%    |     0.58 | 49%        |         |      |
| abd    | evren    | 020 artık momentum + rejim                       | 35%      | 4%     | -25%    |     0.35 | 33%        |         |      |
| abd    | evren    | 020 artık momentum + rejim + vol %13             | 23%      | 3%     | -16%    |     0.33 | 33%        |         |      |
| abd    | evren    | 007P trend portföyü                              | 247%     | 17%    | -31%    |     0.97 | 87%        |         |      |
| abd    | evren    | 007P trend portföyü + rejim                      | 147%     | 12%    | -13%    |     1.1  | 64%        |         |      |
| abd    | evren    | 007P trend portföyü + rejim + vol %8             | 94%      | 9%     | -10%    |     1.08 | 64%        |         |      |
| abd    | evren    | 012 düşük volatilite                             | 93%      | 9%     | -23%    |     0.65 | 87%        |         |      |
| abd    | evren    | 012 düşük volatilite + rejim                     | 60%      | 6%     | -18%    |     0.72 | 64%        |         |      |
| abd    | evren    | 012 düşük volatilite + rejim + vol %7            | 47%      | 5%     | -13%    |     0.73 | 64%        |         |      |
| emtia  | evren    | eşit ağırlık al-tut                              | 103%     | 9%     | -28%    |     0.67 |            |         |      |
| emtia  | evren    | 001 momentum                                     | -40%     | -6%    | -62%    |    -0.11 | 87%        |         |      |
| emtia  | evren    | 001 momentum + rejim                             | -44%     | -7%    | -58%    |    -0.23 | 59%        |         |      |
| emtia  | evren    | 001 momentum + rejim + vol %14                   | -40%     | -6%    | -54%    |    -0.42 | 59%        |         |      |
| emtia  | evren    | 020 artık momentum                               | 73%      | 7%     | -32%    |     0.45 | 49%        |         |      |
| emtia  | evren    | 020 artık momentum + rejim                       | 26%      | 3%     | -38%    |     0.26 | 33%        |         |      |
| emtia  | evren    | 020 artık momentum + rejim + vol %17             | 45%      | 5%     | -19%    |     0.47 | 33%        |         |      |
| emtia  | evren    | 007P trend portföyü                              | 34%      | 4%     | -37%    |     0.32 | 87%        |         |      |
| emtia  | evren    | 007P trend portföyü + rejim                      | 33%      | 4%     | -34%    |     0.36 | 59%        |         |      |
| emtia  | evren    | 007P trend portföyü + rejim + vol %8             | 17%      | 2%     | -29%    |     0.29 | 59%        |         |      |
| emtia  | evren    | 012 düşük volatilite                             | 161%     | 13%    | -18%    |     1.09 | 87%        |         |      |
| emtia  | evren    | 012 düşük volatilite + rejim                     | 52%      | 5%     | -25%    |     0.59 | 59%        |         |      |
| emtia  | evren    | 012 düşük volatilite + rejim + vol %7            | 33%      | 4%     | -18%    |     0.58 | 59%        |         |      |
| emtia  | evren    | 089 değer (emtia)                                | 162%     | 13%    | -37%    |     0.85 | 37%        |         |      |
| emtia  | evren    | 089 değer (emtia) + rejim                        | 92%      | 9%     | -15%    |     0.95 | 26%        |         |      |
| emtia  | evren    | 089 değer (emtia) + rejim + vol %11              | 58%      | 6%     | -10%    |     0.89 | 26%        |         |      |

## 2023-26 (OOS)

| grup   | varlik   | strateji                                         | toplam   | CAGR   | maxDD   |   Sharpe | piyasada   |   islem | KO   |
|:-------|:---------|:-------------------------------------------------|:---------|:-------|:--------|---------:|:-----------|--------:|:-----|
| tek    | BTC-USD  | al-tut                                           | 402%     | 53%    | -53%    |     1.15 |            |         |      |
| tek    | BTC-USD  | 037 SMA50                                        | 173%     | 31%    | -27%    |     1.04 | 45%        |      32 | 25%  |
| tek    | BTC-USD  | 007 12ay (düzeltilmiş)                           | 228%     | 37%    | -32%    |     1.02 | 64%        |       1 | 100% |
| tek    | BTC-USD  | 007 orijinal (52 gün)                            | 107%     | 21%    | -43%    |     0.8  | 41%        |      26 | 27%  |
| tek    | BTC-USD  | T1 bizim (EMA10/30 + SMA50)                      | 197%     | 33%    | -24%    |     1.12 | 43%        |      27 | 30%  |
| tek    | BTC-USD  | 037 SMA50 + vol %12 (orijinal)                   | 37%      | 9%     | -8%     |     1.08 | 45%        |      32 | 28%  |
| tek    | BTC-USD  | 037 SMA50 + vol %49 (IS'ten)                     | 173%     | 31%    | -24%    |     1.08 | 45%        |      32 | 22%  |
| tek    | BTC-USD  | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 40%      | 9%     | -7%     |     1.15 | 43%        |      27 | 33%  |
| tek    | BTC-USD  | T1 bizim (EMA10/30 + SMA50) + vol %49 (IS'ten)   | 196%     | 33%    | -22%    |     1.16 | 43%        |      27 | 26%  |
| tek    | ETH-USD  | al-tut                                           | 109%     | 22%    | -68%    |     0.62 |            |         |      |
| tek    | ETH-USD  | 037 SMA50                                        | 20%      | 5%     | -41%    |     0.31 | 32%        |      24 | 17%  |
| tek    | ETH-USD  | 007 12ay (düzeltilmiş)                           | -16%     | -5%    | -65%    |     0.1  | 49%        |      12 | 25%  |
| tek    | ETH-USD  | 007 orijinal (52 gün)                            | 25%      | 6%     | -48%    |     0.34 | 34%        |      31 | 35%  |
| tek    | ETH-USD  | T1 bizim (EMA10/30 + SMA50)                      | 19%      | 5%     | -42%    |     0.31 | 28%        |      21 | 19%  |
| tek    | ETH-USD  | 037 SMA50 + vol %12 (orijinal)                   | 10%      | 2%     | -10%    |     0.37 | 32%        |      24 | 25%  |
| tek    | ETH-USD  | 037 SMA50 + vol %66 (IS'ten)                     | 24%      | 6%     | -40%    |     0.33 | 32%        |      24 | 17%  |
| tek    | ETH-USD  | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 8%       | 2%     | -9%     |     0.33 | 28%        |      21 | 33%  |
| tek    | ETH-USD  | T1 bizim (EMA10/30 + SMA50) + vol %66 (IS'ten)   | 23%      | 6%     | -41%    |     0.33 | 28%        |      21 | 19%  |
| tek    | XU100.IS | al-tut                                           | -15%     | -4%    | -32%    |    -0    |            |         |      |
| tek    | XU100.IS | 037 SMA50                                        | -18%     | -5%    | -29%    |    -0.26 | 34%        |      23 | 26%  |
| tek    | XU100.IS | 007 12ay (düzeltilmiş)                           | -30%     | -9%    | -35%    |    -0.26 | 64%        |      14 | 29%  |
| tek    | XU100.IS | 007 orijinal (52 gün)                            | -50%     | -17%   | -51%    |    -0.82 | 41%        |      26 | 31%  |
| tek    | XU100.IS | T1 bizim (EMA10/30 + SMA50)                      | -16%     | -5%    | -26%    |    -0.27 | 29%        |      21 | 24%  |
| tek    | XU100.IS | 037 SMA50 + vol %12 (orijinal)                   | -7%      | -2%    | -18%    |    -0.24 | 34%        |      23 | 26%  |
| tek    | XU100.IS | 037 SMA50 + vol %19 (IS'ten)                     | -16%     | -4%    | -27%    |    -0.33 | 34%        |      23 | 26%  |
| tek    | XU100.IS | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | -4%      | -1%    | -12%    |    -0.12 | 29%        |      21 | 24%  |
| tek    | XU100.IS | T1 bizim (EMA10/30 + SMA50) + vol %19 (IS'ten)   | -10%     | -3%    | -20%    |    -0.22 | 29%        |      21 | 24%  |
| tek    | XU030.IS | al-tut                                           | -3%      | -1%    | -32%    |     0.13 |            |         |      |
| tek    | XU030.IS | 037 SMA50                                        | -37%     | -11%   | -39%    |    -0.61 | 39%        |      34 | 24%  |
| tek    | XU030.IS | 007 12ay (düzeltilmiş)                           | -21%     | -6%    | -33%    |    -0.11 | 66%        |      10 | 30%  |
| tek    | XU030.IS | 007 orijinal (52 gün)                            | -34%     | -10%   | -37%    |    -0.44 | 41%        |      16 | 38%  |
| tek    | XU030.IS | T1 bizim (EMA10/30 + SMA50)                      | -35%     | -11%   | -37%    |    -0.63 | 33%        |      32 | 25%  |
| tek    | XU030.IS | 037 SMA50 + vol %12 (orijinal)                   | -17%     | -5%    | -19%    |    -0.58 | 39%        |      34 | 24%  |
| tek    | XU030.IS | 037 SMA50 + vol %20 (IS'ten)                     | -29%     | -9%    | -30%    |    -0.63 | 39%        |      34 | 24%  |
| tek    | XU030.IS | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | -14%     | -4%    | -15%    |    -0.52 | 33%        |      32 | 25%  |
| tek    | XU030.IS | T1 bizim (EMA10/30 + SMA50) + vol %20 (IS'ten)   | -24%     | -7%    | -25%    |    -0.57 | 33%        |      32 | 25%  |
| tek    | ^GSPC    | al-tut                                           | 103%     | 21%    | -19%    |     1.36 |            |         |      |
| tek    | ^GSPC    | 037 SMA50                                        | 49%      | 11%    | -9%     |     1.12 | 74%        |      28 | 43%  |
| tek    | ^GSPC    | 007 12ay (düzeltilmiş)                           | 72%      | 16%    | -23%    |     1.19 | 90%        |       2 | 100% |
| tek    | ^GSPC    | 007 orijinal (52 gün)                            | 56%      | 13%    | -8%     |     1.22 | 77%        |      17 | 53%  |
| tek    | ^GSPC    | T1 bizim (EMA10/30 + SMA50)                      | 40%      | 9%     | -9%     |     0.98 | 72%        |      28 | 43%  |
| tek    | ^GSPC    | 037 SMA50 + vol %12 (orijinal)                   | 37%      | 9%     | -9%     |     0.99 | 74%        |      28 | 39%  |
| tek    | ^GSPC    | 037 SMA50 + vol %10 (IS'ten)                     | 30%      | 7%     | -9%     |     0.92 | 74%        |      28 | 39%  |
| tek    | ^GSPC    | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 31%      | 7%     | -9%     |     0.87 | 72%        |      28 | 39%  |
| tek    | ^GSPC    | T1 bizim (EMA10/30 + SMA50) + vol %10 (IS'ten)   | 26%      | 6%     | -9%     |     0.81 | 72%        |      28 | 39%  |
| tek    | ^NDX     | al-tut                                           | 183%     | 32%    | -23%    |     1.48 |            |         |      |
| tek    | ^NDX     | 037 SMA50                                        | 64%      | 14%    | -12%    |     1    | 72%        |      37 | 32%  |
| tek    | ^NDX     | 007 12ay (düzeltilmiş)                           | 106%     | 21%    | -29%    |     1.16 | 90%        |       3 | 67%  |
| tek    | ^NDX     | 007 orijinal (52 gün)                            | 61%      | 14%    | -16%    |     0.95 | 69%        |      20 | 45%  |
| tek    | ^NDX     | T1 bizim (EMA10/30 + SMA50)                      | 54%      | 12%    | -12%    |     0.91 | 68%        |      35 | 31%  |
| tek    | ^NDX     | 037 SMA50 + vol %12 (orijinal)                   | 37%      | 9%     | -8%     |     0.93 | 72%        |      37 | 32%  |
| tek    | ^NDX     | 037 SMA50 + vol %14 (IS'ten)                     | 42%      | 10%    | -9%     |     0.93 | 72%        |      37 | 32%  |
| tek    | ^NDX     | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 34%      | 8%     | -9%     |     0.87 | 68%        |      35 | 31%  |
| tek    | ^NDX     | T1 bizim (EMA10/30 + SMA50) + vol %14 (IS'ten)   | 38%      | 9%     | -10%    |     0.87 | 68%        |      35 | 31%  |
| tek    | GC=F     | al-tut                                           | 131%     | 25%    | -25%    |     1.21 |            |         |      |
| tek    | GC=F     | 037 SMA50                                        | 85%      | 18%    | -12%    |     1.05 | 68%        |      26 | 27%  |
| tek    | GC=F     | 007 12ay (düzeltilmiş)                           | 107%     | 21%    | -25%    |     1.07 | 97%        |       3 | 33%  |
| tek    | GC=F     | 007 orijinal (52 gün)                            | 62%      | 14%    | -27%    |     0.81 | 74%        |      29 | 34%  |
| tek    | GC=F     | T1 bizim (EMA10/30 + SMA50)                      | 81%      | 17%    | -12%    |     1.03 | 66%        |      26 | 23%  |
| tek    | GC=F     | 037 SMA50 + vol %12 (orijinal)                   | 58%      | 13%    | -10%    |     1.13 | 68%        |      26 | 27%  |
| tek    | GC=F     | 037 SMA50 + vol %10 (IS'ten)                     | 48%      | 11%    | -8%     |     1.11 | 68%        |      26 | 27%  |
| tek    | GC=F     | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 53%      | 12%    | -10%    |     1.06 | 66%        |      26 | 23%  |
| tek    | GC=F     | T1 bizim (EMA10/30 + SMA50) + vol %10 (IS'ten)   | 44%      | 10%    | -10%    |     1.04 | 66%        |      26 | 23%  |
| bist   | evren    | eşit ağırlık al-tut                              | -10%     | -3%    | -33%    |     0.06 |            |         |      |
| bist   | evren    | 001 momentum                                     | 19%      | 5%     | -42%    |     0.31 | 100%       |         |      |
| bist   | evren    | 001 momentum + rejim                             | -11%     | -3%    | -37%    |     0.02 | 51%        |         |      |
| bist   | evren    | 001 momentum + rejim + vol %16                   | 15%      | 4%     | -21%    |     0.32 | 51%        |         |      |
| bist   | evren    | 020 artık momentum                               | -8%      | -2%    | -48%    |     0.12 | 100%       |         |      |
| bist   | evren    | 020 artık momentum + rejim                       | -12%     | -3%    | -35%    |     0.01 | 51%        |         |      |
| bist   | evren    | 020 artık momentum + rejim + vol %19             | 6%       | 2%     | -21%    |     0.18 | 51%        |         |      |
| bist   | evren    | 007P trend portföyü                              | 37%      | 9%     | -31%    |     0.42 | 100%       |         |      |
| bist   | evren    | 007P trend portföyü + rejim                      | -9%      | -3%    | -28%    |     0.01 | 51%        |         |      |
| bist   | evren    | 007P trend portföyü + rejim + vol %12            | 11%      | 3%     | -20%    |     0.29 | 51%        |         |      |
| bist   | evren    | 012 düşük volatilite                             | 33%      | 8%     | -33%    |     0.4  | 100%       |         |      |
| bist   | evren    | 012 düşük volatilite + rejim                     | 8%       | 2%     | -29%    |     0.2  | 51%        |         |      |
| bist   | evren    | 012 düşük volatilite + rejim + vol %11           | 12%      | 3%     | -21%    |     0.31 | 51%        |         |      |
| abd    | evren    | eşit ağırlık al-tut                              | 128%     | 24%    | -18%    |     1.7  |            |         |      |
| abd    | evren    | 001 momentum                                     | 328%     | 47%    | -28%    |     1.41 | 100%       |         |      |
| abd    | evren    | 001 momentum + rejim                             | 160%     | 29%    | -24%    |     1.05 | 85%        |         |      |
| abd    | evren    | 001 momentum + rejim + vol %16                   | 102%     | 21%    | -16%    |     1.18 | 85%        |         |      |
| abd    | evren    | 020 artık momentum                               | 168%     | 30%    | -22%    |     1.29 | 100%       |         |      |
| abd    | evren    | 020 artık momentum + rejim                       | 110%     | 22%    | -21%    |     1.09 | 85%        |         |      |
| abd    | evren    | 020 artık momentum + rejim + vol %13             | 75%      | 16%    | -12%    |     1.17 | 85%        |         |      |
| abd    | evren    | 007P trend portföyü                              | 118%     | 23%    | -17%    |     1.59 | 100%       |         |      |
| abd    | evren    | 007P trend portföyü + rejim                      | 81%      | 17%    | -8%     |     1.53 | 85%        |         |      |
| abd    | evren    | 007P trend portföyü + rejim + vol %8             | 57%      | 13%    | -7%     |     1.47 | 85%        |         |      |
| abd    | evren    | 012 düşük volatilite                             | 35%      | 8%     | -13%    |     0.7  | 100%       |         |      |
| abd    | evren    | 012 düşük volatilite + rejim                     | 41%      | 10%    | -10%    |     0.9  | 85%        |         |      |
| abd    | evren    | 012 düşük volatilite + rejim + vol %7            | 25%      | 6%     | -7%     |     0.83 | 85%        |         |      |
| emtia  | evren    | eşit ağırlık al-tut                              | 45%      | 10%    | -13%    |     0.81 |            |         |      |
| emtia  | evren    | 001 momentum                                     | 90%      | 19%    | -44%    |     0.68 | 100%       |         |      |
| emtia  | evren    | 001 momentum + rejim                             | 31%      | 8%     | -44%    |     0.39 | 63%        |         |      |
| emtia  | evren    | 001 momentum + rejim + vol %14                   | 31%      | 7%     | -15%    |     0.59 | 63%        |         |      |
| emtia  | evren    | 020 artık momentum                               | 80%      | 17%    | -33%    |     0.69 | 100%       |         |      |
| emtia  | evren    | 020 artık momentum + rejim                       | 8%       | 2%     | -34%    |     0.21 | 63%        |         |      |
| emtia  | evren    | 020 artık momentum + rejim + vol %17             | 14%      | 4%     | -17%    |     0.3  | 63%        |         |      |
| emtia  | evren    | 007P trend portföyü                              | 92%      | 19%    | -17%    |     1.12 | 100%       |         |      |
| emtia  | evren    | 007P trend portföyü + rejim                      | 40%      | 9%     | -17%    |     0.71 | 63%        |         |      |
| emtia  | evren    | 007P trend portföyü + rejim + vol %8             | 15%      | 4%     | -9%     |     0.5  | 63%        |         |      |
| emtia  | evren    | 012 düşük volatilite                             | 88%      | 18%    | -15%    |     1.35 | 100%       |         |      |
| emtia  | evren    | 012 düşük volatilite + rejim                     | 17%      | 4%     | -15%    |     0.44 | 63%        |         |      |
| emtia  | evren    | 012 düşük volatilite + rejim + vol %7            | 6%       | 2%     | -11%    |     0.26 | 63%        |         |      |
| emtia  | evren    | 089 değer (emtia)                                | 67%      | 15%    | -15%    |     0.93 | 100%       |         |      |
| emtia  | evren    | 089 değer (emtia) + rejim                        | 26%      | 6%     | -14%    |     0.57 | 63%        |         |      |
| emtia  | evren    | 089 değer (emtia) + rejim + vol %11              | 21%      | 5%     | -11%    |     0.54 | 63%        |         |      |

## 2020-26

| grup   | varlik   | strateji                                         | toplam   | CAGR   | maxDD   |   Sharpe | piyasada   |   islem | KO   |
|:-------|:---------|:-------------------------------------------------|:---------|:-------|:--------|---------:|:-----------|--------:|:-----|
| tek    | BTC-USD  | al-tut                                           | 1056%    | 44%    | -77%    |     0.91 |            |         |      |
| tek    | BTC-USD  | 037 SMA50                                        | 1069%    | 44%    | -35%    |     1.18 | 43%        |      49 | 27%  |
| tek    | BTC-USD  | 007 12ay (düzeltilmiş)                           | 1687%    | 53%    | -53%    |     1.18 | 59%        |      12 | 58%  |
| tek    | BTC-USD  | 007 orijinal (52 gün)                            | 1160%    | 45%    | -43%    |     1.19 | 42%        |      37 | 38%  |
| tek    | BTC-USD  | T1 bizim (EMA10/30 + SMA50)                      | 1171%    | 46%    | -34%    |     1.24 | 40%        |      41 | 27%  |
| tek    | BTC-USD  | 037 SMA50 + vol %12 (orijinal)                   | 92%      | 10%    | -8%     |     1.23 | 43%        |      49 | 29%  |
| tek    | BTC-USD  | 037 SMA50 + vol %49 (IS'ten)                     | 798%     | 38%    | -28%    |     1.22 | 43%        |      49 | 24%  |
| tek    | BTC-USD  | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 94%      | 10%    | -7%     |     1.27 | 40%        |      41 | 29%  |
| tek    | BTC-USD  | T1 bizim (EMA10/30 + SMA50) + vol %49 (IS'ten)   | 839%     | 39%    | -26%    |     1.27 | 40%        |      41 | 24%  |
| tek    | ETH-USD  | al-tut                                           | 1845%    | 55%    | -79%    |     0.95 |            |         |      |
| tek    | ETH-USD  | 037 SMA50                                        | 583%     | 33%    | -52%    |     0.82 | 38%        |      50 | 24%  |
| tek    | ETH-USD  | 007 12ay (düzeltilmiş)                           | 1042%    | 43%    | -65%    |     0.91 | 54%        |      22 | 41%  |
| tek    | ETH-USD  | 007 orijinal (52 gün)                            | 705%     | 36%    | -66%    |     0.84 | 42%        |      43 | 37%  |
| tek    | ETH-USD  | T1 bizim (EMA10/30 + SMA50)                      | 570%     | 32%    | -51%    |     0.83 | 34%        |      44 | 25%  |
| tek    | ETH-USD  | 037 SMA50 + vol %12 (orijinal)                   | 57%      | 7%     | -12%    |     0.85 | 38%        |      50 | 28%  |
| tek    | ETH-USD  | 037 SMA50 + vol %66 (IS'ten)                     | 488%     | 30%    | -47%    |     0.84 | 38%        |      50 | 24%  |
| tek    | ETH-USD  | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 49%      | 6%     | -10%    |     0.81 | 34%        |      44 | 32%  |
| tek    | ETH-USD  | T1 bizim (EMA10/30 + SMA50) + vol %66 (IS'ten)   | 410%     | 27%    | -41%    |     0.81 | 34%        |      44 | 25%  |
| tek    | XU100.IS | al-tut                                           | 31%      | 4%     | -45%    |     0.29 |            |         |      |
| tek    | XU100.IS | 037 SMA50                                        | 39%      | 5%     | -29%    |     0.39 | 34%        |      30 | 30%  |
| tek    | XU100.IS | 007 12ay (düzeltilmiş)                           | -21%     | -3%    | -43%    |    -0.04 | 55%        |      24 | 42%  |
| tek    | XU100.IS | 007 orijinal (52 gün)                            | -39%     | -7%    | -51%    |    -0.28 | 36%        |      33 | 36%  |
| tek    | XU100.IS | T1 bizim (EMA10/30 + SMA50)                      | 37%      | 5%     | -27%    |     0.4  | 29%        |      27 | 30%  |
| tek    | XU100.IS | 037 SMA50 + vol %12 (orijinal)                   | 8%       | 1%     | -18%    |     0.19 | 34%        |      30 | 27%  |
| tek    | XU100.IS | 037 SMA50 + vol %19 (IS'ten)                     | 7%       | 1%     | -27%    |     0.15 | 34%        |      30 | 27%  |
| tek    | XU100.IS | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 11%      | 2%     | -15%    |     0.26 | 29%        |      27 | 26%  |
| tek    | XU100.IS | T1 bizim (EMA10/30 + SMA50) + vol %19 (IS'ten)   | 13%      | 2%     | -23%    |     0.22 | 29%        |      27 | 26%  |
| tek    | XU030.IS | al-tut                                           | 33%      | 4%     | -46%    |     0.3  |            |         |      |
| tek    | XU030.IS | 037 SMA50                                        | 10%      | 1%     | -39%    |     0.17 | 35%        |      43 | 26%  |
| tek    | XU030.IS | 007 12ay (düzeltilmiş)                           | -11%     | -2%    | -39%    |     0.05 | 51%        |      20 | 40%  |
| tek    | XU030.IS | 007 orijinal (52 gün)                            | -9%      | -1%    | -37%    |     0.02 | 34%        |      20 | 40%  |
| tek    | XU030.IS | T1 bizim (EMA10/30 + SMA50)                      | -1%      | -0%    | -37%    |     0.07 | 30%        |      39 | 28%  |
| tek    | XU030.IS | 037 SMA50 + vol %12 (orijinal)                   | -3%      | -0%    | -19%    |    -0.01 | 35%        |      43 | 23%  |
| tek    | XU030.IS | 037 SMA50 + vol %20 (IS'ten)                     | -7%      | -1%    | -30%    |    -0.03 | 35%        |      43 | 26%  |
| tek    | XU030.IS | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | -3%      | -0%    | -15%    |    -0.04 | 30%        |      39 | 26%  |
| tek    | XU030.IS | T1 bizim (EMA10/30 + SMA50) + vol %20 (IS'ten)   | -8%      | -1%    | -25%    |    -0.06 | 30%        |      39 | 28%  |
| tek    | ^GSPC    | al-tut                                           | 136%     | 13%    | -35%    |     0.73 |            |         |      |
| tek    | ^GSPC    | 037 SMA50                                        | 67%      | 8%     | -12%    |     0.79 | 65%        |      47 | 40%  |
| tek    | ^GSPC    | 007 12ay (düzeltilmiş)                           | 89%      | 10%    | -27%    |     0.72 | 82%        |       7 | 57%  |
| tek    | ^GSPC    | 007 orijinal (52 gün)                            | 105%     | 11%    | -10%    |     1.02 | 69%        |      24 | 50%  |
| tek    | ^GSPC    | T1 bizim (EMA10/30 + SMA50)                      | 57%      | 7%     | -17%    |     0.73 | 63%        |      46 | 41%  |
| tek    | ^GSPC    | 037 SMA50 + vol %12 (orijinal)                   | 46%      | 6%     | -10%    |     0.71 | 65%        |      47 | 38%  |
| tek    | ^GSPC    | 037 SMA50 + vol %10 (IS'ten)                     | 39%      | 5%     | -9%     |     0.67 | 65%        |      47 | 38%  |
| tek    | ^GSPC    | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 40%      | 5%     | -14%    |     0.64 | 63%        |      46 | 39%  |
| tek    | ^GSPC    | T1 bizim (EMA10/30 + SMA50) + vol %10 (IS'ten)   | 34%      | 4%     | -12%    |     0.6  | 63%        |      46 | 39%  |
| tek    | ^NDX     | al-tut                                           | 251%     | 20%    | -36%    |     0.87 |            |         |      |
| tek    | ^NDX     | 037 SMA50                                        | 123%     | 13%    | -17%    |     0.89 | 64%        |      54 | 31%  |
| tek    | ^NDX     | 007 12ay (düzeltilmiş)                           | 163%     | 15%    | -30%    |     0.79 | 83%        |       9 | 67%  |
| tek    | ^NDX     | 007 orijinal (52 gün)                            | 72%      | 8%     | -23%    |     0.59 | 65%        |      37 | 43%  |
| tek    | ^NDX     | T1 bizim (EMA10/30 + SMA50)                      | 100%     | 11%    | -17%    |     0.8  | 61%        |      52 | 31%  |
| tek    | ^NDX     | 037 SMA50 + vol %12 (orijinal)                   | 55%      | 7%     | -10%    |     0.75 | 64%        |      54 | 31%  |
| tek    | ^NDX     | 037 SMA50 + vol %14 (IS'ten)                     | 62%      | 7%     | -11%    |     0.75 | 64%        |      54 | 31%  |
| tek    | ^NDX     | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 50%      | 6%     | -9%     |     0.7  | 61%        |      52 | 31%  |
| tek    | ^NDX     | T1 bizim (EMA10/30 + SMA50) + vol %14 (IS'ten)   | 56%      | 7%     | -10%    |     0.7  | 61%        |      52 | 31%  |
| tek    | GC=F     | al-tut                                           | 178%     | 16%    | -25%    |     0.89 |            |         |      |
| tek    | GC=F     | 037 SMA50                                        | 78%      | 9%     | -26%    |     0.64 | 56%        |      44 | 27%  |
| tek    | GC=F     | 007 12ay (düzeltilmiş)                           | 116%     | 12%    | -31%    |     0.72 | 81%        |      13 | 31%  |
| tek    | GC=F     | 007 orijinal (52 gün)                            | 45%      | 6%     | -29%    |     0.43 | 60%        |      43 | 28%  |
| tek    | GC=F     | T1 bizim (EMA10/30 + SMA50)                      | 80%      | 9%     | -26%    |     0.66 | 53%        |      39 | 28%  |
| tek    | GC=F     | 037 SMA50 + vol %12 (orijinal)                   | 56%      | 7%     | -21%    |     0.68 | 56%        |      44 | 27%  |
| tek    | GC=F     | 037 SMA50 + vol %10 (IS'ten)                     | 48%      | 6%     | -18%    |     0.68 | 56%        |      44 | 27%  |
| tek    | GC=F     | T1 bizim (EMA10/30 + SMA50) + vol %12 (orijinal) | 53%      | 6%     | -21%    |     0.66 | 53%        |      39 | 28%  |
| tek    | GC=F     | T1 bizim (EMA10/30 + SMA50) + vol %10 (IS'ten)   | 45%      | 6%     | -18%    |     0.65 | 53%        |      39 | 28%  |
| bist   | evren    | eşit ağırlık al-tut                              | 123%     | 13%    | -37%    |     0.52 |            |         |      |
| bist   | evren    | 001 momentum                                     | 829%     | 39%    | -46%    |     0.99 | 100%       |         |      |
| bist   | evren    | 001 momentum + rejim                             | 233%     | 19%    | -42%    |     0.76 | 43%        |         |      |
| bist   | evren    | 001 momentum + rejim + vol %16                   | 129%     | 13%    | -26%    |     0.84 | 43%        |         |      |
| bist   | evren    | 020 artık momentum                               | 535%     | 31%    | -48%    |     0.88 | 100%       |         |      |
| bist   | evren    | 020 artık momentum + rejim                       | 203%     | 18%    | -40%    |     0.73 | 43%        |         |      |
| bist   | evren    | 020 artık momentum + rejim + vol %19             | 143%     | 14%    | -21%    |     0.83 | 43%        |         |      |
| bist   | evren    | 007P trend portföyü                              | 300%     | 23%    | -43%    |     0.77 | 100%       |         |      |
| bist   | evren    | 007P trend portföyü + rejim                      | 59%      | 7%     | -34%    |     0.42 | 43%        |         |      |
| bist   | evren    | 007P trend portföyü + rejim + vol %12            | 41%      | 5%     | -27%    |     0.46 | 43%        |         |      |
| bist   | evren    | 012 düşük volatilite                             | 101%     | 11%    | -53%    |     0.48 | 100%       |         |      |
| bist   | evren    | 012 düşük volatilite + rejim                     | 47%      | 6%     | -35%    |     0.37 | 43%        |         |      |
| bist   | evren    | 012 düşük volatilite + rejim + vol %11           | 21%      | 3%     | -27%    |     0.3  | 43%        |         |      |
| abd    | evren    | eşit ağırlık al-tut                              | 237%     | 20%    | -32%    |     1.02 |            |         |      |
| abd    | evren    | 001 momentum                                     | 788%     | 38%    | -37%    |     1.14 | 100%       |         |      |
| abd    | evren    | 001 momentum + rejim                             | 288%     | 22%    | -31%    |     0.88 | 74%        |         |      |
| abd    | evren    | 001 momentum + rejim + vol %16                   | 175%     | 16%    | -24%    |     0.97 | 74%        |         |      |
| abd    | evren    | 020 artık momentum                               | 364%     | 25%    | -31%    |     1.01 | 100%       |         |      |
| abd    | evren    | 020 artık momentum + rejim                       | 168%     | 16%    | -28%    |     0.83 | 74%        |         |      |
| abd    | evren    | 020 artık momentum + rejim + vol %13             | 101%     | 11%    | -19%    |     0.85 | 74%        |         |      |
| abd    | evren    | 007P trend portföyü                              | 242%     | 20%    | -31%    |     1.05 | 100%       |         |      |
| abd    | evren    | 007P trend portföyü + rejim                      | 162%     | 15%    | -17%    |     1.29 | 74%        |         |      |
| abd    | evren    | 007P trend portföyü + rejim + vol %8             | 98%      | 11%    | -13%    |     1.25 | 74%        |         |      |
| abd    | evren    | 012 düşük volatilite                             | 65%      | 8%     | -23%    |     0.55 | 100%       |         |      |
| abd    | evren    | 012 düşük volatilite + rejim                     | 82%      | 9%     | -10%    |     0.92 | 74%        |         |      |
| abd    | evren    | 012 düşük volatilite + rejim + vol %7            | 51%      | 6%     | -9%     |     0.85 | 74%        |         |      |
| emtia  | evren    | eşit ağırlık al-tut                              | 148%     | 14%    | -28%    |     0.92 |            |         |      |
| emtia  | evren    | 001 momentum                                     | 97%      | 11%    | -56%    |     0.47 | 100%       |         |      |
| emtia  | evren    | 001 momentum + rejim                             | 36%      | 5%     | -48%    |     0.3  | 67%        |         |      |
| emtia  | evren    | 001 momentum + rejim + vol %14                   | 36%      | 5%     | -25%    |     0.39 | 67%        |         |      |
| emtia  | evren    | 020 artık momentum                               | 177%     | 16%    | -42%    |     0.66 | 100%       |         |      |
| emtia  | evren    | 020 artık momentum + rejim                       | 43%      | 5%     | -49%    |     0.34 | 67%        |         |      |
| emtia  | evren    | 020 artık momentum + rejim + vol %17             | 74%      | 9%     | -32%    |     0.58 | 67%        |         |      |
| emtia  | evren    | 007P trend portföyü                              | 170%     | 16%    | -30%    |     0.91 | 100%       |         |      |
| emtia  | evren    | 007P trend portföyü + rejim                      | 120%     | 12%    | -28%    |     0.87 | 67%        |         |      |
| emtia  | evren    | 007P trend portföyü + rejim + vol %8             | 51%      | 6%     | -17%    |     0.78 | 67%        |         |      |
| emtia  | evren    | 012 düşük volatilite                             | 276%     | 22%    | -15%    |     1.54 | 100%       |         |      |
| emtia  | evren    | 012 düşük volatilite + rejim                     | 101%     | 11%    | -21%    |     0.96 | 67%        |         |      |
| emtia  | evren    | 012 düşük volatilite + rejim + vol %7            | 51%      | 6%     | -15%    |     0.9  | 67%        |         |      |
| emtia  | evren    | 089 değer (emtia)                                | 337%     | 24%    | -37%    |     1.15 | 99%        |         |      |
| emtia  | evren    | 089 değer (emtia) + rejim                        | 141%     | 14%    | -21%    |     1.05 | 66%        |         |      |
| emtia  | evren    | 089 değer (emtia) + rejim + vol %11              | 90%      | 10%    | -15%    |     0.96 | 66%        |         |      |

