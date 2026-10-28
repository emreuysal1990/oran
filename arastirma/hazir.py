"""Ortak hazırlık: veri, marj temizleme, Poisson uyumu, ham pazar ihtimalleri. Sonuç cache.pkl"""
import sys, time, pickle; sys.path[:0] = [".", ".."]
import numpy as np, pandas as pd
import veri, model, modelkit as mk

RHO = mk.RHO
d = veri.yukle()
d = d[d.Over25.notna() & d.Under25.notna()].reset_index(drop=True)
P = veri.marj_guc(d.OddHome.values, d.OddDraw.values, d.OddAway.values)
U = veri.marj_guc(d.Over25.values, d.Under25.values)[:, 0]
S = veri.sonuclar(d)
hm = d.HTHome.notna()
FH = d.HTHome[hm].mean() / d.FTHome[hm].mean()
FA = d.HTAway[hm].mean() / d.FTAway[hm].mean()
t = time.time()
lh, la = mk.lambda_uydur(P[:, 0], P[:, 1], P[:, 2], U, rho=RHO)
print("uyum", round(time.time() - t, 1), "sn;", len(d), "maç; FH, FA =", round(FH, 4), round(FA, 4))
pm = model.piyasalar(lh, la, RHO, FH, FA)
PM = np.full((len(d), len(veri.KODLAR)), np.nan)
for j, k in enumerate(veri.KODLAR):
    if k in pm:
        PM[:, j] = pm[k]
pickle.dump(dict(d=d, P=P, U=U, S=S, lh=lh, la=la, PM=PM, RHO=RHO, FH=FH, FA=FA), open("cache.pkl", "wb"))
print("kaydedildi")
