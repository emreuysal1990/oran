"""
Öneri formülü (yalnızca numpy). guncelle.py her çalışmada bunu çağırır; sonuç veri.json'daki "oneri" bölümüne yazılır.

Formül (arastirma/f_*.py ile 22 Avrupa liginde, 2024-07 -> 2026-09 arasında, her maç yalnızca kendinden önceki veriyle test edildi):
  1) İhtimal: maçın kendi oranlarından kurulan gol modeli (Poisson / Dixon-Coles; korner ve kart negatif binom).
     Test döneminde her ihtimal aralığında tutma oranı modelin ihtimaliyle 1 puan içinde aynı çıktı.
  2) Destek: oranları en çok benzeyen 10 geçmiş maçın (aynı lig, marjsız 1-X-2 ve 2,5 Alt/Üst ±2,5 puan) en az 9'unda
     o pazar tuttuysa öneri "destekli" sayılır. Destekli öneriler iki sezonda da modelin söylediğinden +0,5 ve +1,2 puan
     daha sık tuttu; bu yüzden beklenen tutma oranına 1 puan eklenir.
  3) Öneri: adil oran (1 / ihtimal) en az 1,20, ihtimal en az seçilen sınır (sayfada ayarlanır, varsayılan %70).
  Denenip elenenler: takım formu (gol, isabetli şut, şut, korner, kart, puan) eklemek tahminleri kötüleştirdi;
  en yakın 3 maçta ortak sonuç ve lig sırası benzerliği ihtimalin üstüne bir şey katmadı.
"""
import math

import numpy as np

import modelkit as mk

# (kod, etiket, grup) — sayfadaki etiketlerle aynı
PAZARLAR = [
    ("MS1", "MS 1", "Maç sonucu"), ("MSX", "MS X", "Maç sonucu"), ("MS2", "MS 2", "Maç sonucu"),
    ("CS1X", "Çifte şans 1X", "Maç sonucu"), ("CSX2", "Çifte şans X2", "Maç sonucu"), ("CS12", "Çifte şans 12", "Maç sonucu"),
    ("U15", "1,5 Üst", "Toplam gol"), ("A15", "1,5 Alt", "Toplam gol"), ("U25", "2,5 Üst", "Toplam gol"), ("A25", "2,5 Alt", "Toplam gol"),
    ("U35", "3,5 Üst", "Toplam gol"), ("A35", "3,5 Alt", "Toplam gol"), ("U45", "4,5 Üst", "Toplam gol"), ("A45", "4,5 Alt", "Toplam gol"),
    ("KGV", "KG Var", "Karşılıklı gol"), ("KGY", "KG Yok", "Karşılıklı gol"),
    ("EV05U", "Ev 0,5 Üst", "Takım golü"), ("EV05A", "Ev 0,5 Alt", "Takım golü"), ("EV15U", "Ev 1,5 Üst", "Takım golü"),
    ("EV15A", "Ev 1,5 Alt", "Takım golü"), ("EV25U", "Ev 2,5 Üst", "Takım golü"),
    ("DEP05U", "Dep 0,5 Üst", "Takım golü"), ("DEP05A", "Dep 0,5 Alt", "Takım golü"), ("DEP15U", "Dep 1,5 Üst", "Takım golü"),
    ("DEP15A", "Dep 1,5 Alt", "Takım golü"), ("DEP25U", "Dep 2,5 Üst", "Takım golü"),
    ("IY1", "İY 1", "İlk yarı"), ("IYX", "İY X", "İlk yarı"), ("IY2", "İY 2", "İlk yarı"),
    ("IY05U", "İY 0,5 Üst", "İlk yarı"), ("IY05A", "İY 0,5 Alt", "İlk yarı"), ("IY15U", "İY 1,5 Üst", "İlk yarı"),
    ("IY15A", "İY 1,5 Alt", "İlk yarı"), ("IYKGV", "İY KG Var", "İlk yarı"),
    ("IY2Y05U", "2. yarı 0,5 Üst", "İkinci yarı"), ("IY2Y15U", "2. yarı 1,5 Üst", "İkinci yarı"),
    ("K75U", "Korner 7,5 Üst", "Korner"), ("K85U", "Korner 8,5 Üst", "Korner"), ("K85A", "Korner 8,5 Alt", "Korner"),
    ("K95U", "Korner 9,5 Üst", "Korner"), ("K95A", "Korner 9,5 Alt", "Korner"), ("K105U", "Korner 10,5 Üst", "Korner"),
    ("K105A", "Korner 10,5 Alt", "Korner"), ("K115A", "Korner 11,5 Alt", "Korner"),
    ("C25U", "Kart 2,5 Üst", "Kart"), ("C35U", "Kart 3,5 Üst", "Kart"), ("C35A", "Kart 3,5 Alt", "Kart"),
    ("C45U", "Kart 4,5 Üst", "Kart"), ("C45A", "Kart 4,5 Alt", "Kart"), ("C55U", "Kart 5,5 Üst", "Kart"), ("C55A", "Kart 5,5 Alt", "Kart"),
]
KODLAR = [p[0] for p in PAZARLAR]
GRUPLAR = ["Maç sonucu", "Toplam gol", "Karşılıklı gol", "Takım golü", "İlk yarı", "İkinci yarı", "Korner", "Kart"]
GRUP_I = np.array([GRUPLAR.index(p[2]) for p in PAZARLAR])

