import sys, pickle, warnings; sys.path.insert(0, "."); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
G0 = pd.Timestamp("1970-01-01"); gn = lambda s: (pd.Timestamp(s) - G0).days
c = pickle.load(open("cache.pkl", "rb")); z = pickle.load(open("f_ozellik.pkl", "rb")); R = pickle.load(open("f_bagimsiz_son.pkl", "rb")); pay = pickle.load(open("f_pay.pkl", "rb"))["pay"]
gun = c["d"].gun.values; S = z["S"]; M0 = R["M0"]
N10 = z["V1N"]
des = (N10 >= 8) & (np.where(np.isfinite(pay), pay, 0) >= 0.899)
FA, FB = (gn("2024-07-01"), gn("2025-07-01")), (gn("2025-07-01"), 10 ** 7)
def dene(ad, esik, kosul):
    band = ~np.isnan(S) & ~np.isnan(M0) & (M0 >= 0.55) & (M0 <= 1 / (esik * 1.19))
    skor = M0 + 0.01 * des
    s_ = "  %-44s" % ad
    for fad, f in (("A", FA), ("B", FB)):
        gunler = np.unique(gun[(gun >= f[0]) & (gun < f[1])])
        n = h = 0; p = 0.0; say = []; hepsi = 0; dolu = 0
        for g in gunler:
            ii = np.where(gun == g)[0]; sec = []
            for i in ii:
                js = np.where(band[i] & kosul[i])[0]
                if not len(js): continue
                j = js[np.argmax(skor[i, js])]; sec.append((i, j))
            say.append(len(sec))
            if sec:
                dolu += 1; t = [S[i, j] for i, j in sec]; n += len(t); h += int(sum(t)); p += sum(M0[i, j] for i, j in sec); hepsi += all(t)
        say = np.array(say)
        s_ += " | %s: tuttu %.3f (ihtimal %.3f) günde %.1f tahmin, boş gün %%%d, günün hepsi tuttu %%%.0f" % (fad, h / max(n, 1), p / max(n, 1), say.mean(), 100 * (say == 0).mean(), 100 * hepsi / max(dolu, 1))
    print(s_)
tam = np.ones_like(M0, bool)
for esik in (1.30,):
    print("Tahmini İddaa >= %.2f, maç başına en iyi tahmin; güven kuralı:" % esik)
    dene("hepsi (her maçın en iyisi)", esik, tam)
    dene("ihtimal >= %62", esik, M0 >= 0.62)
    dene("ihtimal >= %63", esik, M0 >= 0.63)
    dene("ihtimal >= %64", esik, M0 >= 0.64)
    dene("destekli (10 benzer maçın 9+)", esik, des)
    dene("destekli ve ihtimal >= %60", esik, des & (M0 >= 0.60))
    dene("destekli ve ihtimal >= %62", esik, des & (M0 >= 0.62))
    dene("destekli ve ihtimal >= %63", esik, des & (M0 >= 0.63))
    dene("benzer maçların 10'u da tuttu", esik, (N10 >= 10) & (np.where(np.isfinite(pay), pay, 0) >= 0.999))
    dene("10/10 ve ihtimal >= %60", esik, (N10 >= 10) & (np.where(np.isfinite(pay), pay, 0) >= 0.999) & (M0 >= 0.60))
