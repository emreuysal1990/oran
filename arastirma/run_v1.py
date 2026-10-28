import sys, time, pickle; sys.path[:0] = [".", ".."]
import numpy as np, pandas as pd
import veri, v1
c = pickle.load(open("cache.pkl", "rb"))
d, P, U, S = c["d"], c["P"], c["U"], c["S"]
ilk = (pd.Timestamp("2023-07-01") - pd.Timestamp("1970-01-01")).days
test_bas = (pd.Timestamp("2024-07-01") - pd.Timestamp("1970-01-01")).days
hedef = np.where(d.gun.values >= test_bas)[0]
print("test maçı:", len(hedef))
t = time.time()
tah, yn, yh = v1.v1_tahmin(d, S, P, U, hedef, ilk)
print("sure", round(time.time() - t, 1))
pickle.dump(dict(hedef=hedef, tah=tah, yn=yn, yh=yh), open("v1_sonuc.pkl", "wb"))
print("tah doluluk:", np.isfinite(tah).mean(), " sinyal sayısı:", ((yn >= 4) & (yh == yn) & (yn > 0)).sum())
