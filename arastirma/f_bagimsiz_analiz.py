import sys, pickle, warnings; sys.path.insert(0, "."); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import veri
G0 = pd.Timestamp("1970-01-01"); gn = lambda s: (pd.Timestamp(s) - G0).days
c = pickle.load(open("cache.pkl", "rb")); z = pickle.load(open("f_ozellik.pkl", "rb")); R = pickle.load(open("f_bagimsiz_son.pkl", "rb")); pay = pickle.load(open("f_pay.pkl", "rb"))["pay"]
d = c["d"]; gun = d.gun.values; KOD = veri.KODLAR; S = z["S"]; M0, MS, MH = R["M0"], R["MS"], R["MH"]
FA, FB = (gn("2024-07-01"), gn("2025-07-01")), (gn("2025-07-01"), 10 ** 7)
UST = 1 / (1.30 * 1.19)                  # tahmini İddaa >= 1,30
band = ~np.isnan(S) & ~np.isnan(M0) & ~np.isnan(MS) & (M0 >= 0.55) & (M0 <= UST)
def sezon(m, f): return m & ((gun >= f[0]) & (gun < f[1]))[:, None]
print("[2] İddaa >= 1,30 bandı (oran ihtimali %55-64,6): bağımsız modelin farkına göre tutma - oran ihtimali")
for ad, M in (("yalnız istatistik (MS)", MS), ("istatistik+oran (MH)", MH)):
    fk = M - M0
    print("  ", ad)
    for a_, b_ in ((-1, -0.10), (-0.10, -0.03), (-0.03, 0.03), (0.03, 0.10), (0.10, 1)):
        out = []
        for f in (FA, FB):
            m = sezon(band, f) & (fk >= a_) & (fk < b_)
            out.append((m.sum(), S[m].mean() - M0[m].mean() if m.sum() else np.nan, S[m].mean() if m.sum() else np.nan))
        print("     model farkı %+.2f..%+.2f: A n=%6d tuttu %.3f (oranın %+.3f) | B n=%6d tuttu %.3f (oranın %+.3f)" % (a_, b_, out[0][0], out[0][2], out[0][1], out[1][0], out[1][2], out[1][1]))
# [3] Günün 5'i: sıralama farklı ölçütlerle
print("\n[3] Günün 5'i (tahmini İddaa >= 1,30; her gün 5 ayrı maç), sıralama ölçütüne göre:")
des = (np.where(np.isfinite(pay), pay, 0) >= 0.899)
def gunun5(skor, uygun):
    res = {"A": [0, 0, 0.0, []], "B": [0, 0, 0.0, []]}
    for fad, f in (("A", FA), ("B", FB)):
        for g in np.unique(gun[(gun >= f[0]) & (gun < f[1])]):
            ii = np.where(gun == g)[0]; sec = []
            for i in ii:
                js = np.where(uygun[i])[0]
                if not len(js): continue
                j = js[np.argmax(skor[i, js])]; sec.append((skor[i, j], i, j))
            sec.sort(reverse=True); sec = sec[:5]
            if len(sec) < 5: continue
            t = [S[i, j] for _, i, j in sec]
            if any(np.isnan(t)): continue
            r = res[fad]; r[0] += 5; r[1] += int(sum(t)); r[2] += sum(M0[i, j] for _, i, j in sec); r[3].append(int(sum(t)))
    return res
uygun = band
for ad, skor in (("oran ihtimali + destek (şu anki)", M0 + 0.01 * des), ("istatistik+oran modeli (MH)", np.where(np.isnan(MH), -1, MH)),
                 ("yalnız istatistik (MS)", np.where(np.isnan(MS), -1, MS)), ("iki modelin ortalaması", np.where(np.isnan(MS), -1, (M0 + MS) / 2)),
                 ("MH - oran (en büyük 'değer')", np.where(np.isnan(MH), -1, MH - M0))):
    r = gunun5(skor, uygun)
    s_ = "  %-34s" % ad
    for fad in ("A", "B"):
        n, h, p, gl = r[fad]; gl = np.array(gl)
        s_ += " | sezon %s: tuttu %.3f (oran ihtimali %.3f) günde %.2f/5, 5'te 5 %%%.1f" % (fad, h / n, p / n, gl.mean(), 100 * (gl == 5).mean())
    print(s_)
# [4] Gerçek Bet365 oranıyla getiri (MS ve 2,5 Alt/Üst): model oranın ima ettiğinden yüksek diyorsa oyna
print("\n[4] Bet365 oranıyla getiri (model ihtimali × oran > eşik ise 1 birim):")
pairs = (("MS1", "OddHome"), ("MSX", "OddDraw"), ("MS2", "OddAway"), ("U25", "Over25"), ("A25", "Under25"))
for ad, M in (("istatistik+oran (MH)", MH), ("yalnız istatistik (MS)", MS)):
    for esik in (1.00, 1.05, 1.10):
        out = []
        for f in (FA, FB):
            gl = []
            for k, oc in pairs:
                j = KOD.index(k); o = d[oc].values
                m = (gun >= f[0]) & (gun < f[1]) & np.isfinite(o) & ~np.isnan(M[:, j]) & ~np.isnan(S[:, j]) & (M[:, j] * o > esik)
                gl += list(S[m, j] * o[m] - 1)
            gl = np.array(gl); out.append((len(gl), gl.mean() * 100, 1.96 * gl.std() / np.sqrt(max(len(gl), 1)) * 100))
        print("  %-24s eşik %.2f: sezon A bahis %5d getiri %+.1f%% (±%.1f) | sezon B bahis %5d getiri %+.1f%% (±%.1f)" % (ad, esik, *out[0], *out[1]))
