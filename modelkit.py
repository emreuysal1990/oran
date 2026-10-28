"""
Oran modeli çekirdeği (yalnızca numpy). Hem araştırmada hem üretimde (guncelle.py) aynen kullanılır.

1) Piyasa oranlarından (1X2 + 2,5 Alt/Üst) marj temizlenir, Poisson/Dixon-Coles skor modeli uydurulur
   (beklenen ev ve deplasman golü).
2) Korner ve kart toplamları için negatif binom ortalaması: lig seviyesi + takımların son 20 maçı + oran bilgisi.
"""
import math
from collections import deque

import numpy as np

G = 13                                  # 0..12 gol
K = np.arange(G)
LF = np.array([math.lgamma(k + 1) for k in range(G)])
RHO = -0.04                             # Dixon-Coles düşük skor düzeltmesi
KAPPA = 0.90                            # 2 ve üzeri gol farkı hücrelerinin ağırlığı (Poisson fark kuyruğunu daraltır)
PENCERE = 20                            # takım özellikleri için son maç sayısı
MIN_MAC = 4
LIG_PENCERE = 400                       # lig seviyesi için son maç sayısı


# ----------------------------------------------------------------------------- marj temizleme
def marj_guc(*oranlar, it=40):
    """Güç yöntemi: sum(p_i^k)=1 olan k bulunur (favori-uzun vade yanlılığını azaltır). Girdi: oran dizileri."""
    inv = np.column_stack([1.0 / np.asarray(x, float) for x in oranlar])
    lo = np.ones(len(inv))
    hi = np.full(len(inv), 3.0)
    for _ in range(it):
        mid = (lo + hi) / 2
        s = (inv ** mid[:, None]).sum(axis=1)
        buyuk = s > 1
        lo = np.where(buyuk, mid, lo)
        hi = np.where(buyuk, hi, mid)
    k = (lo + hi) / 2
    p = inv ** k[:, None]
    return p / p.sum(axis=1, keepdims=True)


# ----------------------------------------------------------------------------- Poisson / Dixon-Coles
def pmf(lam):
    lam = np.clip(lam, 1e-4, 9.0)
    return np.exp(-lam[:, None] + K[None, :] * np.log(lam)[:, None] - LF[None, :])


_FARK = np.abs(np.arange(G)[:, None] - np.arange(G)[None, :])
_W = np.where(_FARK >= 2, KAPPA, 1.0)


def matris(lh, la, rho=RHO, kappa=KAPPA):
    """Skor matrisi M[n, ev golü, dep golü]: bağımsız Poisson × Dixon-Coles düzeltmesi × fark ağırlığı, toplamı 1."""
    M = pmf(lh)[:, :, None] * pmf(la)[:, None, :]
    if rho != 0.0:
        M[:, 0, 0] *= 1 - lh * la * rho
        M[:, 0, 1] *= 1 + lh * rho
        M[:, 1, 0] *= 1 + la * rho
        M[:, 1, 1] *= 1 - rho
    if kappa != 1.0:
        M = M * np.where(_FARK >= 2, kappa, 1.0)[None]
    return M / M.sum((1, 2), keepdims=True)


_IL = np.tril_indices(G, -1)
_IU = np.triu_indices(G, 1)


def ozet(M):
    p1 = M[:, _IL[0], _IL[1]].sum(1)
    p2 = M[:, _IU[0], _IU[1]].sum(1)
    px = np.einsum("nii->n", M)
    T = np.zeros((M.shape[0], 8))
    for t in range(8):
        for h in range(t + 1):
            T[:, t] += M[:, h, t - h]
    return p1, px, p2, T


def uyum(lh, la, rho=RHO):
    p1, px, p2, T = ozet(matris(lh, la, rho))
    return np.column_stack([p1, px, p2, 1.0 - T[:, :3].sum(1)])


def lambda_uydur(p1, px, p2, pu, rho=RHO, pu_onsel=None, w_onsel=0.3, it=30, parca=20000):
    """
    Piyasa ihtimallerine (1, X, 2, 2,5 Üst) en küçük kareler uyumu → (beklenen ev golü, beklenen deplasman golü).
    pu NaN ise pu_onsel (tahmini 2,5 Üst ihtimali) w_onsel ağırlığıyla kullanılır.
    """
    p1, px, p2, pu = (np.asarray(x, float) for x in (p1, px, p2, pu))
    n = len(p1)
    hedef = np.column_stack([p1, px, p2, pu])
    w = np.ones((n, 4))
    eksik = np.isnan(pu)
    if eksik.any():
        on = np.asarray(pu_onsel, float) if pu_onsel is not None else np.full(n, 0.5)
        hedef[eksik, 3] = on[eksik] if on.ndim else on
        w[eksik, 3] = w_onsel
    lh = np.empty(n)
    la = np.empty(n)
    for a in range(0, n, parca):
        b = min(a + parca, n)
        th = np.column_stack([np.full(b - a, math.log(1.45)), np.full(b - a, math.log(1.1))])
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
            d1 = np.clip(-(a22 * g1 - a12 * g2) / det, -0.4, 0.4)
            d2 = np.clip(-(-a12 * g1 + a11 * g2) / det, -0.4, 0.4)
            th[:, 0] += d1
            th[:, 1] += d2
            th = np.clip(th, math.log(0.05), math.log(6.0))
            if max(np.abs(d1).max(), np.abs(d2).max()) < 1e-7:
                break
        lh[a:b] = np.exp(th[:, 0])
        la[a:b] = np.exp(th[:, 1])
    return lh, la


