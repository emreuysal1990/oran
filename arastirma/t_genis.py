import sys, pickle, json; sys.path[:0] = [".", ".."]
import numpy as np, pandas as pd
import veri, genis
c = pickle.load(open("cache.pkl", "rb")); r1 = pickle.load(open("v1_sonuc.pkl", "rb"))
d, lh, la = c["d"], c["lh"], c["la"]
kats = json.load(open("kat_degerlendirme.json"))
h = r1["hedef"]
dt = d.iloc[h].reset_index(drop=True)
G0 = pd.Timestamp("1970-01-01"); gn = lambda s: (pd.Timestamp(s) - G0).days
gh = d.gun.values[h]
pm = None
for ad, (a, b) in (("A", (gn("2024-07-01"), gn("2025-07-01"))), ("B", (gn("2025-07-01"), 10 ** 7))):
    m = (gh >= a) & (gh < b); kat = kats[ad]
    parca = genis.genis_piyasalar(lh[h][m], la[h][m], kat["rho"], kat["fh"], kat["fa"])
    if pm is None: pm = {k: np.full(len(h), np.nan) for k in parca}
    for k, v in parca.items(): pm[k][m] = v
ob = genis.genis_sonuclar(dt)
# tabanı: eğitim döneminde ortalama oran (2023-07 → 2024-06) 
tr = np.where(d.gun.values < d.gun.values[r1["hedef"]].min())[0]
dtr = d.iloc[tr].reset_index(drop=True); otr = genis.genis_sonuclar(dtr)
sat = []
for k in pm:
    y = ob[k]; ok = ~np.isnan(y); p = pm[k]
    taban = np.nanmean(otr[k])
    sat.append((k, ok.sum(), y[ok].mean(), p[ok].mean(), p[ok].mean() - y[ok].mean(), veri.logkayip(p[ok], y[ok]).mean(), veri.logkayip(np.full(ok.sum(), taban), y[ok]).mean()))
T = pd.DataFrame(sat, columns=["pazar", "n", "gerçek", "model", "sapma", "ll_model", "ll_taban"])
T["kazanc"] = T.ll_taban - T.ll_model
pd.set_option("display.width", 200); pd.set_option("display.max_rows", 200)
print(T.round(4).to_string(index=False))
print("ortalama |sapma| = %.4f ; en büyük = %.4f ; tabandan kötü olan pazar: %d/%d" % (T.sapma.abs().mean(), T.sapma.abs().max(), (T.kazanc < 0).sum(), len(T)))
# toplamların 1'e eşitliği
for grp in (["MS1_U25","MS1_A25","MSX_U25","MSX_A25","MS2_U25","MS2_A25"], ["IYMS_11","IYMS_1X","IYMS_12","IYMS_X1","IYMS_XX","IYMS_X2","IYMS_21","IYMS_2X","IYMS_22"], ["TG01","TG23","TG46","TG7P"], ["YARI_1","YARI_E","YARI_2"], ["Y2_1","Y2_X","Y2_2"]):
    print("toplam", grp[0][:6], np.round(sum(pm[k] for k in grp).mean(), 6), np.round(sum(pm[k] for k in grp).std(), 6))
