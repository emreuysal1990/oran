"""Sayfadaki (v1) benzer maç yönteminin birebir Python karşılığı: tara() + analiz()."""
import numpy as np

ONCUL = 8.0


def v1_tahmin(d, S, P, U, hedef_idx, havuz_ilk_gun, tol=0.025, maks=10, minimum=4, esik=1.0, au_var=True):
    """
    d: DataFrame (tarih sıralı), S: (n,49) sonuç (NaN=uygulanamaz), P: (n,3) p1,px,p2, U: (n,) pu (NaN olabilir)
    hedef_idx: tahmin yapılacak satır indeksleri
    Dönüş: tah (m,49), yakin_n (m,49), yakin_h (m,49)  — sinyal = yakin_n>=minimum & yakin_h/yakin_n>=esik
    """
    n_pazar = S.shape[1]
    Sv = np.where(np.isnan(S), -1, S).astype(np.int8)
    gun = d.gun.values
    lig = d.Division.values
    tah = np.full((len(hedef_idx), n_pazar), np.nan)
    yn = np.zeros((len(hedef_idx), n_pazar), dtype=np.int16)
    yh = np.zeros((len(hedef_idx), n_pazar), dtype=np.int16)
    tol2 = 2 * tol
    pos = {int(i): k for k, i in enumerate(hedef_idx)}
    hedef_set = set(int(i) for i in hedef_idx)
    for lg in np.unique(lig[list(hedef_set)]):
        idx = np.where((lig == lg) & (gun >= havuz_ilk_gun))[0]      # havuz: kendi ligi, sayfadaki geçmiş
        g = gun[idx]
        p1, px, p2 = P[idx, 0], P[idx, 1], P[idx, 2]
        pu = U[idx]
        s = Sv[idx]
        # lig ortalaması için birikimli sayılar
        gecerli = (s >= 0).astype(np.int32)
        cn = np.vstack([np.zeros((1, n_pazar), np.int32), np.cumsum(gecerli, axis=0)])
        ch = np.vstack([np.zeros((1, n_pazar), np.int32), np.cumsum((s > 0).astype(np.int32), axis=0)])
        pu_var = (~np.isnan(pu)).mean() > 0.5
        for j, i in enumerate(idx):
            if int(i) not in hedef_set:
                continue
            b = np.searchsorted(g, g[j], side="left")      # gün olarak kesin öncesi
            k = pos[int(i)]
            n_lig = cn[b]
            lo = np.where(n_lig >= 30, ch[b] / np.maximum(n_lig, 1), np.nan)
            if b == 0:
                tah[k] = lo
                continue
            d1 = np.abs(P[i, 0] - p1[:b])
            d2 = np.abs(P[i, 2] - p2[:b])
            dx = np.abs(P[i, 1] - px[:b])
            m = (d1 <= tol2) & (d2 <= tol2) & (dx <= tol2)
            dm = np.maximum(np.maximum(d1, d2), dx)
            if au_var and not np.isnan(U[i]) and pu_var:
                du = np.abs(U[i] - pu[:b])
                m &= (~np.isnan(du)) & (du <= tol2)
                dm = np.maximum(dm, np.nan_to_num(du, nan=9.0))
            gen = np.where(m)[0]
            if len(gen) == 0:
                tah[k] = lo
                continue
            dd = dm[gen]
            yak_mask = dd <= tol + 1e-12
            yak = gen[yak_mask]
            # d artan, eşitlikte yeni olan önce
            sira = np.lexsort((-g[yak], dm[yak]))
            sec = yak[sira][:maks]
            ss = s[sec]
            nn = (ss >= 0).sum(0)
            hh = (ss > 0).sum(0)
            sg = s[gen]
            tn_all = (sg >= 0).sum(0)
            th_all = (sg > 0).sum(0)
            # geniş penceredeki herkes (yakın olanlar dahil) sayılır: n+gn = tum geniş içinde seçilmişler + dışarıdakiler
            # v1: tn = n + gn, h+gh -> seçilenler + seçilmeyen geniş  == tüm geniş
            tn = tn_all
            th = th_all
            with np.errstate(invalid="ignore", divide="ignore"):
                t_ = np.where(np.isnan(lo), np.where(tn > 0, th / np.maximum(tn, 1), np.nan), (th + ONCUL * lo) / (tn + ONCUL))
            tah[k] = t_
            yn[k] = nn
            yh[k] = hh
    return tah, yn, yh
