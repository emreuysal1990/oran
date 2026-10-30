"""Ortak sonuç tahminlerinde ihtimal kaynağı: geniş pencere (sayfadaki 'tahmini ihtimal') mı, oranlardan gol modeli mi?"""
import sys, pickle, json; sys.path.insert(0, ".")
import numpy as np, pandas as pd
import uc3, modelkit as mk, veri
from math import lgamma
c = pickle.load(open("cache.pkl", "rb")); yy = pickle.load(open("yeni_sonuc.pkl", "rb"))
lh, la = c["lh"], c["la"]; PMf = yy["PMf"]; KOD51 = list(veri.KODLAR)
kat = json.load(open("../katsayilar.json")); FH, FA = kat["fh"], kat["fa"]
G = 13; K_ = np.arange(G); LF = np.array([lgamma(k + 1) for k in range(G)])
pois = lambda lam: np.exp(-lam[:, None] + K_[None, :] * np.log(lam)[:, None] - LF[None, :])

R = uc3.calistir(3, haric=True)
print("tahmin", len(R), " tutma", R.y.mean().round(4), " ort tah (hariç)", R.tah.mean().round(4))
i = R.mac.values; kod = R.kod.values
M = mk.matris(lh[i], la[i])                                   # FT skor matrisi
H1 = pois(lh[i] * FH)[:, :, None] * pois(la[i] * FA)[:, None, :]   # İY skor matrisi (bağımsız)
H2 = pois(lh[i] * (1 - FH))[:, :, None] * pois(la[i] * (1 - FA))[:, None, :]  # 2. yarı
gh_, ga_ = np.meshgrid(K_, K_, indexing="ij")
p = np.full(len(R), np.nan)
s3 = lambda a, b: np.where(a > b, "1", np.where(a == b, "X", "2"))
MSg = s3(gh_, ga_)
def ft(mask_fn):
    return lambda r: (M[r] * mask_fn(gh_, ga_)).sum()
for r in range(len(R)):
    k = kod[r]; Mi = M[r]
    if k.startswith("SK"):
        a, b = map(int, k[2:].split("-")); p[r] = Mi[a, b] if a < G and b < G else 0
    elif k.startswith("MS"): p[r] = Mi[MSg == k[2:]].sum()
    elif k.startswith("CS"): p[r] = Mi[np.isin(MSg, list(k[2:]))].sum()
    elif k.startswith("GA"):
        t = gh_ + ga_; lo, hi = {"0-1": (0, 1), "2-3": (2, 3), "4-5": (4, 5), "6+": (6, 99)}[k[2:]]; p[r] = Mi[(t >= lo) & (t <= hi)].sum()
    elif k.startswith("KG"): v = (gh_ > 0) & (ga_ > 0); p[r] = Mi[v].sum() if k[2:] == "Var" else Mi[~v].sum()
    elif k[0] == "H" and k[1:3].isdigit():
        ev, dep, h = int(k[1]), int(k[2]), k[3]; p[r] = Mi[s3(gh_ + ev, ga_ + dep) == h].sum()
    elif k[:2] in ("AU", "EV", "DP"):
        yon, cz = k[2], float(k[3:]); x = {"AU": gh_ + ga_, "EV": gh_, "DP": ga_}[k[:2]]
        p[r] = Mi[x > cz].sum() if yon == "U" else Mi[x < cz].sum()
    elif k.startswith("IS"):
        a, b = map(int, k[2:].split("-")); p[r] = H1[r, a, b] / H1[r].sum()
    elif k.startswith("IY"): p[r] = (H1[r] * (MSg == k[2:])).sum() / H1[r].sum()
    elif k.startswith("IG"):
        yon, cz = k[2], float(k[3:]); x = gh_ + ga_; h1 = H1[r] / H1[r].sum(); p[r] = h1[x > cz].sum() if yon == "U" else h1[x < cz].sum()
    elif k.startswith("IM"):
        iy, ms = k[2:].split("/"); h1 = H1[r] / H1[r].sum(); h2 = H2[r] / H2[r].sum(); tot = 0.0
        for a in range(7):
            for b in range(7):
                if h1[a, b] < 1e-9 or s3(np.array(a), np.array(b)) != iy: continue
                for x in range(7):
                    for y_ in range(7):
                        if s3(np.array(a + x), np.array(b + y_)) == ms: tot += h1[a, b] * h2[x, y_]
        p[r] = tot
    elif k[:2] in ("KO", "KA"):
        yon, cz = k[2], k[3:]
        m51 = ("K" if k[:2] == "KO" else "C") + cz.replace(".", "") + yon
        if m51 in KOD51: p[r] = PMf[i[r], KOD51.index(m51)]
R["model"] = p
ok = R.model.notna() & R.tah.notna()
Z = R[ok].copy(); Z["model"] = Z.model.clip(1e-4, 1 - 1e-4); Z["tah"] = Z.tah.clip(1e-4, 1 - 1e-4)
ll = lambda q: -(Z.y * np.log(q) + (1 - Z.y) * np.log(1 - q)).mean()
print("karşılaştırılan tahmin:", ok.sum(), "/", len(R))
print("log kayıp  tahmini ihtimal: %.4f   model: %.4f" % (ll(Z.tah), ll(Z.model)))
print("Brier      tahmini ihtimal: %.4f   model: %.4f" % (((Z.y - Z.tah) ** 2).mean(), ((Z.y - Z.model) ** 2).mean()))
print("\ntüre göre (adil oran >= 1,5 olanlar, model ihtimaline göre):")
W = Z[Z.model <= 1 / 1.5]
for t, g in W.groupby("tur"):
    print("  %-16s n=%6d tuttu %.3f | model %.3f (fark %+.3f) | tahmini %.3f (fark %+.3f) | log kayıp model %.4f tahmini %.4f" % (
        t, len(g), g.y.mean(), g.model.mean(), g.y.mean() - g.model.mean(), g.tah.mean(), g.y.mean() - g.tah.mean(),
        -(g.y * np.log(g.model) + (1 - g.y) * np.log(1 - g.model)).mean(), -(g.y * np.log(g.tah) + (1 - g.y) * np.log(1 - g.tah)).mean()))
print("\nkalibrasyon (model):")
for a, b in ((0, .1), (.1, .2), (.2, .3), (.3, .4), (.4, .5), (.5, .6), (.6, .7), (.7, .8), (.8, .9), (.9, 1.01)):
    g = Z[(Z.model >= a) & (Z.model < b)]
    if len(g): print("  [%.1f,%.1f) n=%6d tuttu %.3f model %.3f | tahmini %.3f" % (a, b, len(g), g.y.mean(), g.model.mean(), g.tah.mean()))
pickle.dump(R, open("uc_model.pkl", "wb"))