EN_AZ_ADIL = 1.20          # 1,20 altındaki adil oranlar önerilmez
TABAN_IHTIMAL = 0.55       # sayfada seçilebilecek en düşük ihtimal sınırı (daha altı saklanmaz)
TOL = 0.025                # benzerlik toleransı (±2,5 puan)
YAKIN = 10                 # en yakın kaç maç
DESTEK_EN_AZ_MAC = 8       # destek için en az bu kadar sonucu bilinen benzer maç
DESTEK_ORAN = 0.9          # ... ve en az %90'ında tutmuş olmalı
DESTEK_EK = 0.01           # destekli önerilerin beklenen tutmasına eklenen pay (araştırma: +0,5 / +1,2 puan)
IDDAA_MARJ = 1.19          # tahmini İddaa oranı = adil oran / 1,19 (örnek maçlarda MS, Alt/Üst, KG marjı %18-19)
GUNUN5_ESIK = [1.2, 1.3, 1.4, 1.5]   # "Günün 5'i": tahmini İddaa oranı en az bu kadar
GUNUN5_ADET = 5

_K = np.arange(mk.G)
_LF = np.array([math.lgamma(k + 1) for k in range(mk.G)])


def _pois(lam):
    lam = np.clip(lam, 1e-4, 9.0)
    return np.exp(-lam[:, None] + _K[None, :] * np.log(lam)[:, None] - _LF[None, :])


def ihtimaller(lh, la, mc, mkart, kat):
    """Her maç için 51 pazarın model ihtimali (n, 51). Korner/kart ortalaması yoksa o pazarlar NaN."""
    n = len(lh)
    M = mk.matris(lh, la, kat["rho"])
    p1, px, p2, T = mk.ozet(M)
    c = np.cumsum(T, 1)
    ev, dp = M.sum(2), M.sum(1)
    evc, dpc = np.cumsum(ev, 1), np.cumsum(dp, 1)
    o = {"MS1": p1, "MSX": px, "MS2": p2, "CS1X": p1 + px, "CSX2": px + p2, "CS12": p1 + p2}
    for k, kk in ((15, 1), (25, 2), (35, 3), (45, 4)):
        o[f"A{k}"], o[f"U{k}"] = c[:, kk], 1 - c[:, kk]
    kgv = 1 - ev[:, 0] - dp[:, 0] + M[:, 0, 0]
    o["KGV"], o["KGY"] = kgv, 1 - kgv
    o["EV05A"], o["EV05U"], o["EV15A"], o["EV15U"], o["EV25U"] = evc[:, 0], 1 - evc[:, 0], evc[:, 1], 1 - evc[:, 1], 1 - evc[:, 2]
    o["DEP05A"], o["DEP05U"], o["DEP15A"], o["DEP15U"], o["DEP25U"] = dpc[:, 0], 1 - dpc[:, 0], dpc[:, 1], 1 - dpc[:, 1], 1 - dpc[:, 2]
    # ilk yarı: bağımsız Poisson (gollerin fh / fa payı)
    Mh = _pois(lh * kat["fh"])[:, :, None] * _pois(la * kat["fa"])[:, None, :]
    q1, qx, q2, Th = mk.ozet(Mh)
    ch = np.cumsum(Th, 1)
    o["IY1"], o["IYX"], o["IY2"] = q1, qx, q2
    o["IY05A"], o["IY05U"], o["IY15A"], o["IY15U"] = ch[:, 0], 1 - ch[:, 0], ch[:, 1], 1 - ch[:, 1]
    o["IYKGV"] = (1 - Mh.sum(2)[:, 0]) * (1 - Mh.sum(1)[:, 0])
    l2 = lh * (1 - kat["fh"]) + la * (1 - kat["fa"])
    e0 = np.exp(-l2)
    o["IY2Y05U"], o["IY2Y15U"] = 1 - e0, 1 - e0 * (1 + l2)
    for anahtar, mu_, kodlar in (("c", mc, [("K75U", 8, 1), ("K85U", 9, 1), ("K85A", 9, 0), ("K95U", 10, 1), ("K95A", 10, 0),
                                               ("K105U", 11, 1), ("K105A", 11, 0), ("K115A", 12, 0)]),
                                 ("k", mkart, [("C25U", 3, 1), ("C35U", 4, 1), ("C35A", 4, 0), ("C45U", 5, 1), ("C45A", 5, 0),
                                               ("C55U", 6, 1), ("C55A", 6, 0)])):
        var = np.isfinite(mu_)
        cum = np.full((n, 41), np.nan)
        if var.any():
            cum[var] = np.cumsum(mk.nb_tablo(mu_[var], kat[anahtar]["alfa"]), 1)
        for kod, esik, ust in kodlar:
            p = 1 - cum[:, esik - 1]
            o[kod] = p if ust else 1 - p
    return np.column_stack([o[k] for k in KODLAR])


