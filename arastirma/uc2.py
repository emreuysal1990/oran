"""'Benzer N maç, hepsinde aynı' yönteminin varyantları. Sayfadaki JS mantığının Python karşılığı + lig sırası benzerliği."""
import sys, pickle, time; sys.path.insert(0, ".")
import numpy as np, pandas as pd

c = pickle.load(open("cache.pkl", "rb"))
d, P, U = c["d"], c["P"], c["U"]
n = len(d)
gun = d.gun.values; lig = d.Division.values
fh, fa = d.FTHome.values.astype(int), d.FTAway.values.astype(int)
hh, ha = d.HTHome.values, d.HTAway.values
iyok = ~np.isnan(hh) & ~np.isnan(ha)
hh = np.where(iyok, hh, -1).astype(int); ha = np.where(iyok, ha, -1).astype(int)
kor = (d.HomeCorners + d.AwayCorners).values; kart = (d.HomeYellow + d.AwayYellow + d.HomeRed + d.AwayRed).values

# ---------------------------------------------------------------- lig sırası (maçtan önce), sezon içinde
def siralar():
    rh = np.full(n, np.nan); ra = np.full(n, np.nan)
    for (lg, sz), grp in d.groupby(["Division", "sezon"]):
        idx = grp.sort_values(["gun"]).index.values
        takimlar = sorted(set(grp.HomeTeam) | set(grp.AwayTeam)); T = len(takimlar); ti = {t: k for k, t in enumerate(takimlar)}
        pts = np.zeros(T); gd = np.zeros(T); gf = np.zeros(T); oyn = np.zeros(T)
        g = gun[idx]; i = 0
        while i < len(idx):
            j = i
            while j < len(idx) and g[j] == g[i]: j += 1
            sira = np.lexsort((-gf, -gd, -pts))       # en iyi önce
            rank = np.empty(T); rank[sira] = np.arange(T)
            for r in idx[i:j]:
                h, a = ti[d.HomeTeam[r]], ti[d.AwayTeam[r]]
                if oyn.sum() / T >= 3:                   # her takım ortalama 3+ maç oynadıysa sıra anlamlı
                    rh[r] = rank[h] / (T - 1); ra[r] = rank[a] / (T - 1)
            for r in idx[i:j]:
                h, a = ti[d.HomeTeam[r]], ti[d.AwayTeam[r]]
                x, y = fh[r], fa[r]
                pts[h] += 3 if x > y else 1 if x == y else 0; pts[a] += 3 if y > x else 1 if x == y else 0
                gd[h] += x - y; gd[a] += y - x; gf[h] += x; gf[a] += y; oyn[h] += 1; oyn[a] += 1
            i = j
    return rh, ra
t0 = time.time(); RH, RA = siralar(); print("sıralar", round(time.time() - t0, 1), "sn; dolu", np.isfinite(RH).mean().round(3))

# ---------------------------------------------------------------- tahminler (JS ucTahminler ile aynı)
s3 = lambda a, b: "1" if a > b else ("X" if a == b else "2")
aralik = lambda x: "0-1" if x <= 1 else "2-3" if x <= 3 else "4-5" if x <= 5 else "6+"
def nitel(i):
    """maç i için kategorik değerler ve sayısal değerler"""
    v = {"SK": f"{fh[i]}-{fa[i]}", "MS": s3(fh[i], fa[i]), "GA": aralik(fh[i] + fa[i]), "KG": "Var" if fh[i] > 0 and fa[i] > 0 else "Yok"}
    if iyok[i]:
        v["IS"] = f"{hh[i]}-{ha[i]}"; v["IY"] = s3(hh[i], ha[i]); v["IM"] = v["IY"] + "/" + v["MS"]
    for ev, dep in ((0, 1), (0, 2), (1, 0), (2, 0)): v[f"H{ev}{dep}"] = s3(fh[i] + ev, fa[i] + dep)
    return v
NITEL = [nitel(i) for i in range(n)]
SAYI = {"AU": (fh + fa).astype(float), "EV": fh.astype(float), "DP": fa.astype(float),
        "IG": np.where(iyok, hh + ha, np.nan).astype(float), "KO": kor.astype(float), "KA": kart.astype(float)}
CIZ = {"AU": [1.5, 2.5, 3.5, 4.5, 5.5], "EV": [0.5, 1.5, 2.5], "DP": [0.5, 1.5, 2.5], "IG": [0.5, 1.5, 2.5],
       "KO": [6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5, 13.5], "KA": [1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5]}
TUR = {"SK": "Kesin skor", "IS": "İlk yarı skoru", "IM": "İY/MS", "MS": "Maç sonucu", "CS": "Çifte şans", "IY": "İlk yarı sonucu",
       "GA": "Gol aralığı", "AU": "Alt/Üst", "KG": "Karşılıklı gol", "H": "Handikap", "EV": "Ev golü", "DP": "Deplasman golü",
       "IG": "İlk yarı gol", "KO": "Korner", "KA": "Kart"}

