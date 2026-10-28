"""JS modelinin Python ile aynı sonucu verdiğini doğrulamak için test vakaları ve beklenen değerler üretir -> parite.json"""
import sys, json, pickle; sys.path[:0] = [".", ".."]
import numpy as np
from scipy.stats import norm
import veri, model, genis, modelkit as mk
kat = json.load(open("../katsayilar.json"))
rng = np.random.default_rng(7)
c = pickle.load(open("cache.pkl", "rb"))
n = len(c["lh"]); ix = rng.choice(n, 140, replace=False)
lh = np.concatenate([c["lh"][ix], [0.3, 4.5, 3.0, 0.9, 2.2, 5.5, 0.15, 1.2, 1.2, 2.8]])
la = np.concatenate([c["la"][ix], [0.2, 0.4, 3.0, 0.9, 0.5, 5.0, 0.15, 3.5, 1.2, 0.35]])
mc = rng.uniform(6, 15, len(lh)); mkk = rng.uniform(2.2, 7, len(lh))
out = {"pazar": [], "fit": [], "kk": [], "nba": []}
pm = model.piyasalar(lh, la, kat["rho"], kat["fh"], kat["fa"])
gp = genis.genis_piyasalar(lh, la, kat["rho"], kat["fh"], kat["fa"])
nbc = mk.nb_tablo(mc, kat["c"]["alfa"]); nbk = mk.nb_tablo(mkk, kat["k"]["alfa"])
cc, ck = np.cumsum(nbc, 1), np.cumsum(nbk, 1)
KOR = [("K75U", 8, 1), ("K85U", 9, 1), ("K85A", 9, 0), ("K95U", 10, 1), ("K95A", 10, 0), ("K105U", 11, 1), ("K105A", 11, 0), ("K115A", 12, 0)]
KAR = [("C25U", 3, 1), ("C35U", 4, 1), ("C35A", 4, 0), ("C45U", 5, 1), ("C45A", 5, 0), ("C55U", 6, 1), ("C55A", 6, 0)]
for i in range(len(lh)):
    e = {k: float(v[i]) for k, v in pm.items()}
    for kod, es, ust in KOR: p = 1 - cc[i, es - 1]; e[kod] = float(p if ust else 1 - p)
    for kod, es, ust in KAR: p = 1 - ck[i, es - 1]; e[kod] = float(p if ust else 1 - p)
    g = {k: float(v[i]) if np.ndim(v) else float(v) for k, v in gp.items()}
    out["pazar"].append({"lh": float(lh[i]), "la": float(la[i]), "mc": float(mc[i]), "mk": float(mkk[i]), "temel": e, "genis": g})
# λ uydurma: gerçek oran setleri (bir kısmında 2,5 A/Ü yok)
d = c["d"]; ix2 = rng.choice(len(d), 120, replace=False)
for j, i in enumerate(ix2):
    o = [float(d.OddHome.values[i]), float(d.OddDraw.values[i]), float(d.OddAway.values[i]), float(d.Over25.values[i]), float(d.Under25.values[i])]
    P = mk.marj_guc(np.array([o[0]]), np.array([o[1]]), np.array([o[2]]))[0]
    pu = mk.marj_guc(np.array([o[3]]), np.array([o[4]]))[0, 0]
    lig_u = float(rng.uniform(0.4, 0.62))
    if j % 3 == 0:
        on = mk.pu_onsel_tahmin(P[0:1], P[1:2], P[2:3], np.array([lig_u]), kat["pu_onsel_w"])
        l1, l2 = mk.lambda_uydur(P[0:1], P[1:2], P[2:3], np.array([np.nan]), rho=kat["rho"], pu_onsel=on)
        out["fit"].append({"o": o[:3] + [None, None], "lig_u": lig_u, "lh": float(l1[0]), "la": float(l2[0])})
    else:
        l1, l2 = mk.lambda_uydur(P[0:1], P[1:2], P[2:3], np.array([pu]), rho=kat["rho"])
        out["fit"].append({"o": o, "lig_u": lig_u, "lh": float(l1[0]), "la": float(l2[0])})
