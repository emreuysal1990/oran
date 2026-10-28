"""Genişletilmiş pazarlar: skor matrisi ve yarı-modelinden türetilen birleşik pazarlar (Python referansı; JS bunun kopyası)."""
import numpy as np
import modelkit as mk

G = mk.G
H_, A_ = np.meshgrid(np.arange(G), np.arange(G), indexing="ij")     # [h, a]
TOP = H_ + A_

def _topla(M, mask):
    return (M * mask[None, :, :]).sum((1, 2))

def skellam_tablo(l1, l2, dmax=12):
    """İki bağımsız Poisson farkının dağılımı: sütunlar d=-dmax..dmax"""
    p1, p2 = mk.pmf(l1), mk.pmf(l2)
    n = len(l1)
    out = np.zeros((n, 2 * dmax + 1))
    for h in range(G):
        for a in range(G):
            d = h - a
            if abs(d) <= dmax:
                out[:, d + dmax] += p1[:, h] * p2[:, a]
    return out

def genis_piyasalar(lh, la, rho, fh, fa):
    M = mk.matris(lh, la, rho)
    out = {}
    ev, dp = H_ > A_, H_ < A_
    ber = H_ == A_
    sonuc = {"1": ev, "X": ber, "2": dp}
    u25, a25 = TOP >= 3, TOP <= 2
    kgv, kgy = (H_ > 0) & (A_ > 0), (H_ == 0) | (A_ == 0)
    for s, m in sonuc.items():
        out[f"MS{s}_U25"] = _topla(M, m & u25); out[f"MS{s}_A25"] = _topla(M, m & a25)
        out[f"MS{s}_KGV"] = _topla(M, m & kgv); out[f"MS{s}_KGY"] = _topla(M, m & kgy)
    for ad, m in (("1X", ev | ber), ("X2", dp | ber), ("12", ev | dp)):
        out[f"{ad}_U25"] = _topla(M, m & u25); out[f"{ad}_A25"] = _topla(M, m & a25)
    out["KGV_U25"], out["KGV_A25"] = _topla(M, kgv & u25), _topla(M, kgv & a25)
    out["KGY_U25"], out["KGY_A25"] = _topla(M, kgy & u25), _topla(M, kgy & a25)
    # toplam gol aralığı, tek/çift, ek çizgiler
    out["TG01"], out["TG23"] = _topla(M, TOP <= 1), _topla(M, (TOP >= 2) & (TOP <= 3))
    out["TG46"], out["TG7P"] = _topla(M, (TOP >= 4) & (TOP <= 6)), _topla(M, TOP >= 7)
    out["TEK"] = np.full(len(lh), 0.5); out["CIFT"] = np.full(len(lh), 0.5)       # tek/çift: model bilgi eklemiyor (gerçek oran ≈ %50)
    out["A05"] = _topla(M, TOP == 0); out["U05"] = 1 - out["A05"]
    out["U55"] = _topla(M, TOP >= 6); out["A55"] = 1 - out["U55"]
    # handikaplı MS (ev takımına eklenen gol: -2,-1,+1,+2)
    for hn in (-2, -1, 1, 2):
        fark = H_ + hn - A_
        ad = f"HND{'m' if hn < 0 else 'p'}{abs(hn)}"
        out[ad + "_1"], out[ad + "_X"], out[ad + "_2"] = _topla(M, fark > 0), _topla(M, fark == 0), _topla(M, fark < 0)
    # ilk yarı / ikinci yarı (bağımsız yarılar) ve İY/MS
    l1h, l1a = lh * fh, la * fa
    l2h, l2a = lh * (1 - fh), la * (1 - fa)
    D1, D2 = skellam_tablo(l1h, l1a), skellam_tablo(l2h, l2a)          # d = -12..12, indeks d+12
    dm = 12
    P1 = {"1": D1[:, dm + 1:].sum(1), "X": D1[:, dm], "2": D1[:, :dm].sum(1)}
    out["Y2_1"], out["Y2_X"], out["Y2_2"] = D2[:, dm + 1:].sum(1), D2[:, dm], D2[:, :dm].sum(1)
    # FT farkı = d1 + d2
    n = len(lh)
    ftd = np.zeros((n, 3, 3))          # [IY sonucu(1,X,2), MS sonucu(1,X,2)]
    dd = np.arange(-dm, dm + 1)
    for i1, (nm1, mask1) in enumerate((("1", dd > 0), ("X", dd == 0), ("2", dd < 0))):
        for d1 in dd[mask1]:
            p_d1 = D1[:, d1 + dm]
            # d2 aralığı: FT>0 ⇔ d2 > -d1 ; FT=0 ⇔ d2 = -d1 ; FT<0 ⇔ d2 < -d1
            c = np.cumsum(D2, axis=1)         # P(d2 <= x) , x=-12..12
            def le(x):                        # P(d2 <= x)
                x = max(min(x, dm), -dm - 1)
                return np.zeros(n) if x < -dm else c[:, x + dm]
            ftd[:, i1, 0] += p_d1 * (1 - le(-d1))
            ftd[:, i1, 1] += p_d1 * (le(-d1) - le(-d1 - 1))
            ftd[:, i1, 2] += p_d1 * le(-d1 - 1)
    # IPF adımı: MS marjinalini Dixon-Coles matrisine eşitle
    ms_dc = np.column_stack([out["MS1_U25"] + out["MS1_A25"], out["MSX_U25"] + out["MSX_A25"], out["MS2_U25"] + out["MS2_A25"]])
    ms_h = ftd.sum(1)
    ftd = ftd * (ms_dc / ms_h)[:, None, :]
    ftd = ftd / ftd.sum((1, 2), keepdims=True)
    for i1, a in enumerate("1X2"):
        for i2, b in enumerate("1X2"):
            out[f"IYMS_{a}{b}"] = ftd[:, i1, i2]
    # çifte şans İY ve en çok gol yarısı
    out["IY1X"], out["IYX2"], out["IY12"] = P1["1"] + P1["X"], P1["X"] + P1["2"], P1["1"] + P1["2"]
    t1, t2 = mk.pmf(l1h + l1a), mk.pmf(l2h + l2a)
    cm1 = np.cumsum(t1, 1)
    c2 = np.cumsum(t2, 1)
    out["YARI_1"] = sum(t1[:, k] * (c2[:, k - 1] if k > 0 else 0.0) for k in range(G))   # 1. yarıda daha çok gol: T1 > T2
    out["YARI_E"] = (t1 * t2).sum(1)
    out["YARI_2"] = 1 - out["YARI_1"] - out["YARI_E"]
    return out

