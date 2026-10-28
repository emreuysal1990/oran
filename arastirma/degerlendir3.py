"""Nihai değerlendirme (veri ufku 2023-07-01): her test dönemi için model yalnızca ondan ÖNCEKİ veriyle eğitilir (genişleyen pencere).
   Fold A: eğitim 2023-07 -> 2024-06, test 2024-07 -> 2025-06.  Fold B: eğitim 2023-07 -> 2025-06, test 2025-07 -> .
   Karşılaştırma: lig tabanı, v1 (benzer maç yöntemi, sayfadaki 2023 sonrası havuz) ve yeni model."""
import sys, json, pickle; sys.path[:0] = [".", ".."]
import numpy as np, pandas as pd
import veri, model, modelkit as mk, egit
G0 = pd.Timestamp("1970-01-01"); gn = lambda s: (pd.Timestamp(s) - G0).days

c = pickle.load(open("cache.pkl", "rb")); r1 = pickle.load(open("v1_sonuc.pkl", "rb")); q = pickle.load(open("taban.pkl", "rb"))
d, S, P, U, lh, la = c["d"], c["S"], c["P"], c["U"], c["lh"], c["la"]
gun = d.gun.values
KOD = veri.KODLAR
F = None
katlar = {}
for ad, bit in (("A", "2024-07-01"), ("B", "2025-07-01")):
    kat, (d2, P2, U2, lh2, la2, F2) = egit.egit(gn(bit), f"kat_{ad}.json", rapor=True)
    assert len(d2) == len(d)
    katlar[ad] = kat; F = F2
json.dump({"A": katlar["A"], "B": katlar["B"]}, open("kat_degerlendirme.json", "w"))
fold = {"A": (gn("2024-07-01"), gn("2025-07-01")), "B": (gn("2025-07-01"), 10 ** 7)}

PMf = np.full_like(S, np.nan)
for ad, (a, b) in fold.items():
    m = (gun >= a) & (gun < b)
    kat = katlar[ad]
    pm = model.piyasalar(lh[m], la[m], kat["rho"], kat["fh"], kat["fa"])
    blok = np.full((m.sum(), len(KOD)), np.nan)
    for j, k in enumerate(KOD):
        if k in pm: blok[:, j] = pm[k]
    for t, kodlar in (("c", [("K75U", 8, 1), ("K85U", 9, 1), ("K85A", 9, 0), ("K95U", 10, 1), ("K95A", 10, 0), ("K105U", 11, 1), ("K105A", 11, 0), ("K115A", 12, 0)]),
                      ("k", [("C25U", 3, 1), ("C35U", 4, 1), ("C35A", 4, 0), ("C45U", 5, 1), ("C45A", 5, 0), ("C55U", 6, 1), ("C55A", 6, 0)])):
        Fm = [F[i][t] for i in np.where(m)[0]]
        mu, ok = mk.kk_matris(Fm, lh[m], la[m], d.Division.values[m], kat[t])
        cum = np.cumsum(mk.nb_tablo(mu, kat[t]["alfa"]), 1)
        for kod, esik, ust in kodlar:
            p = 1 - cum[:, esik - 1]
            blok[:, KOD.index(kod)] = np.where(ok, p if ust else 1 - p, np.nan)
    PMf[m] = blok

h = r1["hedef"]
V1, B0 = r1["tah"], q["B0"][h]
Y = S[h]; PN = PMf[h]
rows = []
for j, k in enumerate(KOD):
    y = Y[:, j]; ok = ~np.isnan(y) & ~np.isnan(V1[:, j]) & ~np.isnan(B0[:, j]) & ~np.isnan(PN[:, j])
    lb, lv, ln = (veri.logkayip(x[ok, j], y[ok]) for x in (B0, V1, PN))
    dl = lv - ln
    rows.append(dict(kod=k, grup=veri.GRUP[k], n=int(ok.sum()), oran=y[ok].mean(), taban=lb.mean(), v1=lv.mean(), yeni=ln.mean(), kazanc_v1=dl.mean(), t=dl.mean() / (dl.std() / np.sqrt(ok.sum())),
                     kazanc_taban=(lb - ln).mean(), brier_v1=((V1[ok, j] - y[ok]) ** 2).mean(), brier_yeni=((PN[ok, j] - y[ok]) ** 2).mean(), brier_taban=((B0[ok, j] - y[ok]) ** 2).mean()))
T = pd.DataFrame(rows)
pd.set_option("display.width", 250)
Gp = T.groupby("grup").agg(pazar=("kod", "size"), taban=("taban", "mean"), v1=("v1", "mean"), yeni=("yeni", "mean"), brier_v1=("brier_v1", "mean"), brier_yeni=("brier_yeni", "mean")).round(4)
print(Gp)
npz = len(T)
print("\nTÜM %d PAZAR ortalama log kayıp: taban %.4f  v1 %.4f  yeni %.4f   | Brier: taban %.4f v1 %.4f yeni %.4f" % (npz, T.taban.mean(), T.v1.mean(), T.yeni.mean(), T.brier_taban.mean(), T.brier_v1.mean(), T.brier_yeni.mean()))
print("yeni v1'den iyi: %d/%d ; yeni tabandan iyi: %d/%d ; v1 tabandan iyi: %d/%d ; test maçı: %d" % ((T.kazanc_v1 > 0).sum(), npz, (T.kazanc_taban > 0).sum(), npz, (T.v1 < T.taban).sum(), npz, len(h)))
print(T[T.grup.isin(["Korner", "Kart"])].round(4).to_string(index=False))
pickle.dump(dict(PMf=PMf, T=T), open("yeni_sonuc.pkl", "wb"))
T.to_csv("degerlendirme_tablosu.csv", index=False)
