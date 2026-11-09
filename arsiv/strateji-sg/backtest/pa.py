"""Price action kurulum dedektörleri — Galen Woods, "Price Action ile Günlük Trading Teknikleri" Cilt 3
(+ 51 Strateji Bölüm 7.3 pin bar, 7.7 iki bacaklı geri çekilme).

Her dedektör UZUN kurulumu arar; kısa kurulumlar fiyat ekseni ters çevrilerek aynı fonksiyonla bulunur
(o'=-o, h'=-l, l'=-h, c'=-c), böylece tanımlar birebir simetriktir.

Ortak kural (Galen 1.5): giriş kurulum mumunun tepesinin bir tık üstüne bekleyen alış emri, yalnız bir sonraki
mumda geçerli; stop kurulum mumunun dibinin bir tık altı. Dedektör i mumunun kapanışında kurulumu bildirir:
tetik = h[i] + tik, stop = l[i] - tik.

Tanımlar (uzun):
  trend çubuğu    : gövde > aralığın %50'si (Galen 4.2). Yükseliş mumu: c > o, düşüş mumu: c < o.
  TBF  Trend Çubuğu Arızası (4.2.1): A=i-1 ayı trend çubuğu; B=i, l[i] < l[i-1] ve B ayı trend çubuğu değil.
  CBF  Tıkanıklık Kırılım Arızası (2.2.4): en az 3 ardışık mum önceki mumun aralığında kapanır (tıkanıklık);
       i-1 düşüş kırılım mumu (c[i-1] < l[i-2]); i yükseliş mumu.
  DEC  Yavaşlama (5.2.2): 3 ardışık mum önceki dibin altına AZALAN mesafeyle iner; sınır = son mumun dibi.
       Sınır kırılmadıkça sonraki 'pencere' mum içindeki her yükseliş mumu kurulumdur.
  ANT  Doruğa Karşı (6.2.3): aynı, fakat ARTAN mesafeyle (aşırı satım).
  PZ   Basınç Bölgesi (7.2.2): 3 ardışık mumun alt gölgeleri en az pz_esik*ATR örtüşür; bölge = [en düşük dip,
       en düşük gövde altı]. Bölgeye değip bölge üstünde kapanan yükseliş mumu kurulumdur; bölge altı iptal.
  WPB  Zayıf Geri Çekilme (9.2.5): son 'wpb_n' mumdaki tepeden beri geri çekilmede 3+ ardışık düşüş mumu ve
       2+ ardışık ayı trend çubuğu yok; ilk bacak bitmiş (tepe yapan bir yükseliş) ve ikinci bacak başlamış
       (yeni dip); kurulum: düşüş mumunu izleyen yükseliş mumu.
  PIN  Pin bar (51 Str. 7.3): alt fitil >= 2 x gövde ve >= aralığın %60'ı, kapanış üst üçte birde,
       dip önceki mumun dibinin altında.
  H1/H2 Al Brooks Yüksek 1 / Yüksek 2 boğa bayrağı (Trends Bölüm 10, 20; "En iyi 10 model"): yeni tepeden sonra bir mumun
       tepesi önceki mumun tepesini aşamayınca geri çekilme başlar. Geri çekilmede önceki mumun tepesini aşan her mum bir
       "deneme"dir. Hk kurulumu: (k-1) deneme olmuş, geri çekilme tepesi aşılmamış ve i mumu GÜÇLÜ BOĞA SİNYAL MUMU
       (kapanış > açılış ve kapanış aralığın üst 'sinyal_kapanis' kısmında) -> i'nin tepesi üstüne alış stop emri;
       bir sonraki mum bu tepeyi aşarsa k. deneme = Hk girişi. Yeni tepe yapılınca sayım sıfırlanır.
"""
import numpy as np
from numba import njit

KURULUMLAR = ("TBF", "CBF", "DEC", "ANT", "PZ", "WPB", "PIN", "H1", "H2")