def sonuclar(maclar):
    """Oynanmış maçların 51 pazardaki sonucu (1 tuttu, 0 tutmadı, NaN bilinmiyor). sonuc: [ev, dep, İYev, İYdep, korner, kart]"""
    out = np.full((len(maclar), len(KODLAR)), np.nan)
    for i, m in enumerate(maclar):
        s = m.get("sonuc")
        if not s or s[0] is None or s[1] is None:
            continue
        fh, fa = s[0], s[1]
        t = fh + fa
        v = {"MS1": fh > fa, "MSX": fh == fa, "MS2": fh < fa, "CS1X": fh >= fa, "CSX2": fh <= fa, "CS12": fh != fa,
             "U15": t >= 2, "A15": t <= 1, "U25": t >= 3, "A25": t <= 2, "U35": t >= 4, "A35": t <= 3, "U45": t >= 5, "A45": t <= 4,
             "KGV": fh > 0 and fa > 0, "KGY": fh == 0 or fa == 0,
             "EV05U": fh >= 1, "EV05A": fh == 0, "EV15U": fh >= 2, "EV15A": fh <= 1, "EV25U": fh >= 3,
             "DEP05U": fa >= 1, "DEP05A": fa == 0, "DEP15U": fa >= 2, "DEP15A": fa <= 1, "DEP25U": fa >= 3}
        if s[2] is not None and s[3] is not None:
            hh, ha = s[2], s[3]
            ht, h2 = hh + ha, t - hh - ha
            v.update({"IY1": hh > ha, "IYX": hh == ha, "IY2": hh < ha, "IY05U": ht >= 1, "IY05A": ht == 0, "IY15U": ht >= 2,
                      "IY15A": ht <= 1, "IYKGV": hh > 0 and ha > 0, "IY2Y05U": h2 >= 1, "IY2Y15U": h2 >= 2})
        if s[4] is not None:
            k = s[4]
            v.update({"K75U": k >= 8, "K85U": k >= 9, "K85A": k <= 8, "K95U": k >= 10, "K95A": k <= 9, "K105U": k >= 11,
                      "K105A": k <= 10, "K115A": k <= 11})
        if s[5] is not None:
            k = s[5]
            v.update({"C25U": k >= 3, "C35U": k >= 4, "C35A": k <= 3, "C45U": k >= 5, "C45A": k <= 4, "C55U": k >= 6, "C55A": k <= 5})
        for j, kod in enumerate(KODLAR):
            if kod in v:
                out[i, j] = 1.0 if v[kod] else 0.0
    return out


