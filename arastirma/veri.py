"""Araştırma: veriyi yükle, pazar sonuçlarını üret (sayfadaki 49 futbol pazarıyla aynı tanımlar)."""
import os
import numpy as np
import pandas as pd

# Veri: https://github.com/xgabora/Club-Football-Match-Data-2000-2025 (football-data.co.uk kaynaklı). Yol: MATCHES_CSV ortam değişkeni.
KAYNAK = os.environ.get("MATCHES_CSV", "Matches.csv")
ANA = "E0 E1 E2 E3 EC SC0 SC1 SC2 SC3 D1 D2 I1 I2 SP1 SP2 F1 F2 N1 B1 P1 T1 G1".split()

# (kod, grup) — sayfadaki FUTBOL_PAZARLAR ile aynı sırada
PAZARLAR = [
    ("MS1", "Maç sonucu"), ("MSX", "Maç sonucu"), ("MS2", "Maç sonucu"), ("CS1X", "Maç sonucu"), ("CSX2", "Maç sonucu"), ("CS12", "Maç sonucu"),
    ("U15", "Toplam gol"), ("A15", "Toplam gol"), ("U25", "Toplam gol"), ("A25", "Toplam gol"), ("U35", "Toplam gol"), ("A35", "Toplam gol"),
    ("U45", "Toplam gol"), ("A45", "Toplam gol"),
    ("KGV", "Karşılıklı gol"), ("KGY", "Karşılıklı gol"),
    ("EV05U", "Takım golü"), ("EV05A", "Takım golü"), ("EV15U", "Takım golü"), ("EV15A", "Takım golü"), ("EV25U", "Takım golü"),
    ("DEP05U", "Takım golü"), ("DEP05A", "Takım golü"), ("DEP15U", "Takım golü"), ("DEP15A", "Takım golü"), ("DEP25U", "Takım golü"),
    ("IY1", "İlk yarı"), ("IYX", "İlk yarı"), ("IY2", "İlk yarı"), ("IY05U", "İlk yarı"), ("IY05A", "İlk yarı"), ("IY15U", "İlk yarı"),
    ("IY15A", "İlk yarı"), ("IYKGV", "İlk yarı"), ("IY2Y05U", "İkinci yarı"), ("IY2Y15U", "İkinci yarı"),
    ("K75U", "Korner"), ("K85U", "Korner"), ("K85A", "Korner"), ("K95U", "Korner"), ("K95A", "Korner"), ("K105U", "Korner"),
    ("K105A", "Korner"), ("K115A", "Korner"),
    ("C25U", "Kart"), ("C35U", "Kart"), ("C35A", "Kart"), ("C45U", "Kart"), ("C45A", "Kart"), ("C55U", "Kart"), ("C55A", "Kart"),
]
KODLAR = [p[0] for p in PAZARLAR]
GRUP = dict(PAZARLAR)


def yukle(ilk="2023-07-01"):
    """Veri ufku: 2023/24 sezonu başından (1 Temmuz 2023) itibaren. Daha eski veri kullanılmaz."""
    d = pd.read_csv(KAYNAK, low_memory=False)
    d = d[d.Division.isin(ANA) & (d.MatchDate >= ilk)].copy()
    d = d.dropna(subset=["FTHome", "FTAway", "OddHome", "OddDraw", "OddAway"])
    for c in ("OddHome", "OddDraw", "OddAway", "Over25", "Under25", "MaxHome", "MaxDraw", "MaxAway", "MaxOver25", "MaxUnder25"):
        d[c] = d[c].where(d[c] > 1.0)
    d = d.dropna(subset=["OddHome", "OddDraw", "OddAway"])
    d["MatchTime"] = d["MatchTime"].fillna("")
    d = d.sort_values(["MatchDate", "MatchTime", "Division", "HomeTeam"], kind="stable").reset_index(drop=True)
    d["tarih"] = pd.to_datetime(d.MatchDate)
    d["gun"] = (d.tarih - pd.Timestamp("1970-01-01")).dt.days.astype(int)
    # sezon başlangıç yılı
    d["sezon"] = np.where(d.tarih.dt.month >= 7, d.tarih.dt.year, d.tarih.dt.year - 1)
    return d


