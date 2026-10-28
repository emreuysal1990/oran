"""Eski sinyaller nasıl daha sık tutar? Sinyalleri yakın maç sayısı, eski tahmin ve yeni model ihtimaliyle süzme."""
import sys, pickle; sys.path.insert(0, ".")
import numpy as np
c = pickle.load(open("cache.pkl", "rb")); r = pickle.load(open("v1_sonuc.pkl", "rb")); yy = pickle.load(open("yeni_sonuc.pkl", "rb"))
S = c["S"]; h = r["hedef"]; Y = S[h]; PN = yy["PMf"][h]; V1 = r["tah"]; yn, yh = r["yn"], r["yh"]
nm = len(h)
ok = ~np.isnan(Y) & ~np.isnan(PN) & ~np.isnan(V1)
sig = (yn >= 4) & (yh == yn) & ok
def rap(ad, k):
    n = int(k.sum()); y = Y[k]
    print("  %-42s n=%6d  maç başına %.2f  tuttu=%.3f (±%.3f)" % (ad, n, n / nm, y.mean(), 1.96 * y.std() / np.sqrt(max(n, 1))))
print("test maçı", nm)
rap("eski sinyal (4+ maçın hepsi)", sig)
print("\n[A] yakın maç sayısına göre (hepsi tuttu)")
for n in range(4, 11): rap("%d/%d" % (n, n), sig & (yn == n))
rap("8/8 ve üstü", sig & (yn >= 8)); rap("10/10", sig & (yn == 10))
print("\n[B] eski sinyal + eski sayfanın 'tahmini ihtimali' en az")
for t in (0.70, 0.75, 0.80, 0.85, 0.90): rap("tahmini >= %.2f" % t, sig & (V1 >= t))
print("\n[C] eski sinyal + yeni modelin ihtimali en az")
for t in (0.60, 0.70, 0.75, 0.80, 0.85, 0.90): rap("model >= %.2f" % t, sig & (PN >= t))
print("\n[D] 10/10 + model")
for t in (0.70, 0.80, 0.85): rap("10/10 ve model >= %.2f" % t, sig & (yn == 10) & (PN >= t))
print("\n[E] model >= t (sinyal şartı olmadan) karşılaştırma")
for t in (0.75, 0.80, 0.85, 0.90): rap("yalnız model >= %.2f" % t, ok & (PN >= t))
print("\n[F] eski sinyal ama model < 0.60 (yani oranlar zayıf diyor)")
rap("sinyal & model < 0.60", sig & (PN < 0.60)); rap("sinyal & model < 0.50", sig & (PN < 0.50))
