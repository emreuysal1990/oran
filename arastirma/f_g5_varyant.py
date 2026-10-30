import sys, pickle, warnings; sys.path.insert(0, "."); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import veri
G0 = pd.Timestamp("1970-01-01"); gn = lambda s: (pd.Timestamp(s) - G0).days
c = pickle.load(open("cache.pkl", "rb")); z = pickle.load(open("f_ozellik.pkl", "rb")); R = pickle.load(open("f_bagimsiz_son.pkl", "rb")); pay = pickle.load(open("f_pay.pkl", "rb"))["pay"]
gun = c["d"].gun.values; S = z["S"]; M0, MS = R["M0"], R["MS"]; KOD = veri.KODLAR
grup = np.array([veri.GRUP[k] for k in KOD])
FA, FB = (gn("2024-07-01"), gn("2025-07-01")), (gn("2025-07-01"), 10 ** 7)
UST = 1 / (1.30 * 1.19)
des = np.where(np.isfinite(pay), pay, 0) >= 0.899
band = ~np.isnan(S) & ~np.isnan(M0) & (M0 >= 0.55) & (M0 <= UST)
fk = np.clip(np.nan_to_num(MS - M0), -0.1, 0.1)
def dene(ad, skor, uygun):
    s_ = "  %-58s" % ad; tum = []
    for fad, f in (("A", FA), ("B", FB)):
        n = h = 0; p = 0.0; gl = []
        for g in np.unique(gun[(gun >= f[0]) & (gun < f[1])]):
            ii = np.where(gun == g)[0]; sec = []
            for i in ii:
                js = np.where(uygun[i])[0]
                if not len(js): continue
                j = js[np.argmax(skor[i, js])]; sec.append((skor[i, j], i, j))
            sec.sort(reverse=True); sec = sec[:5]
            if len(sec) < 5: continue
            t = [S[i, j] for _, i, j in sec]
            n += 5; h += int(sum(t)); p += sum(M0[i, j] for _, i, j in sec); gl.append(int(sum(t)))
        gl = np.array(gl); tum.append(h / n)
        s_ += " | %s: %.3f (ihtimal %.3f) %.2f/5 5'te5 %%%.1f gün %d" % (fad, h / n, p / n, gl.mean(), 100 * (gl == 5).mean(), len(gl))
    print(s_ + "  | ort %.3f" % np.mean(tum))
print("Günün 5'i varyantları (tahmini İddaa >= 1,30), iki sezon:")
dene("1) şu anki: ihtimal + 0,01 destek", M0 + 0.01 * des, band)
dene("2) destek payı 0,02", M0 + 0.02 * des, band)
dene("3) destek payı 0,03", M0 + 0.03 * des, band)
dene("4) önce destekliler (destek 0,10 öncelik)", M0 + 0.10 * des, band)
dene("5) yalnız destekli adaylar", M0, band & des)
dene("6) ihtimal + 0,02 destek + 0,2 × istatistik farkı", M0 + 0.02 * des + 0.2 * fk, band)
dene("7) ihtimal + 0,02 destek + 0,4 × istatistik farkı", M0 + 0.02 * des + 0.4 * fk, band)
dene("8) istatistik de onaylamalı (MS >= oran)", M0 + 0.02 * des, band & (np.nan_to_num(MS - M0, nan=-1) >= 0))
dene("9) destekli ve istatistik onaylı", M0, band & des & (np.nan_to_num(MS - M0, nan=-1) >= 0))
for g in ("Korner", "Kart", "Toplam gol", "Takım golü", "Maç sonucu", "İlk yarı"):
    dene("10) yalnız %s" % g, M0 + 0.02 * des, band & (grup == g)[None, :])
dene("11) korner ve kart hariç", M0 + 0.02 * des, band & ~np.isin(grup, ["Korner", "Kart"])[None, :])
