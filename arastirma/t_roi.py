import sys, pickle; sys.path[:0] = [".", ".."]
import numpy as np, pandas as pd
import veri
c = pickle.load(open("cache.pkl", "rb")); r = pickle.load(open("v1_sonuc.pkl", "rb"))
d, S, P, U = c["d"], c["S"], c["P"], c["U"]
h = r["hedef"]
dt = d.iloc[h]
Y = S[h]
def say(ad, y, odds, m):
    k = m & np.isfinite(odds) & ~np.isnan(y)
    if k.sum() == 0: return
    g = y[k] * odds[k] - 1
    se = g.std() / np.sqrt(k.sum())
    print(f"{ad:45s} bahis={k.sum():6d}  isabet={y[k].mean():.3f}  ROI={g.mean()*100:+6.2f}%  (±{1.96*se*100:.1f})")
print("== Tüm maçlara düz bahis (test dönemi 2024-07 → 2026-09) ==")
for ad, j, oc, mc in (("MS1", 0, "OddHome", "MaxHome"), ("MSX", 1, "OddDraw", "MaxDraw"), ("MS2", 2, "OddAway", "MaxAway"), ("2,5 Üst", 8, "Over25", "MaxOver25"), ("2,5 Alt", 9, "Under25", "MaxUnder25")):
    y = Y[:, j]; ones = np.ones(len(h), bool)
    say(ad + " @ Bet365", y, dt[oc].values, ones); say(ad + " @ en yüksek oran", y, dt[mc].values, ones)
print("\n== v1 sinyalli bahisler (4+ benzer maçta hepsi tuttu), Bet365 oranından ==")
yn, yh = r["yn"], r["yh"]; sig = (yn >= 4) & (yh == yn)
for ad, j, oc in (("MS1", 0, "OddHome"), ("MSX", 1, "OddDraw"), ("MS2", 2, "OddAway"), ("2,5 Üst", 8, "Over25"), ("2,5 Alt", 9, "Under25")):
    say(ad + " sinyal", Y[:, j], dt[oc].values, sig[:, j])
tum = []
for ad, j, oc in (("MS1", 0, "OddHome"), ("MSX", 1, "OddDraw"), ("MS2", 2, "OddAway"), ("U25", 8, "Over25"), ("A25", 9, "Under25")):
    m = sig[:, j] & np.isfinite(dt[oc].values) & ~np.isnan(Y[:, j]); tum.append(Y[m, j] * dt[oc].values[m] - 1)
t = np.concatenate(tum); print(f"{'5 pazar birlikte, sinyalli':45s} bahis={len(t):6d}  ROI={t.mean()*100:+6.2f}% (±{1.96*t.std()/np.sqrt(len(t))*100:.1f})")
print("\n== Favori-uzun vade: Bet365 MS oranı aralığına göre ROI (ev+beraberlik+dep hepsi) ==")
oc = np.concatenate([dt.OddHome.values, dt.OddDraw.values, dt.OddAway.values]); yy = np.concatenate([Y[:, 0], Y[:, 1], Y[:, 2]])
for a, b in ((1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 5.0), (5.0, 10.0), (10.0, 100.0)):
    m = (oc >= a) & (oc < b); g = yy[m] * oc[m] - 1
    print(f"  oran {a:>4}-{b:<5}: bahis={m.sum():6d} ROI={g.mean()*100:+6.2f}% (±{1.96*g.std()/np.sqrt(m.sum())*100:.1f})")
