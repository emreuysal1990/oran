"""Oranlardan Poisson (Dixon-Coles) skor modeli: piyasa ihtimalleri -> beklenen goller -> tüm pazarların ihtimali."""
import numpy as np
from scipy.special import gammaln

G = 13
K = np.arange(G)
LG = gammaln(K + 1)


def pmf(lam):
    lam = np.clip(lam, 1e-4, 9.0)
    return np.exp(-lam[:, None] + K[None, :] * np.log(lam)[:, None] - LG[None, :])


def matris(lh, la, rho=0.0):
    M = pmf(lh)[:, :, None] * pmf(la)[:, None, :]
    if rho != 0.0:
        M[:, 0, 0] *= 1 - lh * la * rho
        M[:, 0, 1] *= 1 + lh * rho
        M[:, 1, 0] *= 1 + la * rho
        M[:, 1, 1] *= 1 - rho
    return M


_IL = np.tril_indices(G, -1)   # ev > dep
_IU = np.triu_indices(G, 1)    # ev < dep


def ozet(M):
    """1X2 ve toplam gol dağılımı (T<=k için kümülatif)."""
    p1 = M[:, _IL[0], _IL[1]].sum(1)
    p2 = M[:, _IU[0], _IU[1]].sum(1)
    px = np.einsum("nii->n", M)
    n = M.shape[0]
    T = np.zeros((n, 8))
    for t in range(8):
        for h in range(t + 1):
            T[:, t] += M[:, h, t - h]
    return p1, px, p2, T


def uyum(lh, la, rho):
    M = matris(lh, la, rho)
    p1, px, p2, T = ozet(M)
    pu = 1.0 - T[:, :3].sum(1)   # P(toplam >= 3)
    return np.column_stack([p1, px, p2, pu])


def fit(p1, px, p2, pu, rho=0.0, onsel_u=None, w_u=None, it=30, parca=20000):
    """Piyasa ihtimallerine en küçük kareler uyumu. pu NaN ise onsel_u (lig ortalaması) küçük ağırlıkla kullanılır."""
    n = len(p1)
    hedef = np.column_stack([p1, px, p2, pu])
    w = np.ones((n, 4))
    if np.isnan(pu).any():
        eksik = np.isnan(pu)
        hedef[eksik, 3] = onsel_u if np.isscalar(onsel_u) else onsel_u[eksik]
        w[eksik, 3] = 0.3 if w_u is None else w_u
    lh = np.empty(n)
    la = np.empty(n)
    for a in range(0, n, parca):
        b = min(a + parca, n)
        th = np.column_stack([np.full(b - a, np.log(1.45)), np.full(b - a, np.log(1.1))])
        for _ in range(it):
            e = 1e-4
            f0 = uyum(np.exp(th[:, 0]), np.exp(th[:, 1]), rho)
            fa_ = uyum(np.exp(th[:, 0] + e), np.exp(th[:, 1]), rho)
            fb_ = uyum(np.exp(th[:, 0]), np.exp(th[:, 1] + e), rho)
            r = (f0 - hedef[a:b]) * w[a:b]
            J1 = (fa_ - f0) / e * w[a:b]
            J2 = (fb_ - f0) / e * w[a:b]
            a11 = (J1 * J1).sum(1) + 1e-6
            a12 = (J1 * J2).sum(1)
            a22 = (J2 * J2).sum(1) + 1e-6
            g1 = (J1 * r).sum(1)
            g2 = (J2 * r).sum(1)
            det = a11 * a22 - a12 * a12
            d1 = -(a22 * g1 - a12 * g2) / det
            d2 = -(-a12 * g1 + a11 * g2) / det
            d1 = np.clip(d1, -0.4, 0.4)
            d2 = np.clip(d2, -0.4, 0.4)
            th[:, 0] += d1
            th[:, 1] += d2
            th = np.clip(th, np.log(0.05), np.log(6.0))
            if max(np.abs(d1).max(), np.abs(d2).max()) < 1e-7:
                break
        lh[a:b] = np.exp(th[:, 0])
        la[a:b] = np.exp(th[:, 1])
    return lh, la


def piyasalar(lh, la, rho, fh=0.45, fa=0.45):
    """Gol temelli tüm pazarların ihtimali. fh/fa: ilk yarı gol payı. (modelkit matrisi: DC + kappa)"""
    import modelkit as mk
    M = mk.matris(lh, la, rho)
    p1, px, p2, T = ozet(M)
    c = np.cumsum(T, axis=1)         # c[:,k] = P(toplam <= k)
    ev = M.sum(2)                    # ev golü dağılımı
    dp = M.sum(1)                    # dep golü dağılımı
    evc, dpc = np.cumsum(ev, 1), np.cumsum(dp, 1)
    out = {"MS1": p1, "MSX": px, "MS2": p2, "CS1X": p1 + px, "CSX2": px + p2, "CS12": p1 + p2}
    for k, kk in ((15, 1), (25, 2), (35, 3), (45, 4)):
        out[f"A{k}"] = c[:, kk]
        out[f"U{k}"] = 1 - c[:, kk]
    kgv = 1 - ev[:, 0] - dp[:, 0] + M[:, 0, 0]
    out["KGV"], out["KGY"] = kgv, 1 - kgv
    out["EV05A"], out["EV05U"] = evc[:, 0], 1 - evc[:, 0]
    out["EV15A"], out["EV15U"] = evc[:, 1], 1 - evc[:, 1]
    out["EV25U"] = 1 - evc[:, 2]
    out["DEP05A"], out["DEP05U"] = dpc[:, 0], 1 - dpc[:, 0]
    out["DEP15A"], out["DEP15U"] = dpc[:, 1], 1 - dpc[:, 1]
    out["DEP25U"] = 1 - dpc[:, 2]
    # ilk yarı: bağımsız Poisson (DC düzeltmesi yok)
    Mh = matris(lh * fh, la * fa, 0.0)
    q1, qx, q2, Th = ozet(Mh)
    ch = np.cumsum(Th, 1)
    out["IY1"], out["IYX"], out["IY2"] = q1, qx, q2
    out["IY05A"], out["IY05U"] = ch[:, 0], 1 - ch[:, 0]
    out["IY15A"], out["IY15U"] = ch[:, 1], 1 - ch[:, 1]
    evh, dph = Mh.sum(2), Mh.sum(1)
    out["IYKGV"] = (1 - evh[:, 0]) * (1 - dph[:, 0])
    # ikinci yarı toplam golü ~ Poisson(lh(1-fh)+la(1-fa))
    l2 = lh * (1 - fh) + la * (1 - fa)
    e0 = np.exp(-l2)
    out["IY2Y05U"] = 1 - e0
    out["IY2Y15U"] = 1 - e0 * (1 + l2)
    return out
