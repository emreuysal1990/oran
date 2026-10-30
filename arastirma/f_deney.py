import sys, pickle, warnings; sys.path.insert(0, "."); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
import veri
G0 = pd.Timestamp("1970-01-01"); gn = lambda s: (pd.Timestamp(s) - G0).days
c = pickle.load(open("cache.pkl", "rb")); z = pickle.load(open("f_ozellik.pkl", "rb"))
d = c["d"]; gun = d.gun.values; KOD = veri.KODLAR; S = z["S"]; FORM = z["FORM"]
lg = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
sig = lambda x: 1 / (1 + np.exp(-x))
FOLD = {"A": (gn("2023-09-15"), gn("2024-07-01"), gn("2025-07-01")), "B": (gn("2023-09-15"), gn("2025-07-01"), 10 ** 7)}
Fm = FORM.reshape(len(d), -1); Fmiss = np.isnan(Fm[:, [0, 11]]).astype(float)   # ev/dep form yok göstergesi
Smiss = np.isnan(Fm[:, [2, 13]]).astype(float)                                     # isabetli şut yok göstergesi

def ozellik(j, PM, tip):
    p = PM[:, j]; cols = [lg(p)]
    if tip in ("M2", "M4"):
        t = z["V1T"][:, j]; nn, hh = z["V1N"][:, j], z["V1H"][:, j]
        cols += [np.where(np.isnan(t), 0, lg(t) - lg(p)), np.where(nn >= 4, hh / np.maximum(nn, 1) - p, 0)]
    if tip in ("M3", "M4"):
        cols += [Fm[:, k] for k in range(Fm.shape[1])] + [Fmiss[:, 0], Fmiss[:, 1], Smiss[:, 0], Smiss[:, 1]]
    return np.column_stack(cols)

TIP = ["M0", "M1", "M2", "M3", "M4"]
SON = {t: np.full(S.shape, np.nan) for t in TIP}
for fad, (a, b, e) in FOLD.items():
    PM = z["PM"][fad]; tr = (gun >= a) & (gun < b); te = (gun >= b) & (gun < e)
    for j in range(len(KOD)):
        y = S[:, j]; ok = ~np.isnan(y) & ~np.isnan(PM[:, j])
        SON["M0"][te & ok, j] = PM[te & ok, j]
        for t in TIP[1:]:
            X = ozellik(j, PM, t)
            mtr, mte = tr & ok, te & ok
            mu = np.nanmean(X[mtr], 0); sd = np.nanstd(X[mtr], 0) + 1e-9
            if t == "M1": mu[:] = 0; sd[:] = 1
            else: mu[0], sd[0] = 0, 1                         # model logiti olduğu gibi
            Xs = np.where(np.isnan((X - mu) / sd), 0, (X - mu) / sd)
            m = LogisticRegression(C=0.05 if t != "M1" else 10, max_iter=500).fit(Xs[mtr], y[mtr])
            SON[t][mte, j] = m.predict_proba(Xs[mte])[:, 1]
pickle.dump(SON, open("f_son.pkl", "wb"))

te_all = gun >= gn("2024-07-01")
ll = lambda p, y: -(y * np.log(np.clip(p, 1e-6, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-6, 1)))
print("Test maçı:", te_all.sum())
rows = []
for j, k in enumerate(KOD):
    y = S[:, j]; ok = te_all & ~np.isnan(y) & np.all([~np.isnan(SON[t][:, j]) for t in TIP], 0)
    r = {"kod": k, "grup": veri.GRUP[k], "n": ok.sum()}
    for t in TIP: r[t] = ll(SON[t][ok, j], y[ok]).mean()
    for fad, (a, b, e) in FOLD.items():
        m2 = ok & (gun >= b) & (gun < e)
        for t in ("M0", "M4"): r[t + fad] = ll(SON[t][m2, j], y[m2]).mean()
    rows.append(r)
T = pd.DataFrame(rows)
print("\nOrtalama log kayıp (küçük = iyi), 51 pazar:")
print("  " + "  ".join("%s %.5f" % (t, T[t].mean()) for t in TIP))
print("  M0'a göre kazanç (%%):  " + "  ".join("%s %+.3f" % (t, 100 * (T.M0.mean() - T[t].mean()) / T.M0.mean()) for t in TIP[1:]))
print("  M4, M0'dan iyi olduğu pazar:", (T.M4 < T.M0).sum(), "/ 51 ; fold A kazanç %.3f%%, fold B kazanç %.3f%%" % (
    100 * (T.M0A.mean() - T.M4A.mean()) / T.M0A.mean(), 100 * (T.M0B.mean() - T.M4B.mean()) / T.M0B.mean()))
g = T.groupby("grup")[TIP].mean()
g["M4 kazanç %"] = 100 * (g.M0 - g.M4) / g.M0; g["M3 kazanç %"] = 100 * (g.M0 - g.M3) / g.M0; g["M2 kazanç %"] = 100 * (g.M0 - g.M2) / g.M0
print(g.round(4).to_string())
T.to_csv("f_tablo.csv", index=False)
