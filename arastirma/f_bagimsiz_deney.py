import sys, pickle, warnings, time; sys.path.insert(0, "."); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
import veri
G0 = pd.Timestamp("1970-01-01"); gn = lambda s: (pd.Timestamp(s) - G0).days
c = pickle.load(open("cache.pkl", "rb")); z = pickle.load(open("f_ozellik.pkl", "rb")); B = pickle.load(open("f_bagimsiz.pkl", "rb"))
d = c["d"]; gun = d.gun.values; KOD = veri.KODLAR; S = z["S"]
X0 = np.column_stack([B["X"], B["lig"].astype(float)]); LIGCOL = X0.shape[1] - 1
lg = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
FOLD = {"A": (gn("2023-09-15"), gn("2024-07-01"), gn("2025-07-01")), "B": (gn("2023-09-15"), gn("2025-07-01"), 10 ** 7)}
MS = np.full(S.shape, np.nan); MH = np.full(S.shape, np.nan); M0 = np.full(S.shape, np.nan)
def hgb(): return HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=80, l2_regularization=1.0,
                                                 early_stopping=True, validation_fraction=0.15, n_iter_no_change=20, categorical_features=[LIGCOL], random_state=0)
t0 = time.time()
for fad, (a, b, e) in FOLD.items():
    PM = z["PM"][fad]
    for j, k in enumerate(KOD):
        y = S[:, j]; ok = ~np.isnan(y) & ~np.isnan(PM[:, j])
        tr, te = ok & (gun >= a) & (gun < b), ok & (gun >= b) & (gun < e)
        M0[te, j] = PM[te, j]
        m = hgb().fit(X0[tr], y[tr]); MS[te, j] = m.predict_proba(X0[te])[:, 1]
        Xh = np.column_stack([X0, lg(PM[:, j])])
        m = hgb().fit(Xh[tr], y[tr]); MH[te, j] = m.predict_proba(Xh[te])[:, 1]
    print("fold", fad, "bitti", round(time.time() - t0), "sn", flush=True)
pickle.dump(dict(MS=MS, MH=MH, M0=M0), open("f_bagimsiz_son.pkl", "wb"))
ll = lambda p, y: -(y * np.log(np.clip(p, 1e-6, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-6, 1)))
te = gun >= gn("2024-07-01")
rows = []
for j, k in enumerate(KOD):
    y = S[:, j]; ok = te & ~np.isnan(y) & ~np.isnan(M0[:, j]) & ~np.isnan(MS[:, j])
    rows.append(dict(kod=k, grup=veri.GRUP[k], M0=ll(M0[ok, j], y[ok]).mean(), MS=ll(MS[ok, j], y[ok]).mean(), MH=ll(MH[ok, j], y[ok]).mean()))
T = pd.DataFrame(rows)
print("\n[1] Ortalama log kayıp (küçük = iyi): oranlar M0 %.5f | yalnız istatistik MS %.5f | istatistik+oran MH %.5f" % (T.M0.mean(), T.MS.mean(), T.MH.mean()))
print("    MS, M0'dan iyi: %d/51 pazar ; MH, M0'dan iyi: %d/51" % ((T.MS < T.M0).sum(), (T.MH < T.M0).sum()))
g = T.groupby("grup")[["M0", "MS", "MH"]].mean(); g["MS fark %"] = 100 * (g.M0 - g.MS) / g.M0; g["MH fark %"] = 100 * (g.M0 - g.MH) / g.M0
print(g.round(4).to_string())
