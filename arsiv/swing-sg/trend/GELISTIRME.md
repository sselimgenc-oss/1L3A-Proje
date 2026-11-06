# Trend kollarının geliştirilmesi ve duyarlılık

| deney                                              | IS_CAGR   | IS_DD   |   IS_Sh | OOS_CAGR   | OOS_DD   |   OOS_Sh |
|:---------------------------------------------------|:----------|:--------|--------:|:-----------|:---------|---------:|
| BTC al-tut                                         | 64%       | -83%    |    1.04 | 53%        | -53%     |     1.15 |
| BTC T1 SMA30                                       | 55%       | -64%    |    1.21 | 21%        | -33%     |     0.83 |
| BTC T1 SMA40                                       | 70%       | -61%    |    1.37 | 35%        | -20%     |     1.18 |
| BTC T1 SMA50                                       | 66%       | -51%    |    1.3  | 33%        | -24%     |     1.12 |
| BTC T1 SMA70                                       | 61%       | -55%    |    1.21 | 29%        | -35%     |     1    |
| BTC T1 SMA100                                      | 64%       | -60%    |    1.21 | 22%        | -35%     |     0.78 |
| BTC T1 SMA50, 2x maliyet                           | 65%       | -53%    |    1.28 | 32%        | -25%     |     1.08 |
| Kripto T1 BTC+ETH, tavan %50                       | 38%       | -44%    |    1.06 | 21%        | -27%     |     0.87 |
| Kripto T1 BTC+ETH, tavan %100                      | 37%       | -54%    |    1    | 35%        | -28%     |     1.13 |
| Kripto T1 portföyü 25 coin, tavan %10, rejim=True  | 64%       | -28%    |    1.39 | 18%        | -51%     |     0.65 |
| Kripto T1 portföyü 25 coin, tavan %20, rejim=True  | 77%       | -34%    |    1.46 | 20%        | -54%     |     0.67 |
| Kripto T1 portföyü 25 coin, tavan %33, rejim=True  | 81%       | -36%    |    1.47 | 24%        | -52%     |     0.74 |
| Kripto T1 portföyü 25 coin, tavan %20, rejim=False | 67%       | -57%    |    1.2  | 23%        | -56%     |     0.68 |
| Kripto T1 ilk 10 coin, tavan %20                   | 92%       | -30%    |    1.53 | 27%        | -40%     |     0.87 |
| ABD eşit ağırlık al-tut                            | 18%       | -32%    |    0.96 | 24%        | -18%     |     1.7  |
| ABD trend 6 ay, rejim yok                          | 19%       | -31%    |    1.02 | 25%        | -19%     |     1.68 |
| ABD trend 6 ay, rejim EMA10/30                     | 12%       | -14%    |    1.05 | 17%        | -11%     |     1.48 |
| ABD trend 6 ay, rejim SMA200                       | 11%       | -20%    |    0.95 | 18%        | -11%     |     1.5  |
| ABD trend 9 ay, rejim yok                          | 17%       | -31%    |    0.98 | 21%        | -18%     |     1.47 |
| ABD trend 9 ay, rejim EMA10/30                     | 12%       | -13%    |    1.1  | 15%        | -9%      |     1.37 |
| ABD trend 9 ay, rejim SMA200                       | 10%       | -20%    |    0.89 | 16%        | -10%     |     1.36 |
| ABD trend 12 ay, rejim yok                         | 17%       | -31%    |    0.97 | 23%        | -17%     |     1.59 |
| ABD trend 12 ay, rejim EMA10/30                    | 12%       | -13%    |    1.1  | 17%        | -8%      |     1.53 |
| ABD trend 12 ay, rejim SMA200                      | 11%       | -20%    |    0.96 | 18%        | -9%      |     1.54 |
| ABD trend 12 ay, rejim EMA10/30, 2x maliyet        | 12%       | -13%    |    1.08 | 17%        | -8%      |     1.51 |
| ABD trend 12 ay, rejim EMA10/30, Mag7 HARİÇ        | 10%       | -12%    |    1    | 16%        | -7%      |     1.49 |
| Emtia vadeli eşit ağırlık al-tut (22)              | 9%        | -28%    |    0.67 | 10%        | -13%     |     0.81 |
| Emtia vadeli düşük vol 126g, en iyi %10            | 13%       | -18%    |    1.07 | 16%        | -10%     |     1.29 |
| Emtia vadeli düşük vol 126g, en iyi %20            | 12%       | -18%    |    0.97 | 13%        | -12%     |     1.05 |
| Emtia vadeli düşük vol 252g, en iyi %10            | 13%       | -18%    |    1.09 | 18%        | -15%     |     1.35 |
| Emtia vadeli düşük vol 252g, en iyi %20            | 14%       | -18%    |    1.13 | 16%        | -15%     |     1.2  |
| Emtia vadeli trend 12 ay (pozitifler)              | 4%        | -37%    |    0.32 | 19%        | -17%     |     1.12 |
| Emtia ETF eşit ağırlık al-tut (18)                 | 3%        | -41%    |    0.29 | 11%        | -16%     |     0.79 |
| Emtia ETF düşük vol 126g, en iyi %10               | 6%        | -18%    |    0.57 | 12%        | -14%     |     1.04 |
| Emtia ETF düşük vol 126g, en iyi %20               | 6%        | -19%    |    0.57 | 12%        | -12%     |     1.07 |
| Emtia ETF düşük vol 252g, en iyi %10               | 8%        | -17%    |    0.81 | 14%        | -9%      |     1.19 |
| Emtia ETF düşük vol 252g, en iyi %20               | 10%       | -17%    |    0.94 | 14%        | -9%      |     1.23 |
| Emtia ETF trend 12 ay (pozitifler)                 | 7%        | -30%    |    0.49 | 13%        | -18%     |     0.79 |
