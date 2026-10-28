import sys, pickle; sys.path[:0] = [".", ".."]
import numpy as np, pandas as pd
import veri
c = pickle.load(open("cache.pkl", "rb")); r = pickle.load(open("v1_sonuc.pkl", "rb")); q = pickle.load(open("taban.pkl", "rb")); yy = pickle.load(open("yeni_sonuc.pkl", "rb"))
d, S, PM = c["d"], c["S"], c["PM"]
h = r["hedef"]; Y = S[h]; V1 = r["tah"]; yn, yh = r["yn"], r["yh"]
PC = yy["PMf"][h]; B0 = q["B0"][h]
J = list(range(len(veri.KODLAR)))
sig = (yn >= 4) & (yh == yn)
print("Sinyal sayısı (51 pazar, 4+ benzer maçta hepsi tuttu):", int(sig[:, J].sum()), "maç başına", round(sig[:, J].sum() / len(h), 2))
# toplam: sinyal verilen (maç,pazar) çiftlerinde gerçek tutma oranı, yeni modelin ihtimali, v1 tahmini, taban
tot = dict(n=0, y=0.0, yeni=0.0, v1=0.0, taban=0.0)
satir = []
for j in J:
    m = sig[:, j] & ~np.isnan(Y[:, j]) & ~np.isnan(PC[:, j]) & ~np.isnan(V1[:, j]) & ~np.isnan(B0[:, j])
    if m.sum() == 0: continue
    satir.append((veri.KODLAR[j], int(m.sum()), Y[m, j].mean(), PC[m, j].mean(), V1[m, j].mean(), B0[m, j].mean()))
    tot["n"] += m.sum(); tot["y"] += Y[m, j].sum(); tot["yeni"] += PC[m, j].sum(); tot["v1"] += V1[m, j].sum(); tot["taban"] += B0[m, j].sum()
print("TÜM SİNYALLER: n=%d  gerçekleşen=%.3f  yeni model ihtimali=%.3f  v1 tahmini=%.3f  lig tabanı=%.3f" % (tot["n"], tot["y"]/tot["n"], tot["yeni"]/tot["n"], tot["v1"]/tot["n"], tot["taban"]/tot["n"]))
fark = tot["y"]/tot["n"] - tot["yeni"]/tot["n"]
# standart hata (Bernoulli, yeni model varsayımı altında)
pm = np.concatenate([PC[sig[:, j] & ~np.isnan(Y[:, j]) & ~np.isnan(PC[:, j]) & ~np.isnan(V1[:, j]) & ~np.isnan(B0[:, j]), j] for j in J])
se = np.sqrt((pm * (1 - pm)).sum()) / len(pm)
print("gerçekleşen - yeni model = %+.4f  (standart hata ~%.4f, korelasyon yüzünden gerçek hata daha büyük)" % (fark, se))
df = pd.DataFrame(satir, columns=["pazar", "n", "gerçek", "yeni", "v1", "taban"]).sort_values("n", ascending=False)
print(df.head(14).round(3).to_string(index=False))
# aynı soru: v1 tahmini yüksek olan (>=0.9) için
