"""Oranlardan bağımsız özellikler (yalnızca maçtan önceki bilgi): kendi Elo, clubelo, genel ve iç saha/deplasman formu, dinlenme, lig seviyesi."""
import sys, pickle, math; sys.path.insert(0, ".")
import numpy as np, pandas as pd
from collections import defaultdict, deque
c = pickle.load(open("cache.pkl", "rb")); z = pickle.load(open("f_ozellik.pkl", "rb"))
d = c["d"]; n = len(d); gun = d.gun.values
H, Aw, L = d.HomeTeam.values, d.AwayTeam.values, d.Division.values
fh, fa = d.FTHome.values.astype(float), d.FTAway.values.astype(float)
nz = lambda x: np.where(pd.isna(x), np.nan, x).astype(float)
sot_h, sot_a = nz(d.HomeTarget.values), nz(d.AwayTarget.values)
sh_h, sh_a = nz(d.HomeShots.values), nz(d.AwayShots.values)
kor_h, kor_a = nz(d.HomeCorners.values), nz(d.AwayCorners.values)
kart_h = nz((d.HomeYellow + d.HomeRed).values); kart_a = nz((d.AwayYellow + d.AwayRed).values)
hh, ha = nz(d.HTHome.values), nz(d.HTAway.values)
order = np.argsort(gun, kind="stable")
# --- kendi Elo (lig içinde; gol farkı çarpanlı; ev avantajı ligden öğrenilir)
elo = defaultdict(lambda: 1500.0); ev_av = defaultdict(lambda: 60.0)
E = np.full((n, 3), np.nan)            # ev elo, dep elo, beklenen ev skoru
son_mac = {}; DIN = np.full((n, 2), np.nan)
# --- iç saha / deplasman formu (son 6)
ic = defaultdict(lambda: deque(maxlen=6)); dis = defaultdict(lambda: deque(maxlen=6))
VF = np.full((n, 2, 6), np.nan)        # [ev takımın iç saha, dep takımın deplasman] x [atılan, yenen, isabetli şut +, isabetli şut -, puan, İY gol]
lig_g = defaultdict(lambda: deque(maxlen=300)); LG = np.full((n, 4), np.nan)   # lig: gol, korner, kart, İY gol ort.
i = 0
while i < n:
    j = i
    while j < n and gun[order[j]] == gun[order[i]]: j += 1
    for r in order[i:j]:
        kh, ka = (L[r], H[r]), (L[r], Aw[r])
        E[r] = [elo[kh], elo[ka], 1 / (1 + 10 ** (-(elo[kh] + ev_av[L[r]] - elo[ka]) / 400))]
        for s_, k in ((0, kh), (1, ka)):
            if k in son_mac: DIN[r, s_] = min(gun[r] - son_mac[k], 21)
        for s_, dq in ((0, ic[kh]), (1, dis[ka])):
            if len(dq) >= 3: VF[r, s_] = np.nanmean(np.array(dq, float), 0)
        lg = lig_g[L[r]]
        if len(lg) >= 50: LG[r] = np.nanmean(np.array(lg, float), 0)
    for r in order[i:j]:
        kh, ka = (L[r], H[r]), (L[r], Aw[r])
        sonuc = 1.0 if fh[r] > fa[r] else 0.5 if fh[r] == fa[r] else 0.0
        bek = E[r, 2]; fark = abs(fh[r] - fa[r]); carp = math.log(fark + 1) + 1 if fark > 0 else 1.0
        dl = 20 * carp * (sonuc - bek)
        elo[kh] += dl; elo[ka] -= dl
        ev_av[L[r]] += 0.5 * (sonuc - bek)     # ev avantajı yavaşça uyarlanır
        son_mac[kh] = son_mac[ka] = gun[r]
        p_h = 3 if fh[r] > fa[r] else 1 if fh[r] == fa[r] else 0; p_a = 3 if fa[r] > fh[r] else 1 if fh[r] == fa[r] else 0
        ic[kh].append([fh[r], fa[r], sot_h[r], sot_a[r], p_h, hh[r]])
        dis[ka].append([fa[r], fh[r], sot_a[r], sot_h[r], p_a, ha[r]])
        lig_g[L[r]].append([fh[r] + fa[r], kor_h[r] + kor_a[r], kart_h[r] + kart_a[r], hh[r] + ha[r]])
    i = j
FORM = z["FORM"]                                   # genel form son 8: 11 özellik x 2 takım
celo = np.column_stack([nz(d.HomeElo.values), nz(d.AwayElo.values)])
X = np.column_stack([E[:, 0] - E[:, 1], E[:, 2], E[:, 0], E[:, 1],
                     celo[:, 0] - celo[:, 1], celo[:, 0], celo[:, 1],
                     FORM.reshape(n, -1), VF.reshape(n, -1), DIN, LG,
                     nz(d.Form3Home.values), nz(d.Form5Home.values), nz(d.Form3Away.values), nz(d.Form5Away.values)])
ad = (["elo_fark", "elo_bek", "elo_ev", "elo_dep", "celo_fark", "celo_ev", "celo_dep"] + [f"form8_{t}_{k}" for t in ("ev", "dep") for k in z["FORM_AD"]] +
      [f"vf_{t}_{k}" for t in ("ev_ic", "dep_dis") for k in ("gf", "ga", "sotf", "sota", "puan", "iygol")] + ["dinlenme_ev", "dinlenme_dep"] +
      ["lig_gol", "lig_kor", "lig_kart", "lig_iygol", "form3_ev", "form5_ev", "form3_dep", "form5_dep"])
lig_kod = pd.Categorical(L).codes
print("özellik:", X.shape, " elo doluluk:", np.isfinite(X[:, 0]).mean().round(3), " clubelo:", np.isfinite(X[:, 4]).mean().round(3))
# Elo'nun tek başına MS tahmini (bilgi var mı?)
ok = gun >= (pd.Timestamp("2024-07-01") - pd.Timestamp("1970-01-01")).days
pickle.dump(dict(X=X, ad=ad, lig=lig_kod), open("f_bagimsiz.pkl", "wb"))
print("kaydedildi")
