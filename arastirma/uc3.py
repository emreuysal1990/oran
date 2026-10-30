"""Hızlı sürüm: tüm olası tahmin kodları için gösterge matrisi Y[n, K] (NaN = uygulanamaz)."""
import sys, pickle, time; sys.path.insert(0, ".")
import numpy as np, pandas as pd
from uc2 import d, P, U, n, gun, lig, fh, fa, hh, ha, iyok, kor, kart, RH, RA, s3, aralik, TUR

# ---------------------------------------------------------------- kod uzayı
NIT = {}   # özellik -> dizi (str ya da None)
NIT["SK"] = np.array([f"{a}-{b}" for a, b in zip(fh, fa)], dtype=object)
NIT["MS"] = np.array([s3(a, b) for a, b in zip(fh, fa)], dtype=object)
NIT["GA"] = np.array([aralik(a + b) for a, b in zip(fh, fa)], dtype=object)
NIT["KG"] = np.array(["Var" if a > 0 and b > 0 else "Yok" for a, b in zip(fh, fa)], dtype=object)
NIT["IS"] = np.array([f"{a}-{b}" if ok else None for a, b, ok in zip(hh, ha, iyok)], dtype=object)
NIT["IY"] = np.array([s3(a, b) if ok else None for a, b, ok in zip(hh, ha, iyok)], dtype=object)
NIT["IM"] = np.array([(s3(a, b) + "/" + m) if ok else None for a, b, ok, m in zip(hh, ha, iyok, NIT["MS"])], dtype=object)
for ev, dep in ((0, 1), (0, 2), (1, 0), (2, 0)):
    NIT[f"H{ev}{dep}"] = np.array([s3(a + ev, b + dep) for a, b in zip(fh, fa)], dtype=object)
SAYI = {"AU": (fh + fa).astype(float), "EV": fh.astype(float), "DP": fa.astype(float),
        "IG": np.where(iyok, hh + ha, np.nan).astype(float), "KO": kor.astype(float), "KA": kart.astype(float)}
CIZ = {"AU": [1.5, 2.5, 3.5, 4.5, 5.5], "EV": [0.5, 1.5, 2.5], "DP": [0.5, 1.5, 2.5], "IG": [0.5, 1.5, 2.5],
       "KO": [6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5], "KA": [1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5]}
KODLAR = []; TURU = []; kol = []
for k, arr in NIT.items():
    for v in sorted({x for x in arr if x is not None}):
        KODLAR.append(k + v); TURU.append(TUR["H" if k.startswith("H") else k])
        kol.append(np.where(np.array([x is None for x in arr]), np.nan, (arr == v).astype(float)))
for cs in ("1X", "X2", "12"):
    KODLAR.append("CS" + cs); TURU.append(TUR["CS"]); kol.append(np.array([1.0 if m in cs else 0.0 for m in NIT["MS"]]))
for k, x in SAYI.items():
    for c_ in CIZ[k]:
        KODLAR.append(f"{k}U{c_}"); TURU.append(TUR[k]); kol.append(np.where(np.isnan(x), np.nan, (x > c_).astype(float)))
        KODLAR.append(f"{k}A{c_}"); TURU.append(TUR[k]); kol.append(np.where(np.isnan(x), np.nan, (x < c_).astype(float)))
Y = np.column_stack(kol); K = len(KODLAR); KI = {k: j for j, k in enumerate(KODLAR)}
print("kod sayısı", K)

def secilenler(L):
    """L: benzer maç indeksleri -> tahmin kodlarının sütun indeksleri (JS ucTahminler ile aynı kurallar)"""
    out = []
    def hepsi(k):
        vs = NIT[k][L]
        return vs[0] if vs[0] is not None and all(x == vs[0] for x in vs) else None
    for k in ("SK", "IS", "IM"):
        v = hepsi(k)
        if v: out.append(KI[k + v])
    ms = hepsi("MS")
    if ms: out.append(KI["MS" + ms])
    else:
        for cs in ("1X", "X2", "12"):
            if all(m in cs for m in NIT["MS"][L]): out.append(KI["CS" + cs])
    for k in ("IY", "GA", "KG"):
        v = hepsi(k)
        if v: out.append(KI[k + v])
    for ev, dep, izin in ((0, 1, "1X"), (0, 2, "1X"), (1, 0, "X2"), (2, 0, "X2")):
        v = hepsi(f"H{ev}{dep}")
        if v and v in izin: out.append(KI[f"H{ev}{dep}{v}"])
    for k in ("AU", "EV", "DP", "IG", "KO", "KA"):
        x = SAYI[k][L]
        if np.isnan(x).any(): continue
        mn, mx = x.min(), x.max(); cz = CIZ[k]
        ust = [c_ for c_ in cz if mn > c_]; alt = [c_ for c_ in cz if mx < c_]
        if ust: out.append(KI[f"{k}U{ust[-1]}"])
        if alt: out.append(KI[f"{k}A{alt[0]}"])
    return out

