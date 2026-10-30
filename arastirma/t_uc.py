"""Fotoğraflardaki yöntem: en yakın 3 benzer maçın 3'ünde de aynı olan sonuç 'tahmin'. Geçmişte ne kadar tuttu?"""
import sys, time, pickle; sys.path.insert(0, ".")
import numpy as np, pandas as pd
import veri, v1
c = pickle.load(open("cache.pkl", "rb")); yy = pickle.load(open("yeni_sonuc.pkl", "rb"))
d, P, U, S = c["d"], c["P"], c["U"], c["S"]
PN_all = yy["PMf"]
fh, fa, hh, ha = (d[k].values.astype(float) for k in ("FTHome", "FTAway", "HTHome", "HTAway"))
ad = list(veri.KODLAR); kol = [S]
def ekle(isim, v, gecerli):
    ad.append(isim); kol.append(np.where(gecerli, v.astype(float), np.nan)[:, None])
htok = ~np.isnan(hh)
sgn = lambda a, b: np.sign(a - b)
for i_, iy in ((1, "1"), (0, "X"), (-1, "2")):
    for m_, ms in ((1, "1"), (0, "X"), (-1, "2")):
        ekle("IYMS " + iy + "/" + ms, (sgn(hh, ha) == i_) & (sgn(fh, fa) == m_), htok)
for a in range(4):
    for b in range(4):
        ekle("Skor %d-%d" % (a, b), (fh == a) & (fa == b), np.ones(len(d), bool))
for a, b in ((0, 0), (1, 0), (0, 1), (1, 1), (2, 0), (0, 2)):
    ekle("IY skor %d-%d" % (a, b), (hh == a) & (ha == b), htok)
tg = fh + fa
for a, b in ((0, 1), (2, 3), (4, 5)):
    ekle("Top. gol %d-%d" % (a, b), (tg >= a) & (tg <= b), np.ones(len(d), bool))
SX = np.hstack(kol); NP = SX.shape[1]
ilk = (pd.Timestamp("2023-07-01") - pd.Timestamp("1970-01-01")).days
test_bas = (pd.Timestamp("2024-07-01") - pd.Timestamp("1970-01-01")).days
hedef = np.where(d.gun.values >= test_bas)[0]
t = time.time()
sonuc = {}
for maks, mn in ((3, 3), (10, 4)):
    tah, yn, yh = v1.v1_tahmin(d, SX, P, U, hedef, ilk, maks=maks, minimum=mn)
    sonuc[maks] = (tah, yn, yh)
print("süre", round(time.time() - t, 1), "sn; test maçı", len(hedef))
Y = SX[hedef]; nm = len(hedef)
# ligin o güne kadarki oranı yerine: geniş penceredeki tahmin (tah) ve 51 pazarda yeni model ihtimali
pickle.dump(dict(ad=ad, hedef=hedef, Y=Y, sonuc=sonuc), open("uc_sonuc.pkl", "wb"))
for maks, mn in ((3, 3), (10, 4)):
    tah, yn, yh = sonuc[maks]
    sig = (yn >= mn) & (yh == yn) & ~np.isnan(Y)
    print("\n=== en yakın %d maç, en az %d maçın hepsi tuttu: sinyal %d (maç başına %.2f), tuttu %.3f, ort. tahmini %.3f"
          % (maks, mn, sig.sum(), sig.sum() / nm, Y[sig].mean(), np.nanmean(tah[sig])))
    # pazarın genel tutma oranına göre dilimler (tah = geniş pencere + lig ortalaması)
    for a, b in ((0, .15), (.15, .3), (.3, .5), (.5, .7), (.7, .85), (.85, 1.01)):
        k = sig & (tah >= a) & (tah < b)
        if k.sum(): print("   tahmini [%.2f,%.2f): sinyal %6d  maç başına %.2f  tuttu %.3f  (ort. tahmini %.3f)" % (a, b, k.sum(), k.sum() / nm, Y[k].mean(), tah[k].mean()))
    rows = []
    for j, a in enumerate(ad):
        k = sig[:, j]
        if k.sum() >= 30: rows.append((a, int(k.sum()), Y[k, j].mean(), np.nanmean(tah[k, j]), np.nanmean(Y[:, j])))
    R = pd.DataFrame(rows, columns=["pazar", "sinyal", "tuttu", "tahmini", "genel"])
    R["fark"] = R.tuttu - R.tahmini
    if maks == 3:
        sec = ["MSX", "MS1", "IYX", "KGV", "U35", "A15", "IYMS X/1", "IYMS X/X", "IYMS 1/1", "IYMS 2/2", "Skor 1-1", "Skor 2-1", "Skor 1-0", "Skor 2-2", "IY skor 0-0", "IY skor 1-0", "Top. gol 2-3", "K75U", "C45A"]
        print(R[R.pazar.isin(sec)].round(3).to_string(index=False))