def genis_sonuclar(d):
    """Aynı kodlar için gerçekleşen sonuç (1/0), HT yoksa NaN"""
    fh, fa = d.FTHome.values, d.FTAway.values
    hh, ha = d.HTHome.values.astype(float), d.HTAway.values.astype(float)
    tot = fh + fa
    ev, dp, ber = fh > fa, fh < fa, fh == fa
    sonuc = {"1": ev, "X": ber, "2": dp}
    u25, a25 = tot >= 3, tot <= 2
    kgv = (fh > 0) & (fa > 0); kgy = ~kgv
    o = {}
    f = lambda x: x.astype(float)
    for s, m in sonuc.items():
        o[f"MS{s}_U25"], o[f"MS{s}_A25"], o[f"MS{s}_KGV"], o[f"MS{s}_KGY"] = f(m & u25), f(m & a25), f(m & kgv), f(m & kgy)
    for ad, m in (("1X", ev | ber), ("X2", dp | ber), ("12", ev | dp)):
        o[f"{ad}_U25"], o[f"{ad}_A25"] = f(m & u25), f(m & a25)
    o["KGV_U25"], o["KGV_A25"], o["KGY_U25"], o["KGY_A25"] = f(kgv & u25), f(kgv & a25), f(kgy & u25), f(kgy & a25)
    o["TG01"], o["TG23"], o["TG46"], o["TG7P"] = f(tot <= 1), f((tot >= 2) & (tot <= 3)), f((tot >= 4) & (tot <= 6)), f(tot >= 7)
    o["TEK"], o["CIFT"] = f(tot % 2 == 1), f(tot % 2 == 0)
    o["A05"], o["U05"], o["U55"], o["A55"] = f(tot == 0), f(tot >= 1), f(tot >= 6), f(tot <= 5)
    for hn in (-2, -1, 1, 2):
        fk = fh + hn - fa; ad = f"HND{'m' if hn < 0 else 'p'}{abs(hn)}"
        o[ad + "_1"], o[ad + "_X"], o[ad + "_2"] = f(fk > 0), f(fk == 0), f(fk < 0)
    nan = np.isnan(hh)
    h1 = np.where(nan, np.nan, np.sign(hh - ha)); ft = np.sign(fh - fa)
    nm = {1: "1", 0: "X", -1: "2"}
    for a in (1, 0, -1):
        for b in (1, 0, -1):
            o[f"IYMS_{nm[a]}{nm[b]}"] = np.where(nan, np.nan, ((h1 == a) & (ft == b)).astype(float))
    h2 = (fh - hh) - (fa - ha)
    o["Y2_1"], o["Y2_X"], o["Y2_2"] = np.where(nan, np.nan, f(h2 > 0)), np.where(nan, np.nan, f(h2 == 0)), np.where(nan, np.nan, f(h2 < 0))
    o["IY1X"], o["IYX2"], o["IY12"] = np.where(nan, np.nan, f(h1 >= 0)), np.where(nan, np.nan, f(h1 <= 0)), np.where(nan, np.nan, f(h1 != 0))
    t1 = hh + ha; t2 = tot - t1
    o["YARI_1"], o["YARI_E"], o["YARI_2"] = np.where(nan, np.nan, f(t1 > t2)), np.where(nan, np.nan, f(t1 == t2)), np.where(nan, np.nan, f(t1 < t2))
    return o
