"""D10-d yardımcı göstergeler. Hepsi nedensel: t. satır yalnız t. mum kapanışına kadar olan veriyi kullanır;
fraktal pivotlar `k` mum SONRA onaylanır (onay anında bilinir)."""
import numpy as np
import pandas as pd


def _pivot_onay(yuksek: np.ndarray, dusuk: np.ndarray, i: int, k: int):
    """i. mumda onaylanan pivotlar (j = i-k): (tepe_mi, dip_mi). Pivot: j'nin ±k komşusundan kesin uç (eşitlikte sayılmaz)."""
    j = i - k
    if j < k:
        return False, False
    bh = yuksek[j - k:i + 1]
    bl = dusuk[j - k:i + 1]
    tepe = bool(yuksek[j] == bh.max() and (bh == yuksek[j]).sum() == 1)
    dip = bool(dusuk[j] == bl.min() and (bl == dusuk[j]).sum() == 1)
    return tepe, dip


def diverjans_durumu(yuksek, dusuk, mom, k=3, min_aralik=6, max_aralik=60, gecerlilik=30, tepe_modu=False) -> pd.DataFrame:
    """Momentum ıraksaması (Bernstein): boğa: son iki onaylı fiyat dibi C (eski) ve A (yeni); A < C (fiyat yeni dip) fakat
    momentum(A) > momentum(C) (momentum yeni dip yapmadı); aralık min_aralik..max_aralik mum; E = C ile A arasındaki momentum
    ZİRVESİ. A'dan sonra fiyat A'nın altına inerse veya A onayından `gecerlilik` mum geçerse geçersiz.
    tepe_modu=True: ayna (tepeler, E = aradaki momentum DİBİ).
    Dönen sütunlar: aktif (bool), a_fiyat, e_seviye, c_fiyat."""
    h, l, m = (np.asarray(x, dtype=float) for x in (yuksek, dusuk, mom))
    n = len(h)
    aktif = np.zeros(n, dtype=bool)
    a_f = np.full(n, np.nan)
    e_s = np.full(n, np.nan)
    c_f = np.full(n, np.nan)
    pivotlar = []        # (indeks, fiyat, momentum)
    cur = None           # (a_idx, a_fiyat, e, c_fiyat, onay_idx)
    fiyat = h if tepe_modu else l
    for i in range(n):
        tp, dp = _pivot_onay(h, l, i, k)
        if (tp if tepe_modu else dp):
            j = i - k
            pivotlar.append((j, fiyat[j], m[j]))
            pivotlar = pivotlar[-6:]
            if len(pivotlar) >= 2:
                (cj, cf, cm), (aj, af, am) = pivotlar[-2], pivotlar[-1]
                fiyat_ok = af > cf if tepe_modu else af < cf
                mom_ok = am < cm if tepe_modu else am > cm
                if fiyat_ok and mom_ok and min_aralik <= aj - cj <= max_aralik and np.isfinite(am) and np.isfinite(cm):
                    ara = m[cj:aj + 1]
                    e = np.nanmin(ara) if tepe_modu else np.nanmax(ara)
                    cur = (aj, af, e, cf, i)
                else:
                    cur = None
        if cur is not None:
            bozuldu = (h[i] > cur[1]) if tepe_modu else (l[i] < cur[1])
            # A'nın kendisi onay mumuna kadar görüldü; A sonrası yeni uç bozar (A mumunun kendisi hariç)
            if i > cur[0] and bozuldu or i - cur[4] > gecerlilik:
                cur = None
        if cur is not None:
            aktif[i] = True
            a_f[i], e_s[i], c_f[i] = cur[1], cur[2], cur[3]
    return pd.DataFrame({"aktif": aktif, "a_fiyat": a_f, "e_seviye": e_s, "c_fiyat": c_f}, index=pd.RangeIndex(n))


def kama_durumu(yuksek, dusuk, k=2, gecerlilik=12, tepe_modu=False) -> pd.DataFrame:
    """Brooks kaması (3 itme). Boğa dönüşü (kama dibi): ardışık 3 onaylı pivot dip L1 > L2 > L3 ve aralarındaki pivot tepeler
    Ha (L1-L2 arası) > Hb (L2-L3 arası) (alçalan tepeler = yakınsayan kama). L3 onayından `gecerlilik` mum boyunca ve L3 kırılmadıkça
    aktif. tepe_modu=True: ayna (kama tepesi, short).
    Dönen: aktif, uc_fiyat (L3 / ayna: tepe), baslangic (L1 değerinden önceki ilk karşı pivot Ha = kama başlangıcı)."""
    h, l = np.asarray(yuksek, dtype=float), np.asarray(dusuk, dtype=float)
    n = len(h)
    aktif = np.zeros(n, dtype=bool)
    uc = np.full(n, np.nan)
    bas = np.full(n, np.nan)
    ana = []     # ana yön pivotları: (idx, fiyat) — boğa dönüşünde dipler
    kars = []    # karşı yön pivotları
    cur = None   # (uc_idx, uc_fiyat, baslangic, onay_idx)
    for i in range(n):
        tp, dp = _pivot_onay(h, l, i, k)
        j = i - k
        if dp or tp:
            ana_mi = tp if tepe_modu else dp
            kars_mi = dp if tepe_modu else tp
            if ana_mi:
                ana.append((j, h[j] if tepe_modu else l[j]))
                ana = ana[-6:]
            if kars_mi:
                kars.append((j, l[j] if tepe_modu else h[j]))
                kars = kars[-6:]
            if ana_mi and len(ana) >= 3:
                (j1, v1), (j2, v2), (j3, v3) = ana[-3:]
                itme_ok = (v1 < v2 < v3) if tepe_modu else (v1 > v2 > v3)
                ha = [v for (jj, v) in kars if j1 < jj < j2]
                hb = [v for (jj, v) in kars if j2 < jj < j3]
                if itme_ok and ha and hb:
                    ha_v = (min(ha) if tepe_modu else max(ha))
                    hb_v = (min(hb) if tepe_modu else max(hb))
                    yakinsa = (ha_v < hb_v) if tepe_modu else (ha_v > hb_v)
                    cur = (j3, v3, ha_v, i) if yakinsa else None
                else:
                    cur = None
        if cur is not None:
            bozuldu = (h[i] > cur[1]) if tepe_modu else (l[i] < cur[1])
            if (i > cur[0] and bozuldu) or i - cur[3] > gecerlilik:
                cur = None
        if cur is not None:
            aktif[i] = True
            uc[i], bas[i] = cur[1], cur[2]
    return pd.DataFrame({"aktif": aktif, "uc_fiyat": uc, "baslangic": bas}, index=pd.RangeIndex(n))


