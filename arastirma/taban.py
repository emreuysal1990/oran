"""Lig taban oranı (v1'deki 'lo'): sayfadaki geçmişten (2023-07-01 sonrası), kendinden önceki günlere kadar, >=30 maç. Çıktı: taban.pkl"""
import sys, pickle; sys.path[:0] = [".", ".."]
import numpy as np, pandas as pd
c = pickle.load(open("cache.pkl", "rb"))
d, S = c["d"], c["S"]
gun, lig = d.gun.values, d.Division.values
B0 = np.full_like(S, np.nan)
for lg in np.unique(lig):
    idx = np.where(lig == lg)[0]
    s = np.where(np.isnan(S[idx]), 0, S[idx]); v = (~np.isnan(S[idx])).astype(float)
    cn = np.vstack([np.zeros((1, S.shape[1])), np.cumsum(v, 0)]); ch = np.vstack([np.zeros((1, S.shape[1])), np.cumsum(s, 0)])
    b = np.searchsorted(gun[idx], gun[idx], side="left")
    with np.errstate(invalid="ignore", divide="ignore"):
        B0[idx] = np.where(cn[b] >= 30, ch[b] / np.maximum(cn[b], 1), np.nan)
pickle.dump(dict(B0=B0), open("taban.pkl", "wb"))
print("taban hazır", B0.shape)