def sonuclar(d):
    """Her pazar için 0/1 sonuç (uygulanamıyorsa NaN). Dönüş: (n, 49) float."""
    fh, fa = d.FTHome.values, d.FTAway.values
    tot = fh + fa
    hh, ha = d.HTHome.values.astype(float), d.HTAway.values.astype(float)
    ht = hh + ha
    kor = (d.HomeCorners + d.AwayCorners).values.astype(float)
    kart = (d.HomeYellow + d.AwayYellow + d.HomeRed + d.AwayRed).values.astype(float)
    h2 = tot - ht
    f = lambda x: x.astype(float)  # noqa
    n = {}
    n["MS1"], n["MSX"], n["MS2"] = f(fh > fa), f(fh == fa), f(fh < fa)
    n["CS1X"], n["CSX2"], n["CS12"] = f(fh >= fa), f(fh <= fa), f(fh != fa)
    for k, c in ((15, 2), (25, 3), (35, 4), (45, 5)):
        n[f"U{k}"], n[f"A{k}"] = f(tot >= c), f(tot <= c - 1)
    n["KGV"], n["KGY"] = f((fh > 0) & (fa > 0)), f((fh == 0) | (fa == 0))
    n["EV05U"], n["EV05A"], n["EV15U"], n["EV15A"], n["EV25U"] = f(fh >= 1), f(fh == 0), f(fh >= 2), f(fh <= 1), f(fh >= 3)
    n["DEP05U"], n["DEP05A"], n["DEP15U"], n["DEP15A"], n["DEP25U"] = f(fa >= 1), f(fa == 0), f(fa >= 2), f(fa <= 1), f(fa >= 3)
    nanlik = np.isnan(ht)
    iy = lambda x: np.where(nanlik, np.nan, x.astype(float))  # noqa
    n["IY1"], n["IYX"], n["IY2"] = iy(hh > ha), iy(hh == ha), iy(hh < ha)
    n["IY05U"], n["IY05A"], n["IY15U"], n["IY15A"] = iy(ht >= 1), iy(ht == 0), iy(ht >= 2), iy(ht <= 1)
    n["IYKGV"] = iy((hh > 0) & (ha > 0))
    n["IY2Y05U"], n["IY2Y15U"] = iy(h2 >= 1), iy(h2 >= 2)
    kn = np.isnan(kor)
    kx = lambda x: np.where(kn, np.nan, x.astype(float))  # noqa
    n["K75U"], n["K85U"], n["K85A"], n["K95U"], n["K95A"] = kx(kor >= 8), kx(kor >= 9), kx(kor <= 8), kx(kor >= 10), kx(kor <= 9)
    n["K105U"], n["K105A"], n["K115A"] = kx(kor >= 11), kx(kor <= 10), kx(kor <= 11)
    cn = np.isnan(kart)
    cx = lambda x: np.where(cn, np.nan, x.astype(float))  # noqa
    n["C25U"], n["C35U"], n["C35A"], n["C45U"], n["C45A"] = cx(kart >= 3), cx(kart >= 4), cx(kart <= 3), cx(kart >= 5), cx(kart <= 4)
    n["C55U"], n["C55A"] = cx(kart >= 6), cx(kart <= 5)
    return np.column_stack([n[k] for k in KODLAR])


def marj_orantili(*o):
    """Çarpımsal (orantılı) marj temizleme. Girdi: oranlar (diziler)."""
    inv = np.column_stack([1.0 / x for x in o])
    return inv / inv.sum(axis=1, keepdims=True)


def marj_guc(*o, it=40):
    """Güç yöntemi: sum(p_i^k)=1 olan k bulunur (favori-uzun vade yanlılığını azaltır)."""
    inv = np.column_stack([1.0 / x for x in o])
    lo = np.ones(len(inv))
    hi = np.full(len(inv), 3.0)
    for _ in range(it):
        mid = (lo + hi) / 2
        s = (inv ** mid[:, None]).sum(axis=1)
        buyuk = s > 1
        lo = np.where(buyuk, mid, lo)
        hi = np.where(buyuk, hi, mid)
    k = (lo + hi) / 2
    return inv ** k[:, None]


def marj_shin(*o, it=60):
    """Shin yöntemi (iç bilgi payı z). Sütun sayısı >=2."""
    inv = np.column_stack([1.0 / x for x in o])
    toplam = inv.sum(axis=1)
    z = np.zeros(len(inv))
    n = inv.shape[1]
    for _ in range(it):
        p = (np.sqrt(z[:, None] ** 2 + 4 * (1 - z[:, None]) * inv ** 2 / toplam[:, None]) - z[:, None]) / (2 * (1 - z[:, None]))
        z = z + (p.sum(axis=1) - 1) * 0.5 * 1.0
        z = np.clip(z, 0, 0.4)
    p = (np.sqrt(z[:, None] ** 2 + 4 * (1 - z[:, None]) * inv ** 2 / toplam[:, None]) - z[:, None]) / (2 * (1 - z[:, None]))
    return p / p.sum(axis=1, keepdims=True)


def logkayip(p, y, eps=1e-6):
    p = np.clip(p, eps, 1 - eps)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))
