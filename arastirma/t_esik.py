"""Sinyal isabeti: eski sinyaller ile yeni modelin ihtimal eşikleri karşılaştırılır (aynı test maçları)."""
import sys, pickle; sys.path.insert(0, ".")
import numpy as np, pandas as pd
import veri
c = pickle.load(open("cache.pkl", "rb")); r = pickle.load(open("v1_sonuc.pkl", "rb")); yy = pickle.load(open("yeni_sonuc.pkl", "rb"))
d, S = c["d"], c["S"]
h = r["hedef"]; Y = S[h]; PN = yy["PMf"][h]; V1 = r["tah"]; yn, yh = r["yn"], r["yh"]
sig = (yn >= 4) & (yh == yn)
ok = ~np.isnan(Y) & ~np.isnan(PN)
nm = len(h)
print("test maçı", nm, "| geçerli (maç,pazar) çifti:", int(ok.sum()))
# 1) eski sinyaller
m = sig & ok & ~np.isnan(V1)
print("\n[1] ESKİ SİNYALLER   n=%d  (maç başına %.2f)  tuttu=%.3f  yeni modelin ort. ihtimali=%.3f  eski yöntemin vaadi=%.3f" % (m.sum(), m.sum() / nm, Y[m].mean(), PN[m].mean(), V1[m].mean()))
# 2) yeni modelin eşikleri (aynı 51 pazar)
print("\n[2] YENİ MODEL: ihtimal eşiği -> seçim sayısı, maç başına, tuttu")
for t in (0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95):
    k = ok & (PN >= t)
    print("   p >= %.2f : n=%6d  (maç başına %.2f)  tuttu=%.3f  ort ihtimal=%.3f" % (t, k.sum(), k.sum() / nm, Y[k].mean(), PN[k].mean()))
# 3) aynı sayıda seçim: en yüksek ihtimalli n_old çift
n_old = int(m.sum())
flat = np.where(ok)
pv = PN[flat]; order = np.argsort(-pv)[:n_old]
sel_y = Y[flat][order]
print("\n[3] AYNI SAYIDA SEÇİM (n=%d, en yüksek ihtimalliler): eşik p>=%.3f, tuttu=%.3f" % (n_old, pv[order].min(), sel_y.mean()))
# 3b) maç başına eşit sayıda: her maçta en yüksek ihtimalli k pazar (k=1..3)
for kk in (1, 2, 3):
    tot = 0; hit = 0
    for i in range(nm):
        idx = np.where(ok[i])[0]
        if len(idx) == 0: continue
        sec = idx[np.argsort(-PN[i, idx])[:kk]]
        tot += len(sec); hit += Y[i, sec].sum()
    print("    her maçta en yüksek ihtimalli %d pazar: n=%d tuttu=%.3f" % (kk, tot, hit / tot))
# 4) sinyalin ek bilgisi: aynı yeni-model ihtimal diliminde sinyal verilen vs verilmeyen
print("\n[4] AYNI İHTİMAL DİLİMİNDE: sinyal verilen - verilmeyen (tutma farkı)")
bins = np.array([0, .3, .4, .5, .6, .7, .8, .9, 1.0001])
tot_w = 0; tot_d = 0; tot_v = 0
for a, b in zip(bins[:-1], bins[1:]):
    s1 = ok & sig & (PN >= a) & (PN < b); s0 = ok & ~sig & (PN >= a) & (PN < b)
    if s1.sum() < 30: continue
    y1, y0 = Y[s1], Y[s0]
    df = y1.mean() - y0.mean(); se = np.sqrt(y1.var() / len(y1) + y0.var() / len(y0))
    print("   p in [%.1f,%.1f): sinyal n=%6d tuttu=%.3f | sinyalsiz n=%7d tuttu=%.3f | fark %+.3f (se %.3f)" % (a, b, s1.sum(), y1.mean(), s0.sum(), y0.mean(), df, se))
    tot_w += len(y1); tot_d += df * len(y1); tot_v += (se * len(y1)) ** 2
print("   ağırlıklı ortalama fark: %+.4f (yaklaşık se %.4f)" % (tot_d / tot_w, np.sqrt(tot_v) / tot_w))
# 5) para: gerçek oranı olan 5 pazar (Bet365), ihtimal dilimine göre ROI
dt = d.iloc[h]
print("\n[5] BET365 ORANLI 5 PAZAR: yeni model ihtimaline göre bahis getirisi (1 birim)")
pairs = (("MS1", 0, "OddHome"), ("MSX", 1, "OddDraw"), ("MS2", 2, "OddAway"), ("U25", 8, "Over25"), ("A25", 9, "Under25"))
rows = []
for ad, j, oc in pairs:
    od = dt[oc].values; y = Y[:, j]; p = PN[:, j]
    k = np.isfinite(od) & ~np.isnan(y) & ~np.isnan(p)
    rows.append(pd.DataFrame(dict(p=p[k], y=y[k], o=od[k])))
R = pd.concat(rows)
for a, b in ((0, .4), (.4, .5), (.5, .6), (.6, .7), (.7, .8), (.8, 1.01)):
    k = R[(R.p >= a) & (R.p < b)]
    if len(k) == 0: continue
    g = k.y * k.o - 1
    print("   p in [%.1f,%.1f): bahis=%6d  tuttu=%.3f  ROI=%+.2f%% (±%.1f)" % (a, b, len(k), k.y.mean(), g.mean() * 100, 1.96 * g.std() / np.sqrt(len(k)) * 100))
k = R[R.p >= 0.7]; g = k.y * k.o - 1
print("   p >= 0.7 hepsi: bahis=%d tuttu=%.3f ROI=%+.2f%% (±%.1f)" % (len(k), k.y.mean(), g.mean() * 100, 1.96 * g.std() / np.sqrt(len(k)) * 100))
