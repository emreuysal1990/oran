"""Formül araştırması - özellik tablosu. Her maç için yalnızca maçtan ÖNCEKİ bilgiler:
   1) model ihtimali (fold katsayılarıyla; korner/kart negatif binom),
   2) benzer maçlar (v1: geniş pencere tahmini, en yakın 10'da tutma payı),
   3) takım formu (son 8 maç: gol, isabetli şut, şut, korner, kart, puan)."""
import sys, json, pickle, time; sys.path.insert(0, ".")
import numpy as np, pandas as pd
import veri, model, modelkit as mk, egit, v1
G0 = pd.Timestamp("1970-01-01"); gn = lambda s: (pd.Timestamp(s) - G0).days
c = pickle.load(open("cache.pkl", "rb"))
d, S, P, U, lh, la = c["d"], c["S"], c["P"], c["U"], c["lh"], c["la"]
n = len(d); gun = d.gun.values; KOD = veri.KODLAR
katlar = json.load(open("kat_degerlendirme.json"))
_, (d2, P2, U2, lh2, la2, F) = egit.egit(10 ** 6, None, rapor=False)

def pm_hesapla(kat):
    pm = model.piyasalar(lh, la, kat["rho"], kat["fh"], kat["fa"])
    blok = np.full((n, len(KOD)), np.nan)
    for j, k in enumerate(KOD):
        if k in pm: blok[:, j] = pm[k]
    for t, kodlar in (("c", [("K75U", 8, 1), ("K85U", 9, 1), ("K85A", 9, 0), ("K95U", 10, 1), ("K95A", 10, 0), ("K105U", 11, 1), ("K105A", 11, 0), ("K115A", 12, 0)]),
                      ("k", [("C25U", 3, 1), ("C35U", 4, 1), ("C35A", 4, 0), ("C45U", 5, 1), ("C45A", 5, 0), ("C55U", 6, 1), ("C55A", 6, 0)])):
        mu, ok = mk.kk_matris([F[i][t] for i in range(n)], lh, la, d.Division.values, kat[t])
        cum = np.cumsum(mk.nb_tablo(mu, kat[t]["alfa"]), 1)
        for kod, esik, ust in kodlar:
            p = 1 - cum[:, esik - 1]; blok[:, KOD.index(kod)] = np.where(ok, p if ust else 1 - p, np.nan)
    return blok
t0 = time.time()
PM = {ad: pm_hesapla(katlar[ad]) for ad in ("A", "B")}
print("model ihtimalleri", round(time.time() - t0, 1), "sn")

# benzer maçlar: ilk 90 gün hariç tüm maçlar
t0 = time.time()
hedef = np.where(gun >= gn("2023-09-15"))[0]
tah, yn, yh = v1.v1_tahmin(d, S, P, U, hedef, gn("2023-07-01"))
V1T = np.full((n, len(KOD)), np.nan); V1N = np.zeros((n, len(KOD))); V1H = np.zeros((n, len(KOD)))
V1T[hedef], V1N[hedef], V1H[hedef] = tah, yn, yh
print("benzer maçlar", round(time.time() - t0, 1), "sn")

# takım formu (son 8 maç, maçtan önce; aynı gün maçlar birbirini görmez)
PEN = 8
kol = {"gf": ("FTHome", "FTAway"), "sot": ("HomeTarget", "AwayTarget"), "sh": ("HomeShots", "AwayShots"),
       "kor": ("HomeCorners", "AwayCorners"), "kart": (None, None)}
kart_h = (d.HomeYellow + d.HomeRed).values; kart_a = (d.AwayYellow + d.AwayRed).values
from collections import defaultdict, deque
hist = defaultdict(lambda: deque(maxlen=PEN))
ad = ["gf_for", "gf_ag", "sot_for", "sot_ag", "sh_for", "sh_ag", "kor_for", "kor_ag", "kart_for", "kart_ag", "puan"]
FORM = np.full((n, 2, len(ad)), np.nan)
order = np.argsort(gun, kind="stable"); i = 0
while i < n:
    j = i
    while j < n and gun[order[j]] == gun[order[i]]: j += 1
    for r in order[i:j]:
        for s_, tk in ((0, d.HomeTeam.values[r]), (1, d.AwayTeam.values[r])):
            h = hist[(d.Division.values[r], tk)]
            if len(h) >= 4: FORM[r, s_] = np.nanmean(np.array(h, dtype=float), 0)
    for r in order[i:j]:
        x = lambda a, b: (float(d[a].values[r]) if a and not pd.isna(d[a].values[r]) else np.nan)
        H = dict(gf=(d.FTHome.values[r], d.FTAway.values[r]), sot=(x("HomeTarget", 0), x("AwayTarget", 0)),
                 sh=(x("HomeShots", 0), x("AwayShots", 0)), kor=(x("HomeCorners", 0), x("AwayCorners", 0)), kart=(kart_h[r], kart_a[r]))
        for s_, tk in ((0, d.HomeTeam.values[r]), (1, d.AwayTeam.values[r])):
            o = 1 - s_
            v = [H["gf"][s_], H["gf"][o], H["sot"][s_], H["sot"][o], H["sh"][s_], H["sh"][o], H["kor"][s_], H["kor"][o], H["kart"][s_], H["kart"][o]]
            gfs, gas = H["gf"][s_], H["gf"][o]
            v.append(3.0 if gfs > gas else 1.0 if gfs == gas else 0.0)
            hist[(d.Division.values[r], d.HomeTeam.values[r] if s_ == 0 else d.AwayTeam.values[r])].append(v)
    i = j
print("form doluluk:", np.isfinite(FORM[:, :, 0]).mean().round(3), " isabetli şut doluluk:", np.isfinite(FORM[:, :, 2]).mean().round(3))
pickle.dump(dict(PM=PM, V1T=V1T, V1N=V1N, V1H=V1H, FORM=FORM, FORM_AD=ad, S=S), open("f_ozellik.pkl", "wb"))
print("kaydedildi")