# korner / kart ortalaması
ligler = list(kat["c"]["lig"].keys())
for i in range(60):
    t = "c" if i % 2 == 0 else "k"; kt = kat[t]
    ort = np.array(kt["ort"]); sd = np.array(kt["sd"])
    f5 = list(rng.normal(ort[4:], sd[4:] * 0.8))
    if i % 7 == 0: f5[1] = None
    if i % 11 == 0: f5 = [None] * 4 + [f5[4]]
    l1, l2 = float(rng.uniform(0.5, 3.2)), float(rng.uniform(0.3, 2.4))
    lg = ligler[i % len(ligler)] if t == "c" else list(kt["lig"].keys())[i % len(kt["lig"])]
    mu, ok = mk.kk_matris([{"c": f5} if False else f5], np.array([l1]), np.array([l2]), np.array([lg]), kt)
    out["kk"].append({"t": t, "oz": [None if x is None else float(x) for x in f5], "lh": l1, "la": l2, "lig": lg, "mu": float(mu[0])})
# NBA (scipy ile bağımsız uygulama)
sM, sT, sH = 13.0, 18.0, 12.1
def ust(L, mu, sd): return 1 - norm.cdf((np.floor(L) + 0.5 - mu) / sd)
def alt(L, mu, sd): return norm.cdf((np.ceil(L) - 0.5 - mu) / sd)
for i in range(60):
    o1 = float(rng.uniform(1.08, 3.5)); o2 = float(1 / (1.06 - 1 / o1)); hnd = float(rng.choice([-9.5, -6, -5.5, -3.5, -1, 0.5, 2.5, 7, 11.5])) * (1 if o1 > o2 else -1) if False else float(rng.choice([-9.5, -6, -5.5, -3.5, -1.5, 0.5, 2.5, 7.5, 11.5]))
    tot = float(rng.choice([215.5, 220, 224.5, 228, 231.5])); tO = float(rng.uniform(1.8, 2.0)); tU = float(rng.uniform(1.8, 2.0))
    p = mk.marj_guc(np.array([o1]), np.array([o2]))[0, 0]; mu = sM * norm.ppf(p)
    pu = mk.marj_guc(np.array([tO]), np.array([tU]))[0, 0]; muT = np.floor(tot) + 0.5 + sT * norm.ppf(pu)
    r = {"N_MS1": p, "N_MS2": 1 - p}
    pU, pA = ust(tot, muT, sT), alt(tot, muT, sT); push = 1 - pU - pA; r["N_UST"], r["N_ALT"] = pU / (1 - push), pA / (1 - push)
    L = -hnd; pc, pd = ust(L, mu, sM), alt(L, mu, sM); push = 1 - pc - pd; r["N_HEV"], r["N_HDEP"] = pc / (1 - push), pd / (1 - push)
    muH, muA = (muT + mu) / 2, (muT - mu) / 2; evT, depT = (tot - hnd) / 2, (tot + hnd) / 2
    eu, ea, du, da = ust(evT, muH, sH), alt(evT, muH, sH), ust(depT, muA, sH), alt(depT, muA, sH)
    r["N_EVU"], r["N_EVA"], r["N_DEPU"], r["N_DEPA"] = eu / (eu + ea), ea / (eu + ea), du / (du + da), da / (du + da)
    F = lambda a, b: norm.cdf((b - mu) / sM) - norm.cdf((a - mu) / sM); Fd = lambda a, b: norm.cdf((b + mu) / sM) - norm.cdf((a + mu) / sM)
    r["N_E1"], r["N_E6"], r["N_E11"], r["N_E16"] = F(0, 5.5), F(5.5, 10.5), F(10.5, 15.5), 1 - norm.cdf((15.5 - mu) / sM)
    r["N_D1"], r["N_D6"], r["N_D11"], r["N_D16"] = Fd(0, 5.5), Fd(5.5, 10.5), Fd(10.5, 15.5), 1 - norm.cdf((15.5 + mu) / sM)
    out["nba"].append({"m": {"o1": o1, "o2": o2, "hnd": hnd, "tot": tot, "tO": tO, "tU": tU}, "p": {k: float(v) for k, v in r.items()}})
json.dump(out, open("../kaynak/parite.json", "w"))
print({k: len(v) for k, v in out.items()}, "temel:", len(out["pazar"][0]["temel"]), "genis:", len(out["pazar"][0]["genis"]))