def abcd_c_durumu(yuksek, dusuk, atr, k=3, ab_atr=3.0, geri_min=0.382, geri_max=0.786, tepe_modu=False) -> pd.DataFrame:
    """ABCD: boğa: A (onaylı pivot dip) -> B (pivot tepe) -> C (pivot dip, C > A, geri çekilme oranı (B-C)/(B-A) geri_min..geri_max,
    AB >= ab_atr x ATR(B anı)). SİNYAL yalnız C'nin onaylandığı mumda (i = C + k) üretilir (`yeni`=True).
    Dönen: yeni, a, b, c (fiyatlar), d (AB=CD hedefi: C + (B-A)). tepe_modu=True ayna (ters ABCD)."""
    h, l, at = (np.asarray(x, dtype=float) for x in (yuksek, dusuk, atr))
    n = len(h)
    yeni = np.zeros(n, dtype=bool)
    A = np.full(n, np.nan)
    B = np.full(n, np.nan)
    C = np.full(n, np.nan)
    D = np.full(n, np.nan)
    ph = []   # tüm pivotlar (idx, tür, fiyat); tür +1 tepe, -1 dip
    for i in range(n):
        tp, dp = _pivot_onay(h, l, i, k)
        j = i - k
        yeni_piv = []
        if dp:
            yeni_piv.append((j, -1, l[j]))
        if tp:
            yeni_piv.append((j, 1, h[j]))
        for p in yeni_piv:
            if ph and ph[-1][1] == p[1]:        # aynı türden ardışık: daha uç olanı tut
                ust = ph[-1]
                if (p[1] == 1 and p[2] > ust[2]) or (p[1] == -1 and p[2] < ust[2]):
                    ph[-1] = p
                    continue
                else:
                    continue
            ph.append(p)
        ph = ph[-8:]
        if len(ph) >= 3 and (dp or tp):
            (ja, ta, fa), (jb, tb, fb), (jc, tc, fc) = ph[-3:]
            if jc == j:       # C az önce onaylandı
                if not tepe_modu and ta == -1 and tb == 1 and tc == -1:
                    ab = fb - fa
                    if ab >= ab_atr * at[jb] and fc > fa and geri_min <= (fb - fc) / ab <= geri_max:
                        yeni[i], A[i], B[i], C[i], D[i] = True, fa, fb, fc, fc + ab
                if tepe_modu and ta == 1 and tb == -1 and tc == 1:
                    ab = fa - fb
                    if ab >= ab_atr * at[jb] and fc < fa and geri_min <= (fc - fb) / ab <= geri_max:
                        yeni[i], A[i], B[i], C[i], D[i] = True, fa, fb, fc, fc - ab
    return pd.DataFrame({"yeni": yeni, "a": A, "b": B, "c": C, "d": D}, index=pd.RangeIndex(n))


def tuzak_durumu(yuksek, dusuk, kapanis, n_tepe=80, n_dip=12, geri_max=24, donus_max=12) -> np.ndarray:
    """Tuzak kırılım (boğa): yeni n_tepe-mumluk tepe (T) -> sonraki geri_max mum içinde mum dibi önceki n_dip mumun dibine iner
    (geri çekilme) -> bundan sonraki donus_max mum içinde KAPANIŞ T'nin üstüne çıkarsa sinyal. Tek ileri geçiş (nedensel)."""
    h, l, c = (np.asarray(x, dtype=float) for x in (yuksek, dusuk, kapanis))
    n = len(h)
    onceki_tepe = pd.Series(h).shift(1).rolling(n_tepe, min_periods=n_tepe).max().to_numpy()
    onceki_dip = pd.Series(l).shift(1).rolling(n_dip, min_periods=n_dip).min().to_numpy()
    sinyal = np.zeros(n, dtype=bool)
    asama, T, t0, t1 = 0, np.nan, 0, 0
    for i in range(n):
        if asama == 2:
            if c[i] > T and i - t1 <= donus_max:
                sinyal[i] = True
                asama = 0
            elif i - t1 >= donus_max:
                asama = 0
        elif asama == 1:
            if i - t0 > geri_max:
                asama = 0
            elif l[i] <= onceki_dip[i]:
                asama, t1 = 2, i
        if asama != 2 and not np.isnan(onceki_tepe[i]) and h[i] > onceki_tepe[i] and not sinyal[i]:
            asama, T, t0 = 1, h[i], i
    return sinyal
