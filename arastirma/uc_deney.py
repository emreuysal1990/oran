import sys, pickle, time; sys.path.insert(0, ".")
import numpy as np, pandas as pd
import uc3
NM = None
def ozet(R, ad, esik=1/1.5):
    global NM
    k = R[R.tah <= esik]
    nm = NM
    s = lambda x: (x.y.mean(), x.tah.mean(), x.y.mean() - x.tah.mean(), np.sqrt(x.y.var() / max(len(x), 1)))
    y, t, a, se = s(k)
    ss = [s(k[k.sezon == z]) for z in sorted(k.sezon.unique())]
    print("%-28s tahmin/maç %.2f | tuttu %.3f  bekl %.3f  fark %+.3f (±%.3f) | sezonlar: %s" % (ad, len(k) / nm, y, t, a, 1.96 * se,
          "  ".join("%+.3f" % x[2] for x in ss)))
R0 = uc3.calistir(3)
NM = (uc3.gun >= uc3.TEST_BAS).sum()
print("test maçı:", NM, " sezonlar:", sorted(R0.sezon.unique()))
print("\n[1] Mevcut (N=3, sadece oran), adil oran eşiğine göre")
for o in (1.0, 1.3, 1.5, 1.7, 2.0, 2.5, 3.0):
    ozet(R0, "adil oran >= %.1f" % o, 1 / o)
print("\n[2] Benzer maç sayısı (adil oran >= 1,5)")
RS = {}
for N in (2, 3, 4, 5, 7, 10):
    RS[N] = R = uc3.calistir(N); ozet(R, "N=%d" % N)
print("\n[3] Lig sırası benzerliği (N=3, adil >= 1,5)")
for w in (0.1, 0.25, 0.5, 1.0):
    R = uc3.calistir(3, w_sira=w); RS[("s", w)] = R; ozet(R, "N=3 sıra ağırlığı %.2f" % w)
for w in (0.25, 0.5):
    R = uc3.calistir(5, w_sira=w); RS[("s5", w)] = R; ozet(R, "N=5 sıra ağırlığı %.2f" % w)
pickle.dump(RS, open("uc_deney.pkl", "wb"))