def sig(x):
    return 1.0 / (1.0 + np.exp(-x))


def logit(p, eps=1e-4):
    p = np.clip(p, eps, 1 - eps)
    return np.log(p / (1 - p))


def pu_onsel_tahmin(p1, px, p2, lig_orani, w):
    """2,5 Alt/Üst oranı olmayan maçlar için 2,5 Üst ihtimali tahmini (lig seviyesi + 1X2). w: 6 katsayı."""
    p1, px, p2, lo = (np.asarray(x, float) for x in (p1, px, p2, lig_orani))
    f = np.column_stack([np.ones(len(p1)), logit(lo), px, (p1 - p2) ** 2, np.abs(p1 - p2), np.maximum(p1, p2)])
    return sig(f @ np.asarray(w, float))


# ----------------------------------------------------------------------------- takım özellikleri (korner / kart)
def ozellik_kur(satirlar, ozellik_adlari=("c", "k")):
    """
    satirlar: (gun, sıra) sırasına göre dizilmiş sözlükler:
       lig, gun, ev, dep, hc, ac (ev/dep korner), hk, ak (ev/dep kart), fh, fa (ev/dep gol)  — bilinmeyenler None
    Her satır için maçtan ÖNCEKİ bilgilerle:
       {'c': [h_for, h_against, a_for, a_against, lig_toplam], 'k': [...], 'u': ligin 2,5 üst oranı}  (yetersizse None)
    Aynı gündeki maçlar birbirini görmez.
    """
    takim = {"c": {}, "k": {}}                 # takım -> (deque for, deque against)
    lig = {"c": {}, "k": {}}                   # lig -> deque toplam
    lig_u = {}                                 # lig -> deque (toplam gol >= 3)
    cikti = [None] * len(satirlar)
    i = 0
    n = len(satirlar)
    while i < n:
        j = i
        while j < n and satirlar[j]["gun"] == satirlar[i]["gun"]:
            j += 1
        for r in range(i, j):                  # önce özellikler
            s = satirlar[r]
            o = {}
            for t in ozellik_adlari:
                f = []
                for tk in (s["ev"], s["dep"]):
                    d = takim[t].get(tk)
                    if d is None or len(d[0]) < MIN_MAC:
                        f += [None, None]
                    else:
                        f += [sum(d[0]) / len(d[0]), sum(d[1]) / len(d[1])]
                ld = lig[t].get(s["lig"])
                f.append(sum(ld) / len(ld) if ld is not None and len(ld) >= 60 else None)
                o[t] = f
            ud = lig_u.get(s["lig"])
            o["u"] = sum(ud) / len(ud) if ud is not None and len(ud) >= 60 else None
            cikti[r] = o
        for r in range(i, j):                  # sonra durumu güncelle
            s = satirlar[r]
            if s.get("fh") is not None and s.get("fa") is not None:
                lig_u.setdefault(s["lig"], deque(maxlen=LIG_PENCERE)).append(1.0 if s["fh"] + s["fa"] >= 3 else 0.0)
            for t, (a, b) in (("c", (s.get("hc"), s.get("ac"))), ("k", (s.get("hk"), s.get("ak")))):
                if a is None or b is None:
                    continue
                for tk, kendi, rakip in ((s["ev"], a, b), (s["dep"], b, a)):
                    d = takim[t].setdefault(tk, (deque(maxlen=PENCERE), deque(maxlen=PENCERE)))
                    d[0].append(kendi)
                    d[1].append(rakip)
                lig[t].setdefault(s["lig"], deque(maxlen=LIG_PENCERE)).append(a + b)
        i = j
    return cikti


def kk_matris(ozellikler, lh, la, lig_kodlari, kat):
    """
    Korner/kart ortalamaları. ozellikler: ozellik_kur çıktısındaki 'c' veya 'k' listesi (maç başına 5 değer/None).
    kat: {"ozellik": [...], "ort": [...], "sd": [...], "w": [...], "b": c, "lig": {kod: katsayı}, "alfa": a}
    Dönüş: (mu, ok) — ok False ise lig için model yok.
    """
    n = len(lh)
    T, D = lh + la, np.abs(lh - la)
    X = np.zeros((n, 9))
    X[:, 0], X[:, 1], X[:, 2], X[:, 3] = T, D, lh, la
    ok = np.ones(n, bool)
    for i, f in enumerate(ozellikler):
        if f is None:
            ok[i] = False
            continue
        for k in range(5):
            X[i, 4 + k] = np.nan if f[k] is None else f[k]
    ort, sd, w = (np.asarray(kat[k], float) for k in ("ort", "sd", "w"))
    Z = (X - ort) / sd
    Z = np.where(np.isnan(Z), 0.0, Z)          # eksik özellik → eğitim ortalaması
    z = kat["b"] + Z @ w
    for i, lg in enumerate(lig_kodlari):
        c = kat["lig"].get(lg)
        if c is None:
            ok[i] = False
        else:
            z[i] += c
    return np.exp(np.clip(z, -5, 5)), ok


def nb_tablo(mu, alfa, kmax=40):
    """Negatif binom olasılık tablosu P(Y=k), k=0..kmax. Var = mu + alfa*mu^2. (JS ile aynı özyineleme)"""
    mu = np.asarray(mu, float)
    r = 1.0 / alfa
    p = r / (r + mu)
    out = np.empty((len(mu), kmax + 1))
    out[:, 0] = p ** r
    for k in range(kmax):
        out[:, k + 1] = out[:, k] * (k + r) / (k + 1) * (1 - p)
    return out