def marjsiz(maclar):
    """Marjı çıkarılmış 1-X-2 ve 2,5 Üst ihtimali (güç yöntemi). Dönüş: (n, 4); 2,5 oranı yoksa son sütun NaN."""
    o = np.array([[(x / 100.0 if x else np.nan) for x in m["oran"][:5]] for m in maclar], float)
    out = np.full((len(maclar), 4), np.nan)
    ok = np.isfinite(o[:, :3]).all(1)
    if ok.any():
        out[ok, :3] = mk.marj_guc(o[ok, 0], o[ok, 1], o[ok, 2])
    au = ok & np.isfinite(o[:, 3]) & np.isfinite(o[:, 4])
    if au.any():
        out[au, 3] = mk.marj_guc(o[au, 3], o[au, 4])[:, 0]
    return out


def benzer_destek(gecmis, Yg, Pg, hedefler, Ph):
    """
    Her hedef maç için aynı ligde, kendisinden önceki günlerde oynanmış, oranları en çok benzeyen 10 maç
    (marjsız 1, X, 2 ve varsa 2,5 Üst farkının en büyüğü ±2,5 puan içinde). Dönüş: N, H (hedef, 51) — sonucu bilinen ve tutan sayısı.
    """
    N = np.zeros((len(hedefler), len(KODLAR)), np.int16)
    H = np.zeros((len(hedefler), len(KODLAR)), np.int16)
    lig_g = np.array([m["lig"] for m in gecmis]); gun_g = np.array([m["gun"] for m in gecmis])
    lig_h = np.array([m["lig"] for m in hedefler]); gun_h = np.array([m["gun"] for m in hedefler])
    for lg in set(lig_h.tolist()):
        gi = np.where(lig_g == lg)[0]
        if not len(gi):
            continue
        gi = gi[np.argsort(gun_g[gi], kind="stable")]
        g = gun_g[gi]; P = Pg[gi]; Y = Yg[gi]
        au_lig = np.isfinite(P[:, 3]).mean() > 0.5
        for hi in np.where(lig_h == lg)[0]:
            t = Ph[hi]
            if not np.isfinite(t[:3]).all():
                continue
            b = np.searchsorted(g, gun_h[hi], side="left")
            if b == 0:
                continue
            dm = np.abs(P[:b, :3] - t[:3]).max(1)
            if au_lig and np.isfinite(t[3]):
                du = np.abs(P[:b, 3] - t[3])
                dm = np.maximum(dm, np.where(np.isfinite(du), du, 9.0))
            aday = np.where(dm <= TOL + 1e-12)[0]
            if not len(aday):
                continue
            sec = aday[np.lexsort((-g[aday], dm[aday]))][:YAKIN]
            y = Y[sec]
            N[hi] = np.isfinite(y).sum(0)
            H[hi] = np.nansum(y, 0)
    return N, H


def destekli(N, H):
    return (N >= DESTEK_EN_AZ_MAC) & (H >= DESTEK_ORAN * N - 1e-9)


def oneriler(P, N, H):
    """Her maç için önerilebilir pazarlar: [[pazar sırası, ihtimal×1000, benzer maç sayısı, tutan], ...] (ihtimale göre azalan)."""
    out = []
    for i in range(len(P)):
        p = P[i]
        ok = np.isfinite(p) & (p >= TABAN_IHTIMAL) & (p <= 1 / EN_AZ_ADIL + 1e-9)
        js = np.where(ok)[0]
        js = js[np.argsort(-p[js])]
        out.append([[int(j), int(round(p[j] * 1000)), int(N[i, j]), int(H[i, j])] for j in js])
    return out


def performans(P, Y, N, H, gunler, donemler):
    """
    Önerilerin geçmiş performansı, sayfadaki filtrelere göre toplanabilsin diye ince dilimlerle:
    satır = [ihtimal dilimi (%55..%83, 1 puan), destekli (0/1), grup, öneri sayısı, tutan, ihtimal toplamı] — dönem başına.
    """
    ok = np.isfinite(P) & np.isfinite(Y) & (P >= TABAN_IHTIMAL) & (P <= 1 / EN_AZ_ADIL + 1e-9)
    dil = np.floor(np.where(np.isfinite(P), P, 0) * 100 + 1e-9).astype(int)
    des = destekli(N, H)
    out = {}
    for ad, (bas, bit) in donemler.items():
        m = ok & ((gunler >= bas) & (gunler < bit))[:, None]
        sat = {}
        for i, j in zip(*np.where(m)):
            k = (int(dil[i, j]), int(des[i, j]), int(GRUP_I[j]))
            s = sat.setdefault(k, [0, 0, 0.0])
            s[0] += 1; s[1] += int(Y[i, j]); s[2] += float(P[i, j])
        out[ad] = [[a, b, c, s[0], s[1], round(s[2], 2)] for (a, b, c), s in sorted(sat.items())]
    return out