@njit(cache=True)
def _uzun(o, h, l, c, a, kod, pencere, pz_esik, wpb_n, cbf_n, sinyal_kapanis=0.6):
    n = len(c)
    out = np.zeros(n, np.bool_)
    rng = h - l
    bull = c > o
    bear = c < o
    btb = bull & ((c - o) > 0.5 * rng)
    stb = bear & ((o - c) > 0.5 * rng)
    if kod == 0:      # TBF
        for i in range(1, n):
            if stb[i - 1] and l[i] < l[i - 1] and not stb[i]:
                out[i] = True
    elif kod == 1:    # CBF
        kos = 0       # i-1'e kadar biten tıkanıklık serisi uzunluğu
        seri = np.zeros(n, np.int64)
        for k in range(1, n):
            if c[k] <= h[k - 1] and c[k] >= l[k - 1]:
                kos += 1
            else:
                kos = 0
            seri[k] = kos
        for i in range(3, n):
            if seri[i - 2] >= cbf_n and c[i - 1] < l[i - 2] and bull[i]:
                out[i] = True
    elif kod == 2 or kod == 3:   # DEC / ANT
        aktif = -1
        sinir = 0.0
        for i in range(3, n):
            x1 = l[i - 3] - l[i - 2]; x2 = l[i - 2] - l[i - 1]; x3 = l[i - 1] - l[i]
            desen = x1 > 0 and x2 > 0 and x3 > 0 and ((x1 > x2 and x2 > x3) if kod == 2 else (x1 < x2 and x2 < x3))
            if desen:
                aktif = i; sinir = l[i]
            if aktif >= 0:
                if i > aktif and l[i] < sinir:
                    aktif = -1
                elif i - aktif > pencere:
                    aktif = -1
                elif bull[i]:
                    out[i] = True
    elif kod == 4:    # PZ
        aktif = -1
        ust = 0.0; alt = 0.0
        for i in range(2, n):
            g_alt = min(min(o[i - 2], c[i - 2]), min(o[i - 1], c[i - 1]), min(o[i], c[i]))
            dip_ust = max(l[i - 2], l[i - 1], l[i])
            if g_alt - dip_ust >= pz_esik * a[i]:
                aktif = i; ust = g_alt; alt = min(l[i - 2], l[i - 1], l[i])
            if aktif >= 0:
                if l[i] < alt or i - aktif > pencere:
                    aktif = -1
                elif bull[i] and l[i] <= ust and c[i] > ust:
                    out[i] = True
    elif kod == 5:    # WPB
        for i in range(wpb_n + 2, n):
            k0 = i - wpb_n
            for m in range(i - wpb_n, i - 1):
                if h[m] >= h[k0]:
                    k0 = m
            if k0 >= i - 2 or h[i] >= h[k0]:
                continue
            zayif = True
            dus = 0; ayi_tb = 0
            bacak1_bitti = -1; bacak2 = -1
            for m in range(k0 + 1, i + 1):
                dus = dus + 1 if bear[m] else 0
                ayi_tb = ayi_tb + 1 if stb[m] else 0
                if dus >= 3 or ayi_tb >= 2:
                    zayif = False
                    break
                if bacak1_bitti < 0 and m > k0 + 1 and h[m] > h[m - 1]:
                    bacak1_bitti = m
                elif bacak1_bitti >= 0 and bacak2 < 0 and l[m] < l[m - 1]:
                    bacak2 = m
            if zayif and bacak2 >= 0 and bacak2 <= i - 1 and bull[i] and bear[i - 1]:
                out[i] = True
    elif kod == 7 or kod == 8:   # H1 / H2
        k_hedef = 1 if kod == 7 else 2
        gc = False; tepe = 0.0; deneme = 0
        for i in range(1, n):
            if gc:
                if h[i] > tepe:               # geri çekilme tepesi aşıldı -> trend devam, sayım sıfır
                    gc = False
                elif h[i] > h[i - 1]:
                    deneme += 1
            if not gc and h[i] <= h[i - 1]:
                gc = True; deneme = 0
                tepe = h[i - 1]
                for m in range(max(0, i - 10), i):
                    if h[m] > tepe:
                        tepe = h[m]
            if gc and deneme == k_hedef - 1 and h[i] <= h[i - 1] and bull[i] and rng[i] > 0 \
                    and (c[i] - l[i]) >= sinyal_kapanis * rng[i]:
                out[i] = True
    elif kod == 6:    # PIN
        for i in range(1, n):
            govde = abs(c[i] - o[i])
            alt_fitil = min(o[i], c[i]) - l[i]
            if rng[i] > 0 and alt_fitil >= 2 * govde and alt_fitil >= 0.6 * rng[i] \
                    and c[i] >= l[i] + 2.0 / 3.0 * rng[i] and l[i] < l[i - 1]:
                out[i] = True
    return out


def kurulum(o, h, l, c, a, ad, yon=1, pencere=5, pz_esik=0.1, wpb_n=20, tik_atr=0.02, cbf_n=3, sinyal_kapanis=0.6):
    """Bir coin dizisinde kurulumları bulur. Dönüş: (maske, tetik_seviyesi, stop_mesafesi[tetikten])."""
    kod = KURULUMLAR.index(ad)
    if yon > 0:
        m = _uzun(o, h, l, c, a, kod, pencere, pz_esik, wpb_n, cbf_n, sinyal_kapanis)
        tik = tik_atr * a
        tetik = h + tik
        stop_mes = (h - l) + 2 * tik
    else:   # ayna: kısa kurulum = ters çevrilmiş fiyatta uzun kurulum
        m = _uzun(-o, -l, -h, -c, a, kod, pencere, pz_esik, wpb_n, cbf_n, sinyal_kapanis)
        tik = tik_atr * a
        tetik = l - tik
        stop_mes = (h - l) + 2 * tik
    return m, tetik, stop_mes