TEST_BAS = (pd.Timestamp("2024-07-01") - pd.Timestamp("1970-01-01")).days
# lig bazında birikimli sayılar (taban oran için)
LIGIDX = {}
for lg in np.unique(lig):
    idx = np.where(lig == lg)[0]; idx = idx[np.argsort(gun[idx], kind="stable")]
    Yl = Y[idx]; cn = np.vstack([np.zeros(K), np.cumsum(~np.isnan(Yl), 0)]); ch = np.vstack([np.zeros(K), np.cumsum(np.nan_to_num(Yl), 0)])
    LIGIDX[lg] = (idx, gun[idx], cn, ch)

def calistir(N=3, w_sira=0.0, tol=0.025, onsel=8, haric=False):
    rows = []
    for lg, (idx, g, cn, ch) in LIGIDX.items():
        for jj, i in enumerate(idx):
            if gun[i] < TEST_BAS: continue
            b = np.searchsorted(g, gun[i], side="left")
            if b < 30: continue
            onc = idx[:b]
            dm = np.maximum.reduce([np.abs(P[onc, 0] - P[i, 0]), np.abs(P[onc, 1] - P[i, 1]), np.abs(P[onc, 2] - P[i, 2])])
            if not np.isnan(U[i]):
                du = np.abs(U[onc] - U[i]); dm = np.maximum(dm, np.where(np.isnan(du), 9, du))
            gen = onc[dm <= 2 * tol]
            dd = dm
            if w_sira > 0:
                if np.isnan(RH[i]): continue
                ds = np.maximum(np.abs(RH[onc] - RH[i]), np.abs(RA[onc] - RA[i]))
                dd = np.maximum(dm, w_sira * np.where(np.isnan(ds), 9, ds))
            aday = np.where(dd <= 2 * tol)[0]
            if len(aday) < N: continue
            sec = aday[np.lexsort((-g[aday], dd[aday]))][:N]
            ks = secilenler(onc[sec])
            if not ks: continue
            ks = np.array(ks)
            if haric: gen = np.setdiff1d(gen, onc[sec])
            y = Y[i, ks]; ok = ~np.isnan(y)
            if not ok.any(): continue
            ks, y = ks[ok], y[ok]
            lo = np.where(cn[b, ks] >= 30, ch[b, ks] / np.maximum(cn[b, ks], 1), np.nan)
            Yg = Y[gen][:, ks]; gn = (~np.isnan(Yg)).sum(0); gh = np.nansum(Yg, 0)
            tah = np.where(np.isnan(lo), np.where(gn > 0, gh / np.maximum(gn, 1), np.nan), (gh + onsel * lo) / (gn + onsel))
            for k, yy, t_, l_ in zip(ks, y, tah, lo):
                rows.append((i, k, yy, t_, l_))
    R = pd.DataFrame(rows, columns=["mac", "k", "y", "tah", "taban"])
    R["kod"] = np.array(KODLAR)[R.k]; R["tur"] = np.array(TURU)[R.k]; R["sezon"] = d.sezon.values[R.mac]
    return R

if __name__ == "__main__":
    t0 = time.time(); R = calistir(3); print("süre", round(time.time() - t0, 1), "sn; tahmin", len(R))
    # uc2 ile aynı mı?
    R2 = pickle.load(open("uc2_N3.pkl", "rb"))
    print("uc2:", len(R2), "tutma", R2.y.mean().round(4), "ort tah", R2.tah.mean().round(4), "| uc3:", len(R), "tutma", R.y.mean().round(4), "ort tah", R.tah.mean().round(4))