def tahminler(L):
    """L: benzer maç indeksleri. Dönüş: [(kod, tür, test(i)->bool/None)]"""
    out = []
    def hepsi(k):
        vs = [NITEL[j].get(k) for j in L]
        return vs[0] if vs[0] is not None and all(x == vs[0] for x in vs) else None
    for k in ("SK", "IS", "IM"):
        v = hepsi(k)
        if v: out.append((k + v, TUR[k], lambda i, k=k, v=v: (NITEL[i].get(k) == v) if NITEL[i].get(k) is not None else None))
    ms = hepsi("MS")
    if ms: out.append(("MS" + ms, TUR["MS"], lambda i, v=ms: NITEL[i]["MS"] == v))
    else:
        for cs in ("1X", "X2", "12"):
            if all(NITEL[j]["MS"] in cs for j in L): out.append(("CS" + cs, TUR["CS"], lambda i, cs=cs: NITEL[i]["MS"] in cs))
    for k in ("IY", "GA", "KG"):
        v = hepsi(k)
        if v: out.append((k + v, TUR[k], lambda i, k=k, v=v: (NITEL[i].get(k) == v) if NITEL[i].get(k) is not None else None))
    for ev, dep, izin in ((0, 1, "1X"), (0, 2, "1X"), (1, 0, "X2"), (2, 0, "X2")):
        k = f"H{ev}{dep}"; v = hepsi(k)
        if v and v in izin: out.append((k + v, TUR["H"], lambda i, k=k, v=v: NITEL[i][k] == v))
    for k in ("AU", "EV", "DP", "IG", "KO", "KA"):
        x = SAYI[k][L]
        if np.isnan(x).any(): continue
        mn, mx = x.min(), x.max(); cz = CIZ[k]
        ust = [c_ for c_ in cz if mn > c_]; alt = [c_ for c_ in cz if mx < c_]
        if ust:
            u = ust[-1]; out.append((f"{k}U{u}", TUR[k], lambda i, k=k, u=u: None if np.isnan(SAYI[k][i]) else SAYI[k][i] > u))
        if alt:
            a = alt[0]; out.append((f"{k}A{a}", TUR[k], lambda i, k=k, a=a: None if np.isnan(SAYI[k][i]) else SAYI[k][i] < a))
    return out

def oran(test, idx):
    n_ = h_ = 0
    for j in idx:
        r = test(j)
        if r is None: continue
        n_ += 1; h_ += r
    return n_, h_

# ---------------------------------------------------------------- çalıştır
TEST_BAS = (pd.Timestamp("2024-07-01") - pd.Timestamp("1970-01-01")).days
def calistir(N=3, w_sira=0.0, tol=0.025, sadece_tam_sira=False):
    kayit = []   # (maç, kod, tür, tuttu, tah, taban, sezon)
    for lg in np.unique(lig):
        idx = np.where(lig == lg)[0]; idx = idx[np.argsort(gun[idx], kind="stable")]
        g = gun[idx]
        for jj, i in enumerate(idx):
            if gun[i] < TEST_BAS: continue
            b = np.searchsorted(g, gun[i], side="left")
            if b < 30: continue
            onc = idx[:b]
            dm = np.maximum.reduce([np.abs(P[onc, 0] - P[i, 0]), np.abs(P[onc, 1] - P[i, 1]), np.abs(P[onc, 2] - P[i, 2])])
            if not np.isnan(U[i]):
                du = np.abs(U[onc] - U[i]); dm = np.maximum(dm, np.where(np.isnan(du), 9, du))
            gen = onc[dm <= 2 * tol]                                   # geniş pencere (tahmini ihtimal için)
            dd = dm.copy()
            if w_sira > 0:
                if np.isnan(RH[i]): continue
                ds = np.maximum(np.abs(RH[onc] - RH[i]), np.abs(RA[onc] - RA[i]))
                dd = np.maximum(dd, w_sira * np.where(np.isnan(ds), 9, ds))
            aday = np.where(dd <= 2 * tol)[0]
            if len(aday) < N: continue
            sec = aday[np.lexsort((-g[aday], dd[aday]))][:N]
            L = onc[sec]
            for kod, tur, test in tahminler(L):
                r = test(i)
                if r is None: continue
                ln, lh = oran(test, onc)                              # lig tabanı (maçtan önce)
                lo = lh / ln if ln >= 30 else np.nan
                gn, gh = oran(test, gen)
                tah = (gh + 8 * lo) / (gn + 8) if not np.isnan(lo) else (gh / gn if gn else np.nan)
                kayit.append((i, kod, tur, int(r), tah, lo, d.sezon.values[i]))
    return pd.DataFrame(kayit, columns=["mac", "kod", "tur", "y", "tah", "taban", "sezon"])

if __name__ == "__main__":
    t0 = time.time()
    R = calistir(N=3)
    print("süre", round(time.time() - t0, 1), "sn; tahmin", len(R), "maç", R.mac.nunique())
    pickle.dump(R, open("uc2_N3.pkl", "wb"))