def gunun5_sec(p, destek, gecerli):
    """
    Bir günün maçlarından "Günün 5'i": her maçta, geçerli pazarlar içinde beklenen tutması en yüksek olan (ihtimal + destek payı);
    sonra maçlar bu değere göre sıralanır, ilk 5 alınır. p: (maç, pazar) ihtimal (binde bire yuvarlanmış), destek: bool, gecerli: bool.
    Dönüş: [(maç sırası, pazar sırası), ...]. Sayfa aynı kuralı aynı sırayla uygular (eşitlikte ihtimal, sonra maç anahtarı).
    """
    bek = np.where(gecerli, p + np.where(destek, DESTEK_EK, 0.0), -1.0)
    secim = []
    for i in range(p.shape[0]):
        if not gecerli[i].any():
            continue
        js = np.where(gecerli[i])[0]
        j = js[np.lexsort((js, -p[i, js], -bek[i, js]))][0]
        secim.append((float(bek[i, j]), float(p[i, j]), i, int(j)))
    return secim


def gunun5_karne(P, N, H, Y, gunler, anahtarlar, donemler):
    """Kuralın geçmişte her gün uygulanmış hâli: eşik ve dönem başına özet (günler, tahminler, tutan, dağılım, 5'li kupon)."""
    pr = np.round(np.where(np.isfinite(P), P, -1.0) * 1000) / 1000
    des = destekli(N, H)
    taban = np.isfinite(P) & (pr >= TABAN_IHTIMAL)
    out = {}
    gun_listesi = sorted(set(gunler.tolist()))
    idx_gun = {g: np.where(gunler == g)[0] for g in gun_listesi}
    for esik in GUNUN5_ESIK:
        gecerli_tum = taban & (pr <= 1 / (esik * IDDAA_MARJ) + 1e-9)
        sonuc_gun = []        # (gün, [ (tuttu or None, p, oran) ...])
        for g in gun_listesi:
            ii = idx_gun[g]
            sec = gunun5_sec(pr[ii], des[ii], gecerli_tum[ii])
            sec.sort(key=lambda x: (-x[0], -x[1], anahtarlar[ii[x[2]]]))
            sec = sec[:GUNUN5_ADET]
            if not sec:
                continue
            sat = []
            for b, p_, i_, j in sec:
                y = Y[ii[i_], j]
                sat.append((None if not np.isfinite(y) else bool(y), p_, max(1.01, 1 / (p_ * IDDAA_MARJ))))
            sonuc_gun.append((g, sat))
        d_out = {}
        for ad, (bas, bit) in donemler.items():
            gunler_d = [(g, s_) for g, s_ in sonuc_gun if bas <= g < bit]
            n = h = 0; ps = 0.0; dag = [0] * (GUNUN5_ADET + 1); kupon_n = kupon_h = 0; kupon_oran = 0.0
            for g, s_ in gunler_d:
                for t, p_, o in s_:
                    if t is None:
                        continue
                    n += 1; h += int(t); ps += p_
                if len(s_) == GUNUN5_ADET and all(t is not None for t, _, _ in s_):
                    k = sum(int(t) for t, _, _ in s_); dag[k] += 1; kupon_n += 1; kupon_h += int(k == GUNUN5_ADET)
                    kupon_oran += float(np.prod([o for _, _, o in s_]))
            d_out[ad] = {"gun": len(gunler_d), "n": n, "h": h, "p": round(ps, 2), "dagilim": dag, "kupon_gun": kupon_n,
                         "kupon_tuttu": kupon_h, "kupon_oran_ort": round(kupon_oran / kupon_n, 2) if kupon_n else None}
        out[f"{esik:.2f}"] = d_out
    return out
