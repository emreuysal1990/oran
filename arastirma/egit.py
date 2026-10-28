"""Katsayıları 2023-07-01 sonrası veriden eğit. kullanım: egit.py <bitis_tarihi|son> <cikti.json>"""
import sys, json, time, pickle; sys.path[:0] = [".", ".."]
import numpy as np, pandas as pd
from sklearn.linear_model import PoissonRegressor
import veri, modelkit as mk, kalib

MIN_LIG = 120                                  # bir ligin korner/kart modeline girmesi için eğitimde en az maç
LIG_KUKLA = {"c": False, "k": True}


def yuvarla(x, n=6):
    """Sayıları n haneye yuvarlar (katsayilar.json küçük ve okunur kalsın)."""
    if isinstance(x, float): return round(x, n)
    if isinstance(x, dict): return {k: yuvarla(v, n) for k, v in x.items()}
    if isinstance(x, list): return [yuvarla(v, n) for v in x]
    return x


def tara_hazirla():
    d = veri.yukle()
    d = d[d.Over25.notna() & d.Under25.notna()].reset_index(drop=True)
    P = mk.marj_guc(d.OddHome.values, d.OddDraw.values, d.OddAway.values)
    U = mk.marj_guc(d.Over25.values, d.Under25.values)[:, 0]
    return d, P, U

def satirlar_yap(d):
    nz = lambda x: None if pd.isna(x) else float(x)
    hc, ac = d.HomeCorners.values, d.AwayCorners.values
    hk = (d.HomeYellow + d.HomeRed).values; ak = (d.AwayYellow + d.AwayRed).values
    return [dict(lig=d.Division.values[i], gun=int(d.gun.values[i]), ev=d.HomeTeam.values[i], dep=d.AwayTeam.values[i],
                 hc=nz(hc[i]), ac=nz(ac[i]), hk=nz(hk[i]), ak=nz(ak[i]), fh=float(d.FTHome.values[i]), fa=float(d.FTAway.values[i]))
            for i in range(len(d))]

def X_matrisi(F, t, lh, la):
    n = len(F)
    X = np.full((n, 9), np.nan)
    X[:, 0], X[:, 1], X[:, 2], X[:, 3] = lh + la, np.abs(lh - la), lh, la
    for i, o in enumerate(F):
        f = o[t]
        for k in range(5):
            if f[k] is not None: X[i, 4 + k] = f[k]
    return X

def egit(bitis_gun, cikti=None, rapor=True):
    t0 = time.time()
    d, P, U = tara_hazirla()
    lh, la = mk.lambda_uydur(P[:, 0], P[:, 1], P[:, 2], U)
    sat = satirlar_yap(d)
    F = mk.ozellik_kur(sat)
    gun = d.gun.values
    ilk = (pd.Timestamp("2023-07-01") - pd.Timestamp("1970-01-01")).days
    tr = (gun >= ilk) & (gun < bitis_gun)
    out = {"rho": mk.RHO, "kappa": mk.KAPPA, "pencere": mk.PENCERE, "lig_pencere": mk.LIG_PENCERE}
    # ilk yarı gol payı
    hm = d.HTHome.notna().values & tr
    out["fh"] = float(d.HTHome[hm].sum() / d.FTHome[hm].sum()); out["fa"] = float(d.HTAway[hm].sum() / d.FTAway[hm].sum())
    # 2,5 Üst önseli (O/U oranı olmayan maçlar için)
    over = ((d.FTHome + d.FTAway).values >= 3).astype(float)
    lo = np.array([o["u"] if o["u"] is not None else np.nan for o in F])
    f = np.column_stack([np.ones(len(d)), kalib.logit(np.where(np.isnan(lo), 0.5, lo)), P[:, 1], (P[:, 0] - P[:, 2]) ** 2, np.abs(P[:, 0] - P[:, 2]), np.maximum(P[:, 0], P[:, 2])])
    m = tr & ~np.isnan(lo)
    out["pu_onsel_w"] = [float(x) for x in kalib.lojistik(f[m], over[m], np.full(6, 1.0), np.zeros(6))]
    # korner ve kart
    ligler = sorted(d.Division.unique())
    for t, ad, y in (("c", "korner", (d.HomeCorners + d.AwayCorners).values.astype(float)),
                     ("k", "kart", (d.HomeYellow + d.AwayYellow + d.HomeRed + d.AwayRed).values.astype(float))):
        X = X_matrisi(F, t, lh, la)
        mm = tr & ~np.isnan(y)
        ort = np.nanmean(X[mm], 0); sd = np.nanstd(X[mm], 0) + 1e-9
        Z = np.where(np.isnan((X - ort) / sd), 0.0, (X - ort) / sd)
        sayi = d.Division[mm].value_counts()
        lg_ok = [l for l in ligler if sayi.get(l, 0) >= MIN_LIG]          # modeli olan ligler (eğitimde yeterli maç)
        if LIG_KUKLA[t]:      # lig kuklaları (hafif ridge ile): kartta küçük ama tutarlı kazanç
            LD = np.column_stack([(d.Division.values == l).astype(float) for l in lg_ok])
            A = np.column_stack([Z, LD]); alpha = 5e-2
        else:                 # korner: lig seviyesi zaten 'lig_toplam' özelliğinde; kukla kazandırmıyor
            A = Z; alpha = 1e-3
        mdl = PoissonRegressor(alpha=alpha, max_iter=2000).fit(A[mm], y[mm])
        mu_tr = mdl.predict(A[mm])
        alfa = max(1e-3, float(np.mean(((y[mm] - mu_tr) ** 2 - mu_tr) / mu_tr ** 2)))
        w = mdl.coef_[:9]; lc = mdl.coef_[9:] if LIG_KUKLA[t] else np.zeros(len(lg_ok))
        out[t] = {"ozellik": ["T", "D", "lh", "la", "ev_atan", "ev_yiyen", "dep_atan", "dep_yiyen", "lig_toplam"], "ort": [float(x) for x in ort], "sd": [float(x) for x in sd],
                  "w": [float(x) for x in w], "b": float(mdl.intercept_), "lig": {l: float(c) for l, c in zip(lg_ok, lc)}, "alfa": alfa, "egitim_n": int(mm.sum())}
        if rapor: print(f"  {ad}: n={mm.sum()} alfa={alfa:.4f} mu_ort={mu_tr.mean():.3f} y_ort={y[mm].mean():.3f}  lig sayısı={len(lg_ok)}")
    out["ufuk"] = "2023-07-01"
    out["egitim_bitis"] = str((pd.Timestamp("1970-01-01") + pd.Timedelta(days=int(gun[tr].max()))).date())
    if cikti: json.dump(yuvarla(out), open(cikti, "w"), ensure_ascii=False, indent=1, sort_keys=True)
    if rapor: print("  süre", round(time.time() - t0, 1), "sn")
    return out, (d, P, U, lh, la, F)

if __name__ == "__main__":
    b = sys.argv[1]
    bg = 10 ** 6 if b == "son" else (pd.Timestamp(b) - pd.Timestamp("1970-01-01")).days
    egit(bg, sys.argv[2])
