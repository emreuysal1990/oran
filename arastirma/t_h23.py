"""2023 ufkunda korner/kart modeli: lig kuklası ve ridge ayarı (genişleyen pencere, iki fold)."""
import sys; sys.path[:0] = [".", ".."]
import numpy as np, pandas as pd
from scipy.special import gammaln
from sklearn.linear_model import PoissonRegressor
import veri, modelkit as mk, egit
d, P, U = egit.tara_hazirla()
lh, la = mk.lambda_uydur(P[:, 0], P[:, 1], P[:, 2], U)
F = mk.ozellik_kur(egit.satirlar_yap(d))
gun = d.gun.values; G0 = pd.Timestamp("1970-01-01"); gn = lambda s: (pd.Timestamp(s) - G0).days
ilk = gn("2023-07-01")
ligler = sorted(d.Division.unique())
def nb_ll(y, mu, a):
    r = 1 / a
    return gammaln(y + r) - gammaln(r) - gammaln(y + 1) + r * np.log(r / (r + mu)) + y * np.log(mu / (r + mu))
Y = {"c": (d.HomeCorners + d.AwayCorners).values.astype(float), "k": (d.HomeYellow + d.AwayYellow + d.HomeRed + d.AwayRed).values.astype(float)}
folds = [("2024-07-01", "2024-07-01", "2025-07-01"), ("2025-07-01", "2025-07-01", "2100-01-01")]
SECIM = {"tam": list(range(9)), "takimsiz": [0, 1, 2, 3, 8], "yalniz_T_lig": [0, 8], "tam_Dsiz": [0, 2, 3, 4, 5, 6, 7, 8]}
for t in ("c", "k"):
    X = egit.X_matrisi(F, t, lh, la); y = Y[t]
    print("==", "korner" if t == "c" else "kart")
    for ad, (trb, tea, teb) in zip("AB", folds):
        tr = (gun >= ilk) & (gun < gn(trb)) & ~np.isnan(y); te = (gun >= gn(tea)) & (gun < gn(teb)) & ~np.isnan(y)
        ort = np.nanmean(X[tr], 0); sd = np.nanstd(X[tr], 0) + 1e-9
        Z = np.where(np.isnan((X - ort) / sd), 0.0, (X - ort) / sd)
        sayi = d.Division[tr].value_counts()
        for sec_ad, cols in SECIM.items():
            for lig_mod in ("lig", "ligsiz"):
                for alpha in (1e-3, 1e-2, 5e-2):
                    if lig_mod == "lig":
                        lg_ok = [l for l in ligler if sayi.get(l, 0) >= 120]
                        LD = np.column_stack([(d.Division.values == l).astype(float) for l in lg_ok])
                        A = np.column_stack([Z[:, cols], LD])
                    else:
                        A = Z[:, cols]
                    m = PoissonRegressor(alpha=alpha, max_iter=2000).fit(A[tr], y[tr])
                    mu_tr = m.predict(A[tr]); a = max(1e-3, float(np.mean(((y[tr] - mu_tr) ** 2 - mu_tr) / mu_tr ** 2)))
                    mu = m.predict(A[te])
                    ll = nb_ll(y[te], mu, a).mean()
                    print(f"  fold {ad} {sec_ad:13s} {lig_mod:6s} alpha={alpha:<6g} test_ll={ll:.5f}  alfa={a:.4f} ntr={tr.sum()} nte={te.sum()}")
