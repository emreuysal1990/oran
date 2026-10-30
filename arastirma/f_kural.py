import sys, pickle, warnings; sys.path.insert(0, "."); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
import veri
G0 = pd.Timestamp("1970-01-01"); gn = lambda s: (pd.Timestamp(s) - G0).days
c = pickle.load(open("cache.pkl", "rb")); z = pickle.load(open("f_ozellik.pkl", "rb")); SON = pickle.load(open("f_son.pkl", "rb"))
d = c["d"]; gun = d.gun.values; KOD = veri.KODLAR; S = z["S"]; FORM = z["FORM"]; lh, la = c["lh"], c["la"]
lg = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
ll = lambda p, y: -(y * np.log(np.clip(p, 1e-6, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-6, 1)))
# --- 1) sade form göstergesi: isabetli şut temelli atak gücünün oranlardaki beklenen gole göre sapması
sot_h = (FORM[:, 0, 2] + FORM[:, 1, 3]) / 2; sot_a = (FORM[:, 1, 2] + FORM[:, 0, 3]) / 2
x_h = np.log(np.clip(sot_h, .5, None)) - np.log(lh); x_a = np.log(np.clip(sot_a, .5, None)) - np.log(la)
FOLD = {"A": (gn("2023-09-15"), gn("2024-07-01"), gn("2025-07-01")), "B": (gn("2023-09-15"), gn("2025-07-01"), 10 ** 7)}
GOL = [k for k in KOD if veri.GRUP[k] in ("Toplam gol", "Karşılıklı gol", "Takım golü", "Maç sonucu")]
kaz = []
for k in GOL:
    j = KOD.index(k); y = S[:, j]; tot0 = tot1 = 0.0; nn = 0
    for fad, (a, b, e) in FOLD.items():
        PM = z["PM"][fad]; ok = ~np.isnan(y) & ~np.isnan(PM[:, j]) & np.isfinite(x_h) & np.isfinite(x_a)
        tr, te = ok & (gun >= a) & (gun < b), ok & (gun >= b) & (gun < e)
        X = np.column_stack([lg(PM[:, j]), np.nan_to_num(x_h - np.nanmean(x_h[tr])), np.nan_to_num(x_a - np.nanmean(x_a[tr]))])
        m = LogisticRegression(C=1.0, max_iter=500).fit(X[tr], y[tr]); p1 = m.predict_proba(X[te])[:, 1]
        tot0 += ll(PM[te, j], y[te]).sum(); tot1 += ll(p1, y[te]).sum(); nn += te.sum()
    kaz.append(100 * (tot0 - tot1) / tot0)
print("[1] Sade şut göstergesi, gol pazarlarında log kayıp kazancı (%%): ortalama %+.3f, en iyi %+.3f, en kötü %+.3f, iyileşen %d/%d" % (
    np.mean(kaz), max(kaz), min(kaz), sum(x > 0 for x in kaz), len(kaz)))

# --- 2) anlaşılır öneri kuralları (test dönemi, eğitim yok: yalnızca eşikler)
te = gun >= gn("2024-07-01"); NM = te.sum()
P0 = SON["M0"]; N10, H10 = z["V1N"], z["V1H"]; pay = np.where(N10 >= 8, H10 / np.maximum(N10, 1), np.nan)
rows = []
ok = te[:, None] & ~np.isnan(S) & ~np.isnan(P0)
def rap(ad, m):
    y = S[m]; p = P0[m]
    print("  %-52s öneri/maç %.2f | tuttu %.3f | model %.3f | ort. adil oran %.2f" % (ad, m.sum() / NM, y.mean(), p.mean(), np.median(1 / p)))
print("\n[2] Kurallar (adil oran >= 1,20 yani ihtimal <= %83,3), test 2024-07 -> 2026-09:")
UST = 1 / 1.20
for a in (0.60, 0.65, 0.70, 0.75, 0.80):
    rap("ihtimal %d-%.1f" % (100 * a, 100 * UST), ok & (P0 >= a) & (P0 <= UST))
print()
for a in (0.65, 0.70, 0.75):
    base = ok & (P0 >= a) & (P0 <= UST)
    rap("ihtimal >= %d  + benzer 10 maçın 10'u tuttu" % (100 * a), base & (pay >= 0.999))
    rap("ihtimal >= %d  + benzer 10 maçın en az 9'u" % (100 * a), base & (pay >= 0.899))
    rap("ihtimal >= %d  + benzer maçlarda 8'den az tuttu" % (100 * a), base & (pay < 0.8))
# --- 3) adil oran aralığına göre, destekli / desteksiz
print("\n[3] Adil oran aralığına göre (destek = benzer 10 maçın en az 9'u tuttu):")
for lo, hi in ((1.20, 1.30), (1.30, 1.45), (1.45, 1.70), (1.70, 2.00)):
    m = ok & (1 / P0 >= lo) & (1 / P0 < hi)
    a_ = m & (pay >= 0.899); b_ = m & ~(pay >= 0.899)
    print("  adil %.2f-%.2f: destekli n=%6d tuttu %.3f model %.3f | desteksiz n=%7d tuttu %.3f model %.3f | fark(tuttu-model) %+.3f / %+.3f" % (
        lo, hi, a_.sum(), S[a_].mean(), P0[a_].mean(), b_.sum(), S[b_].mean(), P0[b_].mean(), S[a_].mean() - P0[a_].mean(), S[b_].mean() - P0[b_].mean()))
pickle.dump(dict(pay=pay), open("f_pay.pkl", "wb"))
